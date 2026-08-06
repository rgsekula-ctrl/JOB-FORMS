# Ryan OS Builder Library

One JSON file per builder in `profiles/`. This is the authoritative record of
what Ryan OS knows about each builder, and anything set here **overrides** the
governed defaults in `../decision-engine/defaults.json`.

**The library is currently empty.** Populating it with real profiles for active
builders is the highest-value next task in the whole project — it needs no code
and no approval, and every field filled in converts a MEDIUM assumption to HIGH.
That is the system getting faster and safer at the same time.

---

## Adding a builder

```bash
cp ryan-os/builder-library/_TEMPLATE.builder.json \
   ryan-os/builder-library/profiles/acme-homes.json
```

Then edit. Minimum viable profile — even this much is worth committing:

```json
{
  "builder_id": "acme-homes",
  "display_name": "Acme Homes",
  "status": "active",
  "builder_type": "production",
  "aliases": ["Acme Homes", "Acme", "acmehomes.com"]
}
```

Verify it loads and matches:

```bash
python3 ryan-os/tests/test_engine.py
```

## Aliases are the most important field

Matching runs in this order:

1. **Email domain** against an alias — most reliable, because superintendents
   type the builder name a dozen different ways but always send from the same
   domain. **Always include the bare domain** (`acmehomes.com`, no `@`).
2. Exact name against `display_name`, `builder_id`, or any alias.
3. Loose containment, longest alias first.

Add every way the builder shows up in Outlook: legal name, DBA, the shorthand
the superintendent uses, and the domain.

## Fields that change the turnover

| Field | Effect |
|---|---|
| `builder_type` | Drives the equipment default: `production` → Carrier, `custom`/`semi-custom` → Lennox EL19KPV |
| `gross_margin` | Overrides the 35% / 30% default at HIGH confidence. **This is where a production builder's real contracted margin belongs.** |
| `equipment` | Overrides the production/custom default at HIGH confidence |
| `jurisdiction` | Turns the permit line from LOW to HIGH confidence |
| `manual_j_overrides` | Builder-standard envelope specs that beat the Ryan OS defaults |
| `options.exclude` | Drops an always-include option — **requires a written reason** |
| `standing_instructions` | Rendered verbatim in every turnover email |
| `system_count_rule` | Free text surfaced to the estimator, e.g. "one system up to 3,000 sqft" |
| `attachments_expected` | Drives the missing-attachment flags |
| `status: flagged` | **Hard stop** — escalates to Ryan. Requires `flag_reason`. |
| `requires_ryan_margin_approval` | **Hard stop** — margin renders as HOLD |

## Excluding an option

Excluding one of the eight always-include options requires a reason:

```json
"options": {
  "exclude": ["decorative_grilles"],
  "exclude_reasons": {
    "decorative_grilles": "Builder uses standard stamped grilles on every plan; the upgrade is never taken."
  }
}
```

The exclusion and its reason both print in the email under Builder Standing
Instructions — so a silent omission is impossible, and anyone reading the email
sees both *what* was dropped and *why*.

## Schema

`schema/builder_profile.schema.json`. Full field documentation lives in the
schema's `description` fields.

## Examples

`examples/` holds two profiles used by the test suite and for onboarding:

- `example-production-homes.json` — full profile: contracted 20% margin, Carrier
  standard package, an excluded option, standing instructions.
- `example-custom-builders.json` — deliberately sparse: no `gross_margin` and no
  `equipment`, so it exercises the 35% existing-builder default and the Lennox
  custom default.

**Examples are not loaded in production.** The engine reads `profiles/` only.
To run against the examples for testing:

```bash
python3 ryan-os/cli/turnover.py intake.json --profiles ryan-os/builder-library/examples
```

## Maintenance

Review profiles at least annually, and any time a governed default turns out
wrong on a job. Set `last_reviewed` when you do.

The signal to watch: a builder whose turnovers keep showing MEDIUM rows sourced
`Ryan OS default` has an incomplete profile. Fill in the real values and those
rows become HIGH.
