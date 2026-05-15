import json
import math
from collections.abc import Iterable
from dataclasses import replace
from typing import Any, Literal, Protocol, cast

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

_TagIntersectionStatus = Literal["not_required", "complete", "incomplete"]


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
            settings=settings,
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
        candidate = DiscoveryCandidate.from_values(
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
            ms1_scan_support_score=ms1_fields.scan_support_score,
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
        candidates.append(_with_tag_fields(candidate, group=group, settings=settings))
    return merge_candidates_by_ms1_peak(candidates, settings=settings)


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


def merge_candidates_by_ms1_peak(
    candidates: Iterable[DiscoveryCandidate],
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


_merge_candidates_by_ms1_peak = merge_candidates_by_ms1_peak


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
    if not (
        first.raw_file == second.raw_file
        and first.sample_stem == second.sample_stem
        and first.ms1_peak_found
        and second.ms1_peak_found
        and _candidate_peak_bounds_present(first)
        and _candidate_peak_bounds_present(second)
        and _within_ppm(
            first.precursor_mz,
            second.precursor_mz,
            settings.precursor_mz_tolerance_ppm,
        )
        and _peak_intervals_overlap(first, second)
        and _seed_ranges_touch_shared_peak(first, second)
    ):
        return False
    if first.neutral_loss_tag == second.neutral_loss_tag:
        return _within_ppm(
            first.product_mz,
            second.product_mz,
            settings.product_mz_tolerance_ppm,
        ) and _within_ppm(
            first.observed_neutral_loss_da,
            second.observed_neutral_loss_da,
            settings.nl_tolerance_ppm,
        )
    return settings.tag_combine_mode == "union"


def _merge_candidate_pair(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
    *,
    settings: DiscoverySettings,
) -> DiscoveryCandidate:
    representative = _representative_candidate(first, second, settings=settings)
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
    matched_tag_names = _ordered_tag_names(
        first.matched_tag_names + second.matched_tag_names,
        settings=settings,
    )
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
        selected_tag_count=len(settings.selected_tag_names),
        matched_tag_count=len(matched_tag_names),
        matched_tag_names=matched_tag_names,
        primary_tag_name=representative.neutral_loss_tag,
        tag_combine_mode=settings.tag_combine_mode,
        tag_intersection_status=_tag_intersection_status(
            matched_tag_names,
            settings=settings,
        ),
        tag_evidence_json=_merge_tag_evidence_json(first, second),
    )


def _representative_candidate(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
    *,
    settings: DiscoverySettings,
) -> DiscoveryCandidate:
    return min(
        (first, second),
        key=lambda candidate: (
            _tag_rank(candidate.neutral_loss_tag, settings=settings),
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


def _with_tag_fields(
    candidate: DiscoveryCandidate,
    *,
    group: DiscoverySeedGroup,
    settings: DiscoverySettings,
) -> DiscoveryCandidate:
    matched_tag_names = _ordered_tag_names(group.matched_tag_names, settings=settings)
    return replace(
        candidate,
        selected_tag_count=len(settings.selected_tag_names),
        matched_tag_count=len(matched_tag_names),
        matched_tag_names=matched_tag_names,
        primary_tag_name=group.neutral_loss_tag,
        tag_combine_mode=settings.tag_combine_mode,
        tag_intersection_status=_tag_intersection_status(
            matched_tag_names,
            settings=settings,
        ),
        tag_evidence_json=group.tag_evidence_json,
    )


def _ordered_tag_names(
    values: Iterable[str],
    *,
    settings: DiscoverySettings,
) -> tuple[str, ...]:
    unique = {value for value in values if value}
    return tuple(
        sorted(unique, key=lambda tag: (_tag_rank(tag, settings=settings), tag))
    )


def _tag_rank(tag: str, *, settings: DiscoverySettings) -> int:
    try:
        return settings.selected_tag_names.index(tag)
    except ValueError:
        return len(settings.selected_tag_names)


def _tag_intersection_status(
    matched_tag_names: tuple[str, ...],
    *,
    settings: DiscoverySettings,
) -> _TagIntersectionStatus:
    if settings.tag_combine_mode != "intersection":
        return "not_required"
    return (
        "complete"
        if set(settings.selected_tag_names).issubset(set(matched_tag_names))
        else "incomplete"
    )


def _merge_tag_evidence_json(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> str:
    payload: dict[str, Any] = {}
    for candidate in (first, second):
        try:
            parsed = json.loads(candidate.tag_evidence_json or "{}")
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            for tag_name, evidence in parsed.items():
                tag_key = str(tag_name)
                if not isinstance(evidence, dict):
                    payload.setdefault(tag_key, evidence)
                    continue
                if isinstance(payload.get(tag_key), dict):
                    payload[tag_key] = _merge_tag_evidence_entry(
                        cast(dict[str, Any], payload[tag_key]),
                        cast(dict[str, Any], evidence),
                    )
                else:
                    payload[tag_key] = dict(evidence)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _merge_tag_evidence_entry(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(first)
    for key, value in second.items():
        merged.setdefault(key, value)

    scan_ids = sorted(
        set(_int_values(first.get("scan_ids")))
        | set(_int_values(second.get("scan_ids")))
    )
    if scan_ids:
        merged["scan_ids"] = scan_ids

    scan_count = _optional_int(first.get("scan_count")) + _optional_int(
        second.get("scan_count")
    )
    if scan_count:
        merged["scan_count"] = scan_count
    elif scan_ids:
        merged["scan_count"] = len(scan_ids)

    _merge_float_min(merged, first, second, "rt_min")
    _merge_float_max(merged, first, second, "rt_max")
    _merge_max_intensity_fields(merged, first, second)
    return merged


def _merge_float_min(
    merged: dict[str, Any],
    first: dict[str, Any],
    second: dict[str, Any],
    key: str,
) -> None:
    values = [
        value
        for value in (_optional_float(first.get(key)), _optional_float(second.get(key)))
        if value is not None
    ]
    if values:
        merged[key] = min(values)


def _merge_float_max(
    merged: dict[str, Any],
    first: dict[str, Any],
    second: dict[str, Any],
    key: str,
) -> None:
    values = [
        value
        for value in (_optional_float(first.get(key)), _optional_float(second.get(key)))
        if value is not None
    ]
    if values:
        merged[key] = max(values)


def _merge_max_intensity_fields(
    merged: dict[str, Any],
    first: dict[str, Any],
    second: dict[str, Any],
) -> None:
    first_intensity = _optional_float(first.get("max_intensity"))
    second_intensity = _optional_float(second.get("max_intensity"))
    if first_intensity is None and second_intensity is None:
        return
    winner = (
        second
        if first_intensity is None
        or (second_intensity is not None and second_intensity > first_intensity)
        else first
    )
    merged["max_intensity"] = _optional_float(winner.get("max_intensity"))
    for key in ("product_mz", "neutral_loss_error_ppm"):
        if key in winner:
            merged[key] = winner[key]


def _int_values(value: object) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        return ()
    parsed: list[int] = []
    for item in value:
        integer = _optional_int(item)
        if integer:
            parsed.append(integer)
    return tuple(parsed)


def _optional_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


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
        scan_support_score: float | None,
    ) -> None:
        self.peak_found = peak_found
        self.apex_rt = apex_rt
        self.area = area
        self.height = height
        self.seed_delta_min = seed_delta_min
        self.peak_rt_start = peak_rt_start
        self.peak_rt_end = peak_rt_end
        self.trace_quality = trace_quality
        self.scan_support_score = scan_support_score


def _detect_ms1_peak(
    rt: np.ndarray,
    intensity: np.ndarray,
    *,
    peak_config: ExtractionConfig,
    best_seed: DiscoverySeed,
    settings: DiscoverySettings,
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
    scan_support_score = compute_ms1_scan_support_score(
        rt,
        peak,
        scans_target=settings.evidence_profile.thresholds.scan_support_target,
    )
    return _Ms1Fields(
        peak_found=True,
        apex_rt=peak.rt,
        area=peak.area,
        height=peak.intensity,
        seed_delta_min=peak.rt - best_seed.rt,
        peak_rt_start=peak.peak_start,
        peak_rt_end=peak.peak_end,
        trace_quality="clean",
        scan_support_score=scan_support_score,
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
        scan_support_score=None,
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
