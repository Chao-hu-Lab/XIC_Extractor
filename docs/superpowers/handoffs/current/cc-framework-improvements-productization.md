# XIC productization handoff

Updated: 2026-06-19 16:20
Branch: `cc/framework-improvements`

This is a compact current-state snapshot. Tier authority remains in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The default numeric matrix is usable for downstream analysis as the current
detected + 511 accepted-Backfill product output, but it predates the Discovery
row-identity fix. Do not claim the activated `quant_matrix.tsv` contains the
`d4-N6-2HE-dA` monoisotopic `300.1605 -> 184.113` target row until a later
discovery/alignment/default-activation expected-diff rerun regenerates it.

The Discovery contract/gate is now fixed for the stop-ship root cause:

- same scan/profile can preserve the valid `301.165 / 185.116` dR isotope row;
- same scan/profile can also emit the inferred `300.1605 / 184.113` row;
- row identity is encoded in `candidate_id`;
- stale, duplicate, or row-mismatched candidate ids fail closed during
  alignment CSV replay;
- full Discovery candidate rows expose basis/delta provenance fields.

## Active References

- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Default matrix activation bundle:
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/`
- Discovery precursor inference validation:
  `docs/superpowers/validation/discovery_precursor_inference_v1/`
- Untargeted Discovery V1 spec:
  `docs/superpowers/specs/2026-05-09-untargeted-discovery-v1-spec.md`
- Blueprint:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`

## Product State

- Current tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Broad 4613-row Backfill remains parked.
- ProductWriter, workbook, GUI, selected peak/area, counted detection, scorer,
  and Backfill authority are unchanged by the Discovery fix.
- The Discovery full-candidate CSV schema and alignment replay behavior did
  change; control plane records this as a no-tier-change public-surface update.

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

## Stop-Ship Root Cause

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

## Implemented Fix

- `DiscoverySettings.ms2_precursor_tol_da` / `scripts/run_discovery.py
  --ms2-precursor-tol-da` define the scan precursor window for inferred CID-NL
  seeds.
- Discovery seed extraction distinguishes `scan_precursor` from
  `product_plus_neutral_loss`.
- Full candidate rows include `neutral_loss_error_basis`,
  `precursor_mz_basis`, `scan_precursor_mz`, `scan_precursor_delta_da`, and
  `max_scan_precursor_abs_delta_da`.
- `neutral_loss_mass_error_ppm=0` on inferred rows means configured-loss
  inference, not measured scan-precursor/product mass error.
- `candidate_id` is `<sample>#<scan>@mz<precursor_mz>_p<product_mz>`.
- Alignment CSV replay rejects stale `sample#scan` ids, mismatched suffixes,
  duplicate candidate ids, and invalid basis enums so 300/301 same-scan rows
  cannot collapse or be rebound silently.

## Validation

Focused tests passed:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_ms2_seeds.py tests/test_discovery_grouping.py tests/test_discovery_csv.py tests/test_discovery_pipeline.py tests/test_alignment_csv_io.py tests/test_discovery_precursor_inference_artifact.py -v --tb=short
```

Result: `79 passed`.

One-RAW Discovery validation passed without 85RAW/scorer:

```powershell
.venv\Scripts\python.exe scripts\run_discovery.py --raw C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\TumorBC2312_DNA.raw --dll-dir C:\Xcalibur\system\programs --output-dir docs\superpowers\validation\discovery_precursor_inference_v1\TumorBC2312_DNA --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --rt-min 22 --rt-max 25 --ms2-precursor-tol-da 1.6 --resolver-mode local_minimum
```

Artifact checker passed:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_discovery_precursor_inference_artifact.py --check-only --summary-json docs\superpowers\validation\discovery_precursor_inference_v1\discovery_precursor_inference_check_summary.json
```

Candidate SHA-256:
`B1B4956C3F0296D51E144659DB127CFB453140A66030C97C22FEED8C11326E2B`.

## Boundaries

- No 85RAW run was launched.
- No scorer was run.
- No ProductWriter/default matrix regeneration was run.
- No workbook/GUI/default extraction behavior changed.
- No current 511-cell writer authority or broad Backfill authority changed.
- Do not demote/delete the `301.165` isotope row.

## Next Actions

1. Finish sub-agent review of the Discovery contract/gate and fix any findings.
2. Run final focused gates: Discovery tests, checker, default activation
   `--check-only`, productization state checker, hook smoke, secret/local-path
   scan, and `git diff --check`.
3. Only after this gate, open a separate regeneration goal for
   discovery/alignment/default-activation expected diff if the product matrix
   should materialize the `300.1605` target row.
