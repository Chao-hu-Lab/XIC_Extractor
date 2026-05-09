from collections.abc import Iterable
from typing import Protocol

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.models import (
    DiscoveryCandidate,
    DiscoverySeed,
    DiscoverySeedGroup,
    DiscoverySettings,
)
from xic_extractor.discovery.priority import (
    assign_review_priority,
    build_candidate_reason,
)
from xic_extractor.signal_processing import find_peak_and_area


class MS1XicSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        ...


def backfill_ms1_candidates(
    raw: MS1XicSource,
    groups: Iterable[DiscoverySeedGroup],
    *,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
) -> tuple[DiscoveryCandidate, ...]:
    candidates: list[DiscoveryCandidate] = []
    for group in groups:
        if not group.seeds:
            continue
        best_seed = _best_seed(group.seeds)
        rt_min = max(0.0, group.rt_seed_min - settings.ms1_search_padding_min)
        rt_max = group.rt_seed_max + settings.ms1_search_padding_min
        rt, intensity = raw.extract_xic(
            group.precursor_mz,
            rt_min,
            rt_max,
            settings.precursor_mz_tolerance_ppm,
        )
        ms1_fields = _detect_ms1_peak(
            rt,
            intensity,
            peak_config=peak_config,
            best_seed=best_seed,
        )
        priority = assign_review_priority(
            seed_event_count=len(group.seeds),
            ms1_peak_found=ms1_fields.peak_found,
            ms1_seed_delta_min=ms1_fields.seed_delta_min,
            settings=settings,
        )
        reason = build_candidate_reason(
            seed_event_count=len(group.seeds),
            ms1_peak_found=ms1_fields.peak_found,
            ms1_seed_delta_min=ms1_fields.seed_delta_min,
            settings=settings,
        )
        candidates.append(
            DiscoveryCandidate.from_values(
                raw_file=group.raw_file,
                sample_stem=group.sample_stem,
                precursor_mz=group.precursor_mz,
                product_mz=group.product_mz,
                observed_neutral_loss_da=group.observed_neutral_loss_da,
                best_seed=best_seed,
                seed_scan_ids=tuple(seed.scan_number for seed in group.seeds),
                neutral_loss_tag=group.neutral_loss_tag,
                configured_neutral_loss_da=group.configured_neutral_loss_da,
                neutral_loss_mass_error_ppm=group.neutral_loss_mass_error_ppm,
                rt_seed_min=group.rt_seed_min,
                rt_seed_max=group.rt_seed_max,
                ms1_search_rt_min=rt_min,
                ms1_search_rt_max=rt_max,
                ms1_seed_delta_min=ms1_fields.seed_delta_min,
                ms1_peak_rt_start=ms1_fields.peak_rt_start,
                ms1_peak_rt_end=ms1_fields.peak_rt_end,
                ms1_height=ms1_fields.height,
                ms1_trace_quality=ms1_fields.trace_quality,
                seed_event_count=len(group.seeds),
                ms1_peak_found=ms1_fields.peak_found,
                ms1_apex_rt=ms1_fields.apex_rt,
                ms1_area=ms1_fields.area,
                ms2_product_max_intensity=max(
                    seed.product_intensity for seed in group.seeds
                ),
                review_priority=priority,
                reason=reason,
            )
        )
    return tuple(candidates)


class _Ms1Fields:
    def __init__(
        self,
        *,
        peak_found: bool,
        apex_rt: float | None,
        area: float | None,
        height: float | None,
        seed_delta_min: float | None,
        peak_rt_start: float | None,
        peak_rt_end: float | None,
        trace_quality: str,
    ) -> None:
        self.peak_found = peak_found
        self.apex_rt = apex_rt
        self.area = area
        self.height = height
        self.seed_delta_min = seed_delta_min
        self.peak_rt_start = peak_rt_start
        self.peak_rt_end = peak_rt_end
        self.trace_quality = trace_quality


def _detect_ms1_peak(
    rt: np.ndarray,
    intensity: np.ndarray,
    *,
    peak_config: ExtractionConfig,
    best_seed: DiscoverySeed,
) -> _Ms1Fields:
    if rt.size == 0 or intensity.size == 0:
        return _missing_ms1_fields()
    result = find_peak_and_area(
        rt,
        intensity,
        peak_config,
        preferred_rt=best_seed.rt,
        strict_preferred_rt=False,
    )
    if result.status != "OK" or result.peak is None:
        return _missing_ms1_fields()
    peak = result.peak
    return _Ms1Fields(
        peak_found=True,
        apex_rt=peak.rt,
        area=peak.area,
        height=peak.intensity,
        seed_delta_min=peak.rt - best_seed.rt,
        peak_rt_start=peak.peak_start,
        peak_rt_end=peak.peak_end,
        trace_quality="clean",
    )


def _missing_ms1_fields() -> _Ms1Fields:
    return _Ms1Fields(
        peak_found=False,
        apex_rt=None,
        area=None,
        height=None,
        seed_delta_min=None,
        peak_rt_start=None,
        peak_rt_end=None,
        trace_quality="missing",
    )


def _best_seed(seeds: Iterable[DiscoverySeed]) -> DiscoverySeed:
    return min(
        seeds,
        key=lambda seed: (
            -seed.product_intensity,
            abs(seed.observed_loss_error_ppm),
            seed.rt,
            seed.scan_number,
        ),
    )
