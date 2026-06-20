---
name: xic-architecture-preflight
description: XIC Extractor implementation preflight for architecture, reuse, and call-cost discipline. Use before implementing or planning non-trivial diagnostics, RAW-backed evidence, preset-performance changes, matrix/activation/value-delta paths, model-selection work, HCD-PI, Delta Mass, CID-NL, or other evidence-provider additions.
---

# XIC Architecture Preflight

Use before writing code for non-trivial XIC features. The goal is to stop
architecture debt before a diagnostic path becomes sticky.

This is a preflight, not a review closeout. It should produce a compact
implementation contract before edits begin.

## Required Output Before Edits

```markdown
Goal:
Existing owner/helper to reuse:
New code location:
Evidence provider role:
Simplest product rule:
Call-cost model:
Public contracts at risk:
Validation gate:
Stop rule:
```

If cleanup-only, state which behavior remains numerically or schema-equivalent.
If behavior changes, name expected diff and acceptance oracle before coding.

## Core Questions

- Which product spine layer advances: `Trace`, `TraceGroup`, `PeakHypothesis`,
  `EvidenceVector`, `IntegrationResult`, model selection, `AuditTrail`, or
  cleanup-only?
- Which existing owner absorbs behavior, and which helper avoids a parallel
  parser/selector/writer?
- What is the simplest human-explainable product rule?
- What call-cost changes: RAW opens, XIC extraction calls, TSV scans, smoothing,
  batching, locality, or cache boundaries?
- Which public contract could drift?
- Which validation tier can close the decision?

## References

- Product spine, owner/helper, product-rule, call-cost, and contract questions:
  `references/preflight-contract.md`
- Red flags and minimal search:
  `references/red-flags-and-search.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
