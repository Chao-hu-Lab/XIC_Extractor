# Full Untarget PeakHypothesis Final Matrix Closeout

## Verdict

Status: `production_candidate`.

The real untargeted product writer path now emits a clean final matrix surface:

- `alignment_matrix.tsv`: `Mz`, `RT`, sample columns
- workbook `Matrix`: `Mz`, `RT`, sample columns
- `alignment_matrix_identity.tsv`: one identity/provenance row per product
  matrix row

Review and audit surfaces still carry legacy family provenance. The product
matrix no longer exposes family ids as row names.

## Downstream Migration And Recovery

Old primary matrix columns:

- `feature_family_id`
- `neutral_loss_tag`
- `family_center_mz`
- `family_center_rt`

New primary matrix columns:

- `Mz`
- `RT`
- sample columns

Replacement lookup:

- old `feature_family_id` access moves to
  `alignment_matrix_identity.tsv:source_feature_family_ids`
- product row id access moves to
  `alignment_matrix_identity.tsv:peak_hypothesis_id`
- row identity basis moves to
  `alignment_matrix_identity.tsv:row_identity_basis`
- split status moves to
  `alignment_matrix_identity.tsv:split_evaluation_status`
- projection status moves to
  `alignment_matrix_identity.tsv:projection_status`
- displayed center provenance moves to
  `alignment_matrix_identity.tsv:center_mz_basis`,
  `center_rt_basis`, and `center_weight_basis`

If a downstream script still requires `feature_family_id` as the primary matrix
row label, it should join `alignment_matrix.tsv` to
`alignment_matrix_identity.tsv` by 1-based row order through
`matrix_row_index`, not by trying to parse `Mz`/`RT`.

## Integrity Evidence

Focused product tests now assert:

- TSV and workbook Matrix have the same clean `Mz`, `RT`, sample-column shape.
- `alignment_matrix_identity.tsv` emits the exact schema from the product
  contract.
- identity sidecar row count equals product matrix row count in focused fixtures.
- sidecar `Mz`/`RT` values match displayed product matrix `Mz`/`RT`.
- product rows reject `family_projection_no_split_evidence`.
- split rows carry `split_peak_hypothesis` and
  `complete_product_ready_split` identity tokens.
- parent aggregate rows with child hypotheses are rejected from product Matrix
  writes.
- one `source_candidate_id` cannot write values into two product hypothesis
  rows.
- product output levels emit `alignment_matrix_identity.tsv` whenever the
  primary matrix surface is emitted.
- Review/Audit still retain family provenance and blank reasons.

Verification commands run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_untargeted_final_matrix_contract.py tests/test_alignment_output_levels.py tests/test_alignment_pipeline_outputs.py tests/test_alignment_pipeline.py tests/test_run_alignment.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_shared_peak_identity_peak_hypothesis_matrix.py tests/test_shared_peak_identity_product_activation.py tests/test_shared_peak_identity_schema.py tests/test_shared_peak_identity_mode_window_assignment_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment tools/diagnostics tests/test_untargeted_final_matrix_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_pipeline_outputs.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_shared_peak_identity_peak_hypothesis_matrix.py tests/test_shared_peak_identity_product_activation.py tests/test_shared_peak_identity_schema.py tests/test_shared_peak_identity_mode_window_assignment_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Observed result:

- product/writer/pipeline/CLI focused tests: `122 passed`
- PeakHypothesis/activation focused tests: passed
- focused ruff: passed
- mypy: passed

## Remaining Risk

This closes the product writer/schema migration with synthetic and no-RAW
contract tests. It does not prove 85RAW scientific readiness or benchmark
performance. The next validation layer should compare real output row counts,
identity-sidecar row counts, projection counts, and selected targeted/untargeted
benchmark cases in a disposable output directory before PR-ready claims.
