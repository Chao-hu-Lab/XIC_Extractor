# P2b Revised AsLS Promotion Gate Note

**Date:** 2026-05-25
**Gate status:** `GO_FOR_PRODUCTION_CANDIDATE`
**Superseded detail:** The latest gate semantics are recorded in
`docs/superpowers/notes/2026-05-25-p2d-rt-boundary-first-p2b-gate-note.md`.
This note is retained as the earlier baseline-truth-only gate record.

## Decision

The old P2b strict RSD comparator remains `NO-GO` as a hard blocker because it
treats linear-edge area as truth. The revised P2b gate supersedes that hard
blocker and treats `area_rsd_regression` as accepted review evidence when the
baseline truth audit classifies the discrepancy as
`linear_edge_over_subtraction_plausible`.

Current 8RAW revised-gate result:

- overall status: `GO_FOR_PRODUCTION_CANDIDATE`
- target count: 6
- hard blocker count: 0
- accepted review count: 3
- global blockers: none
- P4 unexplained area mismatch count: 0
- P4 integration context incomplete count: 0

This note does not switch production `area_baseline_corrected` to AsLS. It
only records that P2b may proceed from old-gate NO-GO into an 8RAW
production-candidate promotion path.

Follow-up all-status baseline truth audit:
`docs/superpowers/notes/2026-05-25-p2-baseline-truth-audit-all-statuses-note.md`.
That audit included old P2 `PASS` rows and found the same
`linear_edge_over_subtraction_plausible` pattern with no AsLS raw-area
overshoot rows.

## Command

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2b_asls_promotion_gate --p2-gate-rows-tsv output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --baseline-truth-summary-tsv output\phase1_p2_baseline_truth_audit\baseline_truth_audit_summary.tsv --area-uncertainty-summary-tsv output\phase1_p4_area_uncertainty_formula\diagnostics\area_integration_uncertainty\area_integration_uncertainty_summary.tsv --output-dir output\phase1_p2b_revised_asls_promotion_gate
```

Result: exit `0`.

## Artifacts

- Rows: `output/phase1_p2b_revised_asls_promotion_gate/p2b_asls_promotion_gate_rows.tsv`
- Summary: `output/phase1_p2b_revised_asls_promotion_gate/p2b_asls_promotion_gate_summary.tsv`
- JSON: `output/phase1_p2b_revised_asls_promotion_gate/p2b_asls_promotion_gate.json`
- Report: `output/phase1_p2b_revised_asls_promotion_gate/p2b_asls_promotion_gate.md`

## Revised Row Decisions

| Target | Family | Old status | Revised status | Reason |
|---|---|---|---|---|
| d3-5-hmdC | FAM000153 | FAIL | ACCEPTED_REVIEW | baseline truth supports linear-edge over-subtraction |
| d3-5-medC | FAM000031 | PASS | PASS | old gate already passed; all-status truth audit also supports linear-edge over-subtraction |
| d4-N6-2HE-dA | FAM000807 | FAIL | ACCEPTED_REVIEW | baseline truth supports linear-edge over-subtraction |
| 15N5-8-oxodG | FAM000538 | PASS | PASS | old gate already passed; all-status truth audit also supports linear-edge over-subtraction |
| d3-N6-medA | FAM000242 | PASS | PASS | old gate already passed; all-status truth audit also supports linear-edge over-subtraction |
| d3-dG-C8-MeIQx | FAM001878 | FAIL | ACCEPTED_REVIEW | baseline truth supports linear-edge over-subtraction |

## Remaining Limits

- This is an 8RAW `production_candidate` gate, not `production_ready`.
- 85RAW has not been rerun in this worktree.
- Production `area_baseline_corrected` remains linear-edge until a separate
  production-switch plan lands or the owner explicitly accepts the 8RAW
  candidate evidence as sufficient for the switch.
- Cleanup can no longer treat P2b as terminally blocked, but it still must not
  assume AsLS production has already happened.
