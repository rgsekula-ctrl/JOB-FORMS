#!/usr/bin/env python3
"""Ryan OS - Bid Turnover CLI.

Take an intake JSON file (what an agent read out of an Outlook bid request)
and print the internal Load & Bid turnover email.

    python3 ryan-os/cli/turnover.py intake.json
    python3 ryan-os/cli/turnover.py intake.json --json
    python3 ryan-os/cli/turnover.py --new-intake > intake.json
    cat intake.json | python3 ryan-os/cli/turnover.py -

Exit codes (so this can be wired into an automation without parsing text):
    0  PROCEED or PROCEED_WITH_FLAG - safe to send
    2  ESCALATE_TO_RYAN - draft produced, hold for review
    1  bad input
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RYAN_OS = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_RYAN_OS, "decision-engine"))

from engine import (  # noqa: E402
    ESCALATE_TO_RYAN,
    BuilderLibrary,
    decide,
    load_defaults,
    render_email,
)

BLANK_INTAKE = {
    "received_at": "",
    "builder_name": "",
    "from_email": "",
    "project": "",
    "project_type": "new construction",
    "customer_type": "builder",
    "jurisdiction": "",
    "stories": None,
    "conditioned_sqft": None,
    "email_subject": "",
    "email_body": "",
    "attachments": [],
    "plans": {"architectural": False, "mechanical": False, "plot": False},
    "mechanical_plan_system_count": None,
    "ai_plan_review": {"system_count": None, "notes": ""},
    "manual_j": {},
    "explicit": {
        "system_count": None,
        "equipment": "",
        "gross_margin": None,
        "deadline": "",
    },
    "notes": "",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="turnover",
        description="Ryan OS Bid Turnover Decision Engine",
    )
    ap.add_argument("intake", nargs="?", help="Path to intake JSON, or - for stdin")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Emit the full decision object instead of the email")
    ap.add_argument("--new-intake", action="store_true",
                    help="Print a blank intake template and exit")
    ap.add_argument("--profiles", default=None,
                    help="Builder profile directory (default: ryan-os/builder-library/profiles)")
    ap.add_argument("--defaults", default=None,
                    help="Path to defaults.json")
    args = ap.parse_args(argv)

    if args.new_intake:
        print(json.dumps(BLANK_INTAKE, indent=2))
        return 0

    if not args.intake:
        ap.print_help()
        return 1

    try:
        if args.intake == "-":
            intake = json.load(sys.stdin)
        else:
            with open(args.intake, "r", encoding="utf-8") as fh:
                intake = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"error: could not read intake: {exc}", file=sys.stderr)
        return 1

    defaults = load_defaults(args.defaults) if args.defaults else load_defaults()
    library = BuilderLibrary.from_dir(args.profiles) if args.profiles else BuilderLibrary.from_dir()

    decision = decide(intake, library, defaults)

    if args.as_json:
        print(json.dumps(decision.to_dict(), indent=2))
    else:
        print(render_email(decision, defaults))
        print()
        print("-" * 70)
        print(f"OUTCOME: {decision.outcome}")
        if decision.outcome == ESCALATE_TO_RYAN:
            print("ACTION:  Do not send. Ryan reviews the items under Known Unknowns first.")
            for e in decision.escalations:
                print(f"         - {e.reason}")
        else:
            print("ACTION:  Safe to send now.")
        print(f"ENGINE:  v{decision.engine_version} / defaults v{decision.defaults_version}")

    return 2 if decision.outcome == ESCALATE_TO_RYAN else 0


if __name__ == "__main__":
    raise SystemExit(main())
