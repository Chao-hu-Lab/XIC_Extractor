# Untargeted Identity Coherence Prototype Overview

**Date:** 2026-05-22
**Status:** Split review draft v0.4
**Branch:** `codex/untargeted-backfill-logic-reset`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset`

This file is the entrypoint. The detailed contract is split into focused specs
so review can separate method, validation, implementation, and downstream
boundary questions.

## Spec Map

Read in this order:

1. [Core identity spec](2026-05-22-untargeted-identity-coherence-core-spec.md)
   - seed coherence gate
   - RT-local candidate retrieval
   - tiered per-sample identity checks
   - would-primary / Review-only identity decisions
   - false independent feature suppression
2. [Controls spec](2026-05-22-untargeted-identity-coherence-controls-spec.md)
   - positive ISTD / stable controls
   - identity decoys
   - input `identity_coherence_controls_manifest.yml` / `.tsv`
   - output `untargeted_identity_coherence_controls.tsv`
   - identity-layer Go/No-Go
3. [Implementation contract](2026-05-22-untargeted-identity-coherence-implementation-contract.md)
   - evidence firewall
   - `IdentityCoherenceConfig`
   - base identity Go/No-Go for firewall, weak-basis, infrastructure, and cost
   - `untargeted_identity_coherence_requests.tsv` seed/request audit surface
   - inline and diagnostic invocation modes
   - process-mode payload boundary
   - frozen output schemas
   - RAW/XIC request accounting
4. [Downstream audit boundary](2026-05-22-untargeted-identity-coherence-downstream-audit-boundary.md)
   - background / blank / QC audit is non-gating
   - contaminant handling consequence
   - final-matrix filtering, area correction, normalization, and statistics
   - future downstream audit spec boundary

The review story is a visual companion:

- [Story HTML](2026-05-22-untargeted-identity-coherence-prototype-story.html)

## Non-Negotiable Order

The implementation sequence must not be reversed:

```text
identity-family formation / false independent feature suppression
  -> Backfill / value recovery for accepted identity families
  -> downstream final-matrix filtering, area correction, normalization, statistics
```

Backfill is value recovery after identity formation. Downstream filtering is
analytical eligibility after identity/value outputs exist.

## Responsibility Boundary

This project does perform filtering-like work inside identity formation, but the
object being filtered is false independent identity, not downstream analytical
eligibility.

In scope for the untargeted identity layer:

- collapse duplicate activations that are really the same feature family;
- prevent duplicate-owner losers from becoming independent primary features;
- re-associate RT-drifted observations with the same identity family when the
  pre-Backfill evidence supports that family relationship;
- expose ambiguous owners, multi-seed conflicts, RT-only support, weak-basis
  support, and Backfill-dependent support as Review-only identity states;
- decide whether an observed row has enough identity-family evidence to be a
  provisional primary identity candidate.

Out of scope for this identity layer:

- final-matrix feature filtering based on blank abundance, QC CV, biological
  missingness, downstream cohort design, or statistical model needs;
- area correction, normalization, imputation, batch correction, or abundance
  transformation;
- deciding whether a biologically real but analytically noisy feature should be
  retained for downstream statistics.

## Method Thesis

The v0.2 design had a methodological flaw: an RT-windowed peak search before
Backfill is still methodologically close to Backfill. It prevents leakage from
Backfill outputs, but it does not by itself prove identity quality.

V0.4 therefore asks:

```text
Can pre-Backfill seed coherence plus independent per-sample trace identity
checks support provisional identity families without letting RT-only recurrence,
Backfill rescue, or downstream background/QC signals masquerade as identity
evidence?
```

RT coherence is necessary but not sufficient.

## Confidence Ceiling

A positive diagnostic decision is only provisional identity-family support. It
is not MSI Level 1 identification and must not be worded as
library/authentic-standard confirmation unless a future contract adds
library-grade MS/MS or authentic-standard evidence.

References:

- Sumner et al. 2007, Metabolomics Standards Initiative,
  <https://doi.org/10.1007/s11306-007-0082-2>
- Schymanski et al. 2014, non-target identification confidence,
  <https://doi.org/10.1021/es5002105>

## Shared Invariants

These apply to every split spec:

- Identity decisions must use pre-Backfill evidence only.
- `owner_backfill` rescued values, workbook values, final matrix inclusion, and
  post-Backfill production statuses are forbidden for identity promotion.
- Targeted ISTD labels and controls are validation evidence only; they do not
  promote identities.
- Identity decoys are in scope because they test false identity promotion.
- Background / blank / QC audit is non-gating and downstream-facing.
- Domain logic must not import `tools/diagnostics`, GUI, workbook, report,
  process, CLI, or RAW adapter surfaces.
- Existing untargeted and targeted primitives may be reused as metrics,
  concepts, or small domain helpers, but not by importing high-level diagnostic
  tools into identity domain logic.

## Review Checklist

Use the split specs to review specific questions:

- Method correctness: review the core identity spec.
- Specificity/sensitivity evidence: review the controls spec.
- Engineering feasibility and schemas: review the implementation contract.
- Scope creep and filtering boundary: review the downstream audit boundary.

Implementation should not begin until the core spec, controls spec, and
implementation contract have been reviewed together. The downstream audit
boundary is allowed to remain intentionally thin, but it must not be violated by
identity implementation.
