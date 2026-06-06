# Selected Full-Envelope FE4 8RAW Changed-Row Gate

**Date:** 2026-06-03
**Readiness label:** `diagnostic_only`
**Run status:** `run_ok`
**Gate status:** `externalize`

## Decision

The 8RAW selected-envelope changed-row diagnostic ran successfully, but the
current selected full-envelope boundary path must stay diagnostic/review-only.
It is not eligible for 85RAW scale-up or product wiring yet.

The first real-data run exposed a policy bug: selected-envelope rows could be
accepted even when the candidate envelope collapsed to too few scans or became
narrower than the legacy resolver interval. That can silently decrease area for
low-intensity or resolver-overwide rows, which is exactly the failure mode this
gate is meant to catch.

The implementation was hardened before accepting the gate:

- candidate envelopes below `SelectedEnvelopePolicy.min_scan_count` now
  externalize as `low_scan` with
  `boundary_stop_reason=selected_envelope_too_few_scans`;
- candidate envelopes narrower than the resolver interval now externalize as
  `overmerge_rejected` with
  `boundary_stop_reason=selected_envelope_narrower_than_resolver`.

## Hardened 8RAW Output

Output root:

```text
output/selected_full_envelope_realdata_preflight/fe4_8raw_selected_envelope_hardened_20260603/
```

Primary artifacts:

```text
tissue_8raw_region_first_safe_merge/xic_results_process_w4.xlsx
tissue_8raw_region_first_safe_merge/selected_envelope_diagnostics.tsv
selected_envelope_review_queue/selected_envelope_changed_rows.tsv
selected_envelope_review_queue/selected_envelope_oracle_review_queue.tsv
selected_envelope_review_queue/selected_envelope_diagnostic_manifest.tsv
selected_envelope_review_queue/selected_envelope_review_queue.json
validation_summary.csv
```

Manifest:

```text
gate_decision=externalize
changed_row_count=83
changed_row_denominator=95
high_risk_strata=low_scan;overmerge_rejected
unresolved_blocker_count=38
blocked_reasons=selected_envelope_narrower_than_resolver;selected_envelope_too_few_scans
next_gate=diagnostic_review_only
```

Distribution:

```text
row_boundary_decision:
  accept_candidate = 57
  externalize = 38

boundary_change_class:
  flank_recovered = 45
  overmerge_rejected = 29
  no_change = 12
  low_scan = 9

boundary_stop_reason:
  baseline_return_reached = 57
  selected_envelope_narrower_than_resolver = 29
  selected_envelope_too_few_scans = 9
```

Area delta summary, including externalized rows:

```text
min = -0.53790
p05 = -0.28574
p50 =  0.00796
p95 =  0.04014
max =  0.56080
```

The largest negative area deltas are now externalized instead of accepted. The
largest positive delta remains an accepted flank-recovery row and still needs an
overlay plot / oracle review before it can support promotion.

## Commands

Preflight:

```powershell
Get-Command python | Select-Object -ExpandProperty Source
python --version
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import importlib.util; print('pythonnet', importlib.util.find_spec('pythonnet') is not None); print('pytest', importlib.util.find_spec('pytest') is not None)"
Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation"
Test-Path "C:\Xcalibur\system\programs"
(Get-ChildItem "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" -Filter *.raw | Measure-Object).Count
```

Observed:

```text
python = C:\Python314\python.exe
python --version = 3.14.0
.venv python = 3.13.7
pythonnet = True
pytest = True
RAW dir exists = True
DLL dir exists = True
RAW count = 8
```

Dry-run:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir . --output-root output\selected_full_envelope_realdata_preflight --run-id fe4_8raw_selected_envelope_20260603 --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 4 --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --setting emit_peak_candidates=true --dry-run
```

Hardened run, actual command launched from this session:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir . --output-root output\selected_full_envelope_realdata_preflight --run-id fe4_8raw_selected_envelope_hardened_20260603 --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 4 --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --setting emit_peak_candidates=true
```

The harness writes its reusable command shape in `validation_summary.csv` as
`uv run python ...` because `scripts.validation_harness_core` stores the
framework command template. The observed foreground run above used the documented
RAW-capable `.venv\Scripts\python.exe` runner.

Review queue packaging:

```powershell
python tools\diagnostics\selected_envelope_review_queue.py --selected-envelope-diagnostics-tsv output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_hardened_20260603\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv --output-dir output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_hardened_20260603\selected_envelope_review_queue
```

## Verification

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_policy.py tests/test_selected_full_envelope_diagnostics.py tests/test_selected_envelope_review_queue.py tests/test_selected_full_envelope_projection.py
```

Observed:

```text
34 passed
```

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\selected_envelope.py tests\test_selected_full_envelope_policy.py xic_extractor\peak_detection\selected_envelope_diagnostics.py tests\test_selected_full_envelope_diagnostics.py tools\diagnostics\selected_envelope_review_queue.py tests\test_selected_envelope_review_queue.py
```

Observed:

```text
All checks passed!
```

## Next Gate

Do not run 85RAW and do not wire selected-envelope area into product matrix
behavior from this state.

The bounded next step is to keep this diagnostic externalized and add plot-backed
review for the 83 changed rows, especially:

- all `low_scan` rows;
- all `overmerge_rejected` rows;
- highest area-increase rows that remain `accept_candidate`;
- promotion-critical ISTD/STD pairs.

After review, either refine the boundary policy and rerun 8RAW, or explicitly
keep selected full-envelope behavior as a review-only diagnostic overlay.
