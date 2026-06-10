# 2026-06-10 DNA-dR Preset 85RAW Run Observations

## Run Identity

This note records the first full 85RAW trial after wiring the built-in
`dna_dr` preset into `scripts/run_alignment.py`.

Output root:

- `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal`

Primary command shape:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --preset dna_dr `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal `
  --expected-sample-count 85 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --raw-workers 11 `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\timing.json `
  --timing-live-output output\standard_peak_backfill_preset_85raw_20260610\alignment_preset_dna_dr_85raw_validation_minimal\timing.live.json
```

The preflight-only form passed before the real RAW/DLL run.

## Product Result

The preset chain successfully completed after resume and published the
standard-peak activation back into the default alignment matrix.

Key observed results:

- Preset summary status: `pass`
- Consolidation status: `pass`
- Coverage status: `complete`
- Review queue rows covered: `671/671`
- Matrix cells written: `7307`
- Activation application status: `applied`
- Activation acceptance status: `pass`
- Output matrix rows: `685`
- Input matrix rows: `685`
- Families added to matrix: `0`
- Families removed from matrix: `0`
- Matrix value conflict cells: `0`
- Non-standard peaks remain out of scope for automatic publication.

Published product files:

- `alignment_matrix.tsv`
- `alignment_matrix_identity.tsv`
- `standard_peak_default_matrix_manifest.json`

Pre-standard-peak backups:

- `alignment_matrix.pre_standard_peak_backfill.tsv`
- `alignment_matrix_identity.pre_standard_peak_backfill.tsv`

Audit files:

- `standard_peak_activation_application_summary.tsv`
- `standard_peak_activation_hypothesis_identity.tsv`
- `standard_peak_activation_value_delta.tsv`

Human review surface:

- `standard_peak_backfill_preset/consolidated/standard_peak_productization/reconciliation_gallery/backfill_evidence_reconciliation_gallery.html`

## Resume Behavior

The first real run was interrupted by the 2 hour shell timeout while already
inside the standard-peak chunk pipeline. The base alignment outputs had already
been written, and chunks through `r361_480` were complete. The run had started
`r481_600` when the timeout happened.

A resume patch was added to `tools/diagnostics/standard_peak_backfill_preset.py`
so that `reuse_existing=True` skips already completed chunk summaries. The
resume call finished the remaining chunks and consolidation successfully.

Completed chunks:

- `r1_120`: `pass`
- `r121_240`: `pass`
- `r241_360`: `pass`
- `r361_480`: `pass`
- `r481_600`: `pass`
- `r601_671`: `pass`

Chunk matrix-cell contribution:

- `r1_120`: `2540`
- `r121_240`: `1316`
- `r241_360`: `1701`
- `r361_480`: `1038`
- `r481_600`: `610`
- `r601_671`: `102`

Total: `7307`.

## Cost Observations

This run proves the product path, but it is not yet cost-clean enough to treat
the full evidence/gallery chain as the normal cheap default.

Observed wall-clock behavior:

- The initial foreground command hit the 2 hour timeout during standard-peak
  productization.
- Resume of the remaining work took about 32 minutes.
- End-to-end wall time for this full preset trial was therefore about 2.5 hours.

The alignment timing log showed these large recorded stages:

- `alignment.owner_backfill`: about `325 sec`
- `alignment.write_outputs`: about `165 sec`
- `alignment.build_owners.extract_xic`: about `163 sec`
- `alignment.cluster_owners`: about `114 sec`
- `alignment.backfill_scope`: about `106 sec`
- `alignment.owner_backfill.extract_xic`: about `99 sec`
- `alignment.primary_consolidation`: about `86 sec`
- `alignment.claim_registry`: about `65 sec`
- `alignment.build_matrix`: about `50 sec`

The timing log contains both aggregate and per-sample stages, so it should not
be summed naively as a single exact runtime. It is still useful for bottleneck
ranking.

## Main Bottleneck Interpretation

The base alignment is acceptable for 85RAW validation, but the current preset
default still performs heavy standard-peak evidence generation for the whole
review queue. That makes the run expensive even when the final matrix decision
does not need every human-facing image.

The costly part is not only writing `7307` values. The expensive part is the
productization chain around those decisions:

- RAW-backed evidence extraction for review candidates;
- shift-aware gate calibration outputs;
- authority bundle outputs;
- shadow projection outputs;
- per-chunk productization artifacts;
- reconciliation gallery images and HTML.

For a production preset, publication and review explanation should be separable.

## Optimization Implications

Recommended next optimization direction:

1. Keep `--preset dna_dr` as the one-command product entry point.
2. Make matrix publication cheap and default.
3. Move full gallery generation behind an explicit review mode, or make it
   selective.
4. Always emit compact audit TSV/JSON for every decision, even when images are
   not generated.
5. Generate images only for rows that need human attention, for example:
   ambiguous rows, blocked rows, visual-only candidates, low-margin machine
   positives, conflict/warning rows, or a capped top-N review queue.
6. Preserve an on-demand rehydration path from audit TSV/JSON back to specific
   PNG overlays.

The useful product split is:

- Product default: final matrix, identity sidecar, manifest, activation summary,
  value delta, and compact provenance hashes.
- Review mode: selected gallery rows and richer overlays.
- Deep audit mode: exhaustive image/evidence generation for calibration or
  debugging.

## Product Semantics Confirmed

The run confirms that the default final matrix can now be understood as:

> primary detected values plus automatically accepted standard-peak same-peak
> backfill values, with formal backups and activation deltas.

The run does not confirm automatic handling of non-standard peaks. Those remain
review-only and should not be silently pulled into the default final matrix.

## Follow-Up Questions For Optimization

The next design pass should answer these questions before changing defaults:

- What is the minimal artifact set needed to trust a published standard-peak
  value without opening a PNG?
- Which decision classes require gallery images by default?
- Should `dna_dr` default to `matrix-only` publication and require an explicit
  flag for full gallery generation?
- Can existing audit TSV/JSON support on-demand overlay rendering without
  re-running the whole standard-peak chain?
- Which stages are mandatory for publication and which are purely explanatory?

## Verification Performed After The Run

Focused regression:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q `
  tests/test_presets_loader.py `
  tests/test_presets_apply.py `
  tests/test_presets_builtins.py `
  tests/test_standard_peak_backfill_preset.py `
  tests/test_standard_peak_backfill_machine_pipeline.py `
  tests/test_standard_peak_backfill_chunk_consolidation.py `
  tests/test_standard_peak_shadow_activation_inputs.py `
  tests/test_shift_aware_standard_peak_gate_calibration.py `
  tests/test_shift_aware_backfill_calibration_pack.py `
  tests/test_shadow_production_projection.py `
  tests/test_standard_peak_backfill_productization.py `
  tests/test_standard_peak_ms1_authority_bundle.py `
  tests/test_backfill_evidence_reconciliation_gallery.py `
  tests/test_family_ms1_alignment_experiment_batch.py `
  tests/test_run_alignment.py
```

Result: `181 passed`.

Lint:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tools tests scripts\run_alignment.py
```

Result: passed.

Type check:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Result: passed.

Patch hygiene:

```powershell
git diff --check
```

Result: no whitespace errors; only expected Windows CRLF warnings.
