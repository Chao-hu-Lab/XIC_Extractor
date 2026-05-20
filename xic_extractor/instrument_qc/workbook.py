from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from xic_extractor.instrument_qc.models import (
    HCDAuditRow,
    InstrumentQCDiagnostic,
    SDOLEKTrendRow,
)
from xic_extractor.instrument_qc.writers import (
    DIAGNOSTIC_TSV_COLUMNS,
    HCD_AUDIT_TSV_COLUMNS,
    TREND_TSV_COLUMNS,
)


def write_sdolek_workbook(
    path: Path,
    rows: Iterable[SDOLEKTrendRow],
    diagnostics: Iterable[InstrumentQCDiagnostic],
    *,
    metadata_source_status: dict[str, str] | None = None,
    mixstds_rows: Iterable[SDOLEKTrendRow] | None = None,
    hcd_rows: Iterable[HCDAuditRow] | None = None,
) -> Path:
    row_list = list(rows)
    mixstds_row_list = list(mixstds_rows) if mixstds_rows is not None else None
    hcd_row_list = list(hcd_rows) if hcd_rows is not None else None
    diagnostic_list = list(diagnostics)
    path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    overview = workbook.active
    overview.title = "Overview"
    _write_overview_sheet(
        overview,
        row_list,
        diagnostic_list,
        metadata_source_status or {},
        mixstds_row_list,
        hcd_row_list,
    )
    _write_trend_sheet(workbook.create_sheet("SDOLEK Trend"), row_list)
    if mixstds_row_list is not None:
        _write_trend_sheet(workbook.create_sheet("Mix STDs Trend"), mixstds_row_list)
    if hcd_row_list is not None:
        _write_hcd_sheet(workbook.create_sheet("HCD Audit"), hcd_row_list)
        _write_manual_review_sheet(
            workbook.create_sheet("Manual Review Queue"),
            row_list,
            mixstds_row_list or [],
            hcd_row_list,
        )
    _write_diagnostics_sheet(workbook.create_sheet("Diagnostics"), diagnostic_list)
    workbook.save(path)
    return path


def _write_overview_sheet(
    sheet: Any,
    rows: list[SDOLEKTrendRow],
    diagnostics: list[InstrumentQCDiagnostic],
    metadata_source_status: dict[str, str],
    mixstds_rows: list[SDOLEKTrendRow] | None,
    hcd_rows: list[HCDAuditRow] | None,
) -> None:
    sheet.append(["metric", "value"])
    _bold_header(sheet)
    status_counts = _counts(row.status for row in rows)
    compound_counts = _counts(row.compound for row in rows)
    diagnostic_counts = _counts(diag.issue for diag in diagnostics)
    hcd_status_counts = _counts(row.hcd_status for row in hcd_rows or [])
    overview_rows = [
        ("report_type", "Instrument QC SDOLEK Trend"),
        (
            "identity_evidence",
            (
                "MS1 trend plus audit-only CID/wHCD product-ion review; "
                "not a production identity gate"
            ),
        ),
        ("total_rows", len(rows)),
        ("detected_rows", status_counts.get("detected", 0)),
        ("sdo_rows", compound_counts.get("SDO", 0)),
        ("lek_rows", compound_counts.get("LEK", 0)),
        ("mixstds_rows", len(mixstds_rows or [])),
        ("hcd_rows", len(hcd_rows or [])),
        ("hcd_status_counts", _format_counts(hcd_status_counts)),
        ("blank_stance", "blank_defer"),
        (
            "injection_order_status",
            metadata_source_status.get("injection_order_status", ""),
        ),
        (
            "injection_order_source",
            metadata_source_status.get("injection_order_source", ""),
        ),
        ("diagnostic_counts", _format_counts(diagnostic_counts)),
        ("top_rt_delta_to_reference", _top_rt_delta(rows)),
        ("top_width_ratio_to_reference", _top_width_ratio(rows)),
    ]
    for key, value in overview_rows:
        sheet.append([key, _xlsx_value(value)])
    _autosize_columns(sheet)


def _write_trend_sheet(sheet: Any, rows: list[SDOLEKTrendRow]) -> None:
    _append_xlsx_row(sheet, TREND_TSV_COLUMNS)
    for row in rows:
        values = _trend_row_to_dict(row)
        _append_xlsx_row(sheet, [values[column] for column in TREND_TSV_COLUMNS])
    _finish_table_sheet(sheet)


def _write_hcd_sheet(sheet: Any, rows: list[HCDAuditRow]) -> None:
    _append_xlsx_row(sheet, HCD_AUDIT_TSV_COLUMNS)
    for row in rows:
        values = _hcd_row_to_dict(row)
        _append_xlsx_row(sheet, [values[column] for column in HCD_AUDIT_TSV_COLUMNS])
    _finish_table_sheet(sheet)


def _write_manual_review_sheet(
    sheet: Any,
    sdolek_rows: list[SDOLEKTrendRow],
    mixstds_rows: list[SDOLEKTrendRow],
    hcd_rows: list[HCDAuditRow],
) -> None:
    columns = [
        "priority",
        "queue_reason",
        "review_item",
        "compound",
        "precursor_mz",
        "row_count",
        "samples",
        "ms1_summary",
        "hcd_summary",
        "rt_drift_hint",
        "product_hint",
        "suggested_action",
        "manual_label",
        "manual_note",
    ]
    _append_xlsx_row(sheet, columns)
    for row in _manual_review_rows(sdolek_rows, mixstds_rows, hcd_rows):
        _append_xlsx_row(sheet, [row.get(column, "") for column in columns])
    _finish_manual_review_sheet(sheet)


def _write_diagnostics_sheet(
    sheet: Any,
    diagnostics: list[InstrumentQCDiagnostic],
) -> None:
    _append_xlsx_row(sheet, DIAGNOSTIC_TSV_COLUMNS)
    for diagnostic in diagnostics:
        values = _diagnostic_to_dict(diagnostic)
        _append_xlsx_row(
            sheet,
            [values[column] for column in DIAGNOSTIC_TSV_COLUMNS],
        )
    _finish_table_sheet(sheet)


def _finish_table_sheet(sheet: Any) -> None:
    _bold_header(sheet)
    sheet.freeze_panes = "A2"
    if sheet.max_row > 1 and sheet.max_column > 1:
        sheet.auto_filter.ref = sheet.dimensions
    _autosize_columns(sheet)


def _finish_manual_review_sheet(sheet: Any) -> None:
    _finish_table_sheet(sheet)
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
        priority = row[0].value
        fill = _priority_fill(str(priority or ""))
        row[0].fill = fill
        row[1].fill = fill
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor="D9EAF7")
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _bold_header(sheet: Any) -> None:
    for cell in sheet[1]:
        cell.font = Font(name="Arial", bold=True)


def _append_xlsx_row(sheet: Any, values: Iterable[object]) -> None:
    sheet.append([_xlsx_value(value) for value in values])


def _xlsx_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, str):
        return _escape_excel_formula(value)
    if isinstance(value, Path):
        return _escape_excel_formula(str(value))
    return value


def _trend_row_to_dict(row: SDOLEKTrendRow) -> dict[str, object]:
    values = asdict(row)
    values["raw_path"] = str(row.raw_path)
    values["trend_flags"] = ";".join(row.trend_flags)
    return values


def _hcd_row_to_dict(row: HCDAuditRow) -> dict[str, object]:
    values = asdict(row)
    values["raw_path"] = str(row.raw_path)
    values["matched_products"] = ";".join(row.matched_products)
    values["review_flags"] = ";".join(row.review_flags)
    return values


def _diagnostic_to_dict(diagnostic: InstrumentQCDiagnostic) -> dict[str, object]:
    return {
        "sample_name": diagnostic.sample_name,
        "raw_path": str(diagnostic.raw_path),
        "issue": diagnostic.issue,
        "detail": diagnostic.detail,
    }


def _escape_excel_formula(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _manual_review_rows(
    sdolek_rows: list[SDOLEKTrendRow],
    mixstds_rows: list[SDOLEKTrendRow],
    hcd_rows: list[HCDAuditRow],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for hcd_row in hcd_rows:
        if "target_rt_window_review" in hcd_row.review_flags:
            if _skip_target_rt_window_queue_row(hcd_row, hcd_rows):
                continue
            rows.append(_manual_row("target_rt_window_mismatch", hcd=hcd_row))
            continue
        if _skip_hcd_product_queue_row(hcd_row, hcd_rows):
            continue
        if hcd_row.hcd_status in {
            "no_ms2_trigger",
            "no_product_match",
            "hcd_partial",
        }:
            rows.append(_manual_row(f"hcd_{hcd_row.hcd_status}", hcd=hcd_row))
        if hcd_row.hcd_status == "hcd_group_unmapped":
            rows.append(_manual_row("hcd_group_unmapped", hcd=hcd_row))
        if "activation_unknown_review" in hcd_row.review_flags:
            rows.append(_manual_row("activation_unknown", hcd=hcd_row))
    for trend_row in sdolek_rows:
        if (
            trend_row.compound == "LEK"
            and trend_row.rt_delta_to_reference_min is not None
            and abs(trend_row.rt_delta_to_reference_min) > 0.30
            and not _compound_rt_is_batch_stable(sdolek_rows, "LEK")
        ):
            rows.append(_manual_row("lek_rt_shift", trend=trend_row))
    for trend_row in mixstds_rows:
        if _has_outside_window_ms2_support(trend_row, hcd_rows):
            continue
        if trend_row.status != "detected":
            rows.append(_manual_row("mixstds_not_detected", trend=trend_row))
    return _compact_manual_review_rows(rows)


def _skip_hcd_product_queue_row(
    hcd_row: HCDAuditRow,
    hcd_rows: list[HCDAuditRow],
) -> bool:
    if hcd_row.hcd_status not in {
        "no_ms2_trigger",
        "no_product_match",
        "hcd_partial",
    }:
        return False
    if hcd_row.hcd_mapping_source == "unmapped":
        return True
    return _has_same_sample_isotope_support(hcd_row, hcd_rows)


def _skip_target_rt_window_queue_row(
    hcd_row: HCDAuditRow,
    hcd_rows: list[HCDAuditRow],
) -> bool:
    if hcd_row.hcd_mapping_source == "unmapped":
        return True
    return _has_same_sample_isotope_support(hcd_row, hcd_rows)


def _has_same_sample_isotope_support(
    hcd_row: HCDAuditRow,
    hcd_rows: list[HCDAuditRow],
) -> bool:
    target_base = _isotope_stripped_label(hcd_row.compound)
    if target_base == hcd_row.compound:
        companion_prefix_required = True
    else:
        companion_prefix_required = False
    for candidate in hcd_rows:
        if candidate.sample_name != hcd_row.sample_name:
            continue
        if candidate.hcd_status != "hcd_supported":
            continue
        if candidate.compound == hcd_row.compound:
            continue
        if _isotope_stripped_label(candidate.compound) != target_base:
            continue
        if companion_prefix_required and candidate.compound == target_base:
            continue
        return True
    return False


def _has_outside_window_ms2_support(
    trend_row: SDOLEKTrendRow,
    hcd_rows: list[HCDAuditRow],
) -> bool:
    return any(
        row.sample_name == trend_row.sample_name
        and row.compound == trend_row.compound
        and row.hcd_status == "hcd_supported"
        and "target_rt_window_review" in row.review_flags
        for row in hcd_rows
    )


def _isotope_stripped_label(label: str) -> str:
    value = re.sub(r"^\[[^\]]+\]-", "", label)
    value = re.sub(r"^(?:d\d+|[0-9]+N\d*)-", "", value)
    return value


def _compound_rt_is_batch_stable(
    rows: list[SDOLEKTrendRow],
    compound: str,
    *,
    min_rows: int = 3,
    max_rt_range_min: float = 0.70,
) -> bool:
    apex_rts = [
        row.apex_rt_min
        for row in rows
        if row.compound == compound
        and row.status == "detected"
        and row.apex_rt_min is not None
    ]
    if len(apex_rts) < min_rows:
        return False
    return max(apex_rts) - min(apex_rts) <= max_rt_range_min


def _compact_manual_review_rows(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            row.get("queue_reason", ""),
            row.get("compound", ""),
            row.get("precursor_mz", ""),
            row.get("hcd_status", ""),
            row.get("activation_method", ""),
            row.get("hcd_mapping_source", ""),
        )
        grouped.setdefault(key, []).append(row)
    items = [
        _manual_review_item(group_rows)
        for group_rows in grouped.values()
    ]
    return sorted(
        items,
        key=lambda row: (
            str(row["priority"]),
            str(row["queue_reason"]),
            str(row["compound"]),
        ),
    )


def _manual_review_item(rows: list[dict[str, object]]) -> dict[str, object]:
    first = rows[0]
    reason = str(first["queue_reason"])
    compound = str(first["compound"])
    precursor_mz = first.get("precursor_mz", "")
    samples = sorted({str(row.get("sample_name", "")) for row in rows})
    hcd_statuses = _counts(
        str(row.get("hcd_status", ""))
        for row in rows
        if row.get("hcd_status", "")
    )
    ms1_statuses = _counts(
        str(row.get("ms1_status", ""))
        for row in rows
        if row.get("ms1_status", "")
    )
    return {
        "priority": _review_priority(reason),
        "queue_reason": reason,
        "review_item": _review_item_label(reason, compound),
        "compound": compound,
        "precursor_mz": precursor_mz,
        "row_count": len(rows),
        "samples": _format_samples(samples),
        "ms1_summary": _format_counts(ms1_statuses),
        "hcd_summary": _format_counts(hcd_statuses),
        "rt_drift_hint": _rt_drift_hint(reason, rows),
        "product_hint": _product_hint(reason, rows),
        "suggested_action": _suggested_action(reason, rows),
        "manual_label": "",
        "manual_note": "",
    }


def _manual_row(
    reason: str,
    *,
    trend: SDOLEKTrendRow | None = None,
    hcd: HCDAuditRow | None = None,
) -> dict[str, object]:
    if hcd is not None:
        return {
            "queue_reason": reason,
            "sample_name": hcd.sample_name,
            "compound": hcd.compound,
            "precursor_mz": hcd.precursor_mz,
            "ms1_status": hcd.ms1_status,
            "ms1_apex_rt_min": hcd.ms1_apex_rt_min,
            "rt_delta_to_reference_min": "",
            "hcd_status": hcd.hcd_status,
            "activation_method": hcd.activation_method,
            "best_ms2_scan_rt_min": hcd.best_ms2_scan_rt_min,
            "apex_ms2_delta_min": hcd.apex_ms2_delta_min,
            "trigger_scan_count": hcd.trigger_scan_count,
            "expected_product_count": hcd.expected_product_count,
            "matched_product_count": hcd.matched_product_count,
            "best_product_ppm": hcd.best_product_ppm,
            "best_product_base_ratio": hcd.best_product_base_ratio,
            "matched_products": ";".join(hcd.matched_products),
            "hcd_mapping_source": hcd.hcd_mapping_source,
            "review_reason": hcd.review_reason,
            "manual_label": "",
            "manual_note": "",
        }
    if trend is None:
        raise ValueError("manual review row requires trend or hcd")
    return {
        "queue_reason": reason,
        "sample_name": trend.sample_name,
        "compound": trend.compound,
        "precursor_mz": trend.precursor_mz,
        "ms1_status": trend.status,
        "ms1_apex_rt_min": trend.apex_rt_min,
        "rt_delta_to_reference_min": trend.rt_delta_to_reference_min,
        "hcd_status": "",
        "activation_method": "",
        "best_ms2_scan_rt_min": "",
        "apex_ms2_delta_min": "",
        "trigger_scan_count": "",
        "expected_product_count": "",
        "matched_product_count": "",
        "best_product_ppm": "",
        "best_product_base_ratio": "",
        "matched_products": "",
        "hcd_mapping_source": "",
        "review_reason": trend.reason,
        "manual_label": "",
        "manual_note": "",
    }


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    return "; ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _review_priority(reason: str) -> str:
    priorities = {
        "hcd_no_ms2_trigger": "P1",
        "hcd_no_product_match": "P1",
        "hcd_hcd_partial": "P2",
        "target_rt_window_mismatch": "P2",
        "lek_rt_shift": "P2",
        "mixstds_not_detected": "P2",
        "hcd_group_unmapped": "P3",
        "activation_unknown": "P3",
    }
    return priorities.get(reason, "P3")


def _review_item_label(reason: str, compound: str) -> str:
    labels = {
        "hcd_no_ms2_trigger": "MS1 detected but no precursor MS2 trigger",
        "hcd_no_product_match": "MS1 detected but expected product missing",
        "hcd_hcd_partial": "MS1 detected with weak/near product evidence",
        "target_rt_window_mismatch": "Product evidence outside target RT window",
        "hcd_group_unmapped": "HCD product group unmapped",
        "activation_unknown": "Activation method unknown",
        "lek_rt_shift": "LEK RT shifted from prior",
        "mixstds_not_detected": "Mix STDs target not detected by MS1",
    }
    return f"{compound}: {labels.get(reason, reason)}"


def _format_samples(samples: list[str], limit: int = 4) -> str:
    shown = [sample for sample in samples if sample][:limit]
    suffix = "" if len(samples) <= limit else f"; +{len(samples) - limit} more"
    return "; ".join(shown) + suffix


def _rt_drift_hint(reason: str, rows: list[dict[str, object]]) -> str:
    if reason == "lek_rt_shift":
        deltas = _float_values(row.get("rt_delta_to_reference_min", "") for row in rows)
        if not deltas:
            return "MS1 RT shift flagged; inspect trend sheet."
        max_abs = max(abs(value) for value in deltas)
        return f"MS1 prior delta max={max_abs:.3f} min; inspect LEK prior/window."
    if reason == "mixstds_not_detected":
        return "No MS1 peak selected; RT drift cannot be judged from HCD."
    deltas = _float_values(row.get("apex_ms2_delta_min", "") for row in rows)
    triggers = _float_values(row.get("trigger_scan_count", "") for row in rows)
    if not triggers or max(triggers) == 0:
        return "No precursor-matched MS2 trigger near MS1 apex."
    if not deltas:
        return "MS2 trigger exists, but delta is unavailable."
    med_delta = median(deltas)
    max_delta = max(deltas)
    if max_delta <= 0.08:
        interpretation = "RT drift is unlikely to be the main issue."
    elif max_delta <= 0.20:
        interpretation = "RT/off-apex timing could contribute; inspect rows."
    else:
        interpretation = "Large apex-MS2 gap; RT/off-apex issue likely."
    return (
        f"MS2-apex delta median={med_delta:.3f}, "
        f"max={max_delta:.3f} min. {interpretation}"
    )


def _product_hint(reason: str, rows: list[dict[str, object]]) -> str:
    if reason == "hcd_no_ms2_trigger":
        return "No product evidence because no precursor MS2 was triggered."
    if reason == "hcd_group_unmapped":
        sources = sorted({str(row.get("hcd_mapping_source", "")) for row in rows})
        return f"Add explicit hcd_base_group/product_group. source={';'.join(sources)}"
    if reason == "activation_unknown":
        return "Method doc sequence row lacks CID/wHCD detail."
    if reason == "target_rt_window_mismatch":
        return (
            "Product/NL evidence exists outside the configured target RT "
            "window; update RT prior/window before judging detection."
        )
    if reason == "lek_rt_shift":
        return (
            "SDO/LEK product table is independent; this queue item is MS1 "
            "RT-prior drift review."
        )
    expected = sum(_to_int(row.get("expected_product_count", "")) for row in rows)
    matched = sum(_to_int(row.get("matched_product_count", "")) for row in rows)
    best_ppm = _float_values(row.get("best_product_ppm", "") for row in rows)
    ratio = _float_values(row.get("best_product_base_ratio", "") for row in rows)
    detail = f"matched/expected={matched}/{expected}"
    sources = sorted(
        {
            str(row.get("hcd_mapping_source", ""))
            for row in rows
            if row.get("hcd_mapping_source", "")
        }
    )
    if sources:
        detail += f"; source={';'.join(sources)}"
    if best_ppm:
        detail += f"; best ppm={min(abs(value) for value in best_ppm):.1f}"
    if ratio:
        detail += f"; max product/base={max(ratio):.3f}"
    if reason == "mixstds_not_detected":
        return "MS1 not detected; HCD evidence not evaluated."
    return detail


def _suggested_action(reason: str, rows: list[dict[str, object]]) -> str:
    if reason == "hcd_no_ms2_trigger":
        return "Check DDA trigger/height threshold and MS1 peak height."
    if reason == "hcd_no_product_match":
        deltas = _float_values(row.get("apex_ms2_delta_min", "") for row in rows)
        sources = {
            str(row.get("hcd_mapping_source", ""))
            for row in rows
            if row.get("hcd_mapping_source", "")
        }
        if "unmapped" in sources:
            return (
                "Add explicit product group or leave this target as CID/NL-only "
                "manual review."
            )
        if deltas and max(deltas) > 0.08:
            return "Inspect RT/off-apex first, then base-specific product pattern."
        if sources == {"sdolek_builtin"}:
            return (
                "Review SDO/LEK-specific CID/wHCD product table and MS2 "
                "trigger quality."
            )
        return (
            "Review base-specific product pattern; add compound-specific "
            "registry if needed."
        )
    if reason == "hcd_hcd_partial":
        return "Inspect spectrum; product may be weak or ppm/intensity gate too strict."
    if reason == "target_rt_window_mismatch":
        return "Review XIC/MS2 at reported RT and update targets.csv RT window."
    if reason == "hcd_group_unmapped":
        return (
            "Add explicit HCD base/product group if this target needs "
            "identity review."
        )
    if reason == "activation_unknown":
        return "Parse method-detail table or manually label activation."
    if reason == "lek_rt_shift":
        return "Check whether LEK prior RT/window should be updated."
    if reason == "mixstds_not_detected":
        return "Confirm MS1 absence in XIC before interpreting HCD."
    return "Manual review."


def _float_values(values: Iterable[object]) -> list[float]:
    parsed: list[float] = []
    for value in values:
        try:
            if value == "":
                continue
            if not isinstance(value, (int, float, str)):
                continue
            parsed.append(float(value))
        except (TypeError, ValueError):
            continue
    return parsed


def _to_int(value: object) -> int:
    try:
        if value == "":
            return 0
        if not isinstance(value, (int, float, str)):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _priority_fill(priority: str) -> PatternFill:
    colors = {
        "P1": "F4CCCC",
        "P2": "FFF2CC",
        "P3": "D9EAD3",
    }
    return PatternFill("solid", fgColor=colors.get(priority, "FFFFFF"))


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _top_rt_delta(rows: list[SDOLEKTrendRow]) -> str:
    candidates = [
        row for row in rows if row.rt_delta_to_reference_min is not None
    ]
    if not candidates:
        return ""
    row = max(candidates, key=lambda item: abs(item.rt_delta_to_reference_min or 0.0))
    return (
        f"{row.sample_name} {row.compound}: "
        f"{row.rt_delta_to_reference_min:.3f} min"
    )


def _top_width_ratio(rows: list[SDOLEKTrendRow]) -> str:
    candidates = [
        row for row in rows if row.base_width_ratio_to_reference is not None
    ]
    if not candidates:
        return ""
    row = max(
        candidates,
        key=lambda item: abs((item.base_width_ratio_to_reference or 1.0) - 1.0),
    )
    return (
        f"{row.sample_name} {row.compound}: "
        f"{row.base_width_ratio_to_reference:.3f}"
    )


def _autosize_columns(sheet: Any) -> None:
    for column_cells in sheet.columns:
        header = column_cells[0]
        letter = header.column_letter
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[letter].width = min(max(max_length + 2, 10), 60)
