# Bid Turnover Decision Engine — Specification

**Version 1.0.0 · Effective 2026-08-06 · Owner: Ryan Sekula**

This is the governed contract. `defaults.json` is the machine-readable form of
everything below, and `engine.py` is the executable form. If the three ever
disagree, **`defaults.json` wins** and the other two are bugs.

---

## 1. Purpose

Turn a new bid request sitting in Outlook into an internal Load & Bid turnover
email — fast enough that the estimating team is working on the Manual J within
minutes, not hours.

### The governing principle

> The system never sacrifices getting work started in pursuit of perfect
> information. If a safe, governed default exists, use it. If something
> materially affects the design or the proposal, flag it. Only interrupt Ryan
> when real business judgment is required.

Every rule below is downstream of that sentence. When a rule is ambiguous in a
live situation, resolve it in the direction of **starting work sooner**.

---

## 2. Inputs and outputs

**Input:** an intake object (`intake_schema.json`) — the structured reading of
one inbound bid request. The agent that reads Outlook fills it in.

**Output:** a `TurnoverDecision` containing
- resolved assumptions, each with a confidence level and a source,
- the option set to price,
- known unknowns,
- an outcome verdict,
- the rendered plain-text turnover email.

**The engine always produces a complete email.** Even a hard escalation
produces a full, sendable draft — it is just marked HOLD so a human presses
send. There is no input that makes the engine refuse to answer.

---

## 3. Builder resolution

Match the inbound request to a Builder Profile in
`../builder-library/profiles/`, in this order:

1. **Email domain** against profile `aliases`. Most reliable — superintendents
   type the builder name a dozen ways but always send from the same domain.
2. **Exact name** against `display_name`, `builder_id`, or any alias
   (normalized: lowercased, punctuation stripped, and the noise words
   *llc / inc / ltd / co / company / homes / builders / construction / custom*
   removed).
3. **Loose containment**, longest alias first, minimum 4 characters.

No match → the builder is **new**. That is a normal, fully-supported state, not
an error.

Resulting `builder_status`, which drives everything downstream:

| Status | Meaning |
|---|---|
| `existing_production` | Profile found, `builder_type: production` |
| `existing_custom` | Profile found, `builder_type: custom` |
| `existing_semi_custom` | Profile found, `builder_type: semi-custom` |
| `new` | No profile |
| `homeowner_direct` | Intake declares `customer_type: homeowner_direct` |

---

## 4. Equipment decision

Evaluated top to bottom; **first match wins**.

| # | Condition | Equipment | Confidence | Source |
|---|---|---|---|---|
| 1 | Builder stated equipment in writing | As stated | HIGH | Builder email |
| 2 | Builder Profile has a standard configuration | Profile config | HIGH | Builder Profile |
| 3 | Existing **production** builder, no config recorded | Carrier production standard | MEDIUM | Ryan OS default |
| 4 | Existing **custom** / semi-custom builder | Lennox EL19KPV + matching VS air handler | HIGH | Ryan OS default |
| 5 | **Homeowner direct** | Lennox EL19KPV + matching VS air handler | MEDIUM | Ryan OS default |
| 6 | **New** builder, reads production | Carrier production standard | MEDIUM | Ryan OS default |
| 7 | **New** builder, reads custom | Lennox EL19KPV + matching VS air handler | MEDIUM | Ryan OS default |
| 8 | **New** builder, cannot classify | Lennox EL19KPV + matching VS air handler | **LOW** | Ryan OS default |

Row 8 is the one that matters most: an unclassifiable new builder gets the
custom default and a LOW flag. It **never blocks the turnover**.

### New-builder classification (rows 6–8)

Deterministic keyword scoring against the email subject + body, using the
signal lists in `defaults.json → builder_classification`:

- Production signals: *plan name, plan #, elevation, lot, phase, section, spec
  home, production, tract, model home, subdivision, standard plan, repeat plan*
- Custom signals: *custom, one-off, architect, designer, homeowner, custom
  home, estate, unique, semi-custom*
- Square footage: ≥ 3,500 adds a custom point; ≤ 3,000 adds a production point.

Higher score wins. **A tie or a zero-zero score is `uncertain`** → row 8.
Deliberately conservative: we would rather flag than silently guess a builder's
entire equipment program.

---

## 5. Gross margin decision

First match wins.

| # | Condition | Margin | Confidence | Source |
|---|---|---|---|---|
| 1 | Profile sets `requires_ryan_margin_approval` | **HOLD** — escalate | LOW | Builder Profile |
| 2 | Margin directed in the request | As stated | HIGH | Builder email |
| 3 | Profile has `gross_margin` | Profile value | HIGH | Builder Profile |
| 4 | Homeowner / one-time direct | **35%** | MEDIUM | Ryan OS default |
| 5 | New builder | **30%** | MEDIUM | Ryan OS default |
| 6 | Existing builder, no profile value | **35%** | MEDIUM | Ryan OS default |

**Margin is never blank.** Row 1 is the only path that leaves it unset, and it
escalates by definition. Accepts either `28` or `0.28` — both normalize to 28%.

> A production builder under contract routinely runs well below 35%. That real
> number belongs in the Builder Profile (row 3), not in the defaults. Row 6 is
> a *fallback so work can start*, and it carries a note telling whoever touches
> the job to record the real number in the profile afterward.

---

## 6. System count decision

Strict priority order — this is the sequence Ryan specified.

| Priority | Source | Confidence |
|---|---|---|
| 1 | Explicit builder instruction in the email | HIGH |
| 2 | Mechanical / HVAC plans | HIGH |
| 3 | AI recommendation from the architectural plans | MEDIUM |
| 4 | Ryan OS default: **one system per floor** | MEDIUM |
| 4b | Story count unknown → assume 1 story, 1 system | **LOW** |

The engine will read a count out of builder prose as a safety net
(`extract_system_count`), but it only matches unambiguous phrasing — "two
systems", "single system", "needs 3 units". It returns nothing for "Lot 2 in
phase 3", because a false positive here would silently outrank the mechanical
plans.

**Every turnover email carries this line, without exception:**

> System count is a starting assumption. The Manual J may change the final
> design — estimator to flag any change before the bid is finalized.

A builder-specific `system_count_rule` in the profile is surfaced to the
estimator as a standing instruction rather than parsed. Free text is more
useful to a human than a rule the engine would get subtly wrong.

---

## 7. Permit decision

| Condition | Value | Confidence |
|---|---|---|
| Profile has jurisdiction + who pulls the permit | `{jurisdiction} — permit pulled by {who} ({allowance})` | HIGH |
| Jurisdiction given in the request | `{jurisdiction} — include standard permit allowance` | MEDIUM |
| Nothing known | `Include standard permit allowance` | **LOW** |

An unknown jurisdiction is never a blocker. It is the canonical LOW-confidence
line item.

---

## 8. Manual J envelope defaults

Resolution order per field: **request-supplied → profile override → Ryan OS
default.**

| Field | Default | Confidence when defaulted |
|---|---|---|
| House direction | Use plot plan if available; if not, worst-case orientation | MEDIUM |
| Attic insulation | Foam attic (R-25 roofline) | MEDIUM |
| Walls | R-15 batt | MEDIUM |
| Roof type | Shingles | MEDIUM |
| Windows | U-0.30 / SHGC-0.25 | MEDIUM |
| Foundation | Slab on grade | MEDIUM |
| Duct location | Conditioned attic | MEDIUM |

Carried over from the existing WCS bid-request standard. These are low-risk:
the load calc gets re-run when the builder supplies real specs.

---

## 9. Always-include options

Every bid prices all eight unless the Builder Profile explicitly excludes one:

1. Dehumidifier option(s)
2. Decorative grille options
3. Fresh air assumptions
4. Exhaust fan options where applicable
5. Permit assumptions
6. Standard labor
7. Standard burdens
8. Estimator design-concern flag-back

**Excluding an option requires a written reason** in the profile
(`options.exclude_reasons`). The exclusion and its reason are then printed in
the email under Builder Standing Instructions — so a silent omission is
impossible, and anyone reading the email can see both *what* was dropped and
*why*.

---

## 10. Confidence levels

| Level | Means | Typical source |
|---|---|---|
| **HIGH** | Confirmed for *this* builder on *this* project by an authoritative source | Builder Profile, written builder instruction, mechanical plans |
| **MEDIUM** | A governed Ryan OS default, or an AI plan reading, that reliably applies to this class of project but is not confirmed for this one | Ryan OS default, AI plan review |
| **LOW** | Unconfirmed, or a guess used purely to avoid delaying work | Not confirmed |

**Every LOW item is automatically listed under Known Unknowns.** That is the
mechanism that lets the engine move fast without hiding anything: speed comes
from proceeding on defaults, safety comes from every default being visible and
attributed.

A MEDIUM governed default is *not* an open question. It is the answer, and the
system stands behind it.

---

## 11. Escalation

Full policy: `../governance/ESCALATION_POLICY.md`.

**Hard stops** (outcome `ESCALATE_TO_RYAN`, subject prefixed `HOLD - RYAN
REVIEW -`, draft still fully rendered):

1. Builder Profile requires Ryan approval for margin.
2. Builder is `flagged` in the library (do-not-bid, credit hold, dispute).
3. Request is outside governed residential new-construction scope — commercial,
   multifamily, geothermal, hydronic/radiant, VRF, or a replacement/retrofit
   with unknown existing conditions.
4. A written builder instruction materially contradicts the Builder Profile on
   equipment brand or margin.

**Never hard stops** — these flag and send:

- Missing plans or attachments
- Unknown jurisdiction or permit cost
- Unknown story count or square footage
- A new builder that cannot be classified
- A rush deadline (marks the subject `RUSH -` and sends)

Equipment conflict detection is **brand-level on purpose**. "Carrier 16 SEER"
against a profile saying "Carrier 15.2 SEER2" is a spec detail the estimator
resolves. "Trane" against "Carrier" is a business decision that belongs to Ryan.

### Outcomes

| Outcome | Meaning | CLI exit |
|---|---|---|
| `PROCEED` | Everything HIGH or MEDIUM. Send. | 0 |
| `PROCEED_WITH_FLAG` | Open items exist and are listed. **Still send.** | 0 |
| `ESCALATE_TO_RYAN` | Business judgment required. Draft held. | 2 |

`PROCEED_WITH_FLAG` is the expected steady state for most real jobs, and it
means *send the email*.

---

## 12. Email standard

See `EMAIL_STANDARD.md` for the rendered contract and a worked example.

Recipients are fixed in `defaults.json → recipients.to`: Ryan, Veston,
estimating3@wahoocomfortsolutions.com.

Subject: `LOAD AND BID NEEDED: {Builder} & {Project}`, with `RUSH - ` or
`HOLD - RYAN REVIEW - ` prefixed when applicable.

---

## 13. Changing this spec

Governed values live in `defaults.json`. Changing one requires the process in
`../governance/GOVERNANCE.md` and a matching entry in
`../governance/DECISION_LOG.md`. The test suite pins the governed numbers
deliberately: changing a default without going through governance breaks
`python3 ryan-os/tests/test_engine.py`, which is the intended speed bump.
