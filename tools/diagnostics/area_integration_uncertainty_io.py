from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from pathlib import Path

from tools.diagnostics.area_integration_uncertainty_models import (
    AlignmentIntegrationAudit,
    EvidenceRow,
    TargetedAudit,
)


def _read_evidence_rows(path: Path) -> tuple[EvidenceRow, ...]:
    rows = _read_required_tsv(
        path,
        (
            "sample",
            "target_label",
            "role",
            "targeted_candidate_id",
            "untargeted_family_id",
            "target_mz",
            "untargeted_family_mz",
            "targeted_area",
            "untargeted_area",
            "area_ratio_untargeted_to_targeted",
            "boundary_delta_start_min",
            "boundary_delta_end_min",
            "targeted_region_verdict",
            "untargeted_region_verdict",
            "targeted_local_mixture_verdict",
            "untargeted_local_mixture_verdict",
            "mismatch_reason",
        ),
    )
    return tuple(
        EvidenceRow(
            sample=row["sample"],
            target_label=row["target_label"],
            role=row["role"],
            targeted_candidate_id=row["targeted_candidate_id"],
            untargeted_family_id=row["untargeted_family_id"],
            target_mz=_optional_float(row["target_mz"]),
            untargeted_family_mz=_optional_float(row["untargeted_family_mz"]),
            targeted_area=_optional_float(row["targeted_area"]),
            untargeted_area=_optional_float(row["untargeted_area"]),
            raw_area_ratio=_optional_float(row["area_ratio_untargeted_to_targeted"]),
            boundary_delta_start_min=_optional_float(row["boundary_delta_start_min"]),
            boundary_delta_end_min=_optional_float(row["boundary_delta_end_min"]),
            targeted_region_verdict=row["targeted_region_verdict"],
            untargeted_region_verdict=row["untargeted_region_verdict"],
            targeted_local_mixture_verdict=row["targeted_local_mixture_verdict"],
            untargeted_local_mixture_verdict=row["untargeted_local_mixture_verdict"],
            mismatch_reason=row["mismatch_reason"],
        )
        for row in rows
    )


def _read_targeted_audits(path: Path) -> dict[tuple[str, str, str], TargetedAudit]:
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "candidate_id",
            "selected",
            "area_raw_counts_seconds",
            "area_baseline_corrected",
            "area_uncertainty",
        ),
    )
    audits: dict[tuple[str, str, str], TargetedAudit] = {}
    for row in rows:
        if _bool_value(row["selected"]) is not True:
            continue
        area = _optional_float(row["area_raw_counts_seconds"])
        baseline_area = _optional_float(row["area_baseline_corrected"])
        uncertainty = _optional_float(row["area_uncertainty"])
        key = (row["sample_name"], row["target_label"], row["candidate_id"])
        audits[key] = TargetedAudit(
            sample=row["sample_name"],
            target_label=row["target_label"],
            candidate_id=row["candidate_id"],
            area=area,
            baseline_area=baseline_area,
            area_uncertainty=uncertainty,
            uncertainty_fraction=_ratio(uncertainty, area),
            baseline_fraction=_ratio(baseline_area, area),
        )
    return audits


def _read_boundary_alternatives(path: Path) -> dict[tuple[str, str, str], float | None]:
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "candidate_id",
            "selected_candidate",
            "boundary_audit_top",
            "area_ratio_vs_candidate_interval",
            "is_candidate_interval",
        ),
    )
    values: dict[tuple[str, str, str], float | None] = {}
    for row in rows:
        if _bool_value(row["selected_candidate"]) is not True:
            continue
        if _bool_value(row["boundary_audit_top"]) is not True:
            continue
        key = (row["sample_name"], row["target_label"], row["candidate_id"])
        values.setdefault(key, _optional_float(row["area_ratio_vs_candidate_interval"]))
    return values


def _read_alignment_integration_audits(
    path: Path,
) -> dict[tuple[str, str], AlignmentIntegrationAudit]:
    rows = _read_required_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "area",
            "area_baseline_corrected",
            "area_uncertainty",
            "uncertainty_fraction",
            "baseline_fraction",
        ),
    )
    audits: dict[tuple[str, str], AlignmentIntegrationAudit] = {}
    for row in rows:
        key = (row["feature_family_id"], row["sample_stem"])
        area = _optional_float(row["area"])
        baseline_area, baseline_area_method = _alignment_baseline_area(row)
        audits[key] = AlignmentIntegrationAudit(
            family_id=row["feature_family_id"],
            sample=row["sample_stem"],
            area=area,
            baseline_area=baseline_area,
            baseline_area_method=baseline_area_method,
            area_uncertainty=_optional_float(row["area_uncertainty"]),
            uncertainty_fraction=_optional_float(row["uncertainty_fraction"]),
            baseline_fraction=_ratio(baseline_area, area),
        )
    return audits


def _alignment_baseline_area(row: dict[str, str]) -> tuple[float | None, str]:
    rollback_area = _optional_float(row.get("area_baseline_corrected_linear_edge"))
    if rollback_area is not None:
        return rollback_area, "linear_edge_compatible"
    return _optional_float(row["area_baseline_corrected"]), "reported_baseline"


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


def _bool_value(value: object) -> bool | None:
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator
