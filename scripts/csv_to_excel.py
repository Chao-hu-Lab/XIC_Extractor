"""
將 xic_results.csv 轉換為格式化 Excel。

欄位結構從 Target 設定推導，支援 apex RT、raw intensity、integrated
area、peak boundary、四態 neutral-loss 結果與 diagnostics sheet。
"""

from __future__ import annotations

import csv
import statistics
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import overload

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from xic_extractor.config import ExtractionConfig, Target, load_config

ColumnMeta = dict[str, object]

_MS1_PALETTES = [
    {"header": "1B5E20", "light": "C8E6C9", "alt": "A5D6A7", "dim": "E8F5E9"},
    {"header": "0D47A1", "light": "BBDEFB", "alt": "90CAF9", "dim": "E3F2FD"},
    {"header": "4A148C", "light": "E1BEE7", "alt": "CE93D8", "dim": "F3E5F5"},
    {"header": "004D40", "light": "B2DFDB", "alt": "80CBC4", "dim": "E0F2F1"},
    {"header": "E65100", "light": "FFE0B2", "alt": "FFCC80", "dim": "FFF3E0"},
    {"header": "880E4F", "light": "FCE4EC", "alt": "F48FB1", "dim": "FCE4EC"},
]
_MS2_HEADER = "37474F"
_MS2_OK = "C8E6C9"
_MS2_WARN = "FFF9C4"
_MS2_FAIL = "FFCDD2"
_MS2_NO_MS2 = "E0E0E0"
_SAMPLE_HEADER = "2E4057"
WHITE = "FFFFFF"
GREY = "F5F5F5"
_THIN = Side(style="thin", color="BDBDBD")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
CENTER = Alignment(horizontal="center", vertical="center")
CENTER_WRAP = Alignment(horizontal="center", vertical="center", wrap_text=True)
ND_ERROR = {"ND", "ERROR"}
_FORMULA_PREFIXES = ("=", "+", "-", "@")
_DIAGNOSTIC_HEADERS = ["SampleName", "Target", "Issue", "Reason"]
_GROUPS = ["Tumor", "Normal", "Benignfat", "QC"]


def _fill(hex6: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex6)


def _apply(cell, **kw: object) -> None:
    for key, value in kw.items():
        setattr(cell, key, value)


def _header_style(hex6: str) -> dict[str, object]:
    return {
        "font": Font(bold=True, color="FFFFFF", size=11),
        "fill": _fill(hex6),
        "alignment": CENTER_WRAP,
        "border": BORDER,
    }


def _safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _excel_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _load_column_meta(config_dir: Path) -> dict[str, ColumnMeta]:
    targets_path = config_dir / "targets.csv"
    if not targets_path.exists():
        return {"SampleName": {"type": "sample"}}
    return _load_column_meta_from_targets(_read_targets_csv_for_meta(targets_path))


def _load_column_meta_from_targets(targets: Iterable[Target]) -> dict[str, ColumnMeta]:
    meta: dict[str, ColumnMeta] = {"SampleName": {"type": "sample"}}
    for palette_idx, target in enumerate(targets):
        label = target.label
        palette = _MS1_PALETTES[palette_idx % len(_MS1_PALETTES)]
        has_nl = target.neutral_loss_da is not None
        nl_col = f"{label}_NL" if has_nl else None
        base = {
            "palette": palette,
            "label": label,
            "nl_col": nl_col,
            "is_istd": target.is_istd,
            "istd_pair": target.istd_pair,
        }
        meta[f"{label}_RT"] = {"type": "ms1_rt", **base}
        meta[f"{label}_Int"] = {"type": "ms1_int", **base}
        meta[f"{label}_Area"] = {"type": "ms1_area", **base}
        meta[f"{label}_PeakStart"] = {"type": "ms1_peak_start", **base}
        meta[f"{label}_PeakEnd"] = {"type": "ms1_peak_end", **base}
        if nl_col:
            meta[nl_col] = {"type": "ms2_nl", "label": label}
    return meta


def _read_targets_csv_for_meta(path: Path) -> list[Target]:
    targets: list[Target] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            label = row.get("label", "").strip()
            if not label:
                continue
            neutral_loss_da = _optional_float(row.get("neutral_loss_da", ""))
            targets.append(
                Target(
                    label=label,
                    mz=_safe_float(row.get("mz", "")) or 0.0,
                    rt_min=_safe_float(row.get("rt_min", "")) or 0.0,
                    rt_max=_safe_float(row.get("rt_max", "")) or 0.0,
                    ppm_tol=_safe_float(row.get("ppm_tol", "")) or 0.0,
                    neutral_loss_da=neutral_loss_da,
                    nl_ppm_warn=_optional_float(row.get("nl_ppm_warn", "")),
                    nl_ppm_max=_optional_float(row.get("nl_ppm_max", "")),
                    is_istd=row.get("is_istd", "false").strip().lower() == "true",
                    istd_pair=row.get("istd_pair", "").strip(),
                )
            )
    return targets


def _optional_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return _safe_float(value)


def _nl_to_display(value: str) -> str:
    if value == "OK":
        return "✓"
    if value.startswith("WARN_"):
        return "⚠ " + value[5:]
    if value == "NL_FAIL":
        return "✗ NL"
    if value == "NO_MS2":
        return "— MS2"
    if value == "ND":
        return "✗"
    return value


def _nl_cell_fill(value: str) -> PatternFill:
    if value == "OK":
        return _fill(_MS2_OK)
    if value.startswith("WARN_"):
        return _fill(_MS2_WARN)
    if value == "NO_MS2":
        return _fill(_MS2_NO_MS2)
    return _fill(_MS2_FAIL)


def _build_data_sheet(
    ws, rows: list[dict[str, str]], col_meta: dict[str, ColumnMeta], csv_keys: list[str]
) -> None:
    for col_idx, key in enumerate(csv_keys, start=1):
        meta = col_meta.get(key, {"type": "unknown"})
        label, color = _header_label_and_color(key, meta)
        _apply(ws.cell(row=1, column=col_idx, value=label), **_header_style(color))
    ws.row_dimensions[1].height = 40

    for row_idx, row in enumerate(rows, start=2):
        alt = row_idx % 2 == 0
        for col_idx, key in enumerate(csv_keys, start=1):
            raw_val = row.get(key, "")
            meta = col_meta.get(key, {"type": "unknown"})
            col_type = str(meta.get("type", ""))
            cell = ws.cell(row=row_idx, column=col_idx)

            if col_type == "ms2_nl":
                cell.value = _nl_to_display(raw_val)
                _apply(
                    cell,
                    fill=_nl_cell_fill(raw_val),
                    alignment=CENTER,
                    border=BORDER,
                )
                continue

            if raw_val in ND_ERROR:
                cell.value = raw_val
                nd_hex = "FF7043" if meta.get("is_istd", False) else "FFE0B2"
                _apply(cell, fill=_fill(nd_hex), alignment=CENTER, border=BORDER)
                continue

            value = _cell_value(raw_val, col_type)
            cell.value = value
            _apply(
                cell,
                fill=_data_fill(col_type, meta, alt),
                alignment=CENTER,
                border=BORDER,
            )
            if isinstance(value, float):
                cell.number_format = _number_format(col_type)

    for col_idx, key in enumerate(csv_keys, start=1):
        col_type = str(col_meta.get(key, {}).get("type", ""))
        width = 30 if col_type == "sample" else 14 if col_type.startswith("ms1") else 18
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.freeze_panes = "B2"


def _header_label_and_color(key: str, meta: ColumnMeta) -> tuple[object, str]:
    col_type = str(meta.get("type", ""))
    if col_type == "sample":
        return "Sample Name", _SAMPLE_HEADER
    if col_type == "ms2_nl":
        return f"{_excel_text(str(meta['label']))}\nNL check", _MS2_HEADER
    if col_type.startswith("ms1"):
        suffix = {
            "ms1_rt": "RT (min)",
            "ms1_int": "Intensity",
            "ms1_area": "Area",
            "ms1_peak_start": "Peak start",
            "ms1_peak_end": "Peak end",
        }[col_type]
        palette = meta["palette"]
        return f"{_excel_text(str(meta['label']))}\n{suffix}", palette["header"]
    return _excel_text(key), _SAMPLE_HEADER


def _cell_value(raw_val: str, col_type: str) -> object:
    if col_type == "sample":
        return _excel_text(raw_val)
    if col_type.startswith("ms1"):
        parsed = _safe_float(raw_val)
        return parsed if parsed is not None else raw_val
    return raw_val


def _data_fill(col_type: str, meta: ColumnMeta, alt: bool) -> PatternFill:
    if col_type == "sample":
        return _fill(GREY if alt else WHITE)
    if col_type in {"ms1_peak_start", "ms1_peak_end"}:
        return _fill(str(meta["palette"]["dim"]))
    if col_type.startswith("ms1"):
        palette = meta["palette"]
        return _fill(str(palette["alt"] if alt else palette["light"]))
    return _fill(GREY if alt else WHITE)


def _number_format(col_type: str) -> str:
    if col_type in {"ms1_rt", "ms1_peak_start", "ms1_peak_end"}:
        return "0.0000"
    if col_type == "ms1_area":
        return "#,##0.00"
    return "#,##0"


def _sample_group(name: str) -> str:
    normalized = name.upper()
    if normalized.startswith("TUMOR"):
        return "Tumor"
    if normalized.startswith("NORMAL"):
        return "Normal"
    if normalized.startswith("BENIGNFAT"):
        return "Benignfat"
    return "QC"


def _is_detected(
    row: dict[str, str],
    rt_key: str,
    area_key: str,
    nl_key: str | None,
    count_no_ms2_as_detected: bool,
) -> bool:
    if _safe_float(row.get(rt_key, "")) is None:
        return False
    if _safe_float(row.get(area_key, "")) is None:
        return False
    if nl_key is None:
        return True
    nl = row.get(nl_key, "")
    return (
        nl == "OK"
        or nl.startswith("WARN_")
        or (count_no_ms2_as_detected and nl == "NO_MS2")
    )


def _build_summary_sheet(
    ws,
    rows: list[dict[str, str]],
    col_meta: dict[str, ColumnMeta],
    csv_keys: list[str],
    count_no_ms2_as_detected: bool = False,
) -> None:
    compounds = _ordered_compounds(col_meta, csv_keys)
    group_rows: dict[str, list[dict[str, str]]] = {group: [] for group in _GROUPS}
    for row in rows:
        group_rows[_sample_group(row.get("SampleName", ""))].append(row)

    _write_summary_headers(ws, compounds, col_meta)
    metrics = [f"{group} ({len(group_rows[group])})" for group in _GROUPS] + [
        "Total Detection",
        "Mean RT (min)",
        "Median Area",
        "Area / ISTD ratio",
        "NL ✓/⚠/✗/—",
        "RT Δ vs ISTD (%)",
    ]

    for row_idx, metric in enumerate(metrics, start=2):
        fill_hex = GREY if row_idx % 2 == 0 else WHITE
        _apply(
            ws.cell(row=row_idx, column=1, value=metric),
            fill=_fill(fill_hex),
            alignment=CENTER,
            border=BORDER,
        )
        for col_idx, compound in enumerate(compounds, start=2):
            value = _summary_value(
                metric,
                compound,
                rows,
                group_rows,
                col_meta,
                count_no_ms2_as_detected,
            )
            _apply(
                ws.cell(row=row_idx, column=col_idx),
                value=value,
                fill=_fill(fill_hex),
                alignment=CENTER,
                border=BORDER,
            )

    ws.column_dimensions["A"].width = 22
    for col_idx in range(2, len(compounds) + 2):
        ws.column_dimensions[get_column_letter(col_idx)].width = 20
    ws.freeze_panes = "B2"


def _ordered_compounds(
    col_meta: dict[str, ColumnMeta], csv_keys: list[str]
) -> list[tuple[str, str, str, str, str | None]]:
    compounds: list[tuple[str, str, str, str, str | None]] = []
    seen: set[str] = set()
    for key in csv_keys:
        meta = col_meta.get(key, {})
        if meta.get("type") != "ms1_rt":
            continue
        label = str(meta["label"])
        if label in seen:
            continue
        seen.add(label)
        compounds.append(
            (label, key, f"{label}_Area", f"{label}_Int", meta.get("nl_col"))
        )
    return compounds


def _write_summary_headers(
    ws,
    compounds: list[tuple[str, str, str, str, str | None]],
    col_meta: dict[str, ColumnMeta],
) -> None:
    headers = ["Metric"] + [compound[0] for compound in compounds]
    for col_idx, header in enumerate(headers, start=1):
        if col_idx == 1:
            color = _SAMPLE_HEADER
            value = header
        else:
            label = compounds[col_idx - 2][0]
            color = str(
                col_meta.get(f"{label}_RT", {})
                .get("palette", {})
                .get("header", _MS2_HEADER)
            )
            value = _excel_text(header)
        _apply(ws.cell(row=1, column=col_idx, value=value), **_header_style(color))
    ws.row_dimensions[1].height = 30


def _summary_value(
    metric: str,
    compound: tuple[str, str, str, str, str | None],
    rows: list[dict[str, str]],
    group_rows: dict[str, list[dict[str, str]]],
    col_meta: dict[str, ColumnMeta],
    count_no_ms2_as_detected: bool,
) -> object:
    label, rt_key, area_key, _int_key, nl_key = compound
    group_match = next((group for group in _GROUPS if metric.startswith(group)), None)
    if group_match:
        return _detection_rate(
            group_rows[group_match], rt_key, area_key, nl_key, count_no_ms2_as_detected
        )
    if metric == "Total Detection":
        return _detection_rate(rows, rt_key, area_key, nl_key, count_no_ms2_as_detected)
    if metric == "Mean RT (min)":
        return _mean_rt(rows, rt_key, area_key, nl_key, count_no_ms2_as_detected)
    if metric == "Median Area":
        return _median_area(rows, rt_key, area_key, nl_key, count_no_ms2_as_detected)
    if metric == "Area / ISTD ratio":
        return _area_ratio(label, rows, col_meta, count_no_ms2_as_detected)
    if metric == "NL ✓/⚠/✗/—":
        return _nl_counts(rows, nl_key)
    if metric == "RT Δ vs ISTD (%)":
        return _rt_delta(label, rows, col_meta, count_no_ms2_as_detected)
    return "—"


def _detection_rate(
    rows: list[dict[str, str]],
    rt_key: str,
    area_key: str,
    nl_key: str | None,
    count_no_ms2_as_detected: bool,
) -> str:
    total = len(rows)
    detected = sum(
        1
        for row in rows
        if _is_detected(
            row,
            rt_key,
            area_key,
            nl_key,
            count_no_ms2_as_detected,
        )
    )
    pct = detected / total * 100 if total else 0
    return f"{detected}/{total} ({pct:.0f}%)"


def _detected_rows(
    rows: list[dict[str, str]],
    rt_key: str,
    area_key: str,
    nl_key: str | None,
    count_no_ms2_as_detected: bool,
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if _is_detected(row, rt_key, area_key, nl_key, count_no_ms2_as_detected)
    ]


def _mean_rt(
    rows: list[dict[str, str]],
    rt_key: str,
    area_key: str,
    nl_key: str | None,
    count_no_ms2_as_detected: bool,
) -> str:
    detected = _detected_rows(rows, rt_key, area_key, nl_key, count_no_ms2_as_detected)
    values = [
        value
        for row in detected
        if (value := _safe_float(row.get(rt_key, ""))) is not None
    ]
    return f"{sum(values) / len(values):.4f}" if values else "—"


def _median_area(
    rows: list[dict[str, str]],
    rt_key: str,
    area_key: str,
    nl_key: str | None,
    count_no_ms2_as_detected: bool,
) -> str:
    detected = _detected_rows(rows, rt_key, area_key, nl_key, count_no_ms2_as_detected)
    values = [
        value
        for row in detected
        if (value := _safe_float(row.get(area_key, ""))) is not None
    ]
    return f"{statistics.median(values):,.2f}" if values else "—"


def _nl_counts(rows: list[dict[str, str]], nl_key: str | None) -> str:
    if nl_key is None:
        return "—"
    values = [row.get(nl_key, "") for row in rows]
    ok = sum(1 for value in values if value == "OK")
    warn = sum(1 for value in values if value.startswith("WARN_"))
    no_ms2 = sum(1 for value in values if value == "NO_MS2")
    fail = len(values) - ok - warn - no_ms2
    return f"✓{ok} ⚠{warn} ✗{fail} —{no_ms2}"


def _area_ratio(
    label: str,
    rows: list[dict[str, str]],
    col_meta: dict[str, ColumnMeta],
    count_no_ms2_as_detected: bool,
) -> str:
    ratio_keys = _paired_keys(label, col_meta)
    if ratio_keys is None:
        return "—"
    rt_key, area_key, nl_key, istd_rt_key, istd_area_key, istd_nl_key = ratio_keys
    ratios: list[float] = []
    for row in rows:
        if not _is_detected(row, rt_key, area_key, nl_key, count_no_ms2_as_detected):
            continue
        if not _is_detected(
            row, istd_rt_key, istd_area_key, istd_nl_key, count_no_ms2_as_detected
        ):
            continue
        analyte_area = _safe_float(row.get(area_key, ""))
        istd_area = _safe_float(row.get(istd_area_key, ""))
        if analyte_area is None or istd_area is None or istd_area == 0:
            continue
        ratios.append(analyte_area / istd_area)
    if not ratios:
        return "—"
    mean_ratio = sum(ratios) / len(ratios)
    sd_ratio = statistics.stdev(ratios) if len(ratios) > 1 else 0.0
    return f"{mean_ratio:.4f}±{sd_ratio:.4f} (n={len(ratios)})"


def _rt_delta(
    label: str,
    rows: list[dict[str, str]],
    col_meta: dict[str, ColumnMeta],
    count_no_ms2_as_detected: bool,
) -> str:
    ratio_keys = _paired_keys(label, col_meta)
    if ratio_keys is None:
        return "—"
    rt_key, area_key, nl_key, istd_rt_key, istd_area_key, istd_nl_key = ratio_keys
    deltas: list[float] = []
    for row in rows:
        if not _is_detected(row, rt_key, area_key, nl_key, count_no_ms2_as_detected):
            continue
        if not _is_detected(
            row, istd_rt_key, istd_area_key, istd_nl_key, count_no_ms2_as_detected
        ):
            continue
        rt_analyte = _safe_float(row.get(rt_key, ""))
        rt_istd = _safe_float(row.get(istd_rt_key, ""))
        if rt_analyte is None or rt_istd is None or rt_istd == 0:
            continue
        deltas.append(abs(rt_analyte - rt_istd) / rt_istd * 100)
    if not deltas:
        return "—"
    mean_delta = sum(deltas) / len(deltas)
    sd_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
    return f"{mean_delta:.2f}±{sd_delta:.2f}% (n={len(deltas)})"


def _paired_keys(
    label: str, col_meta: dict[str, ColumnMeta]
) -> tuple[str, str, str | None, str, str, str | None] | None:
    rt_key = f"{label}_RT"
    meta = col_meta.get(rt_key, {})
    istd_label = str(meta.get("istd_pair", ""))
    if not istd_label:
        return None
    return (
        rt_key,
        f"{label}_Area",
        meta.get("nl_col"),
        f"{istd_label}_RT",
        f"{istd_label}_Area",
        col_meta.get(f"{istd_label}_RT", {}).get("nl_col"),
    )


def _read_diagnostics(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _build_diagnostics_sheet(ws, rows: list[dict[str, str]]) -> None:
    for col_idx, header in enumerate(_DIAGNOSTIC_HEADERS, start=1):
        _apply(
            ws.cell(row=1, column=col_idx, value=header),
            **_header_style(_MS2_HEADER),
        )
    for row_idx, row in enumerate(rows, start=2):
        issue = row.get("Issue", "")
        for col_idx, header in enumerate(_DIAGNOSTIC_HEADERS, start=1):
            raw = row.get(header, "")
            value = (
                _excel_text(raw)
                if header in {"SampleName", "Target", "Reason"}
                else raw
            )
            _apply(
                ws.cell(row=row_idx, column=col_idx, value=value),
                fill=_fill(_diagnostic_fill(issue)),
                alignment=CENTER,
                border=BORDER,
            )
    ws.auto_filter.ref = f"A1:D{max(1, len(rows) + 1)}"
    widths = [24, 20, 18, 60]
    for col_idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.freeze_panes = "A2"


def _diagnostic_fill(issue: str) -> str:
    if issue in {"NO_MS2", "WINDOW_TOO_SHORT"}:
        return _MS2_NO_MS2
    if issue in {"NL_FAIL", "PEAK_NOT_FOUND", "NO_SIGNAL", "FILE_ERROR"}:
        return _MS2_FAIL
    return _MS2_WARN


@overload
def run(base_or_config: Path) -> Path: ...


@overload
def run(base_or_config: ExtractionConfig, targets: list[Target]) -> Path: ...


def run(
    base_or_config: Path | ExtractionConfig,
    targets: list[Target] | None = None,
) -> Path:
    if isinstance(base_or_config, Path):
        config, loaded_targets = load_config(base_or_config / "config")
        return run(config, loaded_targets)
    if targets is None:
        raise TypeError("targets are required when run() receives ExtractionConfig")
    return _run_with_config(base_or_config, targets)


def _run_with_config(config: ExtractionConfig, targets: list[Target]) -> Path:
    output_dir = config.output_csv.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    excel_path = output_dir / f"xic_results_{timestamp}.xlsx"

    rows = _read_results(config.output_csv)
    if not rows:
        print("CSV is empty.")
        return excel_path

    csv_keys = list(rows[0].keys())
    col_meta = _load_column_meta_from_targets(targets)
    diagnostics = _read_diagnostics(config.diagnostics_csv)

    wb = Workbook()
    ws_data = wb.active
    ws_data.title = "XIC Results"
    _build_data_sheet(ws_data, rows, col_meta, csv_keys)

    ws_summary = wb.create_sheet("Summary")
    _build_summary_sheet(
        ws_summary,
        rows,
        col_meta,
        csv_keys,
        count_no_ms2_as_detected=config.count_no_ms2_as_detected,
    )

    ws_diagnostics = wb.create_sheet("Diagnostics")
    _build_diagnostics_sheet(ws_diagnostics, diagnostics)
    if diagnostics:
        wb.active = wb.index(ws_diagnostics)

    wb.save(excel_path)
    _print_summary(
        excel_path,
        rows,
        csv_keys,
        col_meta,
        config.count_no_ms2_as_detected,
    )
    return excel_path


def _read_results(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _print_summary(
    excel_path: Path,
    rows: list[dict[str, str]],
    csv_keys: list[str],
    col_meta: dict[str, ColumnMeta],
    count_no_ms2_as_detected: bool,
) -> None:
    print(f"Saved : {excel_path}")
    print(f"Rows  : {len(rows)}")
    ms1_cols = [
        key for key in csv_keys if col_meta.get(key, {}).get("type") == "ms1_rt"
    ]
    ms2_cols = [
        key for key in csv_keys if col_meta.get(key, {}).get("type") == "ms2_nl"
    ]
    for key in ms1_cols:
        label = key.removesuffix("_RT")
        area_key = f"{label}_Area"
        nl_col = col_meta.get(key, {}).get("nl_col")
        detected = sum(
            1
            for row in rows
            if _is_detected(
                row,
                key,
                area_key,
                nl_col,
                count_no_ms2_as_detected,
            )
        )
        note = " (NL confirmed)" if nl_col else ""
        print(f"  {label} detected{note}: {detected}/{len(rows)}")
    for key in ms2_cols:
        values = [row.get(key, "") for row in rows]
        ok = sum(1 for value in values if value == "OK")
        warn = sum(1 for value in values if value.startswith("WARN_"))
        no_ms2 = sum(1 for value in values if value == "NO_MS2")
        fail = len(values) - ok - warn - no_ms2
        print(f"  {key}  OK:{ok}  WARN:{warn}  FAIL:{fail}  NO_MS2:{no_ms2}")
    for key in ms1_cols:
        if not col_meta.get(key, {}).get("is_istd", False):
            continue
        label = key.removesuffix("_RT")
        area_key = f"{label}_Area"
        nl_col = col_meta.get(key, {}).get("nl_col")
        detected = sum(
            1
            for row in rows
            if _is_detected(
                row,
                key,
                area_key,
                nl_col,
                count_no_ms2_as_detected,
            )
        )
        if detected < len(rows):
            print(f"ISTD_ND: {label} {detected}/{len(rows)}")


def main() -> None:
    base_dir = Path(__file__).parent.parent
    run(base_dir)


if __name__ == "__main__":
    main()
