from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.biological_istd_rt_envelope_io import (
    build_biological_istd_rt_envelope_from_files,
    write_biological_istd_rt_envelope_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an audit-only empirical RT envelope from biological QC ISTDs."
        )
    )
    parser.add_argument(
        "--biological-istd-rows-tsv",
        type=Path,
        required=True,
        help=(
            "Row-level biological QC ISTD RT evidence. Expected columns include "
            "sample_name, injection_order, target_label, rt_min, reliability_state."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = build_biological_istd_rt_envelope_from_files(
            biological_istd_rows_tsv=args.biological_istd_rows_tsv,
        )
        outputs = write_biological_istd_rt_envelope_outputs(
            output_dir=args.output_dir,
            result=result,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in outputs.values():
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
