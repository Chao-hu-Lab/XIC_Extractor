# C1b — Linear Edge Baseline Retirement Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.1
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Companion spec:** [C1a — Baseline module relocation](2026-05-24-peak-pipeline-cleanup-baseline-module-consolidation-spec.md)
**Precondition:** P2 promoted (AsLS is the production baseline). C5 (area
integration single entry) landed and validated. C1a landed and validated.

## Purpose

Retire the linear-edge baseline path. After C5 has migrated every caller
to the single integration entry (which uses AsLS), the
`integrate_linear_edge_baseline` function and the `integrate_with_baseline`
selector wrapper have no remaining callers and can be deleted.

C1b is the second half of the original C1 plan. C1a relocated AsLS into
the peak-detection package. C1b removes the dead linear-edge code path.

This refactor introduces no behavioral change. Validation is behavioral
parity.

## Why C1b Has to Wait for C5

C5 owns the migration of the four current `integrate_linear_edge_baseline`
callers (`integration_audit.py`, `region_safe_merge.py`, `hypotheses.py`,
`peak_candidate_boundaries.py`) onto a single integration entry. Until C5
lands, the linear-edge function still has callers and cannot be deleted.

The original C1 spec tried to own both relocation and retirement, which
created a circular dependency with C5 (C5 needed C1 done; C1 Step 3 needed
C5 done). Splitting into C1a (independent) and C1b (after C5) removes the
cycle.

## Current State (assumed after P2 promoted + C1a + C5)

This section describes the working-tree state C1b expects to find when it
runs. **None of these state items exist in working tree today** — they are
the cumulative output of P2 promotion, C1a, and C5:

- `xic_extractor/peak_detection/baseline.py` will define both
  `integrate_linear_edge_baseline` (legacy) and an AsLS-using path (added
  by P2)
- `integrate_with_baseline` selector (added by P2) will dispatch on
  `baseline_method` argument
- After C5, all production callers will go through `integrate_peak_region`,
  which only uses AsLS
- `BaselineIntegration.baseline_type` field will exist and take only
  `"asls"` in production runs

If any of these conditions are not met at C1b kick-off, escalate to spec
owner — the precondition chain is broken and C1b should not start.

## Required Change

### Step 1 — Delete the linear-edge function

Delete `integrate_linear_edge_baseline` from
`xic_extractor/peak_detection/baseline.py`. Confirm via grep that no
caller remains. If any caller is found, hold the deletion and report.

### Step 2 — Delete the selector wrapper

Delete `integrate_with_baseline` from the same module. The selector
existed only to enable the P2 shadow / promotion transition; after C5 the
hypothesis spine calls AsLS directly and the selector has no callers.

### Step 3 — Decide `baseline_type` field fate

`BaselineIntegration.baseline_type` is currently a string field that took
values `"linear_edge"` or `"asls"`. After Step 1 the field has one
possible value. Options:

- (a) drop the field entirely
- (b) keep it as `"asls"` literal for future-proofing

Decision: keep (b). The handoff vision lists baseline_type as part of the
integration audit contract. Dropping the field would force re-introducing
it later when a third baseline method (airPLS, rolling-ball, BEADS) is
considered.

Document the field's current single-value constraint in the dataclass
docstring so reviewers do not assume it is dynamic.

### Step 4 — Update audit TSV emitters if needed

Since `baseline_type` is constant in all rows, audit TSV emitters can
either keep emitting the column (`alignment_cell_integration_audit.tsv`
already has the column) or drop it. Keep emitting; column constancy is
not a reason to remove it. The C-spec validation contract requires TSV
columns to remain stable.

## Validation Contract

Behavioral parity required:

1. Run 8RAW with the cleanup interim state (Phase 1 + C1a + C5)
2. Apply C1b refactor
3. Re-run 8RAW
4. `peak_candidates.tsv`, `peak_candidate_boundaries.tsv`,
   `alignment_matrix.tsv`, `alignment_review.tsv`, `alignment_cells.tsv`,
   `alignment_cell_integration_audit.tsv` must hash-match
5. `baseline_type` audit column must contain `"asls"` in all rows

## Rollback Condition

Restore the deleted functions if any of:

- a caller of `integrate_linear_edge_baseline` or `integrate_with_baseline`
  is found at refactor time (means C5 missed a site)
- hash mismatch on parity TSVs (would be a regression in the AsLS-only
  path)

## What This Spec Does Not Change

- AsLS formula or parameters
- production area or matrix output
- TSV column names
- `BaselineIntegration` dataclass shape (only the docstring constraint
  changes)
- scoring weights or evidence values

## Open Questions

- Should `BaselineIntegration.baseline_type` be converted from `str` to a
  `Literal["asls"]` type alias to enforce the single-value constraint at
  type-check time? Decision deferred; clean either way.
- If C5 is in flight when C1b is scheduled, what is the coordination
  mechanism? Lean toward: do not start C1b until C5 lands as a single
  validated PR. No partial-state interaction.

## Acceptance Owner

Engineering owner runs parity validation, confirms hash match, records
result under `docs/superpowers/notes/`. PR includes the parity report and
a grep confirmation that no caller of the deleted functions remains.
