"""
csv_to_excel.py
將 xic_results.csv 轉換為格式化 Excel。
欄位結構從 config/targets.csv 自動推導，支援任意數量的特徵。
"""

import csv
import statistics
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ── Colour palette (MS1 target pairs, cycling) ────────────────────────────────
_MS1_PALETTES = [
    {"header": "1B5E20", "light": "C8E6C9", "alt": "A5D6A7"},  # green
    {"header": "0D47A1", "light": "BBDEFB", "alt": "90CAF9"},  # blue
    {"header": "4A148C", "light": "E1BEE7", "alt": "CE93D8"},  # purple
    {"header": "004D40", "light": "B2DFDB", "alt": "80CBC4"},  # teal
    {"header": "E65100", "light": "FFE0B2", "alt": "FFCC80"},  # orange
    {"header": "880E4F", "light": "FCE4EC", "alt": "F48FB1"},  # pink
]
_MS2_HEADER = "37474F"  # blue-grey
_MS2_OK = "C8E6C9"  # green  ✓
_MS2_WARN = "FFF9C4"  # yellow ⚠
_MS2_ND = "FFCDD2"  # red    ✗

_SAMPLE_HEADER = "2E4057"
WHITE = "FFFFFF"
GREY = "F5F5F5"
_THIN = Side(style="thin", color="BDBDBD")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
CENTER = Alignment(horizontal="center", vertical="center")
CENTER_WRAP = Alignment(horizontal="center", vertical="center", wrap_text=True)
# PS1 outputs ASCII tokens; map them to display symbols here
_NL_DISPLAY = {"OK": "✓", "ND": "✗"}  # WARN_Xppm → "⚠ Xppm" handled in _nl_display()
ND_ERROR = {"ND", "ERROR"}


def _fill(hex6: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex6)


def _apply(cell, **kw) -> None:
    for k, v in kw.items():
        setattr(cell, k, v)


def _header_style(hex6: str) -> dict:
    return dict(
        font=Font(bold=True, color="FFFFFF", size=11),
        fill=_fill(hex6),
        alignment=CENTER_WRAP,
        border=BORDER,
    )


def _safe_float(s: str) -> float | None:
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ── Parse targets.csv to understand column types ───────────────────────────────
def _load_column_meta(config_dir: Path) -> dict:
    """
    Returns dict: csv_col_name → {type, palette, label, nl_col}
    type = 'sample' | 'ms1_rt' | 'ms1_int' | 'ms2_nl'
    nl_col: for MS1 columns, the CSV key of the NL column (e.g. "258.1085_NL"), or None.
    Each targets.csv row is one compound; neutral_loss_da non-empty → NL column exists.
    """
    meta: dict[str, dict] = {"SampleName": {"type": "sample"}}
    palette_idx = 0

    targets_path = config_dir / "targets.csv"
    if not targets_path.exists():
        return meta

    with open(targets_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            label = row["label"].strip()
            has_nl = bool(row.get("neutral_loss_da", "").strip())

            pal = _MS1_PALETTES[palette_idx % len(_MS1_PALETTES)]
            palette_idx += 1
            nl_col = f"{label}_NL" if has_nl else None

            meta[f"{label}_RT"] = {
                "type": "ms1_rt",
                "palette": pal,
                "label": label,
                "nl_col": nl_col,
                "is_istd": row.get("is_istd", "false").lower() == "true",
                "istd_pair": row.get("istd_pair", "").strip(),
            }
            meta[f"{label}_Int"] = {
                "type": "ms1_int",
                "palette": pal,
                "label": label,
                "nl_col": nl_col,
            }
            if has_nl:
                meta[nl_col] = {"type": "ms2_nl", "label": label}

    return meta


def _nl_to_display(value: str) -> str:
    """Convert PS1 ASCII token to Unicode display string."""
    if value == "OK":
        return "✓"
    if value == "ND":
        return "✗"
    if value.startswith("WARN_"):
        return "⚠ " + value[5:]  # WARN_12.3ppm → ⚠ 12.3ppm
    return value


def _nl_cell_fill(value: str) -> PatternFill:
    """Return fill colour based on PS1 ASCII token."""
    if value == "OK":
        return _fill(_MS2_OK)
    if value.startswith("WARN_"):
        return _fill(_MS2_WARN)
    return _fill(_MS2_ND)  # ND, ERROR, anything else


# ── Build main data sheet ──────────────────────────────────────────────────────
def _build_data_sheet(
    ws, rows: list[dict], col_meta: dict, csv_keys: list[str]
) -> None:
    # Header row
    for col_idx, key in enumerate(csv_keys, start=1):
        meta = col_meta.get(key, {"type": "unknown"})
        t = meta.get("type", "")

        if t == "sample":
            label, hex6 = "Sample Name", _SAMPLE_HEADER
        elif t == "ms1_rt":
            label = f"{meta['label']}\nRT (min)"
            hex6 = meta["palette"]["header"]
        elif t == "ms1_int":
            label = f"{meta['label']}\nIntensity"
            hex6 = meta["palette"]["header"]
        elif t == "ms2_nl":
            label = f"{meta['label']}\nNL check"
            hex6 = _MS2_HEADER
        else:
            label, hex6 = key, _SAMPLE_HEADER

        _apply(ws.cell(row=1, column=col_idx, value=label), **_header_style(hex6))

    ws.row_dimensions[1].height = 40

    # Data rows
    for row_idx, row in enumerate(rows, start=2):
        alt = row_idx % 2 == 0
        for col_idx, key in enumerate(csv_keys, start=1):
            raw_val = row.get(key, "")
            meta = col_meta.get(key, {"type": "unknown"})
            t = meta.get("type", "")

            cell = ws.cell(row=row_idx, column=col_idx)

            # MS2 NL columns: convert ASCII token → Unicode + colour
            if t == "ms2_nl":
                cell.value = _nl_to_display(raw_val)
                _apply(
                    cell, fill=_nl_cell_fill(raw_val), alignment=CENTER, border=BORDER
                )
                continue

            # MS1 / sample: ND or ERROR → orange warning cell
            if raw_val in ND_ERROR:
                cell.value = raw_val
                nd_hex = "FF7043" if meta.get("is_istd", False) else "FFE0B2"
                _apply(cell, fill=_fill(nd_hex), alignment=CENTER, border=BORDER)
                continue

            # Numeric conversion for MS1 columns
            value = _safe_float(raw_val) if t in ("ms1_rt", "ms1_int") else raw_val
            cell.value = value

            if t == "sample":
                fill = _fill(GREY) if alt else _fill(WHITE)
            elif t == "ms1_rt":
                fill = _fill(
                    meta["palette"]["alt"] if alt else meta["palette"]["light"]
                )
            elif t == "ms1_int":
                fill = _fill(
                    meta["palette"]["alt"] if alt else meta["palette"]["light"]
                )
            else:
                fill = _fill(GREY) if alt else _fill(WHITE)

            _apply(cell, fill=fill, alignment=CENTER, border=BORDER)

            if isinstance(value, float):
                cell.number_format = "0.0000" if t == "ms1_rt" else "#,##0"

    # Column widths
    for col_idx, key in enumerate(csv_keys, start=1):
        t = col_meta.get(key, {}).get("type", "")
        ws.column_dimensions[get_column_letter(col_idx)].width = (
            30 if t == "sample" else 16 if t in ("ms1_rt", "ms1_int") else 18
        )

    ws.freeze_panes = "B2"


# ── Group classification ───────────────────────────────────────────────────────
_GROUPS = ["Tumor", "Normal", "Benignfat", "QC"]


def _sample_group(name: str) -> str:
    n = name.upper()
    if n.startswith("TUMOR"):
        return "Tumor"
    if n.startswith("NORMAL"):
        return "Normal"
    if n.startswith("BENIGNFAT"):
        return "Benignfat"
    return "QC"


def _is_detected(row: dict, rt_key: str, int_key: str, nl_key: str | None) -> bool:
    """True if compound is NL-confirmed detected in this sample."""
    if _safe_float(row.get(rt_key, "")) is None:
        return False
    if _safe_float(row.get(int_key, "")) is None:
        return False
    if nl_key:
        nl = row.get(nl_key, "")
        return nl == "OK" or nl.startswith("WARN_")
    return True


# ── Build summary sheet ────────────────────────────────────────────────────────
def _build_summary_sheet(
    ws, rows: list[dict], col_meta: dict, csv_keys: list[str]
) -> None:
    # Build ordered compound list: (label, rt_key, int_key, nl_key|None)
    compounds: list[tuple[str, str, str, str | None]] = []
    seen: set[str] = set()
    for key in csv_keys:
        meta = col_meta.get(key, {})
        if meta.get("type") == "ms1_rt":
            label = meta["label"]
            if label not in seen:
                seen.add(label)
                compounds.append((label, key, f"{label}_Int", meta.get("nl_col")))

    # Group rows by sample group
    group_rows: dict[str, list[dict]] = {g: [] for g in _GROUPS}
    for row in rows:
        group_rows[_sample_group(row.get("SampleName", ""))].append(row)

    # ── Header row ──────────────────────────────────────────────────────────────
    headers = ["Metric"] + [c[0] for c in compounds]
    for col_idx, h in enumerate(headers, start=1):
        if col_idx == 1:
            hex6 = _SAMPLE_HEADER
        else:
            label = compounds[col_idx - 2][0]
            pal = col_meta.get(f"{label}_RT", {}).get("palette", {})
            hex6 = pal.get("header", _MS2_HEADER)
        _apply(ws.cell(row=1, column=col_idx, value=h), **_header_style(hex6))
    ws.row_dimensions[1].height = 30

    # ── Metric rows ─────────────────────────────────────────────────────────────
    metrics = [f"{g} ({len(group_rows[g])})" for g in _GROUPS] + [
        "Total Detection",
        "Mean RT (min)",
        "Mean Int",
        "NL ✓/⚠/✗",
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

        for col_idx, (label, rt_key, int_key, nl_key) in enumerate(compounds, start=2):
            cell = ws.cell(row=row_idx, column=col_idx)

            # Per-group detection rate rows
            group_match = next((g for g in _GROUPS if metric.startswith(g)), None)
            if group_match:
                src = group_rows[group_match]
                n_total = len(src)
                n_det = sum(1 for r in src if _is_detected(r, rt_key, int_key, nl_key))
                pct = n_det / n_total * 100 if n_total else 0
                val: object = f"{n_det}/{n_total} ({pct:.0f}%)"

            elif metric == "Total Detection":
                n_det = sum(1 for r in rows if _is_detected(r, rt_key, int_key, nl_key))
                pct = n_det / len(rows) * 100 if rows else 0
                val = f"{n_det}/{len(rows)} ({pct:.0f}%)"

            elif metric == "Mean RT (min)":
                det = [r for r in rows if _is_detected(r, rt_key, int_key, nl_key)]
                rt_vals = [
                    v for r in det if (v := _safe_float(r.get(rt_key, ""))) is not None
                ]
                val = f"{sum(rt_vals) / len(rt_vals):.4f}" if rt_vals else "—"

            elif metric == "Mean Int":
                det = [r for r in rows if _is_detected(r, rt_key, int_key, nl_key)]
                int_vals = [
                    v for r in det if (v := _safe_float(r.get(int_key, ""))) is not None
                ]
                val = f"{sum(int_vals) / len(int_vals):,.0f}" if int_vals else "—"

            elif metric == "NL ✓/⚠/✗":
                if nl_key:
                    nl_vals = [r.get(nl_key, "") for r in rows]
                    n_ok = sum(1 for v in nl_vals if v == "OK")
                    n_warn = sum(1 for v in nl_vals if v.startswith("WARN_"))
                    n_nd = len(rows) - n_ok - n_warn
                    val = f"✓{n_ok} ⚠{n_warn} ✗{n_nd}"
                else:
                    val = "—"

            elif metric == "RT Δ vs ISTD (%)":
                istd_label = col_meta.get(rt_key, {}).get("istd_pair", "")
                if not istd_label:
                    val = "—"
                else:
                    istd_rt_key = f"{istd_label}_RT"
                    istd_nl_col = col_meta.get(istd_rt_key, {}).get("nl_col")
                    deltas: list[float] = []
                    for r in rows:
                        if nl_key:
                            analyte_nl = r.get(nl_key, "")
                            if analyte_nl != "OK" and not analyte_nl.startswith(
                                "WARN_"
                            ):
                                continue
                        if istd_nl_col:
                            istd_nl = r.get(istd_nl_col, "")
                            if istd_nl != "OK" and not istd_nl.startswith("WARN_"):
                                continue
                        rt_analyte = _safe_float(r.get(rt_key, ""))
                        rt_istd = _safe_float(r.get(istd_rt_key, ""))
                        if rt_analyte is None or rt_istd is None or rt_istd == 0:
                            continue
                        deltas.append(abs(rt_analyte - rt_istd) / rt_istd * 100)
                    if not deltas:
                        val = "—"
                    else:
                        mean_delta = sum(deltas) / len(deltas)
                        sd_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
                        val = f"{mean_delta:.2f}±{sd_delta:.2f}% (n={len(deltas)})"

            else:
                val = "—"

            _apply(
                cell, value=val, fill=_fill(fill_hex), alignment=CENTER, border=BORDER
            )

    # Column widths
    ws.column_dimensions["A"].width = 22
    for col_idx in range(2, len(compounds) + 2):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18

    ws.freeze_panes = "B2"


# ── Entry point for frozen-exe import ─────────────────────────────────────────
def run(base_dir: Path) -> None:
    """Entry point for both direct call and frozen-exe import."""
    config_dir = base_dir / "config"
    output_dir = base_dir / "output"
    csv_path = output_dir / "xic_results.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    excel_path = output_dir / f"xic_results_{timestamp}.xlsx"

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("CSV is empty.")
        return

    csv_keys = list(rows[0].keys())
    col_meta = _load_column_meta(config_dir)

    wb = Workbook()
    ws_data = wb.active
    ws_data.title = "XIC Results"
    _build_data_sheet(ws_data, rows, col_meta, csv_keys)

    ws_sum = wb.create_sheet("Summary")
    _build_summary_sheet(ws_sum, rows, col_meta, csv_keys)

    wb.save(excel_path)

    ms1_cols = [k for k in csv_keys if col_meta.get(k, {}).get("type") == "ms1_rt"]
    ms2_cols = [k for k in csv_keys if col_meta.get(k, {}).get("type") == "ms2_nl"]
    print(f"Saved : {excel_path}")
    print(f"Rows  : {len(rows)}")
    for k in ms1_cols:
        nl_col = col_meta.get(k, {}).get("nl_col")
        if nl_col:
            n_det = sum(
                1
                for r in rows
                if _safe_float(r.get(k, "")) is not None
                and (r.get(nl_col, "") == "OK" or r.get(nl_col, "").startswith("WARN_"))
            )
            print(
                f"  {k.replace('_RT', '')} detected (NL confirmed): {n_det}/{len(rows)}"
            )
        else:
            n_det = sum(1 for r in rows if _safe_float(r.get(k, "")) is not None)
            print(f"  {k.replace('_RT', '')} detected: {n_det}/{len(rows)}")
    for k in ms2_cols:
        n_ok = sum(1 for r in rows if r.get(k, "") == "OK")
        n_warn = sum(1 for r in rows if r.get(k, "").startswith("WARN_"))
        n_nd = len(rows) - n_ok - n_warn
        print(f"  {k}  OK:{n_ok}  WARN:{n_warn}  ND:{n_nd}")
    for k in ms1_cols:
        if not col_meta.get(k, {}).get("is_istd", False):
            continue
        label_name = k.replace("_RT", "")
        nl_col = col_meta.get(k, {}).get("nl_col")
        if nl_col:
            n_det = sum(
                1
                for r in rows
                if _safe_float(r.get(k, "")) is not None
                and (r.get(nl_col, "") == "OK" or r.get(nl_col, "").startswith("WARN_"))
            )
        else:
            n_det = sum(1 for r in rows if _safe_float(r.get(k, "")) is not None)
        if n_det < len(rows):
            print(f"ISTD_ND: {label_name} {n_det}/{len(rows)}")


# ── CLI entry point ────────────────────────────────────────────────────────────
def main() -> None:
    base_dir = Path(__file__).parent.parent
    run(base_dir)


if __name__ == "__main__":
    main()
