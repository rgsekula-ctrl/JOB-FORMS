---
name: asset-registry
description: >
  Looks up the authoritative Ryan OS resource for any WCS operational need - forms, proposal and bid
  templates, pricing workbooks, job folders, applications, server and Google Drive locations, builder
  libraries. Use BEFORE searching the filesystem, Drive, or the web for any work-related file or tool,
  and whenever Ryan asks "where is", "which version", "what should I use for", "do we have a template
  for", "where do we keep", or mentions finding/locating a form, template, workbook, folder, or app.
  Also use to add a resource to the registry, list registered gaps, or check what Ryan OS considers
  authoritative.
---

# Ryan OS — Asset Registry

**Never search for a work-related resource first. Ask the registry.**

This is a hard governance rule, not a preference. Full policy:
`ryan-os/governance/RESOURCE_DISCOVERY.md`.

## Look it up

```bash
python3 ryan-os/cli/asset.py where "<what you need>"
```

Exit codes let you branch without parsing text:

| Code | Outcome | Do this |
|---|---|---|
| 0 | `FOUND` / `FOUND_CANDIDATE` | Use it. For a candidate, say you used it and ask Ryan to confirm. |
| 4 | `GAP_FLAGGED` | Registry knows it should exist and has none. **Flag it. Do not substitute.** |
| 5 | `NOT_REGISTERED` | Registry has never heard of it. **Flag it. Do not go hunting.** |

Other commands: `find <query>`, `show <asset_id>`, `list --category form`,
`gaps`, `validate`.

## The rule that matters is the miss

Anyone can use a registry when it has the answer. It earns its keep on a miss.

If you can't find a pricing workbook in the registry, then search the drive and
open `Pricing_2024_FINAL_v3.xlsx`, you have done something worse than nothing —
you produced a confident answer from an unverified source, and nobody
downstream can tell. A flagged gap is a five-minute conversation. A silently
wrong resource is a wrong bid.

On a miss:

1. Stop.
2. Tell Ryan the registry has no authoritative entry.
3. Say what you needed it for.
4. Recommend the specific entry that should be added.
5. Do not proceed with a substitute unless Ryan approves one.

Finding a plausible file on disk is **evidence for the recommendation**, not
permission to use it:

> The registry has no authoritative pricing workbook. I found
> `Pricing_2024_FINAL_v3.xlsx` in the shared folder but haven't used it — I
> can't tell if it's current. Should that be registered, or is there a newer one?

## What's covered

Anything that would go into or come out of real WCS work: forms, templates,
pricing, plans, job files, proposals, schedules, builder information,
applications, storage locations.

**Not** covered: general knowledge, HVAC engineering references, code lookups —
anything you can reason about without a company-specific file.

The test: *if two versions could exist and picking the wrong one would be a
problem, it belongs in the registry.*

## Adding an asset

Class A data change — edit `ryan-os/asset-registry/registry.json`, then
`python3 ryan-os/cli/asset.py validate`.

Every asset answers five questions: what is it, where is it, who owns it, when
should it be used, what does it replace.

**`keywords` is the most important field.** Search matches on identity only —
id, name, keywords, category — never on description prose alone, because a
confident wrong answer is worse than no answer. Include the wrong-but-common
names people actually use; that's what makes lookups succeed.

## Current state

30 assets, 6 registered gaps. The highest-impact gap is `pricing-workbook` —
until estimating's pricing source is registered, any agent needing a cost is
guessing or asking.

```bash
python3 ryan-os/cli/asset.py gaps
```
