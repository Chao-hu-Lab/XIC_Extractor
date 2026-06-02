# Region Public Behavior Phase 1 Closeout

**Date:** 2026-06-02
**Status:** Complete for Phase 1 implementation
**Behavior label:** public behavior change
**Parent contract:**
[C4 / C6 / Region Public Behavior Retirement Productization Design](../specs/2026-06-02-public-behavior-retirement-productization-design.md)
**Phase addendum:**
[Region-Boundary Public Behavior Addendum](../specs/2026-06-02-region-boundary-public-behavior-addendum.md)

## Verdict

Region Phase 1 is now productized as a public decision projection.
`RegionSelectionDecision` is the decision owner, and public output surfaces no
longer need to infer product region state from `shadow_verdict`,
`merge_suggestion_source`, or resolver token naming alone.

This phase does not broaden promotion authority. The only extraction behavior
that may change selected bounds or area remains the existing adjacent-WIS
safe-merge class after safe gates pass. Alignment still does not use region
decision fields to promote numeric matrix values.

## Public Behavior Changes

- `peak_region_selection_shadow.tsv` and
  `peak_region_selection_shadow_summary.tsv` now include explicit region
  decision projection fields:
  `decision_status`, `decision_class`, `product_action`,
  `selected_candidate_id`, `selected_boundary_id`, `alternate_boundary_ids`,
  `evidence_sources`, `support_reasons`, `conflict_reasons`, `audit_reason`,
  `promotion_reason`, and `baseline_method`.
- `PeakRegionAuditSummary` and `AlignedCell` now carry the per-cell region
  decision projection directly from `RegionSelectionDecision`.
- `alignment_cells.tsv` now includes per-cell
  `region_decision_status`, `region_decision_class`,
  `region_product_action`, `region_promotion_reason`, and
  `region_baseline_method`.
- Workbook `Audit` now includes the same per-cell region decision fields.
- Alignment workbook metadata schema is now `alignment-results-v2`.

## Expected Non-Changes

- No resolver default or accepted resolver value changed.
- No `alignment_matrix.tsv` schema or workbook `Matrix` schema changed.
- No workbook `Review` or `alignment_review.tsv` region aggregate fields were
  added.
- No new promotion for wider-boundary, neighbor-apex, split, unsupported merge,
  CWT-only, WIS-only, RT-only, shape-only, or score-only evidence.
- No `linear_edge` semantics were reintroduced.

## Review Record

The Phase 1 addendum received xhigh review before implementation:

- `strategy-challenger` initially blocked on alignment numeric boundaries,
  ambiguous exit rules, and missing propagation invariant. Re-check closed all
  blockers.
- `implementation-contract-reviewer` initially blocked on cell-vs-family
  alignment projection and workbook schema versioning. Re-check closed all
  blockers.

Implementation review:

- `implementation-contract-reviewer` initially blocked on missing adapter-chain
  tests and remaining `alignment-results-v1` workbook fixtures. Main fixed both
  issues. Final re-check unblocked implementation.

## Verification

RED tests first failed on missing decision fields, missing `AlignedCell`
projection fields, and old `alignment-results-v1` metadata.

Focused verification after implementation:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_region_audit.py tests/test_alignment_owner_matrix.py tests/test_alignment_xlsx_writer.py tests/test_alignment_tsv_writer.py tests/test_peak_region_selection_shadow.py tests/test_alignment_pipeline_outputs.py
```

Result: `67 passed in 6.71s`.

Workbook v2 cleanup verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_untargeted_final_matrix_contract.py tests/test_alignment_pipeline_atomic_writes.py tests/test_peak_region_audit.py tests/test_alignment_owner_matrix.py tests/test_alignment_xlsx_writer.py tests/test_alignment_tsv_writer.py tests/test_peak_region_selection_shadow.py tests/test_alignment_pipeline_outputs.py
```

Result: `74 passed in 4.97s`.

Phase 1 addendum focused shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_region_model_selection.py tests/test_region_safe_merge.py tests/test_peak_region_selection_shadow.py tests/test_boundary_hypotheses.py tests/test_boundary_scoring.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_table.py tests/test_cwt_proposals.py tests/test_cwt_peak_candidate_audit.py tests/test_config.py tests/test_settings_section.py tests/test_settings_section_advanced.py tests/test_settings_new_fields.py tests/test_gui_main.py tests/test_run_discovery.py tests/test_discovery_pipeline.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_run_alignment.py tests/test_validation_harness.py
```

Result: `446 passed, 6 warnings`. The warnings are existing synthetic CWT
`PeakPropertyWarning` cases.

## Remaining Risk

This phase is `production_candidate` for public region decision projection, not
full RB2 handoff-spine storage. Region facts are still not fully stored in
`IntegrationResult`, `AuditTrail`, `EvidenceVector`, or `PeakHypothesis`.

Alignment numeric matrix behavior remains intentionally unchanged. Any future
alignment promotion of region safe-merge behavior needs a separate behavior spec
and validation review.
