"""Guardrail diagnostics for untargeted alignment checkpoint outputs."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.untargeted_alignment_guardrail_io import (
    _read_optional_tsv,
    _read_required_tsv,
    _read_tsv,
    _write_dict_csv,
    _write_json,
)
from tools.diagnostics.untargeted_alignment_guardrail_metrics import (
    _case_status_reason,
    _compute_case_assertions,
    _edge_endpoint_in_window,
    _first_present,
    _float_in_range,
    _float_value,
    _int_value,
    _is_high_backfill_dependency,
    _is_production_family,
    _is_trueish,
    _metrics_for_comparison,
    _metrics_to_json,
    _mz_in_ppm,
    _production_present_count,
    _review_row_in_window,
    _row_flags,
    _row_in_mz_window,
    _status_counts_by_family,
    _strong_edge_count,
    compute_guardrails,
)
from tools.diagnostics.untargeted_alignment_guardrail_models import (
    CASE_SUMMARY_COLUMNS,
    CASE_WINDOWS,
    COMPARISON_METRICS,
    PRODUCTION_STATUSES,
    TARGETED_ISTD_BENCHMARK_COLUMNS,
    CaseAssertion,
    CaseWindow,
    GuardrailMetrics,
)
from tools.diagnostics.untargeted_alignment_guardrail_outputs import (
    _bool_text,
    _case_summary_row,
    compare_guardrails,
    write_case_assertion_summary_tsv,
)
from tools.diagnostics.untargeted_alignment_guardrail_targets import (
    _benchmark_summaries,
    _count_failure_mode,
    _count_summaries,
    _is_json_trueish,
    _normalize_benchmark_summary,
    _targeted_failure_counts,
    _targeted_istd_metric_row,
    compare_targeted_audit_counts,
    targeted_istd_benchmark_guardrail_rows,
)

__all__ = [
    "CASE_SUMMARY_COLUMNS",
    "CASE_WINDOWS",
    "COMPARISON_METRICS",
    "PRODUCTION_STATUSES",
    "TARGETED_ISTD_BENCHMARK_COLUMNS",
    "CaseAssertion",
    "CaseWindow",
    "GuardrailMetrics",
    "_benchmark_summaries",
    "_bool_text",
    "_case_summary_row",
    "_case_status_reason",
    "_compute_case_assertions",
    "_count_failure_mode",
    "_count_summaries",
    "_edge_endpoint_in_window",
    "_first_present",
    "_float_in_range",
    "_float_value",
    "_int_value",
    "_is_high_backfill_dependency",
    "_is_json_trueish",
    "_is_production_family",
    "_is_trueish",
    "_metrics_for_comparison",
    "_metrics_to_json",
    "_mz_in_ppm",
    "_normalize_benchmark_summary",
    "_production_present_count",
    "_read_optional_tsv",
    "_read_required_tsv",
    "_read_tsv",
    "_review_row_in_window",
    "_row_flags",
    "_row_in_mz_window",
    "_status_counts_by_family",
    "_strong_edge_count",
    "_targeted_failure_counts",
    "_targeted_istd_metric_row",
    "_write_dict_csv",
    "_write_json",
    "compare_guardrails",
    "compare_targeted_audit_counts",
    "compute_guardrails",
    "main",
    "targeted_istd_benchmark_guardrail_rows",
    "write_case_assertion_summary_tsv",
]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        _validate_args(args)
        if args.alignment_dir:
            metrics = compute_guardrails(args.alignment_dir)
            if args.output_json:
                _write_json(args.output_json, _metrics_to_json(metrics))
            if args.case_summary_tsv:
                write_case_assertion_summary_tsv(
                    args.case_summary_tsv,
                    metrics.case_assertions,
                )

        if args.baseline_dir and args.candidate_dir:
            baseline_metrics = compute_guardrails(args.baseline_dir)
            candidate_metrics = compute_guardrails(args.candidate_dir)
            _write_dict_csv(
                args.comparison_csv,
                compare_guardrails(
                    _metrics_for_comparison(baseline_metrics),
                    _metrics_for_comparison(candidate_metrics),
                ),
            )

        if args.baseline_targeted_comparison and args.candidate_targeted_comparison:
            if not args.target_label:
                raise ValueError("--target-label is required for targeted comparison")
            _write_dict_csv(
                args.targeted_comparison_csv,
                compare_targeted_audit_counts(
                    args.baseline_targeted_comparison,
                    args.candidate_targeted_comparison,
                    target_label=args.target_label,
                ),
            )

        if args.targeted_istd_benchmark_json:
            _write_dict_csv(
                args.targeted_istd_benchmark_csv,
                targeted_istd_benchmark_guardrail_rows(
                    args.targeted_istd_benchmark_json,
                ),
            )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute and compare untargeted alignment guardrails.",
    )
    parser.add_argument("--alignment-dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--case-summary-tsv", type=Path)
    parser.add_argument("--comparison-csv", type=Path)
    parser.add_argument("--baseline-targeted-comparison", type=Path)
    parser.add_argument("--candidate-targeted-comparison", type=Path)
    parser.add_argument("--target-label")
    parser.add_argument("--targeted-comparison-csv", type=Path)
    parser.add_argument("--targeted-istd-benchmark-json", type=Path)
    parser.add_argument("--targeted-istd-benchmark-csv", type=Path)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
    baseline_group = (
        args.baseline_dir,
        args.candidate_dir,
        args.comparison_csv,
    )
    targeted_group = (
        args.baseline_targeted_comparison,
        args.candidate_targeted_comparison,
        args.target_label,
        args.targeted_comparison_csv,
    )
    targeted_istd_group = (
        args.targeted_istd_benchmark_json,
        args.targeted_istd_benchmark_csv,
    )
    alignment_group = (
        args.alignment_dir,
        args.output_json,
        args.case_summary_tsv,
    )
    has_alignment_group = any(value is not None for value in alignment_group)
    has_baseline_group = any(value is not None for value in baseline_group)
    has_targeted_group = any(value is not None for value in targeted_group)
    has_targeted_istd_group = any(value is not None for value in targeted_istd_group)

    if has_alignment_group and (args.alignment_dir is None or args.output_json is None):
        raise ValueError(
            "Alignment group requires --alignment-dir and --output-json",
        )
    if has_baseline_group and not all(value is not None for value in baseline_group):
        raise ValueError(
            "Guardrail comparison requires --baseline-dir, --candidate-dir, "
            "and --comparison-csv",
        )
    if has_targeted_group and not all(value is not None for value in targeted_group):
        raise ValueError(
            "Targeted comparison requires --baseline-targeted-comparison, "
            "--candidate-targeted-comparison, --target-label, and "
            "--targeted-comparison-csv",
        )
    if has_targeted_istd_group and not all(
        value is not None for value in targeted_istd_group
    ):
        raise ValueError(
            "Targeted ISTD benchmark requires --targeted-istd-benchmark-json "
            "and --targeted-istd-benchmark-csv",
        )
    if not (
        has_alignment_group
        or has_baseline_group
        or has_targeted_group
        or has_targeted_istd_group
    ):
        raise ValueError(
            "Provide at least one actionable option group: "
            "--alignment-dir with --output-json; --baseline-dir with "
            "--candidate-dir and --comparison-csv; or "
            "--baseline-targeted-comparison with --candidate-targeted-comparison, "
            "--target-label, and --targeted-comparison-csv; or "
            "--targeted-istd-benchmark-json with "
            "--targeted-istd-benchmark-csv.",
        )


if __name__ == "__main__":
    raise SystemExit(main())
