from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


@dataclass(frozen=True)
class ManualTruthRow:
    sheet: str
    sample_name: str
    target: str
    manual_rt: float | None
    manual_height: float | None
    manual_area: float | None
    manual_width: float | None
    manual_shape: str


def read_manual_truth(path: Path) -> list[ManualTruthRow]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    rows: list[ManualTruthRow] = []
    for sheet_name in ("DNA", "RNA"):
        if sheet_name not in workbook.sheetnames:
            continue
        worksheet = workbook[sheet_name]
        rows.extend(_read_sheet_truth(worksheet))
    workbook.close()
    return rows


def _read_sheet_truth(worksheet: Worksheet) -> list[ManualTruthRow]:
    values = list(worksheet.iter_rows(values_only=True))
    if len(values) < 3:
        return []

    raw_blocks = _iter_raw_blocks(values[0])
    rows: list[ManualTruthRow] = []
    for row in values[2:]:
        target = _cell_text(_row_value(row, 1))
        if not target:
            continue
        for sample_name, start_idx in raw_blocks:
            manual_rt = _safe_float(_row_value(row, start_idx))
            manual_height = _safe_float(_row_value(row, start_idx + 1))
            manual_area = _safe_float(_row_value(row, start_idx + 2))
            manual_width = _safe_float(_row_value(row, start_idx + 3))
            manual_shape = _cell_text(_row_value(row, start_idx + 4))
            if manual_rt is None and manual_area is None:
                continue
            rows.append(
                ManualTruthRow(
                    sheet=worksheet.title,
                    sample_name=sample_name,
                    target=target,
                    manual_rt=manual_rt,
                    manual_height=manual_height,
                    manual_area=manual_area,
                    manual_width=manual_width,
                    manual_shape=manual_shape,
                )
            )
    return rows


def _iter_raw_blocks(header_row: Iterable[object]) -> list[tuple[str, int]]:
    blocks: list[tuple[str, int]] = []
    for idx, value in enumerate(header_row):
        if idx < 3:
            continue
        sample_name = _cell_text(value)
        if sample_name:
            blocks.append((_sample_stem(sample_name), idx))
    return blocks


def _sample_stem(value: str) -> str:
    return Path(value).stem


def _row_value(row: tuple[object, ...], idx: int) -> object | None:
    return row[idx] if idx < len(row) else None


def _safe_float(value: object | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cell_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()
