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
from xic_extractor.alignment.matrix import AlignmentMatrix
from xic_extractor.alignment.output_rows import row_id

IdentityDecision = Literal["production_family", "audit_family"]
IdentityConfidence = Literal["high", "medium", "review", "none"]


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
    rows: dict[str, MatrixIdentityRowDecision] = {}
    for cluster in matrix.clusters:
        family_id = row_id(cluster)
        rows[family_id] = decide_matrix_identity_row(
            cluster,
            quality_by_family.get(family_id, ()),
        )
    return MatrixIdentityDecisionSet(rows=rows, cell_quality=quality)


def decide_matrix_identity_row(
    cluster: Any,
    cell_quality: Sequence[CellQualityDecision],
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

    flags = _row_flags(
        evidence=evidence,
        primary_evidence=primary_evidence,
        q_detected=q_detected,
        q_rescue=q_rescue,
        duplicate_count=duplicate_count,
        ambiguous_count=ambiguous_count,
    )
    include, confidence, reason = _promotion_decision(
        cluster,
        evidence=evidence,
        primary_evidence=primary_evidence,
        q_detected=q_detected,
        q_rescue=q_rescue,
        duplicate_count=duplicate_count,
        ambiguous_count=ambiguous_count,
    )
    return MatrixIdentityRowDecision(
        feature_family_id=family_id,
        include_in_primary_matrix=include,
        identity_decision="production_family" if include else "audit_family",
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
) -> tuple[bool, IdentityConfidence, str]:
    if bool(getattr(cluster, "review_only", False)):
        return False, "review", "review_only"
    if _is_consolidation_loser(evidence):
        return False, "review", "family_consolidation_loser"
    if q_detected == 0 and q_rescue > 0:
        return False, "review", "rescue_only"
    if q_detected == 0 and duplicate_count > 0 and ambiguous_count == 0:
        return False, "review", "duplicate_only"
    if q_detected == 0 and ambiguous_count > 0 and duplicate_count == 0:
        return False, "review", "ambiguous_only"
    if q_detected == 0:
        return False, "none", "zero_quantifiable_detected"
    if duplicate_count > q_detected:
        return False, "review", "duplicate_claim_pressure"
    if primary_evidence == "single_sample_local_owner":
        return False, "review", "single_sample_local_owner"
    if primary_evidence in {"owner_complete_link", "cid_nl_only", "owner_identity"}:
        if q_detected >= 2:
            return True, "high", primary_evidence
        return False, "review", "insufficient_detected_identity_support"
    if primary_evidence == "multi_sample_detected":
        return True, "medium", "multi_sample_detected"
    if primary_evidence == "anchored_family":
        return False, "review", "anchored_single_detected_phase_a"
    return False, "review", "insufficient_detected_identity_support"


def _row_flags(
    *,
    evidence: str,
    primary_evidence: str,
    q_detected: int,
    q_rescue: int,
    duplicate_count: int,
    ambiguous_count: int,
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


def _family_evidence(cluster: Any) -> str:
    if hasattr(cluster, "evidence"):
        return str(cluster.evidence)
    if hasattr(cluster, "fold_evidence"):
        return str(cluster.fold_evidence)
    return ""
