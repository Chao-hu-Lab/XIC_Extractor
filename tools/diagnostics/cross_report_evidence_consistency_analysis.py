from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from tools.diagnostics.cross_report_evidence_consistency_models import (
    CandidateRow,
    ConsistencyRow,
    ConsistencySummary,
    ReliabilityRow,
)
from xic_extractor.evidence_semantics import (
    EvidenceSignalSet,
    classify_evidence_consistency,
)


def _consistency_rows(
    reliability_rows: tuple[ReliabilityRow, ...],
    candidate_rows: tuple[CandidateRow, ...],
    *,
    target_mz: Mapping[str, float],
) -> tuple[ConsistencyRow, ...]:
    reliability_by_key = {
        (row.sample_name, row.target_label): row for row in reliability_rows
    }
    selected_by_key: dict[tuple[str, str], list[CandidateRow]] = {}
    for row in candidate_rows:
        if row.selected:
            selected_by_key.setdefault((row.sample_name, row.target_label), []).append(
                row
            )
    keys = sorted(set(reliability_by_key) | set(selected_by_key))
    rows: list[ConsistencyRow] = []
    for key in keys:
        reliability = reliability_by_key.get(key)
        selected_rows = selected_by_key.get(key, [])
        if not selected_rows:
            if reliability is not None:
                rows.append(
                    _consistency_row(
                        reliability,
                        None,
                        target_mz=target_mz.get(reliability.target_label),
                    )
                )
            continue
        if reliability is None:
            for selected in selected_rows:
                rows.append(
                    _consistency_row(
                        None,
                        selected,
                        target_mz=target_mz.get(selected.target_label),
                    )
                )
            continue
        for selected in selected_rows:
            rows.append(
                _consistency_row(
                    reliability,
                    selected,
                    target_mz=target_mz.get(reliability.target_label),
                    multiple_selected=len(selected_rows) > 1,
                )
            )
    return tuple(rows)


def _consistency_row(
    reliability: ReliabilityRow | None,
    selected: CandidateRow | None,
    *,
    target_mz: float | None,
    multiple_selected: bool = False,
) -> ConsistencyRow:
    state = reliability.reliability_state if reliability is not None else ""
    risk_reasons = reliability.risk_reasons if reliability is not None else ()
    consistency = _candidate_consistency(selected)
    status, issue, reason = _classify_consistency(
        reliability,
        selected,
        consistency,
        multiple_selected=multiple_selected,
    )
    sample = (
        reliability.sample_name
        if reliability is not None
        else selected.sample_name
        if selected is not None
        else ""
    )
    target = (
        reliability.target_label
        if reliability is not None
        else selected.target_label
        if selected is not None
        else ""
    )
    return ConsistencyRow(
        sample_name=sample,
        target_label=target,
        target_mz=target_mz,
        reliability_state=state,
        targeted_risk_reasons=";".join(risk_reasons),
        resolver_mode=selected.resolver_mode if selected is not None else "",
        selected_candidate_id=selected.candidate_id if selected is not None else "",
        selected_rt_apex_min=selected.rt_apex_min if selected is not None else None,
        selected_raw_score=selected.raw_score if selected is not None else None,
        selected_confidence=selected.confidence if selected is not None else "",
        targeted_area_to_median_ratio=(
            reliability.area_to_target_median_ratio if reliability is not None else None
        ),
        candidate_support_labels=(
            ";".join(selected.support_labels) if selected is not None else ""
        ),
        candidate_concern_labels=(
            ";".join(selected.concern_labels) if selected is not None else ""
        ),
        candidate_consistency_labels=";".join(consistency),
        consistency_status=status,
        issue_type=issue,
        reason=reason,
    )


def _candidate_consistency(selected: CandidateRow | None) -> tuple[str, ...]:
    if selected is None:
        return ()
    return classify_evidence_consistency(
        EvidenceSignalSet(
            support_labels=selected.support_labels,
            concern_labels=selected.concern_labels,
            proposal_sources=selected.proposal_sources,
            quality_flags=selected.quality_flags,
            ms2_present=selected.ms2_present,
            nl_match=selected.nl_match,
            raw_score=selected.raw_score,
        )
    )


def _classify_consistency(
    reliability: ReliabilityRow | None,
    selected: CandidateRow | None,
    consistency: tuple[str, ...],
    *,
    multiple_selected: bool,
) -> tuple[str, str, str]:
    labels = set(consistency)
    if reliability is None:
        return (
            "mismatch",
            "missing_targeted_reliability",
            "Selected candidate has no matching targeted reliability row.",
        )
    if selected is None:
        if reliability.reliability_state == "targeted_negative":
            return (
                "consistent",
                "",
                "",
            )
        return (
            "mismatch",
            "missing_selected_candidate",
            "Targeted reliability row has no selected peak candidate row.",
        )
    if multiple_selected:
        return (
            "mismatch",
            "multiple_selected_candidates",
            "More than one selected candidate exists for this sample/target.",
        )
    state = reliability.reliability_state
    if state == "benchmark_eligible" and labels & {
        "hard_nl_conflict",
        "missing_ms2",
    }:
        return (
            "mismatch",
            "targeted_clean_candidate_conflict",
            "Targeted reliability says clean, but selected candidate has "
            "hard conflict labels.",
        )
    if state == "targeted_review_positive" and "plausible_nl_dropout" not in labels:
        return (
            "mismatch",
            "review_positive_not_supported_by_candidate",
            "Targeted review-positive state is not supported by selected "
            "candidate consistency labels.",
        )
    if (
        state == "targeted_review"
        and "plausible_nl_dropout" in labels
        and "hard_nl_conflict" not in labels
    ):
        if _has_review_positive_blocker(reliability.risk_reasons):
            return ("consistent", "", "")
        return (
            "mismatch",
            "targeted_review_candidate_suggests_dropout",
            "Targeted review row may be a stronger review-positive dropout case.",
        )
    if state == "targeted_negative" and "ms1_coherent" in labels:
        return (
            "mismatch",
            "targeted_negative_candidate_has_peak",
            "Targeted negative row has a coherent selected candidate peak.",
        )
    return ("consistent", "", "")


def _has_review_positive_blocker(risk_reasons: Sequence[str]) -> bool:
    blockers = {
        "hard_nl_conflict",
        "no_ms2",
        "quality_flags",
        "weak_area_rank",
    }
    return any(reason in blockers for reason in risk_reasons)


def _summary(rows: tuple[ConsistencyRow, ...]) -> ConsistencySummary:
    issues = Counter(row.issue_type for row in rows if row.issue_type)
    return ConsistencySummary(
        rows_checked=len(rows),
        consistent_count=sum(row.consistency_status == "consistent" for row in rows),
        mismatch_count=sum(row.consistency_status == "mismatch" for row in rows),
        missing_candidate_count=issues["missing_selected_candidate"],
        missing_reliability_count=issues["missing_targeted_reliability"],
        issue_counts=";".join(f"{issue}:{count}" for issue, count in issues.items()),
    )
