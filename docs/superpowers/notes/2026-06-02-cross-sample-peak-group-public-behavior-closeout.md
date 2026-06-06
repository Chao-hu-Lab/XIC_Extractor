# Cross-Sample Peak Group Public Behavior Closeout

**Date:** 2026-06-02
**Phase:** Cross-sample peak group public behavior migration
**Status:** production behavior implemented; focused gate passed
**Spec:** `docs/superpowers/specs/2026-06-02-cross-sample-peak-group-public-behavior-addendum.md`

## Verdict

The cross-sample peak group phase is complete for the current goal slice.
Semantic group identity is now projected through product Review/Audit/Cells and
metadata surfaces. `OwnerAlignedFeature` remains the public compatibility
facade, while `CrossSamplePeakGroupHypothesis` / `OwnerGroupDeliveryFeature`
own the successor group delivery contract.

The historical roadmap phase code is not used in new public schema fields,
metadata keys, or code constants. It remains only as a historical alias in the
active spec.

## Public Contract

Preserved:

- `alignment_matrix.tsv` sample columns and primary matrix values.
- Workbook `Matrix` sample columns and primary matrix values.
- Public row ID `feature_family_id` / `FAM######`.
- `owner_backfill` CLI/config naming.
- Public `cluster_sample_local_owners(...)` compatibility return shape.

Changed:

- `alignment_review.tsv` and workbook `Review` add row-level group projection:
  `group_hypothesis_id`, `public_family_id`, `group_construction_role`,
  `group_delivery_role`, `group_membership_source`, `consolidation_state`,
  `consolidation_winner_group_hypothesis_id`,
  `consolidation_source_group_hypothesis_id`.
- `alignment_cells.tsv` and workbook `Audit` add cell-level group projection,
  gap-fill, missing-observation, claim, and consolidation fields, including
  `group_claim_state`.
- `alignment_owner_backfill_seed_audit.tsv` adds group/gap-fill request fields.
- Run metadata schema is now `alignment-results-v3` with semantic policy keys:
  `cross_sample_peak_group_policy`, `public_family_id_policy`,
  `group_delivery_policy`, `gap_fill_policy`, `legacy_owner_backfill_role`,
  `pre_backfill_projection_policy`, and `matrix_value_policy`.
- Failed, unassessable, or no-accepted-peak group-centered backfill attempts now
  materialize as `unchecked` audit outcomes with
  `gap_fill_reason=query_attempt_not_detected` and
  `missing_observation_state=missing_unchecked`; these outcomes do not write
  primary matrix values.

## Review

`implementation-contract-reviewer` initially blocked the phase because failed
or unassessable backfill query outcomes were still being collapsed into generic
absent cells. The fix now materializes those query outcomes in `owner_backfill`,
preserves them in `owner_matrix`, and verifies TSV visibility.

Re-check verdict: `PASS`.

## Verification

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_alignment_owner_family_successor_contract.py tests/test_alignment_owner_clustering.py tests/test_pre_backfill_consolidation.py tests/test_backfill_scope.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_alignment_claim_registry.py tests/test_alignment_primary_consolidation.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_debug_writer.py tests/test_alignment_output_levels.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py tests/test_alignment_process_backend.py tests/test_untargeted_final_matrix_contract.py tests/test_alignment_pipeline_atomic_writes.py
```

Result: `277 passed in 9.71s`.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
```

Result: `All checks passed!`.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Result: `Success: no issues found in 266 source files`.

```powershell
git diff --check
```

Result: no whitespace errors; Git reported CRLF conversion warnings only.

## Residual Risk

- Verification is synthetic/output-contract focused; no 8-RAW or 85-RAW run was
  performed for this phase.
- Legacy compatibility names such as `owner_backfill` and
  `OwnerAlignedFeature` remain by design.
- External consumers that rely on Review/Audit status counts may now see
  explicit `unchecked` query outcomes where attempted backfill previously
  disappeared into generic absent rows.
