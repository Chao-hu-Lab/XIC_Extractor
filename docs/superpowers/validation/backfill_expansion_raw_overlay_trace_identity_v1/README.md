# Backfill Expansion RAW Overlay Trace Identity v1

Status: `pass`.

This gate consumes the 20-row evidence-only RAW overlay batch and joins each trace back to the exact `peak_hypothesis_id + sample_stem` Backfill pressure cell.

## Decision

Release decision: `expected_diff_design_for_666_raw_trace_observed_cells_and_hold_263_cells`.

- Active Backfill pressure cells: `929`.
- Exact sample-local alignment evidence present: `675`.
- Missing exact alignment evidence: `254`.
- RAW trace rows found for alignment-present cells: `675`.
- RAW trace observed cells: `666`.
- RAW trace absent cells: `9`.
- Metric warning cells retained with notes: `43`.
- Held cells: `263`.

The 666 observed cells may feed a future expected-diff/provenance design. They are not write-ready here. The 9 trace-absent cells and 254 missing-alignment cells remain held.

## Boundary

This gate ran a bounded evidence-only RAW overlay, not an 85RAW alignment rerun. It does not write a default matrix, change ProductWriter authority, unpark broad Backfill, or change selected peak/area/counting.

## Files

- Summary JSON: `docs/superpowers/validation/backfill_expansion_raw_overlay_trace_identity_v1/backfill_expansion_raw_overlay_trace_identity_summary.json`
- Checks TSV: `docs/superpowers/validation/backfill_expansion_raw_overlay_trace_identity_v1/backfill_expansion_raw_overlay_trace_identity_checks.tsv`
- Compact row manifest: `docs/superpowers/validation/backfill_expansion_raw_overlay_trace_identity_v1/backfill_expansion_raw_overlay_trace_identity_row_manifest.tsv`
- Full cell gate map: `output/validation/backfill_expansion_raw_overlay_trace_identity_v1/backfill_expansion_raw_overlay_trace_identity_cells.tsv`
- RAW overlay batch outputs: `output/validation/backfill_expansion_raw_overlay_trace_identity_v1/family_ms1_overlay_batch/`
