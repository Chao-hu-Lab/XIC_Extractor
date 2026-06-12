from xic_extractor.diagnostics.backfill_decision_explanation import (
    BackfillDecisionExplanation,
    decision_explanation,
)


def test_decision_explanation_serializes_reason_and_warning_tokens() -> None:
    explanation = BackfillDecisionExplanation(
        decision="context",
        reasons=("identity_supported_review", "missing_projected_matrix_value"),
        warnings=("projection_accept_without_positive_area",),
        production_gap="needs_ms1_same_peak_evidence",
    )

    assert explanation.reason_text == (
        "identity_supported_review;missing_projected_matrix_value"
    )
    assert explanation.warning_text == "projection_accept_without_positive_area"
    assert explanation.production_gap == "needs_ms1_same_peak_evidence"


def test_decision_explanation_helper_accepts_single_or_multiple_reasons() -> None:
    assert decision_explanation("block", "missing_seed").reasons == ("missing_seed",)
    assert decision_explanation(
        "block",
        ("missing_seed", "visual_conflict"),
        warnings=("same_peak_multi_claim",),
    ) == BackfillDecisionExplanation(
        decision="block",
        reasons=("missing_seed", "visual_conflict"),
        warnings=("same_peak_multi_claim",),
    )
