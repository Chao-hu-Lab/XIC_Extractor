from dataclasses import dataclass

from xic_extractor.discovery.models import DiscoveryCandidate


@dataclass(frozen=True)
class DiscoveryEvidence:
    score: int
    tier: str
    ms2_support: str
    ms1_support: str
    rt_alignment: str
    family_context: str


def score_discovery_evidence(candidate: DiscoveryCandidate) -> DiscoveryEvidence:
    ms2_support = classify_ms2_support(candidate)
    ms1_support = classify_ms1_support(candidate)
    rt_alignment = classify_rt_alignment(candidate)
    family_context = classify_family_context(candidate)

    score = 0
    if candidate.ms1_peak_found:
        score += 25
    else:
        score += 5

    score += min(25, max(0, candidate.seed_event_count) * 8)

    if candidate.ms1_seed_delta_min is not None:
        delta = abs(candidate.ms1_seed_delta_min)
        if delta <= 0.05:
            score += 15
        elif delta <= 0.20:
            score += 10
        elif delta <= 0.40:
            score += 5

    if candidate.ms2_product_max_intensity >= 100_000:
        score += 10
    elif candidate.ms2_product_max_intensity >= 10_000:
        score += 5

    if candidate.ms1_area is not None:
        if candidate.ms1_area >= 1_000_000:
            score += 10
        elif candidate.ms1_area >= 100_000:
            score += 5

    if candidate.ms1_trace_quality.upper() in {"GOOD", "CLEAN"}:
        score += 5
    elif candidate.ms1_trace_quality.upper() in {"POOR", "MISSING"}:
        score -= 10

    if candidate.feature_superfamily_size > 1:
        if candidate.feature_superfamily_role == "representative":
            score += 5
        else:
            score -= 5

    score = min(100, max(0, score))
    return DiscoveryEvidence(
        score=score,
        tier=evidence_tier_from_score(score),
        ms2_support=ms2_support,
        ms1_support=ms1_support,
        rt_alignment=rt_alignment,
        family_context=family_context,
    )


def classify_ms2_support(candidate: DiscoveryCandidate) -> str:
    if (
        candidate.seed_event_count >= 3
        or (
            candidate.seed_event_count >= 2
            and candidate.ms2_product_max_intensity >= 10_000
        )
        or candidate.ms2_product_max_intensity >= 100_000
    ):
        return "strong"
    if candidate.seed_event_count >= 2 or candidate.ms2_product_max_intensity >= 10_000:
        return "moderate"
    return "weak"


def classify_ms1_support(candidate: DiscoveryCandidate) -> str:
    if not candidate.ms1_peak_found or candidate.ms1_area is None:
        return "missing"
    trace_quality = candidate.ms1_trace_quality.upper()
    if candidate.ms1_area >= 10_000_000 and trace_quality in {"GOOD", "CLEAN"}:
        return "strong"
    if candidate.ms1_area >= 1_000_000 or trace_quality in {"GOOD", "CLEAN"}:
        return "moderate"
    return "weak"


def classify_rt_alignment(candidate: DiscoveryCandidate) -> str:
    if candidate.ms1_seed_delta_min is None:
        return "missing"
    delta = abs(candidate.ms1_seed_delta_min)
    if delta <= 0.05:
        return "aligned"
    if delta <= 0.20:
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
