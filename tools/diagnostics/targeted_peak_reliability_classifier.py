"""Reliability classification for targeted peak reliability audit."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import median

from tools.diagnostics.targeted_peak_reliability_models import (
    _BLOCKING_TRACE_QUALITY_FLAGS,
    _COHERENT_ISTD_SOFT_TRACE_MIN_RAW_SCORE,
    _SOFT_TRACE_QUALITY_FLAGS,
    ReliabilityState,
    TargetedReliabilityRow,
    TargetedReliabilitySummary,
    _AreaContext,
    _CandidateEvidence,
    _ScoreBreakdown,
    _TargetedInputRow,
)
from xic_extractor.evidence_semantics import (
    EvidenceSignalSet,
    classify_evidence_consistency,
)


def _classify_row(
    row: _TargetedInputRow,
    *,
    score: _ScoreBreakdown | None,
    candidate_evidence: _CandidateEvidence | None,
    known_exception: str,
    area_context: _AreaContext | None,
) -> TargetedReliabilityRow:
    if row.rt is None or row.area is None or row.area <= 0:
        return TargetedReliabilityRow(
            sample_name=row.sample_name,
            target_label=row.target_label,
            role=row.role,
            rt=row.rt,
            area=row.area,
            confidence=row.confidence,
            nl=row.nl,
            prior_rt=score.prior_rt if score is not None else None,
            prior_source=score.prior_source if score is not None else "",
            total_severity=score.total_severity if score is not None else None,
            quality_flags=score.quality_flags if score is not None else "",
            reliability_state="targeted_negative",
            risk_reasons=("no_usable_peak",),
            known_exception=known_exception,
            target_area_median=(
                area_context.target_area_median if area_context is not None else None
            ),
            area_to_target_median_ratio=(
                area_context.area_to_target_median_ratio
                if area_context is not None
                else None
            ),
            weak_area_threshold_ratio=(
                area_context.weak_area_threshold_ratio
                if area_context is not None
                else None
            ),
        )

    coherent_istd_soft_trace = _is_coherent_istd_soft_trace_candidate(
        row,
        score,
        candidate_evidence,
        area_context,
    )

    risk_reasons: list[str] = []
    if row.confidence == "VERY_LOW" or (
        row.confidence == "LOW" and not _is_accepted_low_istd(row)
    ):
        if not coherent_istd_soft_trace:
            risk_reasons.append("low_confidence")
    if _is_nl_fail(row.nl):
        if _is_plausible_nl_dropout(row, score, candidate_evidence):
            risk_reasons.append("plausible_nl_dropout")
        else:
            risk_reasons.append("hard_nl_conflict")
    elif _is_no_ms2(row.nl):
        risk_reasons.append("no_ms2")
    if score is None:
        risk_reasons.append("score_breakdown_unavailable")
    elif _has_blocking_quality_flags(
        score.quality_flags,
        candidate_evidence=candidate_evidence,
    ):
        if not coherent_istd_soft_trace:
            risk_reasons.append("quality_flags")
    if area_context is not None and area_context.weak_area:
        risk_reasons.append("weak_area_rank")
    if _is_nl_fail(row.nl) and candidate_evidence is not None:
        risk_reasons.extend(_candidate_product_context_reasons(candidate_evidence))

    blocking_reasons = tuple(
        reason for reason in risk_reasons if reason != "score_breakdown_unavailable"
    )
    if not blocking_reasons:
        state: ReliabilityState = "benchmark_eligible"
    elif _is_review_positive(blocking_reasons):
        state = "targeted_review_positive"
    else:
        state = "targeted_review"
    return TargetedReliabilityRow(
        sample_name=row.sample_name,
        target_label=row.target_label,
        role=row.role,
        rt=row.rt,
        area=row.area,
        confidence=row.confidence,
        nl=row.nl,
        prior_rt=score.prior_rt if score is not None else None,
        prior_source=score.prior_source if score is not None else "",
        total_severity=score.total_severity if score is not None else None,
        quality_flags=score.quality_flags if score is not None else "",
        reliability_state=state,
        risk_reasons=tuple(dict.fromkeys(risk_reasons)),
        known_exception=known_exception,
        target_area_median=(
            area_context.target_area_median if area_context is not None else None
        ),
        area_to_target_median_ratio=(
            area_context.area_to_target_median_ratio
            if area_context is not None
            else None
        ),
        weak_area_threshold_ratio=(
            area_context.weak_area_threshold_ratio if area_context is not None else None
        ),
    )


def _area_context_by_key(
    rows: Sequence[_TargetedInputRow],
) -> dict[tuple[str, str], _AreaContext]:
    by_target: dict[str, list[_TargetedInputRow]] = defaultdict(list)
    for row in rows:
        if row.area is not None and row.area > 0:
            by_target[row.target_label].append(row)
    context: dict[tuple[str, str], _AreaContext] = {}
    for target_rows in by_target.values():
        if len(target_rows) < 3:
            continue
        target_median = median(float(row.area) for row in target_rows if row.area)
        if target_median <= 0:
            continue
        for row in target_rows:
            if row.area is None:
                continue
            context[(row.sample_name, row.target_label)] = _AreaContext(
                target_area_median=float(target_median),
                area_to_target_median_ratio=float(row.area) / float(target_median),
            )
    return context


def _summarize_rows(
    rows: Sequence[TargetedReliabilityRow],
) -> tuple[TargetedReliabilitySummary, ...]:
    by_target: dict[str, _TargetReliabilitySummaryBuilder] = {}
    for row in rows:
        builder = by_target.get(row.target_label)
        if builder is None:
            builder = _TargetReliabilitySummaryBuilder(role=row.role)
            by_target[row.target_label] = builder
        builder.add(row)
    return tuple(
        by_target[target_label].to_summary(target_label)
        for target_label in sorted(by_target)
    )


@dataclass
class _TargetReliabilitySummaryBuilder:
    role: str
    benchmark_eligible_count: int = 0
    targeted_review_positive_count: int = 0
    targeted_review_count: int = 0
    targeted_negative_count: int = 0
    reasons: Counter[str] = field(default_factory=Counter)
    known_exception: str = ""

    def add(self, row: TargetedReliabilityRow) -> None:
        if row.reliability_state == "benchmark_eligible":
            self.benchmark_eligible_count += 1
        elif row.reliability_state == "targeted_review_positive":
            self.targeted_review_positive_count += 1
        elif row.reliability_state == "targeted_review":
            self.targeted_review_count += 1
        elif row.reliability_state == "targeted_negative":
            self.targeted_negative_count += 1
        self.reasons.update(row.risk_reasons)
        if not self.known_exception and row.known_exception:
            self.known_exception = row.known_exception

    def to_summary(self, target_label: str) -> TargetedReliabilitySummary:
        top_reasons = ";".join(
            reason for reason, _count in self.reasons.most_common(5)
        )
        return TargetedReliabilitySummary(
            target_label=target_label,
            role=self.role,
            benchmark_eligible_count=self.benchmark_eligible_count,
            targeted_review_positive_count=self.targeted_review_positive_count,
            targeted_review_count=self.targeted_review_count,
            targeted_negative_count=self.targeted_negative_count,
            top_risk_reasons=top_reasons,
            known_exception=self.known_exception,
        )


def _is_nl_fail(value: str) -> bool:
    token = value.strip().upper()
    return token == "NL_FAIL" or "NL_FAIL" in token or token.startswith("✗")


def _is_no_ms2(value: str) -> bool:
    token = value.strip().upper().replace(" ", "_")
    return token == "NO_MS2" or "NO_MS2" in token


def _is_review_positive(blocking_reasons: Sequence[str]) -> bool:
    if "plausible_nl_dropout" not in blocking_reasons:
        return False
    hard_reasons = {
        "hard_nl_conflict",
        "no_ms2",
        "quality_flags",
        "weak_area_rank",
    }
    return not any(reason in hard_reasons for reason in blocking_reasons)


def _is_plausible_nl_dropout(
    row: _TargetedInputRow,
    score: _ScoreBreakdown | None,
    candidate_evidence: _CandidateEvidence | None,
) -> bool:
    if candidate_evidence is not None:
        return "plausible_nl_dropout" in classify_evidence_consistency(
            _candidate_evidence_signal_set(candidate_evidence)
        )
    return "plausible_nl_dropout" in classify_evidence_consistency(
        _evidence_signal_set(row, score)
    )


def _candidate_evidence_signal_set(
    evidence: _CandidateEvidence,
) -> EvidenceSignalSet:
    return EvidenceSignalSet(
        support_labels=evidence.support_labels,
        concern_labels=evidence.concern_labels,
        proposal_sources=evidence.proposal_sources,
        quality_flags=evidence.quality_flags,
        ms2_present=evidence.ms2_present,
        nl_match=evidence.nl_match,
        raw_score=evidence.raw_score,
    )


def _candidate_product_context_reasons(
    evidence: _CandidateEvidence,
) -> tuple[str, ...]:
    if not evidence.diagnostic_product_absence_reason:
        return ()
    return (evidence.diagnostic_product_absence_reason,)


def _has_blocking_quality_flags(
    quality_flags: str,
    *,
    candidate_evidence: _CandidateEvidence | None,
) -> bool:
    flags = set(_split_semicolon_labels(quality_flags))
    if not flags:
        return False
    if flags & _BLOCKING_TRACE_QUALITY_FLAGS:
        return True
    hard_flags = flags - _SOFT_TRACE_QUALITY_FLAGS
    if hard_flags:
        return True
    if candidate_evidence is None:
        return True
    return not _has_soft_trace_support_context(candidate_evidence)


def _has_soft_trace_support_context(evidence: _CandidateEvidence) -> bool:
    support = set(evidence.support_labels)
    sources = set(evidence.proposal_sources)
    concerns = set(evidence.concern_labels)
    has_shape_context = (
        bool({"shape_clean", "cwt_same_apex_support"} & support)
        or "centwave_cwt" in sources
    )
    return (
        evidence.ms2_present is True
        and evidence.nl_match is True
        and "strict_nl_ok" in support
        and "local_sn_strong" in support
        and has_shape_context
        and "shape_poor" not in concerns
        and "local_sn_poor" not in concerns
    )


def _is_coherent_istd_soft_trace_candidate(
    row: _TargetedInputRow,
    score: _ScoreBreakdown | None,
    candidate_evidence: _CandidateEvidence | None,
    area_context: _AreaContext | None,
) -> bool:
    if row.role.strip().upper() != "ISTD":
        return False
    if row.rt is None or row.area is None or row.area <= 0:
        return False
    if _is_nl_fail(row.nl) or _is_no_ms2(row.nl):
        return False
    if area_context is not None and area_context.weak_area:
        return False
    if candidate_evidence is None:
        return False
    if candidate_evidence.ms2_present is not True:
        return False
    if candidate_evidence.nl_match is not True:
        return False
    if candidate_evidence.raw_score is None:
        return False
    if candidate_evidence.raw_score < _COHERENT_ISTD_SOFT_TRACE_MIN_RAW_SCORE:
        return False

    support = set(candidate_evidence.support_labels)
    if not {"strict_nl_ok", "local_sn_strong"} <= support:
        return False

    flags = set(candidate_evidence.quality_flags)
    if score is not None:
        flags.update(_split_semicolon_labels(score.quality_flags))
    if flags & _BLOCKING_TRACE_QUALITY_FLAGS:
        return False
    if flags - _SOFT_TRACE_QUALITY_FLAGS:
        return False

    concerns = set(candidate_evidence.concern_labels)
    hard_concerns = {
        "hard_quality_flag",
        "low_scan_support",
        "nl_fail",
        "no_ms2",
        "local_sn_poor",
    }
    return not bool(concerns & hard_concerns)


def _is_accepted_low_istd(row: _TargetedInputRow) -> bool:
    reason = row.reason.upper()
    if any(
        token in reason
        for token in ("HARD QUALITY FLAG", "WEAK CANDIDATE", "NL FAIL", "NO MS2")
    ):
        return False
    return (
        row.role.strip().upper() == "ISTD"
        and row.confidence == "LOW"
        and not _is_nl_fail(row.nl)
        and not _is_no_ms2(row.nl)
        and "DECISION: ACCEPTED" in reason
    )


def _evidence_signal_set(
    row: _TargetedInputRow,
    score: _ScoreBreakdown | None,
) -> EvidenceSignalSet:
    reason = row.reason.upper()
    support_labels: list[str] = []
    concern_labels: list[str] = []
    proposal_sources: list[str] = []
    if "LOCAL S/N STRONG" in reason:
        support_labels.append("local_sn_strong")
    if "TRACE CLEAN" in reason:
        support_labels.append("trace_clean")
    if "SHAPE CLEAN" in reason:
        support_labels.append("shape_clean")
    if "CENTWAVE_CWT" in reason:
        proposal_sources.append("centwave_cwt")
    if _is_nl_fail(row.nl):
        concern_labels.append("nl_fail")
    if _is_no_ms2(row.nl) or "NO MS2" in reason or "NO_MS2" in reason:
        concern_labels.append("no_ms2")
    concern_labels.extend(_reason_hard_concern_labels(reason))
    return EvidenceSignalSet(
        support_labels=tuple(dict.fromkeys(support_labels)),
        concern_labels=tuple(dict.fromkeys(concern_labels)),
        proposal_sources=tuple(dict.fromkeys(proposal_sources)),
        quality_flags=(
            tuple(_split_semicolon_labels(score.quality_flags))
            if score is not None
            else ()
        ),
        ms2_present=False
        if "no_ms2" in concern_labels
        else True
        if _is_nl_fail(row.nl)
        else None,
        nl_match=False if _is_nl_fail(row.nl) else None,
    )


def _reason_hard_concern_labels(reason: str) -> list[str]:
    labels: list[str] = []
    for token, label in (
        ("HARD QUALITY FLAG", "hard_quality_flag"),
        ("WEAK CANDIDATE", "hard_quality_flag"),
        ("LOW SCAN SUPPORT", "low_scan_support"),
        ("LOW_TRACE_CONTINUITY", "low_trace_continuity"),
        ("LOW TRACE CONTINUITY", "low_trace_continuity"),
        ("POOR EDGE RECOVERY", "poor_edge_recovery"),
        ("EDGE CLIPPED", "poor_edge_recovery"),
        ("RT CENTRALITY POOR", "rt_centrality_poor"),
        ("RT_CENTRALITY_POOR", "rt_centrality_poor"),
        ("SHAPE POOR", "shape_poor"),
        ("SHAPE_POOR", "shape_poor"),
    ):
        if token in reason:
            labels.append(label)
    return labels


def _split_semicolon_labels(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]
