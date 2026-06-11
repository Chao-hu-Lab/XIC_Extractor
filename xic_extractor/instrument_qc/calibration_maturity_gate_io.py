from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from xic_extractor.instrument_qc.calibration_maturity_gate import (
    CalibrationMaturityDecision,
    build_calibration_maturity_decisions,
)
from xic_extractor.instrument_qc.calibration_product_loaders import read_tsv_rows
from xic_extractor.tabular_io import write_tsv

MATURITY_GATE_COLUMNS = [
    "maturity_level",
    "target_state",
    "decision",
    "go_no_go",
    "blocker_count",
    "blockers",
    "evidence_summary",
    "review_reason",
]

MATRIX_RT_PREVIEW_REQUIRED_COLUMNS = {
    "coverage_status",
    "correction_status",
    "correction_block_reason",
}


def build_calibration_maturity_gate_from_files(
    *,
    rt_model_summary_json: Path,
    matrix_rt_preview_summary_json: Path,
    matrix_rt_preview_tsv: Path,
    biological_istd_transfer_json: Path,
    response_model_summary_json: Path | None = None,
    biological_response_transfer_json: Path | None = None,
    downstream_compatibility_json: Path | None = None,
) -> tuple[CalibrationMaturityDecision, ...]:
    return build_calibration_maturity_decisions(
        rt_model_summary=_read_required_json(rt_model_summary_json),
        matrix_rt_preview_summary=_read_required_json(matrix_rt_preview_summary_json),
        matrix_rt_preview_row_summary=_matrix_rt_preview_row_summary(
            matrix_rt_preview_tsv
        ),
        biological_istd_transfer_summary=_read_required_json(
            biological_istd_transfer_json
        ),
        response_model_summary=_read_optional_json(response_model_summary_json),
        biological_response_transfer_summary=_read_optional_json(
            biological_response_transfer_json
        ),
        downstream_compatibility_summary=_read_optional_json(
            downstream_compatibility_json
        ),
    )


def write_calibration_maturity_gate_outputs(
    *,
    output_dir: Path,
    decisions: tuple[CalibrationMaturityDecision, ...],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_tsv = output_dir / "instrument_qc_calibration_maturity_gate.tsv"
    summary_json = output_dir / "instrument_qc_calibration_maturity_gate.json"
    review_md = output_dir / "instrument_qc_calibration_maturity_gate.md"
    write_calibration_maturity_gate_tsv(rows_tsv, decisions)
    summary_json.write_text(
        json.dumps(_summary_payload(decisions, rows_tsv, review_md), indent=2)
        + "\n",
        encoding="utf-8",
    )
    review_md.write_text(_render_markdown(decisions), encoding="utf-8")
    return {
        "rows_tsv": rows_tsv,
        "summary_json": summary_json,
        "review_md": review_md,
    }


def write_calibration_maturity_gate_tsv(
    path: Path,
    decisions: tuple[CalibrationMaturityDecision, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        path,
        tuple(_row_to_dict(decision) for decision in decisions),
        MATURITY_GATE_COLUMNS,
    )


def _summary_payload(
    decisions: tuple[CalibrationMaturityDecision, ...],
    rows_tsv: Path,
    review_md: Path,
) -> dict[str, Any]:
    return {
        "total_rows": len(decisions),
        "counts_by_go_no_go": dict(
            sorted(Counter(row.go_no_go for row in decisions).items())
        ),
        "counts_by_decision": dict(
            sorted(Counter(row.decision for row in decisions).items())
        ),
        "rows_tsv": rows_tsv.name,
        "review_md": review_md.name,
    }


def _render_markdown(decisions: tuple[CalibrationMaturityDecision, ...]) -> str:
    lines = [
        "# Instrument QC Calibration Maturity Gate",
        "",
        "This report converts Level 2 through Level 5 calibration goals into",
        "explicit go/no-go decisions. It is audit-only and does not mutate any",
        "matrix, reliability, scoring, resolver, or downstream normalization",
        "contract.",
        "",
        "| Level | Target State | Decision | Blockers | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in decisions:
        blockers = "; ".join(row.blockers) if row.blockers else "none"
        lines.append(
            f"| `{row.maturity_level}` | `{row.target_state}` | "
            f"`{row.decision}` | {blockers} | {row.review_reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def _row_to_dict(decision: CalibrationMaturityDecision) -> dict[str, str]:
    raw = asdict(decision)
    raw["blockers"] = ";".join(decision.blockers)
    return {column: str(raw.get(column, "")) for column in MATURITY_GATE_COLUMNS}


def _read_required_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"required JSON not found: {path}")
    return _read_json(path)


def _matrix_rt_preview_row_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"required matrix RT preview TSV not found: {path}")
    rows = read_tsv_rows(path, required_columns=MATRIX_RT_PREVIEW_REQUIRED_COLUMNS)
    coverage_counts = Counter(
        (row.get("coverage_status") or "").strip() for row in rows
    )
    correction_counts = Counter(
        (row.get("correction_status") or "").strip() for row in rows
    )
    block_reason_counts = Counter(
        (row.get("correction_block_reason") or "").strip()
        for row in rows
        if (row.get("correction_status") or "").strip().startswith("blocked_")
    )
    return {
        "total_rows": len(rows),
        "counts_by_coverage_status": dict(sorted(coverage_counts.items())),
        "counts_by_correction_status": dict(sorted(correction_counts.items())),
        "counts_by_correction_block_reason": dict(
            sorted(block_reason_counts.items())
        ),
    }


def _read_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        raise ValueError(f"optional JSON was provided but not found: {path}")
    return _read_json(path)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload
