"""Root-cause audit for targeted NL dropout review-positive rows."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.targeted_nl_dropout_root_cause_io import (
    _bool_value,
    _optional_float,
    _optional_int,
    _read_candidate_rows,
    _read_reliability_rows,
    _read_required_tsv,
    _read_target_mz,
    _split_labels,
    _text,
)
from tools.diagnostics.targeted_nl_dropout_root_cause_logic import (
    _blocking_quality_flags,
    _classify_root_cause,
    _format_counter,
    _has_soft_trace_context,
    _root_cause_rows,
    _selected_candidates_by_key,
    _summary,
)
from tools.diagnostics.targeted_nl_dropout_root_cause_models import (
    _BLOCKING_TRACE_QUALITY_FLAGS,
    _CANDIDATE_COLUMNS,
    _HARD_CONFLICT_LABELS,
    _OPTIONAL_CANDIDATE_COLUMNS,
    _RELIABILITY_COLUMNS,
    _ROW_COLUMNS,
    _SOFT_TRACE_QUALITY_FLAGS,
    _SUMMARY_COLUMNS,
    CandidateRow,
    ReliabilityRow,
    RootCauseRow,
    RootCauseSummary,
    TargetedNLDropoutRootCauseOutputs,
    TargetedNLDropoutRootCauseResult,
)
from tools.diagnostics.targeted_nl_dropout_root_cause_writers import (
    _format_value,
    _markdown,
    _row_dicts,
    _write_outputs,
    _write_tsv,
)

__all__ = [
    "CandidateRow",
    "ReliabilityRow",
    "RootCauseRow",
    "RootCauseSummary",
    "TargetedNLDropoutRootCauseOutputs",
    "TargetedNLDropoutRootCauseResult",
    "_BLOCKING_TRACE_QUALITY_FLAGS",
    "_CANDIDATE_COLUMNS",
    "_HARD_CONFLICT_LABELS",
    "_OPTIONAL_CANDIDATE_COLUMNS",
    "_RELIABILITY_COLUMNS",
    "_ROW_COLUMNS",
    "_SOFT_TRACE_QUALITY_FLAGS",
    "_SUMMARY_COLUMNS",
    "_blocking_quality_flags",
    "_bool_value",
    "_classify_root_cause",
    "_format_counter",
    "_format_value",
    "_has_soft_trace_context",
    "_markdown",
    "_optional_float",
    "_optional_int",
    "_parse_args",
    "_read_candidate_rows",
    "_read_reliability_rows",
    "_read_required_tsv",
    "_read_target_mz",
    "_root_cause_rows",
    "_row_dicts",
    "_selected_candidates_by_key",
    "_split_labels",
    "_summary",
    "_text",
    "_write_outputs",
    "_write_tsv",
    "main",
    "run_targeted_nl_dropout_root_cause_audit",
]


def run_targeted_nl_dropout_root_cause_audit(
    *,
    targeted_reliability_rows_tsv: Path,
    peak_candidates_tsv: Path,
    output_dir: Path,
    targeted_workbook: Path | None = None,
    nl_ppm_max: float = 10.0,
    apex_ms2_delta_max_min: float = 0.08,
    nl_min_intensity_ratio: float = 0.01,
) -> tuple[TargetedNLDropoutRootCauseOutputs, TargetedNLDropoutRootCauseResult]:
    reliability_rows = _read_reliability_rows(targeted_reliability_rows_tsv)
    candidate_rows = _read_candidate_rows(peak_candidates_tsv)
    selected_by_key = _selected_candidates_by_key(candidate_rows)
    target_mz = _read_target_mz(targeted_workbook) if targeted_workbook else {}
    rows = _root_cause_rows(
        reliability_rows,
        selected_by_key,
        target_mz=target_mz,
        nl_ppm_max=nl_ppm_max,
        apex_ms2_delta_max_min=apex_ms2_delta_max_min,
        nl_min_intensity_ratio=nl_min_intensity_ratio,
    )
    result = TargetedNLDropoutRootCauseResult(
        summary=_summary(reliability_rows, rows),
        rows=rows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = TargetedNLDropoutRootCauseOutputs(
        summary_tsv=output_dir / "targeted_nl_dropout_root_cause_summary.tsv",
        rows_tsv=output_dir / "targeted_nl_dropout_root_cause_rows.tsv",
        json_path=output_dir / "targeted_nl_dropout_root_cause.json",
        markdown_path=output_dir / "targeted_nl_dropout_root_cause.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, result = run_targeted_nl_dropout_root_cause_audit(
            targeted_reliability_rows_tsv=args.targeted_reliability_rows_tsv,
            peak_candidates_tsv=args.peak_candidates_tsv,
            output_dir=args.output_dir,
            targeted_workbook=args.targeted_workbook,
            nl_ppm_max=args.nl_ppm_max,
            apex_ms2_delta_max_min=args.apex_ms2_delta_max_min,
            nl_min_intensity_ratio=args.nl_min_intensity_ratio,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Root-cause JSON: {outputs.json_path}")
    print(f"Root-cause report: {outputs.markdown_path}")
    print(f"Review-positive rows: {result.summary.review_positive_count}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify targeted review-positive NL dropout root causes.",
    )
    parser.add_argument("--targeted-reliability-rows-tsv", type=Path, required=True)
    parser.add_argument("--peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--targeted-workbook",
        type=Path,
        help="Optional targeted workbook used to include target m/z in rows.",
    )
    parser.add_argument("--nl-ppm-max", type=float, default=10.0)
    parser.add_argument("--apex-ms2-delta-max-min", type=float, default=0.08)
    parser.add_argument("--nl-min-intensity-ratio", type=float, default=0.01)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
