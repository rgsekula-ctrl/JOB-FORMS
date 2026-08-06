# Task Prompt — Run a Bid Turnover

A single-shot prompt for an agent that has the repository and Outlook access.
Paste it, or point Codex at it.

---

Run the Ryan OS bid turnover for the email below.

**Process** — full runbook in `ryan-os/playbooks/bid-turnover.md`:

1. Build an intake object per `ryan-os/decision-engine/intake_schema.json`.
   Start from `python3 ryan-os/cli/turnover.py --new-intake`.
2. Fill in **only what the email actually says**. Leave unknowns empty — they
   become governed defaults with an honest confidence level, which is correct.
   Only populate `explicit.*` when the builder stated it in writing.
3. If architectural plans are attached, read them and fill
   `ai_plan_review.system_count` with a one-line reason. If mechanical plans are
   attached, read the count into `mechanical_plan_system_count`.
4. Run `python3 ryan-os/cli/turnover.py intake.json`.
5. Branch on `outcome`:
   - `PROCEED` / `PROCEED_WITH_FLAG` → send the email exactly as rendered, as
     plain text, to the three recipients on the `TO:` line.
   - `ESCALATE_TO_RYAN` → do not send. Give Ryan the draft, the one decision
     needed, and your recommendation.
6. If anything is listed under missing attachments, send a separate short reply
   to the builder asking for it. In parallel — never instead of the turnover.
7. Update the Builder Library with anything durable you learned.

**Rules**

- Do not hand-write the email. Run the engine.
- Do not invent a margin, equipment package, or builder standard.
- Do not delay the turnover for information the governed defaults already cover.
- Do not reformat the rendered email.

**Report back**: outcome, what you sent, what you asked the builder for, what
needs Ryan, and any Builder Library updates you made.

---

**Email to process:**

```
[paste the Outlook message here — sender address, subject, body, attachment names]
```
