"""Build a seed-aware shadow review for rescued-heavy backfill families."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.seed_aware_backfill_review_constants import (
    CLASS_NEIGHBOR,
    CLASS_NOT_ASSESSABLE,
    CLASS_NOT_RESCUED_HEAVY,
    CLASS_SEED_MISSING,
    CLASS_SEED_SUPPORTED,
    CLASS_SHAPE,
    LOW_COVERAGE_REQUIRED_COLUMNS,
    MIN_ACCEPTED_COUNT,
    MIN_RESCUE_COUNT,
    NEIGHBOR_INTERFERENCE_FRACTION_MAX,
    NEIGHBOR_VERDICT,
    OVERLAY_REQUIRED_COLUMNS,
    REVIEW_REQUIRED_COLUMNS,
    SEED_AUDIT_REQUIRED_COLUMNS,
    SEED_OVERLAY_PATTERN,
    SUPPORT_VERDICT,
    WITHHOLD_CLASSES,
)
from tools.diagnostics.seed_aware_backfill_review_io import (
    _group_by_family,
    _normalize_paths,
    _read_tsv,
)
from tools.diagnostics.seed_aware_backfill_review_model import (
    _append_float,
    _blast_radius_row,
    _classification_sort_key,
    _classify_family,
    _family_review_row,
    _float,
    _has_high_neighbor_interference,
    _is_seed_specific_overlay,
    _joined_paths,
    _max_or_blank,
    _min_or_blank,
    _numeric_values,
    _overlay_summary,
    _recommended_action,
    _review_reason,
    _seed_specific_overlay_rows,
    _seed_summary,
    _span,
    _summary_rows,
    build_seed_aware_review,
)
from tools.diagnostics.seed_aware_backfill_review_writers import (
    _blast_fields,
    _family_fields,
    _first_path,
    _format_value,
    _markdown_blast_row,
    _markdown_family_row,
    _write_blast_markdown,
    _write_markdown,
    _write_tsv,
    write_outputs,
)

__all__ = [
    "CLASS_NEIGHBOR",
    "CLASS_NOT_ASSESSABLE",
    "CLASS_NOT_RESCUED_HEAVY",
    "CLASS_SEED_MISSING",
    "CLASS_SEED_SUPPORTED",
    "CLASS_SHAPE",
    "LOW_COVERAGE_REQUIRED_COLUMNS",
    "MIN_ACCEPTED_COUNT",
    "MIN_RESCUE_COUNT",
    "NEIGHBOR_INTERFERENCE_FRACTION_MAX",
    "NEIGHBOR_VERDICT",
    "OVERLAY_REQUIRED_COLUMNS",
    "REVIEW_REQUIRED_COLUMNS",
    "SEED_AUDIT_REQUIRED_COLUMNS",
    "SEED_OVERLAY_PATTERN",
    "SUPPORT_VERDICT",
    "WITHHOLD_CLASSES",
    "_append_float",
    "_blast_fields",
    "_blast_radius_row",
    "_classification_sort_key",
    "_classify_family",
    "_family_fields",
    "_family_review_row",
    "_first_path",
    "_float",
    "_format_value",
    "_group_by_family",
    "_has_high_neighbor_interference",
    "_is_seed_specific_overlay",
    "_joined_paths",
    "_markdown_blast_row",
    "_markdown_family_row",
    "_max_or_blank",
    "_min_or_blank",
    "_normalize_paths",
    "_numeric_values",
    "_overlay_summary",
    "_read_tsv",
    "_recommended_action",
    "_review_reason",
    "_seed_specific_overlay_rows",
    "_seed_summary",
    "_span",
    "_summary_rows",
    "_write_blast_markdown",
    "_write_markdown",
    "_write_tsv",
    "build_seed_aware_review",
    "main",
    "write_outputs",
]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = build_seed_aware_review(
            review_candidates_tsv=args.review_candidates_tsv,
            overlay_batch_summary_tsv=args.overlay_batch_summary_tsv,
            low_ms1_rows_tsv=args.low_ms1_rows_tsv,
            backfill_seed_audit_tsv=args.backfill_seed_audit_tsv,
            protected_family_ids=tuple(args.protected_family_id or ()),
            min_rescue_count=args.min_rescue_count,
            min_accepted_count=args.min_accepted_count,
        )
        write_outputs(args.output_dir, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"seed-aware backfill review: {args.output_dir}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-candidates-tsv", required=True, type=Path)
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        required=True,
        action="append",
        type=Path,
        help=(
            "family_ms1_overlay_batch_summary.tsv; repeat to merge top-review "
            "and seed-specific overlay batches"
        ),
    )
    parser.add_argument("--low-ms1-rows-tsv", required=True, type=Path)
    parser.add_argument("--backfill-seed-audit-tsv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--protected-family-id",
        action="append",
        help=(
            "Family id that should never be treated as automatically safe to "
            "withhold in the blast-radius report"
        ),
    )
    parser.add_argument("--min-rescue-count", type=int, default=MIN_RESCUE_COUNT)
    parser.add_argument("--min-accepted-count", type=int, default=MIN_ACCEPTED_COUNT)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
