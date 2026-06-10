# 2026-06-10 Standard-Peak Final Matrix Closeout Note

## Current Product Surface

The standard-peak 85RAW backfill run is no longer only a sidecar/gallery
artifact. After a passing chunk consolidation with complete review-queue
coverage, the consolidated formal product output is published back to the source
alignment output by default.

Default final matrix:

- `output/backfill_light_cell_evidence_85raw_20260609/alignment_85raw_validation_minimal_light_seed_audit/alignment_matrix.tsv`
- `output/backfill_light_cell_evidence_85raw_20260609/alignment_85raw_validation_minimal_light_seed_audit/alignment_matrix_identity.tsv`

Backup of the pre-standard-peak matrix:

- `output/backfill_light_cell_evidence_85raw_20260609/alignment_85raw_validation_minimal_light_seed_audit/alignment_matrix.pre_standard_peak_backfill.tsv`
- `output/backfill_light_cell_evidence_85raw_20260609/alignment_85raw_validation_minimal_light_seed_audit/alignment_matrix_identity.pre_standard_peak_backfill.tsv`

Publication manifest:

- `output/backfill_light_cell_evidence_85raw_20260609/alignment_85raw_validation_minimal_light_seed_audit/standard_peak_default_matrix_manifest.json`

Formal handoff copy:

- `output/backfill_light_cell_evidence_85raw_20260609/standard_peak_machine_pipeline_consolidated_full_queue_20260610/formal_product_output/alignment_matrix.tsv`
- `output/backfill_light_cell_evidence_85raw_20260609/standard_peak_machine_pipeline_consolidated_full_queue_20260610/formal_product_output/standard_peak_formal_product_manifest.json`

## Verified 85RAW State

- Review-queue coverage: `671/671`
- Duplicate queue ranks: `0`
- Missing queue ranks: `0`
- Standard-peak matrix cells written: `5880`
- Consolidated shadow projection rows: `27565`
- Duplicate consolidated shadow projection keys: `0`
- Source final matrix SHA256:
  `C737474CA544A737E5DBF05329BB44072CC304176D696A01916B7DE318807021`
- Source final matrix identity SHA256:
  `2AA11ED0EAC8F49BBB6B37726918AA523F8E706C3758E5CD7A305C316A1950AB`
- Pre-standard backup SHA256:
  `A78B5F7697D300A66472C12C5E18651E3DCED114169460BDBD23E58927A4B56A`

The source final matrix hash matches the formal product output hash. The
publication manifest records the same backup hash, so the mutation is
traceable.

## Rerun Rule

For repeatable product reruns, use the `*.pre_standard_peak_backfill.tsv` files
as activation input and publish back to the default final matrix paths:

```powershell
.venv\Scripts\python.exe tools\diagnostics\standard_peak_backfill_chunk_consolidation.py `
  --chunk-dir <chunk-output-dir> `
  --review-queue-tsv <alignment_retained_backfill_overlay_review_queue.tsv> `
  --alignment-matrix-tsv output\backfill_light_cell_evidence_85raw_20260609\alignment_85raw_validation_minimal_light_seed_audit\alignment_matrix.pre_standard_peak_backfill.tsv `
  --alignment-matrix-identity-tsv output\backfill_light_cell_evidence_85raw_20260609\alignment_85raw_validation_minimal_light_seed_audit\alignment_matrix_identity.pre_standard_peak_backfill.tsv `
  --publish-alignment-matrix-tsv output\backfill_light_cell_evidence_85raw_20260609\alignment_85raw_validation_minimal_light_seed_audit\alignment_matrix.tsv `
  --publish-alignment-matrix-identity-tsv output\backfill_light_cell_evidence_85raw_20260609\alignment_85raw_validation_minimal_light_seed_audit\alignment_matrix_identity.tsv `
  --alignment-review-tsv <alignment_review.tsv> `
  --emit-formal-product-output `
  --output-dir <consolidated-output-dir>
```

Do not use the already-published `alignment_matrix.tsv` as activation input for
formal reruns. That would make previously written standard-peak cells look like
current matrix values and corrupt written-count semantics.

## Remaining Integration Boundary

The consolidated standard-peak finalizer now writes the default final matrix
when its complete-coverage gate passes. The raw alignment entry point still does
not run the expensive RAW overlay, shift-aware gate, productization, and
consolidation chain by itself. A future public workflow wrapper can make this a
single command, but it should keep the same fail-closed requirements:

- complete queue coverage for formal publication;
- standard-peak gate support;
- provenance-checked trace JSON paths and hashes;
- non-standard peaks remain review-only;
- family/multi-claim context is warning-only only under the approved
  standard-peak same-peak conditions.
