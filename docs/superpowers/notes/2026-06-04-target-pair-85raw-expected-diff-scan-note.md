# Target Pair 85RAW Expected-Diff Scan Note

**Date:** 2026-06-04
**Validation status:** `run_ok`; candidate discovery evidence only
**Scope:** targeted extraction 85RAW, target-pair expected-diff review surface

## Verdict

The targeted 85RAW scan confirms that the 8RAW subset was not representative
enough for target-pair expected-diff behavior. The full 85RAW set exposes many
more row-specific candidates similar in shape to the reviewed
`BenignfatBC1055_DNA / 8-oxodG` case.

This does not make broad auto-reselection production-ready. Product mutation
remains fail-closed: only the explicitly approved `BenignfatBC1055_DNA /
8-oxodG` row entered product behavior in this run.

## Run

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-85raw --base-dir . --output-root output\target_pair_rt_production_ready_20260604 --run-id target_pair_85raw_expected_diff_scan --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 4 --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --setting emit_peak_candidates=true --setting target_pair_rt_calibration_path=C:\Users\user\Desktop\XIC_Extractor\output\target_pair_rt_false_positive_review_20260604\target_pair_rt_calibration_review_bootstrap.tsv --setting model_selection_expected_diff_approval_registry=C:\Users\user\Desktop\XIC_Extractor\output\target_pair_rt_production_ready_20260604\bc1055_row_approval\model_selection_expected_diff_approvals.tsv --confirm-full-run
```

Observed:

```text
suite=tissue-85raw
raw_count=85
status=passed
parallel_mode=process
parallel_workers=4
output=xic_results_process_w4.xlsx
```

Note: `validation_summary.csv` records the harness-reconstructed command
(`uv run python scripts\validation_harness.py ...`). The actual executed command
used the documented RAW runner `.venv\Scripts\python.exe`.

Primary output:

```text
output/target_pair_rt_production_ready_20260604/target_pair_85raw_expected_diff_scan/tissue_85raw_region_first_safe_merge/xic_results_process_w4.xlsx
```

Review table:

```text
output/target_pair_rt_production_ready_20260604/target_pair_85raw_expected_diff_scan/target_pair_row_approval_candidates_review.tsv
```

## Product Guardrail

```text
product_switch_allowed_true_count=1
auto_reselected_count=1
product_switch_accepted_count=1
accepted_row=BenignfatBC1055_DNA / 8-oxodG
```

No other row entered product auto-reselection.

## Candidate Discovery

```text
limited_evidence_shadow_count=595
shadow_auto_reselect_proposed_count=115
auto_reselect_blocked_count=431
changed_row_denominator=116
row_approval_candidate_count=85
false_positive_review_required_count=30
```

Row-approval candidates by target:

| Target | Candidate rows |
| --- | ---: |
| 8-oxo-Guo | 24 |
| 8-oxodG | 22 |
| dG-C8-MeIQx | 15 |
| 5-hmdC | 13 |
| 5-medC | 7 |
| N6-HE-dA | 4 |

Row-approval candidates by MS2/NL explanation:

| Explanation | Candidate rows |
| --- | ---: |
| `ms2_nl_contradicted` | 46 |
| `dda_missing_ms2_not_observed` | 22 |
| expected-diff only | 17 |

False-positive review rows:

```text
false_positive_review_required_count=30
```

These remain manual review / false-positive audit rows, especially when candidate
lookup is missing, paired-area evidence is missing, or paired-area ratio is
outside reference.

## Workbook Surface

The 85RAW workbook uses the cleaned product surface:

```text
Confidence: hidden
Reason: visible
Product State: visible
Counted Detection: visible
Review State: visible
Projection Reason: hidden technical detail
```

Visible product interpretation is therefore projection-first. Legacy
`Confidence`, score, and caps remain technical audit evidence, not product
authority.

## Follow-Up

The next production step is not to approve all 85 rows. The next step is to
select representative review rows from the 85 candidates, generate EIC/MS2
plots, and decide which rows qualify for explicit row-specific approval.
