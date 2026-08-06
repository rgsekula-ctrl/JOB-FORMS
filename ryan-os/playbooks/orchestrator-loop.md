# Playbook: The Orchestrator Loop

The Operations Orchestrator is the operational interface to Ryan OS. Phase 1
delivers one component of it — the Bid Turnover Decision Engine. This document
describes the whole loop, marks what is built, and defines the interfaces the
remaining pieces will plug into.

---

## The loop

```
Outlook
   |
   v
[1] Detect new work            .................. Phase 2
   |
   v
[2] Classify the email         .................. BUILT (playbook, manual trigger)
   |
   v
[3] Consult the Builder Library .................. BUILT
   |
   v
[4] Apply governed defaults    .................. BUILT
   |
   v
[5] Draft / send the turnover  .................. BUILT (draft + send by agent)
   |
   v
[6] Track Manual J progress    .................. Phase 2
   |
   v
[7] Track bid progress         .................. Phase 2
   |
   v
[8] Feed the dashboard         .................. Phase 3
   |
   v
[9] Escalate only when needed  .................. BUILT
```

---

## What Phase 1 delivers

Steps 2 through 5 and step 9, executed by an agent session with Outlook access.

The agent is the runtime. The engine is the decision-maker. That split is
deliberate: the parts that must be identical across Claude, Codex, and ChatGPT
live in deterministic Python, and only the parts that genuinely need judgment —
reading an email, reading a plan set — live in the model.

**Steps 1, 6, 7, and 8 still depend on a human starting a session.** That is the
honest state of Phase 1: the decision-making is automated, the triggering is
not.

---

## Running Phase 1

Ryan or an agent opens a session and says:

> Check Outlook for new bid requests and run the turnover playbook.

The agent then, per inbox pass:

1. Lists unread mail.
2. Classifies each per `email-classification.md`.
3. For each `BID_REQUEST`, runs `bid-turnover.md` end to end.
4. Batches everything `UNCERTAIN` into one summary for Ryan.
5. Reports: turnovers sent, escalations held, items needing Ryan.

A reasonable cadence is twice a day — first thing and mid-afternoon. Bid
requests are not usually minute-sensitive; they are *hour*-sensitive, and twice
daily keeps the worst case under half a day without anyone babysitting an inbox.

---

## Phase 2 — automatic detection and tracking

### Step 1: detect new work

Needs a durable Outlook connection — Graph API subscription, an IMAP poller, or
a scheduled agent session. **Requires a Class C architecture decision** (a new
service, credentials, a persistent runtime), so it is out of Phase 1 scope by
design.

Interim: a scheduled session on a cron trigger, running the loop above. Most of
the benefit, none of the new infrastructure.

### Steps 6 and 7: track Manual J and bid progress

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
Class A data pattern rather than an architecture change. **Not implemented in
Phase 1** — it needs one decision from Ryan first: whether job state belongs in
git (auditable, diffable, but noisy commits) or in a database (cleaner, but new
infrastructure). That is a Class C call.

### Step 8: the dashboard

Once job state exists, the existing Flask app is the natural host — it already
serves the forms the estimating team uses. A `/dashboard` route reading
`ryan-os/jobs/*.json` would show: open turnovers, waiting on Manual J, waiting
on bid, escalations held, and aging.

Deliberately deferred: a dashboard over data that is not being captured yet
would be a screen full of zeros.

---

## Where operational knowledge still lives in Ryan's head

The point of the sprint was to find these. Phase 1 closed the first four:

| Knowledge | Status |
|---|---|
| Which equipment for which builder type | **Closed** — governed defaults + Builder Library |
| What margin to use | **Closed** — governed defaults + Builder Library |
| How many systems | **Closed** — the four-priority decision order |
| What options always get priced | **Closed** — the always-include list |
| Which builders are which type | **Open** — the Builder Library is empty. Highest-value next task. |
| Real contracted margins per builder | **Open** — same. |
| Jurisdiction and permit handling per builder | **Open** — same. |
| When a request is worth Ryan's attention | **Closed** — the four hard stops |
| Whether a job is stuck | **Open** — needs Phase 2 tracking |

**The single highest-value next action is populating the Builder Library with
real profiles for active builders.** It is a Class A data task, it needs no code
and no approval, and every profile added converts MEDIUM assumptions to HIGH —
which is literally the system getting faster and safer at the same time.
