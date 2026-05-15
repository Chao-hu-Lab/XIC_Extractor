"""Input loaders for the single-dR production gate decision report."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def read_tsv(
    path: Path,
    *,
    required_columns: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = tuple(reader.fieldnames or ())
            missing = [
                column for column in required_columns if column not in fieldnames
            ]
            if missing:
                raise ValueError(
                    f"{path}: missing required columns: {', '.join(missing)}"
                )
            return tuple(dict(row) for row in reader)
    except OSError as exc:
        raise ValueError(f"{path}: could not read TSV: {exc}") from exc


def load_discovery_candidates(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "not_provided", "candidates": {}}
    rows, fieldnames = _read_delimited_rows(path)
    missing = [
        column
        for column in ("sample_stem", "candidate_csv")
        if column not in fieldnames
    ]
    if missing:
        raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
    candidates: dict[tuple[str, str], dict[str, float | str]] = {}
    for _, row in rows:
        sample = _machine_text(row.get("sample_stem", ""))
        candidate_csv = _machine_text(row.get("candidate_csv", ""))
        if not sample or not candidate_csv:
            continue
        candidate_path = _resolve_artifact_path(path.parent, candidate_csv)
        candidate_rows, candidate_fieldnames = _read_delimited_rows(candidate_path)
        if "candidate_id" not in candidate_fieldnames:
            raise ValueError(
                f"{candidate_path}: missing required columns: candidate_id"
            )
        for _, candidate_row in candidate_rows:
            candidate_id = _machine_text(candidate_row.get("candidate_id", ""))
            if not candidate_id:
                continue
            quality = {
                "sample_stem": _machine_text(
                    candidate_row.get("sample_stem", sample),
                )
                or sample,
                "candidate_id": candidate_id,
                "evidence_score": _float_or_none(
                    candidate_row.get("evidence_score", ""),
                ),
                "seed_event_count": _float_or_none(
                    candidate_row.get("seed_event_count", ""),
                ),
                "neutral_loss_mass_error_ppm": _float_or_none(
                    candidate_row.get("neutral_loss_mass_error_ppm", ""),
                ),
                "ms1_scan_support_score": _float_or_none(
                    candidate_row.get("ms1_scan_support_score", ""),
                ),
            }
            candidate_sample = str(quality["sample_stem"])
            candidates[(candidate_sample, candidate_id)] = quality
            candidates[("", candidate_id)] = quality
    return {"status": "provided", "candidates": candidates}


def load_rt_context(path: Path | None) -> dict[str, str]:
    if path is None:
        return {"status": "not_provided"}
    rows = read_tsv(path, required_columns=("feature_family_id",))
    contexts: dict[str, str] = {"status": "provided"}
    for row in rows:
        family_id = row.get("feature_family_id", "")
        if not family_id:
            continue
        text = ";".join(
            (
                row.get("rt_context", ""),
                row.get("normalized_rt_support", ""),
                row.get("irt_support", ""),
                row.get("rt_warping_effect", ""),
            ),
        ).lower()
        if "worsen" in text or "context_rt_worsened" in text:
            contexts[family_id] = "context_rt_worsened"
    return contexts


def load_targeted_istd_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "not_provided", "families": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    summaries = payload.get("summaries", ())
    if not isinstance(summaries, Sequence) or isinstance(summaries, (str, bytes)):
        raise ValueError(f"{path}: summaries must be a list")
    by_family: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"target_labels": set(), "statuses": set()},
    )
    for item in summaries:
        if not isinstance(item, Mapping):
            continue
        target = str(item.get("target_label", ""))
        status = str(item.get("status", "UNKNOWN") or "UNKNOWN")
        family_ids = set(_string_list(item.get("primary_feature_ids", ())))
        selected = str(item.get("selected_feature_id", "") or "")
        if selected:
            family_ids.add(selected)
        for family_id in family_ids:
            by_family[family_id]["target_labels"].add(target)
            by_family[family_id]["statuses"].add(status)
    return {
        "status": "provided",
        "families": {
            family_id: {
                "target_labels": tuple(sorted(data["target_labels"])),
                "statuses": tuple(sorted(data["statuses"])),
            }
            for family_id, data in by_family.items()
        },
    }


def _read_delimited_rows(
    path: Path,
) -> tuple[list[tuple[int, dict[str, str]]], tuple[str, ...]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            return (
                [(index, dict(row)) for index, row in enumerate(reader, start=2)],
                tuple(reader.fieldnames or ()),
            )
    except OSError as exc:
        raise ValueError(f"{path}: could not read table: {exc}") from exc


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part for part in _split_list(value) if part)
    if isinstance(value, Sequence):
        return tuple(str(part) for part in value if str(part))
    return ()


def _split_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())


def _float_or_none(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _resolve_artifact_path(parent: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else parent / path


def _machine_text(value: str) -> str:
    if len(value) >= 2 and value[0] == "'" and value[1] in ("=", "+", "-", "@"):
        return value[1:]
    return value
