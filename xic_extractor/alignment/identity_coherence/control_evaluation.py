from __future__ import annotations

from collections.abc import Mapping, Sequence

from .control_models import (
    IdentityCoherenceOutputRecordLike,
    IdentityControlEvaluationResult,
    IdentityControlManifestEntry,
    IdentityControlsConfig,
    IdentityDecoySource,
    _enum_value,
    _record_match_constraints,
    _record_value,
)
from .control_rows import control_row
from .decoy_controls import evaluate_identity_decoy
from .models import SeedGateConfig
from .positive_controls import evaluate_positive_control
from .schema import ControlStatus, ControlType, PositiveControlMappingStatus


def evaluate_identity_controls(
    entries: Sequence[IdentityControlManifestEntry],
    *,
    records: Sequence[IdentityCoherenceOutputRecordLike],
    decoy_sources: Sequence[IdentityDecoySource],
    config: IdentityControlsConfig,
    seed_gate_config: SeedGateConfig = SeedGateConfig(),
    positive_control_evaluator=None,
    decoy_evaluator=None,
) -> IdentityControlEvaluationResult:
    if positive_control_evaluator is None:
        positive_control_evaluator = evaluate_positive_control
    if decoy_evaluator is None:
        decoy_evaluator = evaluate_identity_decoy

    rows: list[dict[str, object]] = []
    for entry in entries:
        if entry.control_type is ControlType.POSITIVE_TARGETED_ISTD:
            rows.append(positive_control_evaluator(entry, records))
            continue

        source_status, source = _resolve_decoy_source(entry, decoy_sources)
        if source is None:
            failure_reason = (
                "ambiguous_mapping"
                if source_status is PositiveControlMappingStatus.AMBIGUOUS_MAPPING
                else "missing_decoy_source"
            )
            control_status = (
                ControlStatus.AMBIGUOUS_MAPPING
                if source_status is PositiveControlMappingStatus.AMBIGUOUS_MAPPING
                else ControlStatus.UNMAPPED
            )
            rows.append(
                control_row(
                    entry,
                    control_status=control_status,
                    control_observed_behavior=failure_reason,
                    control_pass=False,
                    control_failure_reason=failure_reason,
                    positive_control_mapping_status=(
                        PositiveControlMappingStatus.NOT_APPLICABLE
                    ),
                    decoy_generation_method=entry.decoy_generation_method,
                    decoy_source_request_id=entry.decoy_source_request_id,
                )
            )
            continue

        rows.append(
            decoy_evaluator(
                entry,
                source,
                config,
                seed_gate_config=seed_gate_config,
            )
        )

    row_tuple = tuple(rows)
    positive_fraction = _positive_control_pass_fraction(row_tuple)
    decoy_coherent_count = _decoy_coherent_seed_count(row_tuple)
    return IdentityControlEvaluationResult(
        rows=row_tuple,
        positive_control_pass_fraction=positive_fraction,
        positive_control_threshold_met=(
            None
            if positive_fraction is None
            else positive_fraction >= config.positive_control_min_pass_fraction
        ),
        decoy_coherent_seed_count=decoy_coherent_count,
        decoy_coherent_seed_threshold_met=(
            decoy_coherent_count <= config.max_decoy_coherent_seed_count
        ),
    )


def _resolve_decoy_source(
    entry: IdentityControlManifestEntry,
    decoy_sources: Sequence[IdentityDecoySource],
) -> tuple[PositiveControlMappingStatus, IdentityDecoySource | None]:
    supplied = _record_match_constraints(entry)
    if entry.decoy_source_request_id:
        request_matches = [
            source
            for source in decoy_sources
            if (
                source.source_record.seed_gate.resolved_request.request_id
                == entry.decoy_source_request_id
            )
        ]
        if not request_matches:
            return PositiveControlMappingStatus.UNMAPPED, None
        if not supplied:
            if len(request_matches) == 1:
                return PositiveControlMappingStatus.MAPPED, request_matches[0]
            return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None

        matches = [
            source
            for source in request_matches
            if _source_matches_constraints(source, supplied)
        ]
        if len(matches) == 1:
            return PositiveControlMappingStatus.MAPPED, matches[0]
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None

    if not supplied:
        return PositiveControlMappingStatus.UNMAPPED, None

    matches = [
        source
        for source in decoy_sources
        if _source_matches_constraints(source, supplied)
    ]
    if len(matches) == 1:
        return PositiveControlMappingStatus.MAPPED, matches[0]
    if len(matches) > 1:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None

    partial_fields = {
        field
        for field, value in supplied
        if any(
            _record_value(source.source_record, field) == value
            for source in decoy_sources
        )
    }
    if partial_fields:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None
    return PositiveControlMappingStatus.UNMAPPED, None


def _source_matches_constraints(
    source: IdentityDecoySource,
    supplied: tuple[tuple[str, str], ...],
) -> bool:
    return all(
        _record_value(source.source_record, field) == value
        for field, value in supplied
    )


def _positive_control_pass_fraction(
    rows: Sequence[Mapping[str, object]],
) -> float | None:
    positive_rows = [
        row
        for row in rows
        if _enum_value(row.get("control_type")) == "positive_targeted_istd"
    ]
    if not positive_rows:
        return None
    pass_count = sum(1 for row in positive_rows if row.get("control_pass") is True)
    return pass_count / len(positive_rows)


def _decoy_coherent_seed_count(rows: Sequence[Mapping[str, object]]) -> int:
    return sum(
        1
        for row in rows
        if row.get("control_failure_reason") == "decoy_seed_gate_coherent"
    )
