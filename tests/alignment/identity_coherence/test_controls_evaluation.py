from dataclasses import replace

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.controls import (
    IdentityControlManifestEntry,
    evaluate_positive_control,
)
from xic_extractor.alignment.identity_coherence.schema import (
    ControlStatus,
    ControlType,
    FragmentObservationMode,
    IdentityDecision,
    PositiveControlMappingStatus,
)


def _positive_entry(**overrides):
    values = dict(
        control_id="CTRL-ISTD-1",
        control_type=ControlType.POSITIVE_TARGETED_ISTD,
        control_name="ISTD 5mdC",
        expected_mapping_status=PositiveControlMappingStatus.MAPPED,
        control_expected_behavior="would_primary",
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        rt_tolerance_sec=60.0,
        required_failure_reason_when_missed="review_only_insufficient_support",
        decision_id="DEC-1",
        positive_control_target_name="5mdC",
        positive_control_target_mz=500.0,
        positive_control_target_rt_sec=300.0,
        positive_control_mapping_error_ppm=0.2,
        positive_control_mapping_delta_rt_sec=2.0,
    )
    values.update(overrides)
    return IdentityControlManifestEntry(**values)


def _record_with_identity(record, *, decision_id, seed_candidate_id):
    decision = replace(
        record.row_result.decision,
        decision_id=decision_id,
        seed_candidate_id=seed_candidate_id,
    )
    seed_gate = replace(
        record.seed_gate,
        resolved_request=replace(
            record.seed_gate.resolved_request,
            decision_id=decision_id,
            seed_candidate_id=seed_candidate_id,
        ),
    )
    return replace(
        record,
        seed_gate=seed_gate,
        row_result=replace(record.row_result, decision=decision),
    )


def test_evaluate_positive_control_passes_mapped_would_primary():
    row = evaluate_positive_control(_positive_entry(), (output_record(),))

    assert row["control_id"] == "CTRL-ISTD-1"
    assert row["control_type"] == ControlType.POSITIVE_TARGETED_ISTD.value
    assert row["decision_id"] == "DEC-1"
    assert row["identity_family_id"] == "IDF-1"
    assert row["seed_candidate_id"] == "CAND-1"
    assert row["control_status"] == ControlStatus.ASSESSED.value
    assert row["control_observed_behavior"] == (
        "would_primary_provisional_identity_family_support"
    )
    assert row["control_pass"] is True
    assert row["control_failure_reason"] == ""
    assert row["positive_control_mapping_status"] == (
        PositiveControlMappingStatus.MAPPED.value
    )
    assert row["positive_control_target_name"] == "5mdC"


def test_evaluate_positive_control_fails_when_mapped_row_is_not_promoted():
    record = output_record()
    failed_decision = replace(
        record.row_result.decision,
        decision=IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT,
        decision_reason="insufficient_support",
    )
    failed_record = replace(
        record,
        row_result=replace(record.row_result, decision=failed_decision),
    )

    row = evaluate_positive_control(_positive_entry(), (failed_record,))

    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "review_only_insufficient_support"
    assert row["control_failure_reason"] == "review_only_insufficient_support"


def test_evaluate_positive_control_uses_actual_decision_as_failure_reason():
    record = output_record()
    failed_decision = replace(
        record.row_result.decision,
        decision=IdentityDecision.REVIEW_ONLY_SEED_GATE_FAILED,
        decision_reason="seed_gate_failed",
    )
    failed_record = replace(
        record,
        row_result=replace(record.row_result, decision=failed_decision),
    )

    row = evaluate_positive_control(_positive_entry(), (failed_record,))

    assert row["control_observed_behavior"] == "review_only_seed_gate_failed"
    assert row["control_failure_reason"] == "review_only_seed_gate_failed"


def test_evaluate_positive_control_fails_mapping_error_ppm_out_of_tolerance():
    row = evaluate_positive_control(
        _positive_entry(positive_control_mapping_error_ppm=11.0),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == (
        PositiveControlMappingStatus.UNMAPPED.value
    )
    assert row["control_failure_reason"] == (
        "positive_control_mapping_out_of_tolerance"
    )


def test_evaluate_positive_control_fails_missing_mapping_evidence():
    row = evaluate_positive_control(
        _positive_entry(positive_control_mapping_error_ppm=None),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == (
        PositiveControlMappingStatus.UNMAPPED.value
    )
    assert row["control_failure_reason"] == (
        "positive_control_mapping_missing_evidence"
    )


def test_evaluate_positive_control_unmapped_when_decision_id_missing():
    row = evaluate_positive_control(
        _positive_entry(decision_id="MISSING-DECISION"),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == (
        PositiveControlMappingStatus.UNMAPPED.value
    )
    assert row["control_failure_reason"] == "unmapped"


def test_evaluate_positive_control_reports_identity_family_id_ambiguous_mapping():
    first = output_record()
    second = _record_with_identity(
        first,
        decision_id="DEC-2",
        seed_candidate_id="CAND-2",
    )

    row = evaluate_positive_control(
        _positive_entry(decision_id="", identity_family_id="IDF-1"),
        (first, second),
    )

    assert row["control_status"] == ControlStatus.AMBIGUOUS_MAPPING.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == (
        PositiveControlMappingStatus.AMBIGUOUS_MAPPING.value
    )
    assert row["control_failure_reason"] == "ambiguous_mapping"


def test_evaluate_positive_control_reports_conflicting_manifest_keys():
    first = output_record()
    second = _record_with_identity(
        first,
        decision_id="DEC-2",
        seed_candidate_id="CAND-2",
    )

    row = evaluate_positive_control(
        _positive_entry(decision_id="DEC-1", seed_candidate_id="CAND-2"),
        (first, second),
    )

    assert row["control_status"] == ControlStatus.AMBIGUOUS_MAPPING.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == (
        PositiveControlMappingStatus.AMBIGUOUS_MAPPING.value
    )
    assert row["control_failure_reason"] == "ambiguous_mapping"


def test_evaluate_positive_control_reports_expected_mapping_status_mismatch():
    row = evaluate_positive_control(
        _positive_entry(expected_mapping_status=PositiveControlMappingStatus.UNMAPPED),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == (
        PositiveControlMappingStatus.UNMAPPED.value
    )
    assert row["control_failure_reason"] == "expected_mapping_status_mismatch"


def test_positive_control_labels_do_not_mutate_decision_summary():
    record = output_record()
    before = record.row_result.decision

    evaluate_positive_control(_positive_entry(), (record,))

    assert record.row_result.decision is before
    assert before.decision is IdentityDecision.WOULD_PRIMARY
