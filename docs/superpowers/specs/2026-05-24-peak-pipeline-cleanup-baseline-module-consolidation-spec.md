# C1a — Baseline Module Relocation Spec

**Date:** 2026-05-24
**Status:** Completed in 2026-06-01 cleanup-retirement branch — structural
relocation only
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Companion spec:** [C1b — Linear edge retirement](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md)
**Precondition:** Phase 1 conditional blockers are documented and P2b's
conditional audit-promotion surface is stable. C1a must not assume AsLS
production readiness or linear-edge retirement. C1a is one of the first cleanup
specs that can land after that; no other C-spec is prerequisite.

## 2026-06-01 Implementation Closeout

C1a landed on `codex/cleanup-retirement-foundation` as a pure relocation:

- `asls_baseline` moved into `xic_extractor/peak_detection/baseline.py`.
- `xic_extractor/baseline.py` remains a thin compatibility re-export for
  external callers.
- Internal package imports use the peak-detection package path.
- Linear-edge retirement did not happen in this phase; it landed later in C1b
  after C5 and the retirement gates completed.

## Purpose

Relocate `asls_baseline` from the top-level `xic_extractor/baseline.py`
module into the `xic_extractor/peak_detection/` package, while preserving the
top-level import surface as a compatibility re-export unless a separate
breaking-change decision explicitly allows deletion. This is purely structural
and has no behavioral impact.

C1a is the first half of the original C1 plan. The second half — retiring
`integrate_linear_edge_baseline` and the `integrate_with_baseline`
selector — is the responsibility of [C1b](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md),
which depends on C5 having migrated all callers off the linear-edge
function. The split removes a circular dependency between the original C1
and C5.

This refactor introduces no behavioral change. Validation is behavioral
parity (hash-identical outputs).

## Current State

Two baseline modules coexist:

- `xic_extractor/baseline.py` (37 lines) — defines `asls_baseline` only
- `xic_extractor/peak_detection/baseline.py` (85 lines) — defines
  `BaselineIntegration`, `integrate_linear_edge_baseline`,
  `bounded_trace_interval`, `_area_counts_seconds`,
  `_area_uncertainty_counts_seconds`, `_safe_ratio`

After P2 lands (selector + AsLS path) and P2b conditional audit promotion,
`alignment_cell_integration_audit.tsv` can report AsLS in
`area_baseline_corrected`, but this does not prove AsLS baseline truth and does
not authorize deleting `integrate_linear_edge_baseline`. The selector
(`integrate_with_baseline`) remains method-preserving until C5 and the separate
AsLS truth-validation blocker are resolved.

After P4 lands (uncertainty formula correction), `_area_uncertainty_counts_seconds`
is replaced by a baseline-residual-based computation that needs an AsLS
baseline. The linear-edge dependency for uncertainty is gone.

## Required Change

### Step 1 — Move AsLS into the peak_detection package

Move `asls_baseline` from `xic_extractor/baseline.py` into
`xic_extractor/peak_detection/baseline.py`. Baseline correction is a
peak-detection concern; the top-level location was historical.

Update imports:

- `xic_extractor/peak_scoring.py:12` — change
  `from xic_extractor.baseline import asls_baseline` to
  `from xic_extractor.peak_detection.baseline import asls_baseline`
- any other consumer found by grep at refactor time

### Step 2 — Preserve the top-level compatibility module

After the move, replace `xic_extractor/baseline.py` with a thin re-export shim:

```text
from xic_extractor.peak_detection.baseline import asls_baseline
```

Confirm via grep that internal consumers have migrated to the new import path,
then keep the shim for external callers and tests that still import
`xic_extractor.baseline`. Deleting the file is out of scope unless a separate
public-contract break is approved.

### Out of scope for C1a

The following work is owned by [C1b](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md):

- deleting `integrate_linear_edge_baseline` and the
  `integrate_with_baseline` selector
- collapsing `BaselineIntegration.baseline_type` to a single literal

Those changes require C5 to have migrated callers off the linear-edge
function first, so they cannot land alongside C1a.

## Validation Contract

Behavioral parity required:

1. Run 8RAW with the accepted Phase 1 resolver/config surface and the current
   P2b conditional audit-promotion baseline surface
2. Apply C1a relocation refactor
3. Re-run 8RAW
4. `peak_candidates.tsv`, `alignment_matrix.tsv`, `alignment_review.tsv`,
   `alignment_cells.tsv` must hash-match
5. `alignment_cell_integration_audit.tsv` must hash-match (the selected audit
   baseline method is unchanged; only the module location differs)
6. `compute_local_sn_cache` output must be byte-identical (it calls
   `asls_baseline` which moved, but the function body did not change)
7. Import smoke tests must pass:
   - `from xic_extractor.baseline import asls_baseline`
   - `from xic_extractor.peak_detection.baseline import asls_baseline`

## Rollback Condition

Restore the prior imports if any of:

- hash mismatch on the parity TSVs
- a non-obvious import cycle is introduced by moving AsLS into the
  peak_detection package (peak_detection currently imports from the global
  namespace, not the reverse)
- the compatibility re-export changes function identity or defaults

## What This Spec Does Not Change

- AsLS formula or parameters
- production area or matrix output
- TSV column names
- scoring weights or evidence values
- resolver behavior

## Open Questions

- Should `BaselineIntegration` be promoted to a top-level type (e.g.
  `xic_extractor.peak_detection.models.BaselineIntegration`) so the
  hypothesis spine and the legacy audit path import from one location?
  Decision deferred until C3 (model unification) is scoped.
- Is there a circular import risk between `peak_detection/baseline.py` and
  `peak_scoring.py`? `peak_scoring` already imports `asls_baseline` directly;
  after C1 it would import from the peak_detection package. Verify at
  refactor time that no cycle is introduced through the
  `peak_detection.models` -> `peak_scoring` -> `peak_detection.baseline`
  path.
- If P2b conditional audit promotion has not happened (AsLS is still
  shadow-only at refactor time), C1a must wait. The precondition is explicit;
  P2b's note declares the audit surface that Cleanup should preserve, but it
  does not declare AsLS production-ready baseline truth.

## Acceptance Owner

Engineering owner runs the parity validation, confirms hash match, records
the result under `docs/superpowers/notes/`. PR must include the parity
report inline.
