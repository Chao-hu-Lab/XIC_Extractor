# 2026-06-10 Family Authority Backfill Risk Note

## Verdict

FAM000028 exposes a deeper product architecture risk: `Family` is still carrying
too much decision authority. The immediate symptom is that
`NormalBC2263_DNA` and `NormalBC2264_DNA` were not written into the activated
matrix for the m/z 242.114 / RT 12.2653 row, even though the MS1 evidence and
user target/standard review indicate they should be backfilled.

This should not be treated as a one-off manual override. It is evidence that the
current family / duplicate-claim machinery can block valid same-peak backfill at
the product layer.

## 2026-06-10 Resolution Update

The immediate FAM000028 product failure is closed in the standard-peak
productization path.

- The shift-aware calibration pack now admits overlay-supported reference-family
  rows even when non-reference source-family summaries have a low minimum
  post-shift shape correlation.
- Product-authorized standard-peak duplicate / multi-claim labels are retained
  as audit warnings, not hard vetoes, when same-peak MS1 evidence is supported
  and no interference blocker is present.
- The consolidated 85RAW run writes the two previously missing cells:
  - `NormalBC2263_DNA = 5.225e+07`
  - `NormalBC2264_DNA = 1.16494e+07`
- The consolidated shadow projection artifact now deduplicates full-matrix
  projection rows across chunks and fails closed on conflicting accepted values.

Residual risk remains at the broader architecture boundary: raw family grouping
still carries contextual ambiguity and should remain below `PeakHypothesis` and
cell-level same-peak evidence in product authority.

## Concrete Case

- Product row: `FAM000028`
- Matrix row: m/z `242.114`, RT `12.2653`
- Samples not backfilled:
  - `NormalBC2263_DNA`
  - `NormalBC2264_DNA`
- Formal identity output:
  - `source_feature_family_count = 1`
  - `accepted_cell_count = 83`
  - `evidence_status = product_matrix_identity_complete`
- MS1 overlay evidence:
  - `family_verdict = ms1_shape_supports_family_backfill`
  - `detected_count = 83`
  - `rescued_count = 2`
  - `shape_supported_fraction = 1`
  - `global_apex_interference_count = 0`

Key artifacts from the 85RAW productization run:

- `output/backfill_light_cell_evidence_85raw_20260609/standard_peak_machine_pipeline_consolidated_full_queue_20260610/formal_product_output/alignment_matrix_identity.tsv`
- `output/backfill_light_cell_evidence_85raw_20260609/standard_peak_machine_pipeline_consolidated_full_queue_20260610/consolidated_shadow_projection_cells.tsv`
- `output/backfill_light_cell_evidence_85raw_20260609/standard_peak_machine_pipeline_queue_r521_671_20260610/family_ms1_overlay_batch/family_ms1_overlay_batch_summary.tsv`
- `output/backfill_light_cell_evidence_85raw_20260609/standard_peak_machine_pipeline_queue_r521_671_20260610/family_ms1_overlay_batch/648_fam000028_retained_backfill_missing_overlay.png`

## Original Observed Product Failure

The two cells are present as rescued values, but the productized matrix does not
write them:

- `current_raw_status = rescued`
- `current_production_status = accepted_rescue`
- `review_rescued_cell = TRUE`
- `current_matrix_written = FALSE`
- `projected_matrix_written = FALSE`
- `shadow_decision = context`
- `shadow_reasons = evidence_gate_requires_review`
- `shadow_warnings = same_peak_multi_claim`
- `gap_fill_state = not_filled`
- `gap_fill_reason = not_requested_duplicate_loser`

This means the code sees the rescue and records it, but the final authority
chain remains review-only.

## Why This Is Deeper Than One Gate

The current `Family` concept is doing too many jobs:

- coarse m/z / RT grouping
- feature identity proxy
- duplicate claim resolver
- backfill gate input
- gallery / evidence grouping key
- final matrix row influence

Those responsibilities should not have equal authority. In this case, the final
matrix identity row is clean, but older family-level duplicate-claim state still
blocks cell-level backfill. That is the architectural smell.

The practical issue is not that duplicate detection is useless. Duplicate and
multi-claim context is useful as a warning. The problem is that it can still
act as a hard veto against a clean product row with strong same-peak evidence.

## Target / Standard Evidence Gap

The user identified this as a standard/target-supported compound and judged the
target result as requiring backfill. In the inspected productization summary,
`target_benchmark_context_counts` is empty, so the target/standard evidence did
not appear to enter the activated matrix product authority chain.

This is a separate product gap:

- user-level target/standard evidence exists;
- MS1 family overlay supports the same peak;
- but productization does not treat target/standard support as an authority
  source capable of overriding duplicate-loser review-only state.

## Design Implication

`Family` should be downgraded to context. It can explain local ambiguity and
duplicate pressure, but it should not be the product authority that decides
whether a target/standard-backed, same-peak MS1 cell may be written.

Preferred decision hierarchy:

1. `PeakHypothesis` owns same-peak / same-compound product identity.
2. Cell-level `Trace` / sample evidence owns whether a missing value can be
   backfilled.
3. Target/standard anchors can provide strong product authority when they match
   the same `PeakHypothesis`.
4. `Family` and duplicate-claim context become warnings unless there is direct
   evidence of neighboring-peak interference, non-standard peak shape, or
   conflicting product identity.

## Proposed Rule Direction

For standard-peak backfill, a duplicate/multi-claim label should not block
matrix writing when all of the following hold:

- the row has a target/standard anchor or approved product `PeakHypothesis`;
- MS1 overlay supports same-peak shape;
- gaussian-smoothed peak shape is standard;
- no global apex interference is detected;
- the candidate cell is inside the expected same-peak RT / m/z context;
- the value is an accepted rescue and not a conflicting primary detection.

In that case:

- write the value into the activated matrix;
- keep `same_peak_multi_claim` / duplicate context as an audit warning;
- preserve provenance showing the value came from backfill, not primary
  detection.

## Residual Risk

If this is not fixed, valid standard-peak backfills can continue to be lost
whenever historical family consolidation labels a cell as duplicate loser, even
when the final product row and MS1 evidence are clean.

This risk is not limited to FAM000028. Any row where family/source-family
history is noisier than the final `PeakHypothesis` can be affected.
