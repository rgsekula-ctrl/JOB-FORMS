# Ryan OS Decision Log

Architecture and governance decisions, newest last. Every Class B or Class C
change (see `GOVERNANCE.md`) gets an entry here.

Format: what was decided, why, what it supersedes, and what it costs.

---

## ADR-001 — Ryan OS lives in the JOB-FORMS repository

**Date:** 2026-08-06 · **Status:** Implemented, pending Ryan's confirmation

**Decision.** The Operations Orchestrator ships as an additive `ryan-os/`
directory inside the existing `JOB-FORMS` repository rather than a new
repository.

**Reasoning.** JOB-FORMS already holds the operational tooling this connects to
— the Flask forms app, the bid info form, the HVAC bid PDF generator. The
turnover engine feeds those forms; splitting them across repositories would mean
two clones, two branches, and two review paths for one workflow. Nothing under
`ryan-os/` touches existing files except one additive Flask route and one
sidebar link, so the change carries no risk to the forms app.

**Alternatives considered.**
- *A separate `ryan-os` repository.* Cleaner conceptual boundary, and it would
  let Ryan OS version independently. Rejected for now: coordination cost is real
  and immediate, while the boundary benefit is speculative.
- *A private Gist / Drive folder of prompts.* Fastest to start, no version
  control, no tests, no governance. This is the status quo the project exists to
  replace.

**Tradeoffs.** The forms app and Ryan OS are now coupled at the repository
level. If Ryan OS grows to include Outlook connectors and a dashboard service,
it will likely outgrow this home and want extraction — which is a
straightforward `git filter-repo` later, not a trap.

**Critique.** The honest weakness: "additive directory in an existing repo" is
the choice that requires the least thought, and I should not mistake low
friction for correctness. If Ryan already has a Ryan OS repository elsewhere
that I could not see from this session, this is the wrong home and the tree
should be moved there wholesale — the contents are portable, only the paths in
the README and the Flask import change. Flagged for Ryan's confirmation.

---

## ADR-002 — Margin defaults restructured around builder relationship

**Date:** 2026-08-06 · **Status:** Implemented per Ryan's specification

**Decision.** Gross margin defaults are now:

| Case | Default |
|---|---|
| Existing builder | 35% (unless the Builder Profile says otherwise) |
| New builder | 30% |
| Homeowner / one-time direct | 35% |

**Supersedes.** The `wcs-bid-request` skill's rule of *34% custom homes / 18%
production homes*.

**Reasoning (as specified by Ryan).** The old rule keyed margin to *project
type*. The new rule keys it to *relationship*, and pushes project-type variation
into the Builder Profile where it belongs. A production builder's real
contracted margin is a fact about that builder, not about production work in
general — so it lives in `gross_margin` on their profile and overrides the
default at HIGH confidence.

**Tradeoffs.** Until the Builder Library is populated, an existing production
builder with no profile will default to 35% rather than the 18% the old skill
used. That is a large gap on a production job.

Mitigations in place: (1) the 35% fallback renders with an explicit note telling
whoever touches the job to record the real number in the profile; (2) it is a
MEDIUM-confidence row in the table, visibly a default rather than a fact; (3)
Ryan and Veston are both on every turnover email and will catch it.

**Critique.** This mitigation leans on humans reading the email — which is
exactly the kind of dependency this project is trying to remove. The durable fix
is populating Builder Profiles for the active production builders, which is a
Class A data task and the highest-value thing to do next. Until then, ADR-002
trades a known-wrong-but-visible number for a delay, which is the right trade
under the speed principle but should not be mistaken for a solved problem.

---

## ADR-003 — The engine always renders a complete email

**Date:** 2026-08-06 · **Status:** Implemented

**Decision.** There is no input that causes the engine to refuse. Hard
escalations produce a full draft, marked HOLD.

**Reasoning.** The failure mode this system exists to prevent is *work not
starting*. An engine that returns "cannot proceed, need more info" recreates
that failure in software. Rendering a complete draft means the worst case is
Ryan reading an email and pressing send — seconds — rather than Ryan
reconstructing context from scratch.

**Tradeoff.** A held draft is a loaded gun: someone could send it without
reading the HOLD banner. Mitigated with a `HOLD - RYAN REVIEW - ` subject
prefix, a banner as the first line of the body, and CLI exit code 2 so
automation cannot mistake it for a clean run.

**Critique.** Three layers of warning is a lot of belt-and-braces for a risk
that is really about human attention, and none of it helps if a future
automation sends on exit code 2 anyway. The real control is that automation must
branch on `outcome`, not on the presence of email text. That is stated in the
playbook, but it is a convention rather than something the code can enforce from
inside a rendered string.

---

## ADR-004 — Escalation is a closed list, everything else flags

**Date:** 2026-08-06 · **Status:** Implemented

**Decision.** Four hard stops, enumerated in `ESCALATION_POLICY.md`. Anything
not on that list flags inside the email and sends.

**Reasoning.** An open-ended "escalate when unsure" rule is how operational
knowledge stays in Ryan's head — every agent picks a different bar, and the
cautious ones interrupt constantly. A closed list makes agent behavior
predictable and makes the bar itself reviewable.

**Tradeoff.** A closed list will eventually miss a case that should have
stopped. Accepted deliberately: the cost of one bad turnover email is a
correction; the cost of a permanently hesitant system is the problem this sprint
was called to fix.

**Critique.** "Track the misses and add to the list" is the stated maintenance
plan, and it depends entirely on someone actually noticing and logging misses.
There is no mechanism in the system that captures them — no feedback loop from
"the bid went out wrong" back to this file. That is a genuine gap, and the
Phase 2 dashboard is the natural place to close it.
