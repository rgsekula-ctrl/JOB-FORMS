# Ryan OS — Handoff

**Last updated:** 2026-08-06
**Branch:** `claude/bid-turnover-decision-engine-j5sokv` (pushed, clean, no PR opened)
**Status:** Phases 1 and 2 complete and production-ready. Nothing half-finished.

Read this first if you are picking Ryan OS up cold — a new session, a new agent,
or Ryan after a gap. It covers what exists, what needs a decision, and what to
do next.

---

## 30-second verification

```bash
python3 ryan-os/tests/test_engine.py     # 56 tests - decision engine
python3 ryan-os/tests/test_phase2.py     # 49 tests - proposals + asset registry
python3 ryan-os/cli/asset.py validate    # 30 assets, 6 gaps
python3 ryan-os/cli/profile.py validate  # builder profiles
```

All four pass on a bare `python3` with nothing installed. If any fail, something
changed since this was written — start there before building anything.

---

## What Ryan OS does today

It answers the two questions any agent needs before it can act:

| Question | Component | Entry point |
|---|---|---|
| **What should I do?** | Decision Engine | `python3 ryan-os/cli/turnover.py intake.json` |
| **Where is the authoritative resource?** | Asset Registry | `python3 ryan-os/cli/asset.py where "..."` |

Plus, when a builder is unknown:

| | | |
|---|---|---|
| **Who is this builder?** | Profile Proposal | `python3 ryan-os/cli/profile.py propose intake.json` |

Four ways to run all of it — CLI, the Woods Forms App (`python3 app.py`, sidebar:
**Bid Turnover** and **Asset Registry**), the `bid-turnover` / `asset-registry`
Claude skills, and the portable prompts in `prompts/` for Codex or ChatGPT.
**All paths call the same deterministic Python and produce identical output.**
That equivalence is the product; preserve it.

### The three governing principles

1. Never sacrifice getting work started in pursuit of perfect information.
2. Present governed decisions, not open-ended questions.
3. Never search for a resource — ask the registry; flag gaps, never substitute.

Everything in this directory is downstream of those. When a new situation is
ambiguous, resolve it in their direction.

---

## Open decisions — these need Ryan, not an agent

Ordered by how much they block.

### 1. Verify the turnover recipient addresses  ← do this before the first real send

`defaults.json → recipients.to` contains:

```
ryan@wahoocomfortsolutions.com
veston@wahoocomfortsolutions.com
estimating3@wahoocomfortsolutions.com
```

Only `estimating3@` was given to me. **The other two are inferred from the
domain and have never been verified.** Correct them in `defaults.json` — not in
a prompt.

### 2. Confirm Ryan OS belongs in this repository (ADR-001)

Ryan OS ships as an additive `ryan-os/` tree inside `JOB-FORMS`. Nothing existing
was restructured; the only edits to the forms app are an optional import, four
new routes, and two sidebar links.

If a separate Ryan OS repository already exists that I could not see, this is the
wrong home. The contents are portable — only the README paths and the `app.py`
import change. Reasoning and self-critique in `governance/DECISION_LOG.md`.

### 3. Job state tracking: git or a database? (blocks the dashboard)

Manual J and bid completion replies are already classified
(`playbooks/email-classification.md`) but nothing writes the state down. The
proposed shape is one JSON file per job under `ryan-os/jobs/`.

The open question is where it lives: **git** (auditable, diffable, but noisy
commits) or a **database** (cleaner, but new infrastructure). This is a Class C
call. The dashboard is deliberately not built until state is being captured — a
dashboard over uncollected data is a screen of zeros.

### 4. Automatic Outlook detection

Needs a persistent runtime and credentials — Class C. The interim that captures
most of the value with no new infrastructure: a scheduled session running the
loop in `playbooks/orchestrator-loop.md`, twice a day.

### 5. Two small duplicate-version calls

- `Grille_Order_Portable.html` duplicates the in-app grille form. Registered as
  `candidate`, not silently preferred. Declare one authoritative or scope the
  portable one to offline use.
- `templates/design_walk_backup.html` and `templates/linear_grille_order.html`
  are orphans — no route points at them. Delete or wire up.

---

## Highest-value next actions

Both are **Class A data changes**: no code, no approval, just do them.

### 1. Close the six Asset Registry gaps

```bash
python3 ryan-os/cli/asset.py gaps
```

`pricing-workbook` · `job-folder-template` · `drive-root` · `server-root` ·
`manual-j-software` · `outlook-mailbox`

Each is a question agents currently **cannot** answer — by design they flag it
rather than guess. `pricing-workbook` is the most impactful: until estimating's
pricing source is registered, any agent needing a cost is guessing or asking.

Edit `asset-registry/registry.json`, then `asset.py validate`.

### 2. Add profiles for the active production builders

The library now fills itself as new work arrives — one approval per new builder.
What it cannot learn on its own is the **existing** builders' real contracted
margins. A production builder with no profile currently falls back to 35%, which
is far from a typical contracted production margin. That gap is visible (MEDIUM
confidence, with a note) but it depends on a human reading the email.

```bash
python3 ryan-os/cli/profile.py list
cp ryan-os/builder-library/_TEMPLATE.builder.json \
   ryan-os/builder-library/profiles/<slug>.json
```

Even a stub with `aliases` and `builder_type` is worth committing. Always include
the bare email domain in `aliases` — it is the strongest match signal.

---

## Known weaknesses — stated plainly

These are real. Do not rediscover them; do not paper over them.

**Fast approval paths get approved fast.** A Builder Profile created under LOW
confidence carries HIGH confidence forward into every future job. The mitigations
(visible reasoning, labelled confidence, a confirm punch list) all reduce to "we
showed Ryan the information." A `confidence_at_creation` field feeding a review
queue would be an actual control. Recommended, not built. — ADR-005

**The Resource Discovery Rule is convention, not enforcement.** It lives in
prompts and skills. Nothing stops an agent from globbing the filesystem and using
what it finds. — ADR-007

**Registry lookups depend on good keywords.** Search matches identity only
(id, name, keywords, category), never description prose — that strictness was
added after a real bug where "truck inventory spreadsheet" returned the HVAC
Equipment Schedule Template marked AUTHORITATIVE. The tradeoff: a
poorly-keyworded asset is invisible, and invisible reads identically to "not
registered." Better failure direction, still a failure. When adding an asset,
**keywords is the most important field** — include the wrong-but-common names.

**Builder classification is keyword matching, not comprehension.** It is
deterministic and its reasoning is legible, which makes it *reviewable* — not
*right*. It will misread an unusual email.

**The escalation list is closed and will eventually miss a case.** Accepted
deliberately. But nothing captures misses — there is no feedback loop from "that
bid went out wrong" back to the policy. — ADR-004

---

## Rules for whoever works on this next

- **Never restate a governed number in a prompt, skill, or code.** Point at
  `defaults.json`. The moment a margin appears in a prompt, it starts drifting
  from the engine and nobody finds out until a bid is wrong.
- **Run the engine; do not reason out governed values from memory.**
- **Builder-specific value?** Builder Profile — not `defaults.json`.
- **Changing a governed default** is Class B: Ryan approves, log an ADR, bump
  `governed_defaults_version`, update the pinning test. The tests pin those
  numbers on purpose — a failure there is the control working, not an obstacle.
- **Keep the four execution paths equivalent.** New decision logic goes in the
  engine, never in one interface.
- **Layering:** `profile_proposal.py` imports `engine`, never the reverse. Keep
  the engine dependency-free and unaware of proposals.
- **Stdlib only** in `ryan-os/`. It has to run under Codex, Claude, a cron job,
  the Flask app, or a bare `python3` with no install step.

Full process: `governance/GOVERNANCE.md`. Decisions and their self-critiques:
`governance/DECISION_LOG.md` (ADR-001 … ADR-007).

---

## Map

| I want to… | Go to |
|---|---|
| Understand the whole thing | `README.md` |
| See the decision rules | `decision-engine/SPEC.md` |
| Run a turnover | `playbooks/bid-turnover.md` |
| Handle a new builder | `playbooks/new-builder-onboarding.md` |
| Know what is / isn't built | `playbooks/orchestrator-loop.md` |
| Know when to interrupt Ryan | `governance/ESCALATION_POLICY.md` |
| Find a resource | `governance/RESOURCE_DISCOVERY.md` |
| Add a builder | `builder-library/README.md` |
| Add an asset | `asset-registry/README.md` |
| See what changed and why | `CHANGELOG.md`, `governance/DECISION_LOG.md` |

---

## One thing worth keeping in view

The system is only as good as the Builder Library and the Asset Registry. The
engine is finished; the data is not. Every builder profile added and every
registry gap closed converts a MEDIUM assumption into a HIGH one — which is the
system getting **faster and safer at the same time**, the only improvement here
that does not trade one against the other.
