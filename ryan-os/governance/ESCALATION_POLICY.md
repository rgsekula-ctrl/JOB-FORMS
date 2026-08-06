# Escalation Policy

**Ryan is interrupted only when meaningful business judgment is required.**

Everything else is a flag inside the email, not a stop. This document is the
closed list. If a situation is not on it, it is not a reason to hold work.

---

## The three outcomes

| Outcome | Meaning | What the agent does | Exit code |
|---|---|---|---|
| `PROCEED` | Every assumption is HIGH or MEDIUM | Send the email | 0 |
| `PROCEED_WITH_FLAG` | Open items exist and are listed under Known Unknowns | **Send the email** | 0 |
| `ESCALATE_TO_RYAN` | A hard stop was hit | Draft it, hold it, notify Ryan | 2 |

`PROCEED_WITH_FLAG` is the normal state for most real jobs. It means send.
An agent that treats a flag as a stop has misread this policy.

---

## Hard stops (the complete list)

Four conditions, each requiring a decision only Ryan can make.

### 1. `margin_approval_required`

The Builder Profile sets `requires_ryan_margin_approval: true`.

*Why it stops:* margin is the one number the system will not guess when Ryan has
explicitly reserved it. The margin field renders as `HOLD - Ryan approval
required` rather than blank, so nobody prices against a silent zero.

### 2. `builder_flagged`

Profile `status` is `flagged` — do-not-bid, credit hold, open pricing dispute.

*Why it stops:* whether to work for a builder at all is a business relationship
decision. The flag reason is surfaced verbatim so Ryan can decide in one glance.

### 3. `out_of_governed_scope`

Keywords or a declared project type put the request outside residential new
construction: commercial, tenant finish, multifamily, geothermal, hydronic or
radiant, boiler, chiller, VRF, or a replacement/retrofit with unknown existing
conditions.

*Why it stops:* the governed defaults were written for residential new
construction. Outside that envelope, a 35% margin and a Lennox EL19KPV are not
safe assumptions — they are noise, and the confidence table would be lying.

*Known cost:* keyword matching over-triggers. A builder who writes "we're
replacing the plans" gets caught. Over-triggering is the intended error
direction — a false escalation costs one message, a wrong commercial bid costs
real money. Track false positives and tune the keyword list through Class B
governance.

### 4. `instruction_conflicts_with_profile`

A written builder instruction materially contradicts the Builder Profile on
equipment **brand** or on margin.

*Why it stops:* the profile represents a standing agreement. A superintendent
overriding it in a one-line email may be authorized, or may not be — and the
answer is a relationship question, not a technical one.

*Deliberately brand-level.* "Carrier 16 SEER" against a profile saying "Carrier
15.2 SEER2" is a spec detail the estimator settles. "Trane" against "Carrier" is
Ryan's call. Margin conflicts trigger at any difference above half a point.

---

## Never a hard stop

These flag and send. Each one is a case where waiting would cost more than
proceeding.

| Situation | What happens instead |
|---|---|
| **No plans attached** | Turnover sends with plans listed as missing and requested. The team starts what it can. |
| **Unknown jurisdiction / permit cost** | Standard permit allowance, LOW confidence, listed under Known Unknowns. |
| **Unknown story count or square footage** | One system assumed, LOW confidence, flagged. Manual J will correct it. |
| **New builder, unclassifiable** | Ryan OS custom default (Lennox), LOW confidence, flagged. |
| **Rush deadline** | Subject gets `RUSH - ` and the email goes out *faster*, not slower. |
| **Missing envelope specs** | Governed Manual J defaults apply at MEDIUM. |
| **Builder name spelled oddly** | Domain matching handles it; worst case it reads as a new builder. |

---

## What an agent does on escalation

1. **Still render the full draft.** Never hand Ryan a blank and a question. He
   should be able to read the complete email, make one decision, and send.
2. Subject gets `HOLD - RYAN REVIEW - `; the body gets a HOLD banner.
3. Every escalation reason appears under Known Unknowns prefixed `RYAN REVIEW:`.
4. Notify Ryan with: the builder, the project, the one decision needed, and the
   recommended answer. One message, not a conversation.
5. **Do not send to Veston or estimating3** until Ryan clears it.

The bar for a good escalation: Ryan can resolve it with a single reply.
If it needs a back-and-forth, the agent did not gather enough first.

---

## Judgment calls not on this list

An agent encountering something genuinely novel — a situation that feels wrong
but matches no hard stop — should **send the turnover and flag the concern**
under Known Unknowns, then raise it with Ryan separately.

The email going out is almost never the expensive mistake. The expensive mistake
is a day of estimating time lost waiting for a question that had a governed
answer all along.
