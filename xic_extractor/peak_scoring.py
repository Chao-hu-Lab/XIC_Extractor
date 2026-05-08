"""Tier-based peak scoring. Each signal returns (severity, label)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from xic_extractor.baseline import asls_baseline
from xic_extractor.peak_scoring_evidence import (
    ConfidenceCap,
    EvidenceScore,
    EvidenceSignal,
    score_evidence,
)

_LABEL_SYMMETRY = "symmetry"
_LABEL_LOCAL_SN = "local_sn"
_LABEL_NL = "nl_support"
_LABEL_RT_PRIOR = "rt_prior"
_LABEL_RT_CENTRALITY = "rt_centrality"
_LABEL_NOISE_SHAPE = "noise_shape"
_LABEL_PEAK_WIDTH = "peak_width"

_SYMMETRY_SOFT_LOW, _SYMMETRY_SOFT_HIGH = 0.5, 2.0
_SYMMETRY_HARD_LOW, _SYMMETRY_HARD_HIGH = 0.3, 3.0
_SN_SOFT_THRESHOLD = 3.0
_SN_HARD_THRESHOLD = 2.0
_SN_DIRTY_SOFT_THRESHOLD = 2.0
_SN_DIRTY_HARD_THRESHOLD = 1.3
_RT_PRIOR_SIGMA_SOFT = 2.0
_RT_PRIOR_SIGMA_HARD = 5.0
_RT_PRIOR_NO_SIGMA_SOFT_MIN = 0.2
_RT_PRIOR_NO_SIGMA_HARD_MIN = 1.0
_ADAP_LIKE_FLAG_LABELS = {
    "low_scan_support": "low scan support",
    "low_trace_continuity": "low trace continuity",
    "poor_edge_recovery": "poor edge recovery",
}
_ADAP_LIKE_SELECTION_WEIGHT = 0.25
_ADAP_LIKE_SELECTION_MAX = 0.5
_SELECTION_QUALITY_DISTANCE_WEIGHT_MIN = 0.05
_SELECTION_DISTANCE_POINTS_PER_MIN = 60.0
_SELECTION_QUALITY_POINTS_PER_UNIT = 10.0
_SELECTION_FAR_DISTANCE_MAX_MIN = 0.75
_LOW_SCAN_DEMOTION_SCORE_PENALTY = 80.0
_LOW_SCAN_STRONGER_CANDIDATE_INTENSITY_RATIO = 2.0
_LOW_SCAN_STRONGER_CANDIDATE_AREA_RATIO = 15.0
_LOW_SCAN_MAX_CONFIDENCE_RANK_GAP = 1
_LOW_SCAN_CONFIDENCE_DEMOTION = 2
_LOW_SCAN_STRONGER_CANDIDATE_MAX_SELECTION_DISTANCE_MIN = 0.35
_LOW_SCAN_STRONGER_CANDIDATE_EXTENDED_DISTANCE_MIN = 2.5
_DOMINANT_STRICT_NL_AREA_RATIO = 100.0
_DOMINANT_STRICT_NL_MAX_SELECTION_DISTANCE_MIN = 3.0
_DOMINANT_STRICT_NL_DEMOTION_SCORE_PENALTY = 200.0
_ADAP_EQUIVALENT_LEGACY_FLAGS = {
    "low_scan_support": "low_scan_count",
    "poor_edge_recovery": "low_top_edge_ratio",
}


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Any
    severities: tuple[tuple[int, str], ...]
    confidence: Confidence
    reason: str
    prior_rt: float | None
    quality_penalty: int = 0
    selection_quality_penalty: float | None = None
    prefer_rt_prior_tiebreak: bool = False
    evidence_score: EvidenceScore | None = None


@dataclass(frozen=True)
class ScoringContext:
    rt_array: np.ndarray
    intensity_array: np.ndarray
    apex_index: int
    half_width_ratio: float
    fwhm_ratio: float | None
    ms2_present: bool
    nl_match: bool
    rt_prior: float | None
    rt_prior_sigma: float | None
    rt_min: float
    rt_max: float
    dirty_matrix: bool
    neutral_loss_required: bool = True
    baseline_array: np.ndarray | None = None
    residual_mad: float | None = None
    prefer_rt_prior_tiebreak: bool = False


_CONFIDENCE_RANK = {
    Confidence.HIGH: 0,
    Confidence.MEDIUM: 1,
    Confidence.LOW: 2,
    Confidence.VERY_LOW: 3,
}


def confidence_from_total(total_severity: int) -> Confidence:
    if total_severity == 0:
        return Confidence.HIGH
    if total_severity <= 2:
        return Confidence.MEDIUM
    if total_severity <= 4:
        return Confidence.LOW
    return Confidence.VERY_LOW


def _confidence_from_value(value: str) -> Confidence:
    return Confidence(value)


def build_reason(
    signals: list[tuple[int, str]],
    istd_confidence_note: str | None,
    extra_notes: list[str] | None = None,
) -> str:
    concerns = [(severity, label) for severity, label in signals if severity >= 1]
    if not concerns and istd_confidence_note is None and not extra_notes:
        return "all checks passed"

    parts: list[str] = []
    if concerns:
        concerns.sort(key=lambda pair: -pair[0])
        phrase = "; ".join(
            f"{label} ({'major' if severity == 2 else 'minor'})"
            for severity, label in concerns
        )
        parts.append(f"concerns: {phrase}")
    if extra_notes:
        parts.extend(extra_notes)
    if istd_confidence_note is not None:
        parts.append(istd_confidence_note)
    return "; ".join(parts)


_EVIDENCE_REASON_LABELS = {
    "strict_nl_ok": "strict NL OK",
    "no_nl_required": "no NL required",
    "rt_prior_close": "RT prior close",
    "paired_istd_aligned": "paired ISTD aligned",
    "local_sn_strong": "local S/N strong",
    "shape_clean": "shape clean",
    "trace_clean": "trace clean",
    "nl_fail": "nl fail",
    "no_ms2": "no MS2",
    "rt_prior_far": "rt prior far",
    "rt_prior_borderline": "rt prior borderline",
    "rt_centrality_borderline": "RT centrality borderline",
    "rt_centrality_poor": "RT centrality poor",
    "local_sn_borderline": "local S/N borderline",
    "local_sn_poor": "local S/N poor",
    "shape_borderline": "shape borderline",
    "shape_poor": "shape poor",
    "noise_shape_borderline": "noise shape borderline",
    "noise_shape_poor": "noise shape poor",
    "anchor_mismatch": "anchor mismatch",
    "low_scan_support": "low scan support",
    "low_trace_continuity": "low trace continuity",
    "poor_edge_recovery": "poor edge recovery",
    "hard_quality_flag": "hard quality flag",
}

_CAP_REASON_LABELS = {
    "nl_fail_cap": ("VERY_LOW", "nl fail"),
    "no_ms2_cap": ("LOW", "no MS2"),
    "anchor_mismatch_cap": ("VERY_LOW", "anchor mismatch"),
    "zero_area_cap": ("VERY_LOW", "zero area"),
    "rt_window_cap": ("VERY_LOW", "target RT window"),
    "trace_quality_cap": ("MEDIUM", "trace quality"),
    "hard_quality_flag_cap": ("MEDIUM", "hard quality flag"),
}


def build_evidence_reason(
    evidence_score: EvidenceScore,
    istd_confidence_note: str | None,
    extra_notes: list[str] | None = None,
) -> str:
    parts: list[str] = []
    if evidence_score.confidence == Confidence.VERY_LOW.value:
        parts.append("decision: review only, not counted")
    else:
        parts.append("decision: accepted")

    for cap in evidence_score.cap_labels:
        max_confidence, cap_name = _CAP_REASON_LABELS.get(
            cap, ("VERY_LOW", cap.removesuffix("_cap").replace("_", " "))
        )
        parts.append(f"cap: {max_confidence} due to {cap_name}")

    if evidence_score.support_labels:
        support = "; ".join(
            _EVIDENCE_REASON_LABELS.get(label, label)
            for label in evidence_score.support_labels[:3]
        )
        parts.append(f"support: {support}")

    if evidence_score.concern_labels:
        concerns = "; ".join(
            _EVIDENCE_REASON_LABELS.get(label, label)
            for label in evidence_score.concern_labels[:4]
        )
        parts.append(f"concerns: {concerns}")

    if extra_notes:
        parts.extend(extra_notes)

    if istd_confidence_note is not None:
        parts.append(istd_confidence_note)

    return "; ".join(parts) if parts else "all checks passed"


def select_candidate_with_confidence(
    scored: list[ScoredCandidate],
    *,
    selection_rt: float | None = None,
    strict_selection_rt: bool = False,
) -> ScoredCandidate:
    if not scored:
        raise ValueError(
            "select_candidate_with_confidence requires at least one candidate"
        )

    low_scan_demotions = set()
    dominant_area_demotions = set()
    if not strict_selection_rt:
        low_scan_demotions = _low_scan_demotion_ids(
            scored,
            selection_rt=selection_rt,
        )
        dominant_area_demotions = _dominant_area_demotion_ids(
            scored,
            selection_rt=selection_rt,
        )
    selection_demotion_penalties = {
        candidate_id: _LOW_SCAN_DEMOTION_SCORE_PENALTY
        for candidate_id in low_scan_demotions
    }
    for candidate_id in dominant_area_demotions:
        selection_demotion_penalties[candidate_id] = max(
            selection_demotion_penalties.get(candidate_id, 0.0),
            _DOMINANT_STRICT_NL_DEMOTION_SCORE_PENALTY,
        )

    def key(
        scored_candidate: ScoredCandidate,
    ) -> tuple[float, float, float, float, float]:
        candidate = scored_candidate.candidate
        selection_reference = selection_rt
        if selection_reference is None:
            selection_reference = scored_candidate.prior_rt
        distance = (
            abs(candidate.selection_apex_rt - selection_reference)
            if selection_reference is not None
            else float("inf")
        )
        confidence_rank = _CONFIDENCE_RANK[scored_candidate.confidence]
        selection_demotion_penalty = selection_demotion_penalties.get(
            id(scored_candidate),
            0.0,
        )
        selection_demoted = selection_demotion_penalty > 0
        if selection_demoted:
            confidence_rank += _LOW_SCAN_CONFIDENCE_DEMOTION
        selection_quality_penalty = (
            scored_candidate.selection_quality_penalty
            if scored_candidate.selection_quality_penalty is not None
            else float(scored_candidate.quality_penalty)
        )
        if strict_selection_rt and selection_rt is not None:
            return (
                distance,
                float(confidence_rank),
                selection_quality_penalty,
                0.0,
                -candidate.selection_apex_intensity,
            )
        if (
            scored_candidate.prefer_rt_prior_tiebreak
            and scored_candidate.prior_rt is not None
            and selection_rt is None
            and scored_candidate.evidence_score is None
        ):
            return (
                float(confidence_rank),
                distance,
                selection_quality_penalty,
                0.0,
                -candidate.selection_apex_intensity,
            )
        if selection_reference is not None:
            if scored_candidate.evidence_score is None:
                adjusted_distance = distance + (
                    selection_quality_penalty
                    * _SELECTION_QUALITY_DISTANCE_WEIGHT_MIN
                )
                return (
                    float(confidence_rank),
                    adjusted_distance,
                    selection_quality_penalty,
                    distance,
                    -candidate.selection_apex_intensity,
                )
            effective_score = _effective_score(
                scored_candidate,
                distance,
                demotion_penalty=selection_demotion_penalty,
            )
            if distance > _SELECTION_FAR_DISTANCE_MAX_MIN and not selection_demoted:
                if selection_demotion_penalties:
                    return (
                        1.0,
                        -effective_score,
                        distance,
                        selection_quality_penalty,
                        -candidate.selection_apex_intensity,
                    )
                return (
                    1.0,
                    distance,
                    -effective_score,
                    selection_quality_penalty,
                    -candidate.selection_apex_intensity,
                )
            if selection_demoted:
                return (
                    1.0,
                    -effective_score,
                    distance,
                    selection_quality_penalty,
                    -candidate.selection_apex_intensity,
                )
            return (
                0.0,
                -effective_score,
                distance,
                selection_quality_penalty,
                -candidate.selection_apex_intensity,
            )
        return (
            float(confidence_rank),
            selection_quality_penalty,
            0.0,
            0.0,
            -candidate.selection_apex_intensity,
        )

    return min(scored, key=key)


def _low_scan_demotion_ids(
    scored: list[ScoredCandidate],
    *,
    selection_rt: float | None,
) -> set[int]:
    demotions: set[int] = set()
    for scored_candidate in scored:
        if not _has_candidate_flag(scored_candidate, "low_scan_support"):
            continue
        if _has_much_stronger_supported_alternative(
            scored_candidate,
            scored,
            selection_rt=selection_rt,
        ):
            demotions.add(id(scored_candidate))
    return demotions


def _dominant_area_demotion_ids(
    scored: list[ScoredCandidate],
    *,
    selection_rt: float | None,
) -> set[int]:
    demotions: set[int] = set()
    for scored_candidate in scored:
        if _has_dominant_strict_nl_alternative(
            scored_candidate,
            scored,
            selection_rt=selection_rt,
        ):
            demotions.add(id(scored_candidate))
    return demotions


def _has_much_stronger_supported_alternative(
    low_scan_candidate: ScoredCandidate,
    scored: list[ScoredCandidate],
    *,
    selection_rt: float | None,
) -> bool:
    chosen_rank = _CONFIDENCE_RANK[low_scan_candidate.confidence]
    chosen_penalty = _selection_penalty_value(low_scan_candidate)
    chosen_intensity = float(low_scan_candidate.candidate.selection_apex_intensity)
    chosen_abundance = _candidate_abundance(low_scan_candidate)
    if chosen_intensity <= 0 and chosen_abundance <= 0:
        return False

    reference = selection_rt
    if reference is None:
        reference = low_scan_candidate.prior_rt
    for candidate in scored:
        if candidate is low_scan_candidate:
            continue
        if _has_candidate_flag(candidate, "low_scan_support"):
            continue
        if _CONFIDENCE_RANK[candidate.confidence] > (
            chosen_rank + _LOW_SCAN_MAX_CONFIDENCE_RANK_GAP
        ):
            continue
        if _selection_penalty_value(candidate) > chosen_penalty:
            continue
        candidate_distance = (
            abs(candidate.candidate.selection_apex_rt - reference)
            if reference is not None
            else 0.0
        )
        close_intensity_support = (
            reference is None
            or candidate_distance
            <= _LOW_SCAN_STRONGER_CANDIDATE_MAX_SELECTION_DISTANCE_MIN
        ) and float(candidate.candidate.selection_apex_intensity) >= (
            chosen_intensity * _LOW_SCAN_STRONGER_CANDIDATE_INTENSITY_RATIO
        )
        extended_area_support = (
            reference is None
            or candidate_distance
            <= _LOW_SCAN_STRONGER_CANDIDATE_EXTENDED_DISTANCE_MIN
        ) and _candidate_abundance(candidate) >= (
            chosen_abundance * _LOW_SCAN_STRONGER_CANDIDATE_AREA_RATIO
        )
        if not close_intensity_support and not extended_area_support:
            continue
        return True
    return False


def _has_dominant_strict_nl_alternative(
    scored_candidate: ScoredCandidate,
    scored: list[ScoredCandidate],
    *,
    selection_rt: float | None,
) -> bool:
    chosen_abundance = _candidate_abundance(scored_candidate)
    if chosen_abundance <= 0:
        return False

    reference = selection_rt
    if reference is None:
        reference = scored_candidate.prior_rt
    if reference is None:
        return False

    chosen_distance = abs(scored_candidate.candidate.selection_apex_rt - reference)
    if chosen_distance > _SELECTION_FAR_DISTANCE_MAX_MIN:
        return False

    chosen_penalty = _selection_penalty_value(scored_candidate)
    for candidate in scored:
        if candidate is scored_candidate:
            continue
        if candidate.confidence is Confidence.VERY_LOW:
            continue
        if _has_candidate_flag(candidate, "low_scan_support"):
            continue
        if _selection_penalty_value(candidate) > chosen_penalty:
            continue
        candidate_distance = abs(candidate.candidate.selection_apex_rt - reference)
        if candidate_distance > _DOMINANT_STRICT_NL_MAX_SELECTION_DISTANCE_MIN:
            continue
        if not _has_evidence_support(candidate, "strict_nl_ok"):
            continue
        if _candidate_abundance(candidate) < (
            chosen_abundance * _DOMINANT_STRICT_NL_AREA_RATIO
        ):
            continue
        return True
    return False


def _has_candidate_flag(scored_candidate: ScoredCandidate, flag: str) -> bool:
    flags = getattr(scored_candidate.candidate, "quality_flags", ())
    return flag in {str(candidate_flag) for candidate_flag in flags}


def _has_evidence_support(scored_candidate: ScoredCandidate, label: str) -> bool:
    evidence_score = scored_candidate.evidence_score
    if evidence_score is None:
        return False
    return label in {
        str(support_label) for support_label in evidence_score.support_labels
    }


def _selection_penalty_value(scored_candidate: ScoredCandidate) -> float:
    if scored_candidate.selection_quality_penalty is not None:
        return scored_candidate.selection_quality_penalty
    return float(scored_candidate.quality_penalty)


def _candidate_abundance(scored_candidate: ScoredCandidate) -> float:
    peak = getattr(scored_candidate.candidate, "peak", None)
    area = getattr(peak, "area", None)
    area_value = 0.0
    if area is not None:
        try:
            area_value = float(area)
        except (TypeError, ValueError):
            area_value = 0.0
    else:
        area_value = 0.0
    if _is_finite(area_value) and area_value > 0:
        return area_value

    try:
        intensity_value = float(scored_candidate.candidate.selection_apex_intensity)
    except (TypeError, ValueError):
        return 0.0
    if _is_finite(intensity_value) and intensity_value > 0:
        return intensity_value
    return 0.0


def _effective_score(
    scored_candidate: ScoredCandidate,
    distance: float,
    *,
    demotion_penalty: float = 0.0,
) -> float:
    raw_score = (
        float(scored_candidate.evidence_score.raw_score)
        if scored_candidate.evidence_score is not None
        else 50.0 - float(_CONFIDENCE_RANK[scored_candidate.confidence]) * 20.0
    )
    selection_quality_penalty = _selection_penalty_value(scored_candidate)
    return (
        raw_score
        - (distance * _SELECTION_DISTANCE_POINTS_PER_MIN)
        - (selection_quality_penalty * _SELECTION_QUALITY_POINTS_PER_UNIT)
        - demotion_penalty
    )


def _evidence_from_context(
    candidate: Any,
    ctx: ScoringContext,
    severities: list[tuple[int, str]],
    quality_penalty: int,
) -> tuple[list[EvidenceSignal], list[EvidenceSignal], list[ConfidenceCap]]:
    positive: list[EvidenceSignal] = []
    negative: list[EvidenceSignal] = []
    caps: list[ConfidenceCap] = []

    if not ctx.neutral_loss_required:
        positive.append(EvidenceSignal("no_nl_required", 10))
    elif ctx.ms2_present and ctx.nl_match:
        positive.append(EvidenceSignal("strict_nl_ok", 30))
    elif ctx.ms2_present and not ctx.nl_match:
        negative.append(EvidenceSignal("nl_fail", 45))
        caps.append(ConfidenceCap("nl_fail_cap", "VERY_LOW"))
    else:
        negative.append(EvidenceSignal("no_ms2", 25))
        caps.append(ConfidenceCap("no_ms2_cap", "LOW"))

    severity_by_label = {label: severity for severity, label in severities}
    rt_prior_close = False
    if ctx.rt_prior is not None:
        rt_severity = severity_by_label[_LABEL_RT_PRIOR]
        if rt_severity == 0:
            positive.append(EvidenceSignal("rt_prior_close", 15))
            rt_prior_close = True
            if ctx.prefer_rt_prior_tiebreak:
                positive.append(EvidenceSignal("paired_istd_aligned", 20))
        elif rt_severity == 1:
            negative.append(EvidenceSignal("rt_prior_borderline", 15))
        else:
            negative.append(EvidenceSignal("rt_prior_far", 35))

    rt_centrality = severity_by_label[_LABEL_RT_CENTRALITY]
    if rt_centrality == 1:
        negative.append(EvidenceSignal("rt_centrality_borderline", 10))
    elif rt_centrality == 2:
        negative.append(EvidenceSignal("rt_centrality_poor", 20))
        if (
            _outside_rt_window(candidate.selection_apex_rt, ctx.rt_min, ctx.rt_max)
            and not rt_prior_close
        ):
            caps.append(ConfidenceCap("rt_window_cap", "VERY_LOW"))

    local_sn = severity_by_label[_LABEL_LOCAL_SN]
    if local_sn == 0:
        positive.append(EvidenceSignal("local_sn_strong", 10))
    elif local_sn == 1:
        negative.append(EvidenceSignal("local_sn_borderline", 10))
    else:
        negative.append(EvidenceSignal("local_sn_poor", 25))

    shape = max(
        severity_by_label[_LABEL_SYMMETRY],
        severity_by_label[_LABEL_PEAK_WIDTH],
    )
    if shape == 0:
        positive.append(EvidenceSignal("shape_clean", 10))
    elif shape == 1:
        negative.append(EvidenceSignal("shape_borderline", 10))
    else:
        negative.append(EvidenceSignal("shape_poor", 20))

    noise_shape = severity_by_label[_LABEL_NOISE_SHAPE]
    if noise_shape == 1:
        negative.append(EvidenceSignal("noise_shape_borderline", 10))
    elif noise_shape == 2:
        negative.append(EvidenceSignal("noise_shape_poor", 20))

    flags = {str(flag) for flag in getattr(candidate, "quality_flags", ())}
    if not flags.intersection(_ADAP_LIKE_FLAG_LABELS):
        positive.append(EvidenceSignal("trace_clean", 10))

    trace_evidence = {
        "low scan support": ("low_scan_support", 15),
        "low trace continuity": ("low_trace_continuity", 10),
        "poor edge recovery": ("poor_edge_recovery", 10),
    }
    trace_quality_flagged = False
    for severity, label in severities:
        if severity == 0 or label not in trace_evidence:
            continue
        evidence_label, points = trace_evidence[label]
        negative.append(EvidenceSignal(evidence_label, points))
        trace_quality_flagged = True
    if trace_quality_flagged:
        caps.append(ConfidenceCap("trace_quality_cap", "MEDIUM"))

    if quality_penalty > 0:
        negative.append(EvidenceSignal("hard_quality_flag", 25 * quality_penalty))
        caps.append(ConfidenceCap("hard_quality_flag_cap", "MEDIUM"))

    return positive, negative, caps


def _outside_rt_window(observed: float, rt_min: float, rt_max: float) -> bool:
    if not (_is_finite(observed) and _is_finite(rt_min) and _is_finite(rt_max)):
        return True
    return observed < rt_min or observed > rt_max


def score_breakdown_fields(
    evidence_score: EvidenceScore | None,
) -> tuple[tuple[str, str], ...]:
    if evidence_score is None:
        return ()
    return (
        ("Final Confidence", evidence_score.confidence),
        ("Caps", "; ".join(evidence_score.cap_labels)),
        ("Raw Score", str(evidence_score.raw_score)),
        ("Support", "; ".join(evidence_score.support_labels)),
        ("Concerns", "; ".join(evidence_score.concern_labels)),
        ("Base Score", str(evidence_score.base_score)),
        ("Positive Points", str(evidence_score.positive_points)),
        ("Negative Points", str(evidence_score.negative_points)),
    )


def score_candidate(
    candidate: Any,
    ctx: ScoringContext,
    prior_rt: float | None,
    istd_confidence_note: str | None = None,
) -> ScoredCandidate:
    quality_penalty, quality_notes = candidate_quality_penalty(candidate)
    selection_quality_penalty = quality_penalty + candidate_selection_quality_penalty(
        candidate
    )
    severities: list[tuple[int, str]] = [
        symmetry_severity(ctx.half_width_ratio),
        local_sn_severity(
            ctx.intensity_array,
            ctx.apex_index,
            ctx.dirty_matrix,
            baseline=ctx.baseline_array,
            residual_mad=ctx.residual_mad,
        ),
        (
            nl_support_severity(ctx.ms2_present, ctx.nl_match)
            if ctx.neutral_loss_required
            else (0, _LABEL_NL)
        ),
        rt_prior_severity(
            candidate.selection_apex_rt,
            ctx.rt_prior,
            ctx.rt_prior_sigma,
        ),
        rt_centrality_severity(candidate.selection_apex_rt, ctx.rt_min, ctx.rt_max),
        noise_shape_severity(ctx.intensity_array),
        peak_width_severity(ctx.fwhm_ratio),
        *trace_quality_severities(candidate),
    ]
    positive, negative, caps = _evidence_from_context(
        candidate,
        ctx,
        severities,
        quality_penalty,
    )
    evidence_score = score_evidence(positive=positive, negative=negative, caps=caps)
    confidence = _confidence_from_value(evidence_score.confidence)
    reason = build_evidence_reason(
        evidence_score,
        istd_confidence_note,
        extra_notes=quality_notes,
    )
    return ScoredCandidate(
        candidate=candidate,
        severities=tuple(severities),
        confidence=confidence,
        reason=reason,
        prior_rt=prior_rt,
        quality_penalty=quality_penalty,
        selection_quality_penalty=selection_quality_penalty,
        prefer_rt_prior_tiebreak=ctx.prefer_rt_prior_tiebreak,
        evidence_score=evidence_score,
    )


def candidate_quality_penalty(candidate: Any) -> tuple[int, list[str]]:
    raw_flags = getattr(candidate, "quality_flags", ())
    flags = tuple(dict.fromkeys(str(flag) for flag in raw_flags))
    if not flags:
        return 0, []
    notes: list[str] = []

    legacy_flags = list(hard_quality_flags(flags))
    penalty = min(2, len(legacy_flags))
    if legacy_flags:
        notes.append(f"weak candidate: {', '.join(legacy_flags)}")
    return penalty, notes


def trace_quality_severities(candidate: Any) -> tuple[tuple[int, str], ...]:
    flags = {str(flag) for flag in getattr(candidate, "quality_flags", ())}
    return tuple(
        (1 if flag in flags else 0, label)
        for flag, label in _ADAP_LIKE_FLAG_LABELS.items()
    )


def candidate_selection_quality_penalty(candidate: Any) -> float:
    raw_flags = getattr(candidate, "quality_flags", ())
    flags = tuple(dict.fromkeys(str(flag) for flag in raw_flags))
    weighted_flags = [
        flag
        for flag in flags
        if flag in _ADAP_LIKE_FLAG_LABELS
    ]
    return min(
        _ADAP_LIKE_SELECTION_MAX,
        len(weighted_flags) * _ADAP_LIKE_SELECTION_WEIGHT,
    )


def hard_quality_flags(raw_flags: tuple[object, ...]) -> tuple[str, ...]:
    flags = tuple(dict.fromkeys(str(flag) for flag in raw_flags))
    suppressed_legacy = _suppressed_legacy_flags(flags)
    return tuple(
        flag
        for flag in flags
        if flag not in _ADAP_LIKE_FLAG_LABELS
        and flag not in suppressed_legacy
    )


def is_adap_like_quality_flag(flag: object) -> bool:
    return str(flag) in _ADAP_LIKE_FLAG_LABELS


def _suppressed_legacy_flags(flags: tuple[str, ...]) -> set[str]:
    flag_set = set(flags)
    return {
        legacy_flag
        for adap_flag, legacy_flag in _ADAP_EQUIVALENT_LEGACY_FLAGS.items()
        if adap_flag in flag_set and legacy_flag in flag_set
    }


def _is_finite(value: float) -> bool:
    return math.isfinite(float(value))


def _at_least(value: float, threshold: float) -> bool:
    return value >= threshold or math.isclose(
        value,
        threshold,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def symmetry_severity(half_width_ratio: float) -> tuple[int, str]:
    if not _is_finite(half_width_ratio):
        return 2, _LABEL_SYMMETRY
    if (
        half_width_ratio < _SYMMETRY_HARD_LOW
        or half_width_ratio > _SYMMETRY_HARD_HIGH
    ):
        return 2, _LABEL_SYMMETRY
    if (
        half_width_ratio < _SYMMETRY_SOFT_LOW
        or half_width_ratio > _SYMMETRY_SOFT_HIGH
    ):
        return 1, _LABEL_SYMMETRY
    return 0, _LABEL_SYMMETRY


def local_sn_severity(
    intensity: np.ndarray,
    apex_index: int,
    dirty_matrix: bool,
    *,
    baseline: np.ndarray | None = None,
    residual_mad: float | None = None,
) -> tuple[int, str]:
    """S/N ratio of peak apex vs. MAD of trace residual after AsLS baseline."""
    values = np.asarray(intensity, dtype=float)
    if len(values) < 5 or apex_index < 0 or apex_index >= len(values):
        return 2, _LABEL_LOCAL_SN
    cached_baseline = baseline
    mad = residual_mad
    if cached_baseline is None or mad is None:
        cached_baseline, mad = compute_local_sn_cache(values)
    if cached_baseline is None or mad is None:
        return 2, _LABEL_LOCAL_SN
    if mad <= 0:
        return 0, _LABEL_LOCAL_SN
    peak_above_baseline = float(values[apex_index] - cached_baseline[apex_index])
    ratio = peak_above_baseline / mad
    hard = _SN_DIRTY_HARD_THRESHOLD if dirty_matrix else _SN_HARD_THRESHOLD
    soft = _SN_DIRTY_SOFT_THRESHOLD if dirty_matrix else _SN_SOFT_THRESHOLD
    if ratio < hard:
        return 2, _LABEL_LOCAL_SN
    if ratio < soft:
        return 1, _LABEL_LOCAL_SN
    return 0, _LABEL_LOCAL_SN


def compute_local_sn_cache(
    intensity: np.ndarray,
) -> tuple[np.ndarray | None, float | None]:
    values = np.asarray(intensity, dtype=float)
    if len(values) < 5 or not np.all(np.isfinite(values)):
        return None, None
    try:
        baseline = asls_baseline(values)
    except ValueError:
        return None, None
    residual = values - baseline
    mad = float(np.median(np.abs(residual - np.median(residual))))
    return baseline, mad


def nl_support_severity(ms2_present: bool, nl_match: bool) -> tuple[int, str]:
    if ms2_present and nl_match:
        return 0, _LABEL_NL
    if ms2_present and not nl_match:
        return 2, _LABEL_NL
    return 1, _LABEL_NL


def rt_prior_severity(
    observed: float,
    prior: float | None,
    sigma: float | None,
) -> tuple[int, str]:
    if prior is None:
        return 0, _LABEL_RT_PRIOR
    if not _is_finite(observed) or not _is_finite(prior):
        return 2, _LABEL_RT_PRIOR
    deviation = abs(observed - prior)
    if sigma is not None and _is_finite(sigma) and sigma > 0:
        n_sigma = deviation / sigma
        if _at_least(n_sigma, _RT_PRIOR_SIGMA_HARD):
            return 2, _LABEL_RT_PRIOR
        if _at_least(n_sigma, _RT_PRIOR_SIGMA_SOFT):
            return 1, _LABEL_RT_PRIOR
        return 0, _LABEL_RT_PRIOR
    if _at_least(deviation, _RT_PRIOR_NO_SIGMA_HARD_MIN):
        return 2, _LABEL_RT_PRIOR
    if _at_least(deviation, _RT_PRIOR_NO_SIGMA_SOFT_MIN):
        return 1, _LABEL_RT_PRIOR
    return 0, _LABEL_RT_PRIOR


def rt_centrality_severity(
    observed: float, rt_min: float, rt_max: float
) -> tuple[int, str]:
    if not (_is_finite(observed) and _is_finite(rt_min) and _is_finite(rt_max)):
        return 2, _LABEL_RT_CENTRALITY
    span = rt_max - rt_min
    if span <= 0:
        return 2, _LABEL_RT_CENTRALITY
    distance_low = observed - rt_min
    distance_high = rt_max - observed
    min_edge = min(distance_low, distance_high) / span
    if min_edge < 0.01:
        return 2, _LABEL_RT_CENTRALITY
    if min_edge < 0.10:
        return 1, _LABEL_RT_CENTRALITY
    return 0, _LABEL_RT_CENTRALITY


def noise_shape_severity(intensity: np.ndarray) -> tuple[int, str]:
    """Jaggedness: sum of abs second differences normalised by peak span."""
    values = np.asarray(intensity, dtype=float)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        return 2, _LABEL_NOISE_SHAPE
    if len(values) < 3:
        return 0, _LABEL_NOISE_SHAPE
    span = float(values.max() - values.min())
    if span <= 0:
        return 0, _LABEL_NOISE_SHAPE
    second_diff = np.abs(np.diff(values, n=2))
    jagged = float(second_diff.sum() / (span * len(values)))
    if jagged > 0.5:
        return 2, _LABEL_NOISE_SHAPE
    if jagged > 0.3:
        return 1, _LABEL_NOISE_SHAPE
    return 0, _LABEL_NOISE_SHAPE


def peak_width_severity(fwhm_ratio: float | None) -> tuple[int, str]:
    if fwhm_ratio is None:
        return 0, _LABEL_PEAK_WIDTH
    if not _is_finite(fwhm_ratio):
        return 2, _LABEL_PEAK_WIDTH
    if fwhm_ratio < 0.3 or fwhm_ratio > 3.0:
        return 2, _LABEL_PEAK_WIDTH
    if fwhm_ratio < 0.5 or fwhm_ratio > 2.0:
        return 1, _LABEL_PEAK_WIDTH
    return 0, _LABEL_PEAK_WIDTH
