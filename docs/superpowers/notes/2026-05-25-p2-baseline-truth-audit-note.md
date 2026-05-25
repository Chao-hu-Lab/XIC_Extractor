# P2 Baseline Truth Audit Note

**Date:** 2026-05-25
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** diagnostic_only

## Decision

- Baseline truth audit status: 8RAW diagnostic evidence generated for the three P2 AsLS shadow gate failures.
- The failures are now classified as `linear_edge_over_subtraction_plausible`, not as an AsLS raw-area bug.
- P2 AsLS remains shadow-only.
- This audit does not promote AsLS and does not change production `area_baseline_corrected`.
- P2b is still not eligible; production promotion needs later P2/P3/P4 evidence.

## Artifacts

- Rows: `output/phase1_p2_baseline_truth_audit/baseline_truth_audit_rows.tsv`
- Summary: `output/phase1_p2_baseline_truth_audit/baseline_truth_audit_summary.tsv`
- Report: `output/phase1_p2_baseline_truth_audit/baseline_truth_audit.md`
- Plots: `output/phase1_p2_baseline_truth_audit/plots/`

## Findings

| Target | Family | Dominant classification | Median linear subtraction % | Median AsLS subtraction % | Median outside background % | Review interpretation |
|---|---|---|---:|---:|---:|---|
| d3-5-hmdC | FAM000153 | linear_edge_over_subtraction_plausible | 8.85423 | 0.264858 | 0 | 6/8 cells show linear-edge over-subtraction; 2/8 methods are similar. Plots show low outside background, so the linear-edge difference is likely from peak-shoulder subtraction. |
| d4-N6-2HE-dA | FAM000807 | linear_edge_over_subtraction_plausible | 7.52874 | 0.334466 | 0 | 8/8 cells show the same pattern: AsLS stays near the external baseline while linear-edge subtracts across the peak shoulder. |
| d3-dG-C8-MeIQx | FAM001878 | linear_edge_over_subtraction_plausible | 16.6737 | 0.365767 | 0 | 8/8 cells show the strongest old-method bias. Linear-edge subtracts 15-24% in several samples while the outside background remains low. |

## Interpretation

The original P2 gate treated `area_baseline_corrected_asls` as suspicious when
it diverged from linear-edge or increased strict ISTD RSD by more than +0.3
percentage points. The truth audit shows that this assumption is too strong:
for the three failed families, the old linear-edge comparator is probably
underestimating the true area by drawing a baseline through the peak shoulder.

This means the prior P2 NO-GO is better understood as a gate-semantics problem,
not an AsLS implementation failure.

## Next Recommendation

Recommendation: `revise_p2_gate_semantics`.

The P2 gate should keep hard failures for `area_baseline_corrected_asls > area`,
missing coverage, or non-reproducible trace extraction. Area RSD regression
against linear-edge should remain decision evidence, but it should not be a
terminal blocker when baseline truth audit evidence classifies the discrepancy
as `linear_edge_over_subtraction_plausible`.
