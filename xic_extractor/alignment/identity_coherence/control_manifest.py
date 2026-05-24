from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from .control_models import (
    IdentityControlManifestEntry,
    _normalize_text,
)
from .schema import (
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

_ManifestRow = Mapping[str | None, str | list[str] | None]


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


def _validate_required_fields(fieldnames: Sequence[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("identity controls manifest is missing a header row")
    seen: set[str] = set()
    duplicates: list[str] = []
    for field_name in fieldnames:
        if field_name in seen and field_name not in duplicates:
            duplicates.append(field_name)
        seen.add(field_name)
    if duplicates:
        raise ValueError(
            "identity controls manifest duplicate fields: "
            + ", ".join(duplicates)
        )
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
        control_type=_required(row, "control_type", row_index),
        control_name=_required(row, "control_name", row_index),
        expected_mapping_status=_required(
            row, "expected_mapping_status", row_index
        ),
        control_expected_behavior=_required(
            row, "control_expected_behavior", row_index
        ),
        fragment_observation_mode=_required(
            row, "fragment_observation_mode", row_index
        ),
        precursor_tolerance_ppm=_required(row, "precursor_tolerance_ppm", row_index),
        product_tolerance_ppm=_required(row, "product_tolerance_ppm", row_index),
        cid_observed_loss_tolerance_ppm=_required(
            row, "cid_observed_loss_tolerance_ppm", row_index
        ),
        rt_tolerance_sec=_required(row, "rt_tolerance_sec", row_index),
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


def _optional_float(
    row: _ManifestRow,
    field_name: str,
) -> float | str | None:
    raw_value = _optional_text(row, field_name)
    if not raw_value:
        return None
    return raw_value


def _optional_fragment_tags(row: _ManifestRow, field_name: str) -> tuple[str, ...]:
    tags, _flags = normalize_fragment_tags(_optional_text(row, field_name))
    return tags


def _optional_enum(
    enum_type: type[DecoyGenerationMethod],
    row: _ManifestRow,
    field_name: str,
) -> DecoyGenerationMethod | str | None:
    raw_value = _optional_text(row, field_name)
    if not raw_value:
        return None
    if enum_type is FragmentObservationMode:
        return raw_value
    if enum_type is PositiveControlMappingStatus:
        return raw_value
    return raw_value
