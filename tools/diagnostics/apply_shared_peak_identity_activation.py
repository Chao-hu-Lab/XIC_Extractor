"""Apply shared peak identity activation sidecars to alignment TSV copies."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    product_activation,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = product_activation.apply_activation_to_alignment_outputs(
            activation_decisions_tsv=args.activation_decisions_tsv,
            activation_acceptance_tsv=args.activation_acceptance_tsv,
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            alignment_review_tsv=args.alignment_review_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            output_dir=args.output_dir,
            require_acceptance_pass=not args.allow_non_passing_acceptance,
            output_mode=args.output_mode,
            allow_overwrite_source=args.allow_overwrite_source,
            legacy_rt_row_oracle_xlsx=args.legacy_rt_row_oracle_xlsx,
            legacy_rt_row_oracle_mz_ppm=args.legacy_rt_row_oracle_mz_ppm,
            legacy_rt_row_oracle_rt_tolerance_min=(
                args.legacy_rt_row_oracle_rt_tolerance_min
            ),
            require_complete_peak_hypothesis_identity=(
                args.require_complete_peak_hypothesis_identity
            ),
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Activated matrix TSV: {outputs.matrix_tsv}")
    print(f"Activated review TSV: {outputs.review_tsv}")
    print(f"Activated cells TSV: {outputs.cells_tsv}")
    print(f"Activation application summary TSV: {outputs.summary_tsv}")
    print(f"Activation value delta TSV: {outputs.value_delta_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation-decisions-tsv", type=Path, required=True)
    parser.add_argument("--activation-acceptance-tsv", type=Path, required=True)
    parser.add_argument("--alignment-matrix-tsv", type=Path, required=True)
    parser.add_argument("--alignment-review-tsv", type=Path, required=True)
    parser.add_argument("--alignment-cells-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--output-mode",
        choices=("activated-copy", "formal"),
        default="activated-copy",
        help=(
            "activated-copy writes *_activated.tsv sidecars; formal writes "
            "alignment_matrix.tsv, alignment_review.tsv, and alignment_cells.tsv "
            "as the product output contract."
        ),
    )
    parser.add_argument(
        "--allow-overwrite-source",
        action="store_true",
        help=(
            "Allow formal output mode to overwrite source alignment TSVs. "
            "Use only after preserving source artifacts elsewhere."
        ),
    )
    parser.add_argument(
        "--allow-non-passing-acceptance",
        action="store_true",
        help="Diagnostic override only; product application normally requires pass.",
    )
    parser.add_argument(
        "--legacy-rt-row-oracle-xlsx",
        type=Path,
        help=(
            "Optional clean MZmine-style workbook with Mz and RT columns. "
            "Formal mode records matching rows as context only; the legacy "
            "pipeline is not product identity authority and does not replace "
            "peak_hypothesis_id."
        ),
    )
    parser.add_argument(
        "--legacy-rt-row-oracle-mz-ppm",
        type=float,
        default=20.0,
        help="m/z tolerance for --legacy-rt-row-oracle-xlsx matching.",
    )
    parser.add_argument(
        "--legacy-rt-row-oracle-rt-tolerance-min",
        type=float,
        default=1.0,
        help="RT tolerance in minutes for --legacy-rt-row-oracle-xlsx matching.",
    )
    parser.add_argument(
        "--require-complete-peak-hypothesis-identity",
        action="store_true",
        help=(
            "Fail unless formal output can emit peak_hypothesis_id as the "
            "matrix row identity. Family projections are allowed when no split "
            "evidence exists."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
