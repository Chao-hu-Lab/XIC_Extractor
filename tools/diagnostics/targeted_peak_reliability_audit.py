"""Targeted peak reliability audit for benchmark eligibility."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.diagnostics.targeted_peak_reliability_classifier import (
    _area_context_by_key,
    _classify_row,
    _summarize_rows,
)
from tools.diagnostics.targeted_peak_reliability_loaders import (
    _load_selected_candidate_evidence,
    _load_targeted_workbook,
)
from tools.diagnostics.targeted_peak_reliability_models import (
    TargetedReliabilityOutputs,
    TargetedReliabilityResult,
)
from tools.diagnostics.targeted_peak_reliability_writers import _write_outputs


def run_targeted_peak_reliability_audit(
    *,
    targeted_workbook: Path,
    output_dir: Path,
    known_target_exceptions: Sequence[str] = (),
    peak_candidates_tsv: Path | None = None,
) -> tuple[TargetedReliabilityOutputs, TargetedReliabilityResult]:
    rows, score_by_key = _load_targeted_workbook(targeted_workbook)
    candidate_by_key = _load_selected_candidate_evidence(peak_candidates_tsv)
    known = _parse_known_exceptions(known_target_exceptions)
    area_context = _area_context_by_key(rows)
    reliability_rows = tuple(
        _classify_row(
            row,
            score=score_by_key.get((row.sample_name, row.target_label)),
            candidate_evidence=candidate_by_key.get(
                (row.sample_name, row.target_label)
            ),
            known_exception=known.get(row.target_label, ""),
            area_context=area_context.get((row.sample_name, row.target_label)),
        )
        for row in rows
    )
    result = TargetedReliabilityResult(
        rows=reliability_rows,
        summaries=_summarize_rows(reliability_rows),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = TargetedReliabilityOutputs(
        summary_tsv=output_dir / "targeted_peak_reliability_summary.tsv",
        rows_tsv=output_dir / "targeted_peak_reliability_rows.tsv",
        json_path=output_dir / "targeted_peak_reliability.json",
        markdown_path=output_dir / "targeted_peak_reliability.md",
    )
    _write_outputs(outputs, result, known_target_exceptions=known)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, result = run_targeted_peak_reliability_audit(
            targeted_workbook=args.targeted_workbook.resolve(),
            output_dir=args.output_dir.resolve(),
            known_target_exceptions=tuple(args.known_target_exception),
            peak_candidates_tsv=(
                args.peak_candidates_tsv.resolve()
                if args.peak_candidates_tsv is not None
                else None
            ),
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Reliability JSON: {outputs.json_path}")
    print(f"Reliability report: {outputs.markdown_path}")
    return 0 if result.targeted_review_count == 0 else 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit targeted peak reliability for benchmark eligibility.",
    )
    parser.add_argument("--targeted-workbook", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--peak-candidates-tsv",
        type=Path,
        help=(
            "Optional selected peak candidate evidence TSV. When provided, "
            "selected candidate consistency can mark NL_FAIL rows as "
            "targeted_review_positive without making them benchmark eligible."
        ),
    )
    parser.add_argument(
        "--known-target-exception",
        action="append",
        default=[],
        help="Known targeted-side exception in TARGET:FAILURE_MODE form.",
    )
    return parser.parse_args(argv)


def _parse_known_exceptions(values: Sequence[str]) -> dict[str, str]:
    known: dict[str, str] = {}
    for value in values:
        target, separator, mode = value.partition(":")
        if not separator:
            raise ValueError(
                "--known-target-exception must use TARGET:FAILURE_MODE form"
            )
        target = target.strip()
        mode = mode.strip()
        if not target or not mode:
            raise ValueError(
                "--known-target-exception must use TARGET:FAILURE_MODE form"
            )
        known[target] = mode
    return known


if __name__ == "__main__":
    raise SystemExit(main())
