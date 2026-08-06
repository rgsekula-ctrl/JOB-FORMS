# Playbook: Bid Turnover

**Trigger:** a new bid request arrives in Outlook.
**Goal:** estimating is working on the Manual J within minutes.
**Owner:** Operations Orchestrator (any agent).

This is the runbook. Follow it exactly — the value of Ryan OS is that Claude,
Codex, and ChatGPT all execute the same eight steps and produce the same email.

---

## Step 0 — Confirm this is a bid request

Run the classification rules in `email-classification.md`. If it is not a
`BID_REQUEST`, stop and follow that playbook instead.

## Step 1 — Read the email into an intake object

Start from the blank template:

```bash
python3 ryan-os/cli/turnover.py --new-intake > /tmp/intake.json
```

Fill in **only what the email actually says**. Schema:
`ryan-os/decision-engine/intake_schema.json`.

Field discipline, in priority order:

| Field | Why it matters |
|---|---|
| `from_email` | The domain is the strongest Builder Library match signal. Always include it. |
| `builder_name` | As written in the email, not cleaned up. |
| `project` | Address, lot, or project name. Goes in the subject line. |
| `stories` | Drives the one-system-per-floor default. |
| `conditioned_sqft` | Also a production-vs-custom signal for new builders. |
| `attachments` / `plans` | Drives the missing-attachment flags. |
| `email_body` | Paste it. The engine scans for rush language, scope keywords, and system counts. |
| `explicit.*` | **Only** when the builder stated it in writing. These carry HIGH confidence. |

**Do not invent values.** An empty field becomes a governed default with an
honest confidence level, which is correct. A guessed field becomes a HIGH
confidence assertion that is a lie. This is the single most damaging mistake an
agent can make in this workflow.

### If architectural plans are attached

Read them and fill `ai_plan_review.system_count` plus a one-line `notes`
explaining the reasoning (e.g. "1,540 sqft up over 2,360 down, hard separation
at the stair"). This is Priority 3 and beats the one-per-floor default. The
notes render into the email so the estimator can sanity-check you.

### If mechanical plans are attached

Read the system count off the schedule into `mechanical_plan_system_count` and
set `plans.mechanical: true`. This is Priority 2 and beats your plan reading.

## Step 2 — Run the engine

```bash
python3 ryan-os/cli/turnover.py /tmp/intake.json
```

Never hand-write the email. Never reason out a margin from memory. The engine
reads `defaults.json` and the Builder Library so that every agent produces the
identical answer.

## Step 3 — Branch on the outcome

Branch on the `outcome` field, not on whether email text exists — a held draft
looks exactly like a sendable one.

| Outcome | Action |
|---|---|
| `PROCEED` | Send. |
| `PROCEED_WITH_FLAG` | **Send.** Open items are already listed under Known Unknowns. |
| `ESCALATE_TO_RYAN` | Do not send. Go to Step 6. |

The CLI exits 0 for the first two and 2 for the third.

## Step 4 — Send the internal turnover email

Recipients come from the rendered `TO:` line — Ryan, Veston, and
estimating3@wahoocomfortsolutions.com, always all three.

Paste the body **as plain text**. Do not reformat it, do not add markdown, do
not "improve" the wording. The layout is the standard; consistency is what makes
it fast to read.

Attach whatever the builder sent.

## Step 5 — Request anything missing, in parallel

If `missing_attachments` is non-empty, send a **separate** short reply to the
builder asking for it. Do not hold the turnover for this — the two go out
together, which is the entire point.

> Thanks — we're starting the load calc now. Can you send over the
> architectural plans and the plot plan when you get a chance so we can
> finalize the design?

## Step 6 — Escalations only

Do not send to Veston or estimating3. Message Ryan with exactly four things:

1. Builder and project
2. The one decision needed
3. The recommended answer
4. That the full draft is ready to send on his word

The bar: Ryan resolves it in a single reply. If it would take a
back-and-forth, gather more first.

## Step 7 — Update the Builder Library

This is what stops the same question from being asked twice, and it is the step
most likely to get skipped.

| What happened | Do this |
|---|---|
| New builder | Create a profile from `_TEMPLATE.builder.json`. Even a stub with `aliases` and `builder_type` is worth it. |
| A MEDIUM default that you now know the real value for | Record it in the profile. Every MEDIUM converted to HIGH is a question never asked again. |
| A HIGH assumption turned out wrong | Correct the profile, bump `last_reviewed`. |
| Ryan resolved an escalation | Encode the answer so it does not escalate next time. |

Validate against the schema and run `python3 ryan-os/tests/test_engine.py`.

## Step 8 — Track it

Log the turnover for the operations dashboard: builder, project, outcome,
timestamp, open items, and whether the Manual J and bid have come back. Phase 1
does this manually; see `orchestrator-loop.md` for where this is headed.

---

## Worked timing

The whole loop should be **under five minutes** for a known builder with plans
attached, and under ten for a cold new builder where you are reading plans.

If a turnover is taking longer than that, something is wrong with the process,
not with the request. The most common cause: an agent trying to resolve an open
question that the governed defaults already answer. Send it and flag it.

## Common mistakes

| Mistake | Why it is wrong |
|---|---|
| Waiting for plans before sending | Missing attachments flag and send. The team starts what it can. |
| Filling `explicit.equipment` with the *default* you expect | That fakes a HIGH builder instruction and defeats the confidence table. |
| Rewriting the email to sound better | The layout is the standard. Consistency beats polish. |
| Treating `PROCEED_WITH_FLAG` as a stop | It means send. |
| Asking Ryan about a jurisdiction or a story count | Neither is a hard stop. Flag it. |
| Editing `defaults.json` to fit one job | That is a Class B governance change. Use the Builder Profile instead. |
