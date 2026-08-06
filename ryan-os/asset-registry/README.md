# Ryan OS Asset Registry

The authoritative directory of operational resources. It answers one question:

> **Where is the right version of the thing I need?**

Every agent consults this **before** searching the filesystem, Google Drive, or
anywhere else. That is a hard rule — see `../governance/RESOURCE_DISCOVERY.md`.

---

## Use it

```bash
# The main call - resolves and tells you what to do next
python3 ryan-os/cli/asset.py where "bid proposal template"

python3 ryan-os/cli/asset.py find "grille"          # search
python3 ryan-os/cli/asset.py show quickbid-proposal # one asset
python3 ryan-os/cli/asset.py list --category form   # browse
python3 ryan-os/cli/asset.py gaps                   # what's missing
python3 ryan-os/cli/asset.py validate               # integrity check
```

Or browse **Asset Registry** in the Woods Forms App sidebar.

`where` exit codes: **0** use it · **4** known gap, flag it · **5** not
registered, flag it.

---

## The five questions

Every asset must answer all five. The schema enforces the first four.

| Question | Field |
|---|---|
| What is it? | `what_it_is` |
| Where is it? | `where_it_is` (kind + path + detail) |
| Who owns it? | `owner` |
| When should it be used? | `use_when` (and `do_not_use_when`) |
| What does it replace? | `replaces` / `replaced_by` |

---

## Status

| Status | Meaning | Agent behavior |
|---|---|---|
| `authoritative` | The one true version | Use it |
| `candidate` | Exists, not blessed yet | Usable — say so, ask Ryan to confirm |
| `deprecated` | Superseded | `where` redirects to the successor automatically |
| `gap` | Should exist, no version on file | **Flag it. Do not substitute.** |

### Gaps are entries, not omissions

A `gap` is a resource Ryan OS knows should exist but has no authoritative
version for. Writing it down turns an invisible hole into a known unknown — the
same reason the Decision Engine surfaces LOW-confidence assumptions instead of
hiding them.

Six gaps are registered today. The highest-impact one is **`pricing-workbook`**:
until estimating's pricing source is registered, any agent that needs a cost is
guessing or asking.

```bash
python3 ryan-os/cli/asset.py gaps
```

---

## Search is deliberately strict

A query only matches on **identity** — asset id, name, a declared keyword, or
category. A hit in the prose description is not enough on its own.

That strictness is the point. An early version of this registry answered
"truck inventory spreadsheet" with the HVAC Equipment Schedule Template marked
`[AUTHORITATIVE]`, because the word "spreadsheet" appeared in its description.
A confident wrong answer is worse than no answer: the caller stops looking.
Returning `NOT_REGISTERED` sends the agent to Ryan, which is correct.

So when you add an asset, **the `keywords` list is the most important field**.
Include the wrong-but-common names people actually use — that is what makes
lookups succeed.

---

## Adding an asset

Class A data change: edit `registry.json`, then validate.

```bash
python3 ryan-os/cli/asset.py validate
```

Validation checks required fields, enum values, duplicate ids, gaps missing a
recommendation, deprecated assets missing a successor, unreachable locations,
and **referential integrity** — a `related` or `replaced_by` pointing at an
unregistered id fails. A dangling pointer is worse than no pointer.

---

## Layout

```
asset-registry/
├── registry.json                 ← the assets
├── registry.py                   ← loader, search, resolve, validate
├── schema/asset.schema.json
└── README.md
```
