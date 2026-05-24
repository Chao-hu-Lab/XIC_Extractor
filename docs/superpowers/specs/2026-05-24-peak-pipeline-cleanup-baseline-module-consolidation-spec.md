# C1a — Baseline Module Relocation Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.1
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Companion spec:** [C1b — Linear edge retirement](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md)
**Precondition:** Phase 1 (P1-P6) validation reports clean. C1a is one of
the first cleanup specs that can land; no other C-spec is prerequisite.

## Purpose

Relocate `asls_baseline` from the top-level `xic_extractor/baseline.py`
module into the `xic_extractor/peak_detection/` package, then delete the
empty top-level module. This is purely structural and has no behavioral
impact.

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

After P2 lands (selector + AsLS path) and P2 promotion (AsLS becomes
production default for `area_baseline_corrected`), `integrate_linear_edge_baseline`
has no production caller for `area_baseline_corrected`. The selector
(`integrate_with_baseline`) becomes a thin wrapper around AsLS.

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

### Step 2 — Delete the empty top-level module

After the move, `xic_extractor/baseline.py` is empty. Delete the file.
Confirm via `grep -r "from xic_extractor.baseline"` that no consumer remains.

### Out of scope for C1a

The following work is owned by [C1b](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md):

- deleting `integrate_linear_edge_baseline` and the
  `integrate_with_baseline` selector
- collapsing `BaselineIntegration.baseline_type` to a single literal

Those changes require C5 to have migrated callers off the linear-edge
function first, so they cannot land alongside C1a.

## Validation Contract

Behavioral parity required:

1. Run 8RAW with `resolver_mode = region_first_safe_merge` and AsLS
   production baseline (i.e. the Phase 1 final state)
2. Apply C1 refactor
3. Re-run 8RAW
4. `peak_candidates.tsv`, `alignment_matrix.tsv`, `alignment_review.tsv`,
   `alignment_cells.tsv` must hash-match
5. `alignment_cell_integration_audit.tsv` must hash-match (since AsLS path
   is unchanged, only the module location differs)
6. `compute_local_sn_cache` output must be byte-identical (it calls
   `asls_baseline` which moved, but the function body did not change)

## Rollback Condition

Restore the deleted files and revert imports if any of:

- hash mismatch on the parity TSVs
- a non-obvious import cycle is introduced by moving AsLS into the
  peak_detection package (peak_detection currently imports from the global
  namespace, not the reverse)

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
- If P2 promotion has not happened (AsLS is still shadow-only at refactor
  time), C1 must wait. The precondition is explicit; the open question is
  who declares P2 "promoted" and how that is recorded.

## Acceptance Owner

Engineering owner runs the parity validation, confirms hash match, records
the result under `docs/superpowers/notes/`. PR must include the parity
report inline.
