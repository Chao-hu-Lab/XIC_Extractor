from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.rt_ms1_backfill_cross_evidence_io import (
    build_rt_ms1_cross_evidence_from_files,
    write_rt_ms1_cross_evidence_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Cross-tab audit-only Level 2.5 RT support with seed-aware MS1 "
            "backfill review evidence."
        )
    )
    parser.add_argument(
        "--rt-shadow-rows-tsv",
        type=Path,
        required=True,
        help="Level 2.5 instrument_qc_rt_supported_shadow_gate_rows.tsv.",
    )
    parser.add_argument(
        "--seed-aware-families-tsv",
        type=Path,
        required=True,
        help="seed_aware_backfill_review_families.tsv.",
    )
    parser.add_argument(
        "--alignment-review-tsv",
        type=Path,
        help=(
            "Optional alignment_review.tsv. When provided, the report adds "
            "current final-matrix status by evidence grade."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for cross-evidence TSV, JSON, and Markdown diagnostics.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = build_rt_ms1_cross_evidence_from_files(
            rt_shadow_rows_tsv=args.rt_shadow_rows_tsv,
            seed_aware_families_tsv=args.seed_aware_families_tsv,
            alignment_review_tsv=args.alignment_review_tsv,
        )
        outputs = write_rt_ms1_cross_evidence_outputs(
            output_dir=args.output_dir,
            result=result,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in outputs.values():
        print(f"Wrote {path}")
    print(f"RT x MS1 cross-evidence families: {result.total_families}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
