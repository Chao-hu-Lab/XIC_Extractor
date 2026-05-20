from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.pipeline import run_sdolek_pipeline
from xic_extractor.raw_reader import RawReaderError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run opt-in instrument-only QC trend extraction.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Outputs:\n"
            "  instrument_qc_sdolek_trend.tsv\n"
            "  instrument_qc_sdolek_trend.json\n"
            "  instrument_qc_sdolek_diagnostics.tsv\n"
            "  instrument_qc_trend_sdolek.xlsx\n\n"
            "Input note:\n"
            "  --raw-dir must contain the expected SDOLEK subfolder."
        ),
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="Batch RAW root containing the SDOLEK subfolder.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where TSV, JSON, diagnostics TSV, and XLSX are written.",
    )
    parser.add_argument(
        "--mode",
        default="sdolek",
        help="Instrument QC mode. Phase 2 supports only 'sdolek'.",
    )
    parser.add_argument(
        "--injection-order-source",
        type=Path,
        help="Optional docs-derived Sample_Name,Injection_Order CSV.",
    )
    parser.add_argument(
        "--dll-dir",
        type=Path,
        help="Optional Thermo DLL directory override.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode != "sdolek":
        print(
            f"unsupported mode: {args.mode}. Phase 1 supports only 'sdolek'.",
            file=sys.stderr,
        )
        return 2
    try:
        output = run_sdolek_pipeline(
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            injection_order_source=args.injection_order_source,
            dll_dir=args.dll_dir,
        )
    except RawReaderError as exc:
        print(f"RAW reader error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"File not found: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote {output.trend_tsv}")
    print(f"Wrote {output.trend_json}")
    print(f"Wrote {output.diagnostics_tsv}")
    print(f"Wrote {output.workbook}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
