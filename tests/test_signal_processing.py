from pathlib import Path

import numpy as np
import pytest
from scipy.signal import savgol_filter

from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


def _config(
    *,
    smooth_window: int = 15,
    smooth_polyorder: int = 3,
    peak_rel_height: float = 0.95,
    peak_min_prominence_ratio: float = 0.10,
) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("raw"),
        dll_dir=Path("dll"),
        output_csv=Path("output/xic_results.csv"),
        diagnostics_csv=Path("output/xic_diagnostics.csv"),
        smooth_window=smooth_window,
        smooth_polyorder=smooth_polyorder,
        peak_rel_height=peak_rel_height,
        peak_min_prominence_ratio=peak_min_prominence_ratio,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        count_no_ms2_as_detected=False,
    )


def _gaussian(
    rt: np.ndarray, *, center: float, sigma: float, height: float
) -> np.ndarray:
    return height * np.exp(-0.5 * ((rt - center) / sigma) ** 2)


def test_clean_gaussian_peak_returns_raw_apex_and_area() -> None:
    rt = np.linspace(8.0, 10.0, 401)
    intensity = _gaussian(rt, center=9.0, sigma=0.08, height=1000.0)
    expected_area = 1000.0 * 0.08 * np.sqrt(2 * np.pi)

    result = find_peak_and_area(rt, intensity, _config())

    assert result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(9.0, abs=0.01)
    assert result.peak.intensity == pytest.approx(1000.0, rel=0.02)
    assert result.peak.area == pytest.approx(expected_area, rel=0.02)
    assert result.n_points == len(rt)
    assert result.n_prominent_peaks == 1


def test_two_peak_signal_chooses_highest_smoothed_peak() -> None:
    rt = np.linspace(8.0, 10.0, 401)
    intensity = _gaussian(rt, center=8.7, sigma=0.05, height=500.0)
    intensity += _gaussian(rt, center=9.4, sigma=0.06, height=1200.0)

    result = find_peak_and_area(rt, intensity, _config())

    assert result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(9.4, abs=0.01)
    assert result.n_prominent_peaks == 2


def test_positive_flat_noise_returns_peak_not_found() -> None:
    rt = np.linspace(0.0, 1.0, 60)
    intensity = np.full_like(rt, 12.0)

    result = find_peak_and_area(rt, intensity, _config())

    assert result.status == "PEAK_NOT_FOUND"
    assert result.peak is None
    assert result.max_smoothed == pytest.approx(12.0)
    assert result.n_prominent_peaks == 0


def test_deterministic_random_noise_returns_peak_not_found() -> None:
    rng = np.random.default_rng(20260414)
    rt = np.linspace(0.0, 1.0, 240)
    intensity = np.clip(rng.normal(loc=8.0, scale=3.0, size=len(rt)), 0.0, None)

    result = find_peak_and_area(rt, intensity, _config())

    assert result.status == "PEAK_NOT_FOUND"
    assert result.peak is None


def test_negative_baseline_noise_does_not_return_ok_peak() -> None:
    rng = np.random.default_rng(20260414)
    rt = np.linspace(0.0, 1.0, 240)
    intensity = rng.normal(loc=-5.0, scale=2.0, size=len(rt))

    result = find_peak_and_area(rt, intensity, _config())

    assert result.status in {"NO_SIGNAL", "PEAK_NOT_FOUND"}
    assert result.peak is None


def test_zero_signal_returns_no_signal() -> None:
    rt = np.linspace(0.0, 1.0, 60)
    intensity = np.zeros_like(rt)

    result = find_peak_and_area(rt, intensity, _config())

    assert result.status == "NO_SIGNAL"
    assert result.peak is None
    assert result.max_smoothed == pytest.approx(0.0)


def test_empty_signal_returns_no_signal() -> None:
    result = find_peak_and_area(np.array([]), np.array([]), _config())

    assert result.status == "NO_SIGNAL"
    assert result.peak is None
    assert result.n_points == 0
    assert result.max_smoothed is None


def test_mismatched_rt_and_intensity_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        find_peak_and_area(np.array([0.0, 1.0]), np.array([1.0]), _config())


def test_short_signal_returns_window_too_short() -> None:
    rt = np.linspace(0.0, 1.0, 7)
    intensity = _gaussian(rt, center=0.5, sigma=0.1, height=100.0)

    result = find_peak_and_area(rt, intensity, _config(smooth_window=15))

    assert result.status == "WINDOW_TOO_SHORT"
    assert result.peak is None
    assert result.n_points == 7
    assert result.max_smoothed is None


def test_edge_peak_clamps_boundaries_inside_signal() -> None:
    rt = np.linspace(8.0, 10.0, 101)
    intensity = _gaussian(rt, center=8.08, sigma=0.04, height=900.0)

    result = find_peak_and_area(rt, intensity, _config(smooth_window=11))

    assert result.status == "OK"
    assert result.peak is not None
    assert rt[0] <= result.peak.peak_start <= result.peak.rt
    assert result.peak.rt <= result.peak.peak_end <= rt[-1]
    assert result.peak.peak_end > result.peak.peak_start


def test_area_is_computed_from_raw_intensity_not_smoothed() -> None:
    rt = np.linspace(0.0, 1.0, 301)
    intensity = _gaussian(rt, center=0.5, sigma=0.06, height=800.0)
    intensity += 40.0 * np.sin(np.linspace(0.0, 65.0 * np.pi, len(rt)))
    intensity = np.clip(intensity, 0.0, None)
    config = _config(smooth_window=21)

    result = find_peak_and_area(rt, intensity, config)

    assert result.status == "OK"
    assert result.peak is not None

    smoothed = savgol_filter(intensity, config.smooth_window, config.smooth_polyorder)
    left = int(np.searchsorted(rt, result.peak.peak_start, side="left"))
    right = int(np.searchsorted(rt, result.peak.peak_end, side="right"))
    raw_area = np.trapezoid(intensity[left:right], rt[left:right])
    smoothed_area = np.trapezoid(smoothed[left:right], rt[left:right])
    apex_idx = int(np.argmin(np.abs(rt - result.peak.rt)))

    assert result.peak.area == pytest.approx(raw_area)
    assert result.peak.area != pytest.approx(smoothed_area, rel=1e-4)
    assert result.peak.intensity == pytest.approx(intensity[apex_idx])
    assert result.peak.intensity_smoothed == pytest.approx(smoothed[apex_idx])
