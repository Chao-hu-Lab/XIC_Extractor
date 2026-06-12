# Standard-Peak Matrix-Only Bottleneck Optimization Note

Date: 2026-06-11

Validation status: `production_candidate` for 8RAW matrix-only publication; 85RAW
was intentionally not rerun.

## Decision Closed

The previous 8RAW matrix-only vs deep-audit parity artifacts showed that the
base alignment timing was not the bottleneck. The expensive tail was the
post-alignment standard-peak preset, especially
`shift_aware_alignment_experiment`, which rendered PNG review images even in
matrix-only publication mode.

Matrix-only publication now keeps the machine-readable shift-aware summary TSVs
required by the calibration pack and standard-peak gate, but skips PNG review
rendering. Deep-audit and review-gallery remain the image/gallery paths.

`--timing-output` and `--timing-live-output` now include `standard_peak.*` preset
tail stages, so HEARTBEAT monitoring can see the actual post-alignment work.

## Implementation Surface

- `tools/diagnostics/family_ms1_alignment_experiment.py`: added `--no-images`
  to write summary TSVs without PNG rendering; later added an in-process runner
  plus normalized-trace caching for best-shift source-family shape search; the
  latest pass vectorizes the candidate-shift median-curve/Pearson inner loop.
- `tools/diagnostics/family_ms1_alignment_experiment_batch.py`: added
  `--no-images`, summary-only reuse semantics, standard-peak timing spans,
  batch source-family provenance preload, and opt-in incremental summary writes.
- `tools/diagnostics/standard_peak_backfill_machine_pipeline.py`: matrix-only
  now passes summary-only shift-aware mode and records `shift_aware_render_images`.
- `tools/diagnostics/standard_peak_backfill_preset.py`: propagates timing
  recorder through retained gate, chunks, consolidation, and summary write.
- `scripts/run_alignment.py`: propagates the timing recorder into the preset
  runner and supports explicit publication mode override.
- `docs/agent-parameter-settings.md` and `tools/diagnostics/INDEX.md`: updated
  the matrix-only/deep-audit contract.

## Fresh 8RAW Validation

Command:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --preset dna_dr `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\standard_peak_publication_matrix_only_8raw_no_images_20260611 `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\standard_peak_publication_matrix_only_8raw_no_images_20260611\timing.json `
  --timing-live-output output\standard_peak_publication_matrix_only_8raw_no_images_20260611\timing.live.json
```

Result:

- Exit code: `0`
- Wall-clock observed by shell: `232.6 s`
- Preset summary: `status=pass`, `publication_mode=matrix-only`,
  `coverage_status=complete`, `review_queue_row_count=273`,
  `chunk_count=3`, `matrix_cells_written=386`
- PNG count under the new run root: `0`
- Shift-aware output sizes:
  - `r1_120`: 482 files, 0.27 MB, 0 PNG
  - `r121_240`: 482 files, 0.33 MB, 0 PNG
  - `r241_273`: 134 files, 0.09 MB, 0 PNG
- `timing.live.json` contains `586` `standard_peak.*` records.
- Largest measured stage sums from the new timing recorder:
  - `standard_peak.chunk`: 194.23 s
  - `standard_peak.shift_aware_batch`: 138.03 s
  - `standard_peak.shift_aware_batch.row`: 136.55 s
  - `standard_peak.overlay_batch`: 42.69 s
  - `alignment.build_owners.extract_xic`: 15.59 s

Chunk summaries:

| Chunk | Status | Evidence mode | Shift images | Rendered images | Overlay rows | Shift rows | Written |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `r1_120` | `pass` | `evidence_only` | `False` | 0 | 120 | 120 | 266 |
| `r121_240` | `pass` | `evidence_only` | `False` | 0 | 120 | 120 | 120 |
| `r241_273` | `pass` | `evidence_only` | `False` | 0 | 33 | 33 | 0 |

## Product Parity

The new matrix-only run was hash-identical to both canonical 2026-06-10
matrix-only and canonical 2026-06-10 deep-audit for product-affecting artifacts:

| Artifact | New equals old matrix-only | New equals old deep-audit |
| --- | --- | --- |
| `alignment_matrix.tsv` | `True` | `True` |
| `alignment_matrix_identity.tsv` | `True` | `True` |
| `standard_peak_activation_value_delta.tsv` | `True` | `True` |
| `standard_peak_activation_hypothesis_identity.tsv` | `True` | `True` |
| `standard_peak_activation_application_summary.tsv` | `True` | `True` |
| `standard_peak_activation_decisions.tsv` | `True` | `True` |
| `standard_peak_activation_values.tsv` | `True` | `True` |
| `standard_peak_activation_acceptance.tsv` | `True` | `True` |

## Shift-Aware Row Computation Optimization

After the image-free 8RAW run, the remaining dominant standard-peak tail was
summary-only shift-aware row computation. A no-RAW micro timing on the existing
`r1_120` overlay trace JSONs showed:

| Probe | Total | `build_source_family_best_shift_plan` | Cell evidence load |
| --- | ---: | ---: | ---: |
| Pre-cache path | 44.35 s | 38.40 s | 4.30 s across 120 loads |
| Normalized-trace cache + batch preload | 13.73 s | 12.41 s | 0.03 s across 1 load |

The optimized no-RAW probe over all three 8RAW chunks reran 273 rows in
41.91 s and produced byte-identical per-row summary TSVs versus the previous
matrix-only run (`changed_tsv=0`, excluding the intentionally removed
non-preset incremental batch summary file).

Fresh 8RAW command:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --preset dna_dr `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\standard_peak_publication_matrix_only_8raw_shift_cache_20260611 `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --standard-peak-backfill-publication-mode matrix-only `
  --timing-output output\standard_peak_publication_matrix_only_8raw_shift_cache_20260611\timing.json `
  --timing-live-output output\standard_peak_publication_matrix_only_8raw_shift_cache_20260611\timing.live.json
```

Result:

- Exit code: `0`
- Wall-clock observed by shell: `136.2 s`
- Preset summary: `status=pass`, `publication_mode=matrix-only`,
  `coverage_status=complete`, `review_queue_row_count=273`,
  `chunk_count=3`, `matrix_cells_written=386`
- PNG count under the run root: `0`
- Product artifact hashes are identical to the previous matrix-only no-images
  run, canonical 2026-06-10 matrix-only, and canonical 2026-06-10 deep-audit.

Largest measured stage sums after this pass:

| Stage | Previous no-images | Shift-cache run |
| --- | ---: | ---: |
| `standard_peak.chunk` | 194.23 s | 93.24 s |
| `standard_peak.shift_aware_batch` | 138.03 s | 37.49 s |
| `standard_peak.shift_aware_batch.row` | 136.55 s | 36.92 s |
| `standard_peak.overlay_batch` | 42.69 s | 42.64 s |

## Remaining Bottleneck

The remaining 8RAW matrix-only cost is no longer PNG rendering or repeated
source-family best-shift normalization. The largest remaining product-tail
stage is `standard_peak.overlay_batch` at about 42.6 s, which is RAW trace
extraction plus trace JSON/summary writing. Further performance work should
target overlay RAW access locality/reuse or a more aggressive, parity-checked
vectorization of the residual best-shift correlation loop.

## Overlay RAW Access Optimization

Implementation surface:

- `family_ms1_overlay_batch.py` now records overlay extraction metrics in
  `family_ms1_overlay_batch_summary.json`.
- Standard-peak preset in-process callers invoke `run_overlay_batch()` directly
  and write final batch outputs once, instead of using the standalone CLI path
  that rewrites summary/Markdown after each row for resumability.
- Overlay RAW extraction remains sample-batched, but now groups overlapping
  scan windows into bounded super-windows with span factor 2, extracts the union
  window, then crops each returned trace back to its original scan window.

Fail-fast locality probe on the existing 8RAW queue showed exact scan-window
batching had little reuse:

| Chunk | Trace requests | Exact RAW calls | Super-window calls |
| --- | ---: | ---: | ---: |
| `r1_120` | 918 | 794 | 48 |
| `r121_240` | 846 | 650 | 40 |
| `r241_273` | 213 | 198 | 33 |

Overlay-only RAW probes with the optimized code:

| Chunk | Wall time | RAW calls | Mean XIC / RAW call |
| --- | ---: | ---: | ---: |
| `r1_120` | 6.48 s | 48 | 19.13 |
| `r121_240` | 5.71 s | 40 | 21.15 |
| `r241_273` | 4.50 s | 33 | 6.45 |

Normalized trace JSON parity against the previous shift-cache run passed for
all 273 overlay trace JSONs after ignoring path-only provenance differences.
Trace arrays and evidence summaries were unchanged.

Fresh 8RAW command:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --preset dna_dr --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\standard_peak_publication_matrix_only_8raw_overlay_superwindow_final_20260611 --expected-sample-count 8 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --standard-peak-backfill-publication-mode matrix-only --timing-output output\standard_peak_publication_matrix_only_8raw_overlay_superwindow_final_20260611\timing.json --timing-live-output output\standard_peak_publication_matrix_only_8raw_overlay_superwindow_final_20260611\timing.live.json
```

Result:

- Exit code: `0`
- Wall time: 114.3 s
- Preset status: `pass`
- Publication mode: `matrix-only`
- Coverage status: `complete`
- Review queue rows: `273`
- Matrix cells written: `386`
- PNG count: `0`
- Validation status: `production_candidate` for 8RAW matrix-only; 85RAW was
  not run.

Largest measured stage sums after overlay super-window:

| Stage | Shift-cache run | Overlay super-window run |
| --- | ---: | ---: |
| `standard_peak.chunk` | 93.24 s | 71.94 s |
| `standard_peak.overlay_batch` | 42.64 s | 18.75 s |
| `standard_peak.shift_aware_batch` | 37.49 s | 39.08 s |
| `standard_peak.shift_aware_batch.row` | 36.92 s | 38.49 s |

Product artifact hashes are unchanged versus the previous shift-cache run,
canonical 2026-06-10 matrix-only, and canonical 2026-06-10 deep-audit for
`alignment_matrix.tsv`, `alignment_matrix_identity.tsv`,
`standard_peak_activation_value_delta.tsv`,
`standard_peak_activation_hypothesis_identity.tsv`,
`standard_peak_activation_application_summary.tsv`,
`standard_peak_activation_decisions.tsv`,
`standard_peak_activation_values.tsv`, and
`standard_peak_activation_acceptance.tsv`.

After the overlay pass, before vectorized best-shift work, the largest
remaining standard-peak tail was shift-aware row computation at about 38.9 s,
followed by overlay RAW extraction at about 18.8 s. Further gains should target
residual shift-aware correlation work or broader base alignment/owner-backfill
timings, not request-level overlay dedupe; the 8RAW queue had no exact
`(sample, mz, RT window, ppm)` duplicates.

## Shift-Aware Best-Shift Vectorization

Focused no-RAW profiling on the existing `r1_120` overlay summaries confirmed
the residual shift-aware cost was algorithmic, not RAW or TSV I/O:

| Probe | Total wall | `build_source_family_best_shift_plan` | Inner loop |
| --- | ---: | ---: | ---: |
| Scalar candidate-shift loop | 20.73 s | 19.10 s | 18.91 s |
| Vectorized curve/Pearson + small-stack median | 4.98 s | 3.33 s | 3.11 s |

Implementation details:

- `_best_source_family_shape_shift()` now builds all candidate shifted median
  curves for a source family as one matrix instead of recomputing one shift at
  a time.
- `_pearson_similarity_vector()` screens the full candidate matrix, then the
  selected winning curve is re-scored with the existing scalar
  `_pearson_similarity()` before writing output.
- `_nanmedian_small_axis1()` avoids `np.nanmedian` warning overhead for the
  small trace stacks used by source-family groups.
- `tests/test_family_ms1_alignment_experiment.py` includes a scalar-loop
  equivalence test for the vectorized search.

No-RAW all-chunk probe:

| Chunk | Wall time | Rows | Status |
| --- | ---: | ---: | --- |
| `r1_120` | 4.12 s | 120 | `rendered=120` |
| `r121_240` | 4.61 s | 120 | `rendered=120` |
| `r241_273` | 1.23 s | 33 | `rendered=33` |
| Total | 9.96 s | 273 | `changed_shift_tsv=0` |

Fresh 8RAW command:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --preset dna_dr --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\standard_peak_publication_matrix_only_8raw_shift_vectorized_final_20260611 --expected-sample-count 8 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --standard-peak-backfill-publication-mode matrix-only --timing-output output\standard_peak_publication_matrix_only_8raw_shift_vectorized_final_20260611\timing.json --timing-live-output output\standard_peak_publication_matrix_only_8raw_shift_vectorized_final_20260611\timing.live.json
```

Result:

- Exit code: `0`
- Wall time: `70.9 s`
- Preset status: `pass`
- Publication mode: `matrix-only`
- Coverage status: `complete`
- Review queue rows: `273`
- Matrix cells written: `386`
- PNG count: `0`
- Validation status: `production_candidate` for 8RAW matrix-only; 85RAW was
  not run.

Largest measured stage sums after vectorized best-shift:

| Stage | Overlay super-window run | Vectorized best-shift run |
| --- | ---: | ---: |
| `standard_peak.chunk` | 71.94 s | 37.42 s |
| `standard_peak.shift_aware_batch` | 39.08 s | 10.61 s |
| `standard_peak.shift_aware_batch.row` | 38.49 s | 10.04 s |
| `standard_peak.overlay_batch` | 18.75 s | 15.66 s |
| `alignment.owner_backfill` | 16.99 s | 12.35 s |
| `alignment.build_owners.extract_xic` | 14.93 s | 12.14 s |

Product artifact hashes are unchanged versus the overlay super-window run,
canonical 2026-06-10 matrix-only, and canonical 2026-06-10 deep-audit for
`alignment_matrix.tsv`, `alignment_matrix_identity.tsv`,
`standard_peak_activation_value_delta.tsv`,
`standard_peak_activation_hypothesis_identity.tsv`,
`standard_peak_activation_application_summary.tsv`,
`standard_peak_activation_decisions.tsv`,
`standard_peak_activation_values.tsv`, and
`standard_peak_activation_acceptance.tsv`.

After this pass the largest remaining standard-peak tail is overlay RAW
extraction at about 15.7 s, with base owner RAW extraction and owner backfill
now in the same range. Additional gains likely need RAW extraction locality in
base alignment/owner-backfill or a broader preset orchestration pass; the
highest-yield shift-aware algorithmic waste has been removed for 8RAW.

## Overlay Scan-RT Cache Follow-Up

Follow-up no-RAW cleanup on `family_ms1_overlay_batch.py` removed a remaining
locality leak inside the overlay super-window path:

- one per-RAW-handle scan-number to retention-time cache is now shared across
  super-window grouping, union-window request construction, and crop-back to
  the original scan window;
- this does not change request grouping, extracted trace arrays, output schema,
  or product activation artifacts;
- the focused characterization shows the same two-request overlapping-window
  sample now resolves each boundary scan once instead of 2-3 times.

Focused verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_batch.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 1 source file.
No new 8RAW or 85RAW validation was launched for this micro-optimization.
