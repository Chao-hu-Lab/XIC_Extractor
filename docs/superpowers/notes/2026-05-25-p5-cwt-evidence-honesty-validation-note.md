# P5 CWT Evidence Honesty Validation Note

**Date:** 2026-05-25
**Verdict:** `audit_only` implemented and 8RAW-targeted validated.

## What Changed

- Added model docstrings documenting legacy CWT numeric fields as
  audit-presence flags, not real CWT scale or ridge metrics.
- Wrapped the positive-finite CWT same-apex check with a legacy-presence helper
  while keeping behavior unchanged.
- Added `cwt_audit_filter_reason` to `peak_candidate_boundaries.tsv`.
- Marked source-only `cwt_width` boundary rows with
  `legacy_cwt_width_not_real_cwt`.

No production peak selection, scoring weight, `region_safe_merge.py`, or
`enumerate_boundary_hypotheses` default source set was intentionally changed.

## Verification

Focused P5 tests:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_peak_scoring.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_table.py tests\test_peak_candidate_audit.py -q
```

Observed before this note was written: `126 passed`.

8RAW targeted refresh:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m scripts.validation_harness --suite tissue-8raw --output-root output\phase1_p1_resolver_default_validation\targeted --run-id region_first_safe_merge --resolver-mode region_first_safe_merge --setting emit_peak_candidates=true --setting keep_intermediate_csv=true
```

Observed result: exit `0`, output workbook
`output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx`.

TSV audit counts after refresh:

- `peak_candidates.tsv`: 172 rows
- `peak_candidate_boundaries.tsv`: 529 rows
- `boundary_sources == cwt_width`: 44 rows
- `cwt_audit_filter_reason == legacy_cwt_width_not_real_cwt`: 44 rows
- `boundary_sources == cwt_width` with empty marker: 0 rows
- non-`cwt_width` rows with marker: 0 rows

The validation harness emitted existing `PeakPropertyWarning` messages from
width/prominence calculations and still exited `0`.

## Remaining Risk

P5 does not introduce real CWT ridge tracking. It only prevents the current
legacy CWT numeric fields and `cwt_width` boundary rows from being mistaken for
real wavelet evidence. A real CWT upgrade remains P5b / future scope.

P5 does not unblock P2b and does not trigger P6.
