"""Write shadow production projection rows for retained backfill cells."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.alignment.backfill_evidence_projection import (
    load_ms1_pattern_coherence_rows,
    project_backfill_evidence_to_cells,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.primary_matrix_area import (
    MS1_MORPHOLOGY_PRIMARY_MATRIX_AREA_SOURCE,
)
from xic_extractor.alignment.production_decisions import build_production_decisions
from xic_extractor.diagnostics.diagnostic_io import optional_float, read_tsv_required
from xic_extractor.diagnostics.shadow_production_projection import (
    RETAINED_GATE_REQUIRED_COLUMNS,
    ShadowProductionProjectionOutputs,
    build_shadow_production_projection_index,
    write_shadow_production_projection_outputs,
)
from xic_extractor.peak_detection.hypotheses import IntegrationResult

REVIEW_REQUIRED_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "detected_count",
)
CELL_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "height",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
)
GATE_REQUIRED_COLUMNS = RETAINED_GATE_REQUIRED_COLUMNS
OVERLAY_REQUIRED_COLUMNS = (
    "feature_family_id",
    "family_verdict",
    "png_path",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_shadow_production_projection(
            alignment_review_tsv=args.alignment_review_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            retained_gate_tsv=args.retained_gate_tsv,
            output_dir=args.output_dir,
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            alignment_matrix_identity_tsv=args.alignment_matrix_identity_tsv,
            overlay_batch_summary_tsvs=tuple(args.overlay_batch_summary_tsv or ()),
            ms1_pattern_coherence_tsvs=tuple(
                args.ms1_pattern_coherence_tsv or ()
            ),
            source_run_id=args.source_run_id or "",
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"shadow production projection cells TSV: {outputs.tsv}")
    print(f"shadow production projection summary JSON: {outputs.json}")
    return 0


def run_shadow_production_projection(
    *,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    retained_gate_tsv: Path,
    output_dir: Path,
    alignment_matrix_tsv: Path | None = None,
    alignment_matrix_identity_tsv: Path | None = None,
    overlay_batch_summary_tsvs: Sequence[Path] = (),
    ms1_pattern_coherence_tsvs: Sequence[Path] = (),
    source_run_id: str = "",
) -> ShadowProductionProjectionOutputs:
    if alignment_matrix_tsv is not None and not alignment_matrix_tsv.exists():
        raise FileNotFoundError(str(alignment_matrix_tsv))
    if (
        alignment_matrix_identity_tsv is not None
        and not alignment_matrix_identity_tsv.exists()
    ):
        raise FileNotFoundError(str(alignment_matrix_identity_tsv))
    review_rows = read_tsv_required(alignment_review_tsv, REVIEW_REQUIRED_COLUMNS)
    cell_rows = read_tsv_required(alignment_cells_tsv, CELL_REQUIRED_COLUMNS)
    projection_cell_rows: Sequence[Mapping[str, str]] = cell_rows
    gate_rows = read_tsv_required(retained_gate_tsv, GATE_REQUIRED_COLUMNS)
    ms1_pattern_rows: list[dict[str, str]] = []
    for path in ms1_pattern_coherence_tsvs:
        ms1_pattern_rows.extend(load_ms1_pattern_coherence_rows(path))
    if ms1_pattern_rows:
        projection_cell_rows = project_backfill_evidence_to_cells(
            cell_rows=cell_rows,
            ms1_pattern_coherence_rows=ms1_pattern_rows,
        )
    overlay_rows: list[dict[str, str]] = []
    for path in overlay_batch_summary_tsvs:
        overlay_rows.extend(read_tsv_required(path, OVERLAY_REQUIRED_COLUMNS))

    matrix = _alignment_matrix_from_tsv(review_rows, cell_rows)
    decisions = build_production_decisions(matrix, AlignmentConfig())
    index = build_shadow_production_projection_index(
        production_decisions=decisions,
        cell_rows=projection_cell_rows,
        retained_gate_rows=gate_rows,
        overlay_rows=overlay_rows,
        current_matrix_values=_current_matrix_values_by_family_sample(
            alignment_matrix_tsv=alignment_matrix_tsv,
            alignment_matrix_identity_tsv=alignment_matrix_identity_tsv,
        ),
        source_run_id=source_run_id,
        source_review_sha256=_sha256_file(alignment_review_tsv),
        source_cell_sha256=_sha256_file(alignment_cells_tsv),
        source_gate_sha256=_sha256_file(retained_gate_tsv),
        source_matrix_sha256=(
            _sha256_file(alignment_matrix_tsv)
            if alignment_matrix_tsv is not None and alignment_matrix_tsv.exists()
            else ""
        ),
        source_overlay_artifacts=tuple(
            str(path) for path in overlay_batch_summary_tsvs
        ),
        source_overlay_sha256s=tuple(
            _sha256_file(path) for path in overlay_batch_summary_tsvs
        ),
        source_ms1_pattern_coherence_artifacts=tuple(
            str(path) for path in ms1_pattern_coherence_tsvs
        ),
        source_ms1_pattern_coherence_sha256s=tuple(
            _sha256_file(path) for path in ms1_pattern_coherence_tsvs
        ),
    )
    return write_shadow_production_projection_outputs(output_dir, index)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-review-tsv", required=True, type=Path)
    parser.add_argument("--alignment-cells-tsv", required=True, type=Path)
    parser.add_argument("--retained-gate-tsv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--alignment-matrix-tsv", type=Path)
    parser.add_argument("--alignment-matrix-identity-tsv", type=Path)
    parser.add_argument("--overlay-batch-summary-tsv", action="append", type=Path)
    parser.add_argument("--ms1-pattern-coherence-tsv", action="append", type=Path)
    parser.add_argument("--source-run-id")
    return parser.parse_args(argv)


def _current_matrix_values_by_family_sample(
    *,
    alignment_matrix_tsv: Path | None,
    alignment_matrix_identity_tsv: Path | None,
) -> dict[tuple[str, str], str]:
    if alignment_matrix_tsv is None or alignment_matrix_identity_tsv is None:
        return {}
    matrix_header, matrix_rows = _read_tsv_with_header(alignment_matrix_tsv)
    identity_rows = read_tsv_required(
        alignment_matrix_identity_tsv,
        ("matrix_row_index", "peak_hypothesis_id"),
    )
    sample_columns = tuple(
        column for column in matrix_header if column not in {"Mz", "RT"}
    )
    values: dict[tuple[str, str], str] = {}
    for identity in identity_rows:
        row_index = _positive_int(identity.get("matrix_row_index"))
        if row_index is None or row_index > len(matrix_rows):
            continue
        matrix_row = matrix_rows[row_index - 1]
        row_keys = _identity_family_keys(identity)
        for row_key in row_keys:
            for sample in sample_columns:
                values[(row_key, sample)] = matrix_row.get(sample, "")
    return values


def _identity_family_keys(identity: Mapping[str, str]) -> tuple[str, ...]:
    keys = [identity.get("peak_hypothesis_id", "").strip()]
    keys.extend(
        part.strip()
        for part in identity.get("source_feature_family_ids", "").split(";")
        if part.strip()
    )
    return tuple(dict.fromkeys(key for key in keys if key))


def _read_tsv_with_header(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return tuple(reader.fieldnames or ()), list(reader)


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(str(value or "").strip())
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _alignment_matrix_from_tsv(
    review_rows: Sequence[Mapping[str, str]],
    cell_rows: Sequence[Mapping[str, str]],
) -> AlignmentMatrix:
    clusters = tuple(_cluster_from_review(row) for row in review_rows)
    cells = tuple(_cell_from_row(row) for row in cell_rows)
    sample_order = tuple(
        sorted(
            {
                row.get("sample_stem", "")
                for row in cell_rows
                if row.get("sample_stem")
            },
        ),
    )
    return AlignmentMatrix(clusters=clusters, cells=cells, sample_order=sample_order)


def _cluster_from_review(row: Mapping[str, str]) -> SimpleNamespace:
    evidence = row.get("family_evidence") or row.get("evidence") or ""
    return SimpleNamespace(
        feature_family_id=row.get("feature_family_id", ""),
        neutral_loss_tag=row.get("neutral_loss_tag", ""),
        family_center_mz=_float(row.get("family_center_mz")) or 0.0,
        family_center_rt=_float(row.get("family_center_rt")) or 0.0,
        family_product_mz=_float(row.get("family_product_mz")) or 0.0,
        family_observed_neutral_loss_da=(
            _float(row.get("family_observed_neutral_loss_da")) or 0.0
        ),
        has_anchor=_is_trueish(row.get("has_anchor")) or _float(
            row.get("detected_count"),
        )
        not in (None, 0.0),
        event_cluster_ids=tuple(
            part for part in row.get("event_cluster_ids", "").split(";") if part
        ),
        event_member_count=int(_float(row.get("event_member_count")) or 0),
        evidence=evidence,
        review_only=_is_review_only_row(row, evidence),
    )


def _cell_from_row(row: Mapping[str, str]) -> AlignedCell:
    start = _float(row.get("peak_start_rt"))
    end = _float(row.get("peak_end_rt"))
    apex = _float(row.get("apex_rt"))
    raw_area = _float(row.get("area"))
    if apex is None and start is not None and end is not None:
        apex = (start + end) / 2.0
    return AlignedCell(
        sample_stem=row.get("sample_stem", ""),
        cluster_id=row.get("feature_family_id", ""),
        status=row.get("status", ""),  # type: ignore[arg-type]
        area=raw_area,
        apex_rt=apex,
        height=_float(row.get("height")) or 1.0,
        peak_start_rt=start,
        peak_end_rt=end,
        rt_delta_sec=_float(row.get("rt_delta_sec")),
        trace_quality=row.get("trace_quality", ""),
        scan_support_score=_float(row.get("scan_support_score")),
        source_candidate_id=row.get("source_candidate_id") or None,
        source_raw_file=None,
        reason=row.get("reason", ""),
        selected_integration=_integration_from_cell_row(
            row,
            raw_area=raw_area,
            apex=apex,
            start=start,
            end=end,
        ),
        backfill_ms1_pattern_status=row.get("backfill_ms1_pattern_status", ""),
        backfill_ms1_pattern_evidence_level=row.get(
            "backfill_ms1_pattern_evidence_level",
            "",
        ),
        backfill_ms1_product_authority_status=row.get(
            "backfill_ms1_product_authority_status",
            "",
        ),
        backfill_ms1_product_authority_scope=row.get(
            "backfill_ms1_product_authority_scope",
            "",
        ),
        backfill_ms1_product_authority_source=row.get(
            "backfill_ms1_product_authority_source",
            "",
        ),
        backfill_ms1_product_authority_reason=row.get(
            "backfill_ms1_product_authority_reason",
            "",
        ),
        backfill_ms1_product_authority_evidence_sha256=row.get(
            "backfill_ms1_product_authority_evidence_sha256",
            "",
        ),
        backfill_qc_reference_status=row.get("backfill_qc_reference_status", ""),
        backfill_qc_reference_evidence_level=row.get(
            "backfill_qc_reference_evidence_level",
            "",
        ),
        backfill_matrix_rt_drift_status=row.get(
            "backfill_matrix_rt_drift_status",
            "",
        ),
        backfill_drift_evidence_level=row.get("backfill_drift_evidence_level", ""),
        backfill_drift_compatible_status=row.get(
            "backfill_drift_compatible_status",
            "",
        ),
        backfill_drift_corrected_delta_sec=_float(
            row.get("backfill_drift_corrected_delta_sec"),
        ),
        backfill_candidate_ms2_pattern_status=row.get(
            "backfill_candidate_ms2_pattern_status",
            "",
        ),
        backfill_candidate_ms2_evidence_level=row.get(
            "backfill_candidate_ms2_evidence_level",
            "",
        ),
        backfill_candidate_ms2_product_authority_status=row.get(
            "backfill_candidate_ms2_product_authority_status",
            "",
        ),
        backfill_candidate_ms2_product_authority_scope=row.get(
            "backfill_candidate_ms2_product_authority_scope",
            "",
        ),
        backfill_candidate_ms2_product_authority_source=row.get(
            "backfill_candidate_ms2_product_authority_source",
            "",
        ),
        backfill_candidate_ms2_product_authority_reason=row.get(
            "backfill_candidate_ms2_product_authority_reason",
            "",
        ),
        backfill_candidate_ms2_product_authority_evidence_sha256=row.get(
            "backfill_candidate_ms2_product_authority_evidence_sha256",
            "",
        ),
        backfill_evidence_reason=row.get("backfill_evidence_reason", ""),
        group_hypothesis_id=row.get("group_hypothesis_id", ""),
        public_family_id=row.get("public_family_id", ""),
        group_construction_role=row.get("group_construction_role", ""),
        group_delivery_role=row.get("group_delivery_role", ""),
        group_membership_source=row.get("group_membership_source", ""),
        gap_fill_state=row.get("gap_fill_state", ""),
        gap_fill_reason=row.get("gap_fill_reason", ""),
        peak_hypothesis_status=row.get("peak_hypothesis_status", ""),
        product_selection_blocker=row.get("product_selection_blocker", ""),
        rt_mode_status=row.get("rt_mode_status", ""),
        group_claim_state=row.get("group_claim_state", ""),
        consolidation_state=row.get("consolidation_state", ""),
    )


def _integration_from_cell_row(
    row: Mapping[str, str],
    *,
    raw_area: float | None,
    apex: float | None,
    start: float | None,
    end: float | None,
) -> IntegrationResult | None:
    primary_area = _float(row.get("primary_matrix_area")) or raw_area
    if (
        primary_area is None
        or raw_area is None
        or apex is None
        or start is None
        or end is None
    ):
        return None
    return IntegrationResult(
        rt_left_min=start,
        rt_apex_min=apex,
        rt_right_min=end,
        raw_apex_rt_min=apex,
        rt_width_min=max(end - start, 0.0),
        height_raw=_float(row.get("height")) or 1.0,
        height_smoothed=_float(row.get("height")) or 1.0,
        area_raw_counts_seconds=raw_area,
        area_ms1_morphology=primary_area,
        ms1_morphology_area_source=MS1_MORPHOLOGY_PRIMARY_MATRIX_AREA_SOURCE,
        boundary_sources=("alignment_cells_tsv",),
    )


def _is_review_only_row(row: Mapping[str, str], evidence: str) -> bool:
    row_flags = _split_tokens(row.get("row_flags", ""))
    evidence_tokens = _split_tokens(evidence)
    return (
        row.get("identity_reason", "") == "review_only"
        or "review_only" in row_flags
        or "review_only" in evidence_tokens
    )


def _split_tokens(value: object) -> set[str]:
    return {part.strip() for part in str(value or "").split(";") if part.strip()}


def _is_trueish(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _float(value: object) -> float | None:
    return optional_float(value)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


if __name__ == "__main__":
    raise SystemExit(main())
