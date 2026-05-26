# P7.5 85RAW Re-Entry Validation Note

Status: `production_candidate_for_P7_cost_control`

Date: 2026-05-26

## Goal

Validate the post-P7 production-equivalent 85RAW path before deciding whether
P8 optimization is worth doing.

The run must stay auditable:

- no full-audit 85RAW rerun
- no `.mzML` fallback
- no `ms1-index` production equivalence claim
- `--backfill-scope production-equivalent`
- `--audit-evidence-mode none`
- `--performance-profile validation-fast`
- mandatory `timing.json`
- mandatory `timing.live.json`
- monitor log and timeout status sidecars

P8 remains an optimization pool, not a required large phase. Only profiling
evidence can justify small follow-up optimization.

## Inputs

- Discovery batch index:
  `output/phase1_p2b_85raw_validation/discovery/dR/discovery_batch_index.csv`
- Targeted workbook:
  `output/phase1_p2b_85raw_validation/targeted/region_first_safe_merge/tissue_85raw_region_first_safe_merge/xic_results_process_w4.xlsx`
- RAW root:
  `C:/Xcalibur/data/20260106_CSMU_NAA_Tissue_R`
- DLL dir:
  `C:/Xcalibur/system/programs`

## Preflight

Command:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.backfill_scope_probe `
  --discovery-batch-index output\phase1_p2b_85raw_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p75_85raw_reentry\preflight\backfill_scope_probe_production_equivalent `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --raw-workers 8 `
  --raw-xic-batch-size 64
```

Result:

- status: `complete`
- elapsed: 272.72 s
- raw files: 85
- candidates: 30,289
- clustered features: 21,812
- production-equivalent backfill features: 19,799
- skipped features: 2,013
- skipped evidence rows: 38,976
- estimated extract requests: 1,662,662
- median sample extract requests: 19,546
- max sample extract requests: 19,706

Artifacts:

- `output/phase1_p75_85raw_reentry/preflight/backfill_scope_probe_production_equivalent/backfill_scope_probe.json`
- `output/phase1_p75_85raw_reentry/preflight/backfill_scope_probe_production_equivalent/backfill_scope_probe_sample_requests.tsv`
- `output/phase1_p75_85raw_reentry/preflight/backfill_scope_probe_production_equivalent/backfill_scope_probe_feature_requests.tsv`

## 85RAW Production-Equivalent Run

Command shape:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p2b_85raw_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p75_85raw_reentry\alignment\85raw_production_equivalent_monitored `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --timing-output output\phase1_p75_85raw_reentry\alignment\85raw_production_equivalent_monitored\timing.json `
  --timing-live-output output\phase1_p75_85raw_reentry\alignment\85raw_production_equivalent_monitored\timing.live.json
```

The process was run under a monitor loop with a 5,400 s timeout budget.

Result:

- monitor status: `process_exit`
- exit code: 0
- elapsed: 2,402 s
- build-owner sample completes: 85 / 85
- owner-backfill sample completes: 85 / 85
- owner-backfill sample errors: 0
- heavy audit enabled: `False`
- audit evidence mode: `none`

Key timing:

| Stage | Elapsed sec |
|---|---:|
| `alignment.build_owners` | 19.42 |
| `alignment.cluster_owners` | 87.85 |
| `alignment.backfill_scope` | 87.92 |
| `alignment.owner_backfill` | 1472.14 |
| `alignment.build_matrix` | 2.80 |
| `alignment.claim_registry` | 29.88 |
| `alignment.primary_consolidation` | 75.19 |
| `alignment.write_outputs` | 595.40 |

Owner-backfill timing totals:

- `extract_xic_count`: 1,650,986
- `raw_chromatogram_call_count`: 561,105
- point count: 394,116,526

Artifacts:

- `output/phase1_p75_85raw_reentry/alignment/85raw_production_equivalent_monitored/timing.json`
- `output/phase1_p75_85raw_reentry/alignment/85raw_production_equivalent_monitored/timing.live.json`
- `output/phase1_p75_85raw_reentry/alignment/85raw_production_equivalent_monitored/monitor.log`
- `output/phase1_p75_85raw_reentry/alignment/85raw_production_equivalent_monitored/monitor_status.json`
- `output/phase1_p75_85raw_reentry/alignment/85raw_production_equivalent_monitored/alignment_run_metadata.json`
- `output/phase1_p75_85raw_reentry/alignment/85raw_production_equivalent_monitored/skipped_evidence_ledger.tsv`

Large outputs:

- `alignment_cells.tsv`: 370.8 MB
- `alignment_results.xlsx`: 263.4 MB
- `owner_edge_evidence.tsv`: 163.7 MB
- `alignment_review.tsv`: 10.1 MB
- `skipped_evidence_ledger.tsv`: 10.1 MB

## Targeted ISTD Benchmark

Command:

```powershell
python -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p2b_85raw_validation\targeted\region_first_safe_merge\tissue_85raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p75_85raw_reentry\alignment\85raw_production_equivalent_monitored `
  --output-dir output\phase1_p75_85raw_reentry\diagnostics\targeted_istd_benchmark_85raw_production_equivalent
```

Result:

- overall strict benchmark status: `FAIL`
- active fails: 2
- active warnings: 0
- false-positive tag count: 0

The two failures are area-only strict benchmark failures:

| Target | Status | Failure | Coverage | RT p95 abs delta min | log area Pearson | log area Spearman |
|---|---|---|---:|---:|---:|---:|
| `d4-N6-2HE-dA` | `FAIL` | `AREA_MISMATCH` | 85 / 85 | 0.0416 | 0.5786 | 0.9159 |
| `d3-N6-medA` | `FAIL` | `AREA_MISMATCH` | 85 / 85 | 0.0830 | 0.1386 | 0.5813 |

Passing active ISTDs:

- `d3-5-hmdC`: 85 / 85, RT p95 0.00005 min
- `d3-5-medC`: 85 / 85, RT p95 0 min
- `15N5-8-oxodG`: 85 / 85, RT p95 0 min
- `d3-dG-C8-MeIQx`: 85 / 85, RT p95 0 min

Artifacts:

- `output/phase1_p75_85raw_reentry/diagnostics/targeted_istd_benchmark_85raw_production_equivalent/targeted_istd_benchmark.md`
- `output/phase1_p75_85raw_reentry/diagnostics/targeted_istd_benchmark_85raw_production_equivalent/targeted_istd_benchmark_summary.tsv`
- `output/phase1_p75_85raw_reentry/diagnostics/targeted_istd_benchmark_85raw_production_equivalent/targeted_istd_benchmark.json`

## Decision

P7.5 is a `production_candidate_for_P7_cost_control`.

The optimized 85RAW production-equivalent path completed with full heartbeat
and monitor artifacts. It is no longer operationally blocked by the previous
black-box timeout failure.

The strict targeted ISTD benchmark is still not a `production_ready` claim
because two active ISTDs fail area-correlation thresholds. Those failures are
not RT or identity misses:

- both have 85 / 85 coverage;
- both have acceptable RT p95 absolute delta under the current benchmark
  threshold;
- there are no false-positive tag hits.

Given the current project decision that area mismatch is a review signal rather
than an automatic hard blocker when RT and identity coverage are coherent, this
does not justify a large P8 rewrite.

## P8 Recommendation

Do not open a broad P8 refactor.

Only consider small follow-up optimizations if the user wants shorter 85RAW
turnaround:

1. `owner_backfill` request reduction or request-locality optimization.
   Evidence: 1,650,986 XIC extractions and 561,105 raw chromatogram calls.
2. Output writing reduction for validation runs.
   Evidence: `write_outputs` took 595.40 s and wrote hundreds of MB of TSV/XLSX.
3. Keep heartbeat/reporting improvements cheap and sidecar-only.

Do not pursue:

- Trace / TraceGroup / PeakHypothesis architecture rewrite
- ML or DL peak classifier
- `.mzML` fallback
- `ms1-index` production-equivalence claim
- broad async/cache rewrite

Recommended next step: proceed with P2b follow-up review using the completed
85RAW artifacts, and only create a small P8 plan if the 40 minute 85RAW runtime
is operationally too expensive.
