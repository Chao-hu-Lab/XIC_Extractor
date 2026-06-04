from pathlib import Path

from xic_extractor.evidence_semantics import EvidenceDecisionSemantics
from xic_extractor.peak_detection.hypotheses import (
    AuditTrail,
    EvidenceVector,
    IntegrationResult,
    PeakHypothesis,
)
from xic_extractor.peak_detection.model_selection import (
    ExpectedDiffApprovalRecord,
    expected_diff_approval_for_result,
    expected_diff_stable_row_id,
    model_select_peak_hypothesis,
)

CHARACTERIZATION_MAP = Path(
    "docs/superpowers/notes/"
    "2026-06-02-selected-hypothesis-model-selection-characterization-map.md"
)


def test_characterization_map_covers_required_fixture_families() -> None:
    text = CHARACTERIZATION_MAP.read_text(encoding="utf-8")
    required = [
        "clean single peak",
        "confidence rank",
        "role-aware RT prior / ISTD",
        "strict selection RT",
        "final intensity tie-break",
        "local S/N with AsLS",
        "shape / width / morphology",
        "MS2 present / strict NL OK",
        "no MS2 / NL fail",
        "MS2 trace tie-break",
        "CWT same-apex support",
        "low-scan demotion",
        "dominant strict-NL alternative",
        "ADAP-like quality flags",
        "stale final result fallback",
        "no-candidate / no-peak fallback",
    ]

    for fixture_family in required:
        assert fixture_family in text


def test_characterization_map_blocks_legacy_test_deletion() -> None:
    text = CHARACTERIZATION_MAP.read_text(encoding="utf-8")

    assert "Do Not Delete Yet" in text
    assert "tests/test_peak_scoring.py" in text
    assert "no legacy test deletion is proposed" in text


def test_shadow_model_selection_reports_parity_for_legacy_selected_hypothesis() -> None:
    selected = _hypothesis(
        "selected",
        selected=True,
        confidence="HIGH",
        reason="decision: accepted",
        decision_class="accepted",
    )
    rejected = _hypothesis(
        "rejected",
        selected=False,
        confidence="LOW",
        reason="decision: review",
        decision_class="review",
    )

    result = model_select_peak_hypothesis((selected, rejected))

    assert result.selected_candidate_id == selected.hypothesis_id
    assert result.legacy_selected_candidate_id == selected.hypothesis_id
    assert result.trace_group_id == selected.trace_group_id
    assert result.decision_class == "accepted"
    assert result.selection_status == "parity"
    assert result.public_projection["confidence"] == "HIGH"
    assert result.public_projection["reason"] == "decision: accepted"
    assert result.public_projection["compatibility_labels"] == "strict_nl_ok"
    assert result.compatibility_oracle == "legacy_peak_scoring_current_oracle"
    assert result.policy_source == "selected_hypothesis_model_selection_v1"
    assert result.evidence_comparison_policy == "limited_evidence_shadow"
    assert result.product_switch_allowed is True


def test_shadow_model_selection_blocks_no_legacy_selected_hypothesis() -> None:
    result = model_select_peak_hypothesis(
        (
            _hypothesis("first", selected=False, confidence="HIGH"),
            _hypothesis("second", selected=False, confidence="MEDIUM"),
        )
    )

    assert result.selected_candidate_id == ""
    assert result.legacy_selected_candidate_id == ""
    assert result.selection_status == "inconclusive"
    assert result.product_switch_allowed is False
    assert "missing_legacy_selected_hypothesis" in result.diff_reasons


def test_expected_diff_without_approval_record_cannot_product_switch() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")

    result = model_select_peak_hypothesis((legacy, successor))

    assert result.selected_candidate_id == successor.hypothesis_id
    assert result.legacy_selected_candidate_id == legacy.hypothesis_id
    assert result.selection_status == "expected_diff"
    assert result.product_switch_allowed is False
    assert "missing_expected_diff_approval_record" in result.diff_reasons


def test_blocked_and_inconclusive_statuses_cannot_product_switch() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="HIGH")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")

    blocked = model_select_peak_hypothesis(
        (legacy, successor),
        successor_selected_candidate_id=successor.hypothesis_id,
        force_selection_status="blocked_diff",
        diff_reasons=("unexplained_successor_mismatch",),
    )
    inconclusive = model_select_peak_hypothesis(
        (legacy, successor),
        force_selection_status="inconclusive",
        diff_reasons=("candidate_evidence_incomplete",),
    )

    assert blocked.product_switch_allowed is False
    assert inconclusive.product_switch_allowed is False


def test_forced_parity_mismatch_cannot_product_switch() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")

    result = model_select_peak_hypothesis(
        (legacy, successor),
        successor_selected_candidate_id=successor.hypothesis_id,
        force_selection_status="parity",
    )

    assert result.selection_status == "parity"
    assert result.product_switch_allowed is False
    assert "parity_selected_candidate_mismatch" in result.diff_reasons
    assert "parity_public_projection_mismatch" in result.diff_reasons


def test_matrix_expected_diff_requires_real_validation() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")
    synthetic_record = ExpectedDiffApprovalRecord(
        stable_row_id=_stable_row_id(legacy, successor),
        sample_name="SampleA",
        target_label="Analyte",
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
        public_outputs_touched=(
            "candidate table selected marker",
            "confidence",
            "final matrix value",
        ),
        matrix_value_impact="area_value_changed",
        evidence_sources=("ms1_trace",),
        evidence_summary="successor has stronger multi-evidence support",
        validation_tier="synthetic_fixture",
        reviewer_role="implementation-contract-reviewer",
        reviewer_verdict="approved",
        final_label="expected_diff",
    )

    result = model_select_peak_hypothesis(
        (legacy, successor),
        successor_selected_candidate_id=successor.hypothesis_id,
        expected_diff_approval=synthetic_record,
    )

    assert result.selection_status == "expected_diff"
    assert result.product_switch_allowed is False
    assert "matrix_expected_diff_requires_real_validation" in result.diff_reasons


def test_final_matrix_expected_diff_requires_assessed_matrix_impact() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")
    not_assessed_record = ExpectedDiffApprovalRecord(
        stable_row_id=_stable_row_id(legacy, successor),
        sample_name="SampleA",
        target_label="Analyte",
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
        public_outputs_touched=(
            "candidate table selected marker",
            "confidence",
            "final matrix value",
        ),
        matrix_value_impact="not_assessed",
        evidence_sources=("ms1_trace",),
        evidence_summary="successor has stronger multi-evidence support",
        validation_tier="targeted_benchmark",
        reviewer_role="implementation-contract-reviewer",
        reviewer_verdict="approved",
        final_label="expected_diff",
    )

    result = model_select_peak_hypothesis(
        (legacy, successor),
        successor_selected_candidate_id=successor.hypothesis_id,
        expected_diff_approval=not_assessed_record,
    )

    assert result.selection_status == "expected_diff"
    assert result.product_switch_allowed is False
    assert "matrix_expected_diff_requires_assessed_impact" in result.diff_reasons


def test_expected_diff_requires_validation_and_row_evidence() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")
    incomplete_record = ExpectedDiffApprovalRecord(
        stable_row_id="",
        sample_name="SampleA",
        target_label="Analyte",
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
        public_outputs_touched=("candidate table selected marker", "confidence"),
        matrix_value_impact="none",
        evidence_sources=(),
        evidence_summary="",
        validation_tier="not_validated",
        reviewer_role="implementation-contract-reviewer",
        reviewer_verdict="approved",
        final_label="expected_diff",
    )

    result = model_select_peak_hypothesis(
        (legacy, successor),
        expected_diff_approval=incomplete_record,
    )

    assert result.selection_status == "expected_diff"
    assert result.product_switch_allowed is False
    assert "expected_diff_missing_stable_row_id" in result.diff_reasons
    assert "expected_diff_missing_evidence_sources" in result.diff_reasons
    assert "expected_diff_missing_evidence_summary" in result.diff_reasons
    assert "expected_diff_requires_validation" in result.diff_reasons


def test_expected_diff_cannot_underdeclare_area_change_as_confidence_only() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW", area=100.0)
    successor = _hypothesis(
        "successor",
        selected=False,
        confidence="HIGH",
        area=200.0,
    )
    underdeclared_record = ExpectedDiffApprovalRecord(
        stable_row_id=_stable_row_id(legacy, successor),
        sample_name="SampleA",
        target_label="Analyte",
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
        public_outputs_touched=("confidence",),
        matrix_value_impact="none",
        evidence_sources=("ms1_trace",),
        evidence_summary="successor has stronger multi-evidence support",
        validation_tier="targeted_benchmark",
        reviewer_role="implementation-contract-reviewer",
        reviewer_verdict="approved",
        final_label="expected_diff",
    )

    result = model_select_peak_hypothesis(
        (legacy, successor),
        expected_diff_approval=underdeclared_record,
    )

    assert result.selection_status == "expected_diff"
    assert result.product_switch_allowed is False
    assert "expected_diff_missing_area_impact" in result.diff_reasons
    assert "matrix_expected_diff_area_impact_mismatch" in result.diff_reasons


def test_approved_non_matrix_expected_diff_can_product_switch() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")
    approval = ExpectedDiffApprovalRecord(
        stable_row_id=_stable_row_id(legacy, successor),
        sample_name="SampleA",
        target_label="Analyte",
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
        public_outputs_touched=(
            "candidate table selected marker",
            "confidence",
            "reason",
        ),
        matrix_value_impact="none",
        evidence_sources=("ms1_trace", "trace_morphology"),
        evidence_summary="successor projection is better supported",
        validation_tier="synthetic_fixture",
        reviewer_role="implementation-contract-reviewer",
        reviewer_verdict="approved",
        final_label="expected_diff",
    )

    result = model_select_peak_hypothesis(
        (legacy, successor),
        expected_diff_approval=approval,
    )

    assert result.selected_candidate_id == successor.hypothesis_id
    assert result.selection_status == "expected_diff"
    assert result.diff_reasons == ()
    assert result.product_switch_allowed is True


def test_expected_diff_approval_lookup_requires_matching_row_and_candidates() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")
    result = model_select_peak_hypothesis((legacy, successor))
    approval = ExpectedDiffApprovalRecord(
        stable_row_id=_stable_row_id(legacy, successor),
        sample_name="SampleA",
        target_label="Analyte",
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
        public_outputs_touched=(
            "candidate table selected marker",
            "confidence",
            "reason",
        ),
        matrix_value_impact="none",
        evidence_sources=("ms1_trace", "trace_morphology"),
        evidence_summary="successor projection is better supported",
        validation_tier="synthetic_fixture",
        reviewer_role="implementation-contract-reviewer",
        reviewer_verdict="approved",
        final_label="expected_diff",
    )

    assert (
        expected_diff_approval_for_result(
            result,
            {approval.stable_row_id: approval},
            sample_name="SampleA",
            target_label="Analyte",
        )
        is approval
    )
    assert (
        expected_diff_approval_for_result(
            result,
            {"wrong-key": approval},
            sample_name="SampleA",
            target_label="Analyte",
        )
        is None
    )
    assert (
        expected_diff_approval_for_result(
            result,
            {"fixture-2": approval},
            sample_name="OtherSample",
            target_label="Analyte",
        )
        is None
    )


def test_ms2_expected_diff_is_inconclusive_under_limited_evidence_shadow() -> None:
    legacy = _hypothesis("legacy", selected=True, confidence="LOW")
    successor = _hypothesis("successor", selected=False, confidence="HIGH")
    approval = ExpectedDiffApprovalRecord(
        stable_row_id=_stable_row_id(legacy, successor),
        sample_name="SampleA",
        target_label="Analyte",
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
        public_outputs_touched=("candidate table selected marker", "confidence"),
        matrix_value_impact="none",
        evidence_sources=("MS2 trace",),
        evidence_summary="candidate MS2/NL supports successor",
        validation_tier="synthetic_fixture",
        reviewer_role="implementation-contract-reviewer",
        reviewer_verdict="approved",
        final_label="expected_diff",
    )

    result = model_select_peak_hypothesis(
        (legacy, successor),
        successor_selected_candidate_id=successor.hypothesis_id,
        expected_diff_approval=approval,
        evidence_comparison_policy="limited_evidence_shadow",
    )

    assert result.selection_status == "inconclusive"
    assert result.product_switch_allowed is False
    assert (
        "ms2_expected_diff_requires_complete_candidate_evidence"
        in result.diff_reasons
    )


def _hypothesis(
    suffix: str,
    *,
    selected: bool,
    confidence: str = "HIGH",
    reason: str = "decision: accepted",
    decision_class: str = "accepted",
    support_reasons: tuple[str, ...] = ("ms1_coherent",),
    conflict_reasons: tuple[str, ...] = (),
    review_reasons: tuple[str, ...] = (),
    raw_score: int | None = None,
    area: float = 1234.0,
) -> PeakHypothesis:
    return PeakHypothesis(
        hypothesis_id=f"SampleA|Analyte|{suffix}",
        trace_group_id="SampleA|Analyte|trace",
        target_label="Analyte",
        role="Analyte",
        istd_pair="ISTD",
        analysis_mode="targeted",
        resolver_mode="region_first_safe_merge",
        integration=IntegrationResult(
            rt_left_min=8.4,
            rt_apex_min=8.5,
            rt_right_min=8.6,
            raw_apex_rt_min=8.5,
            rt_width_min=0.2,
            height_raw=1200.0,
            height_smoothed=1100.0,
            area_raw_counts_seconds=area,
        ),
        evidence=EvidenceVector(
            confidence=confidence,
            raw_score=raw_score,
            reason=reason,
            decision_semantics=EvidenceDecisionSemantics(
                decision_class=decision_class,
                support_reasons=support_reasons,
                conflict_reasons=conflict_reasons,
                review_reasons=review_reasons,
                compatibility_labels=("strict_nl_ok",),
            ),
        ),
        audit=AuditTrail(
            selected=selected,
            selection_rank=1 if selected else 2,
            selection_reference_rt_min=8.5,
        ),
    )


def _stable_row_id(legacy: PeakHypothesis, successor: PeakHypothesis) -> str:
    return expected_diff_stable_row_id(
        legacy_selected_candidate_id=legacy.hypothesis_id,
        successor_selected_candidate_id=successor.hypothesis_id,
    )
