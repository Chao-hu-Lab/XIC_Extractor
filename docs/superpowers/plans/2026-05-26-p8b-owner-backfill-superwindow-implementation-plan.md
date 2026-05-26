# P8b Owner Backfill Super-Window Implementation Plan

## Verdict

Proceed with a narrow, opt-in super-window extraction path for owner backfill.
The goal is to reduce Thermo RAW chromatogram calls while preserving the exact
production-equivalent matrix. This is not a scoring, RT, boundary, or area
policy change.

## Context

The 8-RAW locality probe showed the current scan-window-aware batching is
already near its exact-window lower bound:

- Exact request count: 14,140
- Exact chunked RAW calls: 5,660
- Super-window estimate: 56 calls at span factor 2
- One-sample microbenchmark: 738 exact calls to 7 super-window calls, with no
  raw trace mismatch after cropping

The remaining optimization target is therefore not larger `raw_xic_batch_size`;
it is merging overlapping scan windows, fetching the union window once, and
cropping each trace back to its original request window before peak picking.

## Now

1. Add an explicit owner backfill window strategy contract.
   - CLI: `--owner-backfill-window-strategy exact|super-window`
   - Default: `exact`
   - Add `--owner-backfill-superwindow-span-factor`, default `2`, only used by
     `super-window`.
   - Record strategy and span factor in run timing/config metadata.

2. Add source support needed by exact-preserving super-windows.
   - Add `retention_time_for_scan(scan_number)` to RAW-backed sources.
   - Delegate it through `TimedRawSource` and `_TimedProcessRawSource`.
   - If a source cannot resolve scan windows and scan RTs, deterministically
     fall back to the current exact-window batching path. Unit tests must cover
     this fallback so unsupported sources do not fail or change results.

3. Implement super-window extraction inside `owner_backfill.py`.
   - Keep `_scan_window_aware_chunks` as the exact strategy.
   - Add a small helper that groups overlapping scan windows per sample.
   - Merge only when the merged scan span is no more than
     `max_individual_span * span_factor`.
   - Convert the merged scan span back to RT bounds for the union request.
   - Fetch union traces with `_extract_many`.
   - Crop returned traces to each original request scan window before calling
     `_backfill_feature_sample_trace`.
   - Preserve feature-major output ordering and existing best-rescue selection.

4. Wire process backend and CLI.
   - Add strategy/span fields to `OwnerBackfillSampleJob`.
   - Pass fields through `run_owner_backfill_process`,
     `extract_owner_backfill_sample_job`, and serial `run_alignment`.
   - Keep `ms1_index_hybrid` validation raw confirmation on the exact strategy
     in this implementation. Do not combine approximate-backend validation with
     super-window optimization until there is separate unit and real-data parity
     evidence for that path.

5. Add tests before implementation.
   - Owner backfill super-window batches overlapping requests into one union RAW
     request and crops traces back to original windows.
   - Super-window falls back to exact batching when scan-window or scan-RT
     methods are unavailable.
   - Output order stays feature-major/sample-major.
   - Process job payload remains pickleable and forwards strategy/span fields.
   - CLI parses and forwards strategy/span fields; invalid span factor is
     rejected by the existing positive-int parser.

## Validation

1. Focused unit tests:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py tests\test_run_alignment.py -q
```

2. Broader related suite:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py tests\test_run_alignment.py tests\test_alignment_pipeline.py tests\test_alignment_pipeline_timing.py -q
```

3. 8-RAW validation-minimal super-window run:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow --output-level validation-minimal --resolver-mode region_first_safe_merge --backfill-scope production-equivalent --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --timing-output output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow\timing.json --timing-live-output output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow\timing.live.json
```

4. Compare against the P8a exact validation-minimal output:

```powershell
Get-FileHash output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal_auto\alignment_matrix.tsv
Get-FileHash output\phase1_p8b_superwindow\alignment\8raw_validation_minimal_superwindow\alignment_matrix.tsv
```

If byte hashes differ, run row/column diff before declaring failure, because
metadata or ordering drift may be distinguishable from quantitative drift.

5. Targeted ISTD benchmark on the super-window output. Known strict area
mismatches may still fail the benchmark; RT/identity regressions are blocking.

## Stop Conditions

- Any RT/apex shift in 8-RAW parity output blocks promotion.
- Any identity/status/matrix row drift blocks promotion unless proven to be a
  metadata-only artifact.
- Any area drift caused by using uncropped union traces blocks promotion.
- If super-window cannot prove 8-RAW parity, keep the implementation behind the
  explicit CLI flag and report it as `diagnostic_only`.

## Later

- Only after 8-RAW parity passes, decide whether `validation-fast` should enable
  `super-window` by default.
- Only after 85-RAW profiling confirms the same bottleneck, consider making
  super-window part of the normal production-equivalent validation profile.
- Do not start a broad P8 rewrite until this exact-preserving optimization is
  either accepted or rejected with evidence.

## Not In Scope

- Changing peak picking, RT acceptance, boundary selection, baseline correction,
  owner-family identity logic, or matrix consolidation.
- Changing `.raw` as the first-class input source.
- Making `.xlsx` or HTML validation artifacts part of the delivery contract.
