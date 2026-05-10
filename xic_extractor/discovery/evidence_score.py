from dataclasses import dataclass

from xic_extractor.discovery.evidence_config import (
    DEFAULT_EVIDENCE_PROFILE,
    DiscoveryEvidenceThresholds,
)
from xic_extractor.discovery.models import DiscoveryCandidate, DiscoverySettings


@dataclass(frozen=True)
class DiscoveryEvidence:
    score: int
    tier: str
    ms2_support: str
    ms1_support: str
    rt_alignment: str
    family_context: str


def score_discovery_evidence(
    candidate: DiscoveryCandidate,
    *,
    settings: DiscoverySettings | None = None,
) -> DiscoveryEvidence:
    profile = (
        settings.evidence_profile
        if settings is not None
        else DEFAULT_EVIDENCE_PROFILE
    )
    weights = profile.weights
    thresholds = profile.thresholds

    ms2_support = classify_ms2_support(candidate, thresholds=thresholds)
    ms1_support = classify_ms1_support(candidate, thresholds=thresholds)
    rt_alignment = classify_rt_alignment(candidate, thresholds=thresholds)
    family_context = classify_family_context(candidate)

    score = 0
    if candidate.ms1_peak_found:
        score += weights.ms1_peak_present
    else:
        score += weights.ms1_peak_absent

    score += min(
        weights.seed_event_max,
        max(0, candidate.seed_event_count) * weights.seed_event_per,
    )

    if candidate.ms1_seed_delta_min is not None:
        delta = abs(candidate.ms1_seed_delta_min)
        if delta <= thresholds.rt_aligned_max_min:
            score += weights.rt_aligned
        elif delta <= thresholds.rt_near_max_min:
            score += weights.rt_near
        elif delta <= thresholds.rt_shifted_max_min:
            score += weights.rt_shifted

    if candidate.ms2_product_max_intensity >= thresholds.product_intensity_high_min:
        score += weights.product_intensity_high
    elif candidate.ms2_product_max_intensity >= thresholds.product_intensity_med_min:
        score += weights.product_intensity_med

    if candidate.ms1_area is not None:
        if candidate.ms1_area >= thresholds.area_high_min:
            score += weights.area_high
        elif candidate.ms1_area >= thresholds.area_med_min:
            score += weights.area_med

    if candidate.ms1_trace_quality.upper() in {"GOOD", "CLEAN"}:
        score += weights.legacy_trace_quality_high
    elif candidate.ms1_trace_quality.upper() in {"POOR", "MISSING"}:
        score += weights.legacy_trace_quality_low

    if candidate.feature_superfamily_size > 1:
        if candidate.feature_superfamily_role == "representative":
            score += weights.superfamily_representative
        else:
            score += weights.superfamily_member

    score = min(100, max(0, score))
    return DiscoveryEvidence(
        score=score,
        tier=evidence_tier_from_score(score),
        ms2_support=ms2_support,
        ms1_support=ms1_support,
        rt_alignment=rt_alignment,
        family_context=family_context,
    )


def classify_ms2_support(
    candidate: DiscoveryCandidate,
    *,
    thresholds: DiscoveryEvidenceThresholds = DEFAULT_EVIDENCE_PROFILE.thresholds,
) -> str:
    if (
        candidate.seed_event_count >= 3
        or (
            candidate.seed_event_count >= 2
            and candidate.ms2_product_max_intensity
            >= thresholds.product_intensity_med_min
        )
        or candidate.ms2_product_max_intensity
        >= thresholds.product_intensity_high_min
    ):
        return "strong"
    if (
        candidate.seed_event_count >= 2
        or candidate.ms2_product_max_intensity
        >= thresholds.product_intensity_med_min
    ):
        return "moderate"
    return "weak"


def classify_ms1_support(
    candidate: DiscoveryCandidate,
    *,
    thresholds: DiscoveryEvidenceThresholds = DEFAULT_EVIDENCE_PROFILE.thresholds,
) -> str:
    if not candidate.ms1_peak_found or candidate.ms1_area is None:
        return "missing"
    trace_quality = candidate.ms1_trace_quality.upper()
    if (
        candidate.ms1_area >= thresholds.ms1_support_strong_area_min
        and trace_quality in {"GOOD", "CLEAN"}
    ):
        return "strong"
    if (
        candidate.ms1_area >= thresholds.ms1_support_moderate_area_min
        or trace_quality in {"GOOD", "CLEAN"}
    ):
        return "moderate"
    return "weak"


def classify_rt_alignment(
    candidate: DiscoveryCandidate,
    *,
    thresholds: DiscoveryEvidenceThresholds = DEFAULT_EVIDENCE_PROFILE.thresholds,
) -> str:
    if candidate.ms1_seed_delta_min is None:
        return "missing"
    delta = abs(candidate.ms1_seed_delta_min)
    if delta <= thresholds.rt_aligned_max_min:
        return "aligned"
    if delta <= thresholds.rt_near_max_min:
        return "near"
    return "shifted"


def classify_family_context(candidate: DiscoveryCandidate) -> str:
    if candidate.feature_superfamily_size <= 1:
        return "singleton"
    if candidate.feature_superfamily_role == "representative":
        return "representative"
    return "member"


def evidence_tier_from_score(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "E"
