from __future__ import annotations

import math
from dataclasses import replace

from .control_models import (
    IdentityControlManifestEntry,
    IdentityControlsConfig,
    IdentityDecoySource,
    _enum_value,
    _is_finite_number,
)
from .control_rows import control_row
from .models import IdentityCoherenceRequest, SeedCandidateEvidence, SeedGateConfig
from .schema import (
    ControlStatus,
    ControlType,
    DecoyGenerationMethod,
    EvidenceStage,
    PositiveControlMappingStatus,
    RequestCandidateIdentityStatus,
)
from .seed_gate import evaluate_seed_gate
from .tags import format_fragment_tags

_REQUIRED_DECOY_OWNER_FIELDS: tuple[str, ...] = (
    "owner_apex_rt",
    "owner_peak_start_rt",
    "owner_peak_end_rt",
    "owner_area",
    "owner_height",
)


def evaluate_identity_decoy(
    entry: IdentityControlManifestEntry,
    source: IdentityDecoySource,
    config: IdentityControlsConfig,
    *,
    seed_gate_config: SeedGateConfig = SeedGateConfig(),
    seed_gate_evaluator=None,
) -> dict[str, object]:
    if seed_gate_evaluator is None:
        seed_gate_evaluator = evaluate_seed_gate

    if entry.control_type is not ControlType.IDENTITY_DECOY:
        raise ValueError("evaluate_identity_decoy requires identity_decoy")
    if entry.decoy_generation_method is None:
        raise ValueError("decoy_generation_method is required")

    source_decision = source.source_record.row_result.decision
    source_request_id = source.source_record.seed_gate.resolved_request.request_id
    provenance_failure = _decoy_source_provenance_failure(
        entry,
        source,
        source_request_id,
    )
    if provenance_failure:
        return control_row(
            entry,
            decision_id=source_decision.decision_id,
            identity_family_id=source_decision.identity_family_id,
            seed_candidate_id=source_decision.seed_candidate_id,
            control_status=ControlStatus.NOT_ASSESSED,
            control_observed_behavior=provenance_failure,
            control_pass=False,
            control_failure_reason=provenance_failure,
            positive_control_mapping_status=(
                PositiveControlMappingStatus.NOT_APPLICABLE
            ),
            decoy_generation_method=entry.decoy_generation_method,
            decoy_source_request_id=source_request_id,
        )

    request, evidence, changed, shift_value = _build_decoy_seed_inputs(
        entry,
        source,
        config,
    )
    result = seed_gate_evaluator(
        request,
        evidence,
        source.owner_like,
        owner_assignment_status=source.owner_assignment_status,
        duplicate_loser=source.duplicate_loser,
        owner_evidence_stage=source.owner_evidence_stage,
        config=seed_gate_config,
    )
    observed = (
        _enum_value(result.seed_reject_reason)
        if result.seed_reject_reason is not None
        else _enum_value(result.seed_gate_class)
    )
    if observed == "coherent_seed":
        passed = False
        failure_reason = "decoy_seed_gate_coherent"
    else:
        passed = True
        failure_reason = ""
    return control_row(
        entry,
        decision_id=source_decision.decision_id,
        identity_family_id=source_decision.identity_family_id,
        seed_candidate_id=source_decision.seed_candidate_id,
        control_status=ControlStatus.ASSESSED,
        control_observed_behavior=str(observed),
        control_pass=passed,
        control_failure_reason=failure_reason,
        positive_control_mapping_status=PositiveControlMappingStatus.NOT_APPLICABLE,
        decoy_generation_method=entry.decoy_generation_method,
        decoy_source_request_id=source_request_id,
        decoy_shift_value=shift_value,
        decoy_identity_constraint_changed=changed,
    )


def _decoy_source_provenance_failure(
    entry: IdentityControlManifestEntry,
    source: IdentityDecoySource,
    source_request_id: str,
) -> str:
    if (
        entry.decoy_source_request_id
        and entry.decoy_source_request_id != source_request_id
    ):
        return "invalid_decoy_source_stage"
    if (
        _enum_value(source.seed_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return "invalid_decoy_source_stage"
    if (
        _enum_value(source.owner_evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return "invalid_decoy_source_stage"
    if str(_enum_value(source.owner_assignment_status)) != "primary":
        return "invalid_decoy_source_stage"
    if source.duplicate_loser:
        return "invalid_decoy_source_stage"
    if not _decoy_owner_fields_are_finite(source.owner_like):
        return "invalid_decoy_source_stage"
    return ""


def _decoy_owner_fields_are_finite(owner_like: object) -> bool:
    return all(
        _is_finite_number(getattr(owner_like, field, None))
        for field in _REQUIRED_DECOY_OWNER_FIELDS
    )


def _build_decoy_seed_inputs(
    entry: IdentityControlManifestEntry,
    source: IdentityDecoySource,
    config: IdentityControlsConfig,
) -> tuple[IdentityCoherenceRequest, SeedCandidateEvidence, str, float | str]:
    method = entry.decoy_generation_method
    source_request = source.source_record.seed_gate.resolved_request
    decoy_request = replace(
        source_request,
        request_id=f"{entry.control_id}:decoy",
        request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
    )
    if method is DecoyGenerationMethod.RT_SHIFT:
        owner_end_rt = _owner_value(source.owner_like, "owner_peak_end_rt")
        margin_sec = config.decoy_rt_owner_boundary_margin_sec
        shifted_rt = owner_end_rt + margin_sec / 60.0
        decoy_evidence = replace(source.seed_evidence, best_seed_rt=shifted_rt)
        return decoy_request, decoy_evidence, "best_seed_rt", margin_sec

    if method is DecoyGenerationMethod.MZ_SHIFT:
        identity = source_request.identity
        shifted_identity = replace(
            identity,
            precursor_mz=_shift_outside_ppm(
                _identity_number(identity.precursor_mz, "precursor_mz"),
                _identity_number(
                    identity.precursor_tolerance_ppm,
                    "precursor_tolerance_ppm",
                ),
            ),
            product_mz=_shift_outside_ppm(
                _identity_number(identity.product_mz, "product_mz"),
                _identity_number(
                    identity.product_tolerance_ppm,
                    "product_tolerance_ppm",
                ),
            ),
        )
        return (
            replace(decoy_request, identity=shifted_identity),
            source.seed_evidence,
            "precursor_mz;product_mz",
            "outside_tolerance",
        )

    if method is DecoyGenerationMethod.FRAGMENT_TAG_SHUFFLE:
        source_tags = tuple(source.seed_evidence.fragment_tags)
        decoy_tags = entry.decoy_fragment_tags or _default_decoy_tags(source_tags)
        identity = source_request.identity
        shifted_identity = replace(identity, fragment_tags=decoy_tags)
        return (
            replace(decoy_request, identity=shifted_identity),
            source.seed_evidence,
            "fragment_tags",
            format_fragment_tags(decoy_tags),
        )

    raise ValueError(f"unsupported decoy_generation_method: {method}")


def _owner_value(owner_like: object, field: str) -> float:
    value = getattr(owner_like, field, None)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return float(value)


def _identity_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be finite positive")
    return float(value)


def _shift_outside_ppm(mz: float, tolerance_ppm: float) -> float:
    return mz * (1.0 + (tolerance_ppm + 1.0) / 1_000_000.0)


def _default_decoy_tags(source_tags: tuple[str, ...]) -> tuple[str, ...]:
    base = "identity_decoy_unmatched_tag"
    if base not in source_tags:
        return (base,)
    index = 2
    while f"{base}_{index}" in source_tags:
        index += 1
    return (f"{base}_{index}",)
