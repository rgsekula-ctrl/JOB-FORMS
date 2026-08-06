# Playbook: Email Classification

**Trigger:** the Orchestrator sees an unread email in Outlook.
**Goal:** route it in seconds, and be conservative about what counts as new work.

Classification is the front door of the Operations Orchestrator. Everything
downstream depends on getting this right, and the expensive error is not
mis-routing a newsletter — it is missing a real bid request or double-processing
one that is already in flight.

---

## Classes

| Class | What it is | Route to |
|---|---|---|
| `BID_REQUEST` | A builder or homeowner asking for HVAC pricing on a project not already in flight | `bid-turnover.md` |
| `BID_UPDATE` | New information on a job already turned over — revised plans, changed scope, added lot | Update the intake, re-run the engine, reply-all on the original thread |
| `MANUAL_J_COMPLETE` | Estimating replying that the load calc is done | Log it, check it against the turnover assumptions |
| `BID_COMPLETE` | Estimating replying that the bid is done | Log it, route to Ryan for review |
| `SCHEDULING` | Install dates, dispatch, service | Not Phase 1 scope. Leave it. |
| `VENDOR` | Supplier quotes, equipment availability, reps | Not Phase 1 scope. Leave it. |
| `NOISE` | Marketing, newsletters, automated notifications | Ignore |
| `UNCERTAIN` | Cannot classify confidently | Leave unread, surface to Ryan in a batch |

---

## Identifying a `BID_REQUEST`

Positive signals — any one is usually enough:

- Plans attached (architectural, mechanical, or a plan set link)
- "Can you price / bid / quote this"
- "New house", "new build", a lot or plan number, a project address
- A known builder domain sending something that is not scheduling
- "What would HVAC run on this"

Negative signals — these are **not** bid requests:

- A reply on a thread already turned over → `BID_UPDATE`
- "When can you get out here" → `SCHEDULING`
- "Your quote is approved" → not Phase 1
- Equipment pricing *from* a supplier → `VENDOR`

### Before classifying as `BID_REQUEST`, check for duplicates

Search sent mail for `LOAD AND BID NEEDED` plus the builder or project. If a
turnover already went out for this project, it is a `BID_UPDATE`.

Duplicate turnovers are worse than late ones: the estimating team starts two
Manual Js, and nobody knows which assumptions are current.

---

## Handling `BID_UPDATE`

1. Pull up the original intake.
2. Update the changed fields.
3. Re-run the engine.
4. **Reply-all on the original turnover thread** — do not start a new one.
5. Lead with what changed:

> Update on this one — builder confirmed two systems and sent the plot plan.
> Revised assumptions below; everything else is unchanged.

Then paste the regenerated email. Same standard, same structure.

---

## Handling `UNCERTAIN`

Do not guess, and do not send a turnover on a maybe.

Leave the email unread and surface it to Ryan in a batch — not one interruption
per ambiguous email. A short list once, with a one-line summary each, is worth
far more than five separate pings.

This is the one place in the Orchestrator where the bias runs toward *not*
acting. A wrong turnover email costs the estimating team real time; an
unclassified email costs one line in a batch summary.

---

## Homeowner vs builder

Set `customer_type: homeowner_direct` when the sender is an individual building
or renovating their own home — not a builder account.

Signals: a personal email domain (gmail, yahoo, me.com), "our new home", "my
house", an architect corresponding on behalf of an owner.

This matters because it drives the 35% homeowner margin and the custom
equipment default. When it is genuinely ambiguous — a builder using a personal
address — treat it as a builder and flag the question under Known Unknowns.

---

## What this playbook does not cover yet

Phase 1 assumes a human or an agent session is looking at Outlook. Automated
polling, threading, and state tracking across sessions are Phase 2 — see
`orchestrator-loop.md`.
