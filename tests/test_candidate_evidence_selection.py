from dataclasses import replace

import numpy as np

from xic_extractor.peak_detection.candidate_scoring import score_candidate
from xic_extractor.peak_detection.candidate_selection import (
    select_candidate_by_evidence,
)
from xic_extractor.peak_detection.evidence_facts import (
    FACTS_VERSION,
    BoundaryEvidenceFacts,
    CandidateEvidenceFacts,
    ChemicalEvidenceFacts,
    EvidenceQuality,
    RtEvidenceFacts,
    TraceEvidenceFacts,
    build_candidate_evidence_facts,
)
from xic_extractor.peak_detection.models import PeakCandidate, PeakResult
from xic_extractor.peak_detection.scoring_models import ScoredCandidate, ScoringContext
from xic_extractor.peak_scoring_evidence import EvidenceScore


def test_typed_selector_ignores_adversarial_legacy_raw_score_and_labels() -> None:
    rt = np.asarray([8.4, 8.5, 8.6, 8.9])
    intensity = np.asarray([100.0, 1000.0, 120.0, 900.0])
    preferred = _candidate(8.5, area=1000.0)
    decoy = _candidate(8.9, area=900.0)
    preferred_ctx = _ctx(rt, intensity, preferred, ms2_present=True, nl_match=True)
    decoy_ctx = _ctx(rt, intensity, decoy, ms2_present=False, nl_match=False)
    preferred_score = score_candidate(preferred, preferred_ctx, prior_rt=8.5)
    decoy_score = score_candidate(decoy, decoy_ctx, prior_rt=8.5)
    preferred_score = preferred_score.__class__(
        **{
            **preferred_score.__dict__,
            "evidence_facts": build_candidate_evidence_facts(
                preferred,
                preferred_ctx,
                role="Analyte",
                istd_pair="ISTD",
            ),
            "evidence_score": _legacy_score(
                raw_score=-999,
                support_labels=("legacy_decoy_negative",),
                concern_labels=("legacy_noise",),
            ),
        }
    )
    decoy_score = decoy_score.__class__(
        **{
            **decoy_score.__dict__,
            "evidence_facts": build_candidate_evidence_facts(
                decoy,
                decoy_ctx,
                role="Analyte",
                istd_pair="ISTD",
            ),
            "evidence_score": _legacy_score(
                raw_score=999,
                support_labels=("strict_nl_ok", "ms2_trace_strong"),
                concern_labels=(),
            ),
        }
    )

    selected = select_candidate_by_evidence(
        [preferred_score, decoy_score],
        selection_rt=8.5,
    )

    assert selected.candidate is preferred


def test_strict_typed_selector_prefers_accepted_evidence_before_rt_distance() -> None:
    accepted = _candidate(10.14, area=1000.0)
    nearer_review = _candidate(10.02, area=900.0)
    accepted_score = _scored_with_facts(
        accepted,
        _facts(
            accepted,
            rt=10.14,
            abundance=1000.0,
            ms2_trace_strength="moderate",
            shape_quality="clean",
        ),
    )
    review_score = _scored_with_facts(
        nearer_review,
        _facts(
            nearer_review,
            rt=10.02,
            abundance=900.0,
            ms2_trace_strength="strong",
            shape_quality="borderline",
        ),
    )

    selected = select_candidate_by_evidence(
        [review_score, accepted_score],
        selection_rt=10.0,
        strict_selection_rt=True,
    )

    assert selected.candidate is accepted


def test_typed_selector_demotes_nl_fail_candidate_far_from_paired_istd() -> None:
    near_anchor = _candidate(10.2, area=100.0)
    far_anchor = _candidate(11.25, area=5000.0)
    near_score = _scored_with_facts(
        near_anchor,
        _facts(
            near_anchor,
            rt=10.2,
            abundance=100.0,
            ms2_trace_strength="weak",
            shape_quality="clean",
            nl_match=False,
            paired_istd_delta_min=0.2,
            paired_istd_status="close",
        ),
    )
    far_score = _scored_with_facts(
        far_anchor,
        _facts(
            far_anchor,
            rt=11.25,
            abundance=5000.0,
            ms2_trace_strength="weak",
            shape_quality="clean",
            nl_match=False,
            paired_istd_delta_min=1.25,
            paired_istd_status="far",
        ),
    )

    selected = select_candidate_by_evidence([far_score, near_score])

    assert selected.candidate is near_anchor


def test_strict_selector_prefers_paired_rt_chrom_segment_over_weak_ms2_nl() -> None:
    paired_rt_segment = _candidate(
        10.02,
        area=900.0,
        proposal_sources=("chrom_peak_segment",),
    )
    weak_ms2_decoy = _candidate(
        10.87,
        area=2000.0,
        proposal_sources=("chrom_peak_segment",),
    )
    paired_rt_score = _scored_with_facts(
        paired_rt_segment,
        _facts(
            paired_rt_segment,
            rt=10.02,
            abundance=900.0,
            ms2_trace_strength="none",
            shape_quality="clean",
            nl_match=False,
            paired_istd_delta_min=0.02,
            paired_istd_status="close",
        ),
    )
    weak_ms2_score = _scored_with_facts(
        weak_ms2_decoy,
        _facts(
            weak_ms2_decoy,
            rt=10.87,
            abundance=2000.0,
            ms2_trace_strength="weak",
            shape_quality="clean",
            nl_match=True,
            paired_istd_delta_min=0.87,
            paired_istd_status="close",
        ),
    )

    selected = select_candidate_by_evidence(
        [weak_ms2_score, paired_rt_score],
        selection_rt=10.0,
        strict_selection_rt=True,
    )

    assert selected.candidate is paired_rt_segment


def test_strict_selector_demotes_late_small_peak_when_anchor_aligned_area_exists(
) -> None:
    anchor_aligned_area = _candidate(
        10.02,
        area=475_000.0,
        proposal_sources=("local_minimum",),
    )
    late_small_context_peak = _candidate(
        10.80,
        area=6_500.0,
        proposal_sources=("local_minimum", "chrom_peak_segment", "centwave_cwt"),
    )
    anchor_score = _scored_with_facts(
        anchor_aligned_area,
        _facts(
            anchor_aligned_area,
            rt=10.02,
            abundance=475_000.0,
            ms2_trace_strength="weak",
            shape_quality="clean",
            nl_match=False,
            paired_istd_delta_min=0.02,
            paired_istd_status="close",
            selection_quality_penalty=8.0,
        ),
    )
    late_score = _scored_with_facts(
        late_small_context_peak,
        _facts(
            late_small_context_peak,
            rt=10.80,
            abundance=6_500.0,
            ms2_trace_strength="weak",
            shape_quality="clean",
            nl_match=False,
            paired_istd_delta_min=0.80,
            paired_istd_status="close",
            selection_quality_penalty=0.0,
        ),
    )

    selected = select_candidate_by_evidence(
        [late_score, anchor_score],
        selection_rt=10.0,
        strict_selection_rt=True,
    )

    assert selected.candidate is anchor_aligned_area


def _scored_with_facts(
    candidate: PeakCandidate,
    facts: CandidateEvidenceFacts,
) -> ScoredCandidate:
    score = score_candidate(
        candidate,
        _ctx(
            np.asarray([9.9, 10.0, 10.1, 10.2]),
            np.asarray([100.0, 1000.0, 900.0, 120.0]),
            candidate,
            ms2_present=True,
            nl_match=True,
            prior_rt=10.0,
        ),
        prior_rt=10.0,
    )
    return replace(score, evidence_facts=facts)


def _facts(
    candidate: PeakCandidate,
    *,
    rt: float,
    abundance: float,
    ms2_trace_strength: str,
    shape_quality: EvidenceQuality,
    nl_match: bool = True,
    paired_istd_delta_min: float | None = None,
    paired_istd_status: str = "missing",
    selection_quality_penalty: float = 0.0,
) -> CandidateEvidenceFacts:
    return CandidateEvidenceFacts(
        facts_version=FACTS_VERSION,
        candidate_id=f"candidate@{rt}",
        abundance=abundance,
        area=abundance,
        height=abundance,
        trace=TraceEvidenceFacts(
            local_sn_quality="strong",
            symmetry_quality=shape_quality,
            width_quality="clean",
            noise_shape_quality="clean",
            scan_count=10,
            duration_min=0.2,
        ),
        chemical=ChemicalEvidenceFacts(
            neutral_loss_required=True,
            ms2_present=True,
            nl_match=nl_match,
            nl_status="OK" if nl_match else "NL_FAIL",
            ms2_trace_strength=ms2_trace_strength,
            acquisition_opportunity="observed",
        ),
        rt=RtEvidenceFacts(
            selected_apex_rt_min=rt,
            rt_prior_min=10.0,
            rt_prior_delta_min=abs(rt - 10.0),
            rt_prior_status="close",
            window_status="inside",
            paired_istd_anchor_rt_min=(
                rt - paired_istd_delta_min
                if paired_istd_delta_min is not None
                else None
            ),
            paired_istd_delta_min=paired_istd_delta_min,
            paired_istd_status=paired_istd_status,
            role="Analyte",
        ),
        boundary=BoundaryEvidenceFacts(
            proposal_sources=candidate.proposal_sources,
            chrom_peak_segment_present=(
                "chrom_peak_segment" in candidate.proposal_sources
            ),
        ),
        quality_penalty=0,
        selection_quality_penalty=selection_quality_penalty,
    )


def _legacy_score(
    *,
    raw_score: int,
    support_labels: tuple[str, ...],
    concern_labels: tuple[str, ...],
) -> EvidenceScore:
    return EvidenceScore(
        base_score=50,
        positive_points=0,
        negative_points=0,
        raw_score=raw_score,
        score_confidence="HIGH",
        confidence="HIGH",
        support_labels=support_labels,
        concern_labels=concern_labels,
        cap_labels=(),
    )


def _ctx(
    rt: np.ndarray,
    intensity: np.ndarray,
    candidate: PeakCandidate,
    *,
    ms2_present: bool,
    nl_match: bool,
    prior_rt: float = 8.5,
) -> ScoringContext:
    return ScoringContext(
        rt_array=rt,
        intensity_array=intensity,
        apex_index=candidate.selection_apex_index,
        half_width_ratio=1.0,
        fwhm_ratio=1.0,
        ms2_present=ms2_present,
        nl_match=nl_match,
        rt_prior=prior_rt,
        rt_prior_sigma=0.1,
        rt_min=8.0,
        rt_max=9.0,
        dirty_matrix=False,
        ms2_trace_strength="strong" if ms2_present and nl_match else None,
    )


def _candidate(
    rt: float,
    *,
    area: float,
    proposal_sources: tuple[str, ...] = ("local_minimum",),
) -> PeakCandidate:
    peak = PeakResult(
        rt=rt,
        intensity=1200.0,
        intensity_smoothed=1100.0,
        area=area,
        peak_start=rt - 0.1,
        peak_end=rt + 0.1,
    )
    apex_index = 1 if rt == 8.5 else 3
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=1100.0,
        selection_apex_index=apex_index,
        raw_apex_rt=rt,
        raw_apex_intensity=1200.0,
        raw_apex_index=apex_index,
        prominence=900.0,
        region_scan_count=8,
        region_duration_min=0.2,
        region_edge_ratio=0.8,
        region_trace_continuity=0.9,
        proposal_sources=proposal_sources,
    )
