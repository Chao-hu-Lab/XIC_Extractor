"""Cross-report consistency diagnostic for targeted evidence surfaces."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.cross_report_evidence_consistency_analysis import (
    _candidate_consistency,
    _classify_consistency,
    _consistency_row,
    _consistency_rows,
    _has_review_positive_blocker,
    _summary,
)
from tools.diagnostics.cross_report_evidence_consistency_io import (
    _bool_value,
    _optional_float,
    _read_candidate_rows,
    _read_reliability_rows,
    _read_required_tsv,
    _read_target_mz,
    _split_labels,
    _text,
)
from tools.diagnostics.cross_report_evidence_consistency_models import (
    _CANDIDATE_COLUMNS,
    _RELIABILITY_COLUMNS,
    _ROW_COLUMNS,
    _SUMMARY_COLUMNS,
    CandidateRow,
    ConsistencyResult,
    ConsistencyRow,
    ConsistencySummary,
    CrossReportConsistencyOutputs,
    ReliabilityRow,
)
from tools.diagnostics.cross_report_evidence_consistency_writers import (
    _format_value,
    _markdown,
    _row_dicts,
    _write_outputs,
    _write_tsv,
)

__all__ = [
    "CandidateRow",
    "ConsistencyResult",
    "ConsistencyRow",
    "ConsistencySummary",
    "CrossReportConsistencyOutputs",
    "ReliabilityRow",
    "_CANDIDATE_COLUMNS",
    "_RELIABILITY_COLUMNS",
    "_ROW_COLUMNS",
    "_SUMMARY_COLUMNS",
    "_bool_value",
    "_candidate_consistency",
    "_classify_consistency",
    "_consistency_row",
    "_consistency_rows",
    "_format_value",
    "_has_review_positive_blocker",
    "_markdown",
    "_optional_float",
    "_parse_args",
    "_read_candidate_rows",
    "_read_reliability_rows",
    "_read_required_tsv",
    "_read_target_mz",
    "_row_dicts",
    "_split_labels",
    "_summary",
    "_text",
    "_write_outputs",
    "_write_tsv",
    "main",
    "run_cross_report_evidence_consistency",
]


def run_cross_report_evidence_consistency(
    *,
    targeted_reliability_rows_tsv: Path,
    peak_candidates_tsv: Path,
    output_dir: Path,
    targeted_workbook: Path | None = None,
) -> tuple[CrossReportConsistencyOutputs, ConsistencyResult]:
    reliability_rows = _read_reliability_rows(targeted_reliability_rows_tsv)
    candidate_rows = _read_candidate_rows(peak_candidates_tsv)
    target_mz = _read_target_mz(targeted_workbook) if targeted_workbook else {}
    rows = _consistency_rows(reliability_rows, candidate_rows, target_mz=target_mz)
    result = ConsistencyResult(summary=_summary(rows), rows=rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = CrossReportConsistencyOutputs(
        summary_tsv=output_dir / "cross_report_evidence_consistency_summary.tsv",
        rows_tsv=output_dir / "cross_report_evidence_consistency_rows.tsv",
        json_path=output_dir / "cross_report_evidence_consistency.json",
        markdown_path=output_dir / "cross_report_evidence_consistency.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, result = run_cross_report_evidence_consistency(
            targeted_reliability_rows_tsv=args.targeted_reliability_rows_tsv,
            peak_candidates_tsv=args.peak_candidates_tsv,
            output_dir=args.output_dir,
            targeted_workbook=args.targeted_workbook,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Consistency JSON: {outputs.json_path}")
    print(f"Consistency report: {outputs.markdown_path}")
    return 1 if result.summary.mismatch_count else 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare targeted reliability and peak candidate evidence.",
    )
    parser.add_argument("--targeted-reliability-rows-tsv", type=Path, required=True)
    parser.add_argument("--peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--targeted-workbook",
        type=Path,
        help="Optional targeted workbook used to include target m/z in review rows.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
