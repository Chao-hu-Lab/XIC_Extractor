from __future__ import annotations

import csv
from pathlib import Path

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.output.workbook_values import ND_ERROR, _safe_float
from xic_extractor.sample_groups import classify_sample_group


def _sample_group(name: str) -> str:
    return classify_sample_group(name)

def _read_diagnostics(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))

def _read_long_results(
    config: ExtractionConfig, targets: list[Target]
) -> list[dict[str, str]]:
    long_path = config.output_csv.with_name("xic_results_long.csv")
    if long_path.exists():
        return _read_results(long_path)
    return _wide_to_long_rows(_read_results(config.output_csv), targets)


def _wide_to_long_rows(
    rows: list[dict[str, str]], targets: list[Target]
) -> list[dict[str, str]]:
    long_rows: list[dict[str, str]] = []
    for row in rows:
        sample_name = row.get("SampleName", "")
        for target in targets:
            long_rows.append(
                {
                    "SampleName": sample_name,
                    "Group": _sample_group(sample_name),
                    "Target": target.label,
                    "Role": "ISTD" if target.is_istd else "Analyte",
                    "ISTD Pair": target.istd_pair,
                    "RT": row.get(f"{target.label}_RT", ""),
                    "Area": row.get(f"{target.label}_Area", ""),
                    "NL": row.get(f"{target.label}_NL", "")
                    if target.neutral_loss_da is not None
                    else "",
                    "Int": row.get(f"{target.label}_Int", ""),
                    "PeakStart": row.get(f"{target.label}_PeakStart", ""),
                    "PeakEnd": row.get(f"{target.label}_PeakEnd", ""),
                    "PeakWidth": _legacy_peak_width(row, target.label),
                    "Confidence": "HIGH",
                    "Reason": "",
                }
            )
    return long_rows


def _read_score_breakdown(config: ExtractionConfig) -> list[dict[str, str]]:
    path = config.output_csv.with_name("xic_score_breakdown.csv")
    if not path.exists():
        return []
    return _read_results(path)


def _legacy_peak_width(row: dict[str, str], label: str) -> str:
    existing = row.get(f"{label}_PeakWidth", "")
    if existing:
        return existing
    start = row.get(f"{label}_PeakStart", "")
    end = row.get(f"{label}_PeakEnd", "")
    if start in ND_ERROR or end in ND_ERROR:
        return start if start == end else ""
    start_value = _safe_float(start)
    end_value = _safe_float(end)
    if start_value is None or end_value is None:
        return ""
    return f"{abs(end_value - start_value):.4f}"


def _read_results(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))
