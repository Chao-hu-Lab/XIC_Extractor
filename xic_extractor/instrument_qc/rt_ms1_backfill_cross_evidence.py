from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

RT_SUPPORTED = "rt_supported_shadow_candidate"
RT_UNCERTAIN = "rt_model_uncertain"
RT_CONFLICT = "biological_transfer_conflict"
RT_CLEAN_ONLY = "clean_standard_only_review"

MS1_SUPPORTED = "seed_shape_supported_review_candidate"
MS1_NEIGHBOR = "neighbor_interference_review"
MS1_SHAPE_INSUFFICIENT = "shape_insufficient_review"
MS1_NOT_ASSESSABLE = "not_assessable"

MIN_RT_SUPPORT_CELL_COUNT = 3
MIN_RT_SUPPORT_FRACTION = 0.10


@dataclass(frozen=True)
class RtShadowCellRow:
    feature_id: str
    source_cell_key: str
    sample_stem: str
    feature_mz: str
    raw_feature_rt_min: str
    row_classification: str
    supporting_biological_istd_label: str
    review_reason: str


@dataclass(frozen=True)
class SeedAwareFamilyRow:
    feature_family_id: str
    family_center_mz: str
    family_center_rt: str
    detected_count: int
    accepted_rescue_count: int
    accepted_cell_count: int
    review_classification: str
    recommended_next_action: str
    review_reason: str
    png_paths: str


@dataclass(frozen=True)
class FinalMatrixFamilyRow:
    feature_family_id: str
    include_in_primary_matrix: bool
    identity_decision: str
    accepted_cell_count: int
    detected_count: int
    accepted_rescue_count: int
    review_rescue_count: int


@dataclass(frozen=True)
class IstdRtEnvelopeTargetRow:
    target_label: str
    anchor_status: str
    rt_range_min: float | None
    normal_abs_residual_min: float | None
    warning_abs_residual_min: float | None
    high_raw_drift: bool


@dataclass(frozen=True)
class RtMs1CrossEvidenceRow:
    feature_family_id: str
    family_center_mz: str
    family_center_rt: str
    detected_count: int
    accepted_rescue_count: int
    accepted_cell_count: int
    ms1_review_classification: str
    rt_supported_cell_count: int
    rt_uncertain_cell_count: int
    rt_conflict_cell_count: int
    rt_clean_only_cell_count: int
    rt_total_cell_count: int
    rt_supported_fraction: str
    rt_support_level: str
    supporting_istd_labels: str
    supporting_istd_normal_envelope_min: str
    supporting_istd_warning_envelope_min: str
    supporting_istd_high_raw_drift: str
    rt_drift_context: str
    combined_classification: str
    evidence_grade: str
    final_matrix_status: str
    final_matrix_identity_decision: str
    final_matrix_detected_count: int
    final_matrix_accepted_rescue_count: int
    final_matrix_accepted_cell_count: int
    blocking_evidence: str
    missing_evidence: str
    recommended_next_action: str
    review_reason: str
    overlay_png_paths: str


@dataclass(frozen=True)
class RtMs1CrossEvidenceResult:
    rows: tuple[RtMs1CrossEvidenceRow, ...]
    counts_by_classification: dict[str, int]
    counts_by_evidence_grade: dict[str, int]
    counts_by_final_matrix_status: dict[str, int]
    matrix_status_by_grade: tuple["FinalMatrixGradeSummaryRow", ...]
    total_families: int
    rt_family_count: int
    matched_family_count: int


@dataclass(frozen=True)
class FinalMatrixGradeSummaryRow:
    evidence_grade: str
    final_matrix_status: str
    family_count: int
    detected_count: int
    accepted_rescue_count: int
    accepted_cell_count: int


def build_rt_ms1_backfill_cross_evidence(
    *,
    rt_rows: Sequence[RtShadowCellRow],
    seed_families: Sequence[SeedAwareFamilyRow],
    final_matrix_rows: Sequence[FinalMatrixFamilyRow] = (),
    istd_rt_envelopes: Sequence[IstdRtEnvelopeTargetRow] = (),
) -> RtMs1CrossEvidenceResult:
    rt_by_family = _group_rt_rows(rt_rows)
    final_matrix_by_family = {
        row.feature_family_id: row for row in final_matrix_rows if row.feature_family_id
    }
    envelope_by_target = {
        row.target_label: row for row in istd_rt_envelopes if row.target_label
    }
    seed_family_ids = {row.feature_family_id for row in seed_families}
    rows = tuple(
        _build_family_row(
            seed_family,
            rt_rows=rt_by_family.get(seed_family.feature_family_id, ()),
            final_matrix_row=final_matrix_by_family.get(
                seed_family.feature_family_id
            ),
            envelope_by_target=envelope_by_target,
        )
        for seed_family in seed_families
    )
    return RtMs1CrossEvidenceResult(
        rows=tuple(
            sorted(
                rows,
                key=lambda row: (
                    _classification_sort_key(row.combined_classification),
                    row.feature_family_id,
                ),
            )
        ),
        counts_by_classification=_counts(row.combined_classification for row in rows),
        counts_by_evidence_grade=_counts(row.evidence_grade for row in rows),
        counts_by_final_matrix_status=_counts(row.final_matrix_status for row in rows),
        matrix_status_by_grade=_matrix_status_by_grade(rows),
        total_families=len(rows),
        rt_family_count=len(rt_by_family),
        matched_family_count=len(seed_family_ids & set(rt_by_family)),
    )


def _group_rt_rows(
    rows: Sequence[RtShadowCellRow],
) -> dict[str, tuple[RtShadowCellRow, ...]]:
    grouped: defaultdict[str, list[RtShadowCellRow]] = defaultdict(list)
    for row in rows:
        if row.feature_id:
            grouped[row.feature_id].append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _build_family_row(
    seed_family: SeedAwareFamilyRow,
    *,
    rt_rows: Sequence[RtShadowCellRow],
    final_matrix_row: FinalMatrixFamilyRow | None,
    envelope_by_target: dict[str, IstdRtEnvelopeTargetRow],
) -> RtMs1CrossEvidenceRow:
    rt_counts = Counter(row.row_classification for row in rt_rows)
    rt_supported = rt_counts.get(RT_SUPPORTED, 0)
    rt_uncertain = rt_counts.get(RT_UNCERTAIN, 0)
    rt_conflict = rt_counts.get(RT_CONFLICT, 0)
    rt_clean_only = rt_counts.get(RT_CLEAN_ONLY, 0)
    drift_context = _rt_drift_context(rt_rows, envelope_by_target)
    rt_support_level = _rt_support_level(
        rt_supported=rt_supported,
        rt_conflict=rt_conflict,
        rt_total=len(rt_rows),
    )
    classification = _classify_cross_evidence(
        ms1_classification=seed_family.review_classification,
        rt_supported_cell_count=rt_supported,
        rt_uncertain_cell_count=rt_uncertain,
        rt_conflict_cell_count=rt_conflict,
        rt_total_cell_count=len(rt_rows),
        rt_drift_context=drift_context,
        rt_support_level=rt_support_level,
    )
    evidence_grade = _evidence_grade(
        ms1_classification=seed_family.review_classification,
        rt_supported_cell_count=rt_supported,
        rt_uncertain_cell_count=rt_uncertain,
        rt_conflict_cell_count=rt_conflict,
        rt_total_cell_count=len(rt_rows),
        rt_drift_context=drift_context,
        rt_support_level=rt_support_level,
    )
    supporting_envelopes = _supporting_envelopes(rt_rows, envelope_by_target)
    return RtMs1CrossEvidenceRow(
        feature_family_id=seed_family.feature_family_id,
        family_center_mz=seed_family.family_center_mz,
        family_center_rt=seed_family.family_center_rt,
        detected_count=seed_family.detected_count,
        accepted_rescue_count=seed_family.accepted_rescue_count,
        accepted_cell_count=seed_family.accepted_cell_count,
        ms1_review_classification=seed_family.review_classification,
        rt_supported_cell_count=rt_supported,
        rt_uncertain_cell_count=rt_uncertain,
        rt_conflict_cell_count=rt_conflict,
        rt_clean_only_cell_count=rt_clean_only,
        rt_total_cell_count=len(rt_rows),
        rt_supported_fraction=_format_fraction(rt_supported, len(rt_rows)),
        rt_support_level=rt_support_level,
        supporting_istd_labels=_supporting_labels(rt_rows),
        supporting_istd_normal_envelope_min=_format_envelope_values(
            envelope.normal_abs_residual_min for envelope in supporting_envelopes
        ),
        supporting_istd_warning_envelope_min=_format_envelope_values(
            envelope.warning_abs_residual_min for envelope in supporting_envelopes
        ),
        supporting_istd_high_raw_drift="TRUE"
        if any(envelope.high_raw_drift for envelope in supporting_envelopes)
        else "FALSE",
        rt_drift_context=drift_context,
        combined_classification=classification,
        evidence_grade=evidence_grade,
        final_matrix_status=_final_matrix_status(final_matrix_row),
        final_matrix_identity_decision=(
            final_matrix_row.identity_decision if final_matrix_row is not None else ""
        ),
        final_matrix_detected_count=(
            final_matrix_row.detected_count if final_matrix_row is not None else 0
        ),
        final_matrix_accepted_rescue_count=(
            final_matrix_row.accepted_rescue_count
            if final_matrix_row is not None
            else 0
        ),
        final_matrix_accepted_cell_count=(
            final_matrix_row.accepted_cell_count
            if final_matrix_row is not None
            else 0
        ),
        blocking_evidence=_blocking_evidence(
            ms1_classification=seed_family.review_classification,
            rt_conflict_cell_count=rt_conflict,
            rt_drift_context=drift_context,
        ),
        missing_evidence=_missing_evidence(
            ms1_classification=seed_family.review_classification,
            rt_supported_cell_count=rt_supported,
            rt_uncertain_cell_count=rt_uncertain,
            rt_conflict_cell_count=rt_conflict,
            rt_total_cell_count=len(rt_rows),
            rt_drift_context=drift_context,
            rt_support_level=rt_support_level,
        ),
        recommended_next_action=_recommended_action(classification),
        review_reason=_review_reason(
            classification,
            ms1_classification=seed_family.review_classification,
            rt_supported_cell_count=rt_supported,
            rt_uncertain_cell_count=rt_uncertain,
            rt_conflict_cell_count=rt_conflict,
            rt_total_cell_count=len(rt_rows),
            rt_drift_context=drift_context,
        ),
        overlay_png_paths=seed_family.png_paths,
    )


def _classify_cross_evidence(
    *,
    ms1_classification: str,
    rt_supported_cell_count: int,
    rt_uncertain_cell_count: int,
    rt_conflict_cell_count: int,
    rt_total_cell_count: int,
    rt_drift_context: str,
    rt_support_level: str,
) -> str:
    has_rt_support = rt_support_level == "dominant_support"
    has_rt_conflict = rt_conflict_cell_count > 0
    has_rt_uncertainty = rt_uncertain_cell_count > 0
    if ms1_classification == MS1_SUPPORTED and has_rt_conflict:
        return "ms1_supported_rt_conflict_review"
    if ms1_classification == MS1_SUPPORTED and has_rt_support:
        return "rt_ms1_supported_review_candidate"
    if (
        ms1_classification == MS1_NEIGHBOR
        and has_rt_support
        and rt_drift_context == "biological_istd_residual_envelope_available"
    ):
        return "rt_supported_ms1_interference_drift_explainable_review"
    if ms1_classification == MS1_NEIGHBOR and has_rt_support:
        return "rt_supported_ms1_interference_review"
    if ms1_classification == MS1_SUPPORTED and has_rt_uncertainty:
        return "ms1_supported_rt_uncertain_review"
    if ms1_classification == MS1_SUPPORTED and rt_total_cell_count == 0:
        return "ms1_supported_rt_context_missing"
    if ms1_classification == MS1_SUPPORTED:
        return "ms1_only_review"
    if has_rt_support:
        return "rt_only_review"
    if has_rt_conflict:
        return "rt_conflict_review"
    if has_rt_uncertainty:
        return "rt_uncertain_review"
    if ms1_classification in {MS1_SHAPE_INSUFFICIENT, MS1_NOT_ASSESSABLE}:
        return "ms1_not_ready_review"
    return "not_supported"


def _final_matrix_status(row: FinalMatrixFamilyRow | None) -> str:
    if row is None:
        return "final_matrix_context_missing"
    if not row.include_in_primary_matrix:
        return "not_in_final_matrix"
    if row.accepted_rescue_count > 0:
        return "in_final_matrix_with_accepted_rescue"
    if row.detected_count > 0 or row.accepted_cell_count > 0:
        return "in_final_matrix_detected_only"
    return "not_in_final_matrix"


def _evidence_grade(
    *,
    ms1_classification: str,
    rt_supported_cell_count: int,
    rt_uncertain_cell_count: int,
    rt_conflict_cell_count: int,
    rt_total_cell_count: int,
    rt_drift_context: str,
    rt_support_level: str,
) -> str:
    has_rt_support = rt_support_level == "dominant_support"
    has_rt_conflict = rt_conflict_cell_count > 0
    has_rt_uncertainty = rt_uncertain_cell_count > 0
    if has_rt_conflict:
        return "E_conflict_or_not_supported"
    if ms1_classification == MS1_SUPPORTED and has_rt_support:
        return "A_dual_axis_supported"
    if ms1_classification == MS1_SUPPORTED and not has_rt_conflict:
        return "B_ms1_shape_supported_rt_unconfirmed"
    if (
        ms1_classification == MS1_NEIGHBOR
        and has_rt_support
        and rt_drift_context == "biological_istd_residual_envelope_available"
    ):
        return "C1_drift_explainable_interference_review"
    if ms1_classification == MS1_NEIGHBOR:
        if rt_drift_context == "not_provided":
            return "C_manual_review_interference"
        return "C2_manual_review_interference"
    if ms1_classification in {MS1_SHAPE_INSUFFICIENT, MS1_NOT_ASSESSABLE}:
        return "D_single_axis_or_not_ready"
    if has_rt_support or has_rt_uncertainty or rt_total_cell_count > 0:
        return "D_single_axis_or_not_ready"
    return "E_conflict_or_not_supported"


def _blocking_evidence(
    *,
    ms1_classification: str,
    rt_conflict_cell_count: int,
    rt_drift_context: str,
) -> str:
    blockers: list[str] = []
    if ms1_classification == MS1_NEIGHBOR:
        if rt_drift_context == "biological_istd_residual_envelope_available":
            blockers.append("possible_neighboring_ms1_interference_under_rt_drift")
        else:
            blockers.append("neighboring_ms1_interference")
    if ms1_classification == MS1_SHAPE_INSUFFICIENT:
        blockers.append("ms1_shape_insufficient")
    if ms1_classification == MS1_NOT_ASSESSABLE:
        blockers.append("ms1_not_assessable")
    if rt_conflict_cell_count > 0:
        blockers.append("rt_transfer_conflict")
    return ";".join(blockers)


def _missing_evidence(
    *,
    ms1_classification: str,
    rt_supported_cell_count: int,
    rt_uncertain_cell_count: int,
    rt_conflict_cell_count: int,
    rt_total_cell_count: int,
    rt_drift_context: str,
    rt_support_level: str,
) -> str:
    missing: list[str] = []
    if ms1_classification != MS1_SUPPORTED:
        missing.append("seed_shape_support")
    if rt_support_level != "dominant_support" and rt_conflict_cell_count == 0:
        if rt_support_level == "weak_support":
            missing.append("dominant_rt_support")
        elif rt_total_cell_count == 0:
            missing.append("rt_context")
        elif rt_uncertain_cell_count > 0:
            missing.append("rt_confirmation")
        else:
            missing.append("biological_istd_rt_support")
    return ";".join(missing)


def _recommended_action(classification: str) -> str:
    if classification == "rt_ms1_supported_review_candidate":
        return "candidate_for_future_opt_in_gate"
    if classification == "rt_supported_ms1_interference_drift_explainable_review":
        return "review_interference_with_rt_envelope_context"
    if classification in {
        "rt_supported_ms1_interference_review",
        "ms1_supported_rt_conflict_review",
        "ms1_supported_rt_uncertain_review",
    }:
        return "manual_review_required"
    if classification == "ms1_supported_rt_context_missing":
        return "generate_rt_shadow_context"
    if classification == "rt_only_review":
        return "generate_or_review_seed_specific_overlay"
    return "keep_review_only"


def _review_reason(
    classification: str,
    *,
    ms1_classification: str,
    rt_supported_cell_count: int,
    rt_uncertain_cell_count: int,
    rt_conflict_cell_count: int,
    rt_total_cell_count: int,
    rt_drift_context: str,
) -> str:
    if classification == "rt_ms1_supported_review_candidate":
        return (
            "Seed-aware MS1 shape and dominant local biological-ISTD RT support "
            "agree."
        )
    if classification == "rt_supported_ms1_interference_review":
        return (
            "RT support exists, but neighboring MS1 interference blocks automatic "
            "use as a production gate candidate."
        )
    if classification == "rt_supported_ms1_interference_drift_explainable_review":
        return (
            "Dominant RT support exists and the supporting biological ISTD has "
            "an empirical residual drift envelope; treat neighboring "
            "interference as review context, not a one-strike blocker."
        )
    if classification == "ms1_supported_rt_conflict_review":
        return (
            "MS1 shape is supported, but local biological ISTD RT evidence "
            "conflicts."
        )
    if classification == "ms1_supported_rt_uncertain_review":
        return "MS1 shape is supported, but RT model uncertainty remains high."
    if classification == "ms1_supported_rt_context_missing":
        return "MS1 shape is supported, but no matching Level 2.5 RT rows were found."
    if classification == "rt_only_review":
        return "RT support exists, but MS1 seed-aware support is not established."
    if classification == "rt_conflict_review":
        return "RT transfer conflict exists and MS1 support is not sufficient."
    if classification == "rt_uncertain_review":
        if ms1_classification == MS1_NEIGHBOR:
            return (
                "MS1 has neighboring interference and RT rows are uncertain; "
                "keep as review-only."
            )
        return "RT rows are present but uncertain and MS1 support is not sufficient."
    if classification == "ms1_not_ready_review":
        return f"MS1 state is {ms1_classification}; keep as review-only."
    return (
        "No combined support; "
        f"rt_supported={rt_supported_cell_count}, "
        f"rt_uncertain={rt_uncertain_cell_count}, "
        f"rt_conflict={rt_conflict_cell_count}, rt_total={rt_total_cell_count}, "
        f"rt_drift_context={rt_drift_context}."
    )


def _supporting_labels(rows: Sequence[RtShadowCellRow]) -> str:
    labels = sorted(
        {
            row.supporting_biological_istd_label
            for row in rows
            if row.row_classification == RT_SUPPORTED
            and row.supporting_biological_istd_label
        }
    )
    return ";".join(labels)


def _supporting_envelopes(
    rows: Sequence[RtShadowCellRow],
    envelope_by_target: dict[str, IstdRtEnvelopeTargetRow],
) -> tuple[IstdRtEnvelopeTargetRow, ...]:
    labels = {
        row.supporting_biological_istd_label
        for row in rows
        if row.row_classification == RT_SUPPORTED
        and row.supporting_biological_istd_label
    }
    return tuple(
        envelope_by_target[label]
        for label in sorted(labels)
        if envelope_by_target.get(label) is not None
        and envelope_by_target[label].anchor_status == "stable_istd_anchor"
    )


def _rt_drift_context(
    rows: Sequence[RtShadowCellRow],
    envelope_by_target: dict[str, IstdRtEnvelopeTargetRow],
) -> str:
    if not envelope_by_target:
        return "not_provided"
    envelopes = _supporting_envelopes(rows, envelope_by_target)
    if not envelopes:
        return "missing_for_supporting_istd"
    if any(
        envelope.normal_abs_residual_min is not None
        and envelope.warning_abs_residual_min is not None
        for envelope in envelopes
    ):
        return "biological_istd_residual_envelope_available"
    return "biological_istd_envelope_incomplete"


def _rt_support_level(
    *,
    rt_supported: int,
    rt_conflict: int,
    rt_total: int,
) -> str:
    if rt_conflict > 0:
        return "conflicted"
    if rt_total <= 0 or rt_supported <= 0:
        return "none"
    fraction = rt_supported / rt_total
    if (
        rt_supported >= MIN_RT_SUPPORT_CELL_COUNT
        and fraction >= MIN_RT_SUPPORT_FRACTION
    ):
        return "dominant_support"
    return "weak_support"


def _format_fraction(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return ""
    return f"{numerator / denominator:.6g}"


def _format_envelope_values(values: Iterable[float | None]) -> str:
    finite = sorted({value for value in values if value is not None})
    return ";".join(f"{value:.6g}" for value in finite)


def _matrix_status_by_grade(
    rows: Sequence[RtMs1CrossEvidenceRow],
) -> tuple[FinalMatrixGradeSummaryRow, ...]:
    grouped: dict[tuple[str, str], list[RtMs1CrossEvidenceRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.evidence_grade, row.final_matrix_status)].append(row)
    return tuple(
        FinalMatrixGradeSummaryRow(
            evidence_grade=grade,
            final_matrix_status=status,
            family_count=len(group_rows),
            detected_count=sum(row.final_matrix_detected_count for row in group_rows),
            accepted_rescue_count=sum(
                row.final_matrix_accepted_rescue_count for row in group_rows
            ),
            accepted_cell_count=sum(
                row.final_matrix_accepted_cell_count for row in group_rows
            ),
        )
        for (grade, status), group_rows in sorted(grouped.items())
    )


def _classification_sort_key(classification: str) -> int:
    priority = {
        "rt_ms1_supported_review_candidate": 0,
        "rt_supported_ms1_interference_drift_explainable_review": 1,
        "rt_supported_ms1_interference_review": 2,
        "ms1_supported_rt_conflict_review": 3,
        "ms1_supported_rt_uncertain_review": 4,
        "ms1_supported_rt_context_missing": 5,
        "ms1_only_review": 6,
        "rt_only_review": 7,
        "rt_conflict_review": 8,
        "rt_uncertain_review": 9,
        "ms1_not_ready_review": 10,
        "not_supported": 11,
    }
    return priority.get(classification, 99)


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))
