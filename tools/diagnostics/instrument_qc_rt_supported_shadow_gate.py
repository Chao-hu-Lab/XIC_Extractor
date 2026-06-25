from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.rt_supported_shadow_gate import (
    RtSupportedShadowGateParameters,
)
from xic_extractor.instrument_qc.rt_supported_shadow_gate_io import (
    build_input_invalid_shadow_gate_result,
    build_rt_supported_shadow_gate_from_files,
    write_rt_supported_shadow_gate_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build audit-only Level 2.5 RT-supported shadow gate diagnostics. "
            "This report never mutates matrix, scoring, resolver, or targeted "
            "reliability outputs."
        ),
    )
    parser.add_argument(
        "--matrix-rt-preview-tsv",
        type=Path,
        required=True,
        help="Row-level matrix RT calibration preview TSV.",
    )
    parser.add_argument(
        "--matrix-rt-preview-summary-json",
        type=Path,
        required=True,
        help="Matrix RT preview summary JSON used as a required companion artifact.",
    )
    parser.add_argument(
        "--biological-istd-transfer-tsv",
        type=Path,
        required=True,
        help="Biological ISTD clean-to-biological transfer audit TSV.",
    )
    parser.add_argument(
        "--biological-istd-transfer-json",
        type=Path,
        required=True,
        help="Biological ISTD transfer summary JSON. Must declare istd_scope.",
    )
    parser.add_argument(
        "--biological-istd-anchor-rows-tsv",
        type=Path,
        help=(
            "Optional row-level biological ISTD anchors. Without this file the "
            "diagnostic can run, but cannot emit rt_supported_shadow_candidate."
        ),
    )
    parser.add_argument(
        "--anchor-rt-window-min",
        type=float,
        default=1.0,
        help=(
            "Maximum RT distance from a matrix row to a biological ISTD anchor "
            "(default: 1.0)."
        ),
    )
    parser.add_argument(
        "--anchor-injection-window",
        type=int,
        default=20,
        help=(
            "Maximum injection-order distance to a biological ISTD anchor "
            "(default: 20)."
        ),
    )
    parser.add_argument(
        "--residual-max-min",
        type=float,
        default=0.30,
        help=(
            "Maximum local residual p95 allowed for review-candidate rows "
            "(default: 0.30)."
        ),
    )
    parser.add_argument(
        "--uncertainty-max-min",
        type=float,
        default=0.30,
        help=(
            "Maximum RT uncertainty allowed for review-candidate rows "
            "(default: 0.30)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for rows, summary TSV, JSON, and Markdown diagnostics.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    parameters = RtSupportedShadowGateParameters(
        anchor_rt_window_min=args.anchor_rt_window_min,
        anchor_injection_window=args.anchor_injection_window,
        residual_max_min=args.residual_max_min,
        uncertainty_max_min=args.uncertainty_max_min,
    )
    try:
        result = build_rt_supported_shadow_gate_from_files(
            matrix_rt_preview_tsv=args.matrix_rt_preview_tsv,
            matrix_rt_preview_summary_json=args.matrix_rt_preview_summary_json,
            biological_istd_transfer_tsv=args.biological_istd_transfer_tsv,
            biological_istd_transfer_json=args.biological_istd_transfer_json,
            biological_istd_anchor_rows_tsv=args.biological_istd_anchor_rows_tsv,
            parameters=parameters,
        )
    except ValueError as exc:
        result = build_input_invalid_shadow_gate_result(
            error=exc,
            parameters=parameters,
        )
        outputs = write_rt_supported_shadow_gate_outputs(
            output_dir=args.output_dir,
            result=result,
        )
        print(str(exc), file=sys.stderr)
    else:
        outputs = write_rt_supported_shadow_gate_outputs(
            output_dir=args.output_dir,
            result=result,
        )
    for path in outputs.values():
        print(f"Wrote {path}")
    print(f"Run verdict: {result.run_verdict}")
    return 0 if result.run_verdict != "input_invalid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
