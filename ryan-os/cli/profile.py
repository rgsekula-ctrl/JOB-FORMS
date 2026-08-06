#!/usr/bin/env python3
"""Ryan OS - Builder Profile CLI (Phase 2).

Turns "we don't know this builder" into a one-keystroke decision.

    # See the governed recommendation for an unknown builder
    python3 ryan-os/cli/profile.py propose intake.json

    # Approve it - writes builder-library/profiles/<slug>.json
    python3 ryan-os/cli/profile.py create intake.json

    # Approve a different classification, or override a value
    python3 ryan-os/cli/profile.py create intake.json --classification new_production
    python3 ryan-os/cli/profile.py create intake.json --margin 32 --equipment "Carrier ..."

    python3 ryan-os/cli/profile.py list
    python3 ryan-os/cli/profile.py show acme-homes
    python3 ryan-os/cli/profile.py validate

Exit codes:
    0  success
    1  bad input / validation failure
    3  profile already exists (use --force to overwrite)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RYAN_OS = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_RYAN_OS, "decision-engine"))

import engine  # noqa: E402
import profile_proposal  # noqa: E402
from profile_proposal import build_profile, propose_profile, render_proposal  # noqa: E402

PROFILES_DIR = os.path.join(_RYAN_OS, "builder-library", "profiles")
SCHEMA_PATH = os.path.join(_RYAN_OS, "builder-library", "schema", "builder_profile.schema.json")


def _load_intake(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _library(profiles_dir: str) -> engine.BuilderLibrary:
    return engine.BuilderLibrary.from_dir(profiles_dir)


# --------------------------------------------------------------------------
# Lightweight schema validation (stdlib only - no jsonschema dependency)
# --------------------------------------------------------------------------

def validate_profile(profile: dict, schema: dict) -> list:
    """Check the things that actually break the engine.

    Deliberately not a full JSON Schema implementation - that would mean a
    dependency, and this catches every failure mode we have seen: missing
    required keys, unknown keys from a typo, bad enums, out-of-range margins.
    """
    errors = []
    props = schema.get("properties", {})

    for key in schema.get("required", []):
        if key not in profile:
            errors.append(f"missing required field: {key}")

    for key in profile:
        if key not in props:
            errors.append(f"unknown field: {key}")

    for key, spec in props.items():
        if key not in profile:
            continue
        value = profile[key]
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{key}: '{value}' is not one of {spec['enum']}")
        if spec.get("type") == "number" and isinstance(value, (int, float)):
            if "minimum" in spec and value < spec["minimum"]:
                errors.append(f"{key}: {value} is below minimum {spec['minimum']}")
            if "maximum" in spec and value > spec["maximum"]:
                errors.append(f"{key}: {value} is above maximum {spec['maximum']}")
        if spec.get("type") == "array" and not isinstance(value, list):
            errors.append(f"{key}: expected a list")
        if spec.get("pattern") and isinstance(value, str):
            import re
            if not re.match(spec["pattern"], value):
                errors.append(f"{key}: '{value}' does not match {spec['pattern']}")

    if profile.get("status") == "flagged" and not profile.get("flag_reason"):
        errors.append("status is 'flagged' but flag_reason is empty - Ryan needs the reason")

    excluded = (profile.get("options") or {}).get("exclude") or []
    reasons = (profile.get("options") or {}).get("exclude_reasons") or {}
    for key in excluded:
        if not reasons.get(key):
            errors.append(f"options.exclude includes '{key}' with no exclude_reasons entry")

    return errors


def _load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_propose(args) -> int:
    intake = _load_intake(args.intake)
    proposal = propose_profile(intake, _library(args.profiles))
    if args.as_json:
        print(json.dumps(proposal.to_dict(), indent=2))
    else:
        print(render_proposal(proposal))
    return 0


def cmd_create(args) -> int:
    intake = _load_intake(args.intake)
    library = _library(args.profiles)
    defaults = engine.load_defaults()

    proposal = propose_profile(intake, library, defaults)

    if proposal.profile_exists and not args.force:
        print(
            f"A profile already exists for this builder: {proposal.existing_profile_id}\n"
            "Edit it directly, or pass --force to write a new one anyway.",
            file=sys.stderr,
        )
        return 3

    candidate = proposal.primary
    if args.classification:
        chosen = proposal.candidate(args.classification)
        if chosen is None:
            valid = ", ".join(c.key for c in proposal.candidates)
            print(f"error: unknown classification '{args.classification}'. Valid: {valid}", file=sys.stderr)
            return 1
        candidate = chosen

    overrides = {}
    if args.margin is not None:
        m = args.margin if args.margin <= 1 else args.margin / 100.0
        overrides["gross_margin"] = m
    if args.equipment:
        overrides["equipment"] = {
            "system": args.equipment, "outdoor_unit": "", "indoor_unit": "",
            "staging": "", "notes": "Set by Ryan when the profile was created.",
        }
    if args.builder_id:
        overrides["builder_id"] = args.builder_id
    if args.display_name:
        overrides["display_name"] = args.display_name

    profile = build_profile(intake, candidate, library, defaults, overrides)

    errors = validate_profile(profile, _load_schema())
    if errors:
        print("error: the generated profile failed validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    os.makedirs(args.profiles, exist_ok=True)
    path = os.path.join(args.profiles, f"{profile['builder_id']}.json")

    if os.path.exists(path) and not args.force:
        print(f"error: {path} already exists. Pass --force to overwrite.", file=sys.stderr)
        return 3

    if args.dry_run:
        print(json.dumps(profile, indent=2))
        print(f"\n(dry run - would write {path})", file=sys.stderr)
        return 0

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2)
        fh.write("\n")

    print(f"Created {path}")
    print(f"  Classification: {candidate.label} [{candidate.confidence}]")
    print(f"  Gross margin:   {profile['gross_margin'] * 100:g}%")
    print(f"  Aliases:        {', '.join(profile['aliases'])}")
    if proposal.needs_confirmation:
        print("\n  Confirm when you get a chance:")
        for n in proposal.needs_confirmation:
            print(f"    - {n}")
    print("\nThe next request from this builder resolves automatically.")
    return 0


def cmd_list(args) -> int:
    library = _library(args.profiles)
    if not library.profiles:
        print(f"No builder profiles in {args.profiles}")
        print("Create one:  python3 ryan-os/cli/profile.py create intake.json")
        return 0

    rows = []
    for p in library.profiles:
        margin = p.get("gross_margin")
        rows.append((
            p.get("builder_id", ""),
            p.get("builder_type", ""),
            p.get("status", ""),
            f"{margin * 100:g}%" if isinstance(margin, (int, float)) else "default",
            p.get("display_name", ""),
        ))

    widths = [max(len(r[i]) for r in rows) + 2 for i in range(4)]
    print(f"{len(rows)} builder profile(s) in {args.profiles}\n")
    for r in sorted(rows):
        print(f"{r[0]:<{widths[0]}}{r[1]:<{widths[1]}}{r[2]:<{widths[2]}}{r[3]:<{widths[3]}}{r[4]}")
    return 0


def cmd_show(args) -> int:
    library = _library(args.profiles)
    for p in library.profiles:
        if p.get("builder_id") == args.builder_id:
            print(json.dumps(p, indent=2))
            return 0
    print(f"error: no profile with builder_id '{args.builder_id}'", file=sys.stderr)
    return 1


def cmd_validate(args) -> int:
    schema = _load_schema()
    library = _library(args.profiles)
    if not library.profiles:
        print(f"No profiles to validate in {args.profiles}")
        return 0

    total_errors = 0
    seen_ids = {}
    for p in library.profiles:
        pid = p.get("builder_id", "<missing id>")
        errors = validate_profile(p, schema)
        if pid in seen_ids:
            errors.append(f"duplicate builder_id (also used by {seen_ids[pid]})")
        seen_ids[pid] = pid
        if errors:
            total_errors += len(errors)
            print(f"FAIL {pid}")
            for e in errors:
                print(f"       - {e}")
        else:
            print(f"ok   {pid}")

    print()
    if total_errors:
        print(f"{total_errors} problem(s) found.")
        return 1
    print(f"All {len(library.profiles)} profile(s) valid.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="profile", description="Ryan OS Builder Profile management")
    ap.add_argument("--profiles", default=PROFILES_DIR, help="Profile directory")
    sub = ap.add_subparsers(dest="command")

    p = sub.add_parser("propose", help="Show the governed recommendation for an unknown builder")
    p.add_argument("intake", help="Intake JSON, or - for stdin")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("create", help="Create a Builder Profile from the recommendation")
    p.add_argument("intake", help="Intake JSON, or - for stdin")
    p.add_argument("--classification", help="Override the recommended classification key")
    p.add_argument("--margin", type=float, help="Override gross margin (32 or 0.32)")
    p.add_argument("--equipment", help="Override the standard equipment description")
    p.add_argument("--builder-id", help="Override the generated slug")
    p.add_argument("--display-name", help="Override the display name")
    p.add_argument("--dry-run", action="store_true", help="Print the profile instead of writing it")
    p.add_argument("--force", action="store_true", help="Overwrite an existing profile")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("list", help="List builder profiles")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="Print one profile")
    p.add_argument("builder_id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("validate", help="Validate every profile against the schema")
    p.set_defaults(func=cmd_validate)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 1

    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
