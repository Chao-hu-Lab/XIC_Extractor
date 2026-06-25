# Gaussian15 MS1 Peak-Group NL Scope Production-Ready Closeout

> Historical closeout note: retained as evidence/provenance, not live
> source-of-truth. Current rerun policy for this gate lives in
> `docs/diagnostic-ledger.md`; durable MS2/NL and Gaussian15 peak-group evidence
> semantics live in `docs/lcms-msms-evidence-rules.md`. Removal or private-note
> migration requires an explicit removal approval plus a repo-self-contained
> referrer pass.

**Date:** 2026-06-05
**Verdict:** `production_ready` for targeted candidate MS2/NL evidence ownership
under Gaussian15 MS1 peak-group scope.

This verdict means selected `chrom_peak_segment` candidates no longer borrow
active MS2/NL support from a different Gaussian15 MS1 peak group. Strict NL
scans outside the selected group remain diagnostic context, not active support
for candidate selection or typed evidence projection.

This does not claim every biological identity is final. Missing DDA/NL,
targeted RT/ISTD conflict, low local quality, and manual EIC/MS2 adjudication
remain separate evidence surfaces.

## Product Behavior

- `neutral_loss.collect_candidate_ms2_evidence()` now accepts optional
  Gaussian15 MS1 peak-group bounds.
- When a scoped group is present, only MS2/NL scans inside that group contribute
  to active `trigger_scan_count`, `strict_nl_scan_count`, `ms2_present`, and
  `nl_match` for the candidate.
- Strict NL outside the selected group is recorded through
  `outside_ms1_peak_group_*` diagnostics and can set
  `strict_nl_outside_ms1_peak_group`, but it is not active candidate support.
- Repeated DDA/NL scans inside the same selected group are counted as multiple
  scans but one chromatographic support event through
  `ms1_peak_group_strict_nl_event_count`.

## Gate

Durable gate:

`tools/diagnostics/ms1_peak_group_nl_scope_gate.py`

The gate consumes `peak_candidates.tsv` and writes:

- `ms1_peak_group_nl_scope_gate_manifest.json`
- `ms1_peak_group_nl_scope_review_rows.tsv`
- `ms1_peak_group_nl_scope_context_rows.tsv`

It fails closed when a selected `chrom_peak_segment` row lacks group scope, uses
an unexpected `ms1_peak_group_source`, has selected apex outside the group
bounds, or appears to borrow active strict NL support from outside the selected
group.

## 8RAW Targeted Gate

Command:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --base-dir C:\Users\user\Desktop\XIC_Extractor --output-root output\gaussian15_ms1_peak_group_nl_scope_8raw_20260605 --run-id nl_peak_group_scope_8raw --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 4 --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --setting emit_peak_candidates=true --setting emit_score_breakdown=true
```

Output:

`output/gaussian15_ms1_peak_group_nl_scope_8raw_20260605/nl_peak_group_scope_8raw/tissue_8raw_region_first_safe_merge/`

Gate manifest:

`output/gaussian15_ms1_peak_group_nl_scope_8raw_20260605/nl_peak_group_scope_8raw/ms1_peak_group_nl_scope_gate/ms1_peak_group_nl_scope_gate_manifest.json`

Key facts:

- `gate_decision=promote`
- `row_count=211`
- `selected_count=96`
- `chrom_candidate_count=111`
- `selected_chrom_count=80`
- `selected_chrom_missing_scope_rows=0`
- `unexpected_ms1_peak_group_source_rows=0`
- `selected_apex_outside_scope_rows=0`
- `borrowed_strict_nl_support_rows=0`
- `selected_chrom_outside_strict_nl_rows=15`
- `context_row_count=15`
- `review_row_count=0`
- `selected_chrom_peak_group_trigger_scan_count=564`
- `selected_chrom_peak_group_strict_nl_scan_count=189`
- `selected_chrom_peak_group_strict_nl_event_count=60`

Sanity diff against the previous Gaussian15 peak-group 8RAW artifact:

- `row_count` remained `211`.
- `selected_count` remained `96`.
- No selected candidate, RT window, area, confidence, reason, or presence drift
  was observed.
- 15 selected rows changed only `trigger_scan_count` /
  `strict_nl_scan_count`, matching the intended removal of outside-group scans
  from active support.

## 85RAW Targeted Gate

Command:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-85raw --confirm-full-run --base-dir C:\Users\user\Desktop\XIC_Extractor --output-root output\gaussian15_ms1_peak_group_nl_scope_85raw_20260605 --run-id nl_peak_group_scope_85raw --resolver-mode region_first_safe_merge --parallel-mode process --parallel-workers 11 --data-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R" --setting emit_peak_candidates=true --setting emit_score_breakdown=true
```

Output:

`output/gaussian15_ms1_peak_group_nl_scope_85raw_20260605/nl_peak_group_scope_85raw/tissue_85raw_region_first_safe_merge/`

Gate manifest:

`output/gaussian15_ms1_peak_group_nl_scope_85raw_20260605/nl_peak_group_scope_85raw/ms1_peak_group_nl_scope_gate/ms1_peak_group_nl_scope_gate_manifest.json`

Key facts:

- `gate_decision=promote`
- `row_count=2334`
- `selected_count=1016`
- `chrom_candidate_count=1184`
- `selected_chrom_count=811`
- `selected_chrom_missing_scope_rows=0`
- `unexpected_ms1_peak_group_source_rows=0`
- `selected_apex_outside_scope_rows=0`
- `borrowed_strict_nl_support_rows=0`
- `selected_chrom_outside_strict_nl_rows=156`
- `selected_chrom_outside_strict_nl_scan_count=163`
- `context_row_count=156`
- `review_row_count=0`
- `selected_chrom_peak_group_trigger_scan_count=5209`
- `selected_chrom_peak_group_strict_nl_scan_count=1941`
- `selected_chrom_peak_group_strict_nl_event_count=603`

Older 85RAW targeted artifacts under the target-pair / morphology phase did not
have the new scope columns and were not used as a parity oracle. Their behavior
also includes unrelated phase changes, so comparing every selected row would mix
this evidence-ownership change with prior target-pair and morphology work.

## Verification

No-RAW and validation checks run in this worktree:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_ms1_peak_group_nl_scope_gate.py tests/test_neutral_loss.py tests/test_candidate_evidence_facts.py tests/test_scoring_context.py tests/test_peak_candidate_table.py
# 71 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools\diagnostics\ms1_peak_group_nl_scope_gate.py
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor tools\diagnostics\ms1_peak_group_nl_scope_gate.py
# Success: no issues found in 295 source files
```

The targeted 8RAW and 85RAW validation harness runs completed with
`tissue-8raw: passed` and `tissue-85raw: passed`.
