# Backfill Expansion Expected-Diff Provenance v1

This gate converts the RAW-observed Backfill expansion cells into a
candidate activation packet. It uses the existing
ProductionAcceptanceManifest and QuantMatrixVersion expected-diff
contracts, then runs a validation-only dry-run matrix writer under
`output/validation/`.

It does not change ProductWriter authority, the public default matrix,
workbooks, GUI behavior, selected peak/area/counting, or the active
product lane.

- Candidate cells: `666`.
- Candidate rows: `20`.
- Dry-run written cells: `666`.
- Unused expected-diff rows: `0`.
- Held cells kept out: `263`.
- Next gate: `explicit_public_default_activation_change`.

Full source evidence, manifest, expected-diff, dry-run matrix, and full
cell provenance stay externalized under `output/validation/`.
