# XIC productization handoff

Updated: 2026-06-19 15:14
Branch: `cc/framework-improvements`
Checkpoint: default QuantMatrix ProductWriter/output activation is committed as
`0e0be3db Activate default quant matrix output`; a later discovery root-cause
fix is in the working tree and not yet committed.

Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`. This
handoff is only a compact current-state continuation snapshot.

## Current Objective

The default numeric matrix has a bounded Backfill product answer: detected
values plus the current 511 accepted Backfill quantification values. Release
use-path cleanup found a stop-ship target-row identity gap for `d4-N6-2HE-dA`.
The root cause is now fixed in discovery seed extraction, but the activated
default matrix bundle has not been regenerated.

## Active References

- Blueprint:
  `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md`
- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Default ProductWriter activation:
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/`
- Discovery precursor inference validation:
  `docs/superpowers/validation/discovery_precursor_inference_v1/`
- Real 511-cell bundle:
  `docs/superpowers/validation/quant_matrix_real_bundle_v1/`

## Current Product State

- Current tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Default `quant_matrix.tsv` contains detected values plus 511 accepted
  Backfill quantification values.
- Backfill values are quantification values, not detections, truth claims, or
  counted detections.
- Detected-only claims remain reconstructable from `cell_provenance.tsv`.
- Broad 4613-row Backfill remains parked.
- Workbook, GUI, selected peak/area, counted detection, scorer, and broad
  Backfill authority are unchanged by the discovery fix.

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

## Stop-Ship Target Row

User review found `d4-N6-2HE-dA` target `m/z=300.1605` absent from the activated
`quant_matrix.tsv`. The matrix has nearby rows `299.155` and `301.165`; the
`301.165 / 185.116` row is a valid dR-tag isotope feature row and must stay in
the matrix on its own evidence, but it must not be bridged back to `300.1605`
as target authority.

Existing 85RAW discovery artifacts under
`local_validation_artifacts/discovery/accepted_p8b/85raw` contained `0`
monoisotopic `300.1605 -> 184.113` candidates in the 22-25 min window and `160`
isotope-shift `301.165 -> 185.116` candidates across all 85 samples. That is
why the activated default matrix is missing the target row.

## Root Cause And Fix

Root cause: `xic_extractor.discovery.ms2_seeds` treated the Thermo MS2 filter
precursor as the only exact precursor when searching for
`precursor - neutral_loss` products. In `TumorBC2312_DNA.raw`, MS2 filter
precursor `300.2028` with product `184.1132` implies
`184.1132 + 116.0474 = 300.1606`, but the old direct-only search looked near
`184.1554` and rejected the valid product before grouping/alignment.

Fix in working tree:

- CID-NL discovery now treats the MS2 filter precursor as an isolation/trigger
  window for product-plus-neutral-loss inferred precursor seeds.
- Direct scan-precursor neutral-loss matches keep the old behavior and still
  choose one best direct product per scan/profile.
- Same scan/profile can now emit a direct `301.165 / 185.116` seed and an
  inferred `300.160x / 184.113` seed without replacing either row.
- `DiscoverySettings` and `scripts/run_discovery.py` expose
  `ms2_precursor_tol_da` / `--ms2-precursor-tol-da`; default is 1.6 Da.
- Discovery `candidate_id` keeps `sample#scan` but appends precursor/product
  m/z row identity to avoid same-scan collisions.
- Discovery `tag_evidence_json` records `precursor_mz_basis`,
  `scan_precursor_mz`, and scan-precursor delta fields.
- Discovery CSV column schemas are unchanged.

Single RAW validation:

- `TumorBC2312_DNA.raw`, 22-25 min, now emits `300.161 / 184.113` rows with
  `precursor_mz_basis=product_plus_neutral_loss`.
- `301.165 / 185.116` remains emitted as its own valid row.
- `duplicate_candidate_ids=0`.
- No 85RAW, scorer, ProductWriter, or default-matrix regeneration was run for
  this fix.

## Activated Bundle Use Path

Primary downstream file:

- `docs/superpowers/validation/quant_matrix_default_product_activation_v1/default_output/quant_matrix.tsv`

Use it as the current wide numeric matrix. Rows keep `Mz` and `RT`; sample
columns contain numeric area values or blanks. Downstream normalization and
statistics can read it without caring whether a value was detected or accepted
Backfill.

Caveat: this activated file predates the discovery fix, so it still does not
contain the `300.1605` target row. Do not claim the activated default matrix
contains `d4-N6-2HE-dA` until a later explicit discovery/alignment/default
activation expected-diff rerun passes.

## Verification In This Working Tree

- `uv run pytest tests/test_discovery_ms2_seeds.py tests/test_discovery_grouping.py tests/test_discovery_csv.py tests/test_discovery_pipeline.py tests/test_run_discovery.py tests/test_presets_apply.py -v --tb=short`
  passed 92 tests.
- Focused `ruff check` over touched discovery/CLI/preset/tests passed.
- `.venv\Scripts\python.exe scripts\run_discovery.py ... --raw TumorBC2312_DNA.raw --rt-min 22 --rt-max 25 --ms2-precursor-tol-da 1.6`
  exited 0 and wrote `docs/superpowers/validation/discovery_precursor_inference_v1/`.

Earlier Phase 11 activation verification before commit included focused
activation tests, broader quant-matrix/productization tests, activation
`--check-only`, `scripts/check_productization_state.py`, `ruff`, `mypy`,
`git diff --check`, and sub-agent review.

## Boundaries

- Do not describe the 511 accepted Backfill values as detections or truth.
- Do not reopen broad Backfill from this checkpoint.
- Do not claim workbook/GUI release behavior from this activation artifact.
- Do not infer target presence from isotope-shift rows.
- Do not delete or demote `301.165`; it is a valid feature row.
- Do not claim the current activated `quant_matrix.tsv` is fixed for
  `300.1605` until it is regenerated and expected-diff validated.
- Control plane has been updated for the public discovery surface change. Tier,
  active lane, and matrix authority remain unchanged.

## Next Actions

1. Review the discovery fix and run any needed broader discovery/alignment
   tests before commit.
2. Plan an explicit discovery/alignment/default-activation expected-diff rerun
   using the fixed discovery path. This is the step that can refresh the default
   matrix target row.
3. If preparing PR/release, rerun the repo CI-equivalent gate and write closeout
   from the control plane, this handoff, and the discovery validation artifact.
4. Open a new authority goal only if expanding beyond the current 511 cells,
   especially for the 3015 unresolved and 1087 missing-overlay pools.
