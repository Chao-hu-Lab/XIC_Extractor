from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from tools.diagnostics.area_integration_uncertainty_io import _ratio
from tools.diagnostics.area_integration_uncertainty_models import (
    BOUNDARY_DELTA_CONCERN_MIN,
    HIGH_UNCERTAINTY_FRACTION,
    LOW_BASELINE_FRACTION,
    RAW_AREA_RATIO_MAX,
    RAW_AREA_RATIO_MIN,
    AlignmentIntegrationAudit,
    AreaIntegrationRow,
    AreaIntegrationSummary,
    EvidenceRow,
    TargetedAudit,
)


def _build_row(
    evidence: EvidenceRow,
    *,
    targeted_audits: Mapping[tuple[str, str, str], TargetedAudit],
    boundary_alternatives: Mapping[tuple[str, str, str], float | None],
    alignment_audits: Mapping[tuple[str, str], AlignmentIntegrationAudit],
) -> AreaIntegrationRow:
    targeted = targeted_audits.get(
        (evidence.sample, evidence.target_label, evidence.targeted_candidate_id)
    )
    alignment = (
        None
        if not evidence.untargeted_family_id
        else alignment_audits.get((evidence.untargeted_family_id, evidence.sample))
    )
    boundary_alternative_ratio = boundary_alternatives.get(
        (evidence.sample, evidence.target_label, evidence.targeted_candidate_id)
    )
    baseline_ratio = _ratio(
        None if alignment is None else alignment.baseline_area,
        None if targeted is None else targeted.baseline_area,
    )
    bucket, reason = _classify(
        evidence,
        targeted=targeted,
        alignment=alignment,
        baseline_ratio=baseline_ratio,
        boundary_alternative_ratio=boundary_alternative_ratio,
    )
    return AreaIntegrationRow(
        sample=evidence.sample,
        target_label=evidence.target_label,
        role=evidence.role,
        targeted_candidate_id=evidence.targeted_candidate_id,
        untargeted_family_id=evidence.untargeted_family_id,
        target_mz=evidence.target_mz,
        untargeted_family_mz=evidence.untargeted_family_mz,
        targeted_area=evidence.targeted_area,
        untargeted_area=evidence.untargeted_area,
        raw_area_ratio=evidence.raw_area_ratio,
        targeted_baseline_area=None if targeted is None else targeted.baseline_area,
        untargeted_baseline_area=None if alignment is None else alignment.baseline_area,
        baseline_area_ratio=baseline_ratio,
        baseline_area_method="" if alignment is None else alignment.baseline_area_method,
        targeted_uncertainty_fraction=(
            None if targeted is None else targeted.uncertainty_fraction
        ),
        untargeted_uncertainty_fraction=(
            None if alignment is None else alignment.uncertainty_fraction
        ),
        targeted_baseline_fraction=(
            None if targeted is None else targeted.baseline_fraction
        ),
        untargeted_baseline_fraction=(
            None if alignment is None else alignment.baseline_fraction
        ),
        boundary_delta_start_min=evidence.boundary_delta_start_min,
        boundary_delta_end_min=evidence.boundary_delta_end_min,
        boundary_alternative_area_ratio=boundary_alternative_ratio,
        targeted_region_verdict=evidence.targeted_region_verdict,
        untargeted_region_verdict=evidence.untargeted_region_verdict,
        targeted_local_mixture_verdict=evidence.targeted_local_mixture_verdict,
        untargeted_local_mixture_verdict=evidence.untargeted_local_mixture_verdict,
        evidence_spine_mismatch_reason=evidence.mismatch_reason,
        integration_bucket=bucket,
        integration_reason=reason,
    )


def _classify(
    evidence: EvidenceRow,
    *,
    targeted: TargetedAudit | None,
    alignment: AlignmentIntegrationAudit | None,
    baseline_ratio: float | None,
    boundary_alternative_ratio: float | None,
) -> tuple[str, str]:
    if not evidence.untargeted_family_id:
        return "missing_alignment_match", "No matched untargeted family."
    if (
        targeted is None
        or alignment is None
        or evidence.raw_area_ratio is None
        or targeted.baseline_area is None
        or alignment.baseline_area is None
    ):
        return "integration_context_incomplete", "Required integration fields missing."

    raw_consistent = _ratio_in_window(evidence.raw_area_ratio)
    label_mismatch = _label_mismatch(evidence)
    if (
        raw_consistent
        and not label_mismatch
        and not _has_high_uncertainty(
            targeted,
            alignment,
        )
    ):
        return (
            "area_consistent_low_uncertainty",
            "Raw area ratio is consistent and uncertainty is low.",
        )
    if raw_consistent and label_mismatch:
        return (
            "label_only_mismatch",
            "RT/area are consistent but diagnostic region labels differ.",
        )
    if (
        not raw_consistent
        and baseline_ratio is not None
        and _ratio_in_window(baseline_ratio)
    ):
        return (
            "baseline_explains_raw_mismatch",
            "Baseline-corrected area ratio falls inside the consistency window.",
        )
    if _boundary_sensitive(evidence, boundary_alternative_ratio):
        return (
            "boundary_sensitive",
            "Boundary delta or selected top-boundary area ratio is outside limits.",
        )
    if _has_high_uncertainty(targeted, alignment):
        return (
            "high_uncertainty",
            "Area uncertainty or baseline fraction is outside limits.",
        )
    return (
        "unexplained_area_mismatch",
        "Area mismatch remains after available integration audit checks.",
    )


def _label_mismatch(evidence: EvidenceRow) -> bool:
    return _nonempty_diff(
        evidence.targeted_region_verdict,
        evidence.untargeted_region_verdict,
    ) or _nonempty_diff(
        evidence.targeted_local_mixture_verdict,
        evidence.untargeted_local_mixture_verdict,
    )


def _nonempty_diff(left: str, right: str) -> bool:
    return bool(left and right and left != right)


def _ratio_in_window(value: float) -> bool:
    return RAW_AREA_RATIO_MIN <= value <= RAW_AREA_RATIO_MAX


def _boundary_sensitive(
    evidence: EvidenceRow,
    boundary_alternative_ratio: float | None,
) -> bool:
    if _abs_gt(evidence.boundary_delta_start_min, BOUNDARY_DELTA_CONCERN_MIN):
        return True
    if _abs_gt(evidence.boundary_delta_end_min, BOUNDARY_DELTA_CONCERN_MIN):
        return True
    return boundary_alternative_ratio is not None and not _ratio_in_window(
        boundary_alternative_ratio
    )


def _has_high_uncertainty(
    targeted: TargetedAudit,
    alignment: AlignmentIntegrationAudit,
) -> bool:
    return (
        _gt(targeted.uncertainty_fraction, HIGH_UNCERTAINTY_FRACTION)
        or _gt(alignment.uncertainty_fraction, HIGH_UNCERTAINTY_FRACTION)
        or _lt(targeted.baseline_fraction, LOW_BASELINE_FRACTION)
        or _lt(alignment.baseline_fraction, LOW_BASELINE_FRACTION)
    )


def _summarize(rows: Sequence[AreaIntegrationRow]) -> AreaIntegrationSummary:
    counter = Counter(row.integration_bucket for row in rows)
    return AreaIntegrationSummary(
        rows_checked=len(rows),
        bucket_counts=_format_counter(counter),
        missing_alignment_match_count=counter["missing_alignment_match"],
        integration_context_incomplete_count=counter["integration_context_incomplete"],
        unexplained_area_mismatch_count=counter["unexplained_area_mismatch"],
    )


def _gt(value: float | None, threshold: float) -> bool:
    return value is not None and value > threshold


def _lt(value: float | None, threshold: float) -> bool:
    return value is not None and value < threshold


def _abs_gt(value: float | None, threshold: float) -> bool:
    return value is not None and abs(value) > threshold


def _format_counter(counter: Counter[str]) -> str:
    return ";".join(f"{key}:{counter[key]}" for key in sorted(counter))
