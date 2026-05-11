from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Any

from xic_extractor.alignment.legacy_io import LoadedFeature, LoadedMatrix


@dataclass(frozen=True)
class FeatureMatch:
    source: str
    xic_cluster_id: str
    legacy_feature_id: str
    xic_mz: float
    legacy_mz: float
    mz_delta_ppm: float
    xic_rt: float
    legacy_rt: float
    rt_delta_sec: float
    distance_score: float
    shared_sample_count: int
    xic_present_count: int
    legacy_present_count: int
    both_present_count: int
    xic_only_count: int
    legacy_only_count: int
    both_missing_count: int
    present_jaccard: float | None
    log_area_pearson: float | None
    status: str
    note: str


@dataclass(frozen=True)
class SummaryMetric:
    source: str
    metric: str
    value: Any
    threshold: Any
    status: str
    note: str


@dataclass(frozen=True)
class _EligiblePair:
    xic: LoadedFeature
    legacy: LoadedFeature
    mz_delta_ppm: float
    rt_delta_sec: float
    distance_score: float


def match_legacy_source(
    xic: LoadedMatrix,
    legacy: LoadedMatrix,
    *,
    match_ppm: float = 20.0,
    match_rt_sec: float = 60.0,
    sample_scope: str = "xic",
) -> tuple[FeatureMatch, ...]:
    scope = _sample_scope(xic, legacy, sample_scope)
    shared_samples = tuple(sample for sample in scope if sample in legacy.sample_order)
    eligible_pairs = sorted(
        _eligible_pairs(xic, legacy, match_ppm=match_ppm, match_rt_sec=match_rt_sec),
        key=lambda pair: (
            pair.distance_score,
            abs(pair.rt_delta_sec),
            abs(pair.mz_delta_ppm),
            pair.xic.feature_id,
            pair.legacy.feature_id,
        ),
    )
    used_xic: set[str] = set()
    used_legacy: set[str] = set()
    matches: list[FeatureMatch] = []
    for pair in eligible_pairs:
        if pair.xic.feature_id in used_xic or pair.legacy.feature_id in used_legacy:
            continue
        used_xic.add(pair.xic.feature_id)
        used_legacy.add(pair.legacy.feature_id)
        matches.append(
            _build_match(pair, source=legacy.source, shared_samples=shared_samples)
        )
    return tuple(matches)


def summarize_legacy_source(
    xic: LoadedMatrix,
    legacy: LoadedMatrix,
    matches: tuple[FeatureMatch, ...],
    *,
    sample_scope: str = "xic",
    match_ppm: float = 20.0,
    match_rt_sec: float = 60.0,
    match_distance_warn_median: float = 0.5,
    match_distance_warn_p90: float = 0.8,
) -> tuple[SummaryMetric, ...]:
    scope_samples = _sample_scope(xic, legacy, sample_scope)
    legacy_sample_set = set(legacy.sample_order)
    xic_sample_set = set(xic.sample_order)
    shared_samples = tuple(
        sample
        for sample in scope_samples
        if sample in xic_sample_set and sample in legacy_sample_set
    )
    failed_sample_count = len(scope_samples) - len(shared_samples)
    failed_rate = (
        failed_sample_count / len(scope_samples) if len(scope_samples) > 0 else None
    )
    matched_xic = {match.xic_cluster_id for match in matches}
    matched_legacy = {match.legacy_feature_id for match in matches}
    distance_scores = [match.distance_score for match in matches]
    present_jaccards = [
        match.present_jaccard for match in matches if match.present_jaccard is not None
    ]
    log_correlations = [
        match.log_area_pearson
        for match in matches
        if match.log_area_pearson is not None
    ]
    blocker_shared_samples = len(scope_samples) == 0 or len(shared_samples) == 0

    metrics = [
        _metric(legacy.source, "xic_feature_count", len(xic.features), "", "INFO", ""),
        _metric(
            legacy.source,
            "legacy_feature_count",
            len(legacy.features),
            "",
            "INFO",
            "",
        ),
        _metric(
            legacy.source,
            "matched_feature_count",
            len(matches),
            ">0",
            "WARN" if len(matches) == 0 else "OK",
            "no matched features" if len(matches) == 0 else "",
        ),
        _metric(
            legacy.source,
            "unmatched_xic_count",
            len(xic.features) - len(matched_xic),
            "",
            "INFO",
            "",
        ),
        _metric(
            legacy.source,
            "unmatched_legacy_count",
            len(legacy.features) - len(matched_legacy),
            "",
            "INFO",
            "",
        ),
        _metric(
            legacy.source, "xic_sample_count", len(xic.sample_order), "", "INFO", ""
        ),
        _metric(
            legacy.source,
            "legacy_sample_count",
            len(legacy.sample_order),
            "",
            "INFO",
            "",
        ),
        _metric(legacy.source, "sample_scope", sample_scope, "", "INFO", ""),
        _metric(
            legacy.source,
            "scope_sample_count",
            len(scope_samples),
            ">0",
            "BLOCK" if len(scope_samples) == 0 else "OK",
            "",
        ),
        _metric(
            legacy.source,
            "shared_sample_count",
            len(shared_samples),
            ">0",
            "BLOCK" if blocker_shared_samples else "OK",
            "no shared samples in selected scope" if blocker_shared_samples else "",
        ),
        _metric(
            legacy.source,
            "failed_sample_match_count",
            failed_sample_count,
            "",
            "INFO",
            "",
        ),
        _metric(
            legacy.source,
            "failed_sample_match_rate",
            failed_rate,
            "<=0.10",
            _warn_rate(failed_rate, 0.10),
            "",
        ),
        _metric(
            legacy.source,
            "out_of_scope_legacy_sample_count",
            len(
                [
                    sample
                    for sample in legacy.sample_order
                    if sample not in scope_samples
                ]
            ),
            "",
            "INFO",
            "",
        ),
        _metric(
            legacy.source,
            "median_abs_mz_delta_ppm",
            _median_or_none([abs(match.mz_delta_ppm) for match in matches]),
            f"<={match_ppm}",
            "INFO",
            "",
        ),
        _metric(
            legacy.source,
            "median_abs_rt_delta_sec",
            _median_or_none([abs(match.rt_delta_sec) for match in matches]),
            f"<={match_rt_sec}",
            "INFO",
            "",
        ),
        _metric(
            legacy.source,
            "median_distance_score",
            _median_or_none(distance_scores),
            f"<={match_distance_warn_median}",
            _warn_stat(distance_scores, match_distance_warn_median, "median"),
            "",
        ),
        _metric(
            legacy.source,
            "p90_distance_score",
            _percentile_or_none(distance_scores, 0.90),
            f"<={match_distance_warn_p90}",
            _warn_stat(distance_scores, match_distance_warn_p90, "p90"),
            "",
        ),
        _metric(
            legacy.source,
            "median_present_jaccard",
            _median_or_none(present_jaccards),
            "",
            "INFO",
            "",
        ),
        _metric(
            legacy.source,
            "median_log_area_pearson",
            _median_or_none(log_correlations),
            "",
            "INFO",
            "",
        ),
    ]
    return tuple(metrics)


def summarize_global(metrics: tuple[SummaryMetric, ...]) -> tuple[SummaryMetric, ...]:
    sources = sorted({metric.source for metric in metrics if metric.source != "global"})
    blocker_count = sum(1 for metric in metrics if metric.status == "BLOCK")
    warning_count = sum(1 for metric in metrics if metric.status == "WARN")
    if blocker_count > 0:
        readiness = "blocked"
    elif warning_count > 0:
        readiness = "review"
    else:
        readiness = "manual_review_ready"
    return (
        _metric("global", "provided_source_count", len(sources), ">0", "OK", ""),
        _metric("global", "blocker_count", blocker_count, "0", "INFO", ""),
        _metric("global", "warning_count", warning_count, "0", "INFO", ""),
        _metric("global", "replacement_readiness", readiness, "", "INFO", ""),
    )


def _eligible_pairs(
    xic: LoadedMatrix,
    legacy: LoadedMatrix,
    *,
    match_ppm: float,
    match_rt_sec: float,
) -> list[_EligiblePair]:
    pairs: list[_EligiblePair] = []
    for xic_feature in xic.features:
        for legacy_feature in legacy.features:
            mz_delta_ppm = _ppm_delta(legacy_feature.mz, xic_feature.mz)
            rt_delta_sec = (legacy_feature.rt_min - xic_feature.rt_min) * 60.0
            if abs(mz_delta_ppm) > match_ppm or abs(rt_delta_sec) > match_rt_sec:
                continue
            distance_score = max(
                abs(mz_delta_ppm) / match_ppm,
                abs(rt_delta_sec) / match_rt_sec,
            )
            pairs.append(
                _EligiblePair(
                    xic=xic_feature,
                    legacy=legacy_feature,
                    mz_delta_ppm=mz_delta_ppm,
                    rt_delta_sec=rt_delta_sec,
                    distance_score=distance_score,
                )
            )
    return pairs


def _build_match(
    pair: _EligiblePair,
    *,
    source: str,
    shared_samples: tuple[str, ...],
) -> FeatureMatch:
    xic_present_count = 0
    legacy_present_count = 0
    both_present_count = 0
    xic_only_count = 0
    legacy_only_count = 0
    both_missing_count = 0
    paired_logs: list[tuple[float, float]] = []
    for sample in shared_samples:
        xic_area = pair.xic.sample_areas.get(sample)
        legacy_area = pair.legacy.sample_areas.get(sample)
        xic_present = _present(xic_area)
        legacy_present = _present(legacy_area)
        xic_present_count += int(xic_present)
        legacy_present_count += int(legacy_present)
        if xic_present and legacy_present:
            both_present_count += 1
            paired_logs.append((math.log10(xic_area), math.log10(legacy_area)))  # type: ignore[arg-type]
        elif xic_present:
            xic_only_count += 1
        elif legacy_present:
            legacy_only_count += 1
        else:
            both_missing_count += 1

    union_present_count = both_present_count + xic_only_count + legacy_only_count
    present_jaccard = (
        both_present_count / union_present_count if union_present_count > 0 else None
    )
    sparse_ok = union_present_count <= 2 and both_present_count >= 1
    if sparse_ok:
        status = "OK"
        note = "sparse overlap"
    elif present_jaccard is not None and present_jaccard >= 0.5:
        status = "OK"
        note = "present_jaccard >= 0.5"
    else:
        status = "REVIEW"
        note = "presence pattern mismatch"

    return FeatureMatch(
        source=source,
        xic_cluster_id=pair.xic.feature_id,
        legacy_feature_id=pair.legacy.feature_id,
        xic_mz=pair.xic.mz,
        legacy_mz=pair.legacy.mz,
        mz_delta_ppm=pair.mz_delta_ppm,
        xic_rt=pair.xic.rt_min,
        legacy_rt=pair.legacy.rt_min,
        rt_delta_sec=pair.rt_delta_sec,
        distance_score=pair.distance_score,
        shared_sample_count=len(shared_samples),
        xic_present_count=xic_present_count,
        legacy_present_count=legacy_present_count,
        both_present_count=both_present_count,
        xic_only_count=xic_only_count,
        legacy_only_count=legacy_only_count,
        both_missing_count=both_missing_count,
        present_jaccard=present_jaccard,
        log_area_pearson=_pearson(paired_logs),
        status=status,
        note=note,
    )


def _sample_scope(
    xic: LoadedMatrix,
    legacy: LoadedMatrix,
    sample_scope: str,
) -> tuple[str, ...]:
    if sample_scope == "xic":
        return xic.sample_order
    if sample_scope == "legacy":
        return legacy.sample_order
    if sample_scope == "intersection":
        legacy_samples = set(legacy.sample_order)
        return tuple(sample for sample in xic.sample_order if sample in legacy_samples)
    raise ValueError(
        f"sample_scope must be xic, legacy, or intersection: {sample_scope!r}"
    )


def _ppm_delta(observed: float, reference: float) -> float:
    return (observed - reference) / reference * 1_000_000.0


def _present(value: float | None) -> bool:
    return value is not None and math.isfinite(value) and value > 0


def _pearson(paired_logs: list[tuple[float, float]]) -> float | None:
    if len(paired_logs) < 3:
        return None
    xs = [pair[0] for pair in paired_logs]
    ys = [pair[1] for pair in paired_logs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in paired_logs)
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    value = numerator / (denom_x * denom_y)
    if math.isclose(value, 1.0, abs_tol=1e-12):
        return 1.0
    if math.isclose(value, -1.0, abs_tol=1e-12):
        return -1.0
    return value


def _median_or_none(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def _percentile_or_none(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[int(position)]
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _warn_rate(value: float | None, threshold: float) -> str:
    if value is None:
        return "BLOCK"
    return "WARN" if value > threshold else "OK"


def _warn_stat(values: list[float], threshold: float, mode: str) -> str:
    if not values:
        return "INFO"
    value = (
        _median_or_none(values)
        if mode == "median"
        else _percentile_or_none(values, 0.90)
    )
    return "WARN" if value is not None and value > threshold else "OK"


def _metric(
    source: str,
    metric: str,
    value: Any,
    threshold: Any,
    status: str,
    note: str,
) -> SummaryMetric:
    return SummaryMetric(
        source=source,
        metric=metric,
        value=value,
        threshold=threshold,
        status=status,
        note=note,
    )
