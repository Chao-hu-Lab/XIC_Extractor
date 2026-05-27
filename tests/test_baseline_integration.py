import numpy as np
import pytest

from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    compute_asls_residual_mad,
    integrate_asls_baseline,
    integrate_linear_edge_baseline,
    integrate_with_baseline,
)
from xic_extractor.peak_detection.integration_audit import (
    build_cell_integration_audit_summary,
)


def test_linear_edge_baseline_subtracts_sloped_local_baseline() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 25.0, 50.0, 35.0, 20.0])

    result = integrate_linear_edge_baseline(intensity, rt, 0, 5)

    assert result.baseline_type == "linear_edge"
    assert result.area_baseline_corrected == pytest.approx(390.0)
    assert result.area_uncertainty is not None
    assert result.baseline_score is not None
    assert 0.0 <= result.baseline_score <= 1.0


def test_area_uncertainty_uses_baseline_residual_noise_not_peak_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.linspace(0.0, 0.9, 10)
    low_peak = np.asarray([10, 10, 10, 12, 18, 12, 10, 10, 10, 10], dtype=float)
    high_peak = np.asarray([10, 10, 10, 20, 90, 20, 10, 10, 10, 10], dtype=float)
    shared_baseline = np.full_like(rt, 10.0)

    monkeypatch.setattr(
        "xic_extractor.peak_detection.baseline.asls_baseline",
        lambda values, **_kwargs: shared_baseline,
    )

    low = integrate_linear_edge_baseline(low_peak, rt, 3, 6)
    high = integrate_linear_edge_baseline(high_peak, rt, 3, 6)

    assert low.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert high.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert low.area_uncertainty == pytest.approx(high.area_uncertainty)
    assert high.area_baseline_corrected > low.area_baseline_corrected


def test_area_uncertainty_returns_none_for_non_positive_scan_period() -> None:
    rt = np.asarray([0.1, 0.1, 0.1, 0.1, 0.1])
    intensity = np.asarray([10.0, 20.0, 25.0, 12.0, 11.0])

    result = integrate_linear_edge_baseline(intensity, rt, 0, 5)

    assert result.area_uncertainty is None
    assert result.baseline_residual_mad is not None
    assert result.area_uncertainty_noise_source == "asls_residual"


def test_area_uncertainty_can_fallback_to_pre_peak_mad(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.linspace(0.0, 0.9, 10)
    intensity = np.asarray([9, 11, 10, 9, 20, 80, 25, 10, 11, 9], dtype=float)

    def _raise_asls(_values: np.ndarray, **_kwargs: object) -> np.ndarray:
        raise ValueError("fit failed")

    monkeypatch.setattr(
        "xic_extractor.peak_detection.baseline.asls_baseline",
        _raise_asls,
    )

    result = integrate_linear_edge_baseline(intensity, rt, 4, 7)

    assert result.area_uncertainty is not None
    assert result.baseline_residual_mad is not None
    assert result.area_uncertainty_noise_source == "pre_peak_mad"


def test_linear_edge_preserves_caller_residual_mad_source() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3])
    intensity = np.asarray([10.0, 30.0, 25.0, 12.0])

    result = integrate_linear_edge_baseline(
        intensity,
        rt,
        0,
        4,
        baseline_residual_mad=2.5,
        baseline_residual_mad_source="manual_residual",
    )

    assert result.baseline_residual_mad == pytest.approx(2.5)
    assert result.area_uncertainty_noise_source == "manual_residual"


def test_linear_edge_baseline_rejects_mismatched_arrays() -> None:
    with pytest.raises(ValueError, match="same length"):
        integrate_linear_edge_baseline(
            np.asarray([1.0, 2.0]),
            np.asarray([0.0]),
            0,
            2,
        )


def test_asls_baseline_integrates_shadow_area_without_exceeding_raw() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])

    result = integrate_asls_baseline(intensity, rt, 1, 5)

    assert result.baseline_type == "asls"
    assert result.area_baseline_corrected > 0.0
    raw_area = 60.0 * float(np.trapezoid(intensity[1:5], rt[1:5]))
    assert result.area_baseline_corrected <= raw_area
    assert result.baseline_score is not None
    assert 0.0 <= result.baseline_score <= 1.0
    assert result.area_uncertainty is not None
    assert result.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert result.baseline_residual_mad is not None
    assert result.area_uncertainty_noise_source == "asls_residual"


def test_asls_baseline_keeps_provenance_when_uncertainty_unavailable() -> None:
    rt = np.asarray([0.1, 0.1, 0.1, 0.1, 0.1])
    intensity = np.asarray([8.0, 12.0, 70.0, 20.0, 12.0])
    baseline = np.full_like(intensity, 8.0)

    result = integrate_asls_baseline(intensity, rt, 0, 5, baseline_values=baseline)

    assert result.area_uncertainty is None
    assert result.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert result.baseline_residual_mad is not None
    assert result.area_uncertainty_noise_source == "asls_residual"


def test_compute_asls_residual_mad_rejects_explicit_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="baseline_values"):
        compute_asls_residual_mad(
            np.asarray([1.0, 2.0, 3.0, 4.0, 5.0]),
            baseline_values=np.asarray([1.0, 2.0]),
        )


def test_integrate_with_baseline_dispatches_supported_methods() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3])
    intensity = np.asarray([10.0, 30.0, 25.0, 12.0])

    linear = integrate_with_baseline(
        intensity,
        rt,
        0,
        4,
        baseline_method="linear_edge",
    )
    asls = integrate_with_baseline(
        intensity,
        rt,
        0,
        4,
        baseline_method="asls",
    )

    assert linear.baseline_type == "linear_edge"
    assert asls.baseline_type == "asls"


def test_integrate_with_baseline_rejects_unknown_method() -> None:
    rt = np.asarray([0.0, 0.1, 0.2])
    intensity = np.asarray([10.0, 20.0, 12.0])

    with pytest.raises(ValueError, match="baseline_method"):
        integrate_with_baseline(
            intensity,
            rt,
            0,
            3,
            baseline_method="airpls",
        )


def test_bounded_trace_interval_matches_integration_interval_contract() -> None:
    assert bounded_trace_interval(2, 3, 3) == (1, 3)
    assert bounded_trace_interval(-5, 1, 4) == (0, 2)

    with pytest.raises(ValueError, match="at least 2"):
        bounded_trace_interval(0, 1, 1)


def test_cell_integration_audit_reports_baseline_corrected_area() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 25.0, 50.0, 35.0, 20.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.4,
        raw_area=1200.0,
    )

    assert summary.raw_area == pytest.approx(1200.0)
    assert summary.area_baseline_corrected is not None
    assert summary.baseline_type == "asls"
    assert summary.area_baseline_corrected_linear_edge == pytest.approx(390.0)
    assert summary.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert summary.baseline_residual_mad is not None
    assert summary.area_uncertainty_noise_source in {"asls_residual", "pre_peak_mad"}
    assert summary.baseline_fraction == pytest.approx(
        summary.area_baseline_corrected / 1200.0
    )
    assert summary.integration_scan_count == 5


def test_cell_integration_audit_defaults_to_asls_with_linear_rollback() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.1,
        peak_end_rt=0.4,
        raw_area=60.0 * float(np.trapezoid(intensity[1:5], rt[1:5])),
    )

    assert summary.baseline_type == "asls"
    assert summary.area_baseline_corrected is not None
    assert summary.baseline_score is not None
    assert summary.area_baseline_corrected_linear_edge is not None
    assert summary.baseline_score_linear_edge is not None
    assert summary.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert summary.area_uncertainty_noise_source == "asls_residual"


def test_cell_integration_audit_can_rollback_to_linear_edge_production() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 25.0, 50.0, 35.0, 20.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.4,
        raw_area=1200.0,
        baseline_integration_method="linear_edge",
    )

    assert summary.baseline_type == "linear_edge"
    assert summary.area_baseline_corrected == pytest.approx(390.0)
    assert summary.area_baseline_corrected_linear_edge is None
    assert summary.baseline_score_linear_edge is None


def test_cell_integration_audit_falls_back_to_linear_edge_when_asls_unavailable() -> (
    None
):
    rt = np.asarray([0.0, 0.1, 0.2])
    intensity = np.asarray([10.0, 80.0, 20.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.2,
        raw_area=60.0 * float(np.trapezoid(intensity, rt)),
        baseline_integration_method="asls",
    )

    assert summary.is_empty is False
    assert summary.baseline_type == "linear_edge_fallback"
    assert summary.area_baseline_corrected is not None
    assert summary.area_baseline_corrected_linear_edge is None


def test_cell_integration_audit_can_emit_legacy_asls_shadow_values() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.1,
        peak_end_rt=0.4,
        raw_area=60.0 * float(np.trapezoid(intensity[1:5], rt[1:5])),
        baseline_integration_method="linear_edge",
        baseline_audit_method="asls",
    )

    assert summary.baseline_type == "linear_edge"
    assert summary.area_baseline_corrected is not None
    assert summary.area_baseline_corrected_asls is not None
    assert summary.baseline_score_asls is not None
    assert 0.0 <= summary.baseline_score_asls <= 1.0
    assert summary.area_baseline_corrected_linear_edge is None


def test_cell_integration_audit_reuses_asls_fit_for_uncertainty_and_shadow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.linspace(0.0, 0.5, 6)
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])
    calls = 0

    def _fake_asls(values: np.ndarray, **_kwargs: object) -> np.ndarray:
        nonlocal calls
        calls += 1
        return np.full_like(values, 8.0)

    monkeypatch.setattr(
        "xic_extractor.peak_detection.baseline.asls_baseline",
        _fake_asls,
    )

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.1,
        peak_end_rt=0.4,
        raw_area=60.0 * float(np.trapezoid(intensity[1:5], rt[1:5])),
    )

    assert calls == 1
    assert summary.baseline_type == "asls"
    assert summary.area_baseline_corrected is not None
    assert summary.baseline_residual_mad is not None


def test_cell_integration_audit_default_has_no_legacy_asls_shadow_values() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3])
    intensity = np.asarray([10.0, 30.0, 25.0, 12.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.3,
        raw_area=100.0,
    )

    assert summary.area_baseline_corrected_asls is None
    assert summary.baseline_score_asls is None


def test_cell_integration_audit_flags_high_local_noise_uncertainty() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 80.0, 20.0, 95.0, 25.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.4,
        raw_area=300.0,
    )

    assert summary.area_uncertainty is not None
    assert summary.uncertainty_fraction is not None
    assert summary.uncertainty_fraction > 0.0
    assert summary.area_uncertainty_formula_version == "baseline_residual_mad_v1"


def test_cell_integration_audit_returns_empty_for_invalid_trace() -> None:
    summary = build_cell_integration_audit_summary(
        np.asarray([0.0, 0.1]),
        np.asarray([10.0]),
        peak_start_rt=0.0,
        peak_end_rt=0.1,
        raw_area=100.0,
    )

    assert summary.is_empty
