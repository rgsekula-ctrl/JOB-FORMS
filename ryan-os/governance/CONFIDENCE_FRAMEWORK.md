# Confidence Framework

Every assumption Ryan OS surfaces carries a **confidence level** and a
**source**. This is what makes speed safe: the system proceeds on defaults, and
the confidence table makes every one of those defaults visible and attributable.

---

## The three levels

### HIGH — confirmed for this builder, on this project

An authoritative source said so, specifically, about this job.

Qualifying sources: Builder Profile, a written builder instruction, mechanical
plans.

> Equipment · HIGH · Builder Profile

### MEDIUM — a governed default that reliably applies

Not confirmed for this specific project, but Ryan has decided it in advance for
this class of project, or an AI plan read produced it.

Qualifying sources: Ryan OS default, AI plan review.

> System Count · MEDIUM · Ryan OS default (one system per floor)

**MEDIUM is not an open question.** It is the answer, and the system stands
behind it. MEDIUM items do *not* go into Known Unknowns. Treating them as
uncertain would reintroduce exactly the hesitation this system exists to remove.

### LOW — unconfirmed, used to avoid delay

We do not know, and we picked something safe so work could start.

Source is usually `Not confirmed`.

> Permit · LOW · Jurisdiction not confirmed

**Every LOW item is automatically listed under Known Unknowns.** No exceptions,
no agent discretion. That automatic promotion is the mechanism that lets the
engine guess without ever hiding a guess.

---

## Source labels

Fixed strings, so the table reads identically from every agent and every code
path.

| Label | Meaning | Typical confidence |
|---|---|---|
| `Builder Profile` | Ryan OS Builder Library | HIGH |
| `Builder email` | Written in the inbound request | HIGH |
| `Mechanical plans` | Read off the mechanical/HVAC set | HIGH |
| `AI plan review` | Inferred from architectural plans | MEDIUM |
| `Ryan OS default` | Governed default in `defaults.json` | MEDIUM (HIGH for the custom equipment default on a known custom builder) |
| `Not confirmed` | Nothing to go on | LOW |

---

## The one HIGH-from-a-default case

An existing **custom** builder with no equipment recorded gets the Lennox
EL19KPV at **HIGH**, not MEDIUM. That is intentional: Ryan OS governance states
this *is* the standard for custom work, so for a builder already classified
custom, the default is as authoritative as a profile entry would be.

An existing **production** builder with no equipment recorded gets MEDIUM
instead — production packages are builder-specific by nature, so the generic
Carrier default is a reasonable starting point rather than a settled fact.

---

## Reading the table

```
Assumption Confidence
Equipment     HIGH    Builder Profile
Gross Margin  HIGH    Builder Profile
System Count  MEDIUM  Ryan OS default
Permit        LOW     Not confirmed
```

What this tells the estimator in about two seconds:

- Equipment and margin are settled. Price against them.
- The system count is Ryan OS's starting position. The Manual J may change it —
  and the email says so explicitly, every time.
- The permit line is a placeholder. Someone needs to confirm the jurisdiction
  before the bid goes out.

**A table with no LOW rows means the estimator can work the entire job without
asking anyone a question.** That is the target state, and it is exactly what a
complete Builder Profile buys.

---

## Using confidence to improve the system

The confidence table is also a to-do list for the Builder Library.

- A **LOW** row is a gap in intake or in the library. Recurring LOWs on the same
  builder mean that profile needs a field filled in.
- A **MEDIUM** row sourced `Ryan OS default` on a repeat builder means the real
  value should be captured into the profile — every one converted to HIGH is a
  question the estimating team never has to ask again.
- A **HIGH** row that turns out wrong means the profile is stale. Correct it and
  bump `last_reviewed`.

The system gets faster over time by converting MEDIUM to HIGH, one builder at a
time.
