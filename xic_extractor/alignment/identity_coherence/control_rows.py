from __future__ import annotations

from .control_models import IdentityControlManifestEntry
from .schema import (
    ControlStatus,
    DecoyGenerationMethod,
    PositiveControlMappingStatus,
)


def control_row(
    entry: IdentityControlManifestEntry,
    *,
    decision_id: str = "",
    identity_family_id: str = "",
    seed_candidate_id: str = "",
    control_status: ControlStatus,
    control_observed_behavior: str,
    control_pass: bool | str,
    control_failure_reason: str,
    positive_control_mapping_status: PositiveControlMappingStatus,
    decoy_generation_method: DecoyGenerationMethod | None = None,
    decoy_source_request_id: str = "",
    decoy_shift_value: float | str = "",
    decoy_identity_constraint_changed: str = "",
    control_notes: str | None = None,
) -> dict[str, object]:
    return {
        "control_id": entry.control_id,
        "control_type": entry.control_type,
        "control_name": entry.control_name,
        "decision_id": decision_id or entry.decision_id,
        "identity_family_id": identity_family_id or entry.identity_family_id,
        "seed_candidate_id": seed_candidate_id or entry.seed_candidate_id,
        "control_status": control_status,
        "control_expected_behavior": entry.control_expected_behavior,
        "control_observed_behavior": control_observed_behavior,
        "control_pass": control_pass,
        "control_failure_reason": control_failure_reason,
        "fragment_observation_mode": entry.fragment_observation_mode,
        "decoy_generation_method": decoy_generation_method or "",
        "decoy_source_request_id": decoy_source_request_id,
        "decoy_shift_value": decoy_shift_value,
        "decoy_identity_constraint_changed": decoy_identity_constraint_changed,
        "positive_control_mapping_status": positive_control_mapping_status,
        "positive_control_target_name": entry.positive_control_target_name,
        "positive_control_target_mz": entry.positive_control_target_mz,
        "positive_control_target_rt_sec": entry.positive_control_target_rt_sec,
        "positive_control_mapping_error_ppm": (
            entry.positive_control_mapping_error_ppm
        ),
        "positive_control_mapping_delta_rt_sec": (
            entry.positive_control_mapping_delta_rt_sec
        ),
        "control_notes": (
            entry.control_notes if control_notes is None else control_notes
        ),
    }
