# P8b 85RAW Super-Window Acceptance Note

## Verdict

`production_candidate` for opt-in `validation-minimal + super-window` 85RAW
validation.

The 85RAW super-window run completed successfully, produced the machine
handoff artifacts, and matched the previous 85RAW production-equivalent output
byte-for-byte for the primary TSVs.

The CLI default remains `exact`; super-window is still an explicit opt-in
strategy until promotion is approved.

## Command

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index output\phase1_p2b_85raw_validation\discovery\dR\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow --output-level validation-minimal --resolver-mode region_first_safe_merge --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --timing-output output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\timing.json --timing-live-output output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\timing.live.json
```

Result: exit code `0`, wall-clock `620.9 s`.

## Artifacts

- `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\alignment_matrix.tsv`
- `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\alignment_review.tsv`
- `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\alignment_cells.tsv`
- `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\skipped_evidence_ledger.tsv`
- `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\alignment_run_metadata.json`
- `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\timing.json`
- `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\timing.live.json`
- `output\phase1_p8b_superwindow\diagnostics\owner_backfill_economics_85raw_superwindow\owner_backfill_request_economics.json`
- `output\phase1_p8b_superwindow\diagnostics\alignment_decision_report_85raw_superwindow_strict_reliability_complete\alignment_decision_report.html`
- `output\phase1_p8b_superwindow\diagnostics\targeted_istd_rt_trend_85raw\xic_results_process_w4_with_istd_rt_trend.xlsx`
- `output\phase1_p8b_superwindow\diagnostics\targeted_istd_rt_trend_85raw\targeted_istd_rt_drift_summary.tsv`

The background process launch attempts in this shell environment exited without
stdout/stderr/timing output, so the acceptance run was executed foreground with
the same heartbeat settings. The final heartbeat artifact was still produced and
matches `timing.json`.

## Equivalence

Compared against:

`output\phase1_p75_85raw_reentry\alignment\85raw_production_equivalent_monitored`

Primary output hashes:

- `alignment_matrix.tsv`: byte-identical
- `alignment_review.tsv`: byte-identical
- `alignment_cells.tsv`: byte-identical

Targeted ISTD benchmark compared against:

`output\phase1_p75_85raw_reentry\diagnostics\targeted_istd_benchmark_85raw_production_equivalent`

- `targeted_istd_benchmark_summary.tsv`: byte-identical

## Performance

| Run | owner_backfill elapsed | RAW chromatogram calls |
|---|---:|---:|
| Previous 85RAW production-equivalent monitored run | 1472.14 s | unavailable in old timing metrics |
| P8b 85RAW super-window run | 181.30 s | 679 |

New owner-backfill metrics:

- `extract_xic_count`: 160,939
- `extract_xic_batch_count`: 679
- `raw_chromatogram_call_count`: 679
- `mean_xic_per_raw_chromatogram_call`: 237.02
- `point_count`: 109,254,070

Super-window fetches wider union traces, so total point count is large. This is
expected; traces are cropped before peak picking and primary TSVs are
byte-identical to the exact-window validation run.

## Targeted Benchmark

Command:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.targeted_istd_benchmark --targeted-workbook output\phase1_p2b_85raw_validation\targeted\region_first_safe_merge\tissue_85raw_region_first_safe_merge\xic_results_process_w4.xlsx --alignment-dir output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow --output-dir output\phase1_p8b_superwindow\diagnostics\targeted_istd_benchmark_85raw_superwindow
```

Result: exit code `1`, same benchmark status as the previous 85RAW
production-equivalent run.

Status:

- PASS: `d3-5-hmdC`
- PASS: `d3-5-medC`
- FAIL `AREA_MISMATCH`: `d4-N6-2HE-dA`
- PASS: `15N5-8-oxodG`
- PASS inactive: `[13C,15N2]-8-oxo-Guo`
- FAIL `AREA_MISMATCH`: `d3-N6-medA`
- PASS: `d3-dG-C8-MeIQx`

No new RT, identity, or coverage failure was introduced by super-window.

## Decision Report

Command:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.alignment_decision_report --alignment-dir output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow --targeted-istd-benchmark-json output\phase1_p8b_superwindow\diagnostics\targeted_istd_benchmark_85raw_superwindow_strict_reliability\targeted_istd_benchmark.json --owner-backfill-economics-json output\phase1_p8b_superwindow\diagnostics\owner_backfill_economics_85raw_superwindow\owner_backfill_request_economics.json --timing-json output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow\timing.json --known-istd-exception d4-N6-2HE-dA:AREA_MISMATCH --known-istd-exception d3-N6-medA:AREA_MISMATCH --output-html output\phase1_p8b_superwindow\diagnostics\alignment_decision_report_85raw_superwindow_strict_reliability_complete\alignment_decision_report.html
```

Result: exit code `0`, verdict `WARN`.

Machine summary:

- ISTD pass: `3`
- ISTD warning: `1` (`d3-5-medC` strict targeted reliability warning)
- ISTD known exceptions: `2` (`d4-N6-2HE-dA`, `d3-N6-medA`)
- ISTD fail / unhandled failures: `0`

Interpretation: the decision report no longer escalates strict targeted
reliability `WARN` rows into hard failures. The two `AREA_MISMATCH` rows are
recorded as known exceptions, so the run remains a P2B `production_candidate`
with warning-level evidence rather than `no_go`.

## Remaining Risk

- `AREA_MISMATCH` remains a benchmark-level strict-area policy issue, not a
  super-window regression. The previous and current benchmark summaries are
  byte-identical.
- Follow-up triage split the two `AREA_MISMATCH` rows into different
  categories:
  `docs\superpowers\notes\2026-05-26-p2b-area-mismatch-triage-note.md`.
  `d4-N6-2HE-dA` is an isotope-shift area-comparison artifact; `d3-N6-medA`
  has target-side ISTD RT trend evidence showing the widest global RT range
  among ISTDs (`2.1538 min`) while remaining locally coherent against a `±4`
  injection rolling median (`local p95 = 0.0483 min`). Both are non-blocking
  for P2B and should remain warning / row-level review evidence, not `no_go`
  evidence.
- Super-window is still explicit opt-in. Promotion to default should be a
  separate decision after review.
