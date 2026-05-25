# P4 Area Uncertainty Formula Validation Note

Gate status: `audit_only`.

Formula version: `baseline_residual_mad_v1`.

## Verification

- Unit tests:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py tests\test_alignment_tsv_writer.py tests\test_area_integration_uncertainty_audit.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py -q`
  passed: `60 passed`.
- Broader P2/P4 safety set:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_alignment_pipeline_outputs.py tests\test_alignment_process_backend.py tests\test_alignment_tsv_writer.py tests\test_baseline_integration.py tests\test_p2_asls_shadow_gate.py tests\test_p2_baseline_truth_audit.py tests\test_area_integration_uncertainty_audit.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py -q`
  passed: `96 passed`.
- Compile smoke:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m py_compile xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\hypotheses.py xic_extractor\alignment\tsv_writer.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py tools\diagnostics\area_integration_uncertainty_audit.py`
  passed.
- 8RAW alignment rerun:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p2_asls_shadow_validation\alignment\asls_shadow --output-level validation --resolver-mode region_first_safe_merge --emit-alignment-cells --emit-alignment-integration-audit --emit-baseline-audit-asls --raw-workers 1 --raw-xic-batch-size 1`
  exited `0`.
- TSV provenance check:
  `alignment_cell_integration_audit.tsv` header includes
  `area_uncertainty_formula_version`, `baseline_residual_mad`, and
  `area_uncertainty_noise_source`.
  All `16966` integration audit rows had formula version
  `baseline_residual_mad_v1`; all had noise source `asls_residual`; empty
  `area_uncertainty` count was `0`.
- Post-implementation review fix:
  targeted `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` also emit
  `area_uncertainty_formula_version`, `baseline_residual_mad`, and
  `area_uncertainty_noise_source` because they already expose
  `area_uncertainty` from the same helper.
- 8RAW targeted candidate rerun:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m scripts.validation_harness --suite tissue-8raw --output-root output\phase1_p1_resolver_default_validation\targeted --run-id region_first_safe_merge --resolver-mode region_first_safe_merge --setting emit_peak_candidates=true --setting keep_intermediate_csv=true`
  exited `0`. The refreshed `peak_candidates.tsv` had `172` rows and
  `peak_candidate_boundaries.tsv` had `529` rows; all rows used
  `baseline_residual_mad_v1`.
- 8RAW evidence-spine rerun:
  `output/phase1_p4_area_uncertainty_formula/diagnostics/evidence_spine_consistency/`
  wrote `72` rows; `56` matched, `36` consistent, `16` missing alignment
  rows, and focused labels remained `15N5-8-oxodG;d3-N6-medA;5-medC;5-hmdC`.
- 8RAW area uncertainty audit:
  `output/phase1_p4_area_uncertainty_formula/diagnostics/area_integration_uncertainty/`
  wrote `72` rows with bucket counts
  `area_consistent_low_uncertainty:36;label_only_mismatch:20;missing_alignment_match:16`.
  `unexplained_area_mismatch_count` remained `0`.
- P2 shadow gate rerun after the P4 alignment rewrite:
  targeted ISTD benchmark exited `0`; `p2_asls_shadow_gate` exited `1` with
  `overall_status=FAIL`, `failed_count=3`, `max_asls_exceeds_raw_area_count=0`,
  and `max_rsd_regression_pct=0.3`. This is the existing P2b blocker, not a
  P4 production-area regression.

## Decision

P4 is accepted as `audit_only`: the formula correction is implemented,
provenance is TSV-local, and the 8RAW area uncertainty diagnostic still has
`unexplained_area_mismatch_count=0`.

P4 does not change production area, scoring, alignment, matrix identity, P2b,
or Cleanup readiness. P2b remains blocked by the separate AsLS shadow gate
decision.
