from pathlib import Path

import numpy as np

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
    )


def test_find_peak_and_area_without_scoring_context_unchanged() -> None:
    rt = np.linspace(0, 10, 501)
    y = 100 * np.exp(-((rt - 5) / 0.2) ** 2) + 1
    result = find_peak_and_area(rt, y, _cfg())
    assert result.status == "OK"
    assert result.peak is not None
    assert abs(result.peak.rt - 5.0) < 0.05


def test_find_peak_and_area_with_scoring_returns_same_best_for_clean_peak() -> None:
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

    result = find_peak_and_area(rt, y, _cfg(), scoring_context_builder=ctx_builder)
    assert result.status == "OK"
    assert result.peak is not None
    assert abs(result.peak.rt - 5.0) < 0.05
