"""Small IO helpers shared by package diagnostics and diagnostic tools.

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


def read_tsv_required(
    path: Path,
    required_columns: Sequence[str],
) -> tuple[dict[str, str], ...]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return tuple(
        read_delimited_rows(
            path,
            required_columns=required_columns,
            encoding="utf-8-sig",
        )
    )


def require_fields(
    rows: Sequence[Mapping[str, Any]],
    required_columns: Sequence[str],
    path: Path,
) -> None:
    if not rows:
        raise ValueError(f"{path} has no data rows")
    fieldnames = set(rows[0])
    missing = [column for column in required_columns if column not in fieldnames]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")


def write_tsv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    fieldnames: Sequence[str],
    *,
    formatter: Callable[[Any], str] | None = None,
    lineterminator: str | None = None,
) -> None:
    write_delimited_rows(
        path,
        rows,
        fieldnames,
        delimiter="\t",
        formatter=formatter,
        lineterminator=lineterminator,
    )


def write_delimited_rows(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    fieldnames: Sequence[str],
    *,
    delimiter: str = ",",
    formatter: Callable[[Any], str] | None = None,
    lineterminator: str | None = None,
) -> None:
    value_formatter = formatter or format_diagnostic_value
    writer_kwargs: dict[str, Any] = {
        "delimiter": delimiter,
        "fieldnames": fieldnames,
        "extrasaction": "ignore",
    }
    if lineterminator is not None:
        writer_kwargs["lineterminator"] = lineterminator
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, **writer_kwargs)
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


def optional_float(value: object) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value) if math.isfinite(value) else None
    text = str(value).strip()
    if text.startswith("'"):
        text = text[1:].strip()
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def optional_int(value: object) -> int | None:
    parsed = optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def required_float(value: object, field: str, label: str) -> float:
    parsed = optional_float(value)
    if parsed is None:
        raise ValueError(f"{label} has invalid {field}: {value!r}")
    return parsed


def bool_value(value: object) -> bool | None:
    normalized = text_value(value).upper()
    if normalized in {"TRUE", "T", "YES", "Y", "1"}:
        return True
    if normalized in {"FALSE", "F", "NO", "N", "0"}:
        return False
    return None


def text_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def split_semicolon_labels(value: object) -> list[str]:
    return [part.strip() for part in text_value(value).split(";") if part.strip()]


def required_indexes(
    header: Sequence[object],
    required_columns: Sequence[str],
    sheet_name: str,
) -> dict[str, int]:
    indexes = {
        str(value).strip(): index for index, value in enumerate(header) if value
    }
    missing = [column for column in required_columns if column not in indexes]
    if missing:
        raise ValueError(
            f"{sheet_name}: missing required columns: {', '.join(missing)}"
        )
    return {column: indexes[column] for column in required_columns}
