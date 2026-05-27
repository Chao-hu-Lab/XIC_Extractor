from __future__ import annotations

from pathlib import Path

from tools.diagnostics.diagnostic_io import (
    bool_value as _bool_value,
    optional_float as _optional_float,
    optional_int as _optional_int,
    read_tsv_required as _read_required_tsv,
)
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
