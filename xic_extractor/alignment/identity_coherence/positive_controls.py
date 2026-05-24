from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from .control_models import (
    IdentityCoherenceOutputRecordLike,
    IdentityControlManifestEntry,
    _enum_value,
    _is_finite_number,
    _record_match_constraints,
    _record_value,
)
from .control_rows import control_row
from .schema import ControlStatus, ControlType, PositiveControlMappingStatus


def evaluate_positive_control(
    entry: IdentityControlManifestEntry,
    records: Sequence[IdentityCoherenceOutputRecordLike],
) -> dict[str, object]:
    if entry.control_type is not ControlType.POSITIVE_TARGETED_ISTD:
        raise ValueError("evaluate_positive_control requires positive_targeted_istd")

    mapping_status, record = _resolve_record_for_entry(entry, records)
    mapping_status, mapping_failure_reason = _validate_positive_control_mapping(
        entry,
        mapping_status,
    )
    if record is None or mapping_failure_reason:
        control_status = _control_status_for_mapping_status(mapping_status)
        failure_reason = mapping_failure_reason or str(_enum_value(mapping_status))
        return control_row(
            entry,
            control_status=control_status,
            control_observed_behavior=failure_reason,
            control_pass=False,
            control_failure_reason=failure_reason,
            positive_control_mapping_status=mapping_status,
        )

    decision = record.row_result.decision
    observed = str(_enum_value(decision.decision))
    passed = observed == "would_primary_provisional_identity_family_support"
    failure_reason = "" if passed else observed
    control_notes = (
        entry.control_notes
        if passed
        else _append_control_note(
            entry.control_notes,
            "required_failure_reason_when_missed="
            f"{entry.required_failure_reason_when_missed}",
        )
    )
    return control_row(
        entry,
        decision_id=decision.decision_id,
        identity_family_id=decision.identity_family_id,
        seed_candidate_id=decision.seed_candidate_id,
        control_status=ControlStatus.ASSESSED,
        control_observed_behavior=observed,
        control_pass=passed,
        control_failure_reason=failure_reason,
        positive_control_mapping_status=mapping_status,
        control_notes=control_notes,
    )


def _validate_positive_control_mapping(
    entry: IdentityControlManifestEntry,
    mapping_status: PositiveControlMappingStatus,
) -> tuple[PositiveControlMappingStatus, str]:
    if mapping_status is not PositiveControlMappingStatus.MAPPED:
        return mapping_status, str(_enum_value(mapping_status))
    if entry.expected_mapping_status is not PositiveControlMappingStatus.MAPPED:
        return (
            PositiveControlMappingStatus.UNMAPPED,
            "expected_mapping_status_mismatch",
        )

    mapping_numbers = (
        entry.positive_control_target_mz,
        entry.positive_control_target_rt_sec,
        entry.positive_control_mapping_error_ppm,
        entry.positive_control_mapping_delta_rt_sec,
    )
    if not all(_is_finite_number(value) for value in mapping_numbers):
        return (
            PositiveControlMappingStatus.UNMAPPED,
            "positive_control_mapping_missing_evidence",
        )
    mapping_error_ppm = float(cast(float, entry.positive_control_mapping_error_ppm))
    mapping_delta_rt_sec = float(
        cast(float, entry.positive_control_mapping_delta_rt_sec)
    )
    if (
        abs(mapping_error_ppm) > entry.precursor_tolerance_ppm
        or abs(mapping_delta_rt_sec) > entry.rt_tolerance_sec
    ):
        return (
            PositiveControlMappingStatus.UNMAPPED,
            "positive_control_mapping_out_of_tolerance",
        )
    return PositiveControlMappingStatus.MAPPED, ""


def _control_status_for_mapping_status(
    mapping_status: PositiveControlMappingStatus,
) -> ControlStatus:
    if mapping_status is PositiveControlMappingStatus.AMBIGUOUS_MAPPING:
        return ControlStatus.AMBIGUOUS_MAPPING
    if mapping_status is PositiveControlMappingStatus.MAPPED:
        return ControlStatus.ASSESSED
    return ControlStatus.UNMAPPED


def _resolve_record_for_entry(
    entry: IdentityControlManifestEntry,
    records: Sequence[IdentityCoherenceOutputRecordLike],
) -> tuple[PositiveControlMappingStatus, IdentityCoherenceOutputRecordLike | None]:
    supplied = _record_match_constraints(entry)
    if not supplied:
        return PositiveControlMappingStatus.UNMAPPED, None

    exact_matches = [
        record
        for record in records
        if all(_record_value(record, field) == value for field, value in supplied)
    ]
    if len(exact_matches) == 1:
        return PositiveControlMappingStatus.MAPPED, exact_matches[0]
    if len(exact_matches) > 1:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None

    partial_fields = {
        field
        for field, value in supplied
        if any(_record_value(record, field) == value for record in records)
    }
    if partial_fields:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None
    return PositiveControlMappingStatus.UNMAPPED, None


def _append_control_note(existing: str, note: str) -> str:
    if not existing:
        return note
    return f"{existing}; {note}"
