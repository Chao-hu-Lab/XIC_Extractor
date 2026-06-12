"""Root-cause classification logic for targeted NL dropout audit."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from tools.diagnostics.targeted_nl_dropout_root_cause_models import (
    _BLOCKING_TRACE_QUALITY_FLAGS,
    _HARD_CONFLICT_LABELS,
    _SOFT_TRACE_QUALITY_FLAGS,
    CandidateRow,
    ReliabilityRow,
    RootCauseRow,
    RootCauseSummary,
)


def _selected_candidates_by_key(
    candidate_rows: Sequence[CandidateRow],
) -> dict[tuple[str, str], tuple[CandidateRow, ...]]:
    selected_by_key: dict[tuple[str, str], list[CandidateRow]] = {}
    for row in candidate_rows:
        if not row.selected:
            continue
        selected_by_key.setdefault((row.sample_name, row.target_label), []).append(row)
    return {key: tuple(values) for key, values in selected_by_key.items()}


def _root_cause_rows(
    reliability_rows: Sequence[ReliabilityRow],
    selected_by_key: Mapping[tuple[str, str], tuple[CandidateRow, ...]],
    *,
    target_mz: Mapping[str, float],
    nl_ppm_max: float,
    apex_ms2_delta_max_min: float,
    nl_min_intensity_ratio: float,
) -> tuple[RootCauseRow, ...]:
    rows: list[RootCauseRow] = []
    for reliability in reliability_rows:
        if reliability.reliability_state != "targeted_review_positive":
            continue
        selected_rows = selected_by_key.get(
            (reliability.sample_name, reliability.target_label),
            (),
        )
        selected = selected_rows[0] if len(selected_rows) == 1 else None
        bucket, reason = _classify_root_cause(
            selected_rows,
            nl_ppm_max=nl_ppm_max,
            apex_ms2_delta_max_min=apex_ms2_delta_max_min,
            nl_min_intensity_ratio=nl_min_intensity_ratio,
        )
        rows.append(
            RootCauseRow(
                sample_name=reliability.sample_name,
                target_label=reliability.target_label,
                target_mz=target_mz.get(reliability.target_label),
                role=reliability.role,
                reliability_state=reliability.reliability_state,
                targeted_risk_reasons=";".join(reliability.risk_reasons),
                resolver_mode=selected.resolver_mode if selected else "",
                selected_candidate_id=selected.candidate_id if selected else "",
                selected_rt_apex_min=selected.rt_apex_min if selected else None,
                selected_raw_score=selected.raw_score if selected else None,
                selected_confidence=selected.confidence if selected else "",
                proposal_sources=(
                    ";".join(selected.proposal_sources) if selected else ""
                ),
                support_labels=";".join(selected.support_labels) if selected else "",
                concern_labels=";".join(selected.concern_labels) if selected else "",
                quality_flags=";".join(selected.quality_flags) if selected else "",
                ms2_present=selected.ms2_present if selected else None,
                nl_match=selected.nl_match if selected else None,
                nl_status=selected.nl_status if selected else "",
                best_loss_ppm=selected.best_loss_ppm if selected else None,
                best_ms2_scan_rt_min=(
                    selected.best_ms2_scan_rt_min if selected else None
                ),
                apex_ms2_delta_min=(selected.apex_ms2_delta_min if selected else None),
                best_product_base_ratio=(
                    selected.best_product_base_ratio if selected else None
                ),
                trigger_scan_count=selected.trigger_scan_count if selected else None,
                strict_nl_scan_count=(
                    selected.strict_nl_scan_count if selected else None
                ),
                ms2_alignment_source=(
                    selected.ms2_alignment_source if selected else ""
                ),
                diagnostic_product_absence_reason=(
                    selected.diagnostic_product_absence_reason if selected else ""
                ),
                nearest_product_loss_ppm=(
                    selected.nearest_product_loss_ppm if selected else None
                ),
                nearest_product_base_ratio=(
                    selected.nearest_product_base_ratio if selected else None
                ),
                nearest_product_mz=selected.nearest_product_mz if selected else None,
                root_cause_bucket=bucket,
                root_cause_reason=reason,
            )
        )
    return tuple(rows)


def _classify_root_cause(
    selected_rows: Sequence[CandidateRow],
    *,
    nl_ppm_max: float,
    apex_ms2_delta_max_min: float,
    nl_min_intensity_ratio: float,
) -> tuple[str, str]:
    if not selected_rows:
        return (
            "no_selected_candidate",
            "No selected peak candidate was found for this review-positive row.",
        )
    if len(selected_rows) > 1:
        return (
            "hard_candidate_conflict",
            "More than one selected candidate exists for this sample/target.",
        )
    selected = selected_rows[0]
    hard_labels = set(selected.concern_labels) & _HARD_CONFLICT_LABELS
    blocking_quality_flags = _blocking_quality_flags(selected)
    if hard_labels or blocking_quality_flags:
        reason = (
            f"Hard conflict labels: {','.join(sorted(hard_labels))}"
            if hard_labels
            else (
                "Candidate has blocking quality flags: "
                f"{','.join(blocking_quality_flags)}."
            )
        )
        return ("hard_candidate_conflict", reason)
    if selected.ms2_present is not True or selected.trigger_scan_count == 0:
        return (
            "no_ms2_trigger",
            "No usable MS2 trigger was recorded for the selected candidate.",
        )
    if selected.best_loss_ppm is None:
        detail = ""
        if selected.diagnostic_product_absence_reason:
            detail = f" Subcause: {selected.diagnostic_product_absence_reason}."
        nearest = ""
        if selected.nearest_product_loss_ppm is not None:
            nearest = (
                f" Nearest product loss ppm: {selected.nearest_product_loss_ppm:.6g}."
            )
        ratio = ""
        if selected.nearest_product_base_ratio is not None:
            ratio = (
                f" Nearest product/base ratio: "
                f"{selected.nearest_product_base_ratio:.6g}."
            )
        return (
            "no_diagnostic_product",
            (
                "No diagnostic product/loss ppm was available from MS2 evidence."
                f"{detail}{nearest}{ratio}"
            ),
        )
    if (
        selected.apex_ms2_delta_min is not None
        and selected.apex_ms2_delta_min > apex_ms2_delta_max_min
    ):
        return (
            "off_apex_ms2",
            (
                f"MS2 scan is {selected.apex_ms2_delta_min:.6g} min from apex, "
                f"above {apex_ms2_delta_max_min:.6g} min."
            ),
        )
    if selected.best_loss_ppm > nl_ppm_max:
        return (
            "ppm_gate_fail",
            (
                f"Best loss ppm {selected.best_loss_ppm:.6g} exceeds "
                f"nl_ppm_max {nl_ppm_max:.6g}."
            ),
        )
    weak_product_threshold = 2 * nl_min_intensity_ratio
    if (
        selected.best_product_base_ratio is not None
        and selected.best_product_base_ratio < weak_product_threshold
    ):
        return (
            "weak_product_ratio",
            (
                f"Product/base ratio {selected.best_product_base_ratio:.6g} is "
                f"below 2 * nl_min_intensity_ratio ({weak_product_threshold:.6g})."
            ),
        )
    return (
        "coherent_ms1_nl_dropout",
        "Selected candidate has coherent MS1 evidence and near-threshold NL dropout.",
    )


def _blocking_quality_flags(selected: CandidateRow) -> tuple[str, ...]:
    flags = set(selected.quality_flags)
    if not flags:
        return ()
    blocking = flags & _BLOCKING_TRACE_QUALITY_FLAGS
    hard = flags - _SOFT_TRACE_QUALITY_FLAGS
    if hard:
        blocking |= hard
    if blocking:
        return tuple(sorted(blocking))
    if _has_soft_trace_context(selected):
        return ()
    return tuple(sorted(flags))


def _has_soft_trace_context(selected: CandidateRow) -> bool:
    support = set(selected.support_labels)
    sources = set(selected.proposal_sources)
    concerns = set(selected.concern_labels)
    has_shape_context = (
        bool({"shape_clean", "cwt_same_apex_support"} & support)
        or "centwave_cwt" in sources
    )
    return (
        "local_sn_strong" in support
        and has_shape_context
        and "shape_poor" not in concerns
        and "local_sn_poor" not in concerns
    )


def _summary(
    reliability_rows: Sequence[ReliabilityRow],
    rows: Sequence[RootCauseRow],
) -> RootCauseSummary:
    review_positive_count = 0
    for reliability in reliability_rows:
        if reliability.reliability_state == "targeted_review_positive":
            review_positive_count += 1

    bucket_counts: Counter[str] = Counter()
    target_counts: Counter[str] = Counter()
    product_absence_counts: Counter[str] = Counter()
    for root_cause in rows:
        bucket_counts[root_cause.root_cause_bucket] += 1
        target_counts[root_cause.target_label] += 1
        if (
            root_cause.root_cause_bucket == "no_diagnostic_product"
            and root_cause.diagnostic_product_absence_reason
        ):
            product_absence_counts[
                root_cause.diagnostic_product_absence_reason
            ] += 1
    return RootCauseSummary(
        rows_checked=len(reliability_rows),
        review_positive_count=review_positive_count,
        included_count=len(rows),
        missing_candidate_count=bucket_counts["no_selected_candidate"],
        bucket_counts=_format_counter(bucket_counts),
        target_counts=_format_counter(target_counts),
        product_absence_reason_counts=_format_counter(product_absence_counts),
    )


def _format_counter(counter: Counter[str]) -> str:
    return ";".join(f"{key}:{counter[key]}" for key in sorted(counter))
