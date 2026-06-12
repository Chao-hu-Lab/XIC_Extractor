from tools.diagnostics.targeted_peak_reliability_classifier import _summarize_rows
from tools.diagnostics.targeted_peak_reliability_models import (
    ReliabilityState,
    TargetedReliabilityRow,
)


def test_summarize_rows_counts_states_once_and_preserves_summary_contract() -> None:
    summaries = _summarize_rows(
        (
            _row(
                "S1",
                "target-b",
                "Target",
                "targeted_review",
                ("low_confidence", "no_ms2"),
                known_exception="manual_exception",
            ),
            _row(
                "S2",
                "target-a",
                "ISTD",
                "benchmark_eligible",
                (),
            ),
            _row(
                "S3",
                "target-b",
                "Target",
                "targeted_review_positive",
                ("plausible_nl_dropout",),
                known_exception="later_exception",
            ),
            _row(
                "S4",
                "target-b",
                "Target",
                "targeted_negative",
                ("no_usable_peak",),
            ),
            _row(
                "S5",
                "target-b",
                "Target",
                "benchmark_eligible",
                ("low_confidence",),
            ),
        )
    )

    assert [summary.target_label for summary in summaries] == ["target-a", "target-b"]
    assert summaries[0].role == "ISTD"
    assert summaries[0].benchmark_eligible_count == 1
    assert summaries[0].top_risk_reasons == ""

    target_b = summaries[1]
    assert target_b.role == "Target"
    assert target_b.benchmark_eligible_count == 1
    assert target_b.targeted_review_positive_count == 1
    assert target_b.targeted_review_count == 1
    assert target_b.targeted_negative_count == 1
    assert target_b.top_risk_reasons == (
        "low_confidence;no_ms2;plausible_nl_dropout;no_usable_peak"
    )
    assert target_b.known_exception == "manual_exception"


def _row(
    sample_name: str,
    target_label: str,
    role: str,
    reliability_state: ReliabilityState,
    risk_reasons: tuple[str, ...],
    *,
    known_exception: str = "",
) -> TargetedReliabilityRow:
    return TargetedReliabilityRow(
        sample_name=sample_name,
        target_label=target_label,
        role=role,
        rt=1.0,
        area=100.0,
        confidence="HIGH",
        nl="OK",
        prior_rt=None,
        prior_source="",
        total_severity=None,
        quality_flags="",
        reliability_state=reliability_state,
        risk_reasons=risk_reasons,
        known_exception=known_exception,
    )
