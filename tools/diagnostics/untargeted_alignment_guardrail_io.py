"""File IO helpers for untargeted alignment guardrails."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from pathlib import Path

from tools.diagnostics.diagnostic_io import write_delimited_rows


def _read_required_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return _read_tsv(path)


def _read_optional_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return _read_tsv(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_dict_csv(path: Path | None, rows: list[dict[str, str]]) -> None:
    if path is None:
        raise ValueError("comparison output path is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    write_delimited_rows(
        path,
        rows,
        tuple(rows[0]),
        extrasaction="raise",
        formatter=_format_csv_value,
    )


def _format_csv_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
