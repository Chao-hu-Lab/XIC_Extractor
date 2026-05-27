# Handoff Productization MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the handoff productization MVP by keeping the Step2 shared audit spine and adding one production-candidate `ExtractionResult` consumer for the selected production-safe `PeakHypothesis`.

**Architecture:** Add a neutral runtime helper module for production-safe hypothesis construction so production code does not import TSV writer modules. Keep audit hypothesis construction separate because it may include CWT audit proposals. Result assembly consumes an optional selected hypothesis and must preserve current output parity.

**Tech Stack:** Python 3.13, dataclasses, pytest, ruff, existing `TraceGroup`, `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, and `AuditTrail` models.

---

## File Structure

- Create: `xic_extractor/extraction/handoff_spine_runtime.py`
  - Owns production-safe hypothesis construction for extraction runtime.
  - Exposes selected-hypothesis lookup.
  - Must not import `add_cwt_proposals_for_audit` or TSV writer modules.

- Create: `tests/test_handoff_spine_runtime.py`
  - Tests selected-hypothesis lookup, selected-only MS2 evidence mapping, final
    selected-result confidence precedence, and no CWT audit dependency.

- Modify: `xic_extractor/extraction/result_assembly.py`
  - Adds optional `selected_hypothesis` input.
  - Uses selected hypothesis for role, ISTD pair, confidence, reason, and quality flags when present.
  - Preserves current fallbacks and public `ExtractionResult` shape.

- Create: `tests/test_result_assembly.py`
  - Tests parity between legacy assembly and selected-hypothesis assembly.
  - Tests `HIGH` fallback when selected hypothesis has no scoring confidence.

- Modify: `xic_extractor/extraction/target_extraction.py`
  - Builds production-safe hypotheses once after selected MS2 evidence is resolved.
  - Passes selected hypothesis into `build_extraction_result`.
  - Leaves audit rows on the existing audit tuple path with CWT proposal injection.

- Modify: `tests/test_target_extraction.py`
  - Adds a focused test proving `extract_one_target(...)` passes a selected hypothesis to result assembly and does not depend on CWT audit proposals for production assembly.

- Create: `docs/superpowers/notes/2026-05-28-handoff-productization-mvp-closeout.md`
  - Records `handoff_spine_mvp_ready` / `production_candidate`.
  - States unchanged public TSV/matrix contracts and next productization decision.

---

### Task 0: Commit Reviewed Planning Artifacts

**Files:**
- Stage: `docs/superpowers/specs/2026-05-28-handoff-productization-mvp-step2-step4-spec.md`
- Stage: `docs/superpowers/plans/2026-05-28-handoff-productization-mvp-goal.md`
- Stage: `docs/superpowers/plans/2026-05-28-handoff-productization-mvp-implementation-plan.md`

- [ ] **Step 1: Verify the reviewed docs are the only current planning artifacts**

Run:

```powershell
git status --short --branch
git diff --check
```

Expected: only these reviewed planning docs are dirty/untracked.

- [ ] **Step 2: Commit planning artifacts before code work**

Run:

```powershell
git add docs\superpowers\specs\2026-05-28-handoff-productization-mvp-step2-step4-spec.md docs\superpowers\plans\2026-05-28-handoff-productization-mvp-goal.md docs\superpowers\plans\2026-05-28-handoff-productization-mvp-implementation-plan.md
git commit -m "docs: define handoff productization mvp"
```

Expected: the executable spec, goal, and implementation plan are recoverable
from git before implementation starts.

---

### Task 1: Add Production-Safe Handoff Spine Runtime

**Files:**
- Create: `xic_extractor/extraction/handoff_spine_runtime.py`
- Create: `tests/test_handoff_spine_runtime.py`

- [ ] **Step 1: Write failing runtime helper tests**

Create `tests/test_handoff_spine_runtime.py`:

```python
import inspect

import numpy as np

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction import handoff_spine_runtime
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
    PeakResult,
)
from xic_extractor.peak_detection.traces import Trace, targeted_trace_group


def test_build_production_peak_hypotheses_maps_selected_ms2_only(tmp_path) -> None:
    target = _target()
    rt = np.asarray([8.3, 8.5, 8.7, 8.9, 9.1])
    intensity = np.asarray([10.0, 100.0, 20.0, 80.0, 10.0])
    trace_group = targeted_trace_group(
        Trace.from_arrays(
            sample_name="SampleA",
            mz=target.mz,
            rt=rt,
            intensity=intensity,
            rt_min=8.0,
            rt_max=9.2,
            ppm_tol=target.ppm_tol,
            source="unit_test",
        ),
        target_label=target.label,
        resolver_mode="region_first_safe_merge",
        role="Analyte",
        istd_pair=target.istd_pair,
    )
    selected = _candidate(8.50)
    rejected = _candidate(8.90)
    peak_result = PeakDetectionResult(
        status="OK",
        peak=selected.peak,
        n_points=11,
        max_smoothed=1200.0,
        n_prominent_peaks=2,
        candidates=(selected, rejected),
        candidate_scores=(
            _score(selected, confidence="HIGH"),
            _score(rejected, confidence="LOW"),
        ),
    )
    hypotheses = handoff_spine_runtime.build_production_peak_hypotheses(
        config=_config(tmp_path),
        sample_name="SampleA",
        target=target,
        peak_result=peak_result,
        selected_candidate_ms2_evidence=_ms2_evidence(),
        rt=rt,
        intensity=intensity,
        trace_group=trace_group,
    )

    selected_hypothesis = handoff_spine_runtime.selected_peak_hypothesis(hypotheses)
    rejected_hypothesis = next(
        hypothesis for hypothesis in hypotheses if not hypothesis.audit.selected
    )

    assert selected_hypothesis is not None
    assert selected_hypothesis.trace_group_id == trace_group.trace_group_id
    assert selected_hypothesis.integration.raw_scan_indices != ()
    assert selected_hypothesis.evidence.nl_status == "OK"
    assert rejected_hypothesis.evidence.nl_status == ""


def test_selected_peak_hypothesis_returns_none_without_selected_candidate(
    tmp_path,
) -> None:
    hypotheses = handoff_spine_runtime.build_production_peak_hypotheses(
        config=_config(tmp_path),
        sample_name="SampleA",
        target=_target(),
        peak_result=PeakDetectionResult(
            status="PEAK_NOT_FOUND",
            peak=None,
            n_points=5,
            max_smoothed=10.0,
            n_prominent_peaks=0,
            candidates=(),
        ),
    )

    assert hypotheses == ()
    assert handoff_spine_runtime.selected_peak_hypothesis(hypotheses) is None


def test_selected_hypothesis_uses_final_peak_result_confidence_when_score_is_stale(
    tmp_path,
) -> None:
    candidate = _candidate(8.50)
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=11,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="VERY_LOW",
        reason="decision: review only, not counted; cap: VERY_LOW",
        candidate_scores=(_score(candidate, confidence="HIGH"),),
    )

    selected = handoff_spine_runtime.selected_peak_hypothesis(
        handoff_spine_runtime.build_production_peak_hypotheses(
            config=_config(tmp_path),
            sample_name="SampleA",
            target=_target(),
            peak_result=peak_result,
        )
    )

    assert selected is not None
    assert selected.evidence.confidence == "VERY_LOW"
    assert selected.evidence.reason == (
        "decision: review only, not counted; cap: VERY_LOW"
    )


def test_production_handoff_runtime_has_no_cwt_audit_dependency() -> None:
    source = inspect.getsource(handoff_spine_runtime)

    assert "add_cwt_proposals_for_audit" not in source
    assert "peak_candidate_table" not in source
    assert "peak_candidate_boundaries" not in source
    assert "peak_candidate_audit" not in source


def _config(tmp_path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path,
        dll_dir=tmp_path,
        output_csv=tmp_path / "xic_results.csv",
        diagnostics_csv=tmp_path / "diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        resolver_mode="region_first_safe_merge",
    )


def _target() -> Target:
    return Target(
        label="Analyte",
        mz=258.1085,
        rt_min=8.0,
        rt_max=9.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=False,
        istd_pair="ISTD",
    )


def _candidate(rt: float) -> PeakCandidate:
    peak = PeakResult(
        rt=rt,
        intensity=1200.0,
        intensity_smoothed=1100.0,
        area=1234.5,
        peak_start=rt - 0.1,
        peak_end=rt + 0.1,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=1100.0,
        selection_apex_index=1,
        raw_apex_rt=rt,
        raw_apex_intensity=1200.0,
        raw_apex_index=1,
        prominence=700.0,
        quality_flags=("trace_continuity_ok",),
    )


def _score(candidate: PeakCandidate, *, confidence: str) -> PeakCandidateScore:
    return PeakCandidateScore(
        candidate=candidate,
        confidence=confidence,
        reason=f"decision: {confidence.lower()}",
        raw_score=90 if confidence == "HIGH" else 40,
        support_labels=("strict_nl_ok",) if confidence == "HIGH" else (),
        concern_labels=() if confidence == "HIGH" else ("low_score",),
    )


def _ms2_evidence() -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=True,
        nl_match=True,
        nl_status="OK",
        trigger_scan_count=1,
        strict_nl_scan_count=1,
        best_loss_ppm=1.2,
        best_scan_rt=8.5,
        best_product_base_ratio=0.4,
        alignment_source="region",
    )
```

- [ ] **Step 2: Run tests and verify expected failure**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py -q
```

Expected: fail with `ImportError` or missing `handoff_spine_runtime`.

- [ ] **Step 3: Implement the neutral runtime helper**

Create `xic_extractor/extraction/handoff_spine_runtime.py`:

```python
from __future__ import annotations

from dataclasses import replace

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.scoring_factory import selected_candidate
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.hypotheses import (
    PeakHypothesis,
    build_peak_hypotheses,
)
from xic_extractor.peak_detection.models import PeakDetectionResult
from xic_extractor.peak_detection.traces import TraceGroup


def build_production_peak_hypotheses(
    *,
    config: ExtractionConfig,
    sample_name: str,
    target: Target,
    peak_result: PeakDetectionResult,
    selected_candidate_ms2_evidence: CandidateMS2Evidence | None = None,
    rt: object | None = None,
    intensity: object | None = None,
    trace_group: TraceGroup | None = None,
) -> tuple[PeakHypothesis, ...]:
    candidate = selected_candidate(peak_result)
    evidence_by_candidate = (
        {candidate: selected_candidate_ms2_evidence}
        if candidate is not None and selected_candidate_ms2_evidence is not None
        else None
    )
    hypotheses = build_peak_hypotheses(
        sample_name=sample_name,
        target_label=target.label,
        role="ISTD" if target.is_istd else "Analyte",
        istd_pair=target.istd_pair,
        resolver_mode=config.resolver_mode,
        peak_result=peak_result,
        candidate_ms2_evidence=evidence_by_candidate,
        rt=rt,
        intensity=intensity,
        trace_group=trace_group,
    )
    return _with_final_selected_result_evidence(hypotheses, peak_result)


def selected_peak_hypothesis(
    hypotheses: tuple[PeakHypothesis, ...],
) -> PeakHypothesis | None:
    for hypothesis in hypotheses:
        if hypothesis.audit.selected:
            return hypothesis
    return None


def _with_final_selected_result_evidence(
    hypotheses: tuple[PeakHypothesis, ...],
    peak_result: PeakDetectionResult,
) -> tuple[PeakHypothesis, ...]:
    if peak_result.confidence is None and not peak_result.reason:
        return hypotheses
    updated: list[PeakHypothesis] = []
    for hypothesis in hypotheses:
        if not hypothesis.audit.selected:
            updated.append(hypothesis)
            continue
        updated.append(
            replace(
                hypothesis,
                evidence=replace(
                    hypothesis.evidence,
                    confidence=(
                        peak_result.confidence or hypothesis.evidence.confidence
                    ),
                    reason=peak_result.reason or hypothesis.evidence.reason,
                ),
            )
        )
    return tuple(updated)
```

- [ ] **Step 4: Run runtime helper tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add xic_extractor\extraction\handoff_spine_runtime.py tests\test_handoff_spine_runtime.py
git commit -m "feat: add production handoff spine runtime"
```

---

### Task 2: Make ExtractionResult Assembly Consume Selected Hypotheses

**Files:**
- Modify: `xic_extractor/extraction/result_assembly.py`
- Create: `tests/test_result_assembly.py`

- [ ] **Step 1: Write failing result assembly parity tests**

Create `tests/test_result_assembly.py`:

```python
from xic_extractor.config import Target
from xic_extractor.extraction.handoff_spine_runtime import (
    build_production_peak_hypotheses,
    selected_peak_hypothesis,
)
from xic_extractor.extraction.result_assembly import build_extraction_result
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
    PeakResult,
)


def test_build_extraction_result_preserves_parity_with_selected_hypothesis(
) -> None:
    target = _target()
    candidate = _candidate()
    peak_result = PeakDetectionResult(
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
    evidence = _ms2_evidence()
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=peak_result,
            selected_candidate_ms2_evidence=evidence,
        )
    )

    legacy = build_extraction_result(
        peak_result=peak_result,
        nl_result=NLResult("WARN", 12.0, 8.5, 1, 0, 1),
        candidate_ms2_evidence=evidence,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
    )
    with_hypothesis = build_extraction_result(
        peak_result=peak_result,
        nl_result=NLResult("WARN", 12.0, 8.5, 1, 0, 1),
        candidate_ms2_evidence=evidence,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert selected is not None
    assert with_hypothesis.peak_result is legacy.peak_result
    assert with_hypothesis.nl_token == legacy.nl_token
    assert with_hypothesis.target_label == legacy.target_label
    assert with_hypothesis.role == legacy.role
    assert with_hypothesis.istd_pair == legacy.istd_pair
    assert with_hypothesis.confidence == legacy.confidence
    assert with_hypothesis.reason == legacy.reason
    assert with_hypothesis.severities == legacy.severities
    assert with_hypothesis.quality_penalty == legacy.quality_penalty
    assert with_hypothesis.quality_flags == legacy.quality_flags
    assert with_hypothesis.score_breakdown == legacy.score_breakdown


def test_build_extraction_result_keeps_high_fallback_without_scoring_confidence(
) -> None:
    target = _target()
    candidate = _candidate()
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
    )
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=peak_result,
        )
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert selected is not None
    assert selected.evidence.confidence == ""
    assert result.confidence == "HIGH"
    assert result.reason == ""


def test_build_extraction_result_preserves_final_confidence_when_score_is_stale(
) -> None:
    target = _target()
    candidate = _candidate()
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=12,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
        confidence="VERY_LOW",
        reason="decision: review only, not counted; cap: VERY_LOW",
        candidate_scores=(
            PeakCandidateScore(
                candidate=candidate,
                confidence="HIGH",
                reason="decision: detected",
                raw_score=95,
            ),
        ),
    )
    selected = selected_peak_hypothesis(
        build_production_peak_hypotheses(
            config=_Config(),
            sample_name="SampleA",
            target=target,
            peak_result=peak_result,
        )
    )

    result = build_extraction_result(
        peak_result=peak_result,
        nl_result=None,
        candidate_ms2_evidence=None,
        target=target,
        candidate=candidate,
        scoring_context_builder=None,
        selected_hypothesis=selected,
    )

    assert selected is not None
    assert selected.evidence.confidence == "VERY_LOW"
    assert result.confidence == "VERY_LOW"
    assert result.reason == "decision: review only, not counted; cap: VERY_LOW"


class _Config:
    resolver_mode = "region_first_safe_merge"


def _target() -> Target:
    return Target(
        label="Analyte",
        mz=258.1085,
        rt_min=8.0,
        rt_max=9.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=False,
        istd_pair="ISTD",
    )


def _candidate() -> PeakCandidate:
    peak = PeakResult(
        rt=8.5,
        intensity=1200.0,
        intensity_smoothed=1100.0,
        area=1234.5,
        peak_start=8.4,
        peak_end=8.6,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=8.5,
        selection_apex_intensity=1100.0,
        selection_apex_index=1,
        raw_apex_rt=8.5,
        raw_apex_intensity=1200.0,
        raw_apex_index=1,
        prominence=700.0,
        quality_flags=("too_broad",),
    )


def _score(candidate: PeakCandidate) -> PeakCandidateScore:
    return PeakCandidateScore(
        candidate=candidate,
        confidence="LOW",
        reason="concerns: local_sn",
        raw_score=41,
        concern_labels=("local_sn",),
    )


def _ms2_evidence() -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=True,
        nl_match=False,
        nl_status="NL_FAIL",
        trigger_scan_count=1,
        strict_nl_scan_count=0,
        best_loss_ppm=125.0,
        best_scan_rt=8.5,
        best_product_base_ratio=0.4,
        alignment_source="region",
    )
```

- [ ] **Step 2: Run tests and verify expected failure**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_result_assembly.py -q
```

Expected: fail with `TypeError: build_extraction_result() got an unexpected keyword argument 'selected_hypothesis'`.

- [ ] **Step 3: Add optional selected hypothesis support**

Modify `xic_extractor/extraction/result_assembly.py`:

```python
from xic_extractor.peak_detection.hypotheses import PeakHypothesis
```

Change the signature:

```python
def build_extraction_result(
    *,
    peak_result: PeakDetectionResult,
    nl_result: NLResult | None,
    candidate_ms2_evidence: CandidateMS2Evidence | None,
    target: Target,
    candidate: PeakCandidate | None,
    scoring_context_builder: Any | None,
    selected_hypothesis: PeakHypothesis | None = None,
) -> ExtractionResult:
```

Add local helpers near the function:

```python
def _result_confidence(
    peak_result: PeakDetectionResult,
    selected_hypothesis: PeakHypothesis | None,
) -> str:
    if selected_hypothesis is not None and selected_hypothesis.evidence.confidence:
        return selected_hypothesis.evidence.confidence
    if peak_result.peak is None:
        return ""
    return peak_result.confidence or "HIGH"


def _result_reason(
    peak_result: PeakDetectionResult,
    selected_hypothesis: PeakHypothesis | None,
) -> str:
    if selected_hypothesis is not None and selected_hypothesis.evidence.reason:
        return selected_hypothesis.evidence.reason
    return peak_result.reason or ""
```

Change the `ExtractionResult(...)` field mapping:

```python
target_label=(
    selected_hypothesis.target_label if selected_hypothesis is not None else target.label
),
role=(
    selected_hypothesis.role
    if selected_hypothesis is not None
    else "ISTD" if target.is_istd else "Analyte"
),
istd_pair=(
    selected_hypothesis.istd_pair
    if selected_hypothesis is not None
    else target.istd_pair
),
confidence=_result_confidence(peak_result, selected_hypothesis),
reason=_result_reason(peak_result, selected_hypothesis),
quality_flags=(
    selected_hypothesis.evidence.quality_flags
    if selected_hypothesis is not None
    else quality_flags
),
```

Keep `quality_penalty`, `severities`, `prior_rt`, `prior_source`, and
`score_breakdown` unchanged from the existing behavior.

- [ ] **Step 4: Run result assembly tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_result_assembly.py tests\test_messages.py tests\test_csv_writers.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add xic_extractor\extraction\result_assembly.py tests\test_result_assembly.py
git commit -m "feat: assemble extraction results from selected hypotheses"
```

---

### Task 3: Wire Targeted Extraction To The Production-Safe Spine

**Files:**
- Modify: `xic_extractor/extraction/target_extraction.py`
- Modify: `tests/test_target_extraction.py`

- [ ] **Step 1: Write failing targeted extraction wiring test**

Add these imports at the top of `tests/test_target_extraction.py`, preserving
ruff import ordering:

```python
import numpy as np

import xic_extractor.extraction.target_extraction as target_extraction
from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extractor import ExtractionResult
from xic_extractor.extraction.istd_recovery import IstdAnchorRecoveryDecision
from xic_extractor.neutral_loss import NLResult
from xic_extractor.peak_detection.hypotheses import PeakHypothesis
from xic_extractor.peak_detection.models import PeakDetectionResult
```

Then add this test function near the existing target-extraction tests:

```python

def test_extract_one_target_passes_selected_hypothesis_to_result_assembly(
    tmp_path,
    monkeypatch,
) -> None:
    config = ExtractionConfig(
        data_dir=tmp_path,
        dll_dir=tmp_path,
        output_csv=tmp_path / "xic_results.csv",
        diagnostics_csv=tmp_path / "diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        emit_peak_candidates=True,
        resolver_mode="region_first_safe_merge",
    )
    target = Target(
        label="Analyte",
        mz=258.1085,
        rt_min=8.0,
        rt_max=9.0,
        ppm_tol=20.0,
        neutral_loss_da=None,
        nl_ppm_warn=None,
        nl_ppm_max=None,
        is_istd=False,
        istd_pair="",
    )
    candidate = _candidate()
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=5,
        max_smoothed=1200.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
    )
    captured: dict[str, object] = {}

    class _Raw:
        def extract_xic(self, *_args, **_kwargs):
            return (
                np.asarray([8.3, 8.4, 8.5, 8.6, 8.7]),
                np.asarray([10.0, 25.0, 100.0, 25.0, 10.0]),
            )

    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        lambda *_args, **_kwargs: peak_result,
    )
    monkeypatch.setattr(
        target_extraction,
        "check_target_nl",
        lambda *_args, **_kwargs: NLResult("NO_MS2", None, None, 0, 0, 0),
    )
    monkeypatch.setattr(
        target_extraction,
        "recover_istd_anchor_peak_if_needed",
        lambda peak_result, **_kwargs: IstdAnchorRecoveryDecision(peak_result),
    )
    monkeypatch.setattr(
        target_extraction,
        "append_peak_audit_rows",
        lambda **_kwargs: None,
    )

    def _fake_build_extraction_result(**kwargs):
        captured.update(kwargs)
        return ExtractionResult(
            peak_result=kwargs["peak_result"],
            nl=kwargs["nl_result"],
            target_label=kwargs["target"].label,
        )

    monkeypatch.setattr(
        target_extraction,
        "build_extraction_result",
        _fake_build_extraction_result,
    )

    results: dict[str, object] = {}
    diagnostics = []
    target_extraction.extract_one_target(
        _Raw(),
        config,
        "SampleA",
        target,
        reference_rt=None,
        results=results,
        diagnostics=diagnostics,
    )

    selected = captured["selected_hypothesis"]
    assert isinstance(selected, PeakHypothesis)
    assert selected.audit.selected is True
    assert selected.target_label == "Analyte"
    assert isinstance(results["Analyte"], ExtractionResult)
```

This test reuses the existing `_candidate()` helper already present in
`tests/test_target_extraction.py`. If the helper name collides after import
reordering, keep a single `_candidate()` definition in that file.

- [ ] **Step 2: Run test and verify expected failure**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_target_extraction.py::test_extract_one_target_passes_selected_hypothesis_to_result_assembly -q
```

Expected: fail because `selected_hypothesis` is not passed to
`build_extraction_result`.

- [ ] **Step 3: Wire production-safe selected hypothesis in extraction**

Modify imports in `xic_extractor/extraction/target_extraction.py`:

```python
from xic_extractor.extraction.handoff_spine_runtime import (
    build_production_peak_hypotheses,
    selected_peak_hypothesis,
)
```

After `candidate_ms2_evidence = selected_candidate_ms2_evidence(...)`, add:

```python
production_hypotheses = build_production_peak_hypotheses(
    config=config,
    sample_name=sample_name,
    target=target,
    peak_result=peak_result,
    selected_candidate_ms2_evidence=candidate_ms2_evidence,
    rt=audit_rt,
    intensity=audit_intensity,
    trace_group=trace_group,
)
selected_hypothesis = selected_peak_hypothesis(production_hypotheses)
```

Update `build_extraction_result(...)` call:

```python
result = build_extraction_result(
    peak_result=peak_result,
    nl_result=nl_result,
    candidate_ms2_evidence=candidate_ms2_evidence,
    target=target,
    candidate=candidate,
    scoring_context_builder=scoring_context_builder,
    selected_hypothesis=selected_hypothesis,
)
```

Do not pass `production_hypotheses` into `append_peak_audit_rows(...)`. The audit
path must continue to build its audit tuple because it includes CWT audit
proposals.

- [ ] **Step 4: Run targeted extraction and focused adjacent tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_target_extraction.py tests\test_extractor.py::test_istd_peak_not_found_retries_with_wider_anchor_window tests\test_extractor.py::test_istd_no_signal_anchor_window_retries_with_wider_anchor_window tests\test_extractor.py::test_istd_weak_anchor_window_peak_uses_wider_recovery -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 3**

```powershell
git add xic_extractor\extraction\target_extraction.py tests\test_target_extraction.py
git commit -m "feat: wire extraction results to handoff spine"
```

---

### Task 4: Closeout Note, Final Verification, And PR-Ready Review

**Files:**
- Create: `docs/superpowers/notes/2026-05-28-handoff-productization-mvp-closeout.md`
- Modify only if implementation review finds stale wording:
  - `docs/superpowers/specs/2026-05-28-handoff-productization-mvp-step2-step4-spec.md`
  - `docs/superpowers/plans/2026-05-28-handoff-productization-mvp-goal.md`

- [ ] **Step 1: Write the closeout note**

Create `docs/superpowers/notes/2026-05-28-handoff-productization-mvp-closeout.md`:

```markdown
# Handoff Productization MVP Closeout

## Verdict

Status: `handoff_spine_mvp_ready` / `production_candidate`.

This PR keeps the Step2 shared audit spine and adds the first production-facing
consumer: targeted `ExtractionResult` assembly can consume the selected
production-safe `PeakHypothesis` while preserving current output behavior.

This is not `production_ready`. It does not authorize default switches, legacy
retirement, CWT production promotion, ASLS promotion, or matrix value changes.

## Public Contracts

- `peak_candidates.tsv`: header/order unchanged.
- `peak_candidate_boundaries.tsv`: header/order unchanged.
- `alignment_matrix.tsv`: remains the downstream correction/statistics delivery
  surface and is not changed by this PR.
- CLI flags, config keys, workbook schemas, resolver defaults, and baseline
  defaults are unchanged.

## Runtime Change

- Audit projection builds one shared audit hypothesis tuple and projects both
  candidate and boundary audit rows from it.
- Production result assembly builds a separate production-safe hypothesis tuple
  from the original production `PeakDetectionResult`.
- Production assembly uses the selected hypothesis as an internal handoff
  contract, without using CWT audit-only proposals.

## Verification

Record the exact focused test, compile, ruff, and diff-check commands run here.

## Next Decision

The next handoff productization decision is whether selected peak/integration
behavior should be natively represented by the spine, or whether downstream
matrix handoff should consume a spine-derived contract. It should not be another
audit-only report unless it closes a specific production decision.
```

- [ ] **Step 2: Run full focused verification**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_peak_hypotheses.py tests\test_handoff_spine_runtime.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run static checks**

Run:

```powershell
python -m py_compile xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py
uv run ruff check xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py tests\test_peak_candidate_audit.py tests\test_peak_candidate_boundaries.py tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py
git diff --check
```

Expected: all checks pass. If `uv` hits user-cache permission errors, rerun the
same `uv run ruff ...` command with approved escalation; do not substitute a
different linter command.

- [ ] **Step 4: Inspect for architecture drift**

Run:

```powershell
rg -n "add_cwt_proposals_for_audit|peak_candidate_table|peak_candidate_boundaries|peak_candidate_audit" xic_extractor\extraction\result_assembly.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\target_extraction.py
```

Expected:

- `handoff_spine_runtime.py` has no matches.
- `result_assembly.py` has no matches.
- `target_extraction.py` may match `append_peak_audit_rows` only because audit
  projection remains there.

Inspect changed docs only for overclaim wording. Do not scan all historical docs
as a pass/fail gate.

- [ ] **Step 5: Review the implementation before closeout commit**

Review the full diff against the checklist below with an explicit critical
thinking pass:

- Does this PR advance product-facing handoff behavior, or did it accidentally
  fall back to another audit-only adapter?
- Did any production path import writer/audit modules or CWT audit-only proposal
  logic?
- Did any behavior change leak into resolver selection, scoring, NL matching,
  baseline, diagnostics, or matrix outputs?
- Are parity tests strong enough to catch changed `ExtractionResult` behavior?
- Are docs and closeout wording honest about `production_candidate` versus
  `production_ready`?

If the review finds a blocker, fix it and rerun the smallest affected tests
before committing.

- [ ] **Step 6: Commit Task 4**

```powershell
git add docs\superpowers\notes\2026-05-28-handoff-productization-mvp-closeout.md
git commit -m "docs: close out handoff productization mvp"
```

- [ ] **Step 7: Final branch status**

Run:

```powershell
git status --short --branch
git log --oneline --decorate -6
```

Expected:

- clean worktree;
- branch contains Step2 docs, Step2 implementation, the reviewed planning
  artifacts commit, and the four MVP runtime/result/wiring/closeout commits.

---

## Implementation Review Checklist

After Task 4, review the whole diff before push / PR:

- [ ] Production path does not import TSV writer modules.
- [ ] CWT audit proposal injection remains audit-only.
- [ ] `ExtractionResult` public dataclass fields are unchanged.
- [ ] `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` headers are unchanged.
- [ ] No alignment / matrix writer files changed.
- [ ] No resolver default, baseline default, scoring weight, or NL matching behavior changed.
- [ ] Tests prove selected-hypothesis assembly parity and `HIGH` fallback.
- [ ] Tests prove stale candidate scores cannot undo final
  `PeakDetectionResult` confidence/reason downgrades.
- [ ] Closeout note uses `handoff_spine_mvp_ready` / `production_candidate` only.
- [ ] Remaining risk is explicitly limited to future native spine-backed selection/integration or downstream matrix handoff.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `$plan-ceo-review` | Scope & strategy | 1 | CLEAR | Scope held: Step2+Step3+Step4 closes one coherent MVP decision without expanding into cleanup, matrix behavior, ASLS, CWT production, or 85RAW validation. |
| Codex Review | `critical-artifact-review` | Independent artifact challenge | 1 | FIXED | Added missing runtime-helper verification, planning artifact commit step, post-implementation critical review gate, and stronger trace-context test coverage. |
| Eng Review | `$plan-eng-review` | Architecture & tests | 1 | FIXED | Found one blocker: stale candidate-level scores could undo final `PeakDetectionResult` confidence/reason downgrades. Spec, goal, tests, and implementation guidance now require final-result precedence. |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | SKIPPED | No UI or human-facing report surface changes in this MVP. |
| DX Review | `$plan-devex-review` | Developer experience gaps | 1 | CLEAR | Execution path now has Task 0 recoverability, focused commands, stop rules, expected failures, and final review/reporting requirements. |

**UNRESOLVED:** 0.

**VERDICT:** CEO + DX + ENG CLEARED after fixing the stale-score blocker. Ready to execute Task 0, then implement the MVP task-by-task.
