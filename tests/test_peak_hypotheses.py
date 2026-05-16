from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.hypotheses import (
    build_peak_hypotheses,
    hypothesis_audit_id,
)
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
    PeakResult,
)


def test_hypothesis_id_is_deterministic() -> None:
    candidate = _candidate(
        8.1234567,
        left=8.001234,
        right=8.654321,
        proposal_sources=("legacy_savgol",),
    )

    first = hypothesis_audit_id(
        sample_name="SampleA",
        target_label="Analyte",
        resolver_mode="legacy_savgol",
        candidate=candidate,
    )
    second = hypothesis_audit_id(
        sample_name="SampleA",
        target_label="Analyte",
        resolver_mode="legacy_savgol",
        candidate=candidate,
    )

    assert first == second
    assert first == (
        "SampleA|Analyte|legacy_savgol|legacy_savgol|"
        "8.12346|8.00123|8.65432"
    )


def test_build_peak_hypotheses_marks_selected_and_rejected_candidates() -> None:
    selected = _candidate(8.5, area=5000.0, proposal_sources=("legacy_savgol",))
    rejected = _candidate(8.9, area=900.0, proposal_sources=("local_minimum",))
    result = PeakDetectionResult(
        status="OK",
        peak=selected.peak,
        n_points=20,
        max_smoothed=3000.0,
        n_prominent_peaks=2,
        candidates=(selected, rejected),
        candidate_scores=(
            _score(selected, raw_score=92, confidence="HIGH"),
            _score(rejected, raw_score=58, confidence="LOW"),
        ),
        selection_reference_rt=8.45,
    )

    hypotheses = build_peak_hypotheses(
        sample_name="SampleA",
        target_label="Analyte",
        role="Analyte",
        istd_pair="ISTD",
        resolver_mode="arbitrated",
        peak_result=result,
        candidate_ms2_evidence={
            selected: _ms2_evidence(nl_match=True),
            rejected: _ms2_evidence(nl_match=False),
        },
    )

    assert [hypothesis.audit.selected for hypothesis in hypotheses] == [True, False]
    assert hypotheses[0].audit.selection_rank == 1
    assert hypotheses[0].audit.proposal_sources == ("legacy_savgol",)
    assert hypotheses[0].evidence.ms2_present is True
    assert hypotheses[0].evidence.nl_match is True
    assert hypotheses[0].evidence.raw_score == 92
    assert hypotheses[0].evidence.support_labels == ("strict_nl_ok", "shape_clean")
    assert hypotheses[0].integration.boundary_sources == ("candidate_interval",)
    assert hypotheses[1].audit.proposal_sources == ("local_minimum",)
    assert hypotheses[1].audit.rejection_reason == "lower_confidence"
    assert hypotheses[1].evidence.nl_match is False
    assert hypotheses[1].evidence.concern_labels == ("nl_fail",)


def test_hypothesis_selection_reference_comes_from_detection_result() -> None:
    selected = _candidate(8.5)
    result = PeakDetectionResult(
        status="OK",
        peak=selected.peak,
        n_points=20,
        max_smoothed=3000.0,
        n_prominent_peaks=1,
        candidates=(selected,),
        selection_reference_rt=None,
    )

    hypothesis = build_peak_hypotheses(
        sample_name="SampleA",
        target_label="Analyte",
        role="Analyte",
        istd_pair="",
        resolver_mode="legacy_savgol",
        peak_result=result,
    )[0]

    assert hypothesis.audit.selection_reference_rt_min is None


def test_build_peak_hypotheses_returns_empty_without_candidate_intervals() -> None:
    result = PeakDetectionResult(
        status="PEAK_NOT_FOUND",
        peak=None,
        n_points=20,
        max_smoothed=3000.0,
        n_prominent_peaks=0,
        candidates=(),
    )

    assert (
        build_peak_hypotheses(
            sample_name="SampleA",
            target_label="Analyte",
            role="Analyte",
            istd_pair="",
            resolver_mode="legacy_savgol",
            peak_result=result,
        )
        == ()
    )


def _candidate(
    rt: float,
    *,
    left: float | None = None,
    right: float | None = None,
    area: float = 1000.0,
    proposal_sources: tuple[str, ...] = ("legacy_savgol",),
) -> PeakCandidate:
    peak_start = rt - 0.2 if left is None else left
    peak_end = rt + 0.2 if right is None else right
    peak = PeakResult(
        rt=rt,
        intensity=1200.0,
        intensity_smoothed=1100.0,
        area=area,
        peak_start=peak_start,
        peak_end=peak_end,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=1100.0,
        selection_apex_index=7,
        raw_apex_rt=rt,
        raw_apex_intensity=1200.0,
        raw_apex_index=7,
        prominence=700.0,
        proposal_sources=proposal_sources,
        source_apex_rank=1,
    )


def _score(
    candidate: PeakCandidate,
    *,
    raw_score: int,
    confidence: str,
) -> PeakCandidateScore:
    return PeakCandidateScore(
        candidate=candidate,
        confidence=confidence,
        reason=f"decision: {confidence.lower()}",
        raw_score=raw_score,
        support_labels=("strict_nl_ok", "shape_clean"),
        concern_labels=() if confidence == "HIGH" else ("nl_fail",),
        cap_labels=() if confidence == "HIGH" else ("nl_fail_cap",),
    )


def _ms2_evidence(*, nl_match: bool) -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=True,
        nl_match=nl_match,
        nl_status="OK" if nl_match else "NL_FAIL",
        trigger_scan_count=1,
        strict_nl_scan_count=1 if nl_match else 0,
        best_loss_ppm=1.0 if nl_match else None,
        best_scan_rt=8.5,
        best_product_base_ratio=0.3,
        alignment_source="region",
    )
