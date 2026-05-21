from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from xic_extractor.instrument_qc.calibration_product_loaders import read_tsv_rows
from xic_extractor.instrument_qc.rt_ms1_backfill_cross_evidence import (
    FinalMatrixFamilyRow,
    IstdRtEnvelopeTargetRow,
    RtMs1CrossEvidenceResult,
    RtShadowCellRow,
    SeedAwareFamilyRow,
    build_rt_ms1_backfill_cross_evidence,
)

RT_SHADOW_REQUIRED_COLUMNS = {
    "feature_id",
    "source_cell_key",
    "sample_stem",
    "feature_mz",
    "raw_feature_rt_min",
    "row_classification",
    "supporting_biological_istd_label",
    "review_reason",
}

SEED_AWARE_REQUIRED_COLUMNS = {
    "feature_family_id",
    "family_center_mz",
    "family_center_rt",
    "detected_count",
    "accepted_rescue_count",
    "accepted_cell_count",
    "review_classification",
    "recommended_next_action",
    "review_reason",
    "png_paths",
}

ALIGNMENT_REVIEW_REQUIRED_COLUMNS = {
    "feature_family_id",
    "include_in_primary_matrix",
    "identity_decision",
    "accepted_cell_count",
    "detected_count",
    "accepted_rescue_count",
    "review_rescue_count",
}

ISTD_RT_ENVELOPE_REQUIRED_COLUMNS = {
    "target_label",
    "anchor_status",
    "rt_range_min",
    "normal_abs_residual_min",
    "warning_abs_residual_min",
    "high_raw_drift",
}

FAMILY_COLUMNS = [
    "feature_family_id",
    "family_center_mz",
    "family_center_rt",
    "detected_count",
    "accepted_rescue_count",
    "accepted_cell_count",
    "ms1_review_classification",
    "rt_supported_cell_count",
    "rt_uncertain_cell_count",
    "rt_conflict_cell_count",
    "rt_clean_only_cell_count",
    "rt_total_cell_count",
    "rt_supported_fraction",
    "rt_support_level",
    "supporting_istd_labels",
    "supporting_istd_normal_envelope_min",
    "supporting_istd_warning_envelope_min",
    "supporting_istd_high_raw_drift",
    "rt_drift_context",
    "combined_classification",
    "evidence_grade",
    "final_matrix_status",
    "final_matrix_identity_decision",
    "final_matrix_detected_count",
    "final_matrix_accepted_rescue_count",
    "final_matrix_accepted_cell_count",
    "blocking_evidence",
    "missing_evidence",
    "recommended_next_action",
    "review_reason",
    "overlay_png_paths",
]

SUMMARY_COLUMNS = ["metric", "value"]
FINAL_MATRIX_GRADE_COLUMNS = [
    "evidence_grade",
    "final_matrix_status",
    "family_count",
    "detected_count",
    "accepted_rescue_count",
    "accepted_cell_count",
]


def build_rt_ms1_cross_evidence_from_files(
    *,
    rt_shadow_rows_tsv: Path,
    seed_aware_families_tsv: Path,
    alignment_review_tsv: Path | None = None,
    biological_istd_rt_envelope_targets_tsv: Path | None = None,
) -> RtMs1CrossEvidenceResult:
    return build_rt_ms1_backfill_cross_evidence(
        rt_rows=_load_rt_shadow_rows(rt_shadow_rows_tsv),
        seed_families=_load_seed_aware_families(seed_aware_families_tsv),
        final_matrix_rows=_load_alignment_review_rows(alignment_review_tsv),
        istd_rt_envelopes=_load_istd_rt_envelopes(
            biological_istd_rt_envelope_targets_tsv
        ),
    )


def write_rt_ms1_cross_evidence_outputs(
    *,
    output_dir: Path,
    result: RtMs1CrossEvidenceResult,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    families_tsv = output_dir / "rt_ms1_backfill_cross_evidence_families.tsv"
    summary_tsv = output_dir / "rt_ms1_backfill_cross_evidence_summary.tsv"
    final_matrix_grade_tsv = (
        output_dir / "rt_ms1_backfill_final_matrix_grade_summary.tsv"
    )
    summary_json = output_dir / "rt_ms1_backfill_cross_evidence.json"
    review_md = output_dir / "rt_ms1_backfill_cross_evidence.md"
    _write_tsv(
        families_tsv,
        [asdict(row) for row in result.rows],
        FAMILY_COLUMNS,
    )
    _write_tsv(summary_tsv, _summary_rows(result), SUMMARY_COLUMNS)
    _write_tsv(
        final_matrix_grade_tsv,
        [asdict(row) for row in result.matrix_status_by_grade],
        FINAL_MATRIX_GRADE_COLUMNS,
    )
    summary_json.write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    review_md.write_text(
        _render_markdown(result, families_tsv=families_tsv, summary_tsv=summary_tsv),
        encoding="utf-8",
    )
    return {
        "families_tsv": families_tsv,
        "summary_tsv": summary_tsv,
        "final_matrix_grade_tsv": final_matrix_grade_tsv,
        "summary_json": summary_json,
        "review_md": review_md,
    }


def _load_rt_shadow_rows(path: Path) -> tuple[RtShadowCellRow, ...]:
    rows = read_tsv_rows(path, required_columns=RT_SHADOW_REQUIRED_COLUMNS)
    return tuple(
        RtShadowCellRow(
            feature_id=(row.get("feature_id") or "").strip(),
            source_cell_key=(row.get("source_cell_key") or "").strip(),
            sample_stem=(row.get("sample_stem") or "").strip(),
            feature_mz=(row.get("feature_mz") or "").strip(),
            raw_feature_rt_min=(row.get("raw_feature_rt_min") or "").strip(),
            row_classification=(row.get("row_classification") or "").strip(),
            supporting_biological_istd_label=(
                row.get("supporting_biological_istd_label") or ""
            ).strip(),
            review_reason=(row.get("review_reason") or "").strip(),
        )
        for row in rows
    )


def _load_seed_aware_families(path: Path) -> tuple[SeedAwareFamilyRow, ...]:
    rows = read_tsv_rows(path, required_columns=SEED_AWARE_REQUIRED_COLUMNS)
    return tuple(
        SeedAwareFamilyRow(
            feature_family_id=(row.get("feature_family_id") or "").strip(),
            family_center_mz=(row.get("family_center_mz") or "").strip(),
            family_center_rt=(row.get("family_center_rt") or "").strip(),
            detected_count=_parse_int(row, "detected_count", path=path),
            accepted_rescue_count=_parse_int(
                row,
                "accepted_rescue_count",
                path=path,
            ),
            accepted_cell_count=_parse_int(row, "accepted_cell_count", path=path),
            review_classification=(
                row.get("review_classification") or ""
            ).strip(),
            recommended_next_action=(
                row.get("recommended_next_action") or ""
            ).strip(),
            review_reason=(row.get("review_reason") or "").strip(),
            png_paths=(row.get("png_paths") or "").strip(),
        )
        for row in rows
    )


def _load_alignment_review_rows(
    path: Path | None,
) -> tuple[FinalMatrixFamilyRow, ...]:
    if path is None:
        return ()
    rows = read_tsv_rows(path, required_columns=ALIGNMENT_REVIEW_REQUIRED_COLUMNS)
    return tuple(
        FinalMatrixFamilyRow(
            feature_family_id=(row.get("feature_family_id") or "").strip(),
            include_in_primary_matrix=_parse_bool(
                row,
                "include_in_primary_matrix",
                path=path,
            ),
            identity_decision=(row.get("identity_decision") or "").strip(),
            accepted_cell_count=_parse_int(row, "accepted_cell_count", path=path),
            detected_count=_parse_int(row, "detected_count", path=path),
            accepted_rescue_count=_parse_int(
                row,
                "accepted_rescue_count",
                path=path,
            ),
            review_rescue_count=_parse_int(row, "review_rescue_count", path=path),
        )
        for row in rows
    )


def _load_istd_rt_envelopes(
    path: Path | None,
) -> tuple[IstdRtEnvelopeTargetRow, ...]:
    if path is None:
        return ()
    rows = read_tsv_rows(path, required_columns=ISTD_RT_ENVELOPE_REQUIRED_COLUMNS)
    return tuple(
        IstdRtEnvelopeTargetRow(
            target_label=(row.get("target_label") or "").strip(),
            anchor_status=(row.get("anchor_status") or "").strip(),
            rt_range_min=_parse_optional_float(row, "rt_range_min", path=path),
            normal_abs_residual_min=_parse_optional_float(
                row,
                "normal_abs_residual_min",
                path=path,
            ),
            warning_abs_residual_min=_parse_optional_float(
                row,
                "warning_abs_residual_min",
                path=path,
            ),
            high_raw_drift=_parse_bool(row, "high_raw_drift", path=path),
        )
        for row in rows
    )


def _summary_rows(result: RtMs1CrossEvidenceResult) -> list[dict[str, str]]:
    rows = [
        {"metric": "family_count", "value": str(result.total_families)},
        {"metric": "rt_family_count", "value": str(result.rt_family_count)},
        {"metric": "matched_family_count", "value": str(result.matched_family_count)},
    ]
    rows.extend(
        {"metric": f"classification:{label}", "value": str(count)}
        for label, count in result.counts_by_classification.items()
    )
    rows.extend(
        {"metric": f"evidence_grade:{label}", "value": str(count)}
        for label, count in result.counts_by_evidence_grade.items()
    )
    rows.extend(
        {"metric": f"final_matrix_status:{label}", "value": str(count)}
        for label, count in result.counts_by_final_matrix_status.items()
    )
    return rows


def _summary_payload(result: RtMs1CrossEvidenceResult) -> dict[str, Any]:
    return {
        "total_families": result.total_families,
        "rt_family_count": result.rt_family_count,
        "matched_family_count": result.matched_family_count,
        "counts_by_classification": result.counts_by_classification,
        "counts_by_evidence_grade": result.counts_by_evidence_grade,
        "counts_by_final_matrix_status": result.counts_by_final_matrix_status,
        "matrix_status_by_grade": [
            asdict(row) for row in result.matrix_status_by_grade
        ],
    }


def _render_markdown(
    result: RtMs1CrossEvidenceResult,
    *,
    families_tsv: Path,
    summary_tsv: Path,
) -> str:
    lines = [
        "# RT x MS1 Backfill Cross Evidence",
        "",
        "This diagnostic is audit-only. It does not mutate matrix values,",
        "backfill behavior, scoring, resolver behavior, targeted reliability,",
        "or downstream normalization.",
        "",
        f"- families: `{families_tsv.name}`",
        f"- summary: `{summary_tsv.name}`",
        f"- seed-aware families evaluated: `{result.total_families}`",
        f"- RT families available: `{result.rt_family_count}`",
        f"- families with both inputs: `{result.matched_family_count}`",
        "- final-matrix grade summary: "
        "`rt_ms1_backfill_final_matrix_grade_summary.tsv`",
        "",
        "## Classification Counts",
        "",
    ]
    if result.counts_by_classification:
        for label, count in result.counts_by_classification.items():
            lines.append(f"- `{label}`: {count}")
    else:
        lines.append("- no families evaluated")
    lines.extend(
        [
            "",
            "## Evidence Grade Counts",
            "",
        ]
    )
    if result.counts_by_evidence_grade:
        for label, count in result.counts_by_evidence_grade.items():
            lines.append(f"- `{label}`: {count}")
    else:
        lines.append("- no families evaluated")
    lines.extend(
        [
            "",
            "## Final Matrix Status x Evidence Grade",
            "",
            "| grade | final matrix status | families | detected | "
            "accepted rescue | accepted cells |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for grade_row in result.matrix_status_by_grade:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{grade_row.evidence_grade}`",
                    f"`{grade_row.final_matrix_status}`",
                    str(grade_row.family_count),
                    str(grade_row.detected_count),
                    str(grade_row.accepted_rescue_count),
                    str(grade_row.accepted_cell_count),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Top Families",
            "",
            "| grade | class | family | m/z | RT | rescued | RT supported cells | "
            "RT support level | matrix | blockers | missing | reason |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | "
            "--- | --- |",
        ]
    )
    for row in result.rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.evidence_grade}`",
                    f"`{row.combined_classification}`",
                    row.feature_family_id,
                    row.family_center_mz,
                    row.family_center_rt,
                    str(row.accepted_rescue_count),
                    str(row.rt_supported_cell_count),
                    row.rt_support_level,
                    row.final_matrix_status,
                    row.blocking_evidence,
                    row.missing_evidence,
                    row.review_reason,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `rt_ms1_supported_review_candidate`: both seed-aware MS1 shape and",
            "  dominant local biological-ISTD RT support agree.",
            "- `rt_supported_ms1_interference_review`: dominant RT support exists,",
            "  but neighboring MS1 interference still blocks production escalation.",
            "- `rt_supported_ms1_interference_drift_explainable_review`: RT",
            "  support is dominant, and the supporting ISTD has biological RT",
            "  residual envelope context. Treat the interference label as review",
            "  context, not as a one-strike blocker.",
            "- Dominant RT support requires at least three supported cells, at",
            "  least 10% supported cells, and zero RT conflict cells.",
            "- Any RT conflict caps the grade at conflict/not-supported review.",
            "- RT evidence alone must not rescue a family whose MS1 context is",
            "  conflicted.",
            "- `B_ms1_shape_supported_rt_unconfirmed` means MS1 shape evidence is",
            "  strong, while RT evidence is absent or uncertain rather than negative.",
            "- If families with both inputs is low, treat the run as an artifact",
            "  scope mismatch and regenerate matching RT/seed-aware diagnostics.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_tsv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    fieldnames: list[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {field: _format_value(row.get(field)) for field in fieldnames}
            )


def _parse_int(row: Mapping[str, str], column: str, *, path: Path) -> int:
    value = (row.get(column) or "").strip()
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError as exc:
        raise ValueError(
            f"{path.name} column {column} has invalid integer value: {value!r}"
        ) from exc


def _parse_optional_float(
    row: Mapping[str, str],
    column: str,
    *,
    path: Path,
) -> float | None:
    value = (row.get(column) or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{path.name} column {column} has invalid numeric value: {value!r}"
        ) from exc


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _parse_bool(row: Mapping[str, str], column: str, *, path: Path) -> bool:
    value = (row.get(column) or "").strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no", ""}:
        return False
    raise ValueError(
        f"{path.name} column {column} has invalid boolean value: {value!r}"
    )
