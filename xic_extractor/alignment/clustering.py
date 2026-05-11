from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from xic_extractor.alignment.compatibility import (
    can_attach_to_cluster,
    ppm_distance,
)
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

    for _, stratum_candidates in _candidates_by_neutral_loss_tag(candidates):
        stratum_clusters = _cluster_stratum_greedy(
            stratum_candidates,
            active_config,
            start_index=1,
        )
        clusters.extend(stratum_clusters)

    return _sort_and_reindex_clusters(clusters, start_index=1)


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

    return _finalize_clusters(clusters, config, start_index=start_index)


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


def _finalize_clusters(
    clusters: Sequence[AlignmentCluster],
    config: AlignmentConfig,
    *,
    start_index: int = 1,
) -> tuple[AlignmentCluster, ...]:
    retained_clusters: list[AlignmentCluster] = []
    ejected_members: list[Any] = []

    for cluster in clusters:
        retained_members, cluster_ejected_members = _partition_final_members(
            cluster,
            config,
        )
        ejected_members.extend(cluster_ejected_members)
        if retained_members:
            retained_clusters.append(
                _rebuild_cluster_with_members(cluster, retained_members, config),
            )

    retained_clusters = list(_sort_clusters(retained_clusters))
    for member in sorted(
        ejected_members,
        key=lambda item: alignment_candidate_sort_key(item, config),
    ):
        if _attach_to_first_final_compatible_cluster(
            retained_clusters,
            member,
            config,
        ):
            retained_clusters = list(_sort_clusters(retained_clusters))
            continue
        retained_clusters.append(
            _build_singleton_cluster(
                member,
                config,
                cluster_index=start_index + len(retained_clusters),
            ),
        )
        retained_clusters = list(_sort_clusters(retained_clusters))

    return _sort_and_reindex_clusters(retained_clusters, start_index=start_index)


def _partition_final_members(
    cluster: AlignmentCluster,
    config: AlignmentConfig,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    retained_members: list[Any] = []
    ejected_members: list[Any] = []

    for member in cluster.members:
        if _member_fits_final_cluster(cluster, member, config):
            retained_members.append(member)
        else:
            ejected_members.append(member)

    return tuple(retained_members), tuple(ejected_members)


def _member_fits_final_cluster(
    cluster: AlignmentCluster,
    member: Any,
    config: AlignmentConfig,
) -> bool:
    return _member_fits_cluster_representative(
        cluster,
        member,
        config,
    ) and can_attach_to_cluster(cluster, member, config)


def _member_fits_cluster_representative(
    cluster: AlignmentCluster,
    member: Any,
    config: AlignmentConfig,
) -> bool:
    return (
        _required_string_attr(member, "neutral_loss_tag") == cluster.neutral_loss_tag
        and ppm_distance(
            cluster.cluster_center_mz,
            _required_positive_number_attr(member, "precursor_mz"),
        )
        <= config.max_ppm
        and abs(_candidate_rt(member) - cluster.cluster_center_rt) * 60.0
        <= config.max_rt_sec
        and ppm_distance(
            cluster.cluster_product_mz,
            _required_positive_number_attr(member, "product_mz"),
        )
        <= config.product_mz_tolerance_ppm
        and ppm_distance(
            cluster.cluster_observed_neutral_loss_da,
            _required_positive_number_attr(member, "observed_neutral_loss_da"),
        )
        <= config.observed_loss_tolerance_ppm
    )


def _attach_to_first_final_compatible_cluster(
    clusters: list[AlignmentCluster],
    candidate: Any,
    config: AlignmentConfig,
) -> bool:
    for index, cluster in enumerate(clusters):
        if _cluster_has_sample_member(cluster, candidate):
            continue
        if not can_attach_to_cluster(cluster, candidate, config):
            continue
        candidate_cluster = _cluster_with_candidate(cluster, candidate, config)
        retained_members, ejected_members = _partition_final_members(
            candidate_cluster,
            config,
        )
        if ejected_members or len(retained_members) != len(candidate_cluster.members):
            continue
        clusters[index] = candidate_cluster
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


def _rebuild_cluster_with_members(
    cluster: AlignmentCluster,
    members: tuple[Any, ...],
    config: AlignmentConfig,
) -> AlignmentCluster:
    return build_alignment_cluster(
        cluster_id=cluster.cluster_id,
        neutral_loss_tag=cluster.neutral_loss_tag,
        members=members,
        anchor_members=_anchor_members_for(members, config),
    )


def _sort_and_reindex_clusters(
    clusters: Sequence[AlignmentCluster],
    *,
    start_index: int,
) -> tuple[AlignmentCluster, ...]:
    return tuple(
        build_alignment_cluster(
            cluster_id=_internal_cluster_id(start_index + index),
            neutral_loss_tag=cluster.neutral_loss_tag,
            members=cluster.members,
            anchor_members=cluster.anchor_members,
        )
        for index, cluster in enumerate(_sort_clusters(clusters))
    )


def _sort_clusters(
    clusters: Sequence[AlignmentCluster],
) -> tuple[AlignmentCluster, ...]:
    return tuple(sorted(clusters, key=_cluster_sort_key))


def _cluster_sort_key(cluster: AlignmentCluster) -> tuple[object, ...]:
    return (
        cluster.cluster_center_mz,
        cluster.cluster_center_rt,
        cluster.neutral_loss_tag,
        tuple(
            sorted(
                (
                    _required_string_attr(member, "candidate_id"),
                    _required_string_attr(member, "sample_stem"),
                    _required_positive_number_attr(member, "precursor_mz"),
                    _candidate_rt(member),
                )
                for member in cluster.members
            ),
        ),
    )


def _candidate_anchor_members(
    candidate: Any,
    config: AlignmentConfig,
) -> tuple[Any, ...]:
    if is_alignment_anchor(candidate, config):
        return (candidate,)
    return ()


def _anchor_members_for(
    members: tuple[Any, ...],
    config: AlignmentConfig,
) -> tuple[Any, ...]:
    return tuple(
        member
        for member in members
        if _candidate_anchor_members(member, config)
    )


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


def _required_positive_number_attr(owner: Any, field: str) -> float:
    value = _finite_number_attr(owner, field)
    if value is None or value <= 0:
        raise ValueError(f"alignment candidate field '{field}' must be positive")
    return value


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
