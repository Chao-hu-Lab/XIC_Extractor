"""Input loaders for the RT normalization anchor diagnostic."""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from openpyxl import load_workbook

from tools.diagnostics.rt_normalization_anchor_models import (
    AlignmentCell,
    AlignmentFeature,
    AnchorDefinition,
)
from xic_extractor.alignment.rt_normalization import AnchorPoint
from xic_extractor.injection_rolling import read_injection_order


def _read_anchor_definitions(
    path: Path,
    *,
    active_neutral_loss_da: float,
    active_neutral_loss_tolerance_da: float,
) -> dict[str, AnchorDefinition]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["Targets"]
        rows = sheet.iter_rows(values_only=True)
        header = next(rows)
        cols = _required_indexes(
            header,
            ("Label", "Role", "RT min", "RT max", "NL (Da)"),
            "Targets",
        )
        anchors: dict[str, AnchorDefinition] = {}
        for row in rows:
            label = _text(row[cols["Label"]])
            role = _text(row[cols["Role"]])
            if not label or role != "ISTD":
                continue
            neutral_loss = _required_float(row[cols["NL (Da)"]], "NL (Da)", label)
            if abs(neutral_loss - active_neutral_loss_da) > (
                active_neutral_loss_tolerance_da
            ):
                continue
            rt_min = _required_float(row[cols["RT min"]], "RT min", label)
            rt_max = _required_float(row[cols["RT max"]], "RT max", label)
            anchors[label] = AnchorDefinition(
                label=label,
                role=role,
                neutral_loss_da=neutral_loss,
                reference_rt_min=(rt_min + rt_max) / 2.0,
            )
        return anchors
    finally:
        workbook.close()


def _read_anchor_points(
    path: Path,
    anchors: Mapping[str, AnchorDefinition],
) -> tuple[AnchorPoint, ...]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["XIC Results"]
        rows = sheet.iter_rows(values_only=True)
        header = next(rows)
        cols = _required_indexes(
            header,
            ("SampleName", "Target", "Role", "RT"),
            "XIC Results",
        )
        current_sample = ""
        points: list[AnchorPoint] = []
        for row in rows:
            raw_sample = row[cols["SampleName"]]
            if raw_sample not in (None, ""):
                current_sample = _normalize_sample_id(_text(raw_sample))
            if not current_sample:
                continue
            label = _text(row[cols["Target"]])
            role = _text(row[cols["Role"]])
            if role != "ISTD" or label not in anchors:
                continue
            rt = _float_value(row[cols["RT"]])
            if rt is None:
                continue
            points.append(
                AnchorPoint(
                    sample_stem=current_sample,
                    target_label=label,
                    observed_rt_min=rt,
                    reference_rt_min=anchors[label].reference_rt_min,
                )
            )
        return tuple(points)
    finally:
        workbook.close()


def _read_optional_injection_order(
    sample_info: Path | None,
    *,
    reference_source: str,
) -> dict[str, int] | None:
    if not reference_source.startswith("injection-"):
        return None
    if sample_info is None:
        raise ValueError(f"sample_info is required for {reference_source}")
    return read_injection_order(sample_info)


def _read_alignment_review(path: Path) -> dict[str, AlignmentFeature]:
    rows = _read_required_tsv(path)
    _require_fields(rows, ("feature_family_id",), path)
    features: dict[str, AlignmentFeature] = {}
    for row in rows:
        family_id = row["feature_family_id"]
        features[family_id] = AlignmentFeature(
            feature_family_id=family_id,
            include_in_primary_matrix=_is_trueish(
                row.get("include_in_primary_matrix"),
            ),
            family_center_mz=_float_value(row.get("family_center_mz")),
            family_center_rt=_float_value(row.get("family_center_rt")),
        )
    return features


def _read_alignment_cells(path: Path) -> tuple[AlignmentCell, ...]:
    rows = _read_required_tsv(path)
    _require_fields(
        rows,
        ("feature_family_id", "sample_stem", "apex_rt"),
        path,
    )
    cells: list[AlignmentCell] = []
    for row in rows:
        apex_rt = _float_value(row.get("apex_rt"))
        if apex_rt is None:
            continue
        cells.append(
            AlignmentCell(
                feature_family_id=row["feature_family_id"],
                sample_stem=_normalize_sample_id(row["sample_stem"]),
                apex_rt=apex_rt,
            )
        )
    return tuple(cells)


def _read_required_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _require_fields(
    rows: list[dict[str, str]],
    required: Sequence[str],
    path: Path,
) -> None:
    if not rows:
        raise ValueError(f"{path} has no data rows")
    fieldnames = set(rows[0])
    missing = [field for field in required if field not in fieldnames]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")


def _required_indexes(
    header: Sequence[object],
    required: Sequence[str],
    sheet_name: str,
) -> dict[str, int]:
    indexes = {str(value).strip(): index for index, value in enumerate(header) if value}
    missing = [field for field in required if field not in indexes]
    if missing:
        raise ValueError(f"{sheet_name} sheet missing required columns: {missing}")
    return indexes


def _required_float(value: object, field: str, label: str) -> float:
    parsed = _float_value(value)
    if parsed is None:
        raise ValueError(f"{label} has invalid {field}: {value!r}")
    return parsed


def _float_value(value: object) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value) if math.isfinite(value) else None
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_sample_id(sample_id: str) -> str:
    value = sample_id.strip()
    return re.sub(
        r"(^|_)QC_(\d+)$",
        lambda match: f"{match.group(1)}QC{match.group(2)}",
        value,
    )


def _is_trueish(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}
