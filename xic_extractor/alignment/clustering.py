from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.models import AlignmentCluster

_REVIEW_PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def is_alignment_anchor(
    candidate: Any,
    config: AlignmentConfig | None = None,
) -> bool:
    active_config = config or AlignmentConfig()
    priority = _string_attr(candidate, "review_priority")
    evidence_score = _int_attr(candidate, "evidence_score")
    seed_event_count = _int_attr(candidate, "seed_event_count")
    ms1_peak_found = _bool_attr(candidate, "ms1_peak_found")
    scan_support_score = _finite_number_attr(candidate, "ms1_scan_support_score")

    return (
        priority in active_config.anchor_priorities
        and evidence_score is not None
        and evidence_score >= active_config.anchor_min_evidence_score
        and seed_event_count is not None
        and seed_event_count >= active_config.anchor_min_seed_events
        and ms1_peak_found is True
        and scan_support_score is not None
        and scan_support_score >= active_config.anchor_min_scan_support_score
    )


def alignment_candidate_sort_key(
    candidate: Any,
    config: AlignmentConfig | None = None,
) -> tuple[int, int, int, int, int, float, int, float, int, float, int, str, int, str]:
    active_config = config or AlignmentConfig()
    evidence_score = _int_attr(candidate, "evidence_score")
    seed_event_count = _int_attr(candidate, "seed_event_count")
    scan_support_score = _finite_number_attr(candidate, "ms1_scan_support_score")
    precursor_mz = _finite_number_attr(candidate, "precursor_mz")
    rt = _candidate_rt(candidate)
    sample_stem = _string_attr(candidate, "sample_stem")
    candidate_id = _string_attr(candidate, "candidate_id")

    return (
        0 if is_alignment_anchor(candidate, active_config) else 1,
        _REVIEW_PRIORITY_RANK.get(_string_attr(candidate, "review_priority"), 3),
        -(evidence_score if evidence_score is not None else -1),
        -(seed_event_count if seed_event_count is not None else -1),
        0 if scan_support_score is not None else 1,
        -scan_support_score if scan_support_score is not None else 0.0,
        0 if precursor_mz is not None else 1,
        precursor_mz if precursor_mz is not None else math.inf,
        0 if rt is not None else 1,
        rt if rt is not None else math.inf,
        0 if sample_stem is not None else 1,
        sample_stem or "",
        0 if candidate_id is not None else 1,
        candidate_id or "",
    )


def cluster_candidates(
    candidates: Sequence[Any],
    config: AlignmentConfig | None = None,
) -> tuple[AlignmentCluster, ...]:
    if candidates:
        raise NotImplementedError("alignment clustering is not implemented yet")
    return ()


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
