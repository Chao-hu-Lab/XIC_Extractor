# Backfill Expansion Sample-Local MS1 Evidence v1

Status: `pass`.

This is a no-RAW gate over the 929 active Backfill pressure cells created by CID-NL Discovery activation. It joins the pressure cells against the current fix3 85RAW-derived alignment cell evidence using only the exact `peak_hypothesis_id + sample_stem` key.

## Decision

Release decision: `raw_overlay_trace_identity_gate_for_675_present_cells_and_hold_254_missing_alignment_cells`.

- Active Backfill pressure cells: `929`.
- Exact sample-local alignment evidence present: `675`.
- Missing exact alignment cell evidence: `254`.
- Present cells with `review_rescue` state: `675`.
- Present cells with `DNA_dR` tag evidence: `675`.
- Present cells with `production_family` identity: `675`.
- RAW overlay queue rows: `20`.

The present 675 cells are not write-ready. They are the bounded input for a future RAW overlay trace/identity gate. The missing 254 cells stay held because row/family evidence is not projected onto cells.

## Boundary

This gate does not run RAW, does not write a default matrix, does not change ProductWriter authority, does not unpark broad Backfill, and does not change selected peak/area/counting.

## Files

- Summary JSON: `docs/superpowers/validation/backfill_expansion_sample_local_ms1_evidence_v1/backfill_expansion_sample_local_ms1_evidence_summary.json`
- Checks TSV: `docs/superpowers/validation/backfill_expansion_sample_local_ms1_evidence_v1/backfill_expansion_sample_local_ms1_evidence_checks.tsv`
- Compact row manifest: `docs/superpowers/validation/backfill_expansion_sample_local_ms1_evidence_v1/backfill_expansion_sample_local_ms1_evidence_row_manifest.tsv`
- Full cell evidence map: `output/validation/backfill_expansion_sample_local_ms1_evidence_v1/backfill_expansion_sample_local_ms1_evidence_cells.tsv`
- RAW overlay queue: `output/validation/backfill_expansion_sample_local_ms1_evidence_v1/backfill_expansion_sample_local_ms1_overlay_queue.tsv`
