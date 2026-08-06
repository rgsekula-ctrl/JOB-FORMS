# Ryan OS — Operations Orchestrator

The execution layer for Ryan OS. It answers the two questions any agent needs
before it can act:

| Question | Answered by |
|---|---|
| **What should I do?** | **Decision Engine** — governed defaults, confidence, escalation |
| **Where is the authoritative resource?** | **Asset Registry** — one directory, gaps flagged not filled |

Its first job: turn a new HVAC bid request sitting in Outlook into an internal
Load & Bid turnover email, fast enough that the estimating team is working on
the Manual J within minutes.

---

## The governing principles

> **1.** The system never sacrifices getting work started in pursuit of perfect
> information. If a safe, governed default exists, use it. If something
> materially affects the design or the proposal, flag it. Only interrupt Ryan
> when real business judgment is required.

> **2.** Present governed decisions, not open-ended questions. Ryan approves or
> overrides — he does not build the answer.

> **3.** Never search for a work-related resource. Ask the Asset Registry. If
> there is no authoritative version, flag the gap — never quietly substitute
> another one.

Every rule in this directory is downstream of those three.

---

## Run it

### From the terminal

```bash
python3 ryan-os/cli/turnover.py --new-intake > intake.json   # blank template
# fill in what the builder's email actually says
python3 ryan-os/cli/turnover.py intake.json                  # get the email
```

Try it against the shipped examples:

```bash
python3 ryan-os/cli/turnover.py ryan-os/cli/examples/01-known-custom-builder.json \
  --profiles ryan-os/builder-library/examples
```

Exit code 0 means send. Exit code 2 means hold for Ryan.

**Unknown builder?** You get a recommendation, not a question:

```bash
python3 ryan-os/cli/profile.py propose intake.json   # ranked classification + reasoning
python3 ryan-os/cli/profile.py create  intake.json   # approve it - next job is automatic
```

**Need a resource?** Ask the registry before looking anywhere else:

```bash
python3 ryan-os/cli/asset.py where "bid proposal template"
# exit 0 = use it · 4 = known gap, flag it · 5 = not registered, flag it
```

### From the forms app

```bash
python3 app.py
```

Then open **Bid Turnover** in the sidebar. Paste the builder's email, fill in
what it says, get the turnover email with a copy button — plus, for an unknown
builder, the ranked classification and a **Create Builder Profile** button.
**Asset Registry** in the same sidebar browses and resolves resources.

### From an agent

Claude picks up the `bid-turnover` and `asset-registry` skills automatically.
For Codex or ChatGPT, paste `prompts/operations-orchestrator.system.md` as the
system prompt and `prompts/bid-turnover.task.md` as the task.

All four paths run the same engine and produce the identical email. That is the
whole point.

---

## What it decides

| Decision | Rule |
|---|---|
| **Equipment** | Builder Profile → else production = Carrier standard, custom = Lennox EL19KPV + matching VS air handler. New builder that can't be classified gets the custom default, flagged. |
| **Gross margin** | Builder Profile → else existing 35%, new 30%, homeowner 35%. Never blank. |
| **System count** | Builder's written instruction → mechanical plans → AI plan review → one per floor. Always with the "Manual J may change this" caveat. |
| **Options** | Eight always-included items. Excluding one requires a written reason in the Builder Profile. |
| **Permit** | Builder Profile jurisdiction → stated jurisdiction → standard allowance, flagged. |
| **Escalation** | Four hard stops. Everything else flags and sends. |
| **Unknown builder** | Ranked classification (New Custom / New Production / Homeowner / Existing-profile-missing) with reasoning, recommended terms, and a pre-filled profile. Never a question. |

Every assumption comes back with a confidence level and a source:

```
Assumption Confidence
Equipment     HIGH    Builder Profile
Gross Margin  HIGH    Builder Profile
System Count  MEDIUM  Ryan OS default
Permit        LOW     Not confirmed
```

Every LOW row is automatically listed under Known Unknowns. That is what makes
proceeding on defaults safe: the system guesses, but it never hides a guess.

---

## Layout

```
ryan-os/
├── decision-engine/
│   ├── defaults.json          ← governed values. SINGLE SOURCE OF TRUTH.
│   ├── engine.py              ← decision logic (stdlib only, deterministic)
│   ├── profile_proposal.py    ← governed recommendation for unknown builders
│   ├── SPEC.md                ← the human-readable contract
│   ├── EMAIL_STANDARD.md      ← email layout + worked example
│   └── intake_schema.json     ← what an agent reads out of Outlook
├── asset-registry/
│   ├── registry.json          ← the authoritative directory of resources
│   ├── registry.py            ← search, resolve, validate
│   └── schema/
├── builder-library/
│   ├── profiles/              ← one JSON per builder (fills itself as work arrives)
│   ├── examples/              ← two sample profiles used by the tests
│   ├── schema/
│   └── _TEMPLATE.builder.json
├── governance/
│   ├── GOVERNANCE.md          ← what may change, and how
│   ├── ESCALATION_POLICY.md   ← when Ryan gets interrupted
│   ├── RESOURCE_DISCOVERY.md  ← never search; ask the registry
│   ├── CONFIDENCE_FRAMEWORK.md
│   └── DECISION_LOG.md        ← ADR-001 … ADR-007
├── playbooks/
│   ├── bid-turnover.md        ← the runbook
│   ├── new-builder-onboarding.md
│   ├── email-classification.md
│   └── orchestrator-loop.md   ← what's built vs. what isn't
├── prompts/                   ← portable system + task prompts
├── cli/                       ← turnover.py · profile.py · asset.py
└── tests/                     ← 105 tests, stdlib unittest
```

---

## Tests

```bash
python3 ryan-os/tests/test_engine.py    # 56 - decision engine
python3 ryan-os/tests/test_phase2.py    # 49 - proposals + asset registry
python3 ryan-os/cli/asset.py validate   # registry integrity
python3 ryan-os/cli/profile.py validate # builder profiles
```

No dependencies, no install. The suite **pins the governed numbers on purpose** —
changing 35% to 32% breaks it. That is not friction to route around, it is the
governance control working. See `governance/GOVERNANCE.md`.

---

## The most important next steps

**1. Register the six Asset Registry gaps.** `python3 ryan-os/cli/asset.py gaps`

Pricing workbook, job folder template, Drive root, server root, Manual J
software, Outlook mailbox. Each is a question agents currently cannot answer —
and by design they will flag it rather than guess. `pricing-workbook` is the
highest-impact of the six.

**2. Add profiles for the active production builders.** The library now fills
itself as new work arrives, one approval per builder. What it cannot learn on
its own is the *existing* builders' real contracted margins, where the 35%
fallback is furthest from the truth.

Both are Class A data changes — no code, no approval.

---

## What is not built

Honest scope boundaries — details in `playbooks/orchestrator-loop.md`:

- **No automatic Outlook detection.** An agent session or a person still starts
  the loop. Automating it needs a persistent runtime and credentials — a Class C
  architecture decision.
- **No job state tracking.** The turnover email asks for reply-all on Manual J
  and bid completion, and the classification playbook routes those replies, but
  nothing writes the state down yet.
- **No dashboard.** Deferred until state is being captured — a dashboard over
  data nobody is collecting is a screen of zeros.

---

## Changing something

| You want to | Do this |
|---|---|
| Add or update a builder | `profile.py create`, or edit `builder-library/profiles/` — no approval needed |
| Register a resource, or close a gap | Edit `asset-registry/registry.json`, then `asset.py validate` — no approval needed |
| Handle a builder-specific margin or equipment package | Builder Profile, not `defaults.json` |
| Change a governed default for everyone | Class B: Ryan approves, log it in `DECISION_LOG.md`, bump the version, update the test |
| Add a component or change the structure | Class C: written proposal, Ryan decides |

Full process in `governance/GOVERNANCE.md`.
