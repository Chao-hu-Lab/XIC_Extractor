# Backfill Expansion Census v1

Status: `pass`.

This is a no-RAW census of the Backfill pressure created by the current CID-NL Discovery default activation. It does not run Backfill, does not change the default matrix, and does not expand ProductWriter authority.

## Current Scope

- Existing Backfill write-ready authority: `511` cells.
- CID-NL active successor rows: `20` rows.
- CID-NL active row sample-cell universe: `1700` cells.
- Directly detected cells on those rows: `676`.
- Discovery default-written cells on those rows: `95`.
- New Backfill pressure cells: `929`.

These 929 cells are blank cells on rows that Discovery has already made product-visible. They are candidates for future Backfill evidence review only; they are not writable cells yet.

## Parked Future Pressure

- Write-authorized but non-active CID-NL rows: `23` rows.
- Blank cells on those parked rows: `1010`.

Those cells stay parked because the rows are not active Discovery product scope. They cannot be routed through Backfill until the Discovery feature-inclusion authority changes.

## Boundary

Backfill authority remains the existing 511-cell `backfill_policy_write_ready_rows` scope. This census is diagnostic evidence for the next Backfill gate: sample-local MS1/identity evidence for active-row blank cells.

## Files

- Summary JSON: `docs/superpowers/validation/backfill_expansion_census_v1/backfill_expansion_census_summary.json`
- Checks TSV: `docs/superpowers/validation/backfill_expansion_census_v1/backfill_expansion_census_checks.tsv`
- Compact row manifest: `docs/superpowers/validation/backfill_expansion_census_v1/backfill_expansion_census_row_manifest.tsv`
- Full opportunity cell map: `output/validation/backfill_expansion_census_v1/backfill_expansion_opportunity_cells.tsv`
