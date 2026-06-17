# XIC Productization Evidence Inventory - 2026-06-17 23:40

Purpose: give another reviewer/agent enough factual context to critique the
current productization rules. This is an evidence list, not a promotion plan.

## Verdict

- The broad Backfill north star is still not solved. Current product-ready
  Backfill authority is limited to generated policy `write_ready` rows: 511
  matrix cells in the latest no-RAW 85RAW replay.
- The 4613 number means source-audit/generated-policy candidate rows, not 4613
  writable cells. Latest classification is 511 `write_ready`, 0
  `detected_flagged`, 4102 `blocked`.
- `standard_peak_backfill_policy_quality_explanations.tsv` is explanation-only.
  It explains blocked rows but cannot activate, rewrite, or promote anything.
- Several narrow Backfill slices are `production_ready`, but several tempting
  broad/general rules have direct negative evidence and must not be promoted.
- Targeted MS1 limited rescue, sample metadata no-output projection, and
  ReviewAction candidate sidecar verification are separate lanes with their own
  boundaries.

## Current Repo State Inspected

- Branch: `cc/framework-improvements`, ahead of origin by 33 commits.
- Worktree before this report: clean.
- Latest relevant commits:
  - `9ced4d61 docs: refresh productization handoff`
  - `a2c7d347 feat: add backfill policy quality explanations`
  - `3e2a9a2d Improve handoff snapshot workflow`
  - `34cdf61d docs: mark sample metadata order parity ready`
  - `6005870f feat: add review action candidate sidecar gate`
  - `d2c3b205 feat: add observed oracle backfill policy gate`

## Backfill Evidence That Currently Supports `production_ready`

| Evidence | Artifact / path | What it proves | What it does not prove |
| --- | --- | --- | --- |
| Generated policy writer replay | `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_quality_explained_no_raw_productization/standard_peak_backfill_policy_summary.json` | 4613 policy rows classified as 511 `write_ready`, 0 `detected_flagged`, 4102 `blocked`; quality explanation row count is 4613. | Does not make all 4613 rows writable. |
| Product writer expected-diff | `.../generated_policy_quality_explained_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | `acceptance_status=pass`, `readiness_tier=production_ready`, expected scope `backfill_policy_write_ready_rows`, 511 eligible/written cells, no blocking reasons. | Only covers the 511 generated `write_ready` rows. |
| Productization replay summary | `.../generated_policy_quality_explained_no_raw_productization/standard_peak_backfill_productization_summary.json` | Productization run `status=pass`, `matrix_cells_written=511`. | Not a broad activation proof. |
| Row-specific observed oracle | `output/productization_realdata_seed_guard_85raw_20260617/policy_observed_oracle_detected_flagged_full_trace/summary.json` | 72 formerly flagged rows passed full stored-trace reintegration within accepted `0.1 min / 10% area`; max boundary error `8.91875e-05`, max area relative error `0.098218`. | Only covers those 72 row-specific observed-oracle rows. |
| High-signal clean scoped writer | `.../narrow_high_signal_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | 72/72 expected-diff pass, `production_ready`. | Historical scoped slice, not product ceiling. |
| Low-scan clean scoped writer | `.../narrow_low_scan_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | 42/42 expected-diff pass, `production_ready`. | Does not justify arbitrary low-scan rows. |
| Low-height clean scoped writer | `.../narrow_low_height_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | 57/57 expected-diff pass, `production_ready`. | Does not make height `<2e6` alone a product rule. |
| Low-height-low-scan scoped writer | `.../narrow_low_height_low_scan_clean_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | 69/69 expected-diff pass, `production_ready`. | This is a bounded clean intersection only. |
| Low-height reintegration-stable scoped writer | `.../narrow_low_height_reintegration_stable_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | 220/220 expected-diff pass, `production_ready`. | Does not approve the full 299-row stability pool. |

## Backfill Positive Oracle Evidence

| Scope | Artifact | Result | Key numbers |
| --- | --- | --- | --- |
| High-signal clean heldout trace | `heldout_trace_reintegration_oracle/summary.json` | pass | 20 selected cases / 20 families. |
| Low-scan clean | `heldout_trace_reintegration_oracle_low_scan_clean_probe/summary.json` | pass | 56 available rows / 11 families; 11/11 pass; max boundary error `4.86717e-05`, max area error `0.038786`. |
| Low-height clean bounded | `heldout_trace_reintegration_oracle_low_height_bounded_probe_pad050/summary.json` | pass | 230 available rows / 54 families; 20/20 pass; max boundary error `0.0857986`, max area error `0.0564106`. |
| Low-height-low-scan clean | `heldout_trace_reintegration_oracle_low_height_low_scan_clean_probe/summary.json` | pass | 210 available rows / 51 families; 20/20 pass; max boundary error `4.80376e-05`, max area error `0.00881912`. |
| Low-height reintegration-stable family | `heldout_trace_reintegration_oracle_low_height_reintegration_stable_family/summary.json` | pass | Candidate scope 220 rows / 66 families; oracle basis is detected trace rows from same families; 20/20 pass; max boundary error `0.0830019`, max area error `0.0725986`. |
| Shape-clean reintegration-stable family | `heldout_trace_reintegration_oracle_shape_clean_reintegration_stable_family/summary.json` | pass | Candidate scope 104 rows / 33 families; 20/20 pass; max boundary error `0.0830019`, max area error `0.0725986`. |

## Backfill Negative Evidence / Do Not Promote

| Tempting rule | Artifact | Result | Why it blocks promotion |
| --- | --- | --- | --- |
| Direct all-stability writer | `heldout_trace_reintegration_oracle_all_stability_family/summary.json` | fail | 299 candidate rows / 77 families; 19/20 pass, 1 fail; max area error `0.19621` > 10% ceiling. |
| Apex-delta clean | `heldout_trace_reintegration_oracle_apex_delta_clean_probe/summary.json` | fail | 17/20 pass, 3 fail; max boundary error `2.19621`, max area error `0.424518`. |
| Width-only clean | `heldout_trace_reintegration_oracle_width_clean_probe/summary.json` | fail | 1/3 pass, 2 fail; max boundary error `1.86561`, max area error `0.599229`. |
| Shape-margin clean | `heldout_trace_reintegration_oracle_shape_margin_clean_probe/summary.json` | fail | 6/8 pass, 2 fail; max area error `0.198393`. |
| Shape-clean reintegration-stable writer | `narrow_shape_clean_reintegration_stable_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | fail as writer | Oracle passed, but product writer wrote 0 new cells; 104 rows were unchanged/pre-existing, so no nonzero product delta exists. |
| Quality blocker tokens | `standard_peak_backfill_policy_quality_explanations.tsv` | explanation only | These explain why rows stayed blocked. They are not evidence classes and must not be activation inputs. |

## Current Backfill Blocker Distribution

Latest quality sidecar has 4613 rows, all `explanation_only=TRUE`.

- Decision counts: 511 `write_ready`, 4102 `blocked`.
- Blocked next-evidence counts:
  - 1087 `trace_overlay_or_reintegration_evidence_required`
  - 3015 `approved_evidence_class_or_passing_oracle_required`
- Most common blocked combinations:
  - 1087 `missing_overlay_path`
  - 981 `shape_lt_0.95;height_lt_2000000;width_outside_0.30_0.65;scan_count_lt_10;scan_count_lt_7`
  - 505 same as above plus `apex_delta_gt_0.15`
  - 266 `height_lt_2000000;width_outside_0.30_0.65;scan_count_lt_10;scan_count_lt_7`
- Individual blocker token counts among blocked:
  - 2714 `height_lt_2000000`
  - 2630 `width_outside_0.30_0.65`
  - 2539 `scan_count_lt_10`
  - 2267 `shape_lt_0.95`
  - 2030 `scan_count_lt_7`
  - 1119 `apex_delta_gt_0.15`
  - 1087 `missing_overlay_path`
  - 476 `scan_count_gt_9`
  - 301 `height_gte_2000000`
  - 58 `local_global_ratio_lt_0.95`

Critical interpretation: these counts describe blocked rows. They are useful for
choosing review questions, not for creating write authority.

## Non-Backfill Lane Evidence

| Lane | Current tier | Evidence | Boundary |
| --- | --- | --- | --- |
| Targeted MS1 shape identity limited rescue | `production_ready` for headless limited workflows only | Control plane records explicit support TSV, auto-limited CLI, no-flag normal CLI default, 8RAW auto run, foreground 85RAW auto run with 11 support rows / 11 long-row changes / 66 matrix cells, and full gates. | Limited to `limited_5hmdc_5medc_v1`, targets `5-hmdC + 5-medC`, and output may only become `detected_flagged`. GUI and broader targets remain blocked. |
| Sample metadata no-output projection | `production_ready` for order/projection only; role/value behavior blocked | Focused tests recorded as 63 passed; resolver projects into extraction injection order, alignment sample-column order, instrument-QC sidecar, RT-normalization anchor diagnostic. | Roles/QC/blank/batch/matrix/exclusion must not change quant output, counted detection, normalized values, workbook, or matrix without new expected-diff/product decision. |
| ReviewAction audited apply / candidate sidecar | audited copy is `production_surface`; candidate sidecar verification is `production_candidate` | `6005870f` added candidate sidecar verifier and tests; focused `tests/test_review_actions.py` recorded as 32 passed; full gate later passed. | Candidate sidecar verifies identity only. It does not switch selected peak, recompute manual-boundary area, change counted detection, or write primary matrix. |
| Provisional production-candidate gate | `diagnostic_only` | Tests guard `readiness_label=diagnostic_only`, `production_ready=false`, and unchanged matrix. | Must not be consumed as product authority. |

## Validation Commands Recently Recorded

Current latest Backfill sidecar closeout:

- `uv run pytest tests\test_standard_peak_backfill_productization.py -q` -> 31 passed.
- `uv run ruff check xic_extractor\diagnostics\standard_peak_backfill_productization.py tests\test_standard_peak_backfill_productization.py` -> pass.
- `uv run mypy xic_extractor\diagnostics\standard_peak_backfill_productization.py` -> pass.
- no-RAW 85RAW replay under `generated_policy_quality_explained_no_raw_productization/` -> exit 0.
- full local gate after commit scope:
  - `uv run ruff check xic_extractor tests` -> pass.
  - `uv run mypy xic_extractor` -> pass.
  - `uv run pytest -v --tb=short -x` -> 3780 passed, 1 skipped.
  - `uv run python scripts\check_diagnostics_index.py` -> pass.

## Questions For Critical Review

1. Are the current `production_ready` Backfill slices evidence classes or just
   dataset-specific scaffolding that should be collapsed into a simpler product
   gate?
2. Is family-level detected-trace oracle evidence acceptable for rescued-cell
   writer authority, or does it require a stricter masked/product-writer oracle?
3. What evidence type should replace nested rules if the product goal is
   low-manual-intervention Backfill?
4. Should quality sidecar tokens stay purely explanatory, or should they be
   transformed into a separate candidate-prioritization queue with no matrix
   authority?
5. What minimal lockbox/holdout design would prevent cherry-picking when using
   the 4613-row candidate universe?

## Hard Warnings

- Do not treat `4613 rows` as 4613 approved writes.
- Do not promote broad Backfill from quality blocker distribution.
- Do not revive all-stability, apex-delta, width-only, or shape-margin as
  writers without addressing their failed oracle evidence.
- Do not treat shape-clean stability as a writer: it has passing oracle evidence
  but zero new product writes.
- Do not change default extraction, GUI behavior, workbook schema, selected
  peak/area, counted detection, or primary matrix semantics without a public
  contract and expected-diff.
