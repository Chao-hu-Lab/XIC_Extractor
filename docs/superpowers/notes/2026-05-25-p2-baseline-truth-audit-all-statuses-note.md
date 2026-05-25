# P2 Baseline Truth Audit All Statuses Note

**Date:** 2026-05-25
**Gate status:** `diagnostic_only`

## Decision

The baseline truth audit was rerun on both old P2 gate `FAIL` and `PASS`
selected ISTD families. The originally passing families showed the same
dominant pattern as the failing families: linear-edge area subtraction is
plausibly too aggressive, while AsLS stays below raw area and does not show a
raw-area overshoot blocker.

This strengthens the revised P2b interpretation: old P2 `PASS` means the strict
RSD comparator did not flag the row, not that linear-edge area is the better
baseline truth.

## Command

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2_baseline_truth_audit --p2-gate-rows-tsv output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p2_baseline_truth_audit_all_statuses --include-gate-status FAIL --include-gate-status PASS
```

Result: exit `0`; `48` rows and `6` families.

## Artifacts

- Rows: `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit_rows.tsv`
- Summary: `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit_summary.tsv`
- JSON: `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit.json`
- Report: `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit.md`
- Plots: `output/phase1_p2_baseline_truth_audit_all_statuses/plots/`

## Summary

| Target | Family | Old P2 status | Review status | Median linear subtraction % | Median AsLS subtraction % | Max AsLS vs linear % |
|---|---|---:|---|---:|---:|---:|
| 15N5-8-oxodG | FAM000538 | PASS | linear_edge_over_subtraction_plausible | 9.68265 | 0.297963 | 41.7365 |
| d3-5-hmdC | FAM000153 | FAIL | linear_edge_over_subtraction_plausible | 8.85423 | 0.264858 | 26.4931 |
| d3-5-medC | FAM000031 | PASS | linear_edge_over_subtraction_plausible | 15.6723 | 0.239676 | 36.3731 |
| d3-N6-medA | FAM000242 | PASS | linear_edge_over_subtraction_plausible | 17.7809 | 0.460796 | 28.9706 |
| d3-dG-C8-MeIQx | FAM001878 | FAIL | linear_edge_over_subtraction_plausible | 16.6737 | 0.365767 | 31.7657 |
| d4-N6-2HE-dA | FAM000807 | FAIL | linear_edge_over_subtraction_plausible | 7.52874 | 0.334466 | 17.2492 |

Additional check: no row had `asls_raw_pct > 100.0`.

## Interpretation

The PASS families are not counterexamples to AsLS. They show a stable linear
edge over-subtraction pattern that the old RSD gate did not treat as a failure.
This explains why a strict RSD-only comparator is too narrow: it can miss stable
linear-edge bias and can mislabel AsLS as worse when AsLS is closer to the
chromatogram baseline evidence.

This note does not switch production area integration to AsLS. It only records
additional diagnostic evidence for the revised P2b gate.
