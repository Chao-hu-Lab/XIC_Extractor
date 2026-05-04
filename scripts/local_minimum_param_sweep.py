from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from statistics import median
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


@dataclass(frozen=True)
class ProgramPeakRow:
    sample_name: str
    target: str
    is_istd: bool
    rt: float | None
    height: float | None
    area: float | None
    detected: bool


@dataclass(frozen=True)
class ParameterSet:
    name: str
    settings_overrides: dict[str, str]


@dataclass(frozen=True)
class PerTargetScoreRow:
    name: str
    sample_name: str
    target: str
    is_istd: bool
    manual_rt: float | None
    program_rt: float | None
    rt_abs_delta_min: float | None
    manual_height: float | None
    program_height: float | None
    height_abs_pct_error: float | None
    manual_area: float | None
    program_area: float | None
    area_abs_pct_error: float | None
    missing_peak: bool
    manual_shape: str


@dataclass(frozen=True)
class ParameterSetScore:
    name: str
    settings_overrides: dict[str, str]
    detected_rows: int
    scored_rows: int
    missing_manual_peaks: int
    istd_misses: int
    area_median_abs_pct_error: float | None
    height_median_abs_pct_error: float | None
    rt_median_abs_delta_min: float | None
    rt_max_abs_delta_min: float | None
    area_within_10pct: int
    area_within_20pct: int
    large_area_misses: int
    per_target_rows: list[PerTargetScoreRow]


_STATIC_LOCAL_MINIMUM_PARAMS = {
    "resolver_min_relative_height": "0.0",
    "resolver_min_absolute_height": "25.0",
    "resolver_peak_duration_min": "0.0",
    "resolver_peak_duration_max": "10.0",
}

_GRID_VALUES = {
    "quick": {
        "resolver_chrom_threshold": ("0.03", "0.05"),
        "resolver_min_search_range_min": ("0.05", "0.08"),
        "resolver_min_ratio_top_edge": ("1.5", "1.7"),
        "resolver_min_scans": ("3", "5"),
    },
    "standard": {
        "resolver_chrom_threshold": ("0.03", "0.05", "0.08"),
        "resolver_min_search_range_min": ("0.05", "0.08", "0.12"),
        "resolver_min_ratio_top_edge": ("1.3", "1.5", "1.7", "2.0"),
        "resolver_min_scans": ("3", "5"),
    },
}


def build_parameter_sets(*, grid: str) -> list[ParameterSet]:
    if grid not in _GRID_VALUES:
        raise ValueError(f"Unknown grid: {grid}")

    parameter_sets = [
        ParameterSet("legacy_savgol", {"resolver_mode": "legacy_savgol"}),
        ParameterSet("local_minimum_current", {"resolver_mode": "local_minimum"}),
    ]
    grid_values = _GRID_VALUES[grid]
    keys = list(grid_values.keys())
    for idx, values in enumerate(product(*(grid_values[key] for key in keys)), start=1):
        settings = {
            "resolver_mode": "local_minimum",
            **_STATIC_LOCAL_MINIMUM_PARAMS,
            **dict(zip(keys, values)),
        }
        parameter_sets.append(
            ParameterSet(f"local_minimum_grid_{idx:03d}", settings)
        )
    return parameter_sets


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


def score_parameter_set(
    name: str,
    settings_overrides: dict[str, str],
    truth_rows: list[ManualTruthRow],
    program_rows: list[ProgramPeakRow],
    *,
    istd_targets: set[str] | None = None,
) -> ParameterSetScore:
    program_by_key = {
        (row.sample_name, row.target): row
        for row in program_rows
    }
    istd_target_names = set(istd_targets or ())
    per_target_rows: list[PerTargetScoreRow] = []
    for truth in truth_rows:
        program = program_by_key.get((truth.sample_name, truth.target))
        detected = _program_peak_detected(program)
        is_istd = (
            truth.target in istd_target_names
            or (program.is_istd if program is not None else False)
        )
        rt_abs_delta = _abs_delta(program.rt, truth.manual_rt) if detected else None
        height_abs_pct_error = (
            _abs_pct_error(program.height, truth.manual_height) if detected else None
        )
        area_abs_pct_error = (
            _abs_pct_error(program.area, truth.manual_area) if detected else None
        )
        per_target_rows.append(
            PerTargetScoreRow(
                name=name,
                sample_name=truth.sample_name,
                target=truth.target,
                is_istd=is_istd,
                manual_rt=truth.manual_rt,
                program_rt=program.rt if detected else None,
                rt_abs_delta_min=_round_optional(rt_abs_delta),
                manual_height=truth.manual_height,
                program_height=program.height if detected else None,
                height_abs_pct_error=_round_optional(height_abs_pct_error),
                manual_area=truth.manual_area,
                program_area=program.area if detected else None,
                area_abs_pct_error=_round_optional(area_abs_pct_error),
                missing_peak=not detected,
                manual_shape=truth.manual_shape,
            )
        )

    area_errors = [
        row.area_abs_pct_error
        for row in per_target_rows
        if row.area_abs_pct_error is not None
    ]
    height_errors = [
        row.height_abs_pct_error
        for row in per_target_rows
        if row.height_abs_pct_error is not None
    ]
    rt_deltas = [
        row.rt_abs_delta_min
        for row in per_target_rows
        if row.rt_abs_delta_min is not None
    ]
    missing_rows = [row for row in per_target_rows if row.missing_peak]
    return ParameterSetScore(
        name=name,
        settings_overrides=settings_overrides,
        detected_rows=sum(not row.missing_peak for row in per_target_rows),
        scored_rows=len(area_errors),
        missing_manual_peaks=len(missing_rows),
        istd_misses=sum(row.is_istd for row in missing_rows),
        area_median_abs_pct_error=_rounded_median(area_errors),
        height_median_abs_pct_error=_rounded_median(height_errors),
        rt_median_abs_delta_min=_rounded_median(rt_deltas),
        rt_max_abs_delta_min=round(max(rt_deltas), 6) if rt_deltas else None,
        area_within_10pct=sum(error <= 0.10 + 1e-12 for error in area_errors),
        area_within_20pct=sum(error <= 0.20 + 1e-12 for error in area_errors),
        large_area_misses=sum(error > 0.20 + 1e-12 for error in area_errors),
        per_target_rows=per_target_rows,
    )


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


def _program_peak_detected(row: ProgramPeakRow | None) -> bool:
    return bool(
        row is not None
        and row.detected
        and row.rt is not None
        and row.area is not None
    )


def _abs_delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return abs(left - right)


def _abs_pct_error(value: float | None, truth: float | None) -> float | None:
    if value is None or truth is None or truth <= 0:
        return None
    return abs(value - truth) / truth


def _rounded_median(values: list[float]) -> float | None:
    if not values:
        return None
    return round(median(values), 6)


def _round_optional(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)
