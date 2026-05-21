from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.decision_report import (
    build_instrument_qc_decision,
    render_instrument_qc_decision_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a compact instrument QC decision report.",
    )
    parser.add_argument("--instrument-qc-dir", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    decision = build_instrument_qc_decision(args.instrument_qc_dir)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_instrument_qc_decision_markdown(decision),
        encoding="utf-8",
    )
    print(f"Wrote {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
