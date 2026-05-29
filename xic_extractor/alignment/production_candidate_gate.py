from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from xic_extractor.alignment.machine_decision import project_machine_decision

CandidateGateStatus = Literal[
    "production_candidate",
    "keep_provisional",
    "audit",
    "excluded",
]
CandidateRecommendedAction = Literal[
    "track_candidate",
    "keep_provisional",
    "review",
    "exclude",
]
CandidateConfidence = Literal["medium", "review", "none"]

PRODUCTION_CANDIDATE_GATE_COLUMNS = (
    "feature_family_id",
    "matrix_role",
    "candidate_gate_status",
    "recommended_action",
    "evidence_tier",
    "support_components",
    "dependent_context",
    "challenge_blockers",
    "tier2_evidence_available",
    "candidate_confidence",
    "source_review_artifact",
    "source_review_sha256",
    "source_cell_artifact",
    "source_cell_sha256",
    "source_matrix_artifact",
    "source_matrix_sha256",
)

MIN_SCAN_SUPPORT_SCORE = 0.5
LOW_SCAN_SUPPORT_MAX = 0.2
MAX_ABS_RT_DELTA_SEC = 180.0
MAX_RESCUED_APEX_RT_SPAN_MIN = 0.35

_PROVISIONAL_DECISION = "provisional_discovery"
_REQUIRED_FLAGS = frozenset({"single_detected_seed", "provisional_retention_candidate"})
_STRUCTURAL_EXCLUDE_FLAGS = frozenset(
    {"family_consolidation_loser", "duplicate_only", "rescue_only", "zero_present"}
)
_INDEPENDENT_TIER2_SUPPORT_COMPONENTS = frozenset(
    {"validated_tier2_trace_evidence"}
)
_INTERFERENCE_MARKERS = ("neighbor", "interference")
_LOW_COVERAGE_MARKERS = (
    "low_scan_support",
    "skipped_low_scan_support",
    "coverage",
    "unassessable",
)
_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


@dataclass(frozen=True)
class GateSourceContext:
    review_path: Path
    review_sha256: str
    cell_path: Path
    cell_sha256: str
    matrix_path: Path
    matrix_sha256: str


@dataclass(frozen=True)
class ProductionCandidateGateDecision:
    feature_family_id: str
    matrix_role: str
    candidate_gate_status: CandidateGateStatus
    recommended_action: CandidateRecommendedAction
    evidence_tier: int
    support_components: tuple[str, ...]
    dependent_context: tuple[str, ...]
    challenge_blockers: tuple[str, ...]
    tier2_evidence_available: bool
    candidate_confidence: CandidateConfidence
    source_context: GateSourceContext


def source_context_for_artifacts(
    *,
    review_path: Path,
    cell_path: Path,
    matrix_path: Path,
) -> GateSourceContext:
    return GateSourceContext(
        review_path=review_path,
        review_sha256=_sha256_file(review_path),
        cell_path=cell_path,
        cell_sha256=_sha256_file(cell_path),
        matrix_path=matrix_path,
        matrix_sha256=_sha256_file(matrix_path),
    )


def evaluate_production_candidate_gate(
    review_row: Mapping[str, object],
    cell_rows: Sequence[Mapping[str, object]],
    *,
    source_context: GateSourceContext,
) -> ProductionCandidateGateDecision:
    review = _string_row(review_row)
    cells = tuple(_string_row(row) for row in cell_rows)
    machine = project_machine_decision(review, cells)
    flags = _split_tokens(review.get("row_flags"))

    structural_blockers = _structural_blockers(review, flags)
    if structural_blockers:
        return _decision(
            review=review,
            machine_role=machine.matrix_role,
            status=(
                "excluded"
                if set(structural_blockers) & _STRUCTURAL_EXCLUDE_FLAGS
                else "audit"
            ),
            blockers=structural_blockers,
            evidence_tier=1,
            support=(),
            dependent=(),
            tier2_available=False,
            source_context=source_context,
        )

    if not _is_retention_candidate(review, flags):
        return _decision(
            review=review,
            machine_role=machine.matrix_role,
            status=_status_for_non_candidate(machine.matrix_role),
            blockers=("not_retention_candidate",),
            evidence_tier=1,
            support=(),
            dependent=(),
            tier2_available=False,
            source_context=source_context,
        )

    rescued = tuple(row for row in cells if row.get("status") == "rescued")
    support = _explicit_positive_support(review)
    tier2_available = bool(support)
    dependent = _dependent_context(review, rescued)
    blockers = _challenge_blockers(rescued)
    if _int_value(review.get("quantifiable_rescue_count")) and not rescued:
        blockers = _ordered_unique((*blockers, "missing_rescued_cell_evidence"))
    if not tier2_available:
        blockers = _ordered_unique((*blockers, "missing_positive_tier2_support"))

    if any(blocker != "missing_positive_tier2_support" for blocker in blockers):
        status: CandidateGateStatus = "audit"
    elif blockers:
        status = "keep_provisional"
    else:
        status = "production_candidate"

    return _decision(
        review=review,
        machine_role=machine.matrix_role,
        status=status,
        blockers=blockers,
        evidence_tier=2 if tier2_available else 1,
        support=support,
        dependent=dependent,
        tier2_available=tier2_available,
        source_context=source_context,
    )


def is_candidate_gate_scope(review_row: Mapping[str, object]) -> bool:
    return "provisional_retention_candidate" in _split_tokens(
        review_row.get("row_flags")
    )


def production_candidate_gate_as_row(
    decision: ProductionCandidateGateDecision,
) -> dict[str, str]:
    return {
        "feature_family_id": decision.feature_family_id,
        "matrix_role": decision.matrix_role,
        "candidate_gate_status": decision.candidate_gate_status,
        "recommended_action": decision.recommended_action,
        "evidence_tier": str(decision.evidence_tier),
        "support_components": ";".join(decision.support_components),
        "dependent_context": ";".join(decision.dependent_context),
        "challenge_blockers": ";".join(decision.challenge_blockers),
        "tier2_evidence_available": (
            "TRUE" if decision.tier2_evidence_available else "FALSE"
        ),
        "candidate_confidence": decision.candidate_confidence,
        "source_review_artifact": str(decision.source_context.review_path),
        "source_review_sha256": decision.source_context.review_sha256,
        "source_cell_artifact": str(decision.source_context.cell_path),
        "source_cell_sha256": decision.source_context.cell_sha256,
        "source_matrix_artifact": str(decision.source_context.matrix_path),
        "source_matrix_sha256": decision.source_context.matrix_sha256,
    }


def summarize_gate_decisions(
    decisions: Sequence[ProductionCandidateGateDecision],
) -> dict[str, object]:
    status_counts = Counter(decision.candidate_gate_status for decision in decisions)
    return {
        "schema_version": "production-candidate-gate-v1",
        "readiness_label": "diagnostic_only",
        "row_count": len(decisions),
        "production_candidate_count": status_counts["production_candidate"],
        "keep_provisional_count": status_counts["keep_provisional"],
        "audit_count": status_counts["audit"],
        "excluded_count": status_counts["excluded"],
        "production_ready": False,
        "matrix_contract_changed": False,
    }


def _decision(
    *,
    review: Mapping[str, str],
    machine_role: str,
    status: CandidateGateStatus,
    blockers: Sequence[str],
    evidence_tier: int,
    support: Sequence[str],
    dependent: Sequence[str],
    tier2_available: bool,
    source_context: GateSourceContext,
) -> ProductionCandidateGateDecision:
    return ProductionCandidateGateDecision(
        feature_family_id=review.get("feature_family_id", ""),
        matrix_role=machine_role,
        candidate_gate_status=status,
        recommended_action=_recommended_action(status),
        evidence_tier=evidence_tier,
        support_components=_ordered_unique(support),
        dependent_context=_ordered_unique(dependent),
        challenge_blockers=_ordered_unique(blockers),
        tier2_evidence_available=tier2_available,
        candidate_confidence=_confidence(status),
        source_context=source_context,
    )


def _status_for_non_candidate(matrix_role: str) -> CandidateGateStatus:
    if matrix_role == "excluded":
        return "excluded"
    if matrix_role == "audit":
        return "audit"
    return "keep_provisional"


def _recommended_action(status: CandidateGateStatus) -> CandidateRecommendedAction:
    if status == "production_candidate":
        return "track_candidate"
    if status == "keep_provisional":
        return "keep_provisional"
    if status == "excluded":
        return "exclude"
    return "review"


def _confidence(status: CandidateGateStatus) -> CandidateConfidence:
    if status == "production_candidate":
        return "medium"
    if status in {"keep_provisional", "audit"}:
        return "review"
    return "none"


def _is_retention_candidate(review: Mapping[str, str], flags: frozenset[str]) -> bool:
    if review.get("identity_decision") != _PROVISIONAL_DECISION:
        return False
    if not _REQUIRED_FLAGS.issubset(flags):
        return False
    detected_count = _int_value(review.get("quantifiable_detected_count"))
    rescue_count = _int_value(review.get("quantifiable_rescue_count"))
    duplicate_count = _int_value(review.get("duplicate_assigned_count"))
    ambiguous_count = _int_value(review.get("ambiguous_ms1_owner_count"))
    if None in {detected_count, rescue_count, duplicate_count, ambiguous_count}:
        return False
    if detected_count != 1:
        return False
    if rescue_count is None or rescue_count <= 0:
        return False
    if duplicate_count != 0:
        return False
    return ambiguous_count == 0


def _structural_blockers(
    review: Mapping[str, str],
    flags: frozenset[str],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if review.get("identity_reason") == "review_only" or "review_only" in flags:
        blockers.append("review_only")
    blockers.extend(flag for flag in sorted(flags & _STRUCTURAL_EXCLUDE_FLAGS))
    return tuple(blockers)


def _explicit_positive_support(review: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(
        token
        for token in _split_tokens(review.get("independent_tier2_support_components"))
        if token in _INDEPENDENT_TIER2_SUPPORT_COMPONENTS
    )


def _dependent_context(
    review: Mapping[str, str],
    rescued: Sequence[Mapping[str, str]],
) -> tuple[str, ...]:
    context: list[str] = []
    if review.get("primary_evidence") == "owner_complete_link":
        context.append("owner_backfill_context")
    if rescued:
        context.append("family_ms1_context")
    if rescued and all(
        (_float(row.get("scan_support_score")) or 0.0) >= MIN_SCAN_SUPPORT_SCORE
        for row in rescued
    ):
        context.append("rescued_cell_scan_support_distribution")
    if rescued and all(_local_apex_consistent(row) for row in rescued):
        context.append("selected_boundary_local_apex_consistency")
    apex_rts = [_float(row.get("apex_rt")) for row in rescued]
    finite_apex_rts = [value for value in apex_rts if value is not None]
    if (
        len(finite_apex_rts) >= 2
        and max(finite_apex_rts) - min(finite_apex_rts)
        <= MAX_RESCUED_APEX_RT_SPAN_MIN
    ):
        context.append("rescued_cell_rt_coherence")
    return tuple(context)


def _challenge_blockers(rescued: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    blockers: list[str] = []
    if any(_has_marker(row, _INTERFERENCE_MARKERS) for row in rescued):
        blockers.append("neighboring_interference_challenge")
    if any(_low_assessable_coverage(row) for row in rescued):
        blockers.append("low_assessable_coverage_challenge")
    if any(not _local_apex_consistent(row) for row in rescued):
        blockers.append("selected_boundary_local_apex_inconsistency")
    return tuple(blockers)


def _local_apex_consistent(row: Mapping[str, str]) -> bool:
    apex = _float(row.get("apex_rt"))
    start = _float(row.get("peak_start_rt"))
    end = _float(row.get("peak_end_rt"))
    rt_delta = _float(row.get("rt_delta_sec"))
    if apex is None or start is None or end is None or rt_delta is None:
        return False
    return start <= apex <= end and abs(rt_delta) <= MAX_ABS_RT_DELTA_SEC


def _low_assessable_coverage(row: Mapping[str, str]) -> bool:
    scan_support = _float(row.get("scan_support_score"))
    if scan_support is None:
        return True
    if scan_support <= LOW_SCAN_SUPPORT_MAX:
        return True
    return _has_marker(row, _LOW_COVERAGE_MARKERS)


def _has_marker(row: Mapping[str, str], markers: Sequence[str]) -> bool:
    text = " ".join(
        str(row.get(field, ""))
        for field in (
            "reason",
            "region_local_mixture_diagnostic",
            "region_local_mixture_reason",
            "region_review_reason",
            "region_shadow_status",
            "region_shadow_verdict",
        )
    ).lower()
    return any(marker in text for marker in markers)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _string_row(row: Mapping[str, object]) -> dict[str, str]:
    return {
        str(key): "" if value is None else str(value)
        for key, value in row.items()
    }


def _split_tokens(value: object) -> frozenset[str]:
    return frozenset(
        part.strip() for part in str(value or "").split(";") if part.strip()
    )


def _ordered_unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _float(value: object) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip().lstrip("'"))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _int_value(value: object) -> int | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return None
        return int(value)
    text = str(value).strip().lstrip("'")
    if not _INTEGER_PATTERN.fullmatch(text):
        return None
    try:
        return int(text)
    except ValueError:
        return None
