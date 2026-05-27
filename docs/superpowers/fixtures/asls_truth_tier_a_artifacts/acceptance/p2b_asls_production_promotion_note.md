# P2b AsLS Conditional Audit Promotion Note

Date: 2026-05-26

## Verdict

`conditional_audit_promotion` for `alignment_cell_integration_audit.tsv`
baseline reporting.

This is not proof that AsLS is the more accurate absolute baseline estimator.
The current promotion is limited to the integration-audit baseline field and
does not change final matrix quantification.

This note supersedes older wording that called the result a
`production_candidate`. That term is now too broad because P2b validated
identity/RT/boundary hard blockers and final-matrix equivalence, not
spike-in recovery, concentration-series linearity, blank behavior, or another
truth-validation contract for baseline accuracy.

## Implemented Contract

- `baseline_integration_method` is now the integration-audit baseline selector.
- Default integration-audit method is `asls`.
- Rollback method is `linear_edge`.
- Default `alignment_cell_integration_audit.tsv` reports
  `area_baseline_corrected` with `baseline_type=asls`.
- Default audit schema includes temporary rollback fields
  `area_baseline_corrected_linear_edge` and `baseline_score_linear_edge`.
- Legacy P2 shadow reruns remain available: `--emit-baseline-audit-asls`
  preserves linear-edge production output and emits
  `area_baseline_corrected_asls` plus `baseline_score_asls` unless an explicit
  `--baseline-integration-method` override is supplied.
- `alignment_matrix.tsv` remains driven by accepted `cell.area`.

## Validation

Unit and contract checks:

- `python -m pytest tests\test_baseline_integration.py tests\test_config.py tests\test_run_alignment.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_tsv_writer.py tests\test_untargeted_final_matrix_contract.py tests\test_p2_asls_shadow_gate.py tests\test_p2_baseline_truth_audit.py tests\test_area_integration_uncertainty_audit.py tests\test_evidence_spine_consistency.py tests\test_p2b_asls_promotion_gate.py -q`
- Result: `208 passed`
- `py_compile` over modified production and diagnostic modules: pass

8RAW promoted-schema run:

- Command used the repo virtual environment:
  `.venv\Scripts\python.exe -m scripts.run_alignment ... --output-level validation --resolver-mode region_first_safe_merge --emit-alignment-cells --emit-alignment-integration-audit --performance-profile validation-fast`
- Output:
  `output\phase1_p2b_asls_production_promotion\alignment\8raw_asls_production`
- Wall time: about `163 s`
- First attempt with system `python` failed because that interpreter did not
  have `pythonnet`; rerun with `.venv\Scripts\python.exe` succeeded.

Promoted audit schema check:

- `alignment_cell_integration_audit.tsv` header includes
  `area_baseline_corrected_linear_edge`.
- It does not include the legacy shadow column `area_baseline_corrected_asls`.
- Sample rows report `baseline_type=asls`.

Final matrix equivalence:

- Promoted run `alignment_matrix.tsv` SHA256:
  `24B246A48488F05017D19B44C5EBF14645DCAE667957B7572D3B7B40E98357F9`
- P8B 8RAW validation-minimal/super-window baseline `alignment_matrix.tsv`
  SHA256:
  `24B246A48488F05017D19B44C5EBF14645DCAE667957B7572D3B7B40E98357F9`
- Conclusion: final matrix output is byte-identical to the accepted P8B
  baseline.

Diagnostics:

- Evidence spine summary:
  `output\phase1_p2b_asls_production_promotion\diagnostics\evidence_spine_consistency\evidence_spine_consistency_summary.tsv`
  - rows checked: `72`
  - matched rows: `56`
  - consistent rows: `35`
  - missing alignment rows: `16`
- Targeted ISTD benchmark summary:
  `output\phase1_p2b_asls_production_promotion\diagnostics\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv`
  - strict benchmark still reports expected `AREA_MISMATCH` rows; this is
    diagnostic context, not a P2b hard blocker by itself.
- Area integration uncertainty:
  `output\phase1_p2b_asls_production_promotion\diagnostics\area_integration_uncertainty\area_integration_uncertainty_summary.tsv`
  - rows checked: `72`
  - `unexplained_area_mismatch_count=0`
  - `integration_context_incomplete_count=0`
  - promoted-schema rows use `baseline_area_method=linear_edge_compatible`.
- P2 AsLS gate:
  `output\phase1_p2b_asls_production_promotion\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_summary.tsv`
  - old P2 comparator status: `FAIL`
  - failed count: `2`
  - failure reason: `area_rsd_regression`
  - `max_asls_exceeds_raw_area_count=0`
- P2b promotion gate:
  `output\phase1_p2b_asls_production_promotion\diagnostics\p2b_asls_promotion_gate\p2b_asls_promotion_gate_summary.tsv`
  - overall status emitted by the current diagnostic: `GO_FOR_PRODUCTION_CANDIDATE`
  - design-correction interpretation: `conditional_audit_promotion`
  - hard blockers: `0`
  - accepted review rows: `2`
  - accepted reason: `rt_boundary_evidence_supports_area_variability`

85RAW foreground primary-delivery validation:

- Note:
  `docs\superpowers\notes\2026-05-26-p2b-85raw-foreground-validation-note.md`
- Alignment output:
  `output\phase1_p2b_85raw_formal_validation\alignment\85raw_validation_minimal_superwindow_foreground`
- Command shape:
  `.venv\Scripts\python.exe`, 85RAW discovery index with `85` rows,
  `validation-minimal`, `production-equivalent`, `audit_evidence_mode=none`,
  `validation-fast`, `super-window`, and heartbeat sidecars.
- Result: exit code `0`, shell wall-clock about `706 s`.
- Metadata confirms `baseline_integration_method=asls`,
  `output_level=validation-minimal`, `backfill_scope=production-equivalent`,
  and `owner_backfill_window_strategy=super-window`.
- `alignment_matrix.tsv`, `alignment_review.tsv`, and `alignment_cells.tsv`
  are byte-identical to the accepted P8b 85RAW super-window run.
- Targeted ISTD benchmark summary is byte-identical to the accepted P8b
  benchmark summary.
- Decision report with known exceptions:
  - verdict: `WARN`
  - matrix rows: `592`
  - samples: `85`
  - ISTD pass: `4`
  - ISTD known `AREA_MISMATCH`: `2`
  - ISTD fail: `0`

## Remaining Risk

- 85RAW primary delivery has passed with the P2b config, but
  `validation-minimal` intentionally does not emit
  `alignment_cell_integration_audit.tsv`. This note validates the matrix /
  review / cells delivery surface, not a full 85RAW integration-audit export.
- The strict targeted benchmark still surfaces area-mismatch warnings. Current
  evidence says they are not P2b hard blockers, but they remain useful review
  rows for boundary/ownership follow-up.
- The linear-edge rollback audit columns are temporary promotion aids. Cleanup
  should remove or formalize them only after downstream consumers, 85RAW, and
  AsLS truth-validation requirements are reviewed.
- Linear-edge retirement is still blocked. P2b does not authorize deleting
  `integrate_linear_edge_baseline`; that requires a separate truth-validation
  result showing AsLS accuracy/linearity/blank behavior or an equivalent known
  baseline benchmark.
