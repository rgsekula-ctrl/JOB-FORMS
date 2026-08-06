#!/usr/bin/env python3
"""Ryan OS - Asset Registry CLI (Phase 2).

The first stop before looking for any work-related resource.

    python3 ryan-os/cli/asset.py find "bid proposal template"
    python3 ryan-os/cli/asset.py where "pricing"        # resolve + what to do next
    python3 ryan-os/cli/asset.py show quickbid-proposal
    python3 ryan-os/cli/asset.py list --category form
    python3 ryan-os/cli/asset.py gaps
    python3 ryan-os/cli/asset.py validate

Exit codes for `where`:
    0  authoritative or candidate asset found - use it
    4  known gap - flag it, do not substitute
    5  not registered - flag it, do not go hunting
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RYAN_OS = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_RYAN_OS, "asset-registry"))

from registry import (  # noqa: E402
    FOUND,
    FOUND_CANDIDATE,
    GAP_FLAGGED,
    NOT_REGISTERED,
    AssetRegistry,
)

DEFAULT_REGISTRY = os.path.join(_RYAN_OS, "asset-registry", "registry.json")


def _load(args) -> AssetRegistry:
    return AssetRegistry.load(args.registry)


def _print_asset(a, verbose: bool = False) -> None:
    badge = {"authoritative": "[AUTHORITATIVE]", "candidate": "[CANDIDATE]",
             "deprecated": "[DEPRECATED]", "gap": "[GAP]"}.get(a.status, f"[{a.status}]")
    print(f"{badge} {a.name}  ({a.asset_id})")
    print(f"  What:     {a.what_it_is}")
    print(f"  Where:    {a.location}")
    if (a.where_it_is or {}).get("detail"):
        print(f"            {a.where_it_is['detail']}")
    print(f"  Owner:    {a.owner}")
    print(f"  Use when: {a.use_when}")
    if a.do_not_use_when:
        print(f"  NOT when: {a.do_not_use_when}")
    if a.replaces:
        print(f"  Replaces: {', '.join(a.replaces)}")
    if a.replaced_by:
        print(f"  Replaced by: {a.replaced_by}")
    if a.status == "gap" and a.gap_recommendation:
        print(f"  GAP:      {a.gap_recommendation}")
    if verbose:
        if a.keywords:
            print(f"  Keywords: {', '.join(a.keywords)}")
        if a.related:
            print(f"  Related:  {', '.join(a.related)}")
        if a.notes:
            print(f"  Notes:    {a.notes}")
        if a.last_verified:
            print(f"  Verified: {a.last_verified}")


def cmd_find(args) -> int:
    reg = _load(args)
    results = reg.search(args.query)
    if not results:
        print(f"No registered asset matches '{args.query}'.")
        print("\nDo NOT go looking elsewhere and use whatever turns up.")
        print("Flag it to Ryan and recommend adding it to the registry.")
        return 5

    for a in results[: args.limit]:
        _print_asset(a, verbose=args.verbose)
        print()
    if len(results) > args.limit:
        print(f"({len(results) - args.limit} more - raise --limit to see them)")
    return 0


def cmd_where(args) -> int:
    reg = _load(args)
    res = reg.resolve(args.query)

    if args.as_json:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"QUERY:   {res.query}")
        print(f"OUTCOME: {res.outcome}")
        print(f"         {res.message}")
        if res.asset and res.outcome != NOT_REGISTERED:
            print()
            _print_asset(res.asset, verbose=args.verbose)
        print()
        print(f"ACTION:  {res.action_required}")
        if res.alternatives:
            print()
            print("Also registered:")
            for a in res.alternatives:
                print(f"  - {a.name} ({a.asset_id}) [{a.status}]")

    return {FOUND: 0, FOUND_CANDIDATE: 0, GAP_FLAGGED: 4, NOT_REGISTERED: 5}.get(res.outcome, 0)


def cmd_show(args) -> int:
    reg = _load(args)
    a = reg.get(args.asset_id)
    if not a:
        print(f"error: no asset with id '{args.asset_id}'", file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(a.to_dict(), indent=2))
    else:
        _print_asset(a, verbose=True)
    return 0


def cmd_list(args) -> int:
    reg = _load(args)
    assets = reg.assets
    if args.category:
        assets = [a for a in assets if a.category == args.category]
    if args.status:
        assets = [a for a in assets if a.status == args.status]

    if not assets:
        print("No assets match that filter.")
        print(f"Categories: {', '.join(reg.categories())}")
        return 0

    assets = sorted(assets, key=lambda a: (a.category, a.asset_id))
    w_id = max(len(a.asset_id) for a in assets) + 2
    w_cat = max(len(a.category) for a in assets) + 2
    w_st = max(len(a.status) for a in assets) + 2

    print(f"{len(assets)} asset(s)\n")
    for a in assets:
        print(f"{a.asset_id:<{w_id}}{a.category:<{w_cat}}{a.status:<{w_st}}{a.name}")
    return 0


def cmd_gaps(args) -> int:
    reg = _load(args)
    gaps = reg.gaps()
    if not gaps:
        print("No gaps registered. Every known resource has an authoritative version.")
        return 0

    print(f"{len(gaps)} REGISTERED GAP(S)")
    print("Resources Ryan OS knows should exist but has no authoritative version for.\n")
    for a in gaps:
        print(f"  {a.name}  ({a.asset_id})")
        print(f"    What:  {a.what_it_is}")
        print(f"    Fix:   {a.gap_recommendation}")
        print()
    print("Until these are registered, agents must flag them rather than substitute another version.")
    return 0


def cmd_validate(args) -> int:
    reg = _load(args)
    errors = reg.validate()
    if errors:
        print(f"{len(errors)} problem(s) in the registry:\n")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"Registry valid. {len(reg.assets)} asset(s), {len(reg.gaps())} registered gap(s).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="asset", description="Ryan OS Asset Registry")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--verbose", "-v", action="store_true")
    sub = ap.add_subparsers(dest="command")

    p = sub.add_parser("find", help="Search the registry")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("where", help="Resolve the authoritative resource and what to do next")
    p.add_argument("query")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.set_defaults(func=cmd_where)

    p = sub.add_parser("show", help="Show one asset")
    p.add_argument("asset_id")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("list", help="List assets")
    p.add_argument("--category")
    p.add_argument("--status")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("gaps", help="Show registered gaps")
    p.set_defaults(func=cmd_gaps)

    p = sub.add_parser("validate", help="Check registry integrity")
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
