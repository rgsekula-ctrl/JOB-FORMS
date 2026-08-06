# Ryan OS — Operations Orchestrator

**Phase 1: the Bid Turnover Decision Engine.**

Turns a new HVAC bid request sitting in Outlook into an internal Load & Bid
turnover email — fast enough that the estimating team is working on the Manual J
within minutes.

---

## The governing principle

> The system never sacrifices getting work started in pursuit of perfect
> information. If a safe, governed default exists, use it. If something
> materially affects the design or the proposal, flag it. Only interrupt Ryan
> when real business judgment is required.

Every rule in this directory is downstream of that sentence.

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

### From the forms app

```bash
python3 app.py
```

Then open **Bid Turnover** in the sidebar. Paste the builder's email, fill in
what it says, get the turnover email with a copy button.

### From an agent

Claude picks up the `bid-turnover` skill automatically. For Codex or ChatGPT,
paste `prompts/operations-orchestrator.system.md` as the system prompt and
`prompts/bid-turnover.task.md` as the task.

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
│   ├── SPEC.md                ← the human-readable contract
│   ├── EMAIL_STANDARD.md      ← email layout + worked example
│   └── intake_schema.json     ← what an agent reads out of Outlook
├── builder-library/
│   ├── profiles/              ← one JSON per builder (EMPTY — populate this)
│   ├── examples/              ← two sample profiles used by the tests
│   ├── schema/                ← profile JSON schema
│   └── _TEMPLATE.builder.json
├── governance/
│   ├── GOVERNANCE.md          ← what may change, and how
│   ├── ESCALATION_POLICY.md   ← when Ryan gets interrupted
│   ├── CONFIDENCE_FRAMEWORK.md
│   └── DECISION_LOG.md        ← ADRs, including the margin change
├── playbooks/
│   ├── bid-turnover.md        ← the runbook
│   ├── email-classification.md
│   └── orchestrator-loop.md   ← what's built vs. Phase 2/3
├── prompts/                   ← portable system + task prompts
├── cli/                       ← turnover.py + example intakes
└── tests/                     ← 56 tests, stdlib unittest
```

---

## Tests

```bash
python3 ryan-os/tests/test_engine.py
```

No dependencies, no install. The suite **pins the governed numbers on purpose** —
changing 35% to 32% breaks it. That is not friction to route around, it is the
governance control working. See `governance/GOVERNANCE.md`.

---

## The most important next step

**The Builder Library is empty.** Until it has real profiles, every builder reads
as new: 30% margin, Lennox default, most rows flagged LOW. The system works —
that is what the defaults are for — but it is running on the least information
it will ever have.

Adding profiles needs no code and no approval (a Class A data change). Each one
converts MEDIUM assumptions into HIGH ones, which is the system getting faster
and safer at the same time. Start with the active production builders, where the
35% fallback is furthest from their real contracted margin.

See `builder-library/README.md`.

---

## What Phase 1 does not do

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
| Add or update a builder | Edit `builder-library/profiles/` — no approval needed |
| Handle a builder-specific margin or equipment package | Builder Profile, not `defaults.json` |
| Change a governed default for everyone | Class B: Ryan approves, log it in `DECISION_LOG.md`, bump the version, update the test |
| Add a component or change the structure | Class C: written proposal, Ryan decides |

Full process in `governance/GOVERNANCE.md`.
