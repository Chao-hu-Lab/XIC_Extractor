from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Callable, Iterable

from tools.diagnostics.peak_candidate_score_calibration_io import _bool_value
from tools.diagnostics.peak_candidate_score_calibration_models import (
    _APEX_SHADOW_RT_WINDOW_MIN,
    PeakCandidateScoreRow,
    ScoreLabelImpactRow,
    ScoreRiskRow,
)
from xic_extractor.evidence_semantics import (
    EvidenceSignalSet,
    classify_evidence_consistency,
)


def _risk_rows(rows: tuple[PeakCandidateScoreRow, ...]) -> tuple[ScoreRiskRow, ...]:
    grouped: dict[str, list[PeakCandidateScoreRow]] = {}
    for row in rows:
        grouped.setdefault(row.group_id, []).append(row)
    risks: list[ScoreRiskRow] = []
    for _, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
        risks.extend(_group_risks(group_rows))
    return tuple(risks)


def _group_risks(rows: list[PeakCandidateScoreRow]) -> list[ScoreRiskRow]:
    selected = next((row for row in rows if row.selected), None)
    rejected = [row for row in rows if not row.selected]
    if selected is None:
        return []

    risks: list[ScoreRiskRow] = []
    if _selected_review_only(selected):
        risks.append(
            _risk_row(
                selected,
                "selected_review_only",
                challenger=None,
                reason="Selected candidate is review-only or VERY_LOW confidence.",
            )
        )
    if _selected_nl_fail(selected):
        risks.append(
            _risk_row(
                selected,
                "selected_nl_fail",
                challenger=None,
                reason="Selected candidate carries NL failure evidence.",
            )
        )
        if _plausible_nl_dropout(selected):
            risks.append(
                _risk_row(
                    selected,
                    "plausible_nl_dropout_selected",
                    challenger=None,
                    reason=(
                        "Selected row has strong MS1/shape support but lacks "
                        "the expected NL; treat as possible NL dropout context."
                    ),
                )
            )
    if _selected_no_ms2(selected):
        risks.append(
            _risk_row(
                selected,
                "selected_no_ms2",
                challenger=None,
                reason="Selected candidate lacks MS2 evidence.",
            )
        )

    apex_shadow = _best_challenger(
        rejected,
        lambda row: (
            _same_or_near_apex(selected, row)
            and _has_new_support(
                selected,
                row,
            )
        ),
    )
    if apex_shadow is not None:
        risks.append(
            _risk_row(
                selected,
                "apex_evidence_shadow",
                challenger=apex_shadow,
                reason=(
                    "Rejected near-apex row carries support labels not mirrored "
                    "on the selected row; treat as provenance/boundary context."
                ),
            )
        )

    alternative_rejected = [
        row for row in rejected if not _same_or_near_apex(selected, row)
    ]
    high_score = _best_challenger(
        alternative_rejected,
        lambda row: _score_greater(row.raw_score, selected.raw_score),
    )
    if high_score is not None:
        risks.append(
            _risk_row(
                selected,
                "high_score_rejected_challenger",
                challenger=high_score,
                reason="Rejected challenger has a higher raw score than selected.",
            )
        )

    strict_nl = _best_challenger(
        alternative_rejected,
        lambda row: (
            (
                "strict_nl_ok" in row.support_set
                and "strict_nl_ok" not in selected.support_set
            )
            or ("strict_nl_ok" in row.support_set and _selected_nl_fail(selected))
        ),
    )
    if strict_nl is not None:
        risks.append(
            _risk_row(
                selected,
                "strict_nl_rejected_challenger",
                challenger=strict_nl,
                reason=(
                    "Rejected challenger has strict NL support while selected does not."
                ),
            )
        )

    cwt_supported = _best_challenger(
        alternative_rejected,
        lambda row: "cwt_same_apex_support" in row.support_set,
    )
    if cwt_supported is not None:
        risks.append(
            _risk_row(
                selected,
                "cwt_supported_rejected_challenger",
                challenger=cwt_supported,
                reason="Rejected challenger has same-apex CWT support.",
            )
        )

    return risks


def _selected_review_only(row: PeakCandidateScoreRow) -> bool:
    reason = row.reason.lower()
    return row.confidence.strip().upper() == "VERY_LOW" or "review only" in reason


def _selected_nl_fail(row: PeakCandidateScoreRow) -> bool:
    return "nl_fail" in row.concern_set or _bool_value(row.nl_match) is False


def _selected_no_ms2(row: PeakCandidateScoreRow) -> bool:
    if "no_ms2" in row.concern_set:
        return True
    return (
        _bool_value(row.ms2_present) is False
        and "no_nl_required" not in row.support_set
    )


def _plausible_nl_dropout(row: PeakCandidateScoreRow) -> bool:
    return "plausible_nl_dropout" in classify_evidence_consistency(
        EvidenceSignalSet(
            support_labels=row.support_labels,
            concern_labels=(
                *row.concern_labels,
                *(() if _bool_value(row.nl_match) is not False else ("nl_fail",)),
            ),
            proposal_sources=tuple(row.source_set),
            ms2_present=_bool_value(row.ms2_present),
            nl_match=_bool_value(row.nl_match),
            raw_score=row.raw_score,
        )
    )


def _same_or_near_apex(
    left: PeakCandidateScoreRow,
    right: PeakCandidateScoreRow,
) -> bool:
    if left.rt_apex_min is None or right.rt_apex_min is None:
        return False
    return abs(left.rt_apex_min - right.rt_apex_min) <= _APEX_SHADOW_RT_WINDOW_MIN


def _has_new_support(
    selected: PeakCandidateScoreRow,
    challenger: PeakCandidateScoreRow,
) -> bool:
    return bool(challenger.support_set - selected.support_set) or _score_greater(
        challenger.raw_score,
        selected.raw_score,
    )


def _best_challenger(
    rows: Iterable[PeakCandidateScoreRow],
    predicate: Callable[[PeakCandidateScoreRow], bool],
) -> PeakCandidateScoreRow | None:
    matches = [row for row in rows if predicate(row)]
    if not matches:
        return None
    return max(matches, key=lambda row: _score_sort_value(row.raw_score))


def _score_greater(left: float | None, right: float | None) -> bool:
    return _score_sort_value(left) > _score_sort_value(right)


def _score_sort_value(value: float | None) -> float:
    if value is None:
        return float("-inf")
    return value


def _risk_row(
    selected: PeakCandidateScoreRow,
    risk_type: str,
    *,
    challenger: PeakCandidateScoreRow | None,
    reason: str,
) -> ScoreRiskRow:
    return ScoreRiskRow(
        group_id=selected.group_id,
        sample_name=selected.sample_name,
        target_label=selected.target_label,
        resolver_mode=selected.resolver_mode,
        risk_type=risk_type,
        selected_candidate_id=selected.candidate_id,
        selected_rt_apex_min=selected.rt_apex_min,
        selected_raw_score=selected.raw_score,
        selected_confidence=selected.confidence,
        selected_support_labels=";".join(selected.support_labels),
        selected_concern_labels=";".join(selected.concern_labels),
        challenger_candidate_id=challenger.candidate_id if challenger else "",
        challenger_rt_apex_min=challenger.rt_apex_min if challenger else None,
        challenger_raw_score=challenger.raw_score if challenger else None,
        challenger_confidence=challenger.confidence if challenger else "",
        challenger_support_labels=";".join(challenger.support_labels)
        if challenger
        else "",
        challenger_concern_labels=";".join(challenger.concern_labels)
        if challenger
        else "",
        reason=reason,
    )


def _label_impact(
    rows: tuple[PeakCandidateScoreRow, ...],
) -> tuple[ScoreLabelImpactRow, ...]:
    buckets: dict[tuple[str, str], list[PeakCandidateScoreRow]] = {}
    for row in rows:
        for label in row.support_labels:
            buckets.setdefault(("support", label), []).append(row)
        for label in row.concern_labels:
            buckets.setdefault(("concern", label), []).append(row)
        for label in row.cap_labels:
            buckets.setdefault(("cap", label), []).append(row)

    label_rows = tuple(
        _label_impact_row(kind, label, label_rows)
        for (kind, label), label_rows in buckets.items()
    )
    return tuple(
        sorted(
            label_rows,
            key=lambda row: (
                row.label_kind,
                -(row.selected_count + row.rejected_count),
                row.label,
            ),
        )
    )


def _label_impact_row(
    label_kind: str,
    label: str,
    rows: list[PeakCandidateScoreRow],
) -> ScoreLabelImpactRow:
    selected_scores = [row.raw_score for row in rows if row.selected]
    rejected_scores = [row.raw_score for row in rows if not row.selected]
    selected_count = len(selected_scores)
    rejected_count = len(rejected_scores)
    total = selected_count + rejected_count
    return ScoreLabelImpactRow(
        label_kind=label_kind,
        label=label,
        selected_count=selected_count,
        rejected_count=rejected_count,
        selected_rate=selected_count / total if total else None,
        selected_median_raw_score=_median_score(selected_scores),
        rejected_median_raw_score=_median_score(rejected_scores),
    )


def _summary(
    rows: tuple[PeakCandidateScoreRow, ...],
    risk_rows: tuple[ScoreRiskRow, ...],
) -> dict[str, int]:
    group_ids = {row.group_id for row in rows}
    risk_group_counts = _risk_group_counts(risk_rows)
    return {
        "candidate_row_count": len(rows),
        "candidate_group_count": len(group_ids),
        "selected_row_count": sum(row.selected for row in rows),
        "rejected_row_count": sum(not row.selected for row in rows),
        "selected_review_only_count": risk_group_counts["selected_review_only"],
        "selected_nl_fail_count": risk_group_counts["selected_nl_fail"],
        "selected_no_ms2_count": risk_group_counts["selected_no_ms2"],
        "plausible_nl_dropout_selected_count": risk_group_counts[
            "plausible_nl_dropout_selected"
        ],
        "apex_evidence_shadow_group_count": risk_group_counts["apex_evidence_shadow"],
        "high_score_rejected_challenger_group_count": risk_group_counts[
            "high_score_rejected_challenger"
        ],
        "strict_nl_rejected_challenger_group_count": risk_group_counts[
            "strict_nl_rejected_challenger"
        ],
        "cwt_supported_rejected_challenger_group_count": risk_group_counts[
            "cwt_supported_rejected_challenger"
        ],
    }


def _risk_group_counts(risk_rows: tuple[ScoreRiskRow, ...]) -> Counter[str]:
    risk_groups: dict[str, set[str]] = {}
    for row in risk_rows:
        risk_groups.setdefault(row.risk_type, set()).add(row.group_id)
    return Counter(
        {risk_type: len(group_ids) for risk_type, group_ids in risk_groups.items()}
    )


def _recommendations(
    summary: dict[str, int],
    risk_rows: tuple[ScoreRiskRow, ...],
) -> tuple[str, ...]:
    recommendations: list[str] = []
    if summary["apex_evidence_shadow_group_count"]:
        recommendations.append(
            "Resolve near-apex audit/provenance shadows before treating rejected "
            "CWT rows as true alternative peaks."
        )
    if summary["strict_nl_rejected_challenger_group_count"]:
        recommendations.append(
            "Rebalance NL evidence before changing generic raw-score thresholds."
        )
    if summary["cwt_supported_rejected_challenger_group_count"]:
        recommendations.append(
            "Treat CWT same-apex support as a bounded positive signal only when "
            "chemical evidence is present."
        )
    if summary["selected_review_only_count"] or summary["selected_nl_fail_count"]:
        recommendations.append(
            "Keep weak targeted evidence visible in review, but do not count it as "
            "a clean positive for benchmark denominators."
        )
    if summary["plausible_nl_dropout_selected_count"]:
        recommendations.append(
            "Review plausible NL-dropout rows separately before weakening the "
            "global NL-fail cap."
        )
    if not recommendations and not risk_rows:
        recommendations.append("No scoring conflicts detected in this input.")
    return tuple(recommendations)


def _median_score(values: Iterable[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return float(statistics.median(numeric))
