from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import (
    cells_by_cluster,
    count_status,
    escape_excel_formula,
    format_value,
    production_matrix_area,
    row_id,
    safe_rate,
)
from xic_extractor.alignment.production_decisions import build_production_decisions

ALIGNMENT_REVIEW_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "family_observed_neutral_loss_da",
    "has_anchor",
    "event_cluster_count",
    "event_cluster_ids",
    "event_member_count",
    "detected_count",
    "absent_count",
    "unchecked_count",
    "duplicate_assigned_count",
    "ambiguous_ms1_owner_count",
    "present_rate",
    "identity_decision",
    "identity_confidence",
    "primary_evidence",
    "identity_reason",
    "quantifiable_detected_count",
    "quantifiable_rescue_count",
    "accepted_cell_count",
    "accepted_rescue_count",
    "review_rescue_count",
    "include_in_primary_matrix",
    "row_flags",
    "artificial_adduct_role",
    "artificial_adduct_name",
    "artificial_adduct_related_family_id",
    "artificial_adduct_mz_delta_error_ppm",
    "artificial_adduct_rt_delta_min",
    "representative_samples",
    "family_evidence",
    "warning",
    "reason",
)

ALIGNMENT_CELLS_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "height",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
    "trace_quality",
    "scan_support_score",
    "source_candidate_id",
    "source_raw_file",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "reason",
    "region_candidate_count",
    "region_selected_proposal_sources",
    "region_selected_merge_note",
    "region_shadow_status",
    "region_shadow_verdict",
    "region_merge_suggestion_source",
    "region_area_ratio",
    "region_selected_interval_count",
    "region_selected_interval_gap_max_min",
    "region_local_mixture_diagnostic",
    "region_local_mixture_reason",
    "region_review_reason",
)

BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "area_baseline_corrected",
    "area_uncertainty",
    "area_uncertainty_formula_version",
    "baseline_residual_mad",
    "area_uncertainty_noise_source",
    "baseline_type",
    "baseline_score",
    "uncertainty_fraction",
    "baseline_fraction",
    "integration_scan_count",
)

ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS = BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS

ASLS_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS = (
    "area_baseline_corrected_asls",
    "baseline_score_asls",
)

ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "backfill_seed_mz",
    "backfill_seed_rt",
    "backfill_request_rt_min",
    "backfill_request_rt_max",
    "backfill_request_ppm",
    "backfill_apex_delta_sec",
    "reason",
)


def write_alignment_review_tsv(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> Path:
    config = alignment_config or AlignmentConfig()
    return _write_tsv(
        path,
        ALIGNMENT_REVIEW_COLUMNS,
        _review_rows(matrix, alignment_config=config),
    )


def write_alignment_matrix_tsv(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> Path:
    columns = (
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        *matrix.sample_order,
    )
    rows: list[dict[str, object]] = []
    grouped_cells = cells_by_cluster(matrix)
    decisions = build_production_decisions(
        matrix,
        alignment_config or AlignmentConfig(),
    )
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        row_decision = decisions.row(cluster_id)
        if not row_decision.include_in_primary_matrix:
            continue
        cells = grouped_cells.get(cluster_id, ())
        cells_by_sample = {cell.sample_stem: cell for cell in cells}
        row: dict[str, object] = {
            "feature_family_id": cluster_id,
            "neutral_loss_tag": cluster.neutral_loss_tag,
            "family_center_mz": format_value(_family_center_mz(cluster)),
            "family_center_rt": format_value(_family_center_rt(cluster)),
        }
        for sample_stem in matrix.sample_order:
            cell = cells_by_sample.get(sample_stem)
            decision = (
                decisions.cell(cluster_id, sample_stem) if cell is not None else None
            )
            row[sample_stem] = production_matrix_area(decision)
        rows.append(row)
    return _write_tsv(path, columns, rows)


def write_alignment_cells_tsv(path: Path, matrix: AlignmentMatrix) -> Path:
    clusters_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    rows: list[dict[str, object]] = []
    for cell in matrix.cells:
        cluster = clusters_by_id[cell.cluster_id]
        rows.append(
            {
                "feature_family_id": cell.cluster_id,
                "sample_stem": cell.sample_stem,
                "status": cell.status,
                "area": format_value(cell.area),
                "apex_rt": format_value(cell.apex_rt),
                "height": format_value(cell.height),
                "peak_start_rt": format_value(cell.peak_start_rt),
                "peak_end_rt": format_value(cell.peak_end_rt),
                "rt_delta_sec": format_value(cell.rt_delta_sec),
                "trace_quality": cell.trace_quality,
                "scan_support_score": format_value(cell.scan_support_score),
                "source_candidate_id": cell.source_candidate_id or "",
                "source_raw_file": str(cell.source_raw_file or ""),
                "neutral_loss_tag": cluster.neutral_loss_tag,
                "family_center_mz": format_value(_family_center_mz(cluster)),
                "family_center_rt": format_value(_family_center_rt(cluster)),
                "reason": cell.reason,
                "region_candidate_count": format_value(cell.region_candidate_count),
                "region_selected_proposal_sources": ";".join(
                    cell.region_selected_proposal_sources
                ),
                "region_selected_merge_note": cell.region_selected_merge_note,
                "region_shadow_status": cell.region_shadow_status,
                "region_shadow_verdict": cell.region_shadow_verdict,
                "region_merge_suggestion_source": cell.region_merge_suggestion_source,
                "region_area_ratio": format_value(cell.region_area_ratio),
                "region_selected_interval_count": format_value(
                    cell.region_selected_interval_count
                ),
                "region_selected_interval_gap_max_min": format_value(
                    cell.region_selected_interval_gap_max_min
                ),
                "region_local_mixture_diagnostic": (
                    cell.region_local_mixture_diagnostic
                ),
                "region_local_mixture_reason": cell.region_local_mixture_reason,
                "region_review_reason": cell.region_review_reason,
            }
        )
    return _write_tsv(path, ALIGNMENT_CELLS_COLUMNS, rows)


def write_alignment_cell_integration_audit_tsv(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    baseline_integration_method: str = "asls",
    baseline_audit_method: str = "",
) -> Path:
    if baseline_integration_method not in {"asls", "linear_edge"}:
        raise ValueError(
            "baseline_integration_method must be 'asls' or 'linear_edge'"
        )
    if baseline_audit_method not in {"", "asls"}:
        raise ValueError("baseline_audit_method must be empty or 'asls'")
    columns: tuple[str, ...]
    if baseline_integration_method == "asls":
        columns = ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
    elif baseline_audit_method == "asls":
        columns = (
            *BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS,
            *ASLS_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS,
        )
    else:
        columns = BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
    clusters_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    rows: list[dict[str, object]] = []
    for cell in matrix.cells:
        audit = cell.integration_audit
        if audit is None or audit.is_empty:
            continue
        cluster = clusters_by_id[cell.cluster_id]
        row: dict[str, object] = {
            "feature_family_id": cell.cluster_id,
            "sample_stem": cell.sample_stem,
            "status": cell.status,
            "area": format_value(cell.area),
            "apex_rt": format_value(cell.apex_rt),
            "peak_start_rt": format_value(cell.peak_start_rt),
            "peak_end_rt": format_value(cell.peak_end_rt),
            "neutral_loss_tag": cluster.neutral_loss_tag,
            "family_center_mz": format_value(_family_center_mz(cluster)),
            "family_center_rt": format_value(_family_center_rt(cluster)),
            "area_baseline_corrected": format_value(
                audit.area_baseline_corrected
            ),
            "area_uncertainty": format_value(audit.area_uncertainty),
            "area_uncertainty_formula_version": (
                audit.area_uncertainty_formula_version
            ),
            "baseline_residual_mad": format_value(audit.baseline_residual_mad),
            "area_uncertainty_noise_source": audit.area_uncertainty_noise_source,
            "baseline_type": audit.baseline_type,
            "baseline_score": format_value(audit.baseline_score),
            "uncertainty_fraction": format_value(audit.uncertainty_fraction),
            "baseline_fraction": format_value(audit.baseline_fraction),
            "integration_scan_count": format_value(
                audit.integration_scan_count
            ),
        }
        if baseline_integration_method != "asls" and baseline_audit_method == "asls":
            row["area_baseline_corrected_asls"] = format_value(
                audit.area_baseline_corrected_asls
            )
            row["baseline_score_asls"] = format_value(audit.baseline_score_asls)
        rows.append(row)
    return _write_tsv(path, columns, rows)


def write_alignment_owner_backfill_seed_audit_tsv(
    path: Path,
    matrix: AlignmentMatrix,
) -> Path:
    clusters_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    rows: list[dict[str, object]] = []
    for cell in matrix.cells:
        if cell.status != "rescued" or cell.backfill_seed_mz is None:
            continue
        cluster = clusters_by_id[cell.cluster_id]
        rows.append(
            {
                "feature_family_id": cell.cluster_id,
                "sample_stem": cell.sample_stem,
                "status": cell.status,
                "area": cell.area,
                "apex_rt": cell.apex_rt,
                "peak_start_rt": cell.peak_start_rt,
                "peak_end_rt": cell.peak_end_rt,
                "rt_delta_sec": cell.rt_delta_sec,
                "neutral_loss_tag": cluster.neutral_loss_tag,
                "family_center_mz": _family_center_mz(cluster),
                "family_center_rt": _family_center_rt(cluster),
                "backfill_seed_mz": cell.backfill_seed_mz,
                "backfill_seed_rt": cell.backfill_seed_rt,
                "backfill_request_rt_min": cell.backfill_request_rt_min,
                "backfill_request_rt_max": cell.backfill_request_rt_max,
                "backfill_request_ppm": cell.backfill_request_ppm,
                "backfill_apex_delta_sec": _rt_delta_sec(
                    cell.apex_rt,
                    cell.backfill_seed_rt,
                ),
                "reason": cell.reason,
            }
        )
    return _write_tsv(path, ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS, rows)


def write_alignment_status_matrix_tsv(path: Path, matrix: AlignmentMatrix) -> Path:
    columns = (
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        *matrix.sample_order,
    )
    rows: list[dict[str, object]] = []
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        cells = grouped_cells.get(cluster_id, ())
        cells_by_sample = {cell.sample_stem: cell for cell in cells}
        row: dict[str, object] = {
            "feature_family_id": cluster_id,
            "neutral_loss_tag": cluster.neutral_loss_tag,
            "family_center_mz": format_value(_family_center_mz(cluster)),
            "family_center_rt": format_value(_family_center_rt(cluster)),
        }
        for sample_stem in matrix.sample_order:
            cell = cells_by_sample.get(sample_stem)
            row[sample_stem] = "" if cell is None else cell.status
        rows.append(row)
    return _write_tsv(path, columns, rows)


def _review_rows(
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    grouped_cells = cells_by_cluster(matrix)
    sample_count = len(matrix.sample_order)
    decisions = build_production_decisions(matrix, alignment_config)
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        cells = grouped_cells.get(cluster_id, ())
        row_decision = decisions.row(cluster_id)
        detected_count = count_status(cells, "detected")
        rescued_count = count_status(cells, "rescued")
        absent_count = count_status(cells, "absent")
        unchecked_count = count_status(cells, "unchecked")
        duplicate_assigned_count = count_status(cells, "duplicate_assigned")
        ambiguous_owner_count = count_status(cells, "ambiguous_ms1_owner")
        present_count = detected_count + rescued_count
        rows.append(
            {
                "feature_family_id": cluster_id,
                "neutral_loss_tag": cluster.neutral_loss_tag,
                "family_center_mz": _family_center_mz(cluster),
                "family_center_rt": _family_center_rt(cluster),
                "family_product_mz": _family_product_mz(cluster),
                "family_observed_neutral_loss_da": (
                    _family_observed_neutral_loss_da(cluster)
                ),
                "has_anchor": cluster.has_anchor,
                "event_cluster_count": len(_event_cluster_ids(cluster)),
                "event_cluster_ids": ";".join(_event_cluster_ids(cluster)),
                "event_member_count": _event_member_count(cluster),
                "detected_count": detected_count,
                "absent_count": absent_count,
                "unchecked_count": unchecked_count,
                "duplicate_assigned_count": duplicate_assigned_count,
                "ambiguous_ms1_owner_count": ambiguous_owner_count,
                "present_rate": safe_rate(present_count, sample_count),
                "identity_decision": row_decision.identity_decision,
                "identity_confidence": row_decision.identity_confidence,
                "primary_evidence": row_decision.primary_evidence,
                "identity_reason": row_decision.identity_reason,
                "quantifiable_detected_count": (
                    row_decision.quantifiable_detected_count
                ),
                "quantifiable_rescue_count": (
                    row_decision.quantifiable_rescue_count
                ),
                "accepted_cell_count": row_decision.accepted_cell_count,
                "accepted_rescue_count": row_decision.accepted_rescue_count,
                "review_rescue_count": row_decision.review_rescue_count,
                "include_in_primary_matrix": row_decision.include_in_primary_matrix,
                "row_flags": ";".join(row_decision.row_flags),
                "artificial_adduct_role": _optional_attr(
                    cluster, "artificial_adduct_role"
                ),
                "artificial_adduct_name": _optional_attr(
                    cluster, "artificial_adduct_name"
                ),
                "artificial_adduct_related_family_id": _optional_attr(
                    cluster, "artificial_adduct_related_family_id"
                ),
                "artificial_adduct_mz_delta_error_ppm": _optional_attr(
                    cluster, "artificial_adduct_mz_delta_error_ppm"
                ),
                "artificial_adduct_rt_delta_min": _optional_attr(
                    cluster, "artificial_adduct_rt_delta_min"
                ),
                "representative_samples": _representative_samples(cells),
                "family_evidence": _family_evidence(cluster),
                "warning": _warning(
                    cluster,
                    sample_count=sample_count,
                    detected_count=detected_count,
                    rescued_count=rescued_count,
                    unchecked_count=unchecked_count,
                ),
                "reason": _reason(
                    cluster,
                    present_count,
                    sample_count,
                    rescued_count,
                    duplicate_assigned_count,
                    ambiguous_owner_count,
                ),
            }
        )
    return rows


def _write_tsv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, object]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[escape_excel_formula(column) for column in fieldnames],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    escape_excel_formula(column): format_value(row.get(column, ""))
                    for column in fieldnames
                }
            )
    return path


def _representative_samples(cells: tuple[AlignedCell, ...]) -> str:
    samples = [
        cell.sample_stem for cell in cells if cell.status in {"detected", "rescued"}
    ]
    return _cap_semicolon(samples)


def _representative_candidate_ids(cells: tuple[AlignedCell, ...]) -> str:
    candidate_ids = [
        cell.source_candidate_id
        for cell in cells
        if cell.status == "detected" and cell.source_candidate_id
    ]
    return _cap_semicolon(candidate_ids)


def _cap_semicolon(values: list[str]) -> str:
    capped = values[:5]
    if len(values) > 5:
        capped.append("...")
    return ";".join(capped)


def _warning(
    cluster: Any,
    *,
    sample_count: int,
    detected_count: int,
    rescued_count: int,
    unchecked_count: int,
) -> str:
    if not cluster.has_anchor:
        return "no_anchor"
    if sample_count > 0 and unchecked_count / sample_count > 0.5:
        return "high_unchecked"
    if (
        rescued_count > detected_count
        and (detected_count == 0 or not _has_detected_owner_evidence(cluster))
    ):
        return "high_backfill_dependency"
    return ""


def _reason(
    cluster: Any,
    present_count: int,
    sample_count: int,
    rescued_count: int,
    duplicate_assigned_count: int,
    ambiguous_owner_count: int,
) -> str:
    prefix = "anchor family" if cluster.has_anchor else "no anchor"
    parts = [
        prefix,
        f"{present_count}/{sample_count} present",
        f"{rescued_count} MS1 backfilled",
    ]
    event_cluster_count = len(_event_cluster_ids(cluster))
    if event_cluster_count > 1:
        parts.append(f"merged {event_cluster_count} event clusters")
    if duplicate_assigned_count:
        parts.append(f"{duplicate_assigned_count} duplicate-assigned")
    if ambiguous_owner_count:
        parts.append(f"{ambiguous_owner_count} ambiguous MS1 owner")
    return "; ".join(parts)


def _family_center_mz(row: Any) -> float:
    if hasattr(row, "family_center_mz"):
        return row.family_center_mz
    return row.cluster_center_mz


def _family_center_rt(row: Any) -> float:
    if hasattr(row, "family_center_rt"):
        return row.family_center_rt
    return row.cluster_center_rt


def _rt_delta_sec(left_rt: float | None, right_rt: float | None) -> float | None:
    if left_rt is None or right_rt is None:
        return None
    return (left_rt - right_rt) * 60.0


def _family_product_mz(row: Any) -> float:
    if hasattr(row, "family_product_mz"):
        return row.family_product_mz
    return row.cluster_product_mz


def _family_observed_neutral_loss_da(row: Any) -> float:
    if hasattr(row, "family_observed_neutral_loss_da"):
        return row.family_observed_neutral_loss_da
    return row.cluster_observed_neutral_loss_da


def _event_cluster_ids(row: Any) -> tuple[str, ...]:
    if hasattr(row, "event_cluster_ids"):
        return tuple(row.event_cluster_ids)
    return (str(row.cluster_id), *tuple(row.folded_cluster_ids))


def _event_member_count(row: Any) -> int:
    if hasattr(row, "event_member_count"):
        return int(row.event_member_count)
    return len(row.members) + int(row.folded_member_count)


def _family_evidence(row: Any) -> str:
    if hasattr(row, "evidence"):
        return str(row.evidence)
    return str(row.fold_evidence)


def _optional_attr(row: Any, name: str) -> object:
    return getattr(row, name, "")


def _has_detected_owner_evidence(row: Any) -> bool:
    evidence = _family_evidence(row)
    return evidence == "single_sample_local_owner" or evidence.startswith(
        "owner_complete_link;"
    )
