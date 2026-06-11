"""P2 baseline truth audit CLI for AsLS shadow gate targets.

Thin CLI wrapper. All reusable models, loading, classification, summaries,
plotting, and writers live in
``xic_extractor/diagnostics/p2_baseline_truth_audit.py``; this module only parses
arguments and orchestrates that package logic.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    AreaMetrics as AreaMetrics,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    BaselineTruthOutputs as BaselineTruthOutputs,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    BaselineTruthResult as BaselineTruthResult,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    BaselineTruthRow as BaselineTruthRow,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    TraceLoader as TraceLoader,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    _build_summary_rows as _build_summary_rows,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    build_baseline_truth_row as build_baseline_truth_row,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    classify_baseline_truth_row as classify_baseline_truth_row,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    compute_area_metrics as compute_area_metrics,
)
from xic_extractor.diagnostics.p2_baseline_truth_audit import (  # noqa: E402
    run_p2_baseline_truth_audit,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a diagnostic-only baseline truth audit for P2 AsLS shadow "
            "gate ISTD families."
        )
    )
    parser.add_argument("--p2-gate-rows-tsv", type=Path, required=True)
    parser.add_argument("--alignment-integration-audit-tsv", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--dll-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--rt-margin-min", type=float, default=0.4)
    parser.add_argument(
        "--include-gate-status",
        action="append",
        dest="include_gate_statuses",
        help=(
            "Gate row status to include in the audit. Repeat to include multiple "
            "statuses. Defaults to FAIL."
        ),
    )
    args = parser.parse_args(argv)

    try:
        outputs, result = run_p2_baseline_truth_audit(
            p2_gate_rows_tsv=args.p2_gate_rows_tsv,
            alignment_integration_audit_tsv=args.alignment_integration_audit_tsv,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            output_dir=args.output_dir,
            ppm=args.ppm,
            rt_margin_min=args.rt_margin_min,
            include_gate_statuses=tuple(args.include_gate_statuses or ("FAIL",)),
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Audit JSON: {outputs.json_path}")
    print(f"Audit report: {outputs.markdown_path}")
    print(f"Plot directory: {outputs.plot_dir}")
    print(f"Rows: {result.row_count}; Families: {result.family_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
