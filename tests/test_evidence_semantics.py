from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.evidence_semantics import (
    EvidenceSignalSet,
    canonical_concern_labels,
    canonical_support_labels,
    classify_evidence_consistency,
    common_evidence_from_aligned_cell,
    common_evidence_from_discovery_candidate,
    common_evidence_from_targeted_candidate,
)
from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.signal_processing import (
    PeakCandidate,
    PeakCandidateScore,
    PeakResult,
)


def test_targeted_candidate_projects_to_common_ms1_ms2_evidence() -> None:
    candidate = _candidate(
        rt=8.5,
        area=1200.0,
        region_scan_count=6,
        quality_flags=("low_trace_continuity",),
    )
    evidence = common_evidence_from_targeted_candidate(
        candidate,
        score=_score(candidate, confidence="MEDIUM", raw_score=72),
        candidate_ms2_evidence=_ms2_evidence(nl_match=True),
        target_label="d3-N6-medA",
    )

    assert evidence.source == "targeted_peak"
    assert evidence.source_id == "d3-N6-medA"
    assert evidence.ms1_peak_found is True
    assert evidence.ms1_area == 1200.0
    assert evidence.ms1_apex_rt_min == 8.5
    assert evidence.ms2_present is True
    assert evidence.nl_match is True
    assert evidence.neutral_loss_error_ppm == 1.2
    assert evidence.confidence == "MEDIUM"
    assert evidence.evidence_score == 72
    assert evidence.trace_quality == "review"
    assert "ms1_peak" in canonical_support_labels(evidence)
    assert "nl_match" in canonical_support_labels(evidence)
    assert "trace_quality_review" in canonical_concern_labels(evidence)


def test_discovery_candidate_projects_to_same_common_evidence_semantics() -> None:
    candidate = SimpleNamespace(
        candidate_id="sample#1234",
        sample_stem="sample",
        review_priority="HIGH",
        evidence_score=88,
        seed_event_count=2,
        ms1_peak_found=True,
        ms1_apex_rt=8.51,
        ms1_area=1250.0,
        ms1_height=400.0,
        ms1_peak_rt_start=8.35,
        ms1_peak_rt_end=8.71,
        ms1_seed_delta_min=0.01,
        ms1_trace_quality="clean",
        ms1_scan_support_score=0.83,
        neutral_loss_tag="dR",
        configured_neutral_loss_da=116.0474,
        observed_neutral_loss_da=116.0475,
        neutral_loss_mass_error_ppm=0.86,
        reason="strong MS2 NL seed group; MS1 peak found near seed RT",
    )

    evidence = common_evidence_from_discovery_candidate(candidate)

    assert evidence.source == "discovery_candidate"
    assert evidence.source_id == "sample#1234"
    assert evidence.ms1_peak_found is True
    assert evidence.ms1_area == 1250.0
    assert evidence.ms1_apex_rt_min == 8.51
    assert evidence.rt_delta_min == 0.01
    assert evidence.neutral_loss_tag == "dR"
    assert evidence.seed_event_count == 2
    assert evidence.evidence_score == 88
    assert evidence.review_priority == "HIGH"
    assert canonical_support_labels(evidence) == (
        "ms1_peak",
        "positive_area",
        "ms2_present",
        "nl_match",
        "multi_seed",
        "scan_support",
    )


def test_alignment_cell_projects_backfill_provenance_without_identity_policy() -> None:
    cell = AlignedCell(
        sample_stem="sample",
        cluster_id="FAM001",
        status="rescued",
        area=900.0,
        apex_rt=8.52,
        height=350.0,
        peak_start_rt=8.30,
        peak_end_rt=8.75,
        rt_delta_sec=1.2,
        trace_quality="owner_backfill",
        scan_support_score=0.7,
        source_candidate_id=None,
        source_raw_file=Path("sample.raw"),
        reason="owner-centered MS1 backfill",
    )

    evidence = common_evidence_from_aligned_cell(
        cell,
        neutral_loss_tag="dR",
        family_id="FAM001",
    )

    assert evidence.source == "alignment_cell"
    assert evidence.source_id == "FAM001:sample"
    assert evidence.ms1_peak_found is True
    assert evidence.ms1_area == 900.0
    assert evidence.rt_delta_min == 0.02
    assert evidence.neutral_loss_tag == "dR"
    assert evidence.provenance == "rescued"
    assert "backfill_provenance" in canonical_concern_labels(evidence)


def test_consistency_classifier_splits_nl_dropout_from_conflict() -> None:
    plausible = classify_evidence_consistency(
        EvidenceSignalSet(
            support_labels=("local_sn_strong", "shape_clean", "trace_clean"),
            concern_labels=("nl_fail",),
            ms2_present=True,
            nl_match=False,
            raw_score=35,
        )
    )
    hard = classify_evidence_consistency(
        EvidenceSignalSet(
            support_labels=("local_sn_strong", "trace_clean"),
            concern_labels=("nl_fail", "shape_poor"),
            ms2_present=True,
            nl_match=False,
            raw_score=35,
        )
    )

    assert plausible == (
        "ms1_coherent",
        "plausible_nl_dropout",
    )
    assert hard == (
        "hard_local_quality_conflict",
        "hard_nl_conflict",
    )


def test_consistency_classifier_allows_cwt_as_shape_context_but_not_chemistry() -> None:
    labels = classify_evidence_consistency(
        EvidenceSignalSet(
            support_labels=("local_sn_strong", "trace_clean"),
            concern_labels=("nl_fail",),
            proposal_sources=("centwave_cwt", "local_minimum"),
            ms2_present=True,
            nl_match=False,
            raw_score=20,
        )
    )

    assert labels == (
        "ms1_coherent",
        "plausible_nl_dropout",
    )


def test_consistency_classifier_keeps_no_ms2_distinct_from_nl_dropout() -> None:
    labels = classify_evidence_consistency(
        EvidenceSignalSet(
            support_labels=("local_sn_strong", "shape_clean", "trace_clean"),
            concern_labels=("nl_fail", "no_ms2"),
            ms2_present=False,
            nl_match=False,
            raw_score=35,
        )
    )

    assert labels == (
        "ms1_coherent",
        "missing_ms2",
        "hard_nl_conflict",
    )


def _candidate(
    *,
    rt: float,
    area: float,
    region_scan_count: int | None = None,
    quality_flags: tuple[str, ...] = (),
) -> PeakCandidate:
    peak = PeakResult(
        rt=rt,
        intensity=1000.0,
        intensity_smoothed=900.0,
        area=area,
        peak_start=rt - 0.2,
        peak_end=rt + 0.2,
    )
    return PeakCandidate(
        peak=peak,
        selection_apex_rt=rt,
        selection_apex_intensity=900.0,
        selection_apex_index=3,
        raw_apex_rt=rt,
        raw_apex_intensity=1000.0,
        raw_apex_index=3,
        prominence=500.0,
        region_scan_count=region_scan_count,
        quality_flags=quality_flags,
    )


def _score(
    candidate: PeakCandidate,
    *,
    confidence: str,
    raw_score: int,
) -> PeakCandidateScore:
    return PeakCandidateScore(
        candidate=candidate,
        confidence=confidence,
        reason=f"decision: {confidence.lower()}",
        raw_score=raw_score,
        support_labels=("shape_clean",),
    )


def _ms2_evidence(*, nl_match: bool) -> CandidateMS2Evidence:
    return CandidateMS2Evidence(
        ms2_present=True,
        nl_match=nl_match,
        nl_status="OK" if nl_match else "NL_FAIL",
        trigger_scan_count=1,
        strict_nl_scan_count=1 if nl_match else 0,
        best_loss_ppm=1.2 if nl_match else None,
        best_scan_rt=8.5,
        best_product_base_ratio=0.3,
        alignment_source="region",
    )
