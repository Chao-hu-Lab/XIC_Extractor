from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.sample_metadata import (
    SampleMetadataError,
    load_sample_metadata,
    sample_metadata_to_injection_order,
    summarize_sample_metadata,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a shared sample metadata TSV/CSV file."
    )
    parser.add_argument("path", type=Path, help="Sample metadata TSV or CSV path.")
    parser.add_argument(
        "--summary-json",
        action="store_true",
        help="Print the validation summary as JSON.",
    )
    args = parser.parse_args(argv)

    try:
        rows = load_sample_metadata(args.path)
    except SampleMetadataError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    summary = summarize_sample_metadata(rows)
    summary["injection_order_alias_count"] = len(
        sample_metadata_to_injection_order(rows)
    )
    if args.summary_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            "Sample metadata valid: "
            f"{summary['sample_count']} sample(s), "
            f"{summary['with_injection_order_count']} with injection order, "
            f"{summary['excluded_count']} excluded."
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
