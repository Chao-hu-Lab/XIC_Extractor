# Handoff Productization Consumer Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

> **Execution status:** Implemented. Treat this file as the reviewed execution
> recipe, not the current status source. Current outcome, verification, and
> post-implementation review results are recorded in
> `docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-closeout.md`.

**Goal:** Move targeted CSV numeric peak projection to an
`ExtractionResult` selected-integration view while preserving current schemas
and values.

**Architecture:** `target_extraction.py` already builds a selected production
`PeakHypothesis` and passes it to `build_extraction_result(...)`. This plan
stores that hypothesis on `ExtractionResult`, adds read-only projection
accessors with legacy fallback, then makes `csv_writers.py` consume those
accessors instead of reaching into `PeakDetectionResult.peak`.

**Tech Stack:** Python dataclasses, pytest, csv `DictWriter`, existing handoff
spine models in `xic_extractor.peak_detection.hypotheses`.

**Spec:** `docs/superpowers/specs/2026-05-28-handoff-productization-consumer-migration-spec.md`

---

## File Map

- Modify `xic_extractor/extractor.py`
  - Add `selected_hypothesis` compatibility storage.
  - Add projection accessors: `reported_peak_area`,
    `reported_peak_intensity`, `reported_peak_start`, `reported_peak_end`,
    `reported_peak_width`.
  - Update `reported_rt` to prefer selected `IntegrationResult.rt_apex_min`.
  - Keep `peak`, `nl_result`, `nl_token`, and existing constructor defaults
    compatible.

- Modify `xic_extractor/extraction/result_assembly.py`
  - Pass the optional `selected_hypothesis` through to `ExtractionResult`.
  - Keep confidence/reason/quality fallback behavior unchanged.

- Modify `xic_extractor/output/csv_writers.py`
  - Extend `ExtractionResultLike` with projection accessors.
  - Use those accessors for wide and long RT / Area / Int / PeakStart /
    PeakEnd / PeakWidth projection.
  - Keep NL token, confidence, reason, score breakdown, diagnostics, and
    detection-counting behavior unchanged.

- Modify `tests/test_result_assembly.py`
  - Add selected-integration projection and legacy fallback tests.
  - Keep stale-score and `HIGH` fallback tests intact.

- Modify `tests/test_csv_writers.py`
  - Add a divergent selected-integration fixture that proves wide and long CSV
    rows consume selected integration values, not legacy `PeakResult` values.
  - Add runtime-selected-hypothesis parity so current selected runtime output
    stays value-equivalent to legacy fallback output.
  - Add a no-peak regression for wide and long CSV rows.
  - Add schema / row-count assertions for the divergent fixture.

- Create `docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-closeout.md`
  - Record verdict, contracts preserved, verification, review outcome, and next
    action.

## Now

### Task 1: Pin `ExtractionResult` Projection Semantics

**Files:**
- Modify: `tests/test_result_assembly.py`

- [ ] **Step 1: Add focused selected integration accessor test**

Add imports if missing:

```python
import pytest

from xic_extractor.peak_detection.hypotheses import (
    AuditTrail,
    EvidenceVector,
    IntegrationResult,
    PeakHypothesis,
)
```

Add helpers near existing test helpers:

```python
def _peak_result_with_candidate() -> PeakDetectionResult:
    candidate = _candidate()
    return PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="LOW",
        reason="concerns: local_sn",
        severities=((1, "local_sn"),),
        score_breakdown=(("Raw Score", "41"),),
        candidate_scores=(_score(candidate),),
    )
```

```python
def _selected_hypothesis_with_integration(
    integration: IntegrationResult,
) -> PeakHypothesis:
    return PeakHypothesis(
        hypothesis_id="SampleA|Analyte|selected",
        trace_group_id="SampleA|Analyte|targeted",
        target_label="Analyte",
        role="Analyte",
        istd_pair="ISTD",
        analysis_mode="targeted",
        resolver_mode="local_minimum",
        integration=integration,
        evidence=EvidenceVector(confidence="LOW", reason="selected spine"),
        audit=AuditTrail(selected=True, selection_rank=1),
    )
```

Add a test that deliberately differs from legacy `PeakResult` values:

```python
def test_extraction_result_reports_selected_integration_values() -> None:
    peak_result = _peak_result_with_candidate()
    selected = _selected_hypothesis_with_integration(
        IntegrationResult(
            rt_left_min=8.7,
            rt_apex_min=8.95,
            rt_right_min=9.3,
            raw_apex_rt_min=8.96,
            rt_width_min=-0.42,
            height_raw=765.0,
            height_smoothed=700.0,
            area_raw_counts_seconds=4567.89,
        )
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=_target(),
        candidate=peak_result.candidates[0],
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert result.reported_rt == 8.95
    assert result.reported_peak_area == 4567.89
    assert result.reported_peak_intensity == 765.0
    assert result.reported_peak_start == 8.7
    assert result.reported_peak_end == 9.3
    assert result.reported_peak_width == pytest.approx(0.42)
```

- [ ] **Step 2: Add legacy fallback accessor test**

```python
def test_extraction_result_projection_accessors_fall_back_to_legacy_peak() -> None:
    peak_result = _peak_result_with_candidate()
    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=_target(),
        candidate=peak_result.candidates[0],
        scoring_context_builder=None,
        selected_hypothesis=None,
    )

    peak = peak_result.peak
    assert peak is not None
    assert result.reported_rt == peak_result.candidates[0].selection_apex_rt
    assert result.reported_peak_area == peak.area
    assert result.reported_peak_intensity == peak.intensity
    assert result.reported_peak_start == peak.peak_start
    assert result.reported_peak_end == peak.peak_end
    assert result.reported_peak_width == abs(peak.peak_end - peak.peak_start)
```

- [ ] **Step 3: Run the new tests and confirm expected failure**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_result_assembly.py -q
```

Expected before implementation: fail because `ExtractionResult` has no selected
integration projection accessors.

### Task 2: Implement `ExtractionResult` Selected Integration View

**Files:**
- Modify: `xic_extractor/extractor.py`
- Modify: `xic_extractor/extraction/result_assembly.py`

- [ ] **Step 1: Add selected hypothesis storage and accessors**

In `xic_extractor/extractor.py`, add future annotations as the first statement
in the file, before all imports, and add a type-checking import:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xic_extractor.peak_detection.hypotheses import PeakHypothesis
```

Add this dataclass field to `ExtractionResult`:

```python
selected_hypothesis: PeakHypothesis | None = None
```

Add a private helper and public projection accessors:

```python
    @property
    def _selected_integration(self):
        if self.selected_hypothesis is None:
            return None
        return self.selected_hypothesis.integration

    @property
    def reported_peak_area(self) -> float | None:
        integration = self._selected_integration
        if integration is not None:
            return integration.area_raw_counts_seconds
        peak = self.peak
        return None if peak is None else peak.area

    @property
    def reported_peak_intensity(self) -> float | None:
        integration = self._selected_integration
        if integration is not None:
            return integration.height_raw
        peak = self.peak
        return None if peak is None else peak.intensity

    @property
    def reported_peak_start(self) -> float | None:
        integration = self._selected_integration
        if integration is not None:
            return integration.rt_left_min
        peak = self.peak
        return None if peak is None else peak.peak_start

    @property
    def reported_peak_end(self) -> float | None:
        integration = self._selected_integration
        if integration is not None:
            return integration.rt_right_min
        peak = self.peak
        return None if peak is None else peak.peak_end

    @property
    def reported_peak_width(self) -> float | None:
        start = self.reported_peak_start
        end = self.reported_peak_end
        if start is None or end is None:
            return None
        return abs(end - start)
```

Update `reported_rt`:

```python
    @property
    def reported_rt(self) -> float | None:
        """User-facing RT uses selected integration apex when available."""
        integration = self._selected_integration
        if integration is not None:
            return integration.rt_apex_min
        candidate = selected_candidate(self.peak_result)
        if candidate is not None:
            return candidate.selection_apex_rt
        peak = self.peak
        if peak is None:
            return None
        return peak.rt
```

- [ ] **Step 2: Pass selected hypothesis through result assembly**

In `build_extraction_result(...)`, add `selected_hypothesis=selected_hypothesis`
to the `extractor.ExtractionResult(...)` constructor.

- [ ] **Step 3: Run result assembly tests**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_result_assembly.py -q
```

Expected: all tests in this file pass.

### Task 3: Pin CSV Consumer Migration With Divergent Fixture

**Files:**
- Modify: `tests/test_csv_writers.py`

- [ ] **Step 1: Import handoff hypothesis models**

Add imports:

```python
from xic_extractor.peak_detection.hypotheses import (
    AuditTrail,
    EvidenceVector,
    IntegrationResult,
    PeakHypothesis,
)
```

- [ ] **Step 2: Add helper for divergent selected integration**

```python
def _selected_hypothesis_with_integration(
    integration: IntegrationResult,
) -> PeakHypothesis:
    return PeakHypothesis(
        hypothesis_id="SampleA|WithNL|selected",
        trace_group_id="SampleA|WithNL|targeted",
        target_label="WithNL",
        role="Analyte",
        istd_pair="ISTD",
        analysis_mode="targeted",
        resolver_mode="local_minimum",
        integration=integration,
        evidence=EvidenceVector(confidence="LOW", reason="selected spine"),
        audit=AuditTrail(selected=True, selection_rank=1),
    )
```

- [ ] **Step 3: Add runtime selected-hypothesis parity test**

Import runtime helpers:

```python
from xic_extractor.extraction.handoff_spine_runtime import (
    build_production_peak_hypotheses,
    selected_peak_hypothesis,
)
from xic_extractor.extraction.result_assembly import build_extraction_result
```

Add a tiny config helper:

```python
class _Config:
    resolver_mode = "local_minimum"
```

Add the parity test:

```python
def test_csv_rows_preserve_values_with_runtime_selected_hypothesis() -> None:
    target = _target("WithNL")
    legacy = _result(nl=NLResult("WARN", 12.34, None, 3, 0, 2))
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=legacy.peak_result,
        )
    )
    assert selected is not None
    with_selected = build_extraction_result(
        peak_result=legacy.peak_result,
        nl_result=legacy.nl,
        candidate_ms2_evidence=legacy.candidate_ms2_evidence,
        target=target,
        candidate=legacy.peak_result.candidates[0],
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    fallback_file = FileResult(sample_name="SampleA", results={"WithNL": legacy})
    selected_file = FileResult(
        sample_name="SampleA",
        results={"WithNL": with_selected},
    )

    assert _output_row(selected_file, [target]) == _output_row(
        fallback_file,
        [target],
    )
    assert _long_output_rows(selected_file, [target]) == _long_output_rows(
        fallback_file,
        [target],
    )
```

- [ ] **Step 4: Add CSV-level divergent selected integration test**

```python
def test_csv_rows_project_selected_integration_values_when_present() -> None:
    target = _target("WithNL")
    result = replace(
        _result(nl=NLResult("WARN", 12.34, None, 3, 0, 2)),
        selected_hypothesis=_selected_hypothesis_with_integration(
            IntegrationResult(
                rt_left_min=8.7,
                rt_apex_min=8.95,
                rt_right_min=9.3,
                raw_apex_rt_min=8.96,
                rt_width_min=-0.42,
                height_raw=765.0,
                height_smoothed=700.0,
                area_raw_counts_seconds=4567.89,
            )
        ),
    )
    file_result = FileResult(sample_name="SampleA", results={"WithNL": result})

    wide_row = _output_row(file_result, [target])
    long_rows = _long_output_rows(file_result, [target])

    assert len(long_rows) == 1
    long_row = long_rows[0]
    assert list(wide_row) == [
        "SampleName",
        "WithNL_RT",
        "WithNL_Int",
        "WithNL_Area",
        "WithNL_PeakStart",
        "WithNL_PeakEnd",
        "WithNL_PeakWidth",
        "WithNL_NL",
    ]
    assert wide_row["WithNL_RT"] == "8.9500"
    assert wide_row["WithNL_Area"] == "4567.89"
    assert wide_row["WithNL_Int"] == "765"
    assert wide_row["WithNL_PeakStart"] == "8.7000"
    assert wide_row["WithNL_PeakEnd"] == "9.3000"
    assert wide_row["WithNL_PeakWidth"] == "0.4200"
    assert wide_row["WithNL_NL"] == "WARN_12.3ppm"
    assert long_row["RT"] == "8.9500"
    assert long_row["Area"] == "4567.89"
    assert long_row["Int"] == "765"
    assert long_row["PeakStart"] == "8.7000"
    assert long_row["PeakEnd"] == "9.3000"
    assert long_row["PeakWidth"] == "0.4200"
    assert long_row["NL"] == "WARN_12.3ppm"
    assert long_row["Confidence"] == "LOW"
    assert long_row["Reason"] == "concerns: local_sn (minor)"
```

- [ ] **Step 5: Add no-peak writer regression**

```python
def test_csv_rows_preserve_no_peak_nd_projection() -> None:
    target = _target("WithNL")
    result = ExtractionResult(
        peak_result=PeakDetectionResult(
            status="NO_PEAK",
            peak=None,
            n_points=4,
            max_smoothed=0.0,
            n_prominent_peaks=0,
        ),
        nl=NLResult("NO_MS2", None, None, 0, 0, 0),
        target_label="WithNL",
        role="Analyte",
        istd_pair="",
        confidence="",
        reason="",
    )
    file_result = FileResult(sample_name="SampleA", results={"WithNL": result})

    wide_row = _output_row(file_result, [target])
    long_row = _long_output_rows(file_result, [target])[0]

    for suffix in ("RT", "Int", "Area", "PeakStart", "PeakEnd", "PeakWidth"):
        assert wide_row[f"WithNL_{suffix}"] == "ND"
    assert wide_row["WithNL_NL"] == "NO_MS2"
    assert long_row["RT"] == "ND"
    assert long_row["Area"] == "ND"
    assert long_row["Int"] == "ND"
    assert long_row["PeakStart"] == "ND"
    assert long_row["PeakEnd"] == "ND"
    assert long_row["PeakWidth"] == "ND"
    assert long_row["NL"] == "NO_MS2"
```

- [ ] **Step 6: Run CSV writer tests and confirm expected failure**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_csv_writers.py -q
```

Expected before writer migration: runtime parity and no-peak tests pass, while
the divergent selected-integration test fails because CSV rows still read legacy
`result.peak_result.peak`.

### Task 4: Migrate CSV Writers To Projection Accessors

**Files:**
- Modify: `xic_extractor/output/csv_writers.py`

- [ ] **Step 1: Extend `ExtractionResultLike` protocol**

Add protocol properties:

```python
    @property
    def reported_peak_area(self) -> float | None: ...

    @property
    def reported_peak_intensity(self) -> float | None: ...

    @property
    def reported_peak_start(self) -> float | None: ...

    @property
    def reported_peak_end(self) -> float | None: ...

    @property
    def reported_peak_width(self) -> float | None: ...
```

- [ ] **Step 2: Replace long-row numeric projection**

In `_set_long_peak_values(...)`, stop reading `result.peak_result.peak`. Use:

```python
def _set_long_peak_values(row: dict[str, str], result: ExtractionResultLike) -> None:
    area = result.reported_peak_area
    intensity = result.reported_peak_intensity
    start = result.reported_peak_start
    end = result.reported_peak_end
    width = result.reported_peak_width
    if (
        area is None
        or intensity is None
        or start is None
        or end is None
        or width is None
    ):
        _set_long_ms1_values(row, "ND")
        return
    reported_rt = result.reported_rt
    row["RT"] = f"{reported_rt:.4f}" if reported_rt is not None else "ND"
    row["Area"] = f"{area:.2f}"
    row["Int"] = f"{intensity:.0f}"
    row["PeakStart"] = f"{start:.4f}"
    row["PeakEnd"] = f"{end:.4f}"
    row["PeakWidth"] = f"{width:.4f}"
```

- [ ] **Step 3: Replace wide-row numeric projection**

In `_set_peak_values(...)`, stop reading `result.peak_result.peak`. Use the
same accessors and formatting:

```python
def _set_peak_values(
    row: dict[str, str],
    target: Target,
    result: ExtractionResultLike,
) -> None:
    area = result.reported_peak_area
    intensity = result.reported_peak_intensity
    start = result.reported_peak_start
    end = result.reported_peak_end
    width = result.reported_peak_width
    if (
        area is None
        or intensity is None
        or start is None
        or end is None
        or width is None
    ):
        for suffix in MS1_SUFFIXES:
            row[f"{target.label}_{suffix}"] = "ND"
        return

    reported_rt = result.reported_rt
    row[f"{target.label}_RT"] = (
        f"{reported_rt:.4f}" if reported_rt is not None else "ND"
    )
    row[f"{target.label}_Int"] = f"{intensity:.0f}"
    row[f"{target.label}_Area"] = f"{area:.2f}"
    row[f"{target.label}_PeakStart"] = f"{start:.4f}"
    row[f"{target.label}_PeakEnd"] = f"{end:.4f}"
    row[f"{target.label}_PeakWidth"] = f"{width:.4f}"
```

Keep `_format_peak_width(...)` only if still used elsewhere; otherwise remove it
with its `PeakResult` import if that import becomes unused.

- [ ] **Step 4: Run CSV writer tests**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_csv_writers.py -q
```

Expected: all CSV writer tests pass.

- [ ] **Step 5: Run architecture drift grep**

```powershell
rg -n "peak_result\.peak|result\.peak_result\.peak" xic_extractor\output\csv_writers.py
```

Expected: no matches.

### Task 5: Focused Verification And Closeout

**Files:**
- Create:
  `docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-closeout.md`

- [ ] **Step 1: Run focused verification**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run static checks**

```powershell
python -m py_compile xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py
$env:UV_CACHE_DIR='.uv-cache'
uv run ruff check xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py
git diff --check
```

Expected: compile passes, ruff reports `All checks passed!`, and diff check is
clean.

- [ ] **Step 3: Run architecture drift checks**

```powershell
rg -n "add_cwt_proposals_for_audit|peak_candidate_table|peak_candidate_boundaries|peak_candidate_audit" xic_extractor\extractor.py xic_extractor\output\csv_writers.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\handoff_spine_runtime.py
rg -n "peak_result\.peak|result\.peak_result\.peak" xic_extractor\output\csv_writers.py
```

Expected: no production output/result dependency on audit writer helpers and no
`csv_writers.py` direct legacy peak projection hits.

- [ ] **Step 4: Write closeout note**

Create the closeout note with this structure:

```markdown
# Handoff Productization Consumer Migration Closeout

## Verdict

Status: `handoff_spine_consumer_migration_ready` / `production_candidate`.

This PR migrates targeted CSV numeric peak projection to consume the
`ExtractionResult` selected-integration view while preserving current emitted
CSV values and schemas.

This is not `production_ready`. It does not change `alignment_matrix.tsv`,
resolver selection, baseline defaults, CWT production behavior, ASLS promotion,
or real-data acceptance status.

## Public Contracts

- `xic_results.csv`: schema and formatting preserved.
- `xic_results_long.csv`: schema and formatting preserved.
- `xic_score_breakdown.csv`: schema and formatting preserved.
- `alignment_matrix.tsv`: unchanged and still the downstream
  correction/statistics contract.

## Verification

<paste exact commands and observed results>

## Post-Implementation Review

- `implementation-contract-reviewer` checked the public CSV contract.
- Any blocker findings were fixed before PR.

## Next Decision

Future matrix handoff requires a separate parity/behavior spec. This PR only
proves the next targeted output consumer can consume selected spine-derived
integration values.
```

- [ ] **Step 5: Review before PR**

Run implementation review with at least the `implementation-contract-reviewer`
angle. Review questions:

- Does `csv_writers.py` really consume projection accessors rather than legacy
  peak fields?
- Did any CSV schema or formatting drift?
- Did any audit-only CWT helper enter production output/result code?
- Is any real-data validation being overclaimed?

Fix any blocker before PR.

## Later

- Decide whether `alignment_matrix.tsv` should consume a spine-derived contract.
  That needs a separate spec because alignment owner/backfill/cell-quality
  semantics are not the same as targeted `ExtractionResult`.
- Decide whether selected peak/integration behavior should become natively
  spine-owned rather than legacy-result-owned.

## Not In Scope

- Phase2 cleanup.
- Alignment matrix writer/value/schema changes.
- Resolver, scoring, baseline, ASLS, CWT production, NL matching, diagnostics,
  workbook, CLI, or config changes.
- 8RAW / 85RAW validation unless focused parity tests expose production output
  drift that cannot be explained synthetically.

## Self-Review Before Execution

- [ ] Every spec acceptance criterion maps to a task above.
- [ ] No task touches Phase2 cleanup or alignment matrix code.
- [ ] Divergent CSV-level test fails before writer migration and passes after.
- [ ] Width uses current absolute-width semantics.
- [ ] Baseline-corrected area never replaces emitted raw `Area`.
- [ ] `csv_writers.py` has no lingering direct legacy peak projection hits.
