from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.calibration_product_preview import (
    build_level0_calibration_bundle,
    build_level1_rt_calibration_preview,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build manifest-backed instrument QC calibration evidence bundle "
            "and optional matrix preview sidecar."
        ),
    )
    parser.add_argument("--instrument-qc-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--matrix-input", type=Path)
    parser.add_argument(
        "--matrix-input-role",
        choices=("untargeted_cell_table", "targeted_result_table", "external_matrix"),
    )
    parser.add_argument("--preview-kind", choices=("rt", "response", "both"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_args(args)
        command = " ".join(sys.argv if argv is None else argv)
        if args.matrix_input is None:
            result = build_level0_calibration_bundle(
                instrument_qc_dir=args.instrument_qc_dir,
                output_dir=args.output_dir,
                generation_command=command,
            )
        else:
            if args.preview_kind not in {None, "rt"}:
                raise ValueError(
                    "only --preview-kind rt is implemented in this checkpoint"
                )
            result = build_level1_rt_calibration_preview(
                instrument_qc_dir=args.instrument_qc_dir,
                matrix_input=args.matrix_input,
                matrix_input_role=args.matrix_input_role or "",
                output_dir=args.output_dir,
                generation_command=command,
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _print_outputs(result)
    return 0


def _validate_args(args: argparse.Namespace) -> None:
    if not args.instrument_qc_dir.exists():
        raise ValueError(f"instrument QC dir not found: {args.instrument_qc_dir}")
    if not args.instrument_qc_dir.is_dir():
        raise ValueError(
            f"instrument QC path is not a directory: {args.instrument_qc_dir}"
        )
    trend = args.instrument_qc_dir / "instrument_qc_sdolek_trend.tsv"
    if not trend.exists():
        raise ValueError(f"missing required trend TSV: {trend}")
    if args.matrix_input is None:
        if args.preview_kind is not None:
            raise ValueError("--matrix-input is required when --preview-kind is set")
        if args.matrix_input_role is not None:
            raise ValueError(
                "--matrix-input is required when --matrix-input-role is set"
            )
        return
    if not args.matrix_input.exists():
        raise ValueError(f"matrix input not found: {args.matrix_input}")
    if args.matrix_input_role is None:
        raise ValueError("--matrix-input-role is required when --matrix-input is set")


def _print_outputs(result: object) -> None:
    for name in (
        "manifest_json",
        "evidence_tsv",
        "evidence_summary_json",
        "rt_preview_tsv",
        "rt_preview_summary_json",
        "response_preview_tsv",
        "response_preview_summary_json",
    ):
        value = getattr(result, name, None)
        if value is not None:
            print(f"Wrote {value}")


if __name__ == "__main__":
    raise SystemExit(main())
