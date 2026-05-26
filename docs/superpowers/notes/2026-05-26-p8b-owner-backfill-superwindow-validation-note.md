# P8b Owner Backfill Super-Window Validation Note

## Verdict

`shadow_ready` for opt-in 8-RAW validation. Super-window owner backfill reduces
RAW chromatogram calls while preserving the P8a exact validation-minimal TSV
outputs byte-for-byte.

It is not promoted to default behavior yet. The CLI default remains `exact`.

## Implementation Scope

- Added `--owner-backfill-window-strategy exact|super-window`.
- Added `--owner-backfill-superwindow-span-factor`, default `2`.
- Added RAW scan-to-RT delegation through `RawFileHandle`, `TimedRawSource`, and
  process-backed timed sources.
- Super-window extraction merges overlapping scan windows, fetches the union
  window once, then crops each returned trace back to the original request scan
  window before peak picking.
- `ms1_index_hybrid` confirmation remains exact for this implementation.

## Unit Verification

```powershell
python -m pytest tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py tests\test_run_alignment.py -q
```

Result: `76 passed`.

```powershell
python -m pytest tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py tests\test_run_alignment.py tests\test_alignment_pipeline.py tests\test_alignment_pipeline_timing.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_pipeline_backends.py -q
```

Result: `111 passed`.

```powershell
python -m py_compile xic_extractor\alignment\owner_backfill.py xic_extractor\alignment\process_backend.py xic_extractor\alignment\pipeline.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\raw_sources.py xic_extractor\raw_reader.py scripts\run_alignment.py
```

Result: passed.

Full `python -m pytest tests -q` result: `2308 passed, 3 failed, 1 skipped`.
The three failures are existing GUI/settings tests outside the P8b touched
surface:

- `tests/test_pipeline_worker.py::test_main_window_run_uses_user_writable_config_dir`
- `tests/test_pipeline_worker.py::test_main_window_load_config_persists_first_run_settings_migration`
- `tests/test_settings_section.py::test_settings_section_saves_canonical_keys_after_canonical_load`

## 8-RAW Validation

Command:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow --output-level validation-minimal --resolver-mode region_first_safe_merge --backfill-scope production-equivalent --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --timing-output output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow\timing.json --timing-live-output output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow\timing.live.json
```

Result: exit code `0`, wall-clock `24.4 s`.

Primary artifact parity against
`output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal_auto`:

- `alignment_matrix.tsv`: byte-identical
- `alignment_review.tsv`: byte-identical
- `alignment_cells.tsv`: byte-identical

Owner backfill timing:

| Run | owner_backfill elapsed | RAW chromatogram calls | XIC batches |
|---|---:|---:|---:|
| P8a exact validation-minimal | 23.10 s | 5,660 | 235 |
| P8b super-window factor 2 | 9.82 s | 56 | 56 |

The super-window run fetched more total trace points because each merged union
window is wider, but the traces are cropped before peak picking and the output
TSVs are byte-identical.

## Targeted Benchmark

Command:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.targeted_istd_benchmark --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx --alignment-dir output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow --output-dir output\phase1_p8b_superwindow\diagnostics\targeted_istd_benchmark_8raw_superwindow
```

Result: exit code `1`, same known strict `AREA_MISMATCH` status as P8a.

Benchmark parity against P8a exact:

- `targeted_istd_benchmark_summary.tsv`: byte-identical
- `targeted_istd_benchmark_matches.tsv`: byte-identical

No new RT or identity failure mode was introduced.

## Remaining Risk

- Super-window is validated on 8-RAW only. It should stay opt-in until 85-RAW
  validation passes.
- Full-suite GUI/settings failures remain outside this task and need a separate
  cleanup if the branch gate requires full green.
- If future backends lack exact scan-to-RT support, the implementation falls
  back to exact batching rather than forcing super-window.
