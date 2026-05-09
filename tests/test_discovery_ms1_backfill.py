from pathlib import Path
from typing import get_type_hints

import numpy as np
import pytest

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.grouping import group_discovery_seeds
from xic_extractor.discovery.models import (
    DiscoverySeed,
    DiscoverySettings,
    NeutralLossProfile,
)
from xic_extractor.discovery.ms1_backfill import backfill_ms1_candidates
from xic_extractor.signal_processing import PeakDetectionResult, PeakResult

NEUTRAL_LOSS_DA = 116.0474
RAW_FILE = Path("C:/data/TumorBC2312_DNA.raw")


def test_backfill_peak_config_contract_requires_extraction_config() -> None:
    hints = get_type_hints(backfill_ms1_candidates)

    assert hints["peak_config"] is ExtractionConfig


def test_backfill_runs_real_peak_detection_with_extraction_config() -> None:
    group = _group((_seed(scan_number=10, rt=9.00),))
    rt = np.linspace(8.60, 9.40, 161)
    intensity = _gaussian(rt, center=9.02, sigma=0.04, height=1000.0)
    raw = _FakeRaw(rt=rt, intensity=intensity)

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(ms1_search_padding_min=0.30),
        peak_config=_peak_config(),
    )[0]

    assert candidate.ms1_peak_found is True
    assert candidate.ms1_apex_rt == pytest.approx(9.02)
    assert candidate.ms1_height == pytest.approx(1000.0)
    assert candidate.ms1_area is not None
    assert candidate.ms1_seed_delta_min == pytest.approx(0.02)


def test_backfill_extracts_group_precursor_xic_with_padded_rt_window_and_ppm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group(
        (
            _seed(scan_number=10, rt=7.80, product_intensity=3000.0),
            _seed(scan_number=20, rt=7.90, product_intensity=9000.0),
        ),
        ms1_search_padding_min=0.15,
        precursor_mz_tolerance_ppm=12.0,
    )
    raw = _FakeRaw(
        rt=np.array([7.76, 7.90, 8.01]),
        intensity=np.array([10.0, 500.0, 20.0]),
    )
    peak_config = _peak_config(resolver_mode="local_minimum")
    peak_calls: list[
        tuple[np.ndarray, np.ndarray, ExtractionConfig, float | None, bool]
    ] = []

    def _fake_find_peak_and_area(
        rt: np.ndarray,
        intensity: np.ndarray,
        config: ExtractionConfig,
        *,
        preferred_rt: float | None = None,
        strict_preferred_rt: bool = False,
    ) -> PeakDetectionResult:
        peak_calls.append((rt, intensity, config, preferred_rt, strict_preferred_rt))
        return _ok_peak(rt=7.90, intensity=500.0, area=42.0, start=7.76, end=8.01)

    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        _fake_find_peak_and_area,
    )

    candidates = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(
            ms1_search_padding_min=0.15,
            precursor_mz_tolerance_ppm=12.0,
        ),
        peak_config=peak_config,
    )

    assert raw.requests == [
        (
            group.precursor_mz,
            pytest.approx(7.65),
            pytest.approx(8.05),
            12.0,
        )
    ]
    assert len(peak_calls) == 1
    assert peak_calls[0][0] is raw.rt
    assert peak_calls[0][1] is raw.intensity
    assert peak_calls[0][2] is peak_config
    assert peak_calls[0][3] == 7.90
    assert peak_calls[0][4] is False
    assert len(candidates) == 1


def test_backfill_clamps_ms1_search_rt_min_to_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group((_seed(scan_number=10, rt=0.05),))
    raw = _FakeRaw(rt=np.array([], dtype=float), intensity=np.array([], dtype=float))

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(ms1_search_padding_min=0.20),
        peak_config=_peak_config(),
    )[0]

    assert raw.requests == [
        (
            group.precursor_mz,
            0.0,
            pytest.approx(0.25),
            20.0,
        )
    ]
    assert candidate.ms1_search_rt_min == 0.0
    assert candidate.ms1_search_rt_max == pytest.approx(0.25)


def test_ms1_peak_fields_are_filled_from_peak_detection_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group(
        (
            _seed(scan_number=10, rt=7.80, product_intensity=3000.0),
            _seed(scan_number=20, rt=7.90, product_intensity=9000.0),
        )
    )
    raw = _FakeRaw(
        rt=np.array([7.70, 7.91, 8.08]),
        intensity=np.array([20.0, 900.0, 25.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: _ok_peak(
            rt=7.91,
            intensity=900.0,
            area=1234.5,
            start=7.70,
            end=8.08,
        ),
    )

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(ms1_search_padding_min=0.20),
        peak_config=_peak_config(),
    )[0]

    assert candidate.ms1_peak_found is True
    assert candidate.ms1_apex_rt == 7.91
    assert candidate.ms1_height == 900.0
    assert candidate.ms1_area == 1234.5
    assert candidate.ms1_peak_rt_start == 7.70
    assert candidate.ms1_peak_rt_end == 8.08
    assert candidate.ms1_seed_delta_min == pytest.approx(0.01)
    assert candidate.ms1_trace_quality == "clean"
    assert candidate.review_priority == "HIGH"
    assert candidate.reason == "strong MS2 NL seed group; MS1 peak found near seed RT"
    assert candidate.best_ms2_scan_id == 20
    assert candidate.seed_scan_ids == (10, 20)
    assert candidate.ms2_product_max_intensity == 9000.0


@pytest.mark.parametrize(
    ("rt", "intensity", "peak_result"),
    (
        (np.array([], dtype=float), np.array([], dtype=float), None),
        (
            np.array([7.70, 7.90, 8.10]),
            np.array([0.0, 0.0, 0.0]),
            PeakDetectionResult(
                status="NO_SIGNAL",
                peak=None,
                n_points=3,
                max_smoothed=0.0,
                n_prominent_peaks=0,
            ),
        ),
    ),
)
def test_missing_or_empty_ms1_trace_still_creates_low_priority_candidate(
    monkeypatch: pytest.MonkeyPatch,
    rt: np.ndarray,
    intensity: np.ndarray,
    peak_result: PeakDetectionResult | None,
) -> None:
    group = _group((_seed(scan_number=10, rt=7.80),))
    raw = _FakeRaw(rt=rt, intensity=intensity)
    if peak_result is not None:
        monkeypatch.setattr(
            "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
            lambda *args, **kwargs: peak_result,
        )

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(),
        peak_config=_peak_config(),
    )[0]

    assert candidate.ms1_peak_found is False
    assert candidate.ms1_apex_rt is None
    assert candidate.ms1_height is None
    assert candidate.ms1_area is None
    assert candidate.ms1_peak_rt_start is None
    assert candidate.ms1_peak_rt_end is None
    assert candidate.ms1_seed_delta_min is None
    assert candidate.ms1_trace_quality == "missing"
    assert candidate.review_priority == "LOW"
    assert candidate.reason == "strict MS2 NL seed; MS1 peak missing"


def test_single_seed_with_ms1_peak_is_medium_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group((_seed(scan_number=10, rt=7.80),))
    raw = _FakeRaw(
        rt=np.array([7.70, 7.80, 7.90]),
        intensity=np.array([10.0, 100.0, 10.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: _ok_peak(
            rt=7.80,
            intensity=100.0,
            area=50.0,
            start=7.70,
            end=7.90,
        ),
    )

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(ms1_search_padding_min=0.20),
        peak_config=_peak_config(),
    )[0]

    assert candidate.review_priority == "MEDIUM"
    assert candidate.reason == "single MS2 NL seed; MS1 peak found"


def test_ms1_peak_far_from_best_seed_is_not_high_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group(
        (
            _seed(scan_number=10, rt=7.80, product_intensity=3000.0),
            _seed(scan_number=20, rt=7.90, product_intensity=9000.0),
        )
    )
    raw = _FakeRaw(
        rt=np.array([7.70, 8.16, 8.30]),
        intensity=np.array([10.0, 100.0, 10.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: _ok_peak(
            rt=8.16,
            intensity=100.0,
            area=50.0,
            start=8.10,
            end=8.22,
        ),
    )

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(ms1_search_padding_min=0.20),
        peak_config=_peak_config(),
    )[0]

    assert candidate.ms1_seed_delta_min == pytest.approx(0.26)
    assert candidate.review_priority == "MEDIUM"
    assert candidate.reason == "MS1 peak offset from seed RT"


def test_backfill_merges_candidates_inside_same_ms1_peak_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_group = _group((_seed(scan_number=10, rt=7.80, product_intensity=3000.0),))
    second_group = _group((_seed(scan_number=20, rt=8.04, product_intensity=9000.0),))
    raw = _FakeRaw(
        rt=np.array([7.70, 7.92, 8.10]),
        intensity=np.array([20.0, 900.0, 25.0]),
    )
    peak_results = iter(
        (
            _ok_peak(rt=7.92, intensity=900.0, area=1234.5, start=7.70, end=8.10),
            _ok_peak(rt=7.92, intensity=900.0, area=1234.5, start=7.70, end=8.10),
        )
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: next(peak_results),
    )

    candidates = backfill_ms1_candidates(
        raw,
        (first_group, second_group),
        settings=_settings(ms1_search_padding_min=0.20),
        peak_config=_peak_config(),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.best_ms2_scan_id == 20
    assert candidate.seed_scan_ids == (10, 20)
    assert candidate.seed_event_count == 2
    assert candidate.rt_seed_min == pytest.approx(7.80)
    assert candidate.rt_seed_max == pytest.approx(8.04)
    assert candidate.ms1_area == 1234.5
    assert candidate.ms2_product_max_intensity == 9000.0
    assert candidate.review_priority == "HIGH"
    assert candidate.reason == (
        "MS2 NL seeds merged by shared MS1 peak; MS1 peak found near seed RT"
    )


def test_backfill_does_not_merge_distinct_ms1_peak_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_group = _group((_seed(scan_number=10, rt=7.80, product_intensity=3000.0),))
    second_group = _group((_seed(scan_number=20, rt=8.04, product_intensity=9000.0),))
    raw = _FakeRaw(
        rt=np.array([7.70, 7.80, 8.04, 8.14]),
        intensity=np.array([20.0, 900.0, 850.0, 25.0]),
    )
    peak_results = iter(
        (
            _ok_peak(rt=7.80, intensity=900.0, area=100.0, start=7.70, end=7.88),
            _ok_peak(rt=8.04, intensity=850.0, area=90.0, start=7.96, end=8.14),
        )
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: next(peak_results),
    )

    candidates = backfill_ms1_candidates(
        raw,
        (first_group, second_group),
        settings=_settings(ms1_search_padding_min=0.20),
        peak_config=_peak_config(),
    )

    assert len(candidates) == 2
    assert [candidate.seed_scan_ids for candidate in candidates] == [(10,), (20,)]


def test_ms1_seed_delta_is_signed_but_priority_uses_absolute_distance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group(
        (
            _seed(scan_number=10, rt=7.80, product_intensity=3000.0),
            _seed(scan_number=20, rt=7.90, product_intensity=9000.0),
        )
    )
    raw = _FakeRaw(
        rt=np.array([7.60, 7.70, 7.80]),
        intensity=np.array([10.0, 100.0, 10.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: _ok_peak(
            rt=7.70,
            intensity=100.0,
            area=50.0,
            start=7.60,
            end=7.80,
        ),
    )

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(ms1_search_padding_min=0.20),
        peak_config=_peak_config(),
    )[0]

    assert candidate.ms1_seed_delta_min == pytest.approx(-0.20)
    assert candidate.review_priority == "HIGH"
    assert candidate.reason == "strong MS2 NL seed group; MS1 peak found near seed RT"


@pytest.mark.parametrize(
    ("seed_values", "expected_scan", "expected_rt"),
    (
        (
            (
                (20, 7.82, 0.50),
                (30, 7.86, -0.25),
            ),
            30,
            7.86,
        ),
        (
            (
                (40, 7.88, 0.25),
                (50, 7.84, -0.25),
            ),
            50,
            7.84,
        ),
        (
            (
                (60, 7.84, 0.25),
                (55, 7.84, -0.25),
            ),
            55,
            7.84,
        ),
    ),
)
def test_best_seed_tie_breaks_by_error_then_rt_then_scan_for_candidate(
    monkeypatch: pytest.MonkeyPatch,
    seed_values: tuple[tuple[int, float, float], ...],
    expected_scan: int,
    expected_rt: float,
) -> None:
    seeds = tuple(
        _seed(
            scan_number=scan_number,
            rt=rt,
            product_intensity=10000.0,
            observed_loss_error_ppm=observed_loss_error_ppm,
        )
        for scan_number, rt, observed_loss_error_ppm in seed_values
    )
    group = _group(seeds)
    raw = _FakeRaw(
        rt=np.array([7.70, 7.90, 8.05]),
        intensity=np.array([10.0, 500.0, 20.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: _ok_peak(
            rt=7.90,
            intensity=500.0,
            area=42.0,
            start=7.70,
            end=8.05,
        ),
    )

    candidate = backfill_ms1_candidates(
        raw,
        (group,),
        settings=_settings(),
        peak_config=_peak_config(),
    )[0]

    assert candidate.best_ms2_scan_id == expected_scan
    assert candidate.best_seed_rt == expected_rt
    assert candidate.ms1_seed_delta_min == pytest.approx(7.90 - expected_rt)


def _settings(**overrides: float) -> DiscoverySettings:
    values = {
        "neutral_loss_profile": NeutralLossProfile("DNA_dR", NEUTRAL_LOSS_DA),
        **overrides,
    }
    return DiscoverySettings(**values)


def _peak_config(*, resolver_mode: str = "legacy_savgol") -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=Path("raw"),
        dll_dir=Path("dll"),
        output_csv=Path("output/xic_results.csv"),
        diagnostics_csv=Path("output/xic_diagnostics.csv"),
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        resolver_mode=resolver_mode,
    )


def _gaussian(
    rt: np.ndarray,
    *,
    center: float,
    sigma: float,
    height: float,
) -> np.ndarray:
    return height * np.exp(-0.5 * ((rt - center) / sigma) ** 2)


def _group(
    seeds: tuple[DiscoverySeed, ...],
    **settings_overrides: float,
):
    return group_discovery_seeds(seeds, settings=_settings(**settings_overrides))[0]


def _seed(
    *,
    scan_number: int,
    rt: float,
    precursor_mz: float = 500.0000,
    product_mz: float = 383.9526,
    product_intensity: float = 10000.0,
    observed_loss_error_ppm: float = 0.0,
) -> DiscoverySeed:
    return DiscoverySeed(
        raw_file=RAW_FILE,
        sample_stem="TumorBC2312_DNA",
        scan_number=scan_number,
        rt=rt,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        product_intensity=product_intensity,
        neutral_loss_tag="DNA_dR",
        configured_neutral_loss_da=NEUTRAL_LOSS_DA,
        observed_neutral_loss_da=NEUTRAL_LOSS_DA,
        observed_loss_error_ppm=observed_loss_error_ppm,
    )


def _ok_peak(
    *,
    rt: float,
    intensity: float,
    area: float,
    start: float,
    end: float,
) -> PeakDetectionResult:
    return PeakDetectionResult(
        status="OK",
        peak=PeakResult(
            rt=rt,
            intensity=intensity,
            intensity_smoothed=intensity,
            area=area,
            peak_start=start,
            peak_end=end,
        ),
        n_points=3,
        max_smoothed=intensity,
        n_prominent_peaks=1,
    )


class _FakeRaw:
    def __init__(self, *, rt: np.ndarray, intensity: np.ndarray) -> None:
        self.rt = rt
        self.intensity = intensity
        self.requests: list[tuple[float, float, float, float]] = []

    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        self.requests.append((mz, rt_min, rt_max, ppm_tol))
        return self.rt, self.intensity
