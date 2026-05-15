"""Read-only blast-radius report for proposed matrix identity decisions."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.matrix_identity import build_matrix_identity_decisions

REVIEW_REQUIRED = {"feature_family_id", "include_in_primary_matrix"}
REVIEW_EVIDENCE_COLUMNS = {"family_evidence", "evidence"}
CELL_REQUIRED = {
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
    "reason",
}
MATRIX_REQUIRED = {"feature_family_id"}

OUTPUT_COLUMNS = (
    "feature_family_id",
    "current_include_in_primary_matrix",
    "proposed_include_in_primary_matrix",
    "identity_decision",
    "primary_evidence",
    "identity_reason",
    "quantifiable_detected_count",
    "quantifiable_rescue_count",
    "duplicate_assigned_count",
    "ambiguous_ms1_owner_count",
    "row_flags",
    "would_change_to_audit",
    "would_change_to_production",
    "evidence_status",
    "missing_required_columns",
    "targeted_benchmark_class",
    "targeted_target_name",
    "targeted_role",
    "active_dna_istd_candidate",
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze matrix identity blast radius for alignment outputs.",
    )
    parser.add_argument("--alignment-run", type=Path, required=True)
    parser.add_argument("--benchmark-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-incomplete-summary", action="store_true")
    parser.add_argument("--require-targeted-benchmark", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run_blast_radius(
            alignment_run=args.alignment_run,
            output_dir=args.output_dir,
            benchmark_dir=args.benchmark_dir,
            allow_incomplete_summary=args.allow_incomplete_summary,
            require_targeted_benchmark=args.require_targeted_benchmark,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def run_blast_radius(
    *,
    alignment_run: Path,
    output_dir: Path,
    benchmark_dir: Path | None = None,
    allow_incomplete_summary: bool = False,
    require_targeted_benchmark: bool = False,
) -> int:
    review_rows, review_columns = _read_tsv_with_columns(
        alignment_run / "alignment_review.tsv",
    )
    cell_rows, cell_columns = _read_tsv_with_columns(
        alignment_run / "alignment_cells.tsv",
    )
    matrix_rows, matrix_columns = _read_tsv_with_columns(
        alignment_run / "alignment_matrix.tsv",
    )
    del matrix_rows
    output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_by_family = _load_benchmark_by_family(
        benchmark_dir,
        require=require_targeted_benchmark,
    )
    missing = _missing_columns(review_columns, cell_columns, matrix_columns)
    if missing:
        rows = _incomplete_rows(review_rows, missing, benchmark_by_family)
        _write_outputs(output_dir, rows, evidence_status="evidence_incomplete")
        return 0 if allow_incomplete_summary else 2

    matrix = _alignment_matrix_from_tsv(review_rows, cell_rows)
    decisions = build_matrix_identity_decisions(matrix, AlignmentConfig())
    current_by_family = {
        row.get("feature_family_id", ""): row for row in review_rows
    }
    rows = []
    for family_id in sorted(decisions.rows):
        row_decision = decisions.row(family_id)
        current_row = current_by_family.get(family_id, {})
        current_include = _is_trueish(current_row.get("include_in_primary_matrix"))
        proposed_include = row_decision.include_in_primary_matrix
        benchmark = benchmark_by_family.get(family_id, {})
        rows.append(
            {
                "feature_family_id": family_id,
                "current_include_in_primary_matrix": current_include,
                "proposed_include_in_primary_matrix": proposed_include,
                "identity_decision": row_decision.identity_decision,
                "primary_evidence": row_decision.primary_evidence,
                "identity_reason": row_decision.identity_reason,
                "quantifiable_detected_count": (
                    row_decision.quantifiable_detected_count
                ),
                "quantifiable_rescue_count": (
                    row_decision.quantifiable_rescue_count
                ),
                "duplicate_assigned_count": row_decision.duplicate_assigned_count,
                "ambiguous_ms1_owner_count": (
                    row_decision.ambiguous_ms1_owner_count
                ),
                "row_flags": ";".join(row_decision.row_flags),
                "would_change_to_audit": current_include and not proposed_include,
                "would_change_to_production": (
                    not current_include and proposed_include
                ),
                "evidence_status": "complete",
                "missing_required_columns": "",
                "targeted_benchmark_class": benchmark.get("benchmark_class", ""),
                "targeted_target_name": benchmark.get("target_name", ""),
                "targeted_role": benchmark.get("role", ""),
                "active_dna_istd_candidate": benchmark.get(
                    "active_dna_istd_candidate",
                    "",
                ),
            },
        )
    _write_outputs(output_dir, rows, evidence_status="complete")
    return 0


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
        has_anchor=_is_trueish(row.get("has_anchor")),
        event_cluster_ids=tuple(
            part for part in row.get("event_cluster_ids", "").split(";") if part
        ),
        event_member_count=int(_float(row.get("event_member_count")) or 0),
        evidence=evidence,
        review_only=False,
    )


def _cell_from_row(row: Mapping[str, str]) -> AlignedCell:
    start = _float(row.get("peak_start_rt"))
    end = _float(row.get("peak_end_rt"))
    apex = _float(row.get("apex_rt"))
    if apex is None and start is not None and end is not None:
        apex = (start + end) / 2.0
    return AlignedCell(
        sample_stem=row.get("sample_stem", ""),
        cluster_id=row.get("feature_family_id", ""),
        status=row.get("status", ""),  # type: ignore[arg-type]
        area=_float(row.get("area")),
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
    )


def _missing_columns(
    review_columns: set[str],
    cell_columns: set[str],
    matrix_columns: set[str],
) -> list[str]:
    missing = [
        f"alignment_review.tsv:{column}"
        for column in sorted(REVIEW_REQUIRED - review_columns)
    ]
    if not (REVIEW_EVIDENCE_COLUMNS & review_columns):
        missing.append("alignment_review.tsv:family_evidence or evidence")
    missing.extend(
        f"alignment_cells.tsv:{column}"
        for column in sorted(CELL_REQUIRED - cell_columns)
    )
    missing.extend(
        f"alignment_matrix.tsv:{column}"
        for column in sorted(MATRIX_REQUIRED - matrix_columns)
    )
    return missing


def _incomplete_rows(
    review_rows: Sequence[Mapping[str, str]],
    missing: Sequence[str],
    benchmark_by_family: Mapping[str, Mapping[str, str]],
) -> list[dict[str, object]]:
    if not review_rows:
        review_rows = ({"feature_family_id": ""},)
    rows = []
    for review_row in review_rows:
        family_id = review_row.get("feature_family_id", "")
        benchmark = benchmark_by_family.get(family_id, {})
        rows.append(
            {
                "feature_family_id": family_id,
                "current_include_in_primary_matrix": review_row.get(
                    "include_in_primary_matrix",
                    "",
                ),
                "proposed_include_in_primary_matrix": "",
                "identity_decision": "",
                "primary_evidence": "",
                "identity_reason": "",
                "quantifiable_detected_count": "",
                "quantifiable_rescue_count": "",
                "duplicate_assigned_count": "",
                "ambiguous_ms1_owner_count": "",
                "row_flags": "",
                "would_change_to_audit": "",
                "would_change_to_production": "",
                "evidence_status": "evidence_incomplete",
                "missing_required_columns": ";".join(missing),
                "targeted_benchmark_class": benchmark.get("benchmark_class", ""),
                "targeted_target_name": benchmark.get("target_name", ""),
                "targeted_role": benchmark.get("role", ""),
                "active_dna_istd_candidate": benchmark.get(
                    "active_dna_istd_candidate",
                    "",
                ),
            },
        )
    return rows


def _load_benchmark_by_family(
    benchmark_dir: Path | None,
    *,
    require: bool,
) -> dict[str, dict[str, str]]:
    if benchmark_dir is None:
        if require:
            raise ValueError("--benchmark-dir is required")
        return {}
    required_files = [
        benchmark_dir / "targeted_istd_benchmark_matches.tsv",
        benchmark_dir / "targeted_istd_benchmark_summary.tsv",
        benchmark_dir / "targeted_istd_benchmark.json",
    ]
    missing = [path for path in required_files if not path.exists()]
    if missing and require:
        raise FileNotFoundError(str(missing[0]))
    if missing:
        return {}
    rows, _columns = _read_tsv_with_columns(required_files[0])
    by_family: dict[str, dict[str, str]] = {}
    for row in rows:
        family_id = row.get("feature_family_id", "")
        if family_id:
            by_family[family_id] = dict(row)
    return by_family


def _write_outputs(
    output_dir: Path,
    rows: Sequence[Mapping[str, object]],
    *,
    evidence_status: str,
) -> None:
    _write_tsv(output_dir / "matrix_identity_blast_radius.tsv", OUTPUT_COLUMNS, rows)
    payload = {
        "evidence_status": evidence_status,
        "row_count": len(rows),
        "would_change_to_audit_count": sum(
            1 for row in rows if _is_trueish(row.get("would_change_to_audit"))
        ),
        "would_change_to_production_count": sum(
            1 for row in rows if _is_trueish(row.get("would_change_to_production"))
        ),
        "rows": list(rows),
    }
    (output_dir / "matrix_identity_blast_radius.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _read_tsv_with_columns(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [dict(row) for row in reader], set(reader.fieldnames or [])


def _write_tsv(
    path: Path,
    columns: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {column: _tsv_value(row.get(column, "")) for column in columns},
            )


def _tsv_value(value: object) -> object:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return value


def _float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_trueish(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


if __name__ == "__main__":
    raise SystemExit(main())
