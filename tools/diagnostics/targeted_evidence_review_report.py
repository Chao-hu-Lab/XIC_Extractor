"""CLI facade for the targeted evidence human review report."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.targeted_evidence_review_report_model import build_report
from tools.diagnostics.targeted_evidence_review_report_rendering import render_html


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        payload = build_report(
            targeted_reliability_summary_tsv=args.targeted_reliability_summary_tsv,
            targeted_reliability_rows_tsv=args.targeted_reliability_rows_tsv,
            root_cause_summary_tsv=args.root_cause_summary_tsv,
            root_cause_rows_tsv=args.root_cause_rows_tsv,
            cross_report_summary_tsv=args.cross_report_summary_tsv,
            cross_report_rows_tsv=args.cross_report_rows_tsv,
            run_label=args.run_label,
        )
        write_report(args.output_html, payload)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Targeted evidence review report: {args.output_html}")
    print(f"Verdict: {payload['verdict']}")
    return 0


def write_report(output_html: Path, report: Mapping[str, Any]) -> Path:
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(render_html(report), encoding="utf-8")
    return output_html


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a human-first HTML report from targeted diagnostics.",
    )
    parser.add_argument("--targeted-reliability-summary-tsv", type=Path, required=True)
    parser.add_argument("--targeted-reliability-rows-tsv", type=Path, required=True)
    parser.add_argument("--root-cause-summary-tsv", type=Path, required=True)
    parser.add_argument("--root-cause-rows-tsv", type=Path, required=True)
    parser.add_argument("--cross-report-summary-tsv", type=Path, required=True)
    parser.add_argument("--cross-report-rows-tsv", type=Path)
    parser.add_argument("--output-html", type=Path, required=True)
    parser.add_argument("--run-label", default="")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
