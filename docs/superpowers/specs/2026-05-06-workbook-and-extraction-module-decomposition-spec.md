# Workbook, Extraction, And Signal Processing Module Decomposition Spec

**Date:** 2026-05-06
**Status:** Draft
**Implementation plan:** Not written yet. This document defines future refactor scope and architecture boundaries only.

---

## 1. Summary

PR #29 adds important functionality, but it also confirms two modules have grown beyond comfortable maintenance boundaries:

| Module | Approximate size after PR #29 | Risk |
|---|---:|---|
| `scripts/csv_to_excel.py` | ~1400 lines | Workbook generation mixes parsing, metrics, sheet construction, styling, review logic, and report dispatch. |
| `xic_extractor/extractor.py` | ~1050 lines | Core extraction mixes orchestration, process backend, ISTD pre-pass, target extraction, anchoring, scoring context, MS2 evidence, diagnostics, and output dispatch. |
| `xic_extractor/signal_processing.py` | ~925 lines | Peak detection mixes resolver implementations, candidate models, selection, preferred-RT recovery, trace quality, and area integration. |

Both modules still work and are covered by tests, so this is not a merge blocker. The next maintainability stage should split them into focused modules without changing user-facing behavior.

The refactor goal is not line-count purity. The goal is to make future peak scoring, MS2 evidence, Excel UX, and discovery work safer by giving each responsibility a clear owner.

## 2. Goals

1. Preserve all current CLI, GUI, workbook, CSV, HTML, and config behavior.
2. Split workbook generation into small output modules with stable sheet-level contracts.
3. Split extraction orchestration into pipeline/backends/pre-pass/target-extraction responsibilities.
4. Split signal processing into resolver, selection, trace-quality, and integration modules.
5. Keep public entry points stable:
   - `scripts/csv_to_excel.py` remains executable.
   - `scripts.csv_to_excel.run(...)` remains import-compatible.
   - `xic_extractor.extractor.run(...)` remains import-compatible.
   - `xic_extractor.signal_processing.find_peak_and_area(...)` remains import-compatible.
6. Move code first, then simplify interfaces only where tests prove behavior is unchanged.
7. Avoid touching scoring thresholds, resolver behavior, area integration, or selection rules.

## 3. Non-Goals

- No peak selection changes.
- No scoring weight changes.
- No neutral-loss matching changes.
- No area integration changes.
- No workbook schema changes.
- No sheet rename.
- No GUI layout changes.
- No process-pool behavior changes.
- No new runtime dependency.
- No removal of legacy compatibility paths unless already tested and documented separately.

## 4. Current Problem Statement

### 4.1 `scripts/csv_to_excel.py`

Current responsibilities include:

- reading long result CSV,
- reading legacy wide result CSV,
- reading diagnostics CSV,
- reading score breakdown CSV,
- converting legacy wide output into long rows,
- building Overview sheet,
- building Review Queue sheet,
- building XIC Results sheet,
- building Summary sheet,
- building Targets sheet,
- building Diagnostics sheet,
- building Score Breakdown sheet,
- workbook styling,
- workbook tab coloring,
- review queue issue classification,
- target-level metric aggregation,
- diagnostic evidence shortening,
- optional HTML review report dispatch,
- CLI wrapper.

This makes small workbook copy or layout changes risky because sheet rendering, metrics, style, and file IO are interleaved.

### 4.2 `xic_extractor/extractor.py`

Current responsibilities include:

- public extraction entry point,
- serial execution,
- process-mode execution,
- process job payload handling,
- progress/cancellation handling,
- ISTD pre-pass,
- per-file extraction,
- per-target extraction,
- RT window selection,
- NL anchor selection,
- ISTD anchor fallback,
- sample drift estimation,
- candidate-level MS2 evidence caching,
- scoring context wiring,
- paired anchor mismatch diagnostics,
- output CSV dispatch,
- injection-order resolution,
- RT prior library resolution.

This makes future scoring/discovery changes risky because orchestration and domain decisions are tightly coupled.

### 4.3 `xic_extractor/signal_processing.py`

Current responsibilities include:

- public peak finding entry point,
- peak result and candidate data models,
- legacy Savitzky-Golay candidate formation,
- local-minimum candidate formation,
- local-minimum region splitting,
- preferred-RT selection,
- strict preferred-RT behavior,
- preferred-RT recovery,
- candidate construction,
- raw apex selection,
- area integration,
- local-minimum thresholding,
- ADAP-like trace quality flags,
- trace continuity metrics,
- peak bounds and valley helpers.

This makes resolver evolution risky because algorithm-specific behavior,
selection policy, and quality metrics are tightly coupled. Future MS2 trace
evidence and untargeted discovery work will need cleaner peak-candidate
contracts.

## 5. Desired Workbook Module Boundaries

The workbook refactor should keep `scripts/csv_to_excel.py` as a thin CLI/import compatibility wrapper and move implementation into `xic_extractor/output/`.

Recommended target structure:

```text
xic_extractor/output/
  workbook_builder.py
  workbook_inputs.py
  workbook_styles.py
  sheet_overview.py
  sheet_results.py
  sheet_summary.py
  sheet_review_queue.py
  sheet_targets.py
  sheet_diagnostics.py
  sheet_score_breakdown.py
  review_metrics.py
  review_report.py
```

### 5.1 `workbook_inputs.py`

Owns file input and row normalization:

- read long result rows,
- read diagnostics rows,
- read score breakdown rows,
- read legacy wide rows when needed,
- convert wide rows to long rows,
- preserve current detected/ND token semantics.

It must not import `openpyxl`.

### 5.2 `workbook_styles.py`

Owns visual constants and cell styling helpers:

- fills,
- fonts,
- borders,
- tab colors,
- number formats,
- column widths,
- shared `_excel_text` behavior.

It may import `openpyxl`, but it must not calculate review metrics.

### 5.3 Sheet modules

Each sheet module owns exactly one worksheet:

| Module | Responsibility |
|---|---|
| `sheet_overview.py` | Overview landing sheet and "How to read" copy. |
| `sheet_results.py` | XIC Results long-form sheet. |
| `sheet_summary.py` | target-level Summary rows. |
| `sheet_review_queue.py` | Review Queue row creation and rendering. |
| `sheet_targets.py` | Targets sheet. |
| `sheet_diagnostics.py` | hidden Diagnostics technical log. |
| `sheet_score_breakdown.py` | optional Score Breakdown technical audit. |

Sheet modules may use `review_metrics.py` and `workbook_styles.py`, but should not read files from disk.

### 5.4 `workbook_builder.py`

Owns workbook assembly:

- create workbook,
- create sheets in canonical order,
- call sheet builders,
- hide Diagnostics,
- optionally add Score Breakdown,
- save workbook,
- optionally dispatch HTML review report.

It should be the only workbook module that knows the full sheet order.

### 5.5 `scripts/csv_to_excel.py`

After refactor, this script should contain only:

- CLI parsing,
- compatibility overloads for `run(...)`,
- delegation to `xic_extractor.output.workbook_builder`.

It should stay below roughly 150-250 lines.

## 6. Desired Extraction Module Boundaries

The extraction refactor should keep `xic_extractor/extractor.py` as the public compatibility layer and move implementation into `xic_extractor/extraction/`.

Recommended target structure:

```text
xic_extractor/extraction/
  pipeline.py
  serial_backend.py
  process_backend.py
  jobs.py
  istd_prepass.py
  target_extraction.py
  rt_windows.py
  anchors.py
  drift.py
  diagnostics.py
  output_dispatch.py
  scoring_factory.py
```

`scoring_factory.py` already exists and should remain the scoring context owner.

### 6.1 `pipeline.py`

Owns high-level extraction flow:

- resolve input raw paths,
- choose serial or process backend,
- aggregate `RunOutput`,
- coordinate output dispatch.

It should not contain target-level peak logic.

### 6.2 `serial_backend.py`

Owns serial execution:

- iterate raw files,
- apply progress callback,
- poll cancellation,
- call per-file extraction.

It should not write output files.

### 6.3 `process_backend.py` and `jobs.py`

Own process-mode execution:

- define pickleable job payloads,
- rebuild scoring context inside workers,
- run ISTD pre-pass and Stage 2 extraction,
- preserve cancellation/progress behavior,
- avoid passing closures across Windows process boundaries.

This split is important because process-mode bugs are platform-sensitive.

### 6.4 `istd_prepass.py`

Owns ISTD-only extraction:

- extract ISTD anchors,
- decide whether a candidate can seed pre-pass,
- return per-sample ISTD RTs and diagnostics needed by Stage 2.

It should not know workbook or CSV output.

### 6.5 `target_extraction.py`

Owns extraction of one target in one raw file:

- build XIC trace,
- determine target RT window,
- call peak detection,
- wire scoring context,
- collect candidate MS2 evidence,
- assemble `ExtractionResult`.

This is the highest-value split from `extractor.py`.

### 6.6 `rt_windows.py` and `anchors.py`

Own RT and anchor decisions:

- NL anchor search window,
- fallback RT window,
- anchor-centered window,
- ISTD-paired anchor mismatch logic,
- anchor mismatch confidence downgrade.

These modules should be testable without running full extraction.

### 6.7 `drift.py`

Own sample-level RT drift estimation:

- estimate drift from successful ISTD anchors,
- expose deterministic helper functions for tests.

### 6.8 `output_dispatch.py`

Own writing extraction outputs:

- call `csv_writers.write_all`,
- call Excel pipeline when needed,
- keep output concerns out of extraction logic.

## 7. Public Compatibility Contract

The refactor must keep these imports working:

```python
from scripts.csv_to_excel import run as csv_to_excel_run
from xic_extractor.extractor import run as extractor_run
from xic_extractor.signal_processing import find_peak_and_area
```

The refactor must keep these command-line workflows working:

```powershell
uv run python scripts\csv_to_excel.py <base_or_config>
uv run python scripts\run_extraction.py --base-dir <base>
```

The refactor must not change:

- output workbook sheet names,
- output workbook default sheet order,
- hidden state of `Diagnostics`,
- optional `Score Breakdown`,
- optional review report path naming,
- long CSV schema,
- diagnostics CSV schema,
- run metadata keys,
- result confidence/reason text unless separately planned.

## 8. Desired Signal Processing Module Boundaries

The signal-processing refactor should keep `xic_extractor/signal_processing.py`
as a compatibility facade while moving implementation into a focused package.

Recommended target structure:

```text
xic_extractor/peak_detection/
  models.py
  facade.py
  legacy_savgol.py
  local_minimum.py
  selection.py
  recovery.py
  integration.py
  trace_quality.py
  thresholds.py
```

### 8.1 `models.py`

Owns data structures only:

- `PeakResult`,
- `PeakCandidate`,
- `LocalMinimumRegionQuality`,
- `PeakCandidatesResult`,
- `PeakDetectionResult`.

It should not import SciPy or scoring modules.

### 8.2 `facade.py`

Owns the public algorithm flow currently represented by `find_peak_and_area`:

- call candidate formation,
- run preferred-RT recovery,
- call scored or unscored selection,
- return `PeakDetectionResult`.

It should coordinate modules, not implement resolver internals.

### 8.3 `legacy_savgol.py`

Owns legacy Savitzky-Golay candidate formation:

- smoothing,
- derivative/zero-crossing behavior,
- legacy candidate boundaries.

This module exists to preserve the trusted default behavior while isolating it
from local-minimum changes.

### 8.4 `local_minimum.py`

Owns local-minimum candidate formation:

- `find_peaks` candidate discovery,
- local-minimum regions,
- valley splitting,
- local-minimum thresholding,
- local-minimum region quality object construction.

It should not decide final selected candidate when multiple candidates exist.

### 8.5 `selection.py`

Owns candidate choice among already-built candidates:

- preferred RT selection,
- strict preferred RT behavior,
- intensity fallback,
- scoring-based candidate handoff.

It should not build candidates or integrate area.

### 8.6 `recovery.py`

Owns relaxed local-minimum recovery:

- relaxed config construction,
- preferred-RT recovery candidate selection,
- recovery guardrails.

It should be testable independently from resolver internals.

### 8.7 `integration.py`

Owns area and apex helpers:

- raw apex index,
- area integration in counts-seconds,
- peak bounds.

It should not know scoring or neutral loss.

### 8.8 `trace_quality.py`

Owns MS1/ADAP-like quality signals:

- scan support,
- trace continuity,
- edge recovery,
- duration flags,
- quality flag naming.

It should expose metrics usable by candidate formation without owning selection.

### 8.9 `thresholds.py`

Owns small threshold helpers:

- prominence threshold,
- local-minimum threshold,
- peak height filter helpers.

If these helpers remain trivial, they may live inside resolver modules. Create
this file only when it reduces duplication or clarifies ownership.

## 9. Testing Contract

### 9.1 Workbook refactor tests

Existing tests must remain green:

```powershell
uv run pytest tests\test_csv_to_excel.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_review_metrics.py tests\test_review_report.py -v
```

Additional approval checks:

- same fixture input produces byte-insensitive equivalent workbook values,
- `Diagnostics` remains hidden,
- `Summary` starts with `Target`, `Role`, `ISTD Pair`, `Detected`, `Total`, `Detection %`,
- HTML review report still emits detection chart, flag chart, heatmap, and ISTD RT trend when enabled.

### 9.2 Extraction refactor tests

Existing tests must remain green:

```powershell
uv run pytest tests\test_extractor.py tests\test_extractor_run.py tests\test_neutral_loss.py tests\test_signal_processing.py tests\test_signal_processing_selection.py tests\test_scoring_context.py tests\test_scoring_factory.py tests\test_parallel_execution.py -v
```

Additional approval checks:

- serial and process mode produce equivalent `RunOutput` for fake/raw-free fixtures,
- process job payloads remain pickleable,
- cancellation and progress tests still pass,
- candidate-level MS2 evidence remains selected-candidate scoped,
- ISTD pre-pass still rejects hard-bad anchors while allowing soft ADAP-like flags.

### 9.3 Signal-processing refactor tests

Existing tests must remain green:

```powershell
uv run pytest tests\test_signal_processing.py tests\test_signal_processing_selection.py tests\test_peak_scoring.py -v
```

Additional approval checks:

- `legacy_savgol` fixture behavior is unchanged,
- `local_minimum` fixture behavior is unchanged,
- preferred-RT strict and relaxed selection behavior is unchanged,
- area values are unchanged for existing synthetic fixtures,
- ADAP-like quality flags are unchanged for existing fixture cases,
- `find_peak_and_area(...)` remains import-compatible.

### 9.4 Real-data validation

After both refactors:

1. run the 8-raw tissue validation subset with `parallel_workers=4`,
2. compare workbook shape and key values against the pre-refactor output,
3. verify generated HTML still includes ISTD RT trend,
4. do not run the full 85-raw batch unless the subset changes unexpectedly or user requests it.

## 10. Refactor Ordering

Recommended order:

1. Split workbook modules first.
2. Verify Excel/HTML outputs are behavior-equivalent.
3. Split extraction process/serial backend.
4. Split target extraction and anchor helpers.
5. Verify fake tests and 8-raw subset.
6. Split `signal_processing.py` as a separate PR after extraction orchestration is stable.
7. Re-run focused signal-processing tests and the 8-raw subset.

Rationale:

- workbook split is large but lower domain risk,
- extraction split touches high-risk runtime flow and should happen after output code is stable,
- `signal_processing.py` should not be split in the same PR as extraction orchestration unless the change is purely mechanical.
- resolver behavior and selection policy are high-risk contracts, so signal-processing decomposition deserves its own review.

## 11. Suggested Size Targets

These are guardrails, not hard rules:

| File | Target size |
|---|---:|
| `scripts/csv_to_excel.py` | <= 250 lines |
| `xic_extractor/extractor.py` | <= 250 lines |
| workbook sheet modules | <= 250 lines each |
| extraction backend modules | <= 300 lines each |
| `target_extraction.py` | <= 350 lines |
| `anchors.py` | <= 300 lines |
| `signal_processing.py` compatibility facade | <= 200 lines |
| peak detection resolver modules | <= 300 lines each |
| peak detection selection/recovery modules | <= 250 lines each |

If a file exceeds the target but owns one coherent responsibility, prefer clarity over artificial splitting.

## 12. Acceptance Criteria

This refactor is complete when:

- `scripts/csv_to_excel.py` is a thin wrapper and no longer owns sheet internals,
- `xic_extractor/extractor.py` is a thin public entry point and no longer owns backend/pre-pass/target extraction internals,
- `xic_extractor/signal_processing.py` is a thin compatibility facade and no longer owns every resolver, selection, trace-quality, and integration detail,
- all public imports and CLI commands remain compatible,
- existing tests and CI pass,
- 8-raw tissue validation output is behavior-equivalent,
- no scoring, peak selection, area, or schema change is introduced unintentionally,
- future MS2 trace evidence and discovery work can be added without editing a 1000+ line orchestration file.
