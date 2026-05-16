import csv
from pathlib import Path

from xic_extractor.extraction.peak_candidate_table import (
    build_peak_candidate_rows,
    candidate_audit_id,
)
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.output.peak_candidates import write_peak_candidates_tsv
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakCandidateScore,
    PeakDetectionResult,
    PeakResult,
)


def test_candidate_id_is_deterministic() -> None:
    candidate = _candidate(
        8.1234567,
        left=8.001234,
        right=8.654321,
        proposal_sources=("legacy_savgol",),
    )

    first = candidate_audit_id(
        sample_name="SampleA",
        target_label="Analyte",
        resolver_mode="legacy_savgol",
        candidate=candidate,
    )
    second = candidate_audit_id(
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


def test_build_rows_marks_selected_and_rejected_candidates() -> None:
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
    )

    rows = build_peak_candidate_rows(
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
        selection_reference_rt=8.45,
    )

    assert [row["selected"] for row in rows] == ["TRUE", "FALSE"]
    assert rows[0]["selection_rank"] == "1"
    assert rows[0]["proposal_sources"] == "legacy_savgol"
    assert rows[0]["ms2_present"] == "TRUE"
    assert rows[0]["nl_match"] == "TRUE"
    assert rows[0]["raw_score"] == "92"
    assert rows[0]["support_labels"] == "strict_nl_ok;shape_clean"
    assert rows[1]["proposal_sources"] == "local_minimum"
    assert rows[1]["rejection_reason"] == "lower_confidence"
    assert rows[1]["nl_match"] == "FALSE"
    assert rows[1]["concern_labels"] == "nl_fail"


def test_write_peak_candidates_tsv_serializes_rows_safely(tmp_path: Path) -> None:
    path = tmp_path / "peak_candidates.tsv"
    row = build_peak_candidate_rows(
        sample_name="SampleA",
        target_label="Analyte",
        role="Analyte",
        istd_pair="",
        resolver_mode="legacy_savgol",
        peak_result=PeakDetectionResult(
            status="OK",
            peak=_candidate(8.5).peak,
            n_points=20,
            max_smoothed=3000.0,
            n_prominent_peaks=1,
            candidates=(_candidate(8.5),),
        ),
        selection_reference_rt=None,
    )[0]
    row["reason"] = "line1\nline2\twith tab"

    write_peak_candidates_tsv(path, [row])

    text = path.read_text(encoding="utf-8-sig")
    assert "line1 line2 with tab" in text
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["reason"] == "line1 line2 with tab"


def test_disabled_writer_is_noop(tmp_path: Path) -> None:
    path = tmp_path / "peak_candidates.tsv"

    write_peak_candidates_tsv(path, [{"sample_name": "SampleA"}], enabled=False)

    assert not path.exists()


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
