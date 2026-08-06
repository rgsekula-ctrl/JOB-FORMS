# Ryan OS Governance

**Scope:** the Operations Orchestrator and everything under `ryan-os/`.
**Owner:** Ryan Sekula.

---

## 1. What "governed" means

A governed value is one that an agent may apply **without asking** — because
Ryan has already decided it, once, in writing. Governance is what converts
Ryan's judgment into throughput: the estimating team gets a defensible answer
in seconds instead of waiting on a text message.

Three properties make a value governed:

1. **It is written down** in a versioned file in this repository.
2. **It has a source of truth** — exactly one file owns it.
3. **Changing it leaves a trail** — a decision-log entry and a failing test.

A value that lives only in a prompt, a chat thread, or someone's memory is
*not* governed. Moving values out of those places and into this directory is
the entire point of the project.

---

## 2. Source-of-truth map

| Value | Owned by | Never duplicate it in |
|---|---|---|
| Margin defaults, equipment defaults, option list, escalation triggers, recipients, pricing profiles | `decision-engine/defaults.json` | prompts, skills, code |
| Per-builder margin, equipment, jurisdiction, exclusions | `builder-library/profiles/*.json` | defaults.json |
| Decision *logic* (order of precedence, scoring) | `decision-engine/engine.py` | prompts |
| Classification scoring for unknown builders | `decision-engine/profile_proposal.py` + `defaults.json → profile_proposal` | prompts |
| Where every operational resource lives | `asset-registry/registry.json` | playbooks, prompts, memory |
| Human-readable contract | `decision-engine/SPEC.md` | — |
| Email layout | `decision-engine/EMAIL_STANDARD.md` + `engine.render_email()` | prompts |

Pricing profiles reference a `gross_margin` key rather than restating the
number — the same no-duplication rule applied inside `defaults.json` itself.

**Prompts and skills must never restate a governed number.** They point at the
engine. This is the single most important rule in this document: the moment a
margin appears in a prompt, the prompt and the engine start drifting, and no
one finds out until a bid goes out wrong.

---

## 3. Change classes

### Class A — Data change (no approval ceremony)

Adding or updating a Builder Profile, correcting a contact, recording a
jurisdiction, adding an alias, **adding or correcting an Asset Registry entry**.

Anyone maintaining Ryan OS may do this. Requirements: validate against the
relevant schema, set `last_reviewed`, run the tests.

```bash
python3 ryan-os/cli/profile.py validate     # builder profiles
python3 ryan-os/cli/asset.py validate       # asset registry
```

### Class B — Governed default change (Ryan approves)

Changing a margin default, an equipment default, the option list, a confidence
rule, or an escalation trigger.

Requires:
1. Ryan's explicit approval.
2. An entry in `DECISION_LOG.md` — what changed, why, what it supersedes.
3. Bump `governed_defaults_version` in `defaults.json`.
4. Update the pinning test in `tests/test_engine.py`.
5. Update `SPEC.md`.

The tests pin the governed numbers **on purpose**. Changing 35% to 32% breaks
the suite. That is not friction to route around — it is the control working.

### Class C — Architecture change (Ryan approves, with a written proposal)

Repository structure, a new component, a change to how agents interact with
Ryan OS, anything that changes the governance model itself.

Requires a written proposal covering: the recommendation, the reasoning,
alternatives considered, tradeoffs, and an honest critique of the proposal's own
weaknesses. Then Ryan decides. Agents do not make Class C changes unilaterally.

---

## 4. Agent conduct

Any agent — Claude, Codex, ChatGPT, or a future one — operating the Orchestrator:

**Must**
- Run the engine rather than reasoning out governed values from memory.
- Attach a confidence level and a source to every assumption it surfaces.
- Send when the outcome is `PROCEED` or `PROCEED_WITH_FLAG`.
- Hold and escalate when the outcome is `ESCALATE_TO_RYAN`.
- Present a governed recommendation wherever one is possible, rather than an
  open-ended question.
- Consult the Asset Registry before searching for any work-related resource.
- Say plainly when it deviated from the engine, and why.

**Must not**
- Invent a margin, an equipment package, or a builder standard.
- Silently drop a required option.
- Delay a turnover to chase information the defaults already cover.
- Restate governed numbers from memory instead of reading `defaults.json`.
- Edit `defaults.json` without going through Class B.
- Ask Ryan to build an answer the system could have recommended.
- Substitute an unregistered resource when the registry reports a gap.

**The tie-breaker.** When speed and completeness conflict, choose speed and flag
the gap. When safety and speed conflict — when proceeding could put a wrong
number in front of a customer — escalate. The escalation list in
`ESCALATION_POLICY.md` is deliberately short and closed: if a situation is not
on it, it is not a reason to stop.

---

## 5. Review cadence

| What | How often | Trigger |
|---|---|---|
| Builder Profiles | Annually, or after any job where a default was wrong | `last_reviewed` older than a year |
| Governed defaults | Quarterly | Ryan's call |
| Escalation triggers | After any escalation that should not have been one, or any send that should have been | Every miss is a data point |

The healthiest signal to watch: **how often `PROCEED_WITH_FLAG` items turn out
to have mattered.** If flagged assumptions keep changing the bid, a default is
wrong. If they never do, the defaults are earning their keep.
