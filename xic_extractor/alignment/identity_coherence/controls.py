from __future__ import annotations

import csv
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, cast

from .schema import (
    ControlStatus,
    ControlType,
    DecoyGenerationMethod,
    FragmentObservationMode,
    PositiveControlMappingStatus,
)
from .tags import normalize_fragment_tags

REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = (
    "control_id",
    "control_type",
    "control_name",
    "expected_mapping_status",
    "control_expected_behavior",
    "fragment_observation_mode",
    "precursor_tolerance_ppm",
    "product_tolerance_ppm",
    "cid_observed_loss_tolerance_ppm",
    "rt_tolerance_sec",
    "required_failure_reason_when_missed",
)

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


class IdentityCoherenceOutputRecordLike(Protocol):
    seed_gate: Any
    row_result: Any


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


def read_identity_controls_manifest(
    manifest_path: str | Path,
) -> tuple[IdentityControlManifestEntry, ...]:
    path = Path(manifest_path)
    suffix = path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        raise ValueError("YAML controls manifests are not implemented in this slice")
    if suffix != ".tsv":
        raise ValueError("identity controls manifests must use a .tsv extension")
    return read_identity_controls_manifest_tsv(path)


def read_identity_controls_manifest_tsv(
    manifest_path: str | Path,
) -> tuple[IdentityControlManifestEntry, ...]:
    path = Path(manifest_path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, dialect="excel-tab")
        _validate_required_fields(reader.fieldnames)
        entries: list[IdentityControlManifestEntry] = []
        for row_index, raw_row in enumerate(reader, start=2):
            row = cast(_ManifestRow, raw_row)
            _reject_extra_fields(row, row_index)
            if _row_has_content(row):
                entries.append(_entry_from_row(row, row_index))
        return tuple(entries)


_ManifestRow = Mapping[str | None, str | list[str] | None]


def _validate_required_fields(fieldnames: Sequence[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("identity controls manifest is missing a header row")
    missing = [
        field_name
        for field_name in REQUIRED_MANIFEST_FIELDS
        if field_name not in fieldnames
    ]
    if missing:
        raise ValueError(
            "identity controls manifest missing required fields: "
            + ", ".join(missing)
        )


def _reject_extra_fields(row: _ManifestRow, row_index: int) -> None:
    if None in row:
        raise ValueError(
            f"identity controls manifest row {row_index} has "
            "unexpected extra fields"
        )


def _entry_from_row(
    row: _ManifestRow,
    row_index: int,
) -> IdentityControlManifestEntry:
    return IdentityControlManifestEntry(
        control_id=_required(row, "control_id", row_index),
        control_type=_parse_control_type(
            _required(row, "control_type", row_index)
        ),
        control_name=_required(row, "control_name", row_index),
        expected_mapping_status=_parse_enum(
            PositiveControlMappingStatus,
            _required(row, "expected_mapping_status", row_index),
            "expected_mapping_status",
        ),
        control_expected_behavior=_required(
            row, "control_expected_behavior", row_index
        ),
        fragment_observation_mode=_parse_enum(
            FragmentObservationMode,
            _required(row, "fragment_observation_mode", row_index),
            "fragment_observation_mode",
        ),
        precursor_tolerance_ppm=_required_float(
            row, "precursor_tolerance_ppm", row_index
        ),
        product_tolerance_ppm=_required_float(
            row, "product_tolerance_ppm", row_index
        ),
        cid_observed_loss_tolerance_ppm=_required_float(
            row, "cid_observed_loss_tolerance_ppm", row_index
        ),
        rt_tolerance_sec=_required_float(row, "rt_tolerance_sec", row_index),
        required_failure_reason_when_missed=_required(
            row, "required_failure_reason_when_missed", row_index
        ),
        decision_id=_optional_text(row, "decision_id"),
        identity_family_id=_optional_text(row, "identity_family_id"),
        seed_candidate_id=_optional_text(row, "seed_candidate_id"),
        decoy_generation_method=_optional_enum(
            DecoyGenerationMethod,
            row,
            "decoy_generation_method",
        ),
        decoy_source_request_id=_optional_text(row, "decoy_source_request_id"),
        decoy_fragment_tags=_optional_fragment_tags(row, "decoy_fragment_tags"),
        positive_control_target_name=_optional_text(
            row, "positive_control_target_name"
        ),
        positive_control_target_mz=_optional_float(
            row, "positive_control_target_mz"
        ),
        positive_control_target_rt_sec=_optional_float(
            row, "positive_control_target_rt_sec"
        ),
        positive_control_mapping_error_ppm=_optional_float(
            row, "positive_control_mapping_error_ppm"
        ),
        positive_control_mapping_delta_rt_sec=_optional_float(
            row, "positive_control_mapping_delta_rt_sec"
        ),
        control_notes=_optional_text(row, "control_notes"),
    )


def _row_has_content(row: _ManifestRow) -> bool:
    return any(_normalize_text(value) for value in row.values())


def _required(
    row: _ManifestRow,
    field_name: str,
    row_index: int,
) -> str:
    value = _normalize_text(row.get(field_name))
    if not value:
        raise ValueError(
            f"identity controls manifest row {row_index} field "
            f"{field_name} is required"
        )
    return value


def _optional_text(row: _ManifestRow, field_name: str) -> str:
    return _normalize_text(row.get(field_name))


def _required_float(
    row: _ManifestRow,
    field_name: str,
    row_index: int,
) -> float:
    raw_value = _required(row, field_name, row_index)
    return _parse_float(raw_value, field_name)


def _optional_float(
    row: _ManifestRow,
    field_name: str,
) -> float | None:
    raw_value = _optional_text(row, field_name)
    if not raw_value:
        return None
    return _parse_finite_float(raw_value, field_name)


def _optional_fragment_tags(row: _ManifestRow, field_name: str) -> tuple[str, ...]:
    tags, _flags = normalize_fragment_tags(_optional_text(row, field_name))
    return tags


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


def _optional_enum(
    enum_type: type[DecoyGenerationMethod],
    row: _ManifestRow,
    field_name: str,
) -> DecoyGenerationMethod | None:
    raw_value = _optional_text(row, field_name)
    if not raw_value:
        return None
    return _parse_enum(enum_type, raw_value, field_name)


def _parse_enum(
    enum_type: type[PositiveControlMappingStatus]
    | type[FragmentObservationMode]
    | type[DecoyGenerationMethod],
    value: object,
    field_name: str,
) -> PositiveControlMappingStatus | FragmentObservationMode | DecoyGenerationMethod:
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
        return _control_row(
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
    return _control_row(
        entry,
        decision_id=decision.decision_id,
        identity_family_id=decision.identity_family_id,
        seed_candidate_id=decision.seed_candidate_id,
        control_status=ControlStatus.ASSESSED,
        control_observed_behavior=observed,
        control_pass=passed,
        control_failure_reason=failure_reason,
        positive_control_mapping_status=mapping_status,
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
    if (
        abs(float(entry.positive_control_mapping_error_ppm))
        > entry.precursor_tolerance_ppm
        or abs(float(entry.positive_control_mapping_delta_rt_sec))
        > entry.rt_tolerance_sec
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


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(value)
    )


def _control_row(
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
        "control_notes": entry.control_notes,
    }


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
