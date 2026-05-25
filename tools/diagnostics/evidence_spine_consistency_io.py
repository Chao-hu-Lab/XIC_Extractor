from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from pathlib import Path

from tools.diagnostics.evidence_spine_consistency_models import (
    AlignmentCell,
    TargetedCandidate,
    TargetedShadow,
)


def _read_targeted_candidates(path: Path) -> tuple[TargetedCandidate, ...]:
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "role",
            "candidate_id",
            "selected",
            "rt_apex_min",
            "rt_left_min",
            "rt_right_min",
            "area_raw_counts_seconds",
            "area_baseline_corrected",
            "region_scan_count",
        ),
    )
    return tuple(
        TargetedCandidate(
            sample=row["sample_name"],
            target_label=row["target_label"],
            role=row["role"],
            candidate_id=row["candidate_id"],
            rt=_optional_float(row["rt_apex_min"]),
            left=_optional_float(row["rt_left_min"]),
            right=_optional_float(row["rt_right_min"]),
            area=_optional_float(row["area_raw_counts_seconds"]),
            baseline_area=_optional_float(row["area_baseline_corrected"]),
            scan_count=_optional_int(row["region_scan_count"]),
        )
        for row in rows
        if _bool_value(row["selected"]) is True
    )


def _read_target_mz(path: Path) -> dict[tuple[str, str, str], float]:
    if not path.exists():
        return {}
    rows = _read_required_tsv(
        path,
        ("sample_name", "target_label", "candidate_id", "target_mz"),
    )
    values: dict[tuple[str, str, str], float] = {}
    for row in rows:
        value = _optional_float(row["target_mz"])
        if value is None:
            continue
        key = (row["sample_name"], row["target_label"], row["candidate_id"])
        values.setdefault(key, value)
    return values


def _read_targeted_shadows(path: Path) -> dict[tuple[str, str], TargetedShadow]:
    if not path.exists():
        return {}
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "shadow_verdict",
            "local_mixture_diagnostic",
        ),
    )
    return {
        (row["sample_name"], row["target_label"]): TargetedShadow(
            shadow_verdict=row["shadow_verdict"],
            local_mixture_diagnostic=row["local_mixture_diagnostic"],
        )
        for row in rows
    }


def _read_alignment_cells(path: Path) -> tuple[AlignmentCell, ...]:
    rows = _read_required_tsv(
        path,
        (
            "sample_stem",
            "feature_family_id",
            "status",
            "area",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "family_center_mz",
            "region_shadow_verdict",
            "region_local_mixture_diagnostic",
        ),
    )
    return tuple(
        AlignmentCell(
            sample=row["sample_stem"],
            family_id=row["feature_family_id"],
            status=row["status"],
            mz=_optional_float(row["family_center_mz"]),
            rt=_optional_float(row["apex_rt"]),
            area=_optional_float(row["area"]),
            left=_optional_float(row["peak_start_rt"]),
            right=_optional_float(row["peak_end_rt"]),
            region_verdict=row["region_shadow_verdict"],
            local_mixture_diagnostic=row["region_local_mixture_diagnostic"],
            reason=row.get("reason", ""),
        )
        for row in rows
    )


def _read_required_tsv(
    path: Path,
    required: Sequence[str],
) -> tuple[dict[str, str], ...]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return tuple(dict(row) for row in reader)


def _optional_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_int(value: object) -> int | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _bool_value(value: object) -> bool | None:
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None
