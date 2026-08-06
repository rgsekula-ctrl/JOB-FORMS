---
name: bid-turnover
description: >
  Runs the Ryan OS Bid Turnover Decision Engine to convert an incoming HVAC bid request into the
  internal "LOAD AND BID NEEDED" turnover email for Ryan, Veston, and estimating3. Use whenever a
  new bid request, plan set, or builder inquiry needs to be turned over to the estimating team, or
  when Ryan says "run the turnover", "load and bid email", "turn this over", "bid request came in",
  "check Outlook for bid requests", or forwards/pastes a builder email asking for HVAC pricing.
  Also use to re-run a turnover after new information arrives on a job already sent, and when asked
  what margin, equipment, or system count Ryan OS would assume for a given builder or project.
---

# Ryan OS — Bid Turnover

Convert an inbound bid request into the governed internal Load & Bid turnover
email, fast. Target: estimating is working within minutes.

**Governing principle:** never sacrifice getting work started in pursuit of
perfect information. Safe governed default → use it. Materially affects the
design → flag it. Real business judgment → escalate to Ryan.

## Do not hand-write the email

Run the engine. It reads the governed defaults and the Builder Library so that
Claude, Codex, and ChatGPT all produce the identical answer:

```bash
python3 ryan-os/cli/turnover.py <intake.json>
```

Reasoning out a margin from memory instead of running the engine is the failure
mode this system exists to prevent.

## Steps

1. **Build the intake.** `python3 ryan-os/cli/turnover.py --new-intake > /tmp/intake.json`
   Schema: `ryan-os/decision-engine/intake_schema.json`.

   Fill in only what the email actually says. Always include `from_email` — the
   domain is the strongest Builder Library match. Leave unknowns empty; they
   become governed defaults with honest confidence levels.

   **Only populate `explicit.*` when the builder stated it in writing.** Those
   fields carry HIGH confidence — faking one puts a lie in the confidence table.

2. **Read any plans.** Architectural → `ai_plan_review.system_count` plus a
   one-line reason. Mechanical → `mechanical_plan_system_count` and
   `plans.mechanical: true`.

3. **Run the engine.** `python3 ryan-os/cli/turnover.py /tmp/intake.json`

4. **Branch on `outcome`** (not on whether email text exists — a held draft
   looks identical to a sendable one):

   | Outcome | Action |
   |---|---|
   | `PROCEED` | Send |
   | `PROCEED_WITH_FLAG` | **Send** — open items are already in Known Unknowns |
   | `ESCALATE_TO_RYAN` | Hold. Give Ryan the draft, the one decision, your recommendation |

5. **Send as plain text**, exactly as rendered, to the three recipients on the
   `TO:` line. Do not reformat it.

6. **Request missing attachments in parallel** — a separate short reply to the
   builder, never a reason to hold the turnover.

7. **If the builder has no profile, present the recommendation — never a question.**

   ```bash
   python3 ryan-os/cli/profile.py propose /tmp/intake.json
   ```

   This returns a ranked classification (New Custom / New Production /
   Homeowner / Existing-profile-missing) with confidence, reasoning,
   recommended equipment, margin, pricing profile, and options — plus a fully
   pre-populated profile. Give Ryan the three choices:

   - **Approve for this project only** — the turnover already used these settings.
   - **Create the Builder Profile** — `python3 ryan-os/cli/profile.py create /tmp/intake.json`
   - **Override** — `--classification <key>`, `--margin`, `--equipment`

   Never ask "what should we do with this builder?" The recommendation is the
   answer; Ryan approves or overrides it.

8. **Update the Builder Library** with anything durable. Every MEDIUM converted
   to HIGH is a question never asked again.

## Escalate only for these four

1. Builder Profile requires Ryan's margin approval
2. Builder is flagged in the library
3. Outside residential new construction (commercial, multifamily, geothermal,
   hydronic, VRF, retrofit with unknown existing)
4. A written builder instruction contradicts the profile on equipment brand or
   margin

Missing plans, unknown jurisdiction, unknown story count, an unclassifiable new
builder, and rush deadlines are **not** escalations. They flag and send.

## Reference

| Need | Read |
|---|---|
| Decision rules and precedence | `ryan-os/decision-engine/SPEC.md` |
| Full runbook | `ryan-os/playbooks/bid-turnover.md` |
| Email layout + worked example | `ryan-os/decision-engine/EMAIL_STANDARD.md` |
| Escalation policy | `ryan-os/governance/ESCALATION_POLICY.md` |
| Confidence levels | `ryan-os/governance/CONFIDENCE_FRAMEWORK.md` |
| Adding a builder | `ryan-os/builder-library/README.md` |
| Finding any resource | `ryan-os/governance/RESOURCE_DISCOVERY.md` (or the `asset-registry` skill) |

Changing a governed default is a governance action, not an edit — see
`ryan-os/governance/GOVERNANCE.md`. Use a Builder Profile to handle a
builder-specific value.

## Relationship to `wcs-bid-request`

The older `wcs-bid-request` skill generates the same family of email from Ryan's
dictated notes. **This skill supersedes it for inbound builder requests** —
different margin rules (see DECISION_LOG ADR-002), Builder Library lookup,
confidence tracking, and escalation. Use `wcs-bid-request` only when Ryan is
dictating a job from scratch with no inbound email to process.
