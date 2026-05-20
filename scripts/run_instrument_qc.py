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
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", default="sdolek")
    parser.add_argument("--injection-order-source", type=Path)
    parser.add_argument("--dll-dir", type=Path)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
