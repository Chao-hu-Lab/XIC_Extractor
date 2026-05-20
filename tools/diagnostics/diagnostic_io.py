"""Small IO helpers shared by diagnostics.

Keep this module deliberately narrow. It is not a diagnostic framework; it only
holds repeated CSV/TSV mechanics that already appear across multiple reports.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


def read_delimited_rows(
    path: Path,
    *,
    required_columns: Sequence[str],
    delimiter: str = "\t",
    encoding: str = "utf-8",
) -> list[dict[str, str]]:
    with path.open(newline="", encoding=encoding) as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def write_tsv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    fieldnames: Sequence[str],
    *,
    formatter: Callable[[Any], str] | None = None,
) -> None:
    value_formatter = formatter or format_diagnostic_value
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: value_formatter(row.get(key, "")) for key in fieldnames},
            )


def format_diagnostic_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.6g}"
    return str(value)
