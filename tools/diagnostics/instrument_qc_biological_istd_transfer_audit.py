from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.rt_transfer_audit_io import (
    build_biological_istd_transfer_audit_from_files,
    write_biological_istd_transfer_audit_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build audit-only evidence for clean-standard RT trend transfer "
            "to biological QC ISTDs."
        )
    )
    parser.add_argument("--clean-standard-summary-tsv", type=Path, required=True)
    parser.add_argument("--biological-qc-istd-summary-tsv", type=Path, required=True)
    parser.add_argument(
        "--istd-scope",
        default="provided_biological_qc_istd_summary_rows",
        help=(
            "Explicit scope for ISTD rows used by this audit. The default means "
            "all rows from the provided biological QC ISTD summary are evaluated."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        rows = build_biological_istd_transfer_audit_from_files(
            clean_standard_summary_tsv=args.clean_standard_summary_tsv,
            biological_qc_istd_summary_tsv=args.biological_qc_istd_summary_tsv,
        )
        outputs = write_biological_istd_transfer_audit_outputs(
            output_dir=args.output_dir,
            rows=rows,
            istd_scope=args.istd_scope,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in outputs.values():
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
