"""CLI facade for the alignment decision diagnostic report."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tools.diagnostics.alignment_decision_report_model import build_report
from tools.diagnostics.alignment_decision_report_rendering import render_html


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_report(
            alignment_dir=args.alignment_dir,
            targeted_istd_benchmark_json=args.targeted_istd_benchmark_json,
            owner_backfill_economics_json=args.owner_backfill_economics_json,
            timing_json=args.timing_json,
            rt_normalization_json=args.rt_normalization_json,
            known_istd_exceptions=tuple(args.known_istd_exception),
        )
        write_report(args.output_html, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Alignment decision report: {args.output_html}")
    print(f"Verdict: {report['verdict']}")
    return 0


def write_report(output_html: Path, report: Mapping[str, Any]) -> Path:
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(render_html(report), encoding="utf-8")
    return output_html


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an HTML decision report from alignment diagnostics.",
    )
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-html", type=Path, required=True)
    parser.add_argument("--targeted-istd-benchmark-json", type=Path)
    parser.add_argument("--owner-backfill-economics-json", type=Path)
    parser.add_argument("--timing-json", type=Path)
    parser.add_argument("--rt-normalization-json", type=Path)
    parser.add_argument(
        "--known-istd-exception",
        action="append",
        default=[],
        help="Known ISTD exception in TARGET:FAILURE_MODE format.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
