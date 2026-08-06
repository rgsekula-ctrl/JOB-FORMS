# Playbook: New Builder Onboarding

**Trigger:** a bid request arrives from a builder with no Builder Profile.
**Goal:** capture the organizational knowledge in one approval, without slowing
the turnover down.
**Owner:** Operations Orchestrator.

---

## The principle

A missing Builder Profile is **not a blocker and not a question.** The turnover
still goes out on governed defaults. What changes is that Ryan gets a
recommendation he can approve in one move — and once he does, that builder is
never an open question again.

> Present governed decisions, not open-ended questions. Ryan should approve or
> override decisions rather than build them.

---

## The flow

```
Unknown builder
      |
      v
Turnover sends on governed defaults      <- speed is never traded away
      |
      v
Proposal presented alongside it
      |
      +---> Approve for this project only  -> nothing saved
      +---> Create Builder Profile         -> next job is automatic
      +---> Override                       -> corrected, then saved
```

The turnover and the proposal happen together. The proposal never delays the
email.

## Run it

```bash
python3 ryan-os/cli/profile.py propose intake.json
```

Or use the **Bid Turnover** page in the Woods Forms App — the ranked candidates
and a **Create Builder Profile** button appear under the generated email.

---

## What the recommendation contains

A ranked set of four classifications, each carrying its own recommended terms:

| Classification | Equipment | Margin | Pricing profile |
|---|---|---|---|
| New Custom Builder | Lennox EL19KPV + matching VS air handler | 30% | New Builder Standard |
| New Production Builder | Carrier production standard | 30% | New Builder Standard |
| Homeowner | Lennox EL19KPV + matching VS air handler | 35% | Homeowner / Direct |
| Existing Builder (profile missing) | follows the production/custom read | 35% | Existing Builder Standard |

Plus, for each: a confidence level and **the reasoning that produced it** —
which signals fired and which counted against.

### How candidates are ranked

Deterministic scoring over the request:

- **Personal email domain** (gmail, me.com, …) → homeowner; also counts
  *against* the builder classifications.
- **Company domain** → the three builder classifications.
- **First-person language** ("our new home", "my house") → homeowner.
- **Established-relationship language** ("another one for you", "same as last
  time") → existing builder with a missing profile.
- **Production signals** (plan number, elevation, lot, phase, subdivision) and
  **square footage** thresholds → production vs custom.

Confidence reflects **separation from the runner-up**, not raw score. A
candidate scoring 4 against a 3 is a coin flip and reports LOW; 4 against 0
reports HIGH. That is why a request with no signals still yields a
recommendation — just an honestly LOW-confidence one.

---

## What gets pre-populated

The goal is that approving requires **no typing**, only correction.

| Field | Source |
|---|---|
| `builder_id` | Slug from the name, deduped against existing profiles |
| `display_name` | As written in the email |
| `aliases` | Name + generated acronym + email domain |
| `contacts` | Sender address; name derived from the local part |
| `builder_type` | The chosen classification |
| `gross_margin` | The classification's pricing profile |
| `jurisdiction` | Carried from the request when stated |
| `manual_j_overrides` | Any envelope specs the builder supplied |
| `first_job_date`, `last_reviewed` | The request date |
| `notes` | Provenance: which recommendation, what confidence, what is unconfirmed |

### Equipment is left blank on purpose

When the recommendation is just the governed default, the profile stores an
**empty** equipment block with a note, rather than a copy of the default.

Freezing a copy into every profile would mean that changing the governed
default silently fails to reach any builder created before the change — the
classic drift problem. A blank block inherits. Fill it in only when a builder's
package genuinely differs.

---

## Confirm-after-approval items

The proposal lists what it inferred rather than knew:

- A contact name derived from an email address ("Mike" from `mike@…`)
- An unknown jurisdiction, which keeps permits at LOW confidence
- A classification below HIGH confidence

None of these block creating the profile. They are a short punch list to fix
when convenient — and each one fixed converts a MEDIUM assumption to HIGH.

---

## Overriding

```bash
python3 ryan-os/cli/profile.py create intake.json \
  --classification new_production \
  --margin 32 \
  --equipment "Carrier 15.2 SEER2 single-speed heat pump"
```

`--dry-run` prints the profile without writing it. `--force` overwrites.
The CLI refuses to create a duplicate (exit 3) and validates against the schema
before writing, so a malformed profile never reaches the library.

---

## After creating

Verify the loop actually closed:

```bash
python3 ryan-os/cli/profile.py list
python3 ryan-os/cli/turnover.py intake.json      # margin should now read HIGH / Builder Profile
```

The next request from that builder — even with the name typed differently, as
long as the domain matches — resolves from the profile automatically.

---

## When *not* to create a profile

- **A one-time homeowner.** Approve for this project only. A profile for
  someone who will never send another request is clutter that makes the library
  worse at its job.
- **An unclear referral** where you cannot tell who the customer actually is.
  Run the project on defaults, create the profile once the relationship is real.
- **A builder who is already in the library under another name.** Add an alias
  to the existing profile instead — `python3 ryan-os/cli/profile.py show <id>`
  to check first. Two profiles for one builder is the worst outcome, because
  which one wins then depends on how someone typed the name that day.
