# dna_dr_product_ready performance pass archive

Date: 2026-06-22
Branch: `cc/framework-improvements`

This archive keeps the completed phase details that were pruned from the
current productization handoff.

## Exact-safe 8RAW preset performance

Commands used the foreground documented `scripts.run_alignment --preset
dna_dr_product_ready` path and retained the public CLI surface.

Artifacts:

- Baseline:
  `output/performance/dna_dr_product_ready_8raw_baseline_20260622_freshinput`
- First optimized overlay-reuse run:
  `output/performance/dna_dr_product_ready_8raw_optimized_20260622_freshinput`
- Current optimized run:
  `output/performance/dna_dr_product_ready_8raw_optimized4_20260622_freshinput`

Observed timing:

- Total 8RAW wall time: about 252.5s -> 170.5s.
- RAW overlay opens: 48 -> 8.
- Overlay chromatogram calls: 360 -> 65.
- `standard_peak.chunk`: 99.63s -> 38.43s.
- `alignment.cluster_owners`: 41.69s -> 25.96s.
- `_validate_payload_value` cProfile cumulative time: about 15.9s -> 6.23s.

Output parity and product checks:

- Public TSV hashes matched the baseline for `alignment_review.tsv`,
  `alignment_matrix.tsv`, `alignment_matrix_identity.tsv`,
  `standard_peak_activation_hypothesis_identity.tsv`,
  `standard_peak_activation_value_delta.tsv`, and
  `standard_peak_activation_application_summary.tsv`.
- Standard-peak summary stayed `status=pass`, `chunk_count=6`,
  `review_queue_row_count=676`, `matrix_cells_written=210`, and
  `coverage_status=complete`.
- `scripts.check_product_ready_preset_publication` passed for optimized4.

Implemented exact-output-preserving changes:

- `standard_peak_backfill_preset` now renders one global matrix-only overlay
  summary per pending queue and slices it per chunk.
- Chunked machine calls reuse the existing-overlay contract and do not pass
  overlay-generation parameters alongside `overlay_batch_summary_tsv`.
- Standard-peak render workers use a conservative cap:
  `min(raw_workers, os.cpu_count() or 1, 8)`.
- Owner clustering keeps the same hard-gate ppm comparisons while removing the
  former `_ppm` helper hot path.
- Process-backend payload validation returns immediately for scalar leaves while
  preserving callable/module/file/dataclass/container rejection.

Validation recorded during the pass:

- Focused standard-peak/shift-aware/CLI tests: 84 passed.
- Focused owner-clustering/process-backend tests: 57 passed.
- `ruff check xic_extractor tests`: passed before the checker sync.
- `mypy xic_extractor`: passed.

## Productization packets referenced by current handoff

Full-chain 666-cell diagnostic:
`docs/superpowers/validation/backfill_expansion_full_evidence_chain_v1/`.

- expected diff/provenance: 666/666.
- sample-local source evidence: 666/666.
- RAW overlay trace identity: 666/666.
- old full-chain pass: 374/666.
- old full-chain held: 292/666.

Selective source-family diagnostic:
`docs/superpowers/validation/backfill_expansion_selective_shift_aware_gate_v1/`.

- 491/666 diagnostic-pass.
- 175/666 held.
- grants no ProductWriter authority.

Peak-mode decomposition:
`docs/superpowers/validation/backfill_expansion_peak_mode_decomposition_v1/`.

- 112 clean target-mode candidate cells.
- 37 target-mode cells needing boundary review.
- 29 off-target hold/remap cells.
- 0 missing/unclassified cells.

Clean-target selective default activation v1:
`docs/superpowers/validation/backfill_expansion_clean_target_selective_product_activation_v1/`.

- 84 active writer cells across 7 rows.
- 0 unused expected-diff rows.
- 84 written cells in the externalized default activation replay.
- 84 accepted cell-provenance rows.
- 84 changed matrix cells.
- active scope:
  `backfill_expansion_clean_target_selective_activation_84_cells`.
- excludes the 28 projected-held clean-target cells.
- excludes the 37 boundary-review cells.
- excludes the 29 off-target hold/remap cells.

The 84-cell packet has `write_authority=TRUE`,
`product_writer_changed=TRUE`, `default_quant_matrix_changed=TRUE`, and
`selected_peak_area_or_counting_changed=FALSE`.
