# Owner Quantitation Context 8RAW Closeout

**Date:** 2026-06-03
**Readiness label:** `production_candidate`
**Spec:** [AsLS primary matrix value policy spec](../specs/2026-06-02-asls-primary-matrix-value-policy-spec.md)

## Verdict

The owner candidate re-resolution path should no longer treat the discovery
candidate MS1 peak boundary as the whole final quantitation trace context.

The 8RAW rerun supports a candidate-anchored but wider quantitation context as a
product candidate. The change fixes the observed under-integration pattern where
AsLS was applied to a clipped discovery-candidate interval and could therefore
miss the full chromatographic envelope.

This does not promote CWT or safe-merge as product truth. CWT, local minima,
safe-merge, derivative, and region-first logic remain proposal or
model-selection evidence inside the quantitation context.

## Product Change

Owner candidate re-resolution now pads a valid candidate MS1 peak interval by a
bounded quantitation-context margin:

- max padding: `0.40 min`
- upper bound: `config.max_rt_sec / 60`
- fallback broad seed/search windows remain available when candidate peak
  boundaries are missing or invalid

The margin is intentionally a v0 product candidate. It is evidence-backed by the
8RAW watchlist, but it should still be reviewed in 85RAW and in future
model-selection parity work before being treated as final science.

## 8RAW Alignment Command

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\quantitation_context_owner_window_20260603\8raw `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\quantitation_context_owner_window_20260603\8raw\timing.json `
  --timing-live-output output\quantitation_context_owner_window_20260603\8raw\timing.live.json
```

Run result: exit code `0`; wall-clock about `37 s`.

## Key Artifacts

- `output\quantitation_context_owner_window_20260603\8raw\alignment_matrix.tsv`
- `output\quantitation_context_owner_window_20260603\8raw\alignment_cells.tsv`
- `output\quantitation_context_owner_window_20260603\8raw\alignment_review.tsv`
- `output\quantitation_context_owner_window_20260603\8raw\alignment_matrix_identity.tsv`
- `output\quantitation_context_owner_window_20260603\benchmark\owner_quantitation_context_watchlist.tsv`
- `output\quantitation_context_owner_window_20260603\benchmark\owner_quantitation_context_matrix_watchlist.tsv`
- `output\quantitation_context_owner_window_20260603\benchmark\targeted_istd\targeted_istd_benchmark_summary.tsv`
- `output\quantitation_context_owner_window_20260603\benchmark\targeted_istd\d3_N6_medA_sample_area_audit.tsv`
- `output\quantitation_context_owner_window_20260603\benchmark\targeted_istd\d3_N6_medA_BenignfatBC1055_trace_baseline.png`

## Watchlist Outcome

The matrix watchlist showed the expected direction for the previously
under-integrated 5-medC row:

| Target | Sample | Old matrix | New matrix | Ratio |
|---|---|---:|---:|---:|
| 5-medC | BenignfatBC1055_DNA | 4.82098e6 | 3.45056e7 | 7.16 |
| 5-medC | BenignfatBC1151_DNA | 9.92685e6 | 3.87206e7 | 3.90 |
| 5-medC | Breast_Cancer_Tissue_pooled_QC3 | 1.11463e7 | 4.80613e7 | 4.31 |
| 5-medC | NormalBC2312_DNA | 1.28663e7 | 8.40588e7 | 6.53 |
| 5-medC | TumorBC2312_DNA | 8.05575e6 | 9.20988e7 | 11.43 |

The d3-5-medC, d3-N6-medA, d3-dG-C8-MeIQx, and source-cell d4-N6-2HE-dA
watchlist rows also retained detection and generally moved in the expected
direction. The d4 matrix nearest-row helper did not resolve a stable product
row center for every target map entry, so use the source-cell watchlist for d4
rather than treating the matrix helper blanks as misses.

## Targeted ISTD Benchmark

The default 8RAW targeted workbook benchmark completed and wrote artifacts, but
returned exit code `1` because the strict legacy area-correlation gate failed
for one target:

| Target | Detection | RT | Area gate | Notes |
|---|---:|---:|---|---|
| d3-5-hmdC | 8/8 | pass | pass | primary hit `FAM000154` |
| d3-5-medC | 8/8 | pass | pass | primary hit `FAM000030` |
| d4-N6-2HE-dA | 8/8 | pass | pass | primary hit `FAM000815` |
| 15N5-8-oxodG | 8/8 | pass | pass | primary hit `FAM000553` |
| d3-N6-medA | 8/8 | pass | fail | `AREA_MISMATCH`; primary hit `FAM000251` |
| d3-dG-C8-MeIQx | 8/8 | pass | pass | primary hit `FAM001879` |

The d3-N6-medA failure is not a missing-detection or wrong-RT failure in the
8RAW default workbook: the selected primary family had 8/8 positive cells and
zero sample-level apex RT delta. The strict gate failed because the old targeted
workbook linear-edge area order did not fully match the new AsLS primary matrix
area order.

For the strongest changed-row case, `d3-N6-medA / BenignfatBC1055_DNA`:

- targeted workbook area: `4.42123e8`
- detected cell raw area: `4.11751e8`
- AsLS primary matrix area: `2.65253e8`
- AsLS/raw ratio: `0.644206`
- selected boundary: `25.9481-26.3220 min`
- selected apex: `26.1974 min`

The diagnostic plot shows one dominant peak in the target window and a selected
boundary that covers the apex and main envelope. The area drop is therefore an
AsLS baseline/integration-policy difference from the old targeted linear-edge
area, not evidence that owner re-resolution selected the wrong peak.

The newer `output\xic_results_20260512_1200.xlsx` workbook was also checked as
a diagnostic-only reference. It is not a valid hard gate for this 8RAW alignment
because it contains many samples outside the 8RAW subset; it also shows that
d3-N6-medA targeted behavior is not a stable single-area oracle across the
larger sample set.

## Verification

```powershell
python -m pytest tests\test_alignment_ownership.py -q
python -m pytest tests\test_alignment_ownership.py tests\test_alignment_process_backend.py tests\test_alignment_pipeline.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_tsv_writer.py -q
python -m pytest tests\test_targeted_istd_benchmark.py -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\ownership.py tests\test_alignment_ownership.py
```

Observed results:

- `tests\test_alignment_ownership.py`: `14 passed`
- alignment shard: `86 passed`
- `tests\test_targeted_istd_benchmark.py`: `13 passed`
- ruff: `All checks passed`

## Remaining Risk

- The `0.40 min` context margin is a bounded product candidate, not a final
  model-selection policy.
- CWT and safe-merge were evaluated as diagnostic alternatives. In the current
  watchlist, broad local-minimum context and safe-merge were mostly aligned,
  while CWT missed several true peaks or picked weaker local bumps. They should
  remain proposal evidence until model-selection parity can explain changed
  rows.
- The targeted benchmark still has an old area-correlation gate that compares
  targeted linear-edge workbook areas against AsLS matrix areas. That gate
  should be rewritten as a detection, RT, peak-choice, and changed-row review
  oracle before it is reused as a production pass/fail gate.
- 85RAW validation remains the next delivery-scale gate before calling this
  production-ready.
