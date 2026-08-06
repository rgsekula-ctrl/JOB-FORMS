# Playbook: The Orchestrator Loop

The Operations Orchestrator is the operational interface to Ryan OS. It is built
from two components: the **Bid Turnover Decision Engine** (what should I do?)
and the **Asset Registry** (where is the authoritative resource?). This document
describes the whole loop, marks what is built, and defines the interfaces the
remaining pieces will plug into.

---

## The loop

```
Outlook
   |
   v
[1] Detect new work             ................. NOT BUILT (needs a persistent runtime)
   |
   v
[2] Classify the email          ................. BUILT (playbook, manual trigger)
   |
   v
[3] Consult the Builder Library ................. BUILT
   |     no profile? -> recommend + one-action create .... BUILT (Phase 2)
   v
[4] Apply governed defaults     ................. BUILT
   |
   v
[5] Resolve authoritative resources ............. BUILT (Phase 2 - Asset Registry)
   |
   v
[6] Draft / send the turnover   ................. BUILT (draft + send by agent)
   |
   v
[7] Track Manual J progress     ................. NOT BUILT
   |
   v
[8] Track bid progress          ................. NOT BUILT
   |
   v
[9] Feed the dashboard          ................. NOT BUILT
   |
   v
[10] Escalate only when needed  ................. BUILT
```

**The two questions the Orchestrator can now answer for any agent:**

| Question | Answered by |
|---|---|
| What should I do? | Decision Engine — governed defaults, confidence, escalation |
| Where is the authoritative resource? | Asset Registry — `asset.py where "..."` |

---

## What is delivered today

Steps 2 through 6 and step 10, executed by an agent session with Outlook access.

The agent is the runtime. The engine is the decision-maker. That split is
deliberate: the parts that must be identical across Claude, Codex, and ChatGPT
live in deterministic Python, and only the parts that genuinely need judgment —
reading an email, reading a plan set — live in the model.

**Steps 1, 7, 8, and 9 still depend on a human starting a session.** That is the
honest state today: the decision-making is automated, the triggering is not.

---

## Running it today

Ryan or an agent opens a session and says:

> Check Outlook for new bid requests and run the turnover playbook.

The agent then, per inbox pass:

1. Lists unread mail.
2. Classifies each per `email-classification.md`.
3. For each `BID_REQUEST`, runs `bid-turnover.md` end to end.
4. For any unknown builder, presents the profile recommendation (never a question).
5. Batches everything `UNCERTAIN` into one summary for Ryan.
6. Reports: turnovers sent, escalations held, profiles created, items needing Ryan.

A reasonable cadence is twice a day — first thing and mid-afternoon. Bid
requests are not usually minute-sensitive; they are *hour*-sensitive, and twice
daily keeps the worst case under half a day without anyone babysitting an inbox.

---

## What is left: detection, tracking, and the dashboard

### Step 1: detect new work

Needs a durable Outlook connection — Graph API subscription, an IMAP poller, or
a scheduled agent session. **Requires a Class C architecture decision** (a new
service, credentials, a persistent runtime), so it has been deliberately left
out until Ryan decides.

Interim: a scheduled session on a cron trigger, running the loop above. Most of
the benefit, none of the new infrastructure.

### Steps 7 and 8: track Manual J and bid progress

The tracking hook already exists in the email standard. Every turnover ends with:

> Please reply all when the Manual J is complete and again when the bid is
> complete.

Those replies are the state transitions. `email-classification.md` already
classifies them as `MANUAL_J_COMPLETE` and `BID_COMPLETE`.

What is missing is somewhere to write the state. Proposed minimum:

```json
{
  "job_id": "2026-08-06-example-custom-lot-7",
  "builder": "Example Custom Builders",
  "project": "Lot 7 Hillside",
  "turnover_sent_at": "2026-08-06T08:20:00",
  "outcome": "PROCEED",
  "open_items": [],
  "manual_j_complete_at": null,
  "bid_complete_at": null,
  "bid_sent_to_builder_at": null
}
```

One JSON file per job under `ryan-os/jobs/` would be enough to start, and is a
Class A data pattern rather than an architecture change. **Not implemented
yet** — it needs one decision from Ryan first: whether job state belongs in git
(auditable, diffable, but noisy commits) or in a database (cleaner, but new
infrastructure). That is a Class C call.

### Step 9: the dashboard

Once job state exists, the existing Flask app is the natural host — it already
serves the forms the estimating team uses. A `/dashboard` route reading
`ryan-os/jobs/*.json` would show: open turnovers, waiting on Manual J, waiting
on bid, escalations held, and aging.

Deliberately deferred: a dashboard over data that is not being captured yet
would be a screen full of zeros.

---

## Where operational knowledge still lives in Ryan's head

The point of the sprint was to find these. Phases 1 and 2 closed most of them:

| Knowledge | Status |
|---|---|
| Which equipment for which builder type | **Closed** — governed defaults + Builder Library |
| What margin to use | **Closed** — governed defaults + Builder Library |
| How many systems | **Closed** — the four-priority decision order |
| What options always get priced | **Closed** — the always-include list |
| How to classify an unknown builder | **Closed (Phase 2)** — ranked recommendation with reasoning |
| How to capture a new builder's settings | **Closed (Phase 2)** — one-action profile creation |
| Which form/template/app to use for a task | **Closed (Phase 2)** — Asset Registry |
| Which builders are which type | **Open** — the Builder Library is still nearly empty. |
| Real contracted margins per builder | **Open** — same. |
| Jurisdiction and permit handling per builder | **Open** — same. |
| Where pricing, job folders, Drive, and the server live | **Open** — six registered Asset Registry gaps. |
| When a request is worth Ryan's attention | **Closed** — the four hard stops |
| Whether a job is stuck | **Open** — needs job-state tracking |

Phase 2 changed the shape of the Builder Library problem. It is no longer a data
entry chore — the library now fills itself as work arrives, one approval per new
builder. The remaining manual task is the **existing** active builders, whose
real contracted margins are still only in Ryan's head.

**The two highest-value next actions:**

1. **Register the six Asset Registry gaps** — pricing workbook, job folder
   template, Drive root, server root, Manual J software, Outlook mailbox. Every
   one is a question agents currently cannot answer. `python3 ryan-os/cli/asset.py gaps`
2. **Add profiles for the active production builders**, where the 35% fallback
   is furthest from their real contracted margin.
