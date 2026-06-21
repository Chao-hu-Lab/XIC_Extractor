# Backfill Expansion Clean-Target Selective Default Activation v1

Status: `product_ready_default_matrix_activated`.

This bundle is the bounded default activation for the 84 clean-target
Backfill expansion cells whose selective source-family projection
passes the full evidence chain.

- Activated cells: `84`.
- Activated rows: `7`.
- Written cells: `84`.
- Unused expected-diff rows: `0`.
- Projected-held cells excluded: `28`.
- Boundary-review cells excluded: `37`.
- Off-target hold/remap cells excluded: `29`.

The full default matrix, full provenance, filtered manifest, and
filtered expected diff stay externalized under `output/validation/`.
Version control keeps only this compact summary, checks, and manifest.

Authority boundary: this is active only for the named 84-cell scope.
It does not activate the 28 held cells, 37 boundary-review cells,
29 off-target hold/remap cells, broad Backfill, workbook, GUI,
selected peak, selected area, or counted detection.
