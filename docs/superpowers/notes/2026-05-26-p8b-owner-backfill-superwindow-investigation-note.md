# P8b Owner Backfill Super-Window Investigation Note

Status: `implementation_candidate_needs_plan`

Date: 2026-05-26

## Question

After P8a output thinning, 85RAW is still dominated by owner backfill. The open
question was whether the remaining cost is caused by poor chunking or by the
deeper exact-window contract.

## Finding 1: Exact Scan-Window Chunking Is Already At Its Lower Bound

Command:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.backfill_scope_probe `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p8a_validation_minimal\diagnostics\backfill_scope_probe_8raw_locality `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --raw-workers 8 `
  --raw-xic-batch-size 64 `
  --emit-locality
```

Result:

| Metric | Value |
|---|---:|
| `extract_request_count` | 14,140 |
| `scan_window_aware_chunk_count` | 235 |
| `chunked_raw_chromatogram_call_count` | 5,660 |
| `unique_scan_window_count` | 5,660 |
| `mean_xic_per_chunked_raw_call` | 2.50 |

Interpretation:

- Current owner_backfill already sorts and chunks by exact scan window.
- The observed 8RAW timing value was also 5,660 raw chromatogram calls.
- Therefore, increasing `raw_xic_batch_size` or re-sorting exact windows cannot
  materially improve this path.

## Finding 2: Super-Window Has Large Theoretical Headroom

Same probe, per-sample overlap merge only:

| Strategy | Estimated raw calls |
|---|---:|
| exact scan-window lower bound | 5,660 |
| super-window max span = 1x max individual window | 2,639 |
| super-window max span = 2x max individual window | 56 |
| super-window max span = 4x max individual window | 24 |

Notes:

- The `2x` and `4x` strategies are not automatically production-safe. They fetch
  wider RT ranges and must crop back to each original request window before peak
  picking.
- The old locality analyzer was stale for P7/P8 because it did not count
  `backfill_seed_centers`; `backfill_scope_probe --emit-locality` now uses the
  production backfill seed logic.

## Finding 3: Raw-Level Super-Window Equivalence Looks Plausible

Artifact:

- `output/phase1_p8a_validation_minimal/diagnostics/raw_superwindow_equivalence_8raw.json`

Result:

- checked groups: 12
- samples: first 4 8RAW samples
- each group: 8 XIC requests
- status: `PASS`
- mismatch count: 0

Meaning:

For the checked RAW groups, extracting a larger union RT window and cropping
back to the original request scan window produced point-identical RT/intensity
traces compared with direct extraction.

## Finding 4: One-Sample Microbenchmark Shows Real Speedup

Artifact:

- `output/phase1_p8a_validation_minimal/diagnostics/superwindow_microbenchmark_8raw_sample.json`

Sample:

- `TumorBC2263_DNA`
- backfill extract requests: 1,864

| Path | Raw calls | Elapsed sec | Trace mismatch |
|---|---:|---:|---|
| exact scan-window batching | 738 | 12.20 | none, reference |
| super-window x1 | 313 | 5.39 | none |
| super-window x2 | 7 | 0.75 | none |
| super-window x4 | 3 | 0.75 | none |

Interpretation:

- The bottleneck is vendor raw chromatogram call count, not Python peak picking
  in this microbenchmark slice.
- Super-window x2 appears to capture most of the benefit without the extra span
  of x4.
- This is still a microbenchmark, not production readiness.

## Decision

P8b is worth planning as a small, contained optimization:

- add an owner-backfill super-window extraction path;
- keep default exact path until parity gates pass;
- crop every union-window trace back to the original request scan bounds before
  calling peak detection;
- validate with synthetic tests, raw-level trace parity, 8RAW matrix parity, and
  targeted ISTD benchmark.

Do not implement it as a hidden replacement without a plan/review gate.

## Proposed Acceptance

For P8b to become usable in validation-fast mode:

1. Unit tests prove super-window extraction preserves request order and crops to
   original scan windows.
2. Real RAW microbenchmark has zero trace mismatches on representative 8RAW
   groups.
3. 8RAW `validation-minimal` matrix/review/cells are parity-equivalent against
   exact owner_backfill, except for explicitly reviewed floating-format noise if
   any appears.
4. Targeted ISTD benchmark still runs from minimal TSV artifacts and does not add
   new RT/identity failures.
5. Timing must improve by any positive amount under result equivalence; no
   arbitrary high threshold.
