# Backfill Expansion Evidence Availability v1

Status: `pass`.

This is a no-RAW evidence-availability gate over the Backfill pressure created by CID-NL Discovery activation. It checks whether the current mechanical adjudication and trace recovery artifacts already contain sample-local evidence for the active blank cells.

## Decision

Release decision: `hold_for_new_sample_local_ms1_identity_evidence`.

- Active Backfill pressure cells: `929`.
- Existing mechanical adjudication coverage: `0`.
- Existing trace recovery coverage: `0`.
- Immediate expected-diff-ready cells: `0`.
- Cells requiring new sample-local evidence: `929`.

The key rule is strict: evidence must match the exact `peak_hypothesis_id + sample_stem` cell. Existing row/family evidence is not projected onto these CID-NL cells.

## Boundary

This gate does not run RAW, does not write a default matrix, does not change ProductWriter authority, and does not unpark broad Backfill.

## Files

- Summary JSON: `docs/superpowers/validation/backfill_expansion_evidence_availability_v1/backfill_expansion_evidence_availability_summary.json`
- Checks TSV: `docs/superpowers/validation/backfill_expansion_evidence_availability_v1/backfill_expansion_evidence_availability_checks.tsv`
- Compact row manifest: `docs/superpowers/validation/backfill_expansion_evidence_availability_v1/backfill_expansion_evidence_availability_row_manifest.tsv`
- Full cell map: `output/validation/backfill_expansion_evidence_availability_v1/backfill_expansion_evidence_availability_cells.tsv`
