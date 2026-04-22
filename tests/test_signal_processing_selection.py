from pathlib import Path

import numpy as np
import pytest

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_scoring import ScoringContext
from xic_extractor.signal_processing import find_peak_and_area


def _cfg() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("."),
        dll_dir=Path("."),
        output_csv=Path("out.csv"),
        diagnostics_csv=Path("diag.csv"),
        smooth_window=11,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
        resolver_mode="legacy_savgol",
        resolver_chrom_threshold=0.05,
        resolver_min_search_range_min=0.04,
        resolver_min_relative_height=0.05,
        resolver_min_absolute_height=25.0,
        resolver_min_ratio_top_edge=1.3,
        resolver_peak_duration_min=0.03,
        resolver_peak_duration_max=1.00,
        resolver_min_scans=5,
    )


def test_find_peak_and_area_without_scoring_context_unchanged() -> None:
    rt = np.linspace(0, 10, 501)
    y = 100 * np.exp(-((rt - 5) / 0.2) ** 2) + 1
    result = find_peak_and_area(rt, y, _cfg())
    assert result.status == "OK"
    assert result.peak is not None
    assert abs(result.peak.rt - 5.0) < 0.05


@pytest.mark.parametrize("resolver_mode", ["legacy_savgol", "local_minimum"])
def test_find_peak_and_area_with_scoring_returns_same_best_for_clean_peak(
    resolver_mode: str,
) -> None:
    rt = np.linspace(0, 10, 501)
    y = 100 * np.exp(-((rt - 5) / 0.2) ** 2) + 1

    def ctx_builder(candidate) -> ScoringContext:
        return ScoringContext(
            rt_array=rt,
            intensity_array=y,
            apex_index=candidate.smoothed_apex_index,
            half_width_ratio=1.0,
            fwhm_ratio=1.0,
            ms2_present=True,
            nl_match=True,
            rt_prior=5.0,
            rt_prior_sigma=0.1,
            rt_min=0.0,
            rt_max=10.0,
            dirty_matrix=False,
        )

    config = _cfg()
    config = config.__class__(**{**config.__dict__, "resolver_mode": resolver_mode})

    result = find_peak_and_area(rt, y, config, scoring_context_builder=ctx_builder)
    assert result.status == "OK"
    assert result.peak is not None
    assert abs(result.peak.rt - 5.0) < 0.05


def test_local_minimum_preferred_rt_selects_nearest_region() -> None:
    rt = np.linspace(8.7, 9.3, 601)
    y = 950 * np.exp(-((rt - 8.93) / 0.035) ** 2)
    y += 520 * np.exp(-((rt - 9.08) / 0.03) ** 2)
    y += 20.0

    config = _cfg()
    config = config.__class__(
        **{
            **config.__dict__,
            "resolver_mode": "local_minimum",
            "resolver_chrom_threshold": 0.02,
            "resolver_min_search_range_min": 0.03,
            "resolver_min_relative_height": 0.08,
            "resolver_min_absolute_height": 80.0,
            "resolver_min_ratio_top_edge": 1.2,
            "resolver_peak_duration_min": 0.02,
            "resolver_peak_duration_max": 0.30,
            "resolver_min_scans": 7,
        }
    )

    result = find_peak_and_area(rt, y, config, preferred_rt=9.08)

    assert result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(9.08, abs=0.02)


def test_local_minimum_recovery_relaxes_region_filters_for_preferred_rt() -> None:
    rt = np.linspace(8.0, 10.0, 401)
    y = 1000 * np.exp(-((rt - 8.48) / 0.04) ** 2)
    y += 80 * np.exp(-((rt - 9.03) / 0.05) ** 2)
    y += 5.0

    config = _cfg()
    config = config.__class__(
        **{
            **config.__dict__,
            "resolver_mode": "local_minimum",
            "resolver_min_relative_height": 0.10,
            "resolver_min_absolute_height": 25.0,
            "resolver_min_ratio_top_edge": 1.2,
            "resolver_peak_duration_min": 0.03,
            "resolver_peak_duration_max": 1.00,
            "resolver_min_scans": 5,
        }
    )

    result = find_peak_and_area(
        rt,
        y,
        config,
        preferred_rt=9.03,
    )

    assert result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(9.03, abs=0.03)


def test_local_minimum_recovery_relaxes_duration_cap_for_broad_preferred_peak() -> None:
    rt = np.linspace(8.0, 10.0, 401)
    y = 320000 * np.exp(-((rt - 9.0) / 0.30) ** 2)
    y += 500.0

    config = _cfg()
    config = config.__class__(
        **{
            **config.__dict__,
            "resolver_mode": "local_minimum",
            "resolver_chrom_threshold": 0.05,
            "resolver_min_search_range_min": 0.04,
            "resolver_min_relative_height": 0.05,
            "resolver_min_absolute_height": 25.0,
            "resolver_min_ratio_top_edge": 1.3,
            "resolver_peak_duration_min": 0.03,
            "resolver_peak_duration_max": 1.00,
            "resolver_min_scans": 5,
        }
    )

    result = find_peak_and_area(
        rt,
        y,
        config,
        preferred_rt=9.0,
    )

    assert result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(9.0, abs=0.03)


def test_recovery_path_preserves_scoring_metadata() -> None:
    rt = np.linspace(8.0, 10.0, 401)
    y = 1000 * np.exp(-((rt - 8.48) / 0.04) ** 2)
    y += 80 * np.exp(-((rt - 9.03) / 0.05) ** 2)

    def ctx_builder(candidate) -> ScoringContext:
        return ScoringContext(
            rt_array=rt,
            intensity_array=y,
            apex_index=candidate.smoothed_apex_index,
            half_width_ratio=1.0,
            fwhm_ratio=1.0,
            ms2_present=False,
            nl_match=False,
            rt_prior=9.03,
            rt_prior_sigma=0.02,
            rt_min=8.0,
            rt_max=10.0,
            dirty_matrix=False,
        )

    result = find_peak_and_area(
        rt,
        y,
        _cfg(),
        preferred_rt=9.03,
        scoring_context_builder=ctx_builder,
        istd_confidence_note="ISTD anchor was LOW",
    )

    assert result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(9.03, abs=0.02)
    assert result.confidence is not None
    assert result.reason is not None
    assert len(result.severities) == 7


def test_scoring_tiebreak_uses_context_rt_prior_not_preferred_rt() -> None:
    rt = np.linspace(9.6, 10.4, 401)
    y = 300 * np.exp(-((rt - 10.00) / 0.03) ** 2)
    y += 300 * np.exp(-((rt - 10.25) / 0.03) ** 2)
    y += 2.0

    def ctx_builder(candidate) -> ScoringContext:
        return ScoringContext(
            rt_array=rt,
            intensity_array=y,
            apex_index=candidate.smoothed_apex_index,
            half_width_ratio=1.0,
            fwhm_ratio=1.0,
            ms2_present=True,
            nl_match=True,
            rt_prior=10.25,
            rt_prior_sigma=0.05,
            rt_min=9.6,
            rt_max=10.4,
            dirty_matrix=False,
        )

    result = find_peak_and_area(
        rt,
        y,
        _cfg(),
        preferred_rt=10.00,
        strict_preferred_rt=False,
        scoring_context_builder=ctx_builder,
    )

    assert result.status == "OK"
    assert result.peak is not None
    assert result.peak.rt == pytest.approx(10.25, abs=0.02)


def test_find_peak_and_area_passes_context_prior_into_scoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = np.linspace(9.6, 10.4, 401)
    y = 300 * np.exp(-((rt - 10.00) / 0.03) ** 2)
    y += 300 * np.exp(-((rt - 10.25) / 0.03) ** 2)
    y += 2.0
    observed_prior_rts: list[float | None] = []

    def ctx_builder(candidate) -> ScoringContext:
        return ScoringContext(
            rt_array=rt,
            intensity_array=y,
            apex_index=candidate.smoothed_apex_index,
            half_width_ratio=1.0,
            fwhm_ratio=1.0,
            ms2_present=True,
            nl_match=True,
            rt_prior=10.25,
            rt_prior_sigma=0.05,
            rt_min=9.6,
            rt_max=10.4,
            dirty_matrix=False,
        )

    def _score_candidate(candidate, ctx, prior_rt, istd_confidence_note=None):
        observed_prior_rts.append(prior_rt)
        from xic_extractor.peak_scoring import Confidence, ScoredCandidate

        return ScoredCandidate(
            candidate=candidate,
            severities=tuple(),
            confidence=Confidence.HIGH,
            reason="all checks passed",
            prior_rt=prior_rt,
        )

    monkeypatch.setattr(
        "xic_extractor.signal_processing.score_candidate",
        _score_candidate,
    )

    result = find_peak_and_area(
        rt,
        y,
        _cfg(),
        preferred_rt=10.00,
        strict_preferred_rt=False,
        scoring_context_builder=ctx_builder,
    )

    assert result.status == "OK"
    assert observed_prior_rts
    assert set(observed_prior_rts) == {10.25}
