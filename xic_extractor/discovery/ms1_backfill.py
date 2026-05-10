import math
from collections.abc import Iterable
from dataclasses import replace
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
from xic_extractor.signal_processing import PeakResult, find_peak_and_area


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
    return _merge_candidates_by_ms1_peak(candidates, settings=settings)


def compute_ms1_scan_support_score(
    rt: np.ndarray,
    peak: PeakResult,
    *,
    scans_target: int,
) -> float:
    if scans_target <= 0:
        raise ValueError("scans_target must be greater than 0")
    if rt.size == 0:
        return 0.0
    mask = (rt >= peak.peak_start) & (rt <= peak.peak_end)
    return min(1.0, float(np.count_nonzero(mask)) / float(scans_target))


def _merge_candidates_by_ms1_peak(
    candidates: list[DiscoveryCandidate],
    *,
    settings: DiscoverySettings,
) -> tuple[DiscoveryCandidate, ...]:
    merged: list[DiscoveryCandidate] = []
    for candidate in candidates:
        merge_index = _matching_ms1_peak_candidate_index(
            candidate, merged, settings=settings
        )
        if merge_index is None:
            merged.append(candidate)
            continue
        merged[merge_index] = _merge_candidate_pair(
            merged[merge_index],
            candidate,
            settings=settings,
        )
    return tuple(merged)


def _matching_ms1_peak_candidate_index(
    candidate: DiscoveryCandidate,
    merged: list[DiscoveryCandidate],
    *,
    settings: DiscoverySettings,
) -> int | None:
    for index, existing in enumerate(merged):
        if _can_merge_by_ms1_peak(existing, candidate, settings=settings):
            return index
    return None


def _can_merge_by_ms1_peak(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
    *,
    settings: DiscoverySettings,
) -> bool:
    return (
        first.raw_file == second.raw_file
        and first.sample_stem == second.sample_stem
        and first.neutral_loss_tag == second.neutral_loss_tag
        and first.ms1_peak_found
        and second.ms1_peak_found
        and _candidate_peak_bounds_present(first)
        and _candidate_peak_bounds_present(second)
        and _within_ppm(
            first.precursor_mz,
            second.precursor_mz,
            settings.precursor_mz_tolerance_ppm,
        )
        and _within_ppm(
            first.product_mz,
            second.product_mz,
            settings.product_mz_tolerance_ppm,
        )
        and _within_ppm(
            first.observed_neutral_loss_da,
            second.observed_neutral_loss_da,
            settings.nl_tolerance_ppm,
        )
        and _peak_intervals_overlap(first, second)
        and _seed_ranges_touch_shared_peak(first, second)
    )


def _merge_candidate_pair(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
    *,
    settings: DiscoverySettings,
) -> DiscoveryCandidate:
    representative = _representative_candidate(first, second)
    seed_scan_ids = tuple(sorted(set(first.seed_scan_ids + second.seed_scan_ids)))
    seed_event_count = first.seed_event_count + second.seed_event_count
    rt_seed_min = min(first.rt_seed_min, second.rt_seed_min)
    rt_seed_max = max(first.rt_seed_max, second.rt_seed_max)
    seed_delta = (
        representative.ms1_apex_rt - representative.best_seed_rt
        if representative.ms1_apex_rt is not None
        else None
    )
    priority = assign_review_priority(
        seed_event_count=seed_event_count,
        ms1_peak_found=True,
        ms1_seed_delta_min=seed_delta,
        settings=settings,
    )
    reason = "MS2 NL seeds merged by shared MS1 peak; MS1 peak found near seed RT"
    return replace(
        representative,
        seed_event_count=seed_event_count,
        seed_scan_ids=seed_scan_ids,
        rt_seed_min=rt_seed_min,
        rt_seed_max=rt_seed_max,
        ms1_search_rt_min=min(first.ms1_search_rt_min, second.ms1_search_rt_min),
        ms1_search_rt_max=max(first.ms1_search_rt_max, second.ms1_search_rt_max),
        ms1_seed_delta_min=seed_delta,
        ms2_product_max_intensity=max(
            first.ms2_product_max_intensity,
            second.ms2_product_max_intensity,
        ),
        review_priority=priority,
        reason=reason,
    )


def _representative_candidate(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> DiscoveryCandidate:
    return min(
        (first, second),
        key=lambda candidate: (
            -candidate.ms2_product_max_intensity,
            abs(candidate.neutral_loss_mass_error_ppm),
            candidate.best_seed_rt,
            candidate.best_ms2_scan_id,
        ),
    )


def _candidate_peak_bounds_present(candidate: DiscoveryCandidate) -> bool:
    return (
        candidate.ms1_peak_rt_start is not None
        and candidate.ms1_peak_rt_end is not None
        and candidate.ms1_peak_rt_start <= candidate.ms1_peak_rt_end
    )


def _peak_intervals_overlap(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> bool:
    first_start = first.ms1_peak_rt_start
    first_end = first.ms1_peak_rt_end
    second_start = second.ms1_peak_rt_start
    second_end = second.ms1_peak_rt_end
    if (
        first_start is None
        or first_end is None
        or second_start is None
        or second_end is None
    ):
        return False
    return max(first_start, second_start) <= min(first_end, second_end)


def _seed_ranges_touch_shared_peak(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> bool:
    return _seed_range_touches_peak(first, second) and _seed_range_touches_peak(
        second, first
    )


def _seed_range_touches_peak(
    seed_candidate: DiscoveryCandidate,
    peak_candidate: DiscoveryCandidate,
) -> bool:
    peak_start = peak_candidate.ms1_peak_rt_start
    peak_end = peak_candidate.ms1_peak_rt_end
    if peak_start is None or peak_end is None:
        return False
    return (
        seed_candidate.rt_seed_min <= peak_end
        and seed_candidate.rt_seed_max >= peak_start
    )


def _within_ppm(a: float, b: float, tolerance_ppm: float) -> bool:
    if (
        not math.isfinite(a)
        or not math.isfinite(b)
        or not math.isfinite(tolerance_ppm)
        or a <= 0
        or b <= 0
        or tolerance_ppm < 0
    ):
        return False
    return abs(a - b) / abs(b) * 1_000_000.0 <= tolerance_ppm


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
