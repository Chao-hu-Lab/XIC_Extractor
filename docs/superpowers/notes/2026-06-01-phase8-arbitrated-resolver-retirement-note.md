# Phase 8 Arbitrated Resolver Retirement Note

Status: `C2_ARBITRATED_RESOLVER_RETIRED`

Verdict:

- `arbitrated` is no longer an accepted production resolver mode.
- Old public behavior is rejection, not aliasing:
  `arbitrated resolver mode is retired; use region_first_safe_merge`.
- `legacy_savgol`, `local_minimum`, and `region_first_safe_merge` remain
  accepted. This phase does not demote `legacy_savgol`.
- The C2 one-shot 8RAW comparison did not show `arbitrated` materially
  outperforming the supported path, so the phase is not blocked by
  `BLOCKED_BY_ARBITRATED_BETTER`.

Implementation summary:

- Removed `arbitrated` from `RESOLVER_MODES`, GUI mode choices, CLI resolver
  choices, and config descriptions.
- Config loading rejects `resolver_mode=arbitrated` with the migration message.
- `scripts.run_alignment`, `scripts.run_discovery`, and
  `scripts.validation_harness` reject CLI `--resolver-mode arbitrated`.
- `scripts.validation_harness_core.build_validation_specs` rejects direct
  programmatic `resolver_mode="arbitrated"` input.
- `find_peak_candidates` rejects manually constructed configs whose
  `resolver_mode` is `arbitrated`.
- Deleted the `arbitrated` dispatch branch and its private merge helpers.
  `_combine_proposal_sources` remains because preferred-RT recovery still uses
  it.

8RAW preflight and run:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\cleanup_retirement_phase8_resolver_retirement\supported_region_first_safe_merge --expected-sample-count 8 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --resolver-mode region_first_safe_merge --timing-output output\cleanup_retirement_phase8_resolver_retirement\supported_region_first_safe_merge\timing.json --timing-live-output output\cleanup_retirement_phase8_resolver_retirement\supported_region_first_safe_merge\timing.live.json
```

Observed result: preflight OK; run exit code `0`.

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\cleanup_retirement_phase8_resolver_retirement\arbitrated --expected-sample-count 8 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --resolver-mode arbitrated --timing-output output\cleanup_retirement_phase8_resolver_retirement\arbitrated\timing.json --timing-live-output output\cleanup_retirement_phase8_resolver_retirement\arbitrated\timing.live.json
```

Observed result: preflight OK; run exit code `0`.

Artifact hashes:

| Artifact | supported `region_first_safe_merge` | `arbitrated` |
| --- | --- | --- |
| `alignment_matrix.tsv` | `FD6F11A03084CCBE3685DB3F3D997497ACE408B18E743D6DA2EB91837E443FC8` | `4CF18A24FE26300C3F4C41B5E1540BAED632B03753E9C971D71EB862F357701B` |
| `alignment_review.tsv` | `6DD0DE5C80A6E5E7BDCFA00C70ABEC393AB16F152E8D1B4DC2F471E3A33DA2DD` | `C6B0716E416C4DEDC0F3DE7628ACBA3FF120E737DEFD01BF64A6A9B4E6A1FC1A` |
| `alignment_cells.tsv` | `4EDD5846AB77C714AD565BB8BF5C77925B0CE8E441817C75717F3996C3C6C2CA` | `71EE41F42B17407A63E35B0A717BA92CA079E2E304A0CB3A688CC978DE6A6B3E` |

Strict ISTD benchmark:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.targeted_istd_benchmark --targeted-workbook local_validation_artifacts\targeted_gt_workbooks\8raw\xic_results_20260512_1151.xlsx --alignment-dir output\cleanup_retirement_phase8_resolver_retirement\supported_region_first_safe_merge --output-dir output\cleanup_retirement_phase8_resolver_retirement\diagnostics\targeted_istd_benchmark_supported

.venv\Scripts\python.exe -m tools.diagnostics.targeted_istd_benchmark --targeted-workbook local_validation_artifacts\targeted_gt_workbooks\8raw\xic_results_20260512_1151.xlsx --alignment-dir output\cleanup_retirement_phase8_resolver_retirement\arbitrated --output-dir output\cleanup_retirement_phase8_resolver_retirement\diagnostics\targeted_istd_benchmark_arbitrated
```

Observed result:

| Mode | Overall status | Active fail count | Fail count |
| --- | --- | ---: | ---: |
| supported | `FAIL` | 4 | 4 |
| arbitrated | `FAIL` | 4 | 4 |

Status-level comparison:

- No target changes from `FAIL` to `PASS` under `arbitrated`.
- No target changes from `PASS` to `FAIL` under `arbitrated`.
- `d3-5-medC` worsens in the arbitrated run:
  `log_area_spearman` `0.8571428571428571 -> 0.8333333333333334`.
- The other status-changing candidates are family-id changes without status
  improvement.

Scan evidence:

```powershell
rg -n "arbitrated" xic_extractor gui scripts tests -g "*.py"
```

Observed result:

- Hits are limited to retired-input rejection checks, rejection tests, and the
  retired-mode description.

```powershell
rg -n "_find_peak_candidates_arbitrated|_merge_resolver_candidates|_matching_merge_index|_merged_candidate|_material_boundary_disagreement|_candidate_detail_score|_source_apex_rank|_max_result_smoothed|_strongest_failure_result|_BOUNDARY_MERGE_TOLERANCE" xic_extractor tests
```

Observed result: no hits.

Focused verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\facade.py xic_extractor\peak_detection\recovery.py xic_extractor\settings_schema.py xic_extractor\configuration\settings.py gui\sections\settings_resolver_panel.py gui\sections\settings_advanced_panel.py scripts\run_alignment.py scripts\run_discovery.py scripts\validation_harness.py scripts\validation_harness_core.py tests\test_config.py tests\test_signal_processing.py tests\test_signal_processing_selection.py tests\test_settings_section_advanced.py tests\test_run_alignment.py tests\test_run_discovery.py tests\test_validation_harness.py tests\test_cwt_proposals.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_table.py tests\test_peak_hypotheses.py tests\test_cwt_peak_candidate_audit.py tests\test_peak_candidate_score_calibration_report.py tests\test_cross_report_evidence_consistency.py tests\test_targeted_nl_dropout_root_cause_audit.py tests\test_targeted_peak_reliability_audit.py
```

Observed result: `All checks passed!`

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_config.py tests\test_signal_processing.py tests\test_signal_processing_selection.py tests\test_settings_section_advanced.py tests\test_run_alignment.py tests\test_run_discovery.py tests\test_validation_harness.py tests\test_cwt_proposals.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_table.py tests\test_peak_hypotheses.py tests\test_cwt_peak_candidate_audit.py tests\test_peak_candidate_score_calibration_report.py tests\test_cross_report_evidence_consistency.py tests\test_targeted_nl_dropout_root_cause_audit.py tests\test_targeted_peak_reliability_audit.py
```

Observed result: `316 passed, 6 warnings`.
