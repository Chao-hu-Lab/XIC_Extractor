from dataclasses import replace

import pytest

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence import controls as controls_module
from xic_extractor.alignment.identity_coherence.controls import (
    IdentityControlManifestEntry,
    IdentityControlsConfig,
    IdentityDecoySource,
    evaluate_identity_controls,
    evaluate_identity_decoy,
    evaluate_positive_control,
)
from xic_extractor.alignment.identity_coherence.models import (
    SeedCandidateEvidence,
    SeedGateConfig,
)
from xic_extractor.alignment.identity_coherence.schema import (
    ControlStatus,
    ControlType,
    DecoyGenerationMethod,
    EvidenceStage,
    FragmentObservationMode,
    IdentityDecision,
    PositiveControlMappingStatus,
    SeedRejectReason,
)
from xic_extractor.alignment.identity_coherence.seed_gate import (
    evaluate_seed_gate as real_evaluate_seed_gate,
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
    assert row["control_notes"] == (
        "required_failure_reason_when_missed=review_only_insufficient_support"
    )


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


class OwnerLike:
    owner_apex_rt = 5.0
    owner_peak_start_rt = 4.90
    owner_peak_end_rt = 5.10
    owner_area = 1000.0
    owner_height = 200.0


class MissingOwnerPeakStartLike:
    owner_apex_rt = 5.0
    owner_peak_end_rt = 5.10
    owner_area = 1000.0
    owner_height = 200.0


class NonfiniteOwnerAreaLike:
    owner_apex_rt = 5.0
    owner_peak_start_rt = 4.90
    owner_peak_end_rt = 5.10
    owner_area = float("nan")
    owner_height = 200.0


class MissingOwnerPeakEndLike:
    owner_apex_rt = 5.0
    owner_peak_start_rt = 4.90
    owner_area = 1000.0
    owner_height = 200.0


class NonfiniteOwnerPeakEndLike:
    owner_apex_rt = 5.0
    owner_peak_start_rt = 4.90
    owner_peak_end_rt = float("inf")
    owner_area = 1000.0
    owner_height = 200.0


def _decoy_entry(method, **overrides):
    values = dict(
        control_id=f"CTRL-DECOY-{method.value}",
        control_type=ControlType.IDENTITY_DECOY,
        control_name=f"{method.value} decoy",
        expected_mapping_status=PositiveControlMappingStatus.MAPPED,
        control_expected_behavior="not_would_primary",
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        rt_tolerance_sec=60.0,
        required_failure_reason_when_missed="request_candidate_identity_mismatch",
        decision_id="DEC-1",
        decoy_generation_method=method,
    )
    values.update(overrides)
    return IdentityControlManifestEntry(**values)


def _decoy_source():
    return IdentityDecoySource(
        source_record=output_record(),
        seed_evidence=SeedCandidateEvidence(
            candidate_id="CAND-1",
            precursor_mz=500.0,
            product_mz=384.0,
            cid_observed_loss_da=116.0,
            fragment_tags=("MeR", "dR"),
            best_seed_rt=5.0,
            ms1_scan_support_score=0.9,
            evidence_stage=EvidenceStage.PRE_BACKFILL,
        ),
        owner_like=OwnerLike(),
    )


def test_rt_shift_decoy_uses_owner_boundary_plus_seconds_margin(monkeypatch):
    captured = {}

    def capture_seed_gate(request, candidate_evidence, owner_like, **kwargs):
        captured["best_seed_rt"] = candidate_evidence.best_seed_rt
        return real_evaluate_seed_gate(
            request,
            candidate_evidence,
            owner_like,
            **kwargs,
        )

    monkeypatch.setattr(controls_module, "evaluate_seed_gate", capture_seed_gate)

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        _decoy_source(),
        IdentityControlsConfig(decoy_rt_owner_boundary_margin_sec=6.0),
    )

    assert captured["best_seed_rt"] == pytest.approx(5.20)
    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == (
        SeedRejectReason.SEED_RT_OUTSIDE_OWNER_PEAK.value
    )
    assert row["decoy_generation_method"] == "rt_shift"
    assert row["decoy_shift_value"] == 6.0
    assert row["decoy_identity_constraint_changed"] == "best_seed_rt"


def test_mz_shift_decoy_fails_request_candidate_identity_match(monkeypatch):
    captured = {}

    def capture_seed_gate(request, candidate_evidence, owner_like, **kwargs):
        captured["request_precursor_mz"] = request.identity.precursor_mz
        captured["request_product_mz"] = request.identity.product_mz
        captured["evidence_precursor_mz"] = candidate_evidence.precursor_mz
        captured["evidence_product_mz"] = candidate_evidence.product_mz
        return real_evaluate_seed_gate(
            request,
            candidate_evidence,
            owner_like,
            **kwargs,
        )

    monkeypatch.setattr(controls_module, "evaluate_seed_gate", capture_seed_gate)

    row = evaluate_identity_decoy(
        _decoy_entry(DecoyGenerationMethod.MZ_SHIFT),
        _decoy_source(),
        IdentityControlsConfig(),
    )

    assert captured["request_precursor_mz"] > 500.0
    assert captured["request_product_mz"] > 384.0
    assert captured["evidence_precursor_mz"] == 500.0
    assert captured["evidence_product_mz"] == 384.0
    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == (
        SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH.value
    )
    assert row["decoy_identity_constraint_changed"] == "precursor_mz;product_mz"


def test_fragment_tag_shuffle_decoy_uses_manifest_tags_for_request(monkeypatch):
    source = _decoy_source()
    original_mode_constraint = (
        source.source_record.seed_gate.resolved_request.identity.mode_constraint
    )
    captured = {}

    def capture_seed_gate(request, candidate_evidence, owner_like, **kwargs):
        captured["request_fragment_tags"] = request.identity.fragment_tags
        captured["evidence_fragment_tags"] = candidate_evidence.fragment_tags
        captured["mode_constraint"] = request.identity.mode_constraint
        return real_evaluate_seed_gate(
            request,
            candidate_evidence,
            owner_like,
            **kwargs,
        )

    monkeypatch.setattr(controls_module, "evaluate_seed_gate", capture_seed_gate)

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.FRAGMENT_TAG_SHUFFLE,
            decoy_fragment_tags=("other_diagnostic_tag",),
        ),
        source,
        IdentityControlsConfig(),
    )

    assert captured["request_fragment_tags"] == ("other_diagnostic_tag",)
    assert captured["evidence_fragment_tags"] == ("MeR", "dR")
    assert captured["mode_constraint"] is original_mode_constraint
    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == (
        SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH.value
    )
    assert row["decoy_identity_constraint_changed"] == "fragment_tags"


def test_fragment_tag_shuffle_decoy_generates_default_unmatched_tag(monkeypatch):
    captured = {}

    def capture_seed_gate(request, candidate_evidence, owner_like, **kwargs):
        captured["request_fragment_tags"] = request.identity.fragment_tags
        return real_evaluate_seed_gate(
            request,
            candidate_evidence,
            owner_like,
            **kwargs,
        )

    monkeypatch.setattr(controls_module, "evaluate_seed_gate", capture_seed_gate)

    row = evaluate_identity_decoy(
        _decoy_entry(DecoyGenerationMethod.FRAGMENT_TAG_SHUFFLE),
        _decoy_source(),
        IdentityControlsConfig(),
    )

    assert captured["request_fragment_tags"] == ("identity_decoy_unmatched_tag",)
    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == (
        SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH.value
    )


def test_decoy_that_reaches_coherent_seed_is_control_failure():
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        _decoy_source(),
        IdentityControlsConfig(decoy_rt_owner_boundary_margin_sec=6.0),
        seed_gate_config=SeedGateConfig(require_seed_rt_inside_owner_peak=False),
    )

    assert row["control_pass"] is False
    assert row["control_failure_reason"] == "decoy_seed_gate_coherent"


def test_decoy_rejected_by_earlier_seed_gate_still_passes_control():
    source = _decoy_source()
    source = replace(
        source,
        seed_evidence=replace(source.seed_evidence, ms1_scan_support_score=0.0),
    )

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        source,
        IdentityControlsConfig(),
        seed_gate_config=SeedGateConfig(require_seed_rt_inside_owner_peak=False),
    )

    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == "low_ms1_scan_support"
    assert row["control_failure_reason"] == ""


def test_decoy_rejects_backfill_only_seed_evidence():
    source = _decoy_source()
    source = replace(
        source,
        seed_evidence=replace(
            source.seed_evidence,
            evidence_stage=EvidenceStage.BACKFILL_ONLY,
        ),
    )

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        source,
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


def test_decoy_rejects_post_backfill_owner_evidence():
    source = replace(_decoy_source(), owner_evidence_stage=EvidenceStage.POST_BACKFILL)

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        source,
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


@pytest.mark.parametrize(
    "source_overrides",
    [
        {"owner_assignment_status": "ambiguous"},
        {"duplicate_loser": True},
    ],
)
def test_decoy_rejects_non_primary_or_duplicate_source(source_overrides):
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        replace(_decoy_source(), **source_overrides),
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


@pytest.mark.parametrize(
    "owner_like",
    [
        MissingOwnerPeakStartLike(),
        NonfiniteOwnerAreaLike(),
    ],
)
def test_mz_shift_decoy_rejects_missing_or_nonfinite_owner_fields(owner_like):
    row = evaluate_identity_decoy(
        _decoy_entry(DecoyGenerationMethod.MZ_SHIFT),
        replace(_decoy_source(), owner_like=owner_like),
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


@pytest.mark.parametrize(
    "owner_like",
    [
        MissingOwnerPeakEndLike(),
        NonfiniteOwnerPeakEndLike(),
    ],
)
def test_rt_shift_decoy_rejects_invalid_owner_peak_end_without_raising(owner_like):
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        replace(_decoy_source(), owner_like=owner_like),
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


def test_decoy_rejects_source_request_id_mismatch():
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.MZ_SHIFT,
            decoy_source_request_id="OTHER",
        ),
        _decoy_source(),
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"
    assert row["decoy_source_request_id"] == "REQ-1"


def test_decoy_accepts_matching_source_request_id():
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.MZ_SHIFT,
            decoy_source_request_id="REQ-1",
        ),
        _decoy_source(),
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.ASSESSED.value
    assert row["control_pass"] is True
    assert row["decoy_source_request_id"] == "REQ-1"


def test_evaluate_identity_controls_preserves_manifest_order():
    positive = _positive_entry(control_id="CTRL-A")
    decoy = _decoy_entry(
        DecoyGenerationMethod.MZ_SHIFT,
        control_id="CTRL-B",
    )

    result = evaluate_identity_controls(
        (positive, decoy),
        records=(output_record(),),
        decoy_sources=(_decoy_source(),),
        config=IdentityControlsConfig(),
    )

    rows = result.rows
    assert [row["control_id"] for row in rows] == ["CTRL-A", "CTRL-B"]
    assert [row["control_pass"] for row in rows] == [True, True]
    assert result.positive_control_pass_fraction == 1.0
    assert result.positive_control_threshold_met is True
    assert result.decoy_coherent_seed_count == 0
    assert result.decoy_coherent_seed_threshold_met is True


def test_evaluate_identity_controls_uses_facade_seed_gate_hook(monkeypatch):
    captured = {}

    def capture_seed_gate(request, candidate_evidence, owner_like, **kwargs):
        captured["called"] = True
        captured["best_seed_rt"] = candidate_evidence.best_seed_rt
        return real_evaluate_seed_gate(
            request,
            candidate_evidence,
            owner_like,
            **kwargs,
        )

    monkeypatch.setattr(controls_module, "evaluate_seed_gate", capture_seed_gate)

    result = evaluate_identity_controls(
        (_decoy_entry(DecoyGenerationMethod.RT_SHIFT),),
        records=(output_record(),),
        decoy_sources=(_decoy_source(),),
        config=IdentityControlsConfig(),
    )

    assert captured["called"] is True
    assert captured["best_seed_rt"] == pytest.approx(5.2)
    assert result.rows[0]["control_status"] == "assessed"


def test_evaluate_identity_controls_reports_missing_decoy_source():
    decoy = _decoy_entry(DecoyGenerationMethod.MZ_SHIFT)

    result = evaluate_identity_controls(
        (decoy,),
        records=(output_record(),),
        decoy_sources=(),
        config=IdentityControlsConfig(),
    )

    rows = result.rows
    assert rows[0]["control_status"] == "unmapped"
    assert rows[0]["control_pass"] is False
    assert rows[0]["control_failure_reason"] == "missing_decoy_source"


def test_evaluate_identity_controls_flags_request_id_key_conflict(monkeypatch):
    decoy = _decoy_entry(
        DecoyGenerationMethod.MZ_SHIFT,
        decoy_source_request_id="REQ-1",
        seed_candidate_id="OTHER",
    )

    def fail_if_evaluated(*args, **kwargs):
        raise AssertionError("conflicted decoy source must not be evaluated")

    monkeypatch.setattr(
        controls_module,
        "evaluate_identity_decoy",
        fail_if_evaluated,
    )

    result = evaluate_identity_controls(
        (decoy,),
        records=(output_record(),),
        decoy_sources=(_decoy_source(),),
        config=IdentityControlsConfig(),
    )

    row = result.rows[0]
    assert row["control_status"] == "ambiguous_mapping"
    assert row["control_pass"] is False
    assert row["control_failure_reason"] == "ambiguous_mapping"


def test_evaluate_identity_controls_flags_decoy_coherent_seed_threshold():
    decoy = _decoy_entry(
        DecoyGenerationMethod.RT_SHIFT,
        required_failure_reason_when_missed="seed_rt_outside_owner_peak",
    )
    source = _decoy_source()

    result = evaluate_identity_controls(
        (decoy,),
        records=(output_record(),),
        decoy_sources=(source,),
        config=IdentityControlsConfig(max_decoy_coherent_seed_count=0),
        seed_gate_config=SeedGateConfig(require_seed_rt_inside_owner_peak=False),
    )

    assert result.decoy_coherent_seed_count == 1
    assert result.decoy_coherent_seed_threshold_met is False


def test_identity_controls_config_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="positive_control_min_pass_fraction"):
        IdentityControlsConfig(positive_control_min_pass_fraction=1.5)
    with pytest.raises(ValueError, match="max_decoy_coherent_seed_count"):
        IdentityControlsConfig(max_decoy_coherent_seed_count=-1)
    with pytest.raises(ValueError, match="decoy_rt_owner_boundary_margin_sec"):
        IdentityControlsConfig(decoy_rt_owner_boundary_margin_sec=0.0)
