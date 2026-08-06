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

---

## ADR-005 — A missing Builder Profile produces a recommendation, not a question

**Date:** 2026-08-06 · **Status:** Implemented (Phase 2)

**Decision.** When no Builder Profile exists, the Orchestrator presents a ranked
classification with confidence, reasoning, recommended equipment, margin,
pricing profile, and options — plus a fully pre-populated profile Ryan can save
in one action. It never asks "what should we do with this builder?"

**Reasoning.** Phase 1 removed the thinking from *governed* decisions but left
new builders as an open question, which is where most of the remaining human
effort sat. An open question costs Ryan a context switch, a decision, and then
typing. A recommendation costs him a yes. The classification is deterministic
and auditable, so the recommendation is defensible rather than a guess dressed
up as one.

**Alternatives considered.**
- *Ask Ryan to fill in a profile form.* Highest quality data, worst latency —
  and in practice it does not get done, which is why the library was empty.
- *Auto-create a profile silently on first contact.* Zero effort, but it writes
  unreviewed classifications into the authority that governs future jobs. A bad
  profile is worse than none, because it carries HIGH confidence.
- *Recommend but never persist.* Safe and useless — the same question returns on
  the next project.

**Tradeoffs.** Approval is easy enough that a wrong classification could get
waved through, and it then carries HIGH confidence into future jobs. Mitigated
by: the reasoning being visible at the point of approval, LOW-confidence
classifications being labelled as such, `notes` recording that the values are
governed defaults rather than confirmed, and a confirm-after-approval punch list.

**Critique.** Those mitigations all reduce to "we showed Ryan the information."
Fast approval paths get approved fast — that is their purpose, and it is also
their risk. The structural protection is weaker than it looks: nothing forces a
review of a profile created under LOW confidence. A `confidence_at_creation`
field that surfaces such profiles in a periodic review queue would be a real
control rather than a hopeful one. Not built; recommended for Phase 3.

Also worth stating plainly: the classification scorer is keyword matching, not
comprehension. It will misread an unusual email. It is deterministic and its
reasoning is legible, which makes it *reviewable* — not *right*.

---

## ADR-006 — Equipment is left blank in generated profiles

**Date:** 2026-08-06 · **Status:** Implemented (Phase 2)

**Decision.** When a generated Builder Profile's equipment recommendation is
just the governed default, the profile stores an **empty** equipment block with
an explanatory note instead of a copy of the default.

**Reasoning.** A copy is a snapshot. If Ryan later changes the governed custom
default, every profile created before that change would silently keep the old
equipment at HIGH confidence — the drift problem `GOVERNANCE.md` exists to
prevent, reintroduced through the back door. A blank block inherits.

**Tradeoff.** The profile is less self-describing: reading the JSON alone does
not tell you what equipment this builder gets. Mitigated by the note in the
block explaining the inheritance.

**Critique.** This trades explicitness for correctness, and explicitness has
real value when a human is reading a profile to answer a question. A better
long-term answer is an explicit `"equipment": "inherit"` sentinel, or a
`profile show --resolved` mode that prints the effective configuration with
inherited values marked. The empty block is the right call today, but it is a
convention communicated by a note rather than a mechanism enforced by the schema.

---

## ADR-007 — The Asset Registry answers "where", and a miss is never a search

**Date:** 2026-08-06 · **Status:** Implemented (Phase 2)

**Decision.** Ryan OS maintains an Asset Registry as the authoritative directory
of operational resources. Agents consult it before searching anywhere else. On a
miss they flag the gap and stop — they do not go find a substitute.

**Reasoning.** The Decision Engine answers "what should I do?" but an agent that
executes a perfect decision against the wrong template still produces the wrong
artifact. Together the two are the execution layer. The strict miss behavior is
the whole point: an agent that searches on a miss will find *something*, and a
confident answer from an unverified source is worse than no answer because
everyone downstream assumes it was checked.

**Tradeoffs.** Strictness costs availability. An agent will refuse to use a file
that is sitting right there and obviously correct, and that will be annoying.
Accepted: the annoyance is one message; the alternative failure is a bid priced
off a stale workbook, discovered when a job loses money.

Registered `gap` entries mitigate the friction — a gap tells the agent that Ryan
OS already knows about the hole, so it can flag it precisely instead of
rediscovering it.

**Implementation note — a real bug worth recording.** The first version of the
search matched query words against asset *descriptions*. "Truck inventory
spreadsheet" returned the HVAC Equipment Schedule Template marked
`[AUTHORITATIVE]`, because the word "spreadsheet" appeared once in its
description. That is precisely the false-authority failure this rule exists to
prevent, produced by the tool meant to enforce it. Search now matches only on
identity — id, name, declared keywords, category — and prose can break ties but
never qualify a match. There is a regression test.

**Critique.** Three real weaknesses.

1. **Keyword-quality dependence.** Lookups succeed only if whoever added the
   asset anticipated the words people would use. A poorly-keyworded asset is
   invisible, and invisible reads identically to `NOT_REGISTERED` — the agent
   flags a gap for something already registered. Strictness converts a recall
   problem into a false-gap problem; that is the better failure, but it is a
   failure.
2. **Compliance is convention.** Nothing prevents an agent from calling `Glob`
   and using what it finds. The rule lives in prompts and skills, not in a
   sandbox. It holds only as long as agents follow instructions.
3. **Seeded from one repository.** I registered what I could verify here. The
   registry's authority over pricing workbooks, job folders, servers, and Drive
   is currently six `gap` entries — accurate, but it means the registry cannot
   yet answer the questions most likely to be asked of it. Its usefulness is
   entirely front-loaded onto Ryan filling those in.
