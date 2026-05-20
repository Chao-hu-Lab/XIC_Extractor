import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from xic_extractor.instrument_qc.models import (
    InstrumentQCDiagnostic,
    SDOLEKTrendRow,
)

TREND_TSV_COLUMNS = [
    "sample_name",
    "raw_path",
    "injection_order",
    "compound",
    "precursor_mz",
    "identity_evidence",
    "reference_rt_min",
    "rt_delta_to_reference_min",
    "apex_rt_min",
    "area",
    "base_width_min",
    "reference_base_width_min",
    "base_width_ratio_to_reference",
    "peak_start_rt_min",
    "peak_end_rt_min",
    "trend_confidence",
    "trend_flags",
    "status",
    "reason",
]

DIAGNOSTIC_TSV_COLUMNS = ["sample_name", "raw_path", "issue", "detail"]


def write_trend_tsv(path: Path, rows: Iterable[SDOLEKTrendRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TREND_TSV_COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(_trend_row_to_dict(row))


def write_diagnostics_tsv(
    path: Path,
    diagnostics: Iterable[InstrumentQCDiagnostic],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=DIAGNOSTIC_TSV_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for diagnostic in diagnostics:
            writer.writerow(
                {
                    "sample_name": diagnostic.sample_name,
                    "raw_path": str(diagnostic.raw_path),
                    "issue": diagnostic.issue,
                    "detail": diagnostic.detail,
                }
            )


def write_sdolek_json(
    path: Path,
    rows: Iterable[SDOLEKTrendRow],
    diagnostics: Iterable[InstrumentQCDiagnostic],
) -> None:
    row_list = list(rows)
    diagnostic_list = list(diagnostics)
    payload = {
        "summary": {
            "total_rows": len(row_list),
            "status_counts": _counts(row.status for row in row_list),
            "compound_counts": _counts(row.compound for row in row_list),
            "diagnostic_counts": _counts(diag.issue for diag in diagnostic_list),
        },
        "rows": [_trend_row_to_dict(row) for row in row_list],
        "diagnostics": [_diagnostic_to_dict(diag) for diag in diagnostic_list],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _trend_row_to_dict(row: SDOLEKTrendRow) -> dict[str, object]:
    values = asdict(row)
    values["raw_path"] = str(row.raw_path)
    values["trend_flags"] = ";".join(row.trend_flags)
    return values


def _diagnostic_to_dict(diagnostic: InstrumentQCDiagnostic) -> dict[str, object]:
    return {
        "sample_name": diagnostic.sample_name,
        "raw_path": str(diagnostic.raw_path),
        "issue": diagnostic.issue,
        "detail": diagnostic.detail,
    }


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts
