from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.review_actions import (
    ReviewActionError,
    load_review_actions,
    summarize_review_actions,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a targeted review action TSV/CSV import file."
    )
    parser.add_argument("path", type=Path, help="Review action TSV or CSV path.")
    parser.add_argument(
        "--summary-json",
        action="store_true",
        help="Print the validation summary as JSON.",
    )
    args = parser.parse_args(argv)

    try:
        actions = load_review_actions(args.path)
    except ReviewActionError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    summary = summarize_review_actions(actions)
    if args.summary_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            "Review actions valid: "
            f"{summary['action_count']} action(s), "
            f"{summary['product_mutating_action_count']} product-mutating."
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
