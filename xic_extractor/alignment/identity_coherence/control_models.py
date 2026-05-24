from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, TypeVar

from .models import SeedCandidateEvidence
from .schema import (
    ControlType,
    DecoyGenerationMethod,
    EvidenceStage,
    FragmentObservationMode,
    PositiveControlMappingStatus,
)
from .tags import normalize_fragment_tags

_REQUIRED_TEXT_FIELDS: tuple[str, ...] = (
    "control_id",
    "control_name",
    "control_expected_behavior",
    "required_failure_reason_when_missed",
)

_TEXT_FIELDS: tuple[str, ...] = (
    *_REQUIRED_TEXT_FIELDS,
    "decision_id",
    "identity_family_id",
    "seed_candidate_id",
    "decoy_source_request_id",
    "positive_control_target_name",
    "control_notes",
)

_TOLERANCE_FIELDS: tuple[str, ...] = (
    "precursor_tolerance_ppm",
    "product_tolerance_ppm",
    "cid_observed_loss_tolerance_ppm",
    "rt_tolerance_sec",
)

_OPTIONAL_NUMERIC_FIELDS: tuple[str, ...] = (
    "positive_control_target_mz",
    "positive_control_target_rt_sec",
    "positive_control_mapping_error_ppm",
    "positive_control_mapping_delta_rt_sec",
)

_UNSUPPORTED_CONTROL_TYPES: frozenset[str] = frozenset(
    {
        "blank",
        "qc",
        "background",
        "negative_blank",
        "negative_qc",
        "contaminant",
    }
)

_EnumT = TypeVar("_EnumT", bound=Enum)


class IdentityCoherenceOutputRecordLike(Protocol):
    @property
    def seed_gate(self) -> Any: ...

    @property
    def row_result(self) -> Any: ...


@dataclass(frozen=True)
class IdentityControlManifestEntry:
    control_id: str
    control_type: ControlType
    control_name: str
    expected_mapping_status: PositiveControlMappingStatus
    control_expected_behavior: str
    fragment_observation_mode: FragmentObservationMode
    precursor_tolerance_ppm: float
    product_tolerance_ppm: float
    cid_observed_loss_tolerance_ppm: float
    rt_tolerance_sec: float
    required_failure_reason_when_missed: str
    decision_id: str = ""
    identity_family_id: str = ""
    seed_candidate_id: str = ""
    decoy_generation_method: DecoyGenerationMethod | None = None
    decoy_source_request_id: str = ""
    decoy_fragment_tags: tuple[str, ...] = ()
    positive_control_target_name: str = ""
    positive_control_target_mz: float | None = None
    positive_control_target_rt_sec: float | None = None
    positive_control_mapping_error_ppm: float | None = None
    positive_control_mapping_delta_rt_sec: float | None = None
    control_notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "control_type",
            _parse_control_type(self.control_type),
        )
        object.__setattr__(
            self,
            "expected_mapping_status",
            _parse_enum(
                PositiveControlMappingStatus,
                self.expected_mapping_status,
                "expected_mapping_status",
            ),
        )
        object.__setattr__(
            self,
            "fragment_observation_mode",
            _parse_enum(
                FragmentObservationMode,
                self.fragment_observation_mode,
                "fragment_observation_mode",
            ),
        )
        if self.decoy_generation_method is not None:
            object.__setattr__(
                self,
                "decoy_generation_method",
                _parse_enum(
                    DecoyGenerationMethod,
                    self.decoy_generation_method,
                    "decoy_generation_method",
                ),
            )

        for field_name in _TEXT_FIELDS:
            text_value = _normalize_text(getattr(self, field_name))
            object.__setattr__(self, field_name, text_value)
            if field_name in _REQUIRED_TEXT_FIELDS and not text_value:
                raise ValueError(f"{field_name} must be non-empty")

        for field_name in _TOLERANCE_FIELDS:
            numeric_value = _parse_float(getattr(self, field_name), field_name)
            object.__setattr__(self, field_name, numeric_value)
            if not math.isfinite(numeric_value) or numeric_value <= 0:
                raise ValueError(f"{field_name} must be finite positive")

        for field_name in _OPTIONAL_NUMERIC_FIELDS:
            raw_optional_value = getattr(self, field_name)
            if raw_optional_value is None:
                continue
            optional_value = _parse_finite_float(raw_optional_value, field_name)
            object.__setattr__(self, field_name, optional_value)

        tags, _flags = normalize_fragment_tags(self.decoy_fragment_tags)
        object.__setattr__(self, "decoy_fragment_tags", tags)

        if (
            self.control_type is ControlType.IDENTITY_DECOY
            and self.decoy_generation_method is None
        ):
            raise ValueError(
                "identity_decoy controls require decoy_generation_method"
            )


@dataclass(frozen=True)
class IdentityControlsConfig:
    positive_control_min_pass_fraction: float = 1.00
    max_decoy_coherent_seed_count: int = 0
    decoy_rt_owner_boundary_margin_sec: float = 6.0

    def __post_init__(self) -> None:
        pass_fraction = self.positive_control_min_pass_fraction
        if (
            isinstance(pass_fraction, bool)
            or not isinstance(pass_fraction, int | float)
            or not math.isfinite(pass_fraction)
            or not (0.0 < pass_fraction <= 1.0)
        ):
            raise ValueError(
                "positive_control_min_pass_fraction must be > 0 and <= 1"
            )
        object.__setattr__(
            self,
            "positive_control_min_pass_fraction",
            float(pass_fraction),
        )

        coherent_seed_count = self.max_decoy_coherent_seed_count
        if (
            isinstance(coherent_seed_count, bool)
            or not isinstance(coherent_seed_count, int)
            or coherent_seed_count < 0
        ):
            raise ValueError("max_decoy_coherent_seed_count must be nonnegative")

        margin_sec = _require_positive(
            self.decoy_rt_owner_boundary_margin_sec,
            "decoy_rt_owner_boundary_margin_sec",
        )
        object.__setattr__(
            self,
            "decoy_rt_owner_boundary_margin_sec",
            margin_sec,
        )


@dataclass(frozen=True)
class IdentityDecoySource:
    source_record: IdentityCoherenceOutputRecordLike
    seed_evidence: SeedCandidateEvidence
    owner_like: object
    owner_assignment_status: str = "primary"
    duplicate_loser: bool = False
    owner_evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL


@dataclass(frozen=True)
class IdentityControlEvaluationResult:
    rows: tuple[dict[str, object], ...]
    positive_control_pass_fraction: float | None
    positive_control_threshold_met: bool | None
    decoy_coherent_seed_count: int
    decoy_coherent_seed_threshold_met: bool


def _parse_float(raw_value: object, field_name: str) -> float:
    if not isinstance(raw_value, str | int | float):
        raise ValueError(f"{field_name} must be a number")
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _parse_finite_float(raw_value: object, field_name: str) -> float:
    value = _parse_float(raw_value, field_name)
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _parse_control_type(value: object) -> ControlType:
    if isinstance(value, ControlType):
        return value
    raw_value = _normalize_text(value)
    if raw_value in _UNSUPPORTED_CONTROL_TYPES:
        raise ValueError(f"unsupported identity control_type: {raw_value}")
    try:
        return ControlType(raw_value)
    except ValueError as exc:
        raise ValueError(f"unsupported identity control_type: {raw_value}") from exc


def _parse_enum(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    if isinstance(value, enum_type):
        return value
    raw_value = _normalize_text(value)
    try:
        return enum_type(raw_value)
    except ValueError as exc:
        raise ValueError(f"unsupported {field_name}: {raw_value}") from exc


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _require_positive(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be finite positive")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be finite positive")
    return float(value)


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(value)
    )


def _record_match_constraints(
    entry: IdentityControlManifestEntry,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (field, value)
        for field, value in (
            ("decision_id", entry.decision_id),
            ("identity_family_id", entry.identity_family_id),
            ("seed_candidate_id", entry.seed_candidate_id),
        )
        if value
    )


def _record_value(record: IdentityCoherenceOutputRecordLike, field: str) -> str:
    decision = record.row_result.decision
    values = {
        "decision_id": decision.decision_id,
        "identity_family_id": decision.identity_family_id,
        "seed_candidate_id": decision.seed_candidate_id,
    }
    return values[field]


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
