from __future__ import annotations

import csv
import statistics
from pathlib import Path

from openpyxl import load_workbook

_MIN_WINDOW_SAMPLES = 3


def read_injection_order(path: Path) -> dict[str, int]:
    """Read CSV/XLSX with Sample_Name and Injection_Order columns."""
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return _read_xlsx(path)
    if suffix == ".csv":
        return _read_csv(path)
    raise ValueError(f"Unsupported injection-order file type: {suffix}")


def _read_csv(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with path.open(encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("Sample_Name") or "").strip()
            order = row.get("Injection_Order")
            if not name or order in (None, ""):
                continue
            out[name] = int(str(order).strip())
    return out


def _read_xlsx(path: Path) -> dict[str, int]:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows = ws.iter_rows(values_only=True)
        header = next(rows)
        cols = {str(value): i for i, value in enumerate(header) if value is not None}
        name_i = cols["Sample_Name"]
        order_i = cols["Injection_Order"]
        out: dict[str, int] = {}
        for row in rows:
            name = row[name_i]
            order = row[order_i]
            if name is None or order is None:
                continue
            out[str(name).strip()] = int(str(order).strip())
        return out
    finally:
        wb.close()


def rolling_median_rt(
    istd_label: str,
    target_sample: str,
    rt_by_sample: dict[str, float],
    injection_order: dict[str, int],
    window: int,
) -> float | None:
    """Return the median RT for samples within the target injection window."""
    _ = istd_label
    target_order = injection_order.get(target_sample)
    if target_order is None:
        return None
    lo = target_order - window
    hi = target_order + window
    values: list[float] = []
    for sample, rt in rt_by_sample.items():
        order = injection_order.get(sample)
        if order is None:
            continue
        if lo <= order <= hi:
            values.append(rt)
    if len(values) < _MIN_WINDOW_SAMPLES:
        return None
    return float(statistics.median(values))
