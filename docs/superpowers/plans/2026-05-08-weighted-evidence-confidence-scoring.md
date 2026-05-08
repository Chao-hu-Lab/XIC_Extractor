# Weighted Evidence Confidence Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current pure penalty confidence model with weighted positive/negative evidence plus explicit confidence caps.

**Architecture:** Keep `xic_extractor.peak_scoring` as the public compatibility surface, but move the new evidence arithmetic into focused internal helpers so the scoring rules are inspectable and testable. Preserve default workbook columns while allowing optional Score Breakdown to expose base score, positive points, negative points, caps, and final confidence.

**Tech Stack:** Python 3.14, pytest, numpy, openpyxl, existing `xic_extractor.peak_scoring`, `xic_extractor.output`, and validation harness scripts.

**Spec:** `docs/superpowers/specs/2026-05-08-weighted-evidence-confidence-scoring-spec.md`

---

## Execution Rules

1. Use TDD for every behavior change.
2. Commit after each task.
3. Do not change resolver parameters or area integration.
4. Do not change default workbook row-level columns.
5. Keep `from xic_extractor.peak_scoring import score_candidate` compatible.
6. Run 8-raw validation before 85-raw validation.
7. If real-data output shows broad unexpected target flips, stop and review before adding more scoring rules.

---

## File Structure

Planned ownership:

- Create `xic_extractor/peak_scoring_evidence.py`
  - Owns evidence dataclasses, score arithmetic, confidence thresholds, cap application, and reason text assembly.
  - Does not import RAW readers, workbook builders, GUI, or validation harness.
- Modify `xic_extractor/peak_scoring.py`
  - Keeps existing public scoring functions and signal severity helpers.
  - Converts existing signal results into weighted evidence records.
  - Returns the existing `ScoredCandidate` public shape with compatible fields.
- Modify `xic_extractor/peak_detection/models.py`
  - Adds a generic immutable `score_breakdown` tuple to `PeakDetectionResult`
    without importing scoring modules into peak-detection models.
- Modify `xic_extractor/peak_detection/facade.py`
  - Copies selected candidate evidence details onto `PeakDetectionResult`.
- Modify `xic_extractor/extractor.py`
  - Copies `PeakDetectionResult.score_breakdown` onto `ExtractionResult`.
- Modify `xic_extractor/extraction/anchors.py`
  - Replaces direct confidence mutation helper with an explicit cap reason carried through scoring/output.
  - Keeps current `paired_anchor_mismatch_diagnostic()` public behavior.
- Modify `xic_extractor/output/sheet_summary.py`
  - Keeps detection contract excluding `VERY_LOW`, `NL_FAIL`, and disallowed `NO_MS2`.
- Modify `xic_extractor/output/schema.py`, `xic_extractor/output/csv_writers.py`,
  `xic_extractor/output/excel_pipeline.py`, and
  `xic_extractor/output/sheet_score_breakdown.py`
  - Adds optional positive/negative/cap fields only when `emit_score_breakdown=true`.
- Tests:
  - `tests/test_peak_scoring_evidence.py`
  - `tests/test_peak_scoring.py`
  - `tests/test_extractor.py`
  - `tests/test_csv_to_excel.py`
  - `tests/test_review_metrics.py`

---

## Task 1 — Evidence Score Model

**Files:**

- Create: `tests/test_peak_scoring_evidence.py`
- Create: `xic_extractor/peak_scoring_evidence.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_peak_scoring_evidence.py`:

```python
from xic_extractor.peak_scoring_evidence import (
    ConfidenceCap,
    EvidenceSignal,
    apply_confidence_caps,
    confidence_from_score,
    score_evidence,
)


def test_score_evidence_adds_support_and_subtracts_concerns() -> None:
    result = score_evidence(
        positive=[
            EvidenceSignal("strict_nl_ok", 30),
            EvidenceSignal("local_sn_strong", 10),
        ],
        negative=[
            EvidenceSignal("rt_prior_borderline", 15),
        ],
    )

    assert result.base_score == 50
    assert result.positive_points == 40
    assert result.negative_points == 15
    assert result.raw_score == 75
    assert result.confidence == "MEDIUM"
    assert result.support_labels == ("strict_nl_ok", "local_sn_strong")
    assert result.concern_labels == ("rt_prior_borderline",)


def test_confidence_from_score_thresholds() -> None:
    assert confidence_from_score(80) == "HIGH"
    assert confidence_from_score(60) == "MEDIUM"
    assert confidence_from_score(40) == "LOW"
    assert confidence_from_score(39) == "VERY_LOW"


def test_caps_limit_final_confidence_without_changing_raw_score() -> None:
    scored = score_evidence(
        positive=[EvidenceSignal("strict_nl_ok", 30), EvidenceSignal("shape_clean", 10)],
        negative=[],
        caps=[ConfidenceCap("anchor_mismatch_cap", "VERY_LOW")],
    )

    assert scored.raw_score == 90
    assert scored.score_confidence == "HIGH"
    assert scored.confidence == "VERY_LOW"
    assert scored.cap_labels == ("anchor_mismatch_cap",)


def test_multiple_caps_use_strongest_cap() -> None:
    assert apply_confidence_caps(
        "HIGH",
        [
            ConfidenceCap("no_ms2_cap", "LOW"),
            ConfidenceCap("anchor_mismatch_cap", "VERY_LOW"),
        ],
    ) == "VERY_LOW"
```

- [ ] **Step 2: Run red tests**

Run:

```powershell
uv run pytest tests/test_peak_scoring_evidence.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.peak_scoring_evidence'`.

- [ ] **Step 3: Implement the minimal evidence model**

Create `xic_extractor/peak_scoring_evidence.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConfidenceValue = Literal["HIGH", "MEDIUM", "LOW", "VERY_LOW"]

_CONFIDENCE_RANK: dict[ConfidenceValue, int] = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
    "VERY_LOW": 3,
}


@dataclass(frozen=True)
class EvidenceSignal:
    label: str
    points: int


@dataclass(frozen=True)
class ConfidenceCap:
    label: str
    max_confidence: ConfidenceValue


@dataclass(frozen=True)
class EvidenceScore:
    base_score: int
    positive_points: int
    negative_points: int
    raw_score: int
    score_confidence: ConfidenceValue
    confidence: ConfidenceValue
    support_labels: tuple[str, ...]
    concern_labels: tuple[str, ...]
    cap_labels: tuple[str, ...]


def confidence_from_score(score: int) -> ConfidenceValue:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "VERY_LOW"


def apply_confidence_caps(
    confidence: ConfidenceValue,
    caps: list[ConfidenceCap],
) -> ConfidenceValue:
    capped = confidence
    for cap in caps:
        if _CONFIDENCE_RANK[cap.max_confidence] > _CONFIDENCE_RANK[capped]:
            capped = cap.max_confidence
    return capped


def score_evidence(
    *,
    positive: list[EvidenceSignal],
    negative: list[EvidenceSignal],
    caps: list[ConfidenceCap] | None = None,
    base_score: int = 50,
) -> EvidenceScore:
    cap_list = caps or []
    positive_points = sum(signal.points for signal in positive)
    negative_points = sum(signal.points for signal in negative)
    raw_score = base_score + positive_points - negative_points
    score_confidence = confidence_from_score(raw_score)
    confidence = apply_confidence_caps(score_confidence, cap_list)
    return EvidenceScore(
        base_score=base_score,
        positive_points=positive_points,
        negative_points=negative_points,
        raw_score=raw_score,
        score_confidence=score_confidence,
        confidence=confidence,
        support_labels=tuple(signal.label for signal in positive),
        concern_labels=tuple(signal.label for signal in negative),
        cap_labels=tuple(cap.label for cap in cap_list),
    )
```

- [ ] **Step 4: Run green tests**

Run:

```powershell
uv run pytest tests/test_peak_scoring_evidence.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/peak_scoring_evidence.py tests/test_peak_scoring_evidence.py
git commit -m "feat: add weighted evidence score model"
```

---

## Task 2 — Translate Existing Signals Into Weighted Evidence

**Files:**

- Modify: `tests/test_peak_scoring.py`
- Modify: `xic_extractor/peak_scoring.py`

- [ ] **Step 1: Write failing score-candidate tests**

Add to `tests/test_peak_scoring.py`:

```python
def test_score_candidate_records_positive_and_negative_evidence() -> None:
    cand = _make_candidate(apex_rt=10.0, apex_intensity=1000)
    x = np.linspace(9, 11, 201)
    y = 1000 * np.exp(-((x - 10) / 0.1) ** 2) + 5
    ctx = ScoringContext(
        rt_array=x,
        intensity_array=y,
        apex_index=100,
        half_width_ratio=1.0,
        fwhm_ratio=1.0,
        ms2_present=True,
        nl_match=True,
        rt_prior=10.0,
        rt_prior_sigma=0.1,
        rt_min=9.0,
        rt_max=11.0,
        dirty_matrix=False,
    )

    scored = score_candidate(cand, ctx, prior_rt=10.0)

    assert scored.confidence == Confidence.HIGH
    assert scored.evidence_score.raw_score >= 80
    assert "strict_nl_ok" in scored.evidence_score.support_labels
    assert "rt_prior_close" in scored.evidence_score.support_labels
    assert scored.evidence_score.concern_labels == ()


def test_score_candidate_nl_fail_caps_confidence_to_very_low() -> None:
    cand = _make_candidate(apex_rt=10.0, apex_intensity=1000)
    x = np.linspace(9, 11, 201)
    y = 1000 * np.exp(-((x - 10) / 0.1) ** 2) + 5
    ctx = ScoringContext(
        rt_array=x,
        intensity_array=y,
        apex_index=100,
        half_width_ratio=1.0,
        fwhm_ratio=1.0,
        ms2_present=True,
        nl_match=False,
        rt_prior=10.0,
        rt_prior_sigma=0.1,
        rt_min=9.0,
        rt_max=11.0,
        dirty_matrix=False,
    )

    scored = score_candidate(cand, ctx, prior_rt=10.0)

    assert scored.confidence == Confidence.VERY_LOW
    assert "nl_fail" in scored.evidence_score.concern_labels
    assert "nl_fail_cap" in scored.evidence_score.cap_labels
```

- [ ] **Step 2: Run red tests**

Run:

```powershell
uv run pytest tests/test_peak_scoring.py::test_score_candidate_records_positive_and_negative_evidence tests/test_peak_scoring.py::test_score_candidate_nl_fail_caps_confidence_to_very_low -v
```

Expected: FAIL because `ScoredCandidate` has no `evidence_score`.

- [ ] **Step 3: Extend `ScoredCandidate` and evidence translation**

Modify `xic_extractor/peak_scoring.py`:

```python
from xic_extractor.peak_scoring_evidence import (
    ConfidenceCap,
    EvidenceScore,
    EvidenceSignal,
    score_evidence,
)
```

Extend `ScoredCandidate`:

```python
@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Any
    severities: tuple[tuple[int, str], ...]
    confidence: Confidence
    reason: str
    prior_rt: float | None
    quality_penalty: int = 0
    selection_quality_penalty: float | None = None
    prefer_rt_prior_tiebreak: bool = False
    evidence_score: EvidenceScore | None = None
```

Add helpers:

```python
def _confidence_from_value(value: str) -> Confidence:
    return Confidence(value)


def _evidence_from_context(
    candidate: Any,
    ctx: ScoringContext,
    severities: list[tuple[int, str]],
    quality_penalty: int,
) -> tuple[list[EvidenceSignal], list[EvidenceSignal], list[ConfidenceCap]]:
    positive: list[EvidenceSignal] = []
    negative: list[EvidenceSignal] = []
    caps: list[ConfidenceCap] = []

    if ctx.ms2_present and ctx.nl_match:
        positive.append(EvidenceSignal("strict_nl_ok", 30))
    elif ctx.ms2_present and not ctx.nl_match:
        negative.append(EvidenceSignal("nl_fail", 45))
        caps.append(ConfidenceCap("nl_fail_cap", "VERY_LOW"))
    else:
        negative.append(EvidenceSignal("no_ms2", 25))
        caps.append(ConfidenceCap("no_ms2_cap", "LOW"))

    if ctx.rt_prior is not None:
        rt_severity = dict((label, severity) for severity, label in severities)[_LABEL_RT_PRIOR]
        if rt_severity == 0:
            positive.append(EvidenceSignal("rt_prior_close", 15))
        elif rt_severity == 1:
            negative.append(EvidenceSignal("rt_prior_borderline", 15))
        else:
            negative.append(EvidenceSignal("rt_prior_far", 35))

    if dict((label, severity) for severity, label in severities)[_LABEL_LOCAL_SN] == 0:
        positive.append(EvidenceSignal("local_sn_strong", 10))

    symmetry = dict((label, severity) for severity, label in severities)[_LABEL_SYMMETRY]
    width = dict((label, severity) for severity, label in severities)[_LABEL_PEAK_WIDTH]
    if symmetry == 0 and width == 0:
        positive.append(EvidenceSignal("shape_clean", 10))

    flags = {str(flag) for flag in getattr(candidate, "quality_flags", ())}
    if not flags.intersection(_ADAP_LIKE_FLAG_LABELS):
        positive.append(EvidenceSignal("trace_clean", 10))

    for severity, label in severities:
        if severity == 0:
            continue
        if label == _LABEL_LOCAL_SN:
            negative.append(EvidenceSignal("local_sn_poor" if severity == 2 else "local_sn_borderline", 25 if severity == 2 else 10))
        elif label in {_LABEL_SYMMETRY, _LABEL_PEAK_WIDTH}:
            negative.append(EvidenceSignal("shape_poor" if severity == 2 else "shape_borderline", 20 if severity == 2 else 10))
        elif label == "low scan support":
            negative.append(EvidenceSignal("low_scan_support", 15))
        elif label == "low trace continuity":
            negative.append(EvidenceSignal("low_trace_continuity", 10))
        elif label == "poor edge recovery":
            negative.append(EvidenceSignal("poor_edge_recovery", 10))

    if quality_penalty > 0:
        negative.append(EvidenceSignal("hard_quality_flag", 25 * quality_penalty))

    return positive, negative, caps
```

In `score_candidate()`, after computing severities and `quality_penalty`, call
`score_evidence()`, then set `confidence = _confidence_from_value(evidence_score.confidence)`.

Also add a serializable field helper in `xic_extractor/peak_scoring.py`:

```python
def score_breakdown_fields(evidence_score: EvidenceScore | None) -> tuple[tuple[str, str], ...]:
    if evidence_score is None:
        return ()
    return (
        ("Final Confidence", evidence_score.confidence),
        ("Caps", "; ".join(evidence_score.cap_labels)),
        ("Raw Score", str(evidence_score.raw_score)),
        ("Support", "; ".join(evidence_score.support_labels)),
        ("Concerns", "; ".join(evidence_score.concern_labels)),
        ("Base Score", str(evidence_score.base_score)),
        ("Positive Points", str(evidence_score.positive_points)),
        ("Negative Points", str(evidence_score.negative_points)),
    )
```

Modify `xic_extractor/peak_detection/models.py`:

```python
@dataclass(frozen=True)
class PeakDetectionResult:
    status: PeakStatus
    peak: PeakResult | None
    n_points: int
    max_smoothed: float | None
    n_prominent_peaks: int
    candidates: tuple[PeakCandidate, ...] = ()
    confidence: str | None = None
    reason: str | None = None
    severities: tuple[tuple[int, str], ...] = ()
    score_breakdown: tuple[tuple[str, str], ...] = ()
```

Modify `xic_extractor/peak_detection/facade.py` so `_detection_success()` accepts
`score_breakdown: tuple[tuple[str, str], ...] = ()` and passes it into
`PeakDetectionResult`. When a scored candidate is chosen, pass
`score_breakdown_fields(chosen.evidence_score)`.

- [ ] **Step 4: Run green tests**

Run:

```powershell
uv run pytest tests/test_peak_scoring.py::test_score_candidate_records_positive_and_negative_evidence tests/test_peak_scoring.py::test_score_candidate_nl_fail_caps_confidence_to_very_low -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/peak_scoring.py tests/test_peak_scoring.py
git commit -m "feat: score peaks with weighted evidence"
```

---

## Task 3 — Convert Anchor Mismatch To An Explicit Cap

**Files:**

- Modify: `tests/test_extractor.py`
- Modify: `xic_extractor/extraction/anchors.py`
- Modify: `xic_extractor/peak_scoring.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_extractor.py`:

```python
def test_anchor_mismatch_reason_reports_confidence_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    (config.data_dir / "SampleA.raw").write_text("", encoding="utf-8")
    targets = [
        _target("Analyte", istd_pair="ISTD"),
        _target("ISTD", is_istd=True),
    ]

    monkeypatch.setattr("xic_extractor.extractor.open_raw", _open_raw_factory())
    monkeypatch.setattr(
        "xic_extractor.extraction.istd_prepass.extract_istd_anchors_only",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_nl_anchor_rt",
        _anchor_sequence([13.70, 13.70, 13.75]),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.find_peak_and_area",
        _peak_sequence(
            [_ok_peak(13.70, 2000.0, 3000.0), _ok_peak(13.06, 5000.0, 8000.0)]
        ),
    )
    monkeypatch.setattr(
        "xic_extractor.extractor.check_nl",
        _nl_sequence(
            [
                NLResult("OK", 1.0, 13.70, 1, 0, 1),
                NLResult("OK", 1.0, 13.75, 1, 0, 1),
            ]
        ),
    )

    _run(config, targets)

    long_rows = _read_csv(config.output_csv.with_name("xic_results_long.csv"))
    analyte_row = next(row for row in long_rows if row["Target"] == "Analyte")
    assert analyte_row["Confidence"] == "VERY_LOW"
    assert analyte_row["Reason"].startswith("decision: review only, not counted")
    assert "cap: VERY_LOW due to anchor mismatch" in analyte_row["Reason"]
```

- [ ] **Step 2: Run red test**

Run:

```powershell
uv run pytest tests/test_extractor.py::test_anchor_mismatch_reason_reports_confidence_cap -v
```

Expected: FAIL because reason text does not contain the cap phrase.

- [ ] **Step 3: Implement explicit cap wording**

Modify `xic_extractor/extraction/anchors.py`:

```python
def apply_anchor_mismatch_penalty(
    peak_result: PeakDetectionResult,
    mismatch_reason: str,
) -> PeakDetectionResult:
    reason = (
        "decision: review only, not counted; "
        "cap: VERY_LOW due to anchor mismatch; "
        f"concerns: anchor mismatch; {mismatch_reason}"
    )
    if peak_result.reason:
        reason = f"{reason}; {peak_result.reason}"
    return replace(peak_result, confidence="VERY_LOW", reason=reason)
```

- [ ] **Step 4: Run green test**

Run:

```powershell
uv run pytest tests/test_extractor.py::test_anchor_mismatch_reason_reports_confidence_cap -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/extraction/anchors.py tests/test_extractor.py
git commit -m "fix: report anchor mismatch as confidence cap"
```

---

## Task 4 — Selector Uses Effective Score Instead Of Tuple-Only Penalty

**Files:**

- Modify: `tests/test_peak_scoring.py`
- Modify: `xic_extractor/peak_scoring.py`

- [ ] **Step 1: Write failing selector tests**

Add:

```python
def test_selector_uses_effective_score_to_balance_distance_and_evidence() -> None:
    near_weak = _sc(
        Confidence.LOW,
        10.02,
        1000.0,
        10.0,
        selection_quality_penalty=0.5,
    )
    far_strong = _sc(
        Confidence.MEDIUM,
        10.40,
        2000.0,
        10.0,
        selection_quality_penalty=0.0,
    )
    near_weak = replace(near_weak, evidence_score=_score_for_selector(55))
    far_strong = replace(far_strong, evidence_score=_score_for_selector(70))

    assert (
        select_candidate_with_confidence(
            [near_weak, far_strong],
            selection_rt=10.0,
        )
        is near_weak
    )


def test_selector_does_not_let_far_peak_win_on_score_alone() -> None:
    near = _sc(Confidence.LOW, 10.02, 1000.0, 10.0, selection_quality_penalty=0.0)
    far = _sc(Confidence.MEDIUM, 11.20, 3000.0, 10.0, selection_quality_penalty=0.0)
    near = replace(near, evidence_score=_score_for_selector(45))
    far = replace(far, evidence_score=_score_for_selector(75))

    assert select_candidate_with_confidence([near, far], selection_rt=10.0) is near
```

Also add a small helper in the same test file:

```python
from dataclasses import replace
from xic_extractor.peak_scoring_evidence import EvidenceScore


def _score_for_selector(raw_score: int) -> EvidenceScore:
    confidence = "HIGH" if raw_score >= 80 else "MEDIUM" if raw_score >= 60 else "LOW" if raw_score >= 40 else "VERY_LOW"
    return EvidenceScore(
        base_score=50,
        positive_points=max(0, raw_score - 50),
        negative_points=max(0, 50 - raw_score),
        raw_score=raw_score,
        score_confidence=confidence,
        confidence=confidence,
        support_labels=(),
        concern_labels=(),
        cap_labels=(),
    )
```

- [ ] **Step 2: Run red tests**

Run:

```powershell
uv run pytest tests/test_peak_scoring.py::test_selector_uses_effective_score_to_balance_distance_and_evidence tests/test_peak_scoring.py::test_selector_does_not_let_far_peak_win_on_score_alone -v
```

Expected: FAIL until selector uses `evidence_score.raw_score` and score-point distance penalties.

- [ ] **Step 3: Implement effective-score key**

Modify `select_candidate_with_confidence()`:

```python
_SELECTION_DISTANCE_POINTS_PER_MIN = 40.0
_SELECTION_QUALITY_POINTS_PER_UNIT = 10.0
_SELECTION_FAR_DISTANCE_MAX_MIN = 0.75


def _effective_score(scored_candidate: ScoredCandidate, distance: float) -> float:
    raw_score = (
        float(scored_candidate.evidence_score.raw_score)
        if scored_candidate.evidence_score is not None
        else 50.0 - float(_CONFIDENCE_RANK[scored_candidate.confidence]) * 20.0
    )
    selection_quality_penalty = _selection_penalty_value(scored_candidate)
    return raw_score - (
        distance * _SELECTION_DISTANCE_POINTS_PER_MIN
    ) - (
        selection_quality_penalty * _SELECTION_QUALITY_POINTS_PER_UNIT
    )
```

For non-strict selection with a reference RT, use:

```python
if selection_reference is not None:
    if distance > _SELECTION_FAR_DISTANCE_MAX_MIN:
        return (1.0, distance, -_effective_score(scored_candidate, distance))
    return (0.0, -_effective_score(scored_candidate, distance), distance)
```

Keep strict preferred RT path distance-first.

- [ ] **Step 4: Run green tests**

Run:

```powershell
uv run pytest tests/test_peak_scoring.py::test_selector_uses_effective_score_to_balance_distance_and_evidence tests/test_peak_scoring.py::test_selector_does_not_let_far_peak_win_on_score_alone -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/peak_scoring.py tests/test_peak_scoring.py
git commit -m "feat: select peaks by weighted effective score"
```

---

## Task 5 — Reason Text Shows Decision, Support, Concerns, And Caps

**Files:**

- Modify: `tests/test_peak_scoring.py`
- Modify: `xic_extractor/peak_scoring.py`

- [ ] **Step 1: Write failing reason test**

Add:

```python
def test_reason_text_leads_with_decision_then_support_concerns_and_caps() -> None:
    cand = _make_candidate(apex_rt=10.8, apex_intensity=1000)
    x = np.linspace(9, 11, 201)
    y = 1000 * np.exp(-((x - 10.8) / 0.1) ** 2) + 5
    ctx = ScoringContext(
        rt_array=x,
        intensity_array=y,
        apex_index=180,
        half_width_ratio=1.0,
        fwhm_ratio=1.0,
        ms2_present=True,
        nl_match=False,
        rt_prior=10.0,
        rt_prior_sigma=0.1,
        rt_min=9.0,
        rt_max=11.0,
        dirty_matrix=False,
    )

    scored = score_candidate(cand, ctx, prior_rt=10.0)

    assert scored.reason.startswith("decision: review only, not counted")
    assert "cap: VERY_LOW due to nl fail" in scored.reason
    assert "strict NL OK" not in scored.reason
    assert scored.reason.index("cap:") < scored.reason.index("support:")
    assert scored.reason.index("support:") < scored.reason.index("concerns:")
    assert "concerns:" in scored.reason
    assert "nl fail" in scored.reason
    assert "rt prior far" in scored.reason
```

Add a focused grammar test so default `Reason` stays readable:

```python
def test_reason_text_limits_default_evidence_labels() -> None:
    score = EvidenceScore(
        base_score=50,
        positive_points=50,
        negative_points=90,
        raw_score=10,
        score_confidence="VERY_LOW",
        confidence="VERY_LOW",
        support_labels=(
            "strict_nl_ok",
            "rt_prior_close",
            "local_sn_strong",
            "shape_clean",
        ),
        concern_labels=(
            "nl_fail",
            "rt_prior_far",
            "anchor_mismatch",
            "low_trace_continuity",
            "poor_edge_recovery",
        ),
        cap_labels=("nl_fail_cap",),
    )

    reason = build_evidence_reason(score, istd_confidence_note=None)

    assert reason.startswith("decision: review only, not counted; cap:")
    assert "support: strict NL OK; RT prior close; local S/N strong" in reason
    assert "shape clean" not in reason
    assert "concerns: nl fail; rt prior far; anchor mismatch; low trace continuity" in reason
    assert "poor edge recovery" not in reason
```

- [ ] **Step 2: Run red test**

Run:

```powershell
uv run pytest tests/test_peak_scoring.py::test_reason_text_leads_with_decision_then_support_concerns_and_caps tests/test_peak_scoring.py::test_reason_text_limits_default_evidence_labels -v
```

Expected: FAIL because reason still uses severity-only wording.

- [ ] **Step 3: Implement evidence reason builder**

Add:

```python
_EVIDENCE_REASON_LABELS = {
    "strict_nl_ok": "strict NL OK",
    "rt_prior_close": "RT prior close",
    "local_sn_strong": "local S/N strong",
    "shape_clean": "shape clean",
    "trace_clean": "trace clean",
    "nl_fail": "nl fail",
    "no_ms2": "no MS2",
    "rt_prior_far": "rt prior far",
    "rt_prior_borderline": "rt prior borderline",
    "anchor_mismatch": "anchor mismatch",
    "low_scan_support": "low scan support",
    "low_trace_continuity": "low trace continuity",
    "poor_edge_recovery": "poor edge recovery",
}

_CAP_REASON_LABELS = {
    "nl_fail_cap": ("VERY_LOW", "nl fail"),
    "no_ms2_cap": ("LOW", "no MS2"),
    "anchor_mismatch_cap": ("VERY_LOW", "anchor mismatch"),
    "zero_area_cap": ("VERY_LOW", "zero area"),
}


def build_evidence_reason(
    evidence_score: EvidenceScore,
    istd_confidence_note: str | None,
) -> str:
    parts: list[str] = []
    if evidence_score.confidence == "VERY_LOW":
        parts.append("decision: review only, not counted")
    else:
        parts.append("decision: accepted")
    for cap in evidence_score.cap_labels:
        max_confidence, cap_name = _CAP_REASON_LABELS.get(
            cap, ("VERY_LOW", cap.removesuffix("_cap").replace("_", " "))
        )
        parts.append(f"cap: {max_confidence} due to {cap_name}")
    if evidence_score.support_labels:
        parts.append(
            "support: "
            + "; ".join(
                _EVIDENCE_REASON_LABELS.get(label, label)
                for label in evidence_score.support_labels[:3]
            )
        )
    if evidence_score.concern_labels:
        parts.append(
            "concerns: "
            + "; ".join(
                _EVIDENCE_REASON_LABELS.get(label, label)
                for label in evidence_score.concern_labels[:4]
            )
        )
    if istd_confidence_note is not None:
        parts.append(istd_confidence_note)
    return "; ".join(parts) if parts else "all checks passed"
```

Use this reason when `evidence_score` is present.

- [ ] **Step 4: Run green test**

Run:

```powershell
uv run pytest tests/test_peak_scoring.py::test_reason_text_leads_with_decision_then_support_concerns_and_caps tests/test_peak_scoring.py::test_reason_text_limits_default_evidence_labels -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/peak_scoring.py tests/test_peak_scoring.py
git commit -m "feat: explain weighted confidence evidence"
```

---

## Task 6 — Optional Score Breakdown Exposes Evidence Score

**Files:**

- Modify: `tests/test_csv_writers.py`
- Modify: `tests/test_csv_to_excel.py`
- Modify: `tests/test_excel_pipeline.py`
- Modify: `xic_extractor/output/schema.py`
- Modify: `xic_extractor/output/csv_writers.py`
- Modify: `xic_extractor/output/excel_pipeline.py`
- Modify: `xic_extractor/output/sheet_score_breakdown.py`
- Modify: `xic_extractor/extractor.py`

- [ ] **Step 1: Write failing CSV score-breakdown test**

Add to `tests/test_csv_writers.py`:

```python
def test_score_breakdown_csv_includes_weighted_evidence_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = replace(
        _result(),
        score_breakdown=(
            ("Base Score", "50"),
            ("Positive Points", "40"),
            ("Negative Points", "0"),
            ("Raw Score", "90"),
            ("Caps", ""),
            ("Final Confidence", "HIGH"),
            ("Support", "strict_nl_ok; local_sn_strong"),
            ("Concerns", ""),
        ),
    )
    file_result = FileResult(sample_name="SampleA", results={"WithNL": result})

    write_score_breakdown_csv(config, [file_result])

    breakdown = _read_csv(config.output_csv.with_name("xic_score_breakdown.csv"))[0]
    assert breakdown["Base Score"] == "50"
    assert breakdown["Positive Points"] == "40"
    assert breakdown["Negative Points"] == "0"
    assert breakdown["Raw Score"] == "90"
    assert breakdown["Caps"] == ""
    assert breakdown["Final Confidence"] == "HIGH"
    assert breakdown["Detection Counted"] == "TRUE"
    assert breakdown["Support"] == "strict_nl_ok; local_sn_strong"
    assert breakdown["Concerns"] == ""
```

- [ ] **Step 2: Run red CSV test**

Run:

```powershell
uv run pytest tests/test_csv_writers.py::test_score_breakdown_csv_includes_weighted_evidence_fields -v
```

Expected: FAIL because `ExtractionResult` has no `score_breakdown` field and
`SCORE_BREAKDOWN_HEADERS` has no weighted evidence columns.

- [ ] **Step 3: Add score breakdown fields to result and CSV output**

Modify `xic_extractor/extractor.py`:

```python
@dataclass(frozen=True)
class ExtractionResult:
    peak_result: PeakDetectionResult
    nl: NLResult | None
    candidate_ms2_evidence: CandidateMS2Evidence | None = None
    target_label: str = ""
    role: str = ""
    istd_pair: str = ""
    confidence: str = ""
    reason: str = ""
    severities: tuple[tuple[int, str], ...] = ()
    prior_rt: float | None = None
    prior_source: str = ""
    quality_penalty: int = 0
    quality_flags: tuple[str, ...] = ()
    score_breakdown: tuple[tuple[str, str], ...] = ()
```

Also extend `ExtractionResultLike` in `xic_extractor/output/csv_writers.py` with
`score_breakdown: tuple[tuple[str, str], ...]` so writer tests and type checks
use the same contract as `ExtractionResult`.

In `xic_extractor/extraction/target_extraction.py`, set:

```python
score_breakdown=peak_result.score_breakdown,
```

Modify `xic_extractor/output/schema.py`:

```python
SCORE_BREAKDOWN_HEADERS: tuple[str, ...] = (
    "SampleName",
    "Target",
    "Final Confidence",
    "Detection Counted",
    "Caps",
    "Raw Score",
    "Support",
    "Concerns",
    "Base Score",
    "Positive Points",
    "Negative Points",
    "symmetry",
    "local_sn",
    "nl_support",
    "rt_prior",
    "rt_centrality",
    "noise_shape",
    "peak_width",
    "Quality Penalty",
    "Quality Flags",
    "Total Severity",
    "Confidence",
    "Prior RT",
    "Prior Source",
)
```

Modify `write_score_breakdown_csv()` to pass
`count_no_ms2_as_detected=config.count_no_ms2_as_detected` into
`_score_breakdown_rows()`.

Modify `_score_breakdown_rows()` in `xic_extractor/output/csv_writers.py`:

```python
weighted_fields = dict(result.score_breakdown)
row = {
    "SampleName": file_result.sample_name,
    "Target": result.target_label,
    "Final Confidence": weighted_fields.get("Final Confidence", result.confidence),
    "Detection Counted": "TRUE"
    if is_accepted_result_detection(result, count_no_ms2_as_detected)
    else "FALSE",
    "Caps": weighted_fields.get("Caps", ""),
    "Raw Score": weighted_fields.get("Raw Score", ""),
    "Support": weighted_fields.get("Support", ""),
    "Concerns": weighted_fields.get("Concerns", ""),
    "Base Score": weighted_fields.get("Base Score", ""),
    "Positive Points": weighted_fields.get("Positive Points", ""),
    "Negative Points": weighted_fields.get("Negative Points", ""),
    "symmetry": _format_optional_severity(severities.get("symmetry")),
    "local_sn": _format_optional_severity(severities.get("local_sn")),
    "nl_support": _format_optional_severity(severities.get("nl_support")),
    "rt_prior": _format_optional_severity(severities.get("rt_prior")),
    "rt_centrality": _format_optional_severity(severities.get("rt_centrality")),
    "noise_shape": _format_optional_severity(severities.get("noise_shape")),
    "peak_width": _format_optional_severity(severities.get("peak_width")),
    "Quality Penalty": str(result.quality_penalty),
    "Quality Flags": ",".join(result.quality_flags),
    "Total Severity": str(result.total_severity),
    "Confidence": result.confidence,
    "Prior RT": _format_optional_number(result.prior_rt),
    "Prior Source": result.prior_source,
}
rows.append(row)
```

If accepted-detection logic currently exists only as private row helpers,
promote shared helpers such as `is_accepted_row_detection()` and
`is_accepted_result_detection()`. Summary and HTML heatmap should call the row
helper; Score Breakdown should call the result helper so it does not need to
reconstruct a long-row dictionary only to answer a yes/no decision.

- [ ] **Step 4: Run green CSV test**

Run:

```powershell
uv run pytest tests/test_csv_writers.py::test_score_breakdown_csv_includes_weighted_evidence_fields -v
```

Expected: PASS.

- [ ] **Step 5: Write failing workbook test**

Add to `tests/test_csv_to_excel.py::test_run_emits_score_breakdown_sheet_when_enabled`
by extending the fake `xic_score_breakdown.csv` row:

```python
"Base Score": "50",
"Positive Points": "40",
"Negative Points": "0",
"Raw Score": "90",
"Caps": "",
"Final Confidence": "HIGH",
"Detection Counted": "TRUE",
"Support": "strict_nl_ok; local_sn_strong",
"Concerns": "",
```

Then add assertions after reading `row`:

```python
assert row["Base Score"] == 50
assert row["Positive Points"] == 40
assert row["Negative Points"] == 0
assert row["Raw Score"] == 90
assert row["Final Confidence"] == "HIGH"
assert row["Detection Counted"] == "TRUE"
assert row["Support"] == "strict_nl_ok; local_sn_strong"
assert row["Concerns"] is None
```

- [ ] **Step 6: Run red workbook test**

Run:

```powershell
uv run pytest tests/test_csv_to_excel.py::test_run_emits_score_breakdown_sheet_when_enabled -v
```

Expected: FAIL if `sheet_score_breakdown.py` still treats the new numeric fields
as text.

- [ ] **Step 7: Format weighted numeric fields as numbers**

Modify `xic_extractor/output/sheet_score_breakdown.py` numeric field set:

```python
if header in {
    "symmetry",
    "local_sn",
    "nl_support",
    "rt_prior",
    "rt_centrality",
    "noise_shape",
    "peak_width",
    "Quality Penalty",
    "Total Severity",
    "Prior RT",
    "Base Score",
    "Positive Points",
    "Negative Points",
    "Raw Score",
}:
    value = _safe_float(raw_value)
else:
    value = _excel_text(raw_value)
```

Also mirror the new weighted fields in
`xic_extractor/output/excel_pipeline.py::_run_output_to_score_breakdown_rows()`
using `dict(result.score_breakdown)`.

- [ ] **Step 8: Run green workbook tests**

Run:

```powershell
uv run pytest tests/test_csv_to_excel.py::test_run_emits_score_breakdown_sheet_when_enabled tests/test_excel_pipeline.py::test_write_excel_from_run_output_adds_score_breakdown_when_enabled -v
```

Expected: PASS.

- [ ] **Step 9: Run score-breakdown schema contract**

Modify `tests/test_output_schema_contract.py` so the expected column count is
`24`, then run:

```powershell
uv run pytest tests/test_output_schema_contract.py tests/test_csv_writers.py tests/test_csv_to_excel.py::test_run_emits_score_breakdown_sheet_when_enabled -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

```powershell
git add xic_extractor/output xic_extractor/extractor.py xic_extractor/extraction/target_extraction.py tests
git commit -m "feat: expose weighted evidence score breakdown"
```

---

## Task 6.5 — In-Memory Excel Pipeline Carries Evidence Details

**Files:**

- Modify: `tests/test_excel_pipeline.py`
- Modify: `xic_extractor/output/excel_pipeline.py`

- [ ] **Step 1: Add in-memory pipeline assertion**

Extend `tests/test_excel_pipeline.py::test_write_excel_from_run_output_adds_score_breakdown_when_enabled` so `_run_output()` returns an `ExtractionResult` with:

```python
score_breakdown=(
    ("Base Score", "50"),
    ("Positive Points", "10"),
    ("Negative Points", "5"),
    ("Raw Score", "55"),
    ("Caps", ""),
    ("Final Confidence", "LOW"),
    ("Support", "local_sn_strong"),
    ("Concerns", "shape_borderline"),
),
```

Then assert:

```python
assert row["Base Score"] == 50
assert row["Raw Score"] == 55
assert row["Support"] == "local_sn_strong"
assert row["Concerns"] == "shape_borderline"
```

- [ ] **Step 2: Run red test**

Run:

```powershell
uv run pytest tests/test_excel_pipeline.py::test_write_excel_from_run_output_adds_score_breakdown_when_enabled -v
```

Expected: FAIL until `_run_output_to_score_breakdown_rows()` includes
`result.score_breakdown`.

- [ ] **Step 3: Implement in-memory propagation**

In `xic_extractor/output/excel_pipeline.py`, add:

```python
weighted_fields = dict(result.score_breakdown)
```

and emit the same weighted columns as `csv_writers._score_breakdown_rows()`.

- [ ] **Step 4: Run green test**

Run:

```powershell
uv run pytest tests/test_excel_pipeline.py::test_write_excel_from_run_output_adds_score_breakdown_when_enabled -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/output/excel_pipeline.py tests/test_excel_pipeline.py
git commit -m "feat: carry weighted evidence through excel pipeline"
```

---

## Task 7 — Detection Contract Regression Tests

**Files:**

- Modify: `tests/test_csv_to_excel.py`
- Modify: `tests/test_review_metrics.py`
- Modify: `tests/test_review_report.py`
- Modify: `xic_extractor/output/sheet_summary.py`
- Modify: `xic_extractor/output/review_metrics.py`

- [ ] **Step 1: Add detection contract tests**

Ensure the following tests exist or add them:

```python
def test_summary_detection_excludes_very_low_rows() -> None:
    rows = [
        _long_row("S1", "Analyte", "9.0", "100", "OK", confidence="VERY_LOW"),
        _long_row("S2", "Analyte", "9.1", "110", "OK", confidence="LOW"),
    ]
    wb = Workbook()
    ws = wb.active

    _build_summary_sheet(ws, rows, count_no_ms2_as_detected=False, review_rows=[])
    data = _summary_rows(ws)

    assert data["Analyte"]["Detected"] == 1
    assert data["Analyte"]["Detection %"] == "50%"
```

```python
def test_review_metrics_do_not_count_nl_fail_or_very_low_as_detected() -> None:
    rows = [
        {"SampleName": "S1", "Target": "A", "RT": "1.0", "Area": "100", "NL": "NL_FAIL", "Confidence": "LOW"},
        {"SampleName": "S2", "Target": "A", "RT": "1.1", "Area": "110", "NL": "OK", "Confidence": "VERY_LOW"},
        {"SampleName": "S3", "Target": "A", "RT": "1.2", "Area": "120", "NL": "OK", "Confidence": "LOW"},
        {"SampleName": "S4", "Target": "A", "RT": "1.3", "Area": "0", "NL": "OK", "Confidence": "LOW"},
    ]

    metrics = build_review_metrics(
        rows,
        diagnostics=[],
        review_rows=[],
        count_no_ms2_as_detected=False,
    )

    assert metrics.targets["A"].detected == 1
    assert metrics.targets["A"].detected_percent == "25%"
    assert metrics.heatmap[("A", "S1")] == "not-detected"
    assert metrics.heatmap[("A", "S2")] == "not-detected"
    assert metrics.heatmap[("A", "S3")] == "clean-detected"
    assert metrics.heatmap[("A", "S4")] == "not-detected"
```

Add a direct decision-table test for the shared predicate:

```python
@pytest.mark.parametrize(
    ("row", "count_no_ms2_as_detected", "expected"),
    [
        ({"RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "HIGH"}, False, True),
        ({"RT": "1.0", "Area": "100", "NL": "WARN_LOW_PRODUCT", "Confidence": "LOW"}, False, True),
        ({"RT": "1.0", "Area": "100", "NL": "OK", "Confidence": "VERY_LOW"}, False, False),
        ({"RT": "1.0", "Area": "100", "NL": "NL_FAIL", "Confidence": "LOW"}, False, False),
        ({"RT": "1.0", "Area": "100", "NL": "NO_MS2", "Confidence": "LOW"}, False, False),
        ({"RT": "1.0", "Area": "100", "NL": "NO_MS2", "Confidence": "LOW"}, True, True),
        ({"RT": "1.0", "Area": "0", "NL": "OK", "Confidence": "LOW"}, False, False),
        ({"RT": "ND", "Area": "100", "NL": "OK", "Confidence": "HIGH"}, False, False),
    ],
)
def test_accepted_detection_decision_table(
    row: dict[str, str],
    count_no_ms2_as_detected: bool,
    expected: bool,
) -> None:
    assert is_accepted_row_detection(row, count_no_ms2_as_detected) is expected
```

Also add an HTML contract test in `tests/test_review_report.py` proving that
`VERY_LOW` rows are rendered as review/not-detected states rather than
flagged-detected states. This prevents the same "RT exists, therefore detected"
misread from re-entering the report.

- [ ] **Step 2: Run tests**

Run:

```powershell
uv run pytest tests/test_csv_to_excel.py::test_summary_detection_excludes_very_low_rows tests/test_review_metrics.py::test_review_metrics_do_not_count_nl_fail_or_very_low_as_detected tests/test_review_metrics.py::test_accepted_detection_decision_table tests/test_review_report.py::test_review_report_marks_very_low_rows_as_not_detected -v
```

Expected: PASS if this branch already contains the current detection fix; FAIL
only if implementation moved or regressed the contract.

- [ ] **Step 3: Implement detection contract when the tests expose a regression**

If the tests fail, promote shared output predicates named
`is_accepted_row_detection()` and `is_accepted_result_detection()`. Make
`_is_long_detected()`, review metrics, HTML heatmap, and Score Breakdown use
the shared predicates. The row predicate must match this exact contract:

```python
def is_accepted_row_detection(row: dict[str, str], count_no_ms2_as_detected: bool) -> bool:
    if _safe_float(row.get("RT", "")) is None:
        return False
    area = _safe_float(row.get("Area", ""))
    if area is None or area <= 0:
        return False
    if row.get("Confidence", "") == "VERY_LOW":
        return False
    nl = row.get("NL", "")
    if nl == "NO_MS2":
        return count_no_ms2_as_detected
    if nl == "NL_FAIL":
        return False
    return nl == "" or nl == "OK" or nl.startswith("WARN_")
```

The result predicate must be equivalent, using `result.peak_result.peak`,
`result.reported_rt`, `result.nl_token`, and `result.confidence` instead of row
strings.

- [ ] **Step 4: Commit**

If files changed:

```powershell
git add xic_extractor/output tests
git commit -m "test: lock accepted-peak detection contract"
```

If no files changed:

```powershell
git status --short
```

Expected: no files changed for this task.

---

## Task 8 — Narrow And Full Verification

**Files:**

- No code files unless tests expose defects.
- Validation outputs under `output/validation_harness/` are not committed.

- [ ] **Step 1: Run scoring/output tests**

Run:

```powershell
uv run pytest tests/test_peak_scoring_evidence.py tests/test_peak_scoring.py tests/test_signal_processing_selection.py tests/test_extractor.py tests/test_csv_to_excel.py tests/test_review_metrics.py tests/test_review_report.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full unit suite**

Run:

```powershell
uv run pytest --tb=short -q
```

Expected: PASS.

- [ ] **Step 3: Run ruff**

Run:

```powershell
uv run ruff check xic_extractor tests
```

Expected: `All checks passed!`

- [ ] **Step 4: Run 8-raw local-minimum validation**

Run:

```powershell
uv run python scripts/validation_harness.py --suite tissue-8raw --run-id weighted_evidence_local_8raw --resolver-mode local_minimum --parallel-mode process --parallel-workers 4 --setting emit_review_report=true --setting "injection_order_source=C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx"
```

Expected: harness reports `tissue-8raw: passed`.

- [ ] **Step 5: Inspect 8-raw Summary**

Open the produced `xic_results_process_w4.xlsx` and verify:

```text
Area=0 detected rows: 0
8-oxo-Guo detection pattern remains expected
8-oxodG mismatched RT rows are not counted as detected
d3-N6-medA ISTD remains detected in all 8 samples unless confidence cap is analytically justified
```

- [ ] **Step 6: Run 85-raw local-minimum validation**

Run:

```powershell
uv run python scripts/validation_harness.py --suite tissue-85raw --confirm-full-run --run-id weighted_evidence_local_85raw --resolver-mode local_minimum --parallel-mode process --parallel-workers 4 --setting emit_review_report=true --setting "injection_order_source=C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx"
```

Expected: harness reports `tissue-85raw: passed`.

- [ ] **Step 7: Inspect 85-raw Summary**

Use the workbook Summary, not raw RT/Area counts. Expected checks:

```text
8-oxo-Guo: 2/85 unless new evidence is clearly explained
8-oxodG: 0/85 if only RT/ISTD-mismatched VERY_LOW rows remain
Area=0 detected rows: 0
d3-N6-medA accepted ISTD CV does not materially regress from the post-fix baseline
d3-dG-C8-MeIQx remains 85/85 but CV remains flagged for future investigation if high
```

Then inspect the optional Score Breakdown sheet for those same rows:

```text
8-oxo-Guo non-accepted rows: Detection Counted = FALSE
8-oxodG RT/ISTD-mismatched rows: Final Confidence = VERY_LOW, Detection Counted = FALSE
Area=0 rows: Detection Counted = FALSE
Reason first segment always starts with decision:
Rows excluded from detection never appear as clean/flagged detected in HTML heatmap
```

- [ ] **Step 8: Commit final verification docs only if changed**

If this task creates or updates a short validation note:

```powershell
git add docs/superpowers/plans/2026-05-08-weighted-evidence-confidence-scoring.md
git commit -m "docs: record weighted evidence validation results"
```

If no files changed:

```powershell
git status --short
```

Expected: clean worktree.

---

## Self-Review Checklist

- [ ] Spec requirement "positive evidence can add score" is covered by Tasks 1-2.
- [ ] Spec requirement "critical issues become caps" is covered by Tasks 1 and 3.
- [ ] Spec requirement "selection uses score-point penalties" is covered by Task 4.
- [ ] Spec requirement "Reason shows support/concerns/caps" is covered by Task 5.
- [ ] Spec requirement "Score Breakdown optional evidence fields" is covered by Task 6.
- [ ] Spec requirement "detection excludes VERY_LOW/NL_FAIL" is covered by Task 7.
- [ ] Spec requirement "8-raw then 85-raw validation" is covered by Task 8.
