# Ryan OS Changelog

## 2.0.0 — 2026-08-06

Phase 2. The Orchestrator now presents governed decisions instead of open
questions, captures new organizational knowledge as a by-product of doing the
work, and knows where the authoritative version of things lives.

### Added

**Builder Profile proposals** (`decision-engine/profile_proposal.py`)
- A missing Builder Profile now produces a **ranked recommendation**, never a
  question: New Custom Builder / New Production Builder / Homeowner / Existing
  Builder (profile missing), each with confidence, the reasoning that produced
  the ranking, and recommended equipment, margin, pricing profile, and options.
- Confidence reflects **separation from the runner-up**, not raw score — a 4
  against a 3 is a coin flip and reports LOW.
- Deterministic scoring over personal vs company email domains, first-person
  homeowner language, established-relationship phrasing, production/custom
  signals, and square footage.
- A fully pre-populated profile: slug, aliases (name + acronym + domain),
  contact from the sender address, classification, margin, jurisdiction, dates,
  and provenance notes. Approving requires no typing, only correction.

**Pricing profiles** (`defaults.json`)
- Named profiles — Existing Builder Standard, New Builder Standard, Homeowner /
  Direct — that reference a `gross_margin` key rather than restating the number.

**Builder Profile CLI** (`cli/profile.py`)
- `propose`, `create`, `list`, `show`, `validate`. Overrides for classification,
  margin, equipment, id, and display name. Refuses duplicates (exit 3), and
  validates against the schema before writing.

**Asset Registry** (`asset-registry/`)
- The authoritative directory of operational resources. 30 assets covering
  forms, proposal and bid templates, applications, playbooks, prompts, skills,
  the builder library, and the governed defaults — plus **6 registered gaps**.
- Every asset answers five questions: what it is, where it is, who owns it,
  when to use it, what it replaces.
- `resolve()` never returns a bare miss. It returns `FOUND`, `FOUND_CANDIDATE`,
  `GAP_FLAGGED`, or `NOT_REGISTERED`, each with a required next action.
  Deprecated assets redirect to their successor automatically.
- Validation covers required fields, enums, duplicate ids, gaps missing a
  recommendation, deprecated assets missing a successor, unreachable locations,
  and referential integrity.

**Asset CLI** (`cli/asset.py`)
- `where`, `find`, `show`, `list`, `gaps`, `validate`. `where` exits 0 / 4 / 5
  so automation can branch without parsing text.

**Resource Discovery Rule** (`governance/RESOURCE_DISCOVERY.md`)
- Binding rule: never search for a work-related resource first. On a miss, flag
  the gap and stop — never silently substitute another version.

**Playbook and agent interfaces**
- `playbooks/new-builder-onboarding.md`
- `.claude/skills/asset-registry/SKILL.md`
- `bid-turnover` skill, the portable system prompt, `GOVERNANCE.md`, and the
  turnover playbook all updated for both Phase 2 behaviors.

**Forms app**
- Profile recommendation with a one-click **Create Builder Profile** button on
  the Bid Turnover page; `POST /create-builder-profile`.
- New **Asset Registry** browser at `/asset-registry` with `GET /api/assets`.

**Tests**
- `tests/test_phase2.py` — 49 tests. Total suite is now 105.

### Fixed

- **Asset Registry false authority.** Search originally matched query words
  against asset descriptions, so "truck inventory spreadsheet" returned the HVAC
  Equipment Schedule Template marked `[AUTHORITATIVE]` — the exact
  false-confidence failure the Resource Discovery Rule exists to prevent.
  Matching is now restricted to identity (id, name, declared keywords,
  category); prose can break ties but never qualify a match. Regression test
  added. See `DECISION_LOG.md` ADR-007.

### Decisions

ADR-005 (recommendation not question), ADR-006 (equipment left blank in
generated profiles to avoid default drift), ADR-007 (Asset Registry and the
strict miss behavior) — each with its tradeoffs and self-critique in
`governance/DECISION_LOG.md`.

### Known gaps

- Six registered Asset Registry gaps, `pricing-workbook` the most impactful.
- Nothing forces review of a profile approved under LOW confidence — a
  `confidence_at_creation` review queue is recommended for Phase 3.
- The Resource Discovery Rule is enforced by convention in prompts and skills,
  not by a sandbox.
- Still no automatic Outlook detection, job state tracking, or dashboard.

---

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
