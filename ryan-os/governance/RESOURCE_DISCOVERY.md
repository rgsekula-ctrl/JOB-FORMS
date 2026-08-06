# Resource Discovery Rule

**The Operations Orchestrator must never search for a work-related resource
first. It consults the Ryan OS Asset Registry.**

This is a hard rule, not a preference. It applies to every agent — Claude,
Codex, ChatGPT — and to every kind of resource: forms, templates, workbooks,
applications, folders, servers, Drive locations.

---

## The rule

```
Need a work-related resource
        |
        v
  Ask the Asset Registry
        |
   +----+--------------------------------+
   |                                      |
authoritative version exists         no authoritative version
   |                                      |
   v                                      v
  USE IT                        FLAG THE GAP + recommend
                                adding it to Ryan OS
                                        |
                                        v
                              DO NOT silently choose
                                 another version
```

```bash
python3 ryan-os/cli/asset.py where "<what you need>"
```

Exit codes let automation branch without parsing text:

| Code | Outcome | What it means |
|---|---|---|
| 0 | `FOUND` / `FOUND_CANDIDATE` | Use it |
| 4 | `GAP_FLAGGED` | Registry knows it should exist and has no version. Flag it. |
| 5 | `NOT_REGISTERED` | Registry has never heard of it. Flag it. |

---

## Why the miss cases matter most

Anyone can follow a rule that says "use the registry when it has the answer."
The rule earns its keep on a miss.

An agent that cannot find a pricing workbook in the registry, then searches the
filesystem and opens `Pricing_2024_FINAL_v3.xlsx`, has done something worse than
nothing. It produced a confident answer from an unverified source, and nobody
downstream can tell that happened. The bid goes out priced off a stale
workbook, and the failure is invisible until a job loses money.

**A flagged gap is a five-minute conversation. A silently wrong resource is a
wrong bid.**

So on a miss, the agent must:

1. Stop.
2. Tell Ryan the registry has no authoritative entry.
3. Say what it needed the resource for.
4. Recommend the specific registry entry that should be added.
5. Not proceed with a substitute unless Ryan explicitly approves one.

---

## What counts as "work-related"

Anything that would go into, or come out of, real WCS work: forms, templates,
pricing, plans, job files, proposals, schedules, builder information,
applications, storage locations.

**Not** covered: general knowledge, HVAC engineering references, code lookups,
or anything the agent can reason about without a company-specific file. You do
not need a registry entry to know what ASHRAE 62.2 says.

The test: *if two versions of this could exist and picking the wrong one would
be a problem, it belongs in the registry.*

---

## Never substitute a version silently

If the registry says a resource is a gap, and something that looks like it
exists on disk or in Drive, that is **not** permission to use it. It is
evidence for the recommendation.

The right move:

> The registry has no authoritative pricing workbook. I found
> `Pricing_2024_FINAL_v3.xlsx` in the shared folder but I have not used it —
> I can't tell whether it's current. Should that be registered as the
> authoritative pricing workbook, or is there a newer one?

That message is worth more than a bid, because it converts a recurring
ambiguity into a permanent answer.

---

## Status meanings

| Status | Meaning | Agent behavior |
|---|---|---|
| `authoritative` | The one true version | Use it |
| `candidate` | Exists, not yet blessed | Usable — say you used it, ask Ryan to confirm |
| `deprecated` | Superseded | Do not use for new work; `resolve()` redirects to the successor |
| `gap` | Should exist, no version on file | Flag it, do not substitute |

`gap` entries are in the registry **on purpose**. A gap that is written down is
a known unknown; a gap that is absent is just a hole an agent will improvise
into. This mirrors how the Decision Engine handles LOW-confidence assumptions —
surface them rather than hide them.

---

## Adding an asset

Adding or correcting a registry entry is a **Class A data change** — no
approval ceremony, just do it and validate:

```bash
python3 ryan-os/cli/asset.py validate
```

Every asset must answer the five questions: what is it, where is it, who owns
it, when should it be used, what does it replace. The schema enforces the first
four; `replaces` / `replaced_by` handles the fifth and is how old versions stop
circulating.

Changing the *rule itself* — this document — is a Class C architecture change.

---

## Relationship to the Decision Engine

Together these answer the two questions any agent needs before it can act:

| Question | Answered by |
|---|---|
| **What should I do?** | The Decision Engine — governed defaults, confidence, escalation |
| **Where is the authoritative resource?** | The Asset Registry — this rule |

Neither is sufficient alone. A perfect decision executed against the wrong
template still produces the wrong artifact, and the right template used without
governed decisions still produces an inconsistent one. The pair is the
execution layer for Ryan OS.
