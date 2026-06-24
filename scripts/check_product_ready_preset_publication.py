"""Check current-run product-ready preset publication artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xic_extractor.diagnostics.product_ready_preset_publication_check import (  # noqa: E402
    DEFAULT_EXPECTED_SOURCE_RUN_PREFIX,
    check_product_ready_preset_publication,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment-dir",
        type=Path,
        required=True,
        help="Completed run_alignment output directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Checker output directory. Defaults to "
            "<alignment-dir>/product_ready_preset_publication_check."
        ),
    )
    parser.add_argument(
        "--expected-source-run-prefix",
        default=DEFAULT_EXPECTED_SOURCE_RUN_PREFIX,
        help="Expected source_run_id prefix. Pass an empty string to disable.",
    )
    parser.add_argument(
        "--allow-backfill-expansion-replay",
        action="store_true",
        help=(
            "Do not fail when backfill_expansion_productization_preset exists. "
            "Do not use this for the built-in product-ready preset gate."
        ),
    )
    args = parser.parse_args(argv)

    outputs = check_product_ready_preset_publication(
        alignment_dir=args.alignment_dir,
        output_dir=args.output_dir,
        expected_source_run_prefix=args.expected_source_run_prefix,
        require_no_backfill_expansion_replay=(
            not args.allow_backfill_expansion_replay
        ),
    )
    print(f"Product-ready preset publication summary JSON: {outputs.summary_json}")
    print(f"Product-ready preset publication checks TSV: {outputs.checks_tsv}")
    return 0 if outputs.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
