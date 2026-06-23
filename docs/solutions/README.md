# XIC Solution Notes

`docs/solutions/` stores reusable lessons from solved XIC problems. These notes
are deliberately different from handoffs and productization plans:

- handoffs explain the current branch state;
- plans/specs define what should be built or accepted;
- solution notes capture a reusable pattern, root cause, validation lesson, or
  workflow correction so the next agent does not rediscover it.

Before starting similar work, search this folder together with
`docs/superpowers/notes/` and the productization control plane:

```powershell
rg -n "<topic>|<module>|<error>|<artifact>" docs\solutions docs\superpowers\notes docs\superpowers\plans
```

## Categories

- `productization/`: readiness tier moves, writer authority, expected-diff,
  product blockers.
- `validation/`: no-RAW / 8RAW / 85RAW evidence, oracle design, artifact parity.
- `workflow/`: agent process, review gates, handoff, tool routing.
- `architecture/`: ownership boundaries, public contracts, decomposition.
- `testing/`: focused tests, fixtures, CI-equivalent gate behavior.
- `bugs/`: concrete regressions and root-cause fixes.

## Frontmatter

Use stable, searchable YAML frontmatter:

```yaml
---
title: "Short searchable title"
date: "YYYY-MM-DD"
category: "productization"
module: "backfill"
status: "current"
tags: ["backfill", "expected-diff"]
source_refs:
  - "docs/superpowers/plans/2026-06-15-productization-control-plane.md"
---
```

Keep scalar values quoted if they contain `: ` or ` #`.

## Quality Bar

A useful note answers:

- what symptom, decision, or artifact should make a future agent read it;
- what path was tempting but wrong;
- what rule, pattern, or implementation actually worked;
- what evidence proved it;
- what the next agent should do first.

Use `docs/solutions/templates/xic-solution-note-template.md` for new notes.
