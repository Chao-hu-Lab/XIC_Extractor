import numpy as np

import xic_extractor.extraction.target_extraction as target_extraction
from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.istd_recovery import IstdAnchorRecoveryDecision
from xic_extractor.extraction.ms2_selection import selected_candidate_ms2_evidence
from xic_extractor.extractor import ExtractionResult
from xic_extractor.neutral_loss import CandidateMS2Evidence, NLResult
from xic_extractor.peak_detection.hypotheses import PeakHypothesis
from xic_extractor.peak_detection.models import (
    PeakCandidate,
    PeakDetectionResult,
    PeakResult,
)


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
                np.asarray([10.0, 100.0, 40.0, 20.0, 10.0]),
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

    results: dict[str, ExtractionResult] = {}
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
