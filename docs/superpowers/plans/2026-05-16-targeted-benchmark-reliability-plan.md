# Targeted Benchmark Reliability Implementation Plan

> **For agentic workers:** Implement this plan in order. Keep targeted
> reliability diagnostic work separate from untargeted matrix identity changes.

**Goal:** Make targeted extraction reliable enough to serve as an untargeted
benchmark by separating targeted detection from benchmark-eligible evidence.

**Primary spec:** `docs/superpowers/specs/2026-05-16-targeted-benchmark-reliability-spec.md`

**Branch:** `codex/targeted-benchmark-reliability`

**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\targeted-benchmark-reliability`

---

## Current Code Map

- `xic_extractor/extraction/target_extraction.py`
  - coordinates per-target extraction, RT windows, NL checks, candidate MS2
    evidence, ISTD anchor recovery, and diagnostic record creation.
- `xic_extractor/peak_detection/facade.py`
  - builds candidates, scores them when a scoring context exists, selects the
    final candidate, and returns `PeakDetectionResult`.
- `xic_extractor/peak_scoring.py`
  - owns confidence, evidence score, confidence caps, severity labels, and
    score breakdown rows.
- `xic_extractor/output/detection.py`
  - defines current targeted detection acceptance. It is intentionally less
    strict than benchmark eligibility.
- `xic_extractor/output/csv_writers.py`
  - emits `XIC Results` compatible long CSV rows and optional Score Breakdown.
- `tools/diagnostics/targeted_istd_benchmark.py`
  - validates untargeted alignment against targeted ISTD evidence.

## Phase A: Diagnostic Report First

**Files:**

- Create: `tools/diagnostics/targeted_peak_reliability_audit.py`
- Create: `tests/test_targeted_peak_reliability_audit.py`

- [ ] **Step 1: Add loader and classifier tests**

Cover:

- loads `XIC Results` from workbook;
- loads `Score Breakdown` when present;
- missing `Score Breakdown` still reports `score_breakdown_unavailable`;
- `HIGH`/`MEDIUM` confidence with acceptable NL and finite area becomes
  `benchmark_eligible`;
- `LOW` confidence with finite area becomes `targeted_review`;
- `VERY_LOW`, `NL_FAIL`, invalid RT, or invalid area becomes
  `targeted_negative` unless the row still needs manual review context;
- `NO_MS2` with NL-required target becomes `targeted_review`;
- weak area outlier produces `weak_area_rank`;
- known exception annotation does not hard-code reliability state.

- [ ] **Step 2: Implement minimal diagnostic CLI**

CLI:

```powershell
python tools\diagnostics\targeted_peak_reliability_audit.py `
  --targeted-workbook output\xic_results_20260512_1200.xlsx `
  --output-dir output\diagnostics\targeted_peak_reliability_20260516 `
  --known-target-exception d3-N6-medA:AREA_MISMATCH
```

Required outputs:

```text
targeted_peak_reliability_summary.tsv
targeted_peak_reliability_rows.tsv
targeted_peak_reliability.json
targeted_peak_reliability.md
```

The first implementation should read only workbook/CSV artifacts. Do not require
RAW files or rerun extraction.

- [ ] **Step 3: Run narrow tests**

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_targeted_peak_reliability_audit.py -q
```

Expected: pass.

## Phase B: Benchmark Annotation Compatibility

**Files:**

- Modify: `tools/diagnostics/targeted_istd_benchmark.py`
- Modify: `tests/test_targeted_istd_benchmark.py`

- [ ] **Step 1: Add optional reliability input tests**

Cover:

- benchmark behavior is unchanged when no reliability JSON is provided;
- `targeted_review` rows are annotated in matches and summary;
- weak targeted rows do not count as clean targeted positives when strict
  benchmark reliability mode is enabled;
- known targeted exception remains a warning, not a production pass;
- production alignment code does not import the reliability diagnostic.

- [ ] **Step 2: Add optional CLI input**

Add:

```powershell
--targeted-reliability-json <path>
--strict-targeted-reliability
```

Default behavior remains backward compatible. Strict reliability mode may change
the benchmark diagnostic verdict, but it must not change untargeted alignment
outputs.

- [ ] **Step 3: Run compatibility tests**

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_targeted_istd_benchmark.py tests\test_alignment_decision_report.py -q
```

Expected: pass.

## Phase C: Targeted Selection Characterization

**Files:**

- Modify: `tests/test_signal_processing_selection.py`
- Modify: `tests/test_peak_scoring.py`
- Modify only if tests prove a gap: `xic_extractor/peak_scoring.py`,
  `xic_extractor/peak_detection/facade.py`, or
  `xic_extractor/extraction/target_extraction.py`

- [ ] **Step 1: Characterize wrong-peak risk with synthetic traces**

Add tests for:

- strong expected peak beats a weak nearby artifact;
- weak low-area candidate with poor NL/MS2 evidence cannot become
  `benchmark_eligible`;
- recovered RT-prior candidate preserves confidence caps and reasons;
- `NO_MS2` remains review-level evidence unless config explicitly treats it as
  detected.

- [ ] **Step 2: Implement only proven scoring fixes**

Acceptable small fixes:

- preserve score breakdown metadata through recovery paths;
- add a missing confidence cap when existing severity already proves a candidate
  is outside allowed evidence;
- expose a clearer reason label for low confidence.

Do not retune broad thresholds without a real failure fixture.

- [ ] **Step 3: Run targeted extraction tests**

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_signal_processing_selection.py tests\test_peak_scoring.py tests\test_extractor.py tests\test_extractor_pipeline.py -q
```

Expected: pass.

## Phase D: Real-Data Audit

Use existing targeted workbook artifacts first.

Suggested command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\targeted_peak_reliability_audit.py `
  --targeted-workbook output\xic_results_20260512_1200.xlsx `
  --output-dir output\diagnostics\targeted_peak_reliability_20260516 `
  --known-target-exception d3-N6-medA:AREA_MISMATCH
```

Then run the strict ISTD benchmark with optional reliability annotation after
Phase B lands:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python tools\diagnostics\targeted_istd_benchmark.py `
  --targeted-workbook output\xic_results_20260512_1200.xlsx `
  --alignment-dir output\alignment\owner_backfill_workers11_85raw_20260515 `
  --output-dir output\diagnostics\targeted_istd_benchmark_reliability_20260516 `
  --targeted-reliability-json output\diagnostics\targeted_peak_reliability_20260516\targeted_peak_reliability.json `
  --strict-targeted-reliability
```

## Validation Checklist

- `d3-N6-medA`-style weak targeted evidence is visible as targeted-side review
  risk, not silently treated as clean benchmark truth.
- Strong DNA ISTDs stay benchmark eligible.
- RNA-tag ISTD handling remains explicit in benchmark configuration and is not
  hard-coded in production logic.
- Untargeted matrix TSV/XLSX output is unchanged by Phase A and Phase B.
- Any extraction/scoring code change in Phase C has a narrow failing test first.

## Commit Plan

Use small commits by purpose:

1. `docs: define targeted benchmark reliability pass`
2. `feat: add targeted peak reliability audit`
3. `feat: annotate ISTD benchmark with targeted reliability`
4. `fix: preserve targeted scoring evidence for weak peak review`

Stop after each behavior commit and run the relevant test group before
continuing.
