from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from xic_extractor.alignment.cell_quality import (
    CellQualityDecision,
    build_cell_quality_decisions,
    decision_map_by_family,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import row_id

IdentityDecision = Literal[
    "production_family",
    "provisional_discovery",
    "audit_family",
]
IdentityConfidence = Literal["high", "medium", "review", "none"]

_EXTREME_BACKFILL_MIN_RESCUE_FRACTION = 0.70
_EXTREME_BACKFILL_MAX_DETECTED_SUPPORT = 2
_WEAK_SEED_BACKFILL_MIN_RESCUE_FRACTION = 0.60
_WEAK_SEED_BACKFILL_MAX_DETECTED_SUPPORT = 3
_WEAK_SEED_MIN_EVIDENCE_SCORE = 60
_WEAK_SEED_MIN_EVENT_COUNT = 2
_WEAK_SEED_MAX_ABS_NL_PPM = 10.0


@dataclass(frozen=True)
class MatrixIdentityRowDecision:
    feature_family_id: str
    include_in_primary_matrix: bool
    identity_decision: IdentityDecision
    identity_confidence: IdentityConfidence
    primary_evidence: str
    identity_reason: str
    quantifiable_detected_count: int
    quantifiable_rescue_count: int
    review_rescue_count: int
    duplicate_assigned_count: int
    ambiguous_ms1_owner_count: int
    row_flags: tuple[str, ...]


@dataclass(frozen=True)
class MatrixIdentityDecisionSet:
    rows: dict[str, MatrixIdentityRowDecision]
    cell_quality: dict[tuple[str, str], CellQualityDecision]

    def row(self, feature_family_id: str) -> MatrixIdentityRowDecision:
        return self.rows[feature_family_id]


def build_matrix_identity_decisions(
    matrix: AlignmentMatrix,
    config: AlignmentConfig,
    *,
    cell_quality: Mapping[tuple[str, str], CellQualityDecision] | None = None,
) -> MatrixIdentityDecisionSet:
    quality = (
        dict(cell_quality)
        if cell_quality is not None
        else build_cell_quality_decisions(matrix.cells, config)
    )
    quality_by_family = decision_map_by_family(quality)
    cells_by_family = _cells_by_family(matrix.cells)
    rows: dict[str, MatrixIdentityRowDecision] = {}
    for cluster in matrix.clusters:
        family_id = row_id(cluster)
        rows[family_id] = decide_matrix_identity_row(
            cluster,
            quality_by_family.get(family_id, ()),
            cells_by_family.get(family_id, ()),
        )
    return MatrixIdentityDecisionSet(rows=rows, cell_quality=quality)


def decide_matrix_identity_row(
    cluster: Any,
    cell_quality: Sequence[CellQualityDecision],
    cells: Sequence[AlignedCell] = (),
) -> MatrixIdentityRowDecision:
    family_id = row_id(cluster)
    evidence = _family_evidence(cluster)
    primary_evidence = _primary_evidence(cluster, evidence, cell_quality)
    q_detected = sum(
        1 for decision in cell_quality if decision.is_detected_identity_support
    )
    q_rescue = sum(
        1
        for decision in cell_quality
        if decision.quality_status == "rescue_quantifiable"
    )
    review_rescue = sum(
        1 for decision in cell_quality if decision.quality_status == "review_rescue"
    )
    duplicate_count = sum(
        1 for decision in cell_quality if decision.quality_status == "duplicate_loser"
    )
    ambiguous_count = sum(
        1 for decision in cell_quality if decision.quality_status == "ambiguous_owner"
    )
    cell_count = len(cell_quality)

    flags = _row_flags(
        cluster=cluster,
        evidence=evidence,
        primary_evidence=primary_evidence,
        q_detected=q_detected,
        q_rescue=q_rescue,
        duplicate_count=duplicate_count,
        ambiguous_count=ambiguous_count,
        cell_count=cell_count,
        cells=cells,
    )
    include, identity_decision, confidence, reason = _promotion_decision(
        cluster,
        evidence=evidence,
        primary_evidence=primary_evidence,
        q_detected=q_detected,
        q_rescue=q_rescue,
        duplicate_count=duplicate_count,
        ambiguous_count=ambiguous_count,
        cell_count=cell_count,
        cells=cells,
    )
    return MatrixIdentityRowDecision(
        feature_family_id=family_id,
        include_in_primary_matrix=include,
        identity_decision=identity_decision,
        identity_confidence=confidence,
        primary_evidence=primary_evidence,
        identity_reason=reason,
        quantifiable_detected_count=q_detected,
        quantifiable_rescue_count=q_rescue,
        review_rescue_count=review_rescue,
        duplicate_assigned_count=duplicate_count,
        ambiguous_ms1_owner_count=ambiguous_count,
        row_flags=tuple(flags),
    )


def _promotion_decision(
    cluster: Any,
    *,
    evidence: str,
    primary_evidence: str,
    q_detected: int,
    q_rescue: int,
    duplicate_count: int,
    ambiguous_count: int,
    cell_count: int,
    cells: Sequence[AlignedCell],
) -> tuple[bool, IdentityDecision, IdentityConfidence, str]:
    if bool(getattr(cluster, "review_only", False)):
        return False, "audit_family", "review", "review_only"
    if _is_consolidation_loser(evidence):
        return False, "audit_family", "review", "family_consolidation_loser"
    if q_detected == 0 and q_rescue > 0:
        return False, "audit_family", "review", "rescue_only"
    if q_detected == 0 and duplicate_count > 0 and ambiguous_count == 0:
        return False, "audit_family", "review", "duplicate_only"
    if q_detected == 0 and ambiguous_count > 0 and duplicate_count == 0:
        return False, "audit_family", "review", "ambiguous_only"
    if q_detected == 0:
        return False, "audit_family", "none", "zero_quantifiable_detected"
    if duplicate_count > q_detected:
        return False, "audit_family", "review", "duplicate_claim_pressure"
    if _is_extreme_backfill_dependency(
        cluster,
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=cell_count,
    ):
        return (
            False,
            "provisional_discovery",
            "review",
            "extreme_backfill_dependency",
        )
    if _is_weak_seed_backfill_dependency(
        cluster,
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=cell_count,
        cells=cells,
    ):
        return (
            False,
            "provisional_discovery",
            "review",
            "weak_seed_backfill_dependency",
        )
    if primary_evidence == "single_sample_local_owner":
        return (
            False,
            "provisional_discovery",
            "review",
            "single_sample_local_owner",
        )
    if primary_evidence in {"owner_complete_link", "cid_nl_only", "owner_identity"}:
        if q_detected >= 2:
            return True, "production_family", "high", primary_evidence
        return (
            False,
            "provisional_discovery",
            "review",
            "insufficient_detected_identity_support",
        )
    if primary_evidence == "multi_sample_detected":
        return True, "production_family", "medium", "multi_sample_detected"
    if primary_evidence == "anchored_family":
        return (
            False,
            "provisional_discovery",
            "review",
            "anchored_single_detected_phase_a",
        )
    return (
        False,
        "provisional_discovery",
        "review",
        "insufficient_detected_identity_support",
    )


def _row_flags(
    *,
    cluster: Any,
    evidence: str,
    primary_evidence: str,
    q_detected: int,
    q_rescue: int,
    duplicate_count: int,
    ambiguous_count: int,
    cell_count: int,
    cells: Sequence[AlignedCell],
) -> list[str]:
    flags: list[str] = []
    if primary_evidence == "single_sample_local_owner":
        flags.append("single_sample_local_owner")
    if _is_consolidation_loser(evidence):
        flags.append("family_consolidation_loser")
    if primary_evidence == "anchored_family" and q_detected == 1:
        flags.append("anchored_single_detected")
    if q_rescue > q_detected and q_detected > 0:
        flags.append("rescue_heavy")
    if _is_extreme_backfill_dependency(
        cluster,
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=cell_count,
    ):
        flags.append("high_backfill_dependency")
    if _is_weak_seed_backfill_dependency(
        cluster,
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=cell_count,
        cells=cells,
    ):
        flags.append("weak_seed_backfill_dependency")
    if q_detected == 0 and q_rescue > 0:
        flags.append("rescue_only")
    if duplicate_count > 0:
        flags.append("duplicate_claim_pressure")
    if q_detected == 0 and duplicate_count > 0 and q_rescue == 0:
        flags.append("duplicate_only")
    if ambiguous_count > 0:
        flags.append("ambiguous_ms1_owner_pressure")
    if q_detected == 0 and ambiguous_count > 0 and q_rescue == 0:
        flags.append("ambiguous_only")
    if q_detected == 0 and q_rescue == 0 and duplicate_count == 0:
        flags.append("zero_present")
    return flags


def _primary_evidence(
    cluster: Any,
    evidence: str,
    cell_quality: Sequence[CellQualityDecision],
) -> str:
    q_detected = sum(
        1 for decision in cell_quality if decision.is_detected_identity_support
    )
    if evidence == "single_sample_local_owner":
        return "single_sample_local_owner"
    if evidence.startswith("owner_complete_link"):
        return "owner_complete_link"
    if evidence.startswith("owner_identity"):
        return "owner_identity"
    if evidence.startswith("cid_nl_only"):
        return "cid_nl_only"
    if q_detected >= 2:
        return "multi_sample_detected"
    if q_detected == 1 and bool(getattr(cluster, "has_anchor", False)):
        return "anchored_family"
    return evidence or "none"


def _is_consolidation_loser(evidence: str) -> bool:
    return (
        "primary_family_consolidation_loser" in evidence
        or "pre_backfill_identity_consolidation_loser" in evidence
    )


def _is_extreme_backfill_dependency(
    cluster: Any,
    *,
    q_detected: int,
    q_rescue: int,
    cell_count: int,
) -> bool:
    if not _is_dr_neutral_loss_tag(str(getattr(cluster, "neutral_loss_tag", ""))):
        return False
    if q_detected <= 0 or q_detected > _EXTREME_BACKFILL_MAX_DETECTED_SUPPORT:
        return False
    if cell_count <= 0:
        return False
    return q_rescue / cell_count >= _EXTREME_BACKFILL_MIN_RESCUE_FRACTION


def _is_weak_seed_backfill_dependency(
    cluster: Any,
    *,
    q_detected: int,
    q_rescue: int,
    cell_count: int,
    cells: Sequence[AlignedCell],
) -> bool:
    if not _is_dr_neutral_loss_tag(str(getattr(cluster, "neutral_loss_tag", ""))):
        return False
    if q_detected <= 0 or q_detected > _WEAK_SEED_BACKFILL_MAX_DETECTED_SUPPORT:
        return False
    if cell_count <= 0:
        return False
    if q_rescue / cell_count < _WEAK_SEED_BACKFILL_MIN_RESCUE_FRACTION:
        return False
    return _has_weak_detected_seed_quality(cluster, cells)


def _has_weak_detected_seed_quality(
    cluster: Any,
    cells: Sequence[AlignedCell],
) -> bool:
    candidates = _seed_candidates_by_id(cluster)
    if not candidates:
        return False
    detected_cells = tuple(cell for cell in cells if cell.status == "detected")
    if not detected_cells:
        return False

    matched_candidates: list[Any] = []
    for cell in detected_cells:
        candidate = _candidate_for_source_id(
            candidates,
            cell.source_candidate_id or "",
        )
        if candidate is None:
            return True
        matched_candidates.append(candidate)

    evidence_scores = tuple(
        score
        for candidate in matched_candidates
        for score in (_int_attr(candidate, "evidence_score"),)
        if score is not None
    )
    if evidence_scores and min(evidence_scores) < _WEAK_SEED_MIN_EVIDENCE_SCORE:
        return True

    seed_event_counts = tuple(
        count
        for candidate in matched_candidates
        for count in (_int_attr(candidate, "seed_event_count"),)
        if count is not None
    )
    if seed_event_counts and min(seed_event_counts) < _WEAK_SEED_MIN_EVENT_COUNT:
        return True

    nl_ppm_errors = tuple(
        abs(ppm)
        for candidate in matched_candidates
        for ppm in (_float_attr(candidate, "neutral_loss_mass_error_ppm"),)
        if ppm is not None
    )
    return bool(nl_ppm_errors and max(nl_ppm_errors) > _WEAK_SEED_MAX_ABS_NL_PPM)


def _seed_candidates_by_id(cluster: Any) -> dict[str, Any]:
    candidates: dict[str, Any] = {}
    for candidate in _cluster_seed_candidates(cluster):
        candidate_id = str(getattr(candidate, "candidate_id", "") or "")
        if candidate_id:
            candidates[candidate_id] = candidate
    return candidates


def _cluster_seed_candidates(cluster: Any) -> tuple[Any, ...]:
    members = getattr(cluster, "members", ())
    if members:
        return tuple(
            candidate
            for member in members
            for candidate in _seed_candidates_from_member(member)
        )
    event_clusters = getattr(cluster, "event_clusters", ())
    return tuple(
        candidate
        for event_cluster in event_clusters
        for member in getattr(event_cluster, "members", ())
        for candidate in _seed_candidates_from_member(member)
    )


def _seed_candidates_from_member(member: Any) -> tuple[Any, ...]:
    events = getattr(member, "all_events", None)
    if events is not None:
        return tuple(events)
    primary = getattr(member, "primary_identity_event", None)
    supporting = getattr(member, "supporting_events", ())
    if primary is not None:
        return (primary, *tuple(supporting))
    return (member,)


def _candidate_for_source_id(
    candidates: Mapping[str, Any],
    source_candidate_id: str,
) -> Any | None:
    source = source_candidate_id.strip()
    if not source:
        return None
    for key in _source_candidate_keys(source):
        if key in candidates:
            return candidates[key]
    return None


def _source_candidate_keys(source_candidate_id: str) -> tuple[str, ...]:
    if "#" not in source_candidate_id:
        return (source_candidate_id,)
    head, tail = source_candidate_id.split("#", 1)
    return (source_candidate_id, head, tail)


def _int_attr(item: Any, name: str) -> int | None:
    value = getattr(item, name, None)
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_attr(item: Any, name: str) -> float | None:
    value = getattr(item, name, None)
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _is_dr_neutral_loss_tag(tag: str) -> bool:
    return tag == "dR" or tag.endswith("_dR")


def _cells_by_family(
    cells: Sequence[AlignedCell],
) -> dict[str, tuple[AlignedCell, ...]]:
    grouped: dict[str, list[AlignedCell]] = {}
    for cell in cells:
        grouped.setdefault(cell.cluster_id, []).append(cell)
    return {
        family_id: tuple(sorted(items, key=lambda item: item.sample_stem))
        for family_id, items in grouped.items()
    }


def _family_evidence(cluster: Any) -> str:
    if hasattr(cluster, "evidence"):
        return str(cluster.evidence)
    if hasattr(cluster, "fold_evidence"):
        return str(cluster.fold_evidence)
    return ""
