# P2 AsLS Baseline Shadow Validation Note

**Date:** 2026-05-25
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** diagnostic_only

## Decision

- P2 AsLS shadow decision: the original strict RSD comparator produced a NO-GO under the initial P2 validation contract, but the follow-up baseline truth audit reclassified the failure as a gate-semantics issue.
- Current decision after baseline truth audit: P2 is `shadow_ready` for P3 entry, but not eligible for P2b production promotion.
- Reason: strict ISTD AsLS area RSD regressed beyond the +0.3 absolute percentage-point threshold for 3 of 6 active selected ISTDs.
- Production `area_baseline_corrected` remains linear-edge.
- No `area_baseline_corrected_asls > area` violation was observed, so the current evidence does not point to a raw-area clipping bug in the AsLS integration function.
- P2b is not eligible. Cleanup must not assume AsLS production.

## Artifacts

- Alignment: `output/phase1_p2_asls_shadow_validation/alignment/asls_shadow/`
- Targeted ISTD benchmark: `output/phase1_p2_asls_shadow_validation/diagnostics/targeted_istd_benchmark/`
- P2 AsLS shadow gate: `output/phase1_p2_asls_shadow_validation/diagnostics/p2_asls_shadow_gate/`
- Baseline truth audit: `output/phase1_p2_baseline_truth_audit/`
- Area integration uncertainty: not rerun in the baseline truth audit pass; still required before any P2b promotion decision.

## Gate Results

| Gate | Result | Evidence |
|---|---|---|
| 8RAW AsLS shadow alignment | PASS | `scripts.run_alignment` exited `0`; wrote `alignment_cell_integration_audit.tsv`, `alignment_matrix.tsv`, and validation artifacts under `output/phase1_p2_asls_shadow_validation/alignment/asls_shadow/` |
| AsLS shadow columns emitted | PASS | `alignment_cell_integration_audit.tsv` header includes `area_baseline_corrected_asls` and `baseline_score_asls` |
| Strict ISTD benchmark | PASS | `targeted_istd_benchmark_summary.tsv`: 7 rows, all `status=PASS`, active ISTD FAIL count `0` |
| P2 AsLS shadow gate | FAIL | `p2_asls_shadow_gate_summary.tsv`: `overall_status=FAIL`, `failed_count=3`, `target_count=6`, `max_area_rsd_delta_pct=3.85879`, `max_asls_exceeds_raw_area_count=0` |
| Baseline truth audit | PASS for P3-entry decision evidence | `baseline_truth_audit_summary.tsv`: all three failed families classified as `linear_edge_over_subtraction_plausible`; median outside background `%` is `0`; no AsLS area exceeds raw |
| Area integration uncertainty | PENDING FOR PROMOTION | Not rerun in the baseline truth audit pass. Required before P2b, not required for P3 shadow entry. |

## P2 AsLS Shadow Gate Detail

| Target | Feature | Linear RSD % | AsLS RSD % | Delta pp | Status | Reason |
|---|---|---:|---:|---:|---|---|
| d3-5-hmdC | FAM000153 | 11.2581 | 15.1169 | 3.85879 | FAIL | `area_rsd_regression` |
| d4-N6-2HE-dA | FAM000807 | 20.9301 | 21.5008 | 0.57078 | FAIL | `area_rsd_regression` |
| d3-dG-C8-MeIQx | FAM001878 | 34.1104 | 34.8789 | 0.768493 | FAIL | `area_rsd_regression` |
| d3-5-medC | FAM000031 | 12.4246 | 8.38456 | -4.04001 | PASS |  |
| 15N5-8-oxodG | FAM000538 | 26.3116 | 21.4884 | -4.82317 | PASS |  |
| d3-N6-medA | FAM000242 | 19.3121 | 19.5509 | 0.238792 | PASS |  |

## Commands

- Alignment:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p2_asls_shadow_validation\alignment\asls_shadow --output-level validation --resolver-mode region_first_safe_merge --emit-alignment-cells --emit-alignment-integration-audit --emit-baseline-audit-asls --raw-workers 1 --raw-xic-batch-size 1`
  Result: exit code `0`
- Targeted ISTD benchmark:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.targeted_istd_benchmark --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx --alignment-dir output\phase1_p2_asls_shadow_validation\alignment\asls_shadow --output-dir output\phase1_p2_asls_shadow_validation\diagnostics\targeted_istd_benchmark`
  Result: exit code `0`
- P2 AsLS shadow gate:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2_asls_shadow_gate --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv --targeted-istd-benchmark-summary-tsv output\phase1_p2_asls_shadow_validation\diagnostics\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv --output-dir output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate`
  Result: exit code `1`
- Baseline truth audit:
  `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2_baseline_truth_audit --p2-gate-rows-tsv output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p2_baseline_truth_audit`
  Result: exit code `0`

## Remaining Real-Data Risk

- 85RAW not run.
- P2 remains shadow-only. The original 8RAW strict ISTD RSD comparator still fails, but the baseline truth audit shows the comparator is probably protecting biased linear-edge areas for the three failed families.
- AsLS parameter tuning, alternate baseline methods, or revised promotion criteria would need a new reviewed plan before any further implementation.

## Post-Implementation Review

- Read-only reviewer confirmed the current P2 result is a valid `diagnostic_only` NO-GO, not an implementation bug.
- Reviewer coverage risk was fixed and the real-data P2 gate was rerun. All six active selected ISTDs still have `sample_count=8`; no `shadow_coverage_incomplete` was added.
- Current failure remains the strict AsLS RSD contract: `area_rsd_regression` for `d3-5-hmdC`, `d4-N6-2HE-dA`, and `d3-dG-C8-MeIQx`.
- Follow-up baseline truth audit changed the decision framing: the `area_rsd_regression` rows are no longer treated as terminal P3-entry blockers because all three failed families show low outside background and plausible linear-edge over-subtraction.
