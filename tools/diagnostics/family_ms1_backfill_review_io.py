"""Input loading helpers for family MS1 backfill review reports."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


def _load_overlay_evidence(
    *,
    overlay_trace_data_dirs: Sequence[Path],
    overlay_trace_data_files: Sequence[Path],
) -> dict[str, dict[str, Any]]:
    files: list[Path] = []
    for directory in overlay_trace_data_dirs:
        if directory.is_dir():
            files.extend(sorted(directory.glob("*_trace_data.json")))
    files.extend(overlay_trace_data_files)
    evidence: dict[str, dict[str, Any]] = {}
    for path in files:
        if not path.is_file():
            raise ValueError(f"Overlay trace data JSON not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        family_id = str(data.get("family_id", ""))
        if not family_id:
            raise ValueError(f"Overlay trace data missing family_id: {path}")
        evidence[family_id] = dict(data.get("evidence_summary") or {})
    return evidence


def _cells_by_family(
    rows: Iterable[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["feature_family_id"])].append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _read_tsv(path: Path, *, required_columns: Sequence[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"Required TSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields = reader.fieldnames or ()
        field_set = set(fields)
        missing = [field for field in required_columns if field not in field_set]
        if missing:
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
        return list(reader)
