import numpy as np

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction import peak_candidate_table
from xic_extractor.extraction.peak_candidate_audit import append_peak_audit_rows
from xic_extractor.peak_detection.traces import Trace, targeted_trace_group
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakDetectionResult,
    PeakResult,
)


def test_peak_audit_appender_reuses_one_cwt_audit_result(
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
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        emit_peak_candidates=True,
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
    peak_result = PeakDetectionResult(
        status="OK",
        peak=_candidate(8.5).peak,
        n_points=7,
        max_smoothed=100.0,
        n_prominent_peaks=1,
        candidates=(_candidate(8.5),),
    )
    calls = 0

    def _fake_cwt(peak_result, *_args, **_kwargs):
        nonlocal calls
        calls += 1
        return peak_result

    monkeypatch.setattr(
        "xic_extractor.extraction.peak_candidate_audit.add_cwt_proposals_for_audit",
        _fake_cwt,
    )
    build_calls = 0
    real_build_peak_hypotheses = peak_candidate_table.build_peak_hypotheses

    def _count_build_peak_hypotheses(**kwargs):
        nonlocal build_calls
        build_calls += 1
        return real_build_peak_hypotheses(**kwargs)

    monkeypatch.setattr(
        peak_candidate_table,
        "build_peak_hypotheses",
        _count_build_peak_hypotheses,
    )
    candidate_rows: list[dict[str, str]] = []
    boundary_rows: list[dict[str, str]] = []

    append_peak_audit_rows(
        peak_candidate_rows=candidate_rows,
        peak_candidate_boundary_rows=boundary_rows,
        config=config,
        sample_name="SampleA",
        target=target,
        peak_result=peak_result,
        candidate_ms2_builder=lambda _candidate: None,
        rt=np.asarray([8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8]),
        intensity=np.asarray([10.0, 20.0, 70.0, 100.0, 70.0, 20.0, 10.0]),
    )

    assert calls == 1
    assert build_calls == 1
    assert candidate_rows
    assert boundary_rows
    assert candidate_rows[0]["area_baseline_corrected"] != ""
    assert candidate_rows[0]["area_uncertainty"] != ""
    assert candidate_rows[0]["area_uncertainty_formula_version"] == (
        "baseline_residual_mad_v1"
    )
    assert candidate_rows[0]["baseline_residual_mad"] != ""
    assert candidate_rows[0]["area_uncertainty_noise_source"] != ""


def test_peak_audit_appender_uses_shared_trace_group_for_audit_rows(
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
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        emit_peak_candidates=True,
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
    candidate = _candidate(8.5)
    peak_result = PeakDetectionResult(
        status="OK",
        peak=candidate.peak,
        n_points=7,
        max_smoothed=100.0,
        n_prominent_peaks=1,
        candidates=(candidate,),
    )
    trace = Trace.from_arrays(
        sample_name="SampleA",
        mz=258.1085,
        rt=[8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8],
        intensity=[10.0, 20.0, 70.0, 100.0, 70.0, 20.0, 10.0],
        rt_min=8.2,
        rt_max=8.8,
        ppm_tol=20.0,
    )

    monkeypatch.setattr(
        "xic_extractor.extraction.peak_candidate_audit.add_cwt_proposals_for_audit",
        lambda peak_result, *_args, **_kwargs: peak_result,
    )
    candidate_rows: list[dict[str, str]] = []
    boundary_rows: list[dict[str, str]] = []

    append_peak_audit_rows(
        peak_candidate_rows=candidate_rows,
        peak_candidate_boundary_rows=boundary_rows,
        config=config,
        sample_name="SampleA",
        target=target,
        peak_result=peak_result,
        candidate_ms2_builder=lambda _candidate: None,
        rt=np.asarray([8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8]),
        intensity=np.zeros(7),
        trace_group=targeted_trace_group(
            trace,
            target_label="Analyte",
            resolver_mode="legacy_savgol",
        ),
    )

    assert candidate_rows[0]["area_baseline_corrected"] != "0.00000"
    assert any(row["area_raw_counts_seconds"] != "0.00" for row in boundary_rows)


def _candidate(rt: float) -> PeakCandidate:
    peak = PeakResult(
        rt=rt,
        intensity=100.0,
        intensity_smoothed=95.0,
        area=1200.0,
        peak_start=rt - 0.2,
        peak_end=rt + 0.2,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=95.0,
        selection_apex_index=3,
        raw_apex_rt=rt,
        raw_apex_intensity=100.0,
        raw_apex_index=3,
        prominence=90.0,
        proposal_sources=("legacy_savgol",),
        source_apex_rank=1,
    )
