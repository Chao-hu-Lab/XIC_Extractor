# C1b — Linear Edge Baseline Retirement Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.3 — PAUSED until AsLS truth validation
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Companion spec:** [C1a — Baseline module relocation](2026-05-24-peak-pipeline-cleanup-baseline-module-consolidation-spec.md)
**Precondition:** C5 (area integration single entry) landed and validated, C1a
landed and validated, and [P2c AsLS truth validation](2026-05-26-peak-pipeline-asls-truth-validation-spec.md)
has reached `GO_FOR_LINEAR_EDGE_RETIREMENT`. P2b conditional audit promotion is
not sufficient. P2b's temporary linear-edge rollback audit columns must also be
deprecated by an approved schema note before implementation starts.

## Purpose

Retire the linear-edge baseline path. After C5 has migrated production package
callers to the single integration entry, AsLS truth validation has cleared, and
diagnostic comparator callers have been migrated or retired, the
`integrate_linear_edge_baseline` function and the `integrate_with_baseline`
selector wrapper have no remaining callers and can be deleted.

C1b is the second half of the original C1 plan. C1a relocated AsLS into
the peak-detection package. C1b removes the dead linear-edge code path.

This refactor introduces no behavioral change. Validation is behavioral
parity.

## Why C1b Has to Wait for C5 And AsLS Truth

C5 owns the migration of production package
`integrate_linear_edge_baseline` callers (`integration_audit.py`,
`region_safe_merge.py`, `hypotheses.py`, `peak_candidate_boundaries.py`) onto a
single integration entry. Maintained diagnostic comparator tools may still call
the legacy function after C5; C1b must either migrate those diagnostics to an
approved comparator interface or retire them before deleting the function.

The 2026-05-26 design correction adds a second blocker: P2b currently proves
only conditional audit promotion, not retirement authority. Linear-edge deletion
requires a current-code AsLS-vs-linear-edge baseline evidence gate built from
`p2_baseline_truth_audit`-style summary rows and plots, plus the required
blank/carryover safety disposition or exclusion. It does not require manual
integration as the comparator, and it must not rely on a fixed area-uplift
ratio.

A third blocker is the temporary P2b rollback audit surface. If
`alignment_cell_integration_audit.tsv` still emits
`area_baseline_corrected_linear_edge` or `baseline_score_linear_edge`, C1b
cannot delete the linear-edge computation and also preserve audit parity. Those
rollback columns require a separate schema/deprecation decision before C1b
starts.

The original C1 spec tried to own both relocation and retirement, which
created a circular dependency with C5 (C5 needed C1 done; C1 Step 3 needed
C5 done). Splitting into C1a (independent) and C1b (after C5) removes the
cycle.

## Current State (assumed after C1a + C5 + AsLS truth validation)

This section describes the working-tree state C1b expects to find when it
runs. **None of these state items exist in working tree today** — they are
the cumulative output of C1a, C5, and a separate AsLS truth-validation spec:

- `xic_extractor/peak_detection/baseline.py` will define both
  `integrate_linear_edge_baseline` (legacy) and an AsLS-using path (added
  by P2)
- `integrate_with_baseline` selector (added by P2) will dispatch on
  `baseline_method` argument
- After C5 and truth validation, all production package callers will go through
  the single integration entry, and the selected method will be AsLS-only
- Maintained diagnostic comparator callers in `tools/diagnostics/` will already
  be migrated to an approved comparator interface or explicitly retired
- `BaselineIntegration.baseline_type` field will exist and take only
  `"asls"` in production runs
- P2b temporary linear-edge rollback columns will already be absent from the
  accepted post-rollback audit schema, with a schema/deprecation note and hash

If any of these conditions are not met at C1b kick-off, escalate to spec
owner — the precondition chain is broken and C1b should not start.

## Required Change

### Step 1 — Delete the linear-edge function

Delete `integrate_linear_edge_baseline` from
`xic_extractor/peak_detection/baseline.py`. Confirm via grep that no caller
remains in `xic_extractor/`, `tools/`, `scripts/`, or tests except expected
deletion-diff references. If any maintained caller is found, hold the deletion
and report whether it is production, diagnostic, or test-only.

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
not a reason to remove it.

Do not silently keep or recompute linear-edge rollback columns. If the columns
still exist, stop C1b. Their removal is a public audit schema migration and
must be approved before this refactor.

## Validation Contract

Behavioral parity required:

1. Run 8RAW with the cleanup interim state (Phase 1 + C1a + C5)
2. Apply C1b refactor
3. Re-run 8RAW
4. `peak_candidates.tsv`, `peak_candidate_boundaries.tsv`,
   `alignment_matrix.tsv`, `alignment_review.tsv`, and `alignment_cells.tsv`
   must hash-match
5. `alignment_cell_integration_audit.tsv` must hash-match only against the
   approved post-rollback-column baseline. If rollback columns still exist,
   this validation is invalid and C1b must not start.
6. `baseline_type` audit column must contain `"asls"` in all rows

## Rollback Condition

Restore the deleted functions if any of:

- a caller of `integrate_linear_edge_baseline` or `integrate_with_baseline`
  is found at refactor time (means C5 missed a production site or diagnostic
  comparator migration/retirement is incomplete)
- `area_baseline_corrected_linear_edge` or `baseline_score_linear_edge` is still
  emitted by the accepted audit schema
- hash mismatch on parity TSVs (would be a regression in the AsLS-only
  path)

## What This Spec Does Not Change

- AsLS formula or parameters
- production area or matrix output
- TSV column names, except for the separately approved rollback-column
  deprecation that must happen before C1b starts
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
