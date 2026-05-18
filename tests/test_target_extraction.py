from xic_extractor.extraction.ms2_selection import selected_candidate_ms2_evidence
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.models import PeakCandidate, PeakResult


def test_safe_merge_selected_candidate_builds_missing_ms2_evidence() -> None:
    candidate = _candidate(merge_note="region_first_safe_merge")
    evidence = _evidence("NO_MS2")
    calls: list[PeakCandidate] = []

    def _builder(value: PeakCandidate) -> CandidateMS2Evidence:
        calls.append(value)
        return evidence

    selected = selected_candidate_ms2_evidence(candidate, {}, _builder)

    assert selected is evidence
    assert calls == [candidate]


def test_non_safe_merge_selected_candidate_uses_existing_cache_only() -> None:
    candidate = _candidate()
    calls: list[PeakCandidate] = []

    def _builder(value: PeakCandidate) -> CandidateMS2Evidence:
        calls.append(value)
        return _evidence("NL_FAIL")

    selected = selected_candidate_ms2_evidence(candidate, {}, _builder)

    assert selected is None
    assert calls == []


def _candidate(*, merge_note: str = "") -> PeakCandidate:
    return PeakCandidate(
        peak=PeakResult(
            rt=10.0,
            intensity=100.0,
            intensity_smoothed=100.0,
            area=1000.0,
            peak_start=9.9,
            peak_end=10.1,
        ),
        selection_apex_rt=10.0,
        selection_apex_intensity=100.0,
        selection_apex_index=1,
        raw_apex_rt=10.0,
        raw_apex_intensity=100.0,
        raw_apex_index=1,
        prominence=50.0,
        merge_note=merge_note,
    )


def _evidence(nl_status: str) -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=nl_status != "NO_MS2",
        nl_match=nl_status in {"OK", "WARN"},
        nl_status=nl_status,
        trigger_scan_count=1 if nl_status != "NO_MS2" else 0,
        strict_nl_scan_count=1 if nl_status in {"OK", "WARN"} else 0,
        best_loss_ppm=None,
        best_scan_rt=None,
        best_product_base_ratio=None,
        alignment_source="none",
    )
