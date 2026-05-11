from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from xic_extractor.alignment.compatibility import can_attach_to_cluster
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.models import (
    AlignmentCluster,
    build_alignment_cluster,
)

_INVALID_NUMBER = object()


def is_alignment_anchor(
    candidate: Any,
    config: AlignmentConfig | None = None,
) -> bool:
    active_config = config or AlignmentConfig()
    priority = _string_attr(candidate, "review_priority")
    evidence_score = _int_attr(candidate, "evidence_score")
    seed_event_count = _int_attr(candidate, "seed_event_count")
    ms1_peak_found = _bool_attr(candidate, "ms1_peak_found")
    ms1_apex_rt = _finite_number_attr(candidate, "ms1_apex_rt")
    ms1_area = _finite_number_attr(candidate, "ms1_area")
    scan_support_score = _finite_number_attr(candidate, "ms1_scan_support_score")
    scan_support_valid = _optional_scan_support_is_valid(candidate)

    return (
        priority in active_config.anchor_priorities
        and evidence_score is not None
        and evidence_score >= active_config.anchor_min_evidence_score
        and seed_event_count is not None
        and seed_event_count >= active_config.anchor_min_seed_events
        and ms1_peak_found is True
        and ms1_apex_rt is not None
        and ms1_area is not None
        and ms1_area > 0
        and scan_support_valid
        and (
            scan_support_score is None
            or scan_support_score >= active_config.anchor_min_scan_support_score
        )
    )


def alignment_candidate_sort_key(
    candidate: Any,
    config: AlignmentConfig | None = None,
) -> tuple[object, ...]:
    active_config = config or AlignmentConfig()
    evidence_score = _int_attr(candidate, "evidence_score")
    seed_event_count = _int_attr(candidate, "seed_event_count")
    ms1_area = _finite_number_attr(candidate, "ms1_area")
    neutral_loss_error = _finite_number_attr(candidate, "neutral_loss_mass_error_ppm")
    precursor_mz = _finite_number_attr(candidate, "precursor_mz")
    rt = _candidate_rt(candidate)
    sample_stem = _string_attr(candidate, "sample_stem")
    candidate_id = _string_attr(candidate, "candidate_id")

    return (
        0 if is_alignment_anchor(candidate, active_config) else 1,
        -(evidence_score if evidence_score is not None else -1),
        -(seed_event_count if seed_event_count is not None else -1),
        0 if ms1_area is not None else 1,
        -ms1_area if ms1_area is not None else 0.0,
        0 if neutral_loss_error is not None else 1,
        abs(neutral_loss_error) if neutral_loss_error is not None else math.inf,
        0 if candidate_id is not None else 1,
        candidate_id or "",
        0 if sample_stem is not None else 1,
        sample_stem or "",
        0 if precursor_mz is not None else 1,
        precursor_mz if precursor_mz is not None else math.inf,
        0 if rt is not None else 1,
        rt if rt is not None else math.inf,
    )


def cluster_candidates(
    candidates: Sequence[Any],
    config: AlignmentConfig | None = None,
) -> tuple[AlignmentCluster, ...]:
    if candidates:
        raise NotImplementedError("alignment clustering is not implemented yet")
    return ()


def _cluster_candidates_greedy(
    candidates: Sequence[Any],
    config: AlignmentConfig | None = None,
) -> tuple[AlignmentCluster, ...]:
    active_config = config or AlignmentConfig()
    clusters: list[AlignmentCluster] = []
    next_cluster_index = 1

    for _, stratum_candidates in _candidates_by_neutral_loss_tag(candidates):
        stratum_clusters = _cluster_stratum_greedy(
            stratum_candidates,
            active_config,
            start_index=next_cluster_index,
        )
        clusters.extend(stratum_clusters)
        next_cluster_index += len(stratum_clusters)

    return tuple(clusters)


def _cluster_stratum_greedy(
    candidates: Sequence[Any],
    config: AlignmentConfig,
    *,
    start_index: int = 1,
) -> tuple[AlignmentCluster, ...]:
    clusters: list[AlignmentCluster] = []

    for candidate in sorted(
        candidates,
        key=lambda item: alignment_candidate_sort_key(item, config),
    ):
        if _attach_to_first_compatible_cluster(clusters, candidate, config):
            continue
        clusters.append(
            _build_singleton_cluster(
                candidate,
                config,
                cluster_index=start_index + len(clusters),
            ),
        )

    return tuple(clusters)


def _candidates_by_neutral_loss_tag(
    candidates: Sequence[Any],
) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    strata: dict[str, list[Any]] = {}
    for candidate in candidates:
        neutral_loss_tag = _required_string_attr(candidate, "neutral_loss_tag")
        strata.setdefault(neutral_loss_tag, []).append(candidate)
    return tuple(
        (neutral_loss_tag, tuple(strata[neutral_loss_tag]))
        for neutral_loss_tag in sorted(strata)
    )


def _attach_to_first_compatible_cluster(
    clusters: list[AlignmentCluster],
    candidate: Any,
    config: AlignmentConfig,
) -> bool:
    for index, cluster in enumerate(clusters):
        if not can_attach_to_cluster(cluster, candidate, config):
            continue
        if _cluster_has_sample_member(cluster, candidate):
            continue
        clusters[index] = _cluster_with_candidate(cluster, candidate, config)
        return True
    return False


def _build_singleton_cluster(
    candidate: Any,
    config: AlignmentConfig,
    *,
    cluster_index: int,
) -> AlignmentCluster:
    return build_alignment_cluster(
        cluster_id=_internal_cluster_id(cluster_index),
        neutral_loss_tag=_required_string_attr(candidate, "neutral_loss_tag"),
        members=(candidate,),
        anchor_members=_candidate_anchor_members(candidate, config),
    )


def _cluster_with_candidate(
    cluster: AlignmentCluster,
    candidate: Any,
    config: AlignmentConfig,
) -> AlignmentCluster:
    return build_alignment_cluster(
        cluster_id=cluster.cluster_id,
        neutral_loss_tag=cluster.neutral_loss_tag,
        members=(*cluster.members, candidate),
        anchor_members=(
            *cluster.anchor_members,
            *_candidate_anchor_members(candidate, config),
        ),
    )


def _candidate_anchor_members(
    candidate: Any,
    config: AlignmentConfig,
) -> tuple[Any, ...]:
    if is_alignment_anchor(candidate, config):
        return (candidate,)
    return ()


def _cluster_has_sample_member(
    cluster: AlignmentCluster,
    candidate: Any,
) -> bool:
    sample_stem = _required_string_attr(candidate, "sample_stem")
    return any(
        _required_string_attr(member, "sample_stem") == sample_stem
        for member in cluster.members
    )


def _internal_cluster_id(cluster_index: int) -> str:
    return f"internal-{cluster_index:06d}"


def _candidate_rt(candidate: Any) -> float | None:
    rt = _finite_number_attr(candidate, "ms1_apex_rt")
    if rt is not None:
        return rt
    return _finite_number_attr(candidate, "best_seed_rt")


def _string_attr(owner: Any, field: str) -> str | None:
    try:
        value = getattr(owner, field)
    except AttributeError:
        return None
    if not isinstance(value, str):
        return None
    return value


def _required_string_attr(owner: Any, field: str) -> str:
    value = _string_attr(owner, field)
    if value is None:
        raise ValueError(f"alignment candidate field '{field}' must be a string")
    return value


def _int_attr(owner: Any, field: str) -> int | None:
    try:
        value = getattr(owner, field)
    except AttributeError:
        return None
    if type(value) is not int:
        return None
    return value


def _bool_attr(owner: Any, field: str) -> bool | None:
    try:
        value = getattr(owner, field)
    except AttributeError:
        return None
    if type(value) is not bool:
        return None
    return value


def _finite_number_attr(owner: Any, field: str) -> float | None:
    try:
        value = getattr(owner, field)
    except AttributeError:
        return None
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _optional_scan_support_is_valid(owner: Any) -> bool:
    try:
        value = getattr(owner, "ms1_scan_support_score")
    except AttributeError:
        return True
    if value is None:
        return True
    return _finite_number_or_invalid(value) is not _INVALID_NUMBER


def _finite_number_or_invalid(value: Any) -> float | object:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _INVALID_NUMBER
    if not math.isfinite(value):
        return _INVALID_NUMBER
    return float(value)
