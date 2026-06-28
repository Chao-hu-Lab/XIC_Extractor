import inspect

from xic_extractor import decision_policy as shared_decision_policy
from xic_extractor.alignment import (
    matrix_identity,
    production_decisions,
)
from xic_extractor.evidence_semantics import EvidenceDecisionSemantics
from xic_extractor.peak_detection import (
    candidate_selection,
    model_selection,
)
from xic_extractor.peak_detection import (
    decision_policy as peak_decision_policy,
)
from xic_extractor.peak_detection.hypotheses import (
    AuditTrail,
    EvidenceVector,
    IntegrationResult,
    PeakHypothesis,
)
from xic_extractor.peak_detection.selection_decision import (
    selection_decision_from_hypothesis,
)


def test_selection_decision_uses_typed_projection_when_available() -> None:
    hypothesis = _hypothesis(
        evidence=EvidenceVector(
            confidence="VERY_LOW",
            reason="legacy score says review only",
            projected_confidence="HIGH",
            projected_reason="decision: accepted by typed evidence",
            decision_semantics=EvidenceDecisionSemantics(
                decision_class="accepted",
                support_reasons=("ms1_coherent",),
            ),
        )
    )

    decision = selection_decision_from_hypothesis(hypothesis)

    assert decision.projected_confidence == "HIGH"
    assert decision.projected_reason == "decision: accepted by typed evidence"
    assert decision.compatibility_oracle == "successor_evidence_decision_semantics"


def test_model_selection_key_does_not_read_legacy_score_or_label_counts() -> None:
    legacy = _hypothesis(
        "legacy",
        selected=True,
        evidence=EvidenceVector(
            confidence="VERY_LOW",
            raw_score=999,
            support_labels=("a", "b", "c", "d", "e"),
            projected_confidence="LOW",
            projected_reason="decision: review",
            decision_semantics=EvidenceDecisionSemantics(
                decision_class="review",
                review_reasons=("missing_ms2_not_observed",),
            ),
        ),
    )
    successor = _hypothesis(
        "successor",
        selected=False,
        evidence=EvidenceVector(
            confidence="HIGH",
            raw_score=-999,
            support_labels=(),
            projected_confidence="HIGH",
            projected_reason="decision: accepted",
            decision_semantics=EvidenceDecisionSemantics(
                decision_class="accepted",
                support_reasons=("ms1_coherent",),
            ),
        ),
    )

    result = model_selection.model_select_peak_hypothesis((legacy, successor))

    assert result.selected_candidate_id == successor.hypothesis_id


def test_active_selector_source_has_no_legacy_raw_score_or_label_tie_break() -> None:
    source = inspect.getsource(candidate_selection.select_candidate_by_evidence)

    assert "raw_score" not in source
    assert "support_labels" not in source
    assert "concern_labels" not in source
    assert "evidence_score" not in source


def test_decision_policy_exposes_no_shared_record_ordering_helper() -> None:
    helper_name = "decision_record_" "ordering_key"
    assert not hasattr(shared_decision_policy, helper_name)
    assert not hasattr(peak_decision_policy, helper_name)


def test_decision_record_ordering_stays_selection_local() -> None:
    flatten_expression = "(*record.gate, *record.tie_break)"
    selection_sources = (
        inspect.getsource(candidate_selection._candidate_selection_ordering_key),
        inspect.getsource(model_selection._peak_hypothesis_selection_ordering_key),
    )

    assert all(flatten_expression in source for source in selection_sources)

    non_selection_sources = (
        inspect.getsource(shared_decision_policy),
        inspect.getsource(peak_decision_policy),
        inspect.getsource(matrix_identity),
        inspect.getsource(production_decisions),
    )
    non_selection_source = "\n".join(non_selection_sources)

    assert flatten_expression not in non_selection_source
    assert "ordering_key" not in non_selection_source


def _hypothesis(
    suffix: str = "selected",
    *,
    selected: bool = True,
    evidence: EvidenceVector,
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
            area_raw_counts_seconds=1234.0,
        ),
        evidence=evidence,
        audit=AuditTrail(
            selected=selected,
            selection_rank=1 if selected else 2,
            selection_reference_rt_min=8.5,
        ),
    )
