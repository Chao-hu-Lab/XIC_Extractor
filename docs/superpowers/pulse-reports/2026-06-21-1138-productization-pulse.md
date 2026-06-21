# XIC Productization Pulse - 2026-06-21 11:38

## Verdict

- Current product tier is `product_ready_default_matrix_activated`.
- There are now two registered writer scopes: Backfill 511 cells and CID-NL 95 cells.
- CID-NL Discovery is no longer only diagnostic for the narrowed adopted bundle: `cid_nl_default_product_activation_v1` is `production_ready`, has `write_authority=TRUE`, and changes the default quant matrix for exactly 95 Discovery cells.
- Broad Backfill remains parked. The 4613-candidate universe is still not an auto-write pool.
- The activation is not committed yet. The working tree contains this activation slice plus its docs/checker/test updates.

## Lane Snapshot

| Lane | Tier | Evidence Added | Blocker / Next Evidence |
| --- | --- | --- | --- |
| Backfill current write-ready scope | `production_ready` / `product_ready_default_matrix_activated` | Existing default activation remains exactly 511 cells under `backfill_policy_write_ready_rows`. | Do not broaden without a new independent truth source plus expected-diff. |
| CID-NL Discovery default product activation v1 | `production_ready` / `product_ready_default_matrix_activated` | 95 adopted CID-NL Discovery cells across 20 transitions are now an explicit default matrix/ProductWriter authority scope under `cid_nl_adopt_ready_feature_inclusion_95_cells`. | Any expansion beyond 95 cells needs a new Discovery expected-diff/provenance gate. |
| Broad Backfill auto-write | parked / no writer authority | No new authority granted. | Still blocked as a broad writer pool. |
| Discovery / CID-NL evidence outside the 95-cell bundle | diagnostic or review evidence only | Preserved as evidence/provenance context, not direct writer authority. | Needs explicit adoption gate before product output changes. |

## What Changed

- Added a fail-closed default activation builder: `scripts/build_cid_nl_default_product_activation.py`.
- Registered CID-NL as a second allowed writer lane in the productization status index and authority manifest.
- Updated checker logic from "only Backfill can write" to "only registered writer lanes can write".
- Published compact retained evidence under `docs/superpowers/validation/cid_nl_default_product_activation_v1/`.
- Kept full generated matrix/provenance TSV outputs externalized under ignored `output/validation/cid_nl_default_product_activation_v1/`.
- Updated the active handoff and control plane to state the new default-active CID-NL 95-cell scope.

## Evidence Freshness

- Inspected current branch/status: `cc/framework-improvements`, ahead of origin by 98 commits, with unstaged CID-NL activation changes.
- Ran `uv run python -m scripts.check_productization_state`: pass.
- Ran `uv run python -m scripts.check_productization_authority`: pass.
- Ran `uv run python -m scripts.build_cid_nl_default_product_activation --check-only`: pass.
- Inspected `cid_nl_default_product_activation_summary.json`: `status=pass`, `activation_label=product_ready_default_matrix_activated`, `product_lane=cid_nl_discovery`, `accepted_discovery_cell_count=95`, `written_discovery_cell_count=95`, `product_writer_changed=True`, `default_quant_matrix_changed=True`, `expected_diff_count=95`, `unused_expected_diff_count=0`, `raw_or_85raw_ran=False`.
- Inspected `productization_status_index_v1.tsv`: Backfill writer row is 511 cells; CID-NL writer row is 95 cells; both are `production_ready`.

## Risks Of Overclaim

- This does not mean all CID-NL candidates are product-ready. Only the adopted 95-cell Discovery bundle is default-active.
- This does not authorize deleting or merging source/successor identities.
- This does not change workbook, GUI, selected peak/area, or counted detection behavior.
- This does not prove broad Backfill. Broad Backfill remains parked.
- This pulse did not rerun full pytest or RAW validation; it verified the current control-plane and activation contract.

## Next Best Actions

1. Commit this activation slice cleanly, without staging ignored full matrix outputs.
2. Keep the next product goal on Discovery unless the user explicitly reopens Backfill.
3. If expanding CID-NL Discovery, require a new bounded expected-diff/provenance gate before changing any default output.

Read this first next time: current product authority is Backfill 511 cells plus CID-NL 95 cells; anything beyond that is not default-active.
