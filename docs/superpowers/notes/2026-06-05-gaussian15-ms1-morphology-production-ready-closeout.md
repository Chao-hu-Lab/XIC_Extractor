# Gaussian15 MS1 Morphology Production-Ready Closeout

**Date:** 2026-06-05
**Verdict:** `production_ready` for the Gaussian15 MS1 morphology ownership
transition.

This verdict means active targeted/untargeted product area authority no longer
falls back to legacy AsLS corrected area. Product-facing primary area now uses
typed `gaussian15_positive_asls_residual` facts when available and fails closed
with `missing_ms1_morphology_area` when they are not available. Legacy
`asls_baseline_corrected` remains compatibility/debug evidence only.

This does not claim every matrix identity is biologically final without review.
MS2/NL opportunity, RT/ISTD context, duplicate claims, rescue-heavy rows, and
manual EIC/MS2 adjudication remain separate identity-quality surfaces.

## Human Boundary Oracle

The 8RAW selected-envelope manual review feedback was converted into a boundary
oracle:

`docs/superpowers/fixtures/selected_envelope_manual_boundary_review_gaussian15_peak_group_20260605.tsv`

The accepted behavior is:

- `TumorBC2312_DNA | 8-oxodG`: active boundary extends to the Gaussian peak tail
  near 17.17 min.
- `Breast_Cancer_Tissue_pooled_QC5 | 8-oxodG`: active boundary extends to the
  Gaussian peak tail near 17.20 min.
- `NormalBC2312_DNA | 8-oxodG`: active boundary uses the later Gaussian peak
  group and excludes the earlier noisy region.
- `TumorBC2263_DNA | 8-oxodG`: active boundary avoids the wrong 19 min peak.

The 8RAW candidate gate returned `gate_decision=promote` and
`boundary_gate_decision=promote` for:

`output/gaussian15_ms1_morphology_8raw_20260605/targeted_validation/gaussian15_peak_group_projection_rerun_20260605/chrom_peak_segment_candidate_gate_gaussian_peak_group/chrom_peak_segment_gate_manifest.json`

## 8RAW Alignment Gate

Command shape: `validation-minimal`, `production-equivalent`,
`audit-evidence-mode none`, `validation-fast`, `super-window`, foreground RAW
run.

Output:

`output/gaussian15_ms1_morphology_8raw_20260605/alignment_validation_minimal_no_asls_fallback/`

Observed source distribution from `alignment_cells.tsv`:

| Source | Count |
| --- | ---: |
| `gaussian15_positive_asls_residual` | 15984 |
| blank | 2735 |
| `missing_ms1_morphology_area` | 1 |

Key gate facts:

- `matrix_value_policy=gaussian15_positive_asls_residual_primary`
- `non_gaussian_with_area=0`
- `asls_source_with_area=0`
- `raw_source_with_area=0`

## 85RAW Alignment Gate

Command shape: `validation-minimal`, `production-equivalent`,
`audit-evidence-mode none`, `validation-fast`, `super-window`, foreground RAW
run.

Output:

`output/gaussian15_ms1_morphology_85raw_20260605/alignment_validation_minimal_no_asls_fallback/`

Observed source distribution from `alignment_cells.tsv`:

| Source | Count |
| --- | ---: |
| `gaussian15_positive_asls_residual` | 1546489 |
| blank | 251310 |
| `missing_ms1_morphology_area` | 36 |

Key gate facts:

- `matrix_value_policy=gaussian15_positive_asls_residual_primary`
- `primary_matrix_area_nonblank_count=1546489`
- `non_gaussian_source_with_area=0`
- `asls_source_with_area=0`
- `raw_source_with_area=0`
- `blank_source_with_area=0`
- `matrix_sample_count=85`
- `matrix_row_count=614`
- `matrix_nonblank_cell_count=39186`
- `review_included_row_count=614`

The 36 `missing_ms1_morphology_area` cells are rescued owner-backfill cells with
blank `primary_matrix_area`. They do not write active product area.

## Verification

No-RAW and validation checks run in this worktree:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_fe0_contract.py tests/test_alignment_matrix.py tests/test_alignment_cell_quality.py tests/test_alignment_pipeline_outputs.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_alignment_owner_backfill.py tests/test_untargeted_final_matrix_contract.py tests/test_shared_peak_identity_product_activation.py tests/test_matrix_identity_blast_radius.py
# 124 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_evidence_semantics.py tests/test_peak_hypotheses.py tests/test_peak_model_selection.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_signal_processing_selection.py tests/test_peak_candidate_table.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_untargeted_final_matrix_contract.py tests/test_chrom_peak_segment_projection.py tests/test_chrom_peak_segment_candidate_gate.py tests/test_selected_envelope_plot_review.py tests/test_target_extraction.py tests/test_peak_candidate_audit.py tests/test_candidate_evidence_selection.py tests/test_alignment_matrix.py tests/test_alignment_cell_quality.py tests/test_alignment_pipeline_outputs.py tests/test_alignment_owner_matrix.py tests/test_alignment_owner_backfill.py tests/test_shared_peak_identity_product_activation.py tests/test_matrix_identity_blast_radius.py
# 343 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_run_alignment.py
# 52 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts\run_alignment.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tools\diagnostics\chrom_peak_segment_candidate_gate.py tools\diagnostics\selected_envelope_plot_review.py
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
# Success: no issues found in 294 source files
```

## Runtime Setting

The local `validation-fast` profile now uses `raw-workers=11` and
`raw-xic-batch-size=64`. New 85RAW commands should also pin
`--raw-workers 11` explicitly in the command line.
