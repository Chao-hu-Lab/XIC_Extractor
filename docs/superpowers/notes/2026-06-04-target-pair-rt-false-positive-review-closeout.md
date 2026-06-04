# Target Pair RT False-Positive Review Closeout

**Date:** 2026-06-04
**Readiness label:** `shadow_ready`
**Scope:** target-pair RT auto-reselection false-positive review surface

## Verdict

The target-pair auto-reselection path is not ready for broad automatic product
promotion.

The false-positive watch table is now useful enough for the next decision: it
separates candidate-switch rows into row-specific approval candidates versus
rows that need false-positive review because paired analyte/ISTD area ratio does
not match the run reference.

Single MS2/NL contradiction is intentionally not a hard veto when paired RT and
paired area ratio support the candidate. It remains a review reason because DDA
opportunity can be sparse and NL absence must not dominate the evidence chain.

## Code / Contract Change

`target_pair_rt_auto_reselection.tsv` now includes:

```text
false_positive_review_status
false_positive_review_reasons
```

Status meanings:

```text
row_approval_candidate
false_positive_review_required
product_switch_accepted
not_applicable
```

Hard false-positive review is currently triggered by:

```text
paired_area_ratio:outside_reference_range
paired_area_ratio:inconclusive
paired_area_ratio:missing_*
paired_analyte_missing_credible_istd
unpaired_analyte
```

MS2/NL states are review reasons, not standalone hard vetoes:

```text
ms2_nl_contradicted
dda_missing_ms2_not_observed
```

## 8RAW Review Run

Calibration bootstrap:

```text
output/target_pair_rt_false_positive_review_20260604/target_pair_rt_calibration_review_bootstrap.tsv
```

This is a bounded review bootstrap, not a broad product calibration artifact.
It uses current `config/targets.csv` hash `f858bd9c`. It does not replace the
future Mix STDs / biological-transfer calibration producer.

Final output root:

```text
output/target_pair_rt_false_positive_review_20260604/row_approval_watch_8raw_final2/tissue_8raw_region_first_safe_merge/
```

Primary artifacts:

```text
target_pair_rt_auto_reselection.tsv
target_pair_rt_auto_reselection_summary.tsv
peak_candidates.tsv
xic_results_serial_w1.xlsx
```

Command:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir . --output-root output\target_pair_rt_false_positive_review_20260604 --run-id row_approval_watch_8raw_final2 --resolver-mode region_first_safe_merge --parallel-mode serial --parallel-workers 1 --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --setting emit_peak_candidates=true --setting target_pair_rt_calibration_path=C:\Users\user\Desktop\XIC_Extractor\output\target_pair_rt_false_positive_review_20260604\target_pair_rt_calibration_review_bootstrap.tsv
```

Observed:

```text
tissue-8raw: passed
compare=not_requested
```

## Summary

```text
limited_evidence_shadow_count=56
inconclusive_count=16
shadow_auto_reselect_proposed_count=10
changed_row_denominator=10
false_positive_review_required_count=5
row_approval_candidate_count=5
product_switch_allowed_true_count=0
auto_reselected_count=0
paired_area_ratio_within_reference_count=25
paired_area_ratio_outside_reference_count=10
paired_area_ratio_inconclusive_count=3
false_positive_strata=dda_missing_ms2_not_observed;ms2_nl_contradicted;paired_area_ratio:missing_candidate_area;paired_area_ratio:outside_reference_range;row_specific_expected_diff_required;selected_candidate_lookup_missing
```

## Row-Approval Candidates

These rows have a candidate switch proposal, paired area ratio within the run
reference range, and only row-specific approval / DDA-MS2 review reasons:

| sample | target | area ratio | MS2/NL | reasons |
|---|---:|---:|---|---|
| `BenignfatBC1055_DNA` | `8-oxodG` | `0.49834` | `contradicted` | `ms2_nl_contradicted;row_specific_expected_diff_required` |
| `Breast_Cancer_Tissue_pooled_QC3` | `8-oxo-Guo` | `0.01395` | `contradicted` | `ms2_nl_contradicted;row_specific_expected_diff_required` |
| `Breast_Cancer_Tissue_pooled_QC5` | `8-oxo-Guo` | `0.01176` | `contradicted` | `ms2_nl_contradicted;row_specific_expected_diff_required` |
| `Breast_Cancer_Tissue_pooled_QC5` | `dG-C8-MeIQx` | `0.05712` | `not_observed` | `dda_missing_ms2_not_observed;row_specific_expected_diff_required` |
| `NormalBC2263_DNA` | `dG-C8-MeIQx` | `0.04351` | `not_observed` | `dda_missing_ms2_not_observed;row_specific_expected_diff_required` |

## False-Positive Review Required

These rows should not be row-approved without plot/manual review because the
paired analyte/ISTD area ratio is outside the run reference range or the
selected successor candidate cannot be joined back to the emitted candidate
table:

| sample | target | area ratio | MS2/NL | reasons |
|---|---:|---:|---|---|
| `BenignfatBC1055_DNA` | `dG-C8-MeIQx` |  | `not_observed` | `selected_candidate_lookup_missing;paired_area_ratio:missing_candidate_area;dda_missing_ms2_not_observed;row_specific_expected_diff_required` |
| `BenignfatBC1151_DNA` | `8-oxodG` |  | `contradicted` | `selected_candidate_lookup_missing;paired_area_ratio:missing_candidate_area;ms2_nl_contradicted;row_specific_expected_diff_required` |
| `Breast_Cancer_Tissue_pooled_QC5` | `8-oxodG` | `0.00385` | `not_observed` | `paired_area_ratio:outside_reference_range;dda_missing_ms2_not_observed;row_specific_expected_diff_required` |
| `NormalBC2312_DNA` | `8-oxodG` | `0.00174` | `contradicted` | `paired_area_ratio:outside_reference_range;ms2_nl_contradicted;row_specific_expected_diff_required` |
| `TumorBC2312_DNA` | `8-oxo-Guo` | `0.00397` | `contradicted` | `paired_area_ratio:outside_reference_range;ms2_nl_contradicted;row_specific_expected_diff_required` |

## Review Finding Resolved

Implementation-contract review found one blocking schema-risk: when the selected
successor candidate ID could not be joined back to `peak_candidates.tsv`, the
watch table fell back to the legacy reported RT/area. That made
`selected_candidate_rt` and paired area ratio look more certain than they were.

The writer now fails closed for those rows: selected candidate RT/area are left
blank, `paired_area_ratio_status=missing_candidate_area`, and the row is marked
`false_positive_review_required` with `selected_candidate_lookup_missing`.
The final2 8RAW rerun confirms this behavior for:

```text
BenignfatBC1055_DNA / dG-C8-MeIQx
BenignfatBC1151_DNA / 8-oxodG
```

## Next Decision

Do not broadly enable automatic target-pair reselection yet.

The next bounded product step is to allow row-specific approval generation only
for `row_approval_candidate` rows after plot/manual review confirms the selected
peak is not a false pick. Rows marked `false_positive_review_required` should
remain blocked until the plot/manual review explains the area-ratio outlier.

Future broad automation needs a real calibration producer from Mix STDs or
biological-transfer evidence. This run used a review bootstrap only to exercise
the watch table on 8RAW.
