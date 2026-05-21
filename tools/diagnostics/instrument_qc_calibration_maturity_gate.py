from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.calibration_maturity_gate_io import (
    build_calibration_maturity_gate_from_files,
    write_calibration_maturity_gate_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build audit-only go/no-go decisions for instrument-QC calibration "
            "maturity levels."
        )
    )
    parser.add_argument("--rt-model-summary-json", type=Path, required=True)
    parser.add_argument("--matrix-rt-preview-summary-json", type=Path, required=True)
    parser.add_argument("--matrix-rt-preview-tsv", type=Path, required=True)
    parser.add_argument("--biological-istd-transfer-json", type=Path, required=True)
    parser.add_argument("--response-model-summary-json", type=Path)
    parser.add_argument("--biological-response-transfer-json", type=Path)
    parser.add_argument("--downstream-compatibility-json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        decisions = build_calibration_maturity_gate_from_files(
            rt_model_summary_json=args.rt_model_summary_json,
            matrix_rt_preview_summary_json=args.matrix_rt_preview_summary_json,
            matrix_rt_preview_tsv=args.matrix_rt_preview_tsv,
            biological_istd_transfer_json=args.biological_istd_transfer_json,
            response_model_summary_json=args.response_model_summary_json,
            biological_response_transfer_json=args.biological_response_transfer_json,
            downstream_compatibility_json=args.downstream_compatibility_json,
        )
        outputs = write_calibration_maturity_gate_outputs(
            output_dir=args.output_dir,
            decisions=decisions,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in outputs.values():
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
