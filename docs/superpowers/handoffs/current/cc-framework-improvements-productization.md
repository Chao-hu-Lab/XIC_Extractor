# XIC productization handoff

Updated: 2026-06-19 18:14 +08:00
Branch: `cc/framework-improvements`

This is a compact current-state snapshot. Tier authority remains in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The default numeric matrix is usable for downstream analysis as the current
detected + 511 accepted-Backfill product output. The latest side cleanup did
not change ProductWriter behavior, matrix values, workbook/GUI behavior,
selected peak/area, counted detection, default extraction, scorer behavior, or
Backfill authority.

The `d4-N6-2HE-dA` monoisotopic `300.1605 -> 184.113` absence was traced to
Discovery row creation and the Discovery generation path is fixed. The already
activated default matrix bundle still predates that fix, so do not claim the
activated `quant_matrix.tsv` contains that exact target row until a later
discovery/alignment/default-activation expected-diff rerun regenerates it.

Validation artifact retention cleanup is now executed through the current
Phase 0-5 plan: rendered review HTML/PNG, QuantMatrix review HTML, and
duplicated promotion-packet downstream input copies are not durable
version-controlled product contracts. Contract indexes, status files, summaries,
source hashes, and checker inputs remain in git and are covered by a
metadata-only retention checker.

## Active References

- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Validation retention policy:
  `docs/superpowers/validation/RETENTION.md`
- Validation artifact inventory:
  `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`
- Default matrix activation bundle:
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/`
- Discovery precursor inference validation:
  `docs/superpowers/validation/discovery_precursor_inference_v1/`
- Externalized local rendered artifacts:
  `local_validation_artifacts/externalized_superpowers_validation/`
- Retention checker:
  `scripts/check_validation_artifact_retention.py`

## Product State

- Current tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Broad 4613-row Backfill remains parked.
- ProductWriter default matrix output is activated for detected values plus the
  current 511 accepted Backfill values.
- Four large QuantMatrix TSV validation outputs remain in git as `shrink_later`
  until checker/use-path contracts can be reduced safely.
- The retention cleanup only changes docs/artifact storage policy and removes
  generated review/render/duplicate-copy outputs from version control.

Status-index anchors retained:

- `product_ready_default_matrix_activated`
- Broad Backfill auto-write remains parked
- Goal 0/1 hardening added
- machine-adjudicated without granting new writer authority
- Goal 2 added Review Packet / Approval Workflow v1
- lockbox_shadow_automation_experiment_v1
- Goal 4 added Missing-Overlay Evidence Recovery v1
- keep only as explanation/triage
- Targeted MS1 shape identity limited rescue remains production-ready
- GUI and broader targets remain blocked
- `sample_metadata_v1` remains production-ready for no-output ordering
- roles/batch/matrix/exclusion must not alter quant output
- ReviewAction selected-candidate switch and manual-boundary area recompute remain parked
- manual-boundary area recompute remain parked
- classification and planning only

## Discovery Stop-Ship Fix

User review found `d4-N6-2HE-dA` target `m/z=300.1605` absent from the
activated `quant_matrix.tsv`. The nearby `301.165 / 185.116` row is a valid
dR-tag isotope feature and must stay on its own evidence, but it cannot be used
as target-row authority for `300.1605`.

Root cause: CID-NL Discovery treated the Thermo MS2 filter precursor as the
only exact precursor. In `TumorBC2312_DNA.raw`, the observed product
`184.1132` plus configured dR neutral loss `116.0474` infers row precursor
`300.1606`, but the old direct-only search looked near the scan filter
precursor-derived product and rejected the valid monoisotopic product before
grouping/alignment.

Implemented fix:

- `DiscoverySettings.ms2_precursor_tol_da` / `scripts/run_discovery.py
  --ms2-precursor-tol-da` define the scan precursor window for inferred CID-NL
  seeds.
- Discovery seed extraction distinguishes `scan_precursor` from
  `product_plus_neutral_loss`.
- Full candidate rows include `neutral_loss_error_basis`,
  `precursor_mz_basis`, `scan_precursor_mz`, `scan_precursor_delta_da`, and
  `max_scan_precursor_abs_delta_da`.
- `candidate_id` is `<sample>#<scan>@mz<precursor_mz>_p<product_mz>`.
- Alignment CSV replay rejects stale `sample#scan` ids, mismatched suffixes,
  duplicate candidate ids, and invalid basis enums so 300/301 same-scan rows
  cannot collapse or be rebound silently.

## Validation Artifact Retention

`docs/superpowers/validation/RETENTION.md` defines which validation artifacts
belong in git. `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv` currently
inventories 298 effective rows:

- 126 `keep_contract`
- 36 `keep_summary`
- 4 `shrink_later`
- 132 `externalize`

The cleanup externalized 132 generated validation artifacts / 12.19 MB to
ignored local storage under
`local_validation_artifacts/externalized_superpowers_validation/`. The tracked
Lockbox static-review contract is now
`docs/superpowers/validation/lockbox_static_review_v1/bundle_index.tsv` plus
`docs/superpowers/validation/lockbox_static_review_v1/README.md`; rendered
`index.html`, `cases/*.html`, and `plots/*.png` are generated local/release
artifacts. QuantMatrix real-bundle review HTML now has tracked
`review/quant_matrix_review_report_summary.json`, and promotion packet v2
downstream duplicate input TSVs are externalized while the copied downstream
summary points back to canonical real-bundle inputs by source-root path and
hash.

`scripts/check_validation_artifact_retention.py` now enforces inventory coverage,
forbids externalized/generated rendered files from remaining in the effective
tracked validation surface, verifies stale rendered-path references have an
inventory replacement mapping, and reports the 4 remaining QuantMatrix
`shrink_later` files. Its default mode is clean-checkout safe; the
`--require-externalized-local` mode verifies the ignored local copies on this
machine.

This does not alter any product tier or write authority. The control plane has
a no-tier-change maintenance entry for
`validation_artifact_retention_cleanup_v1`.

## Boundaries

- No 85RAW run was launched.
- No scorer was run.
- No ProductWriter/default extraction/workbook/GUI run was launched.
- Validation default-activation artifacts were only rebuilt to refresh the
  summary hash chain after retention externalization.
- No workbook/GUI/default extraction behavior changed.
- No current 511-cell writer authority or broad Backfill authority changed.
- Do not demote/delete the `301.165` isotope row.
- Do not remove `shrink_later` QuantMatrix files until the checker/status
  contract is changed and verified.

## Validation

Discovery focused validation from the prior fix passed:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms2_seeds.py tests/test_discovery_grouping.py tests/test_discovery_csv.py tests/test_discovery_pipeline.py tests/test_alignment_csv_io.py tests/test_discovery_precursor_inference_artifact.py -v --tb=short
```

Result: `79 passed` for that earlier focused shard.

Retention cleanup validation passed in this closeout:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_validation_artifact_retention.py --require-externalized-local
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_real_bundle.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_promotion_packet_v2.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_default_activation_dry_run.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_product_ready_closeout.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_quant_matrix_default_product_activation.py --check-only
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_static_review_bundle.py tests/test_lockbox_ai_challenge_pack.py tests/test_lockbox_ai_challenge_results.py tests/test_lockbox_second_review_pack.py tests/test_lockbox_owner_boundary_confirmation.py tests/test_lockbox_single_owner_ai_challenge_gate.py tests/test_quant_matrix_real_bundle.py tests/test_quant_matrix_promotion_packet_v2.py tests/test_quant_matrix_default_activation_dry_run.py tests/test_quant_matrix_product_ready_closeout.py tests/test_quant_matrix_default_product_activation.py tests/test_productization_state_index.py tests/test_validation_artifact_retention.py -v --tb=short
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check <changed retention/lockbox/quant scripts/modules/tests>
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Results: retention checker passed with `166` retained validation files, `132`
externalized artifacts, and `4` `shrink_later` warnings; productization state
was consistent; real bundle, promotion packet v2, dry-run, closeout, and
default activation check-only commands passed; focused pytest `119 passed`;
scoped ruff passed; and `mypy xic_extractor` passed.

## Next Actions

1. Commit this as a repo-hygiene/validation-retention change if the diff is
   accepted.
2. Open a later focused cleanup to shrink the four remaining `shrink_later`
   QuantMatrix TSV outputs only after checker/status contracts no longer
   require full dumps.
3. Open a separate regeneration goal for discovery/alignment/default activation
   expected diff when the product matrix should materialize the `300.1605`
   target row.
