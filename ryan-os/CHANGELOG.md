# Ryan OS Changelog

## 1.0.0 — 2026-08-06

First production version of the Operations Orchestrator: the Bid Turnover
Decision Engine.

### Added

**Decision engine** (`decision-engine/`)
- `defaults.json` — governed defaults as the single source of truth: margins,
  equipment, the always-include option list, escalation triggers, recipients,
  Manual J envelope defaults.
- `engine.py` — deterministic, stdlib-only implementation. Builder matching,
  equipment/margin/system-count/permit decisions, confidence tracking,
  escalation, and plain-text email rendering.
- `SPEC.md` — the human-readable governed contract.
- `EMAIL_STANDARD.md` — email layout with a verified worked example.
- `intake_schema.json` — the structured reading of one inbound request.

**Builder Library** (`builder-library/`)
- Profile JSON schema, a fill-in template, and two example profiles used by the
  test suite. `profiles/` ships empty and is the next thing to populate.

**Governance** (`governance/`)
- `GOVERNANCE.md` — source-of-truth map, three change classes, agent conduct.
- `ESCALATION_POLICY.md` — four hard stops; everything else flags and sends.
- `CONFIDENCE_FRAMEWORK.md` — HIGH/MEDIUM/LOW definitions and source labels.
- `DECISION_LOG.md` — ADR-001 through ADR-004.

**Playbooks** (`playbooks/`)
- `bid-turnover.md` — the eight-step runbook.
- `email-classification.md` — inbox triage and duplicate detection.
- `orchestrator-loop.md` — the full loop, marking what is built vs. Phase 2/3.

**Agent interfaces**
- `.claude/skills/bid-turnover/SKILL.md` — auto-triggering Claude skill.
- `prompts/operations-orchestrator.system.md` — portable system prompt.
- `prompts/bid-turnover.task.md` — portable task prompt.

**Tooling**
- `cli/turnover.py` — CLI with `--new-intake`, `--json`, and exit codes
  (0 = send, 2 = hold).
- Five example intakes covering the happy path, a cold new builder, a rush
  production job, a brand-conflict escalation, and a homeowner direct.
- `tests/test_engine.py` — 56 stdlib tests pinning the governed values.

**Forms app integration**
- `GET /bid-turnover` and `POST /generate-bid-turnover` in `app.py`, plus
  `templates/bid_turnover.html` and links from the home page. The engine import
  is optional, so the forms app still runs if `ryan-os/` is absent.

### Changed

- **Margin defaults restructured** from *34% custom / 18% production* to
  *35% existing builder / 30% new builder / 35% homeowner direct*, with
  builder-specific values moving into the Builder Library. Supersedes the
  `wcs-bid-request` skill for inbound requests. See `DECISION_LOG.md` ADR-002 —
  including the known gap this opens until Builder Profiles are populated.

### Known gaps

- Builder Library is empty; every builder currently reads as new.
- No automatic Outlook detection, job state tracking, or dashboard (Phase 2/3).
- Recipient addresses for Ryan and Veston in `defaults.json` are inferred from
  the company domain and need verification against Outlook before the first
  production send.
