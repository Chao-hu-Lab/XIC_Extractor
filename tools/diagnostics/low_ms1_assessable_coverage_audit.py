"""Diagnose low MS1-assessable coverage in family backfill review output."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.diagnostics.low_ms1_coverage_review_classifier import build_audit
from tools.diagnostics.low_ms1_coverage_review_loaders import (
    _backfill_seed_rows_by_family,
    _load_discovery_candidate,
    _read_csv,
    _read_tsv,
    _trace_summary_path,
)
from tools.diagnostics.low_ms1_coverage_review_models import (
    ALIGNMENT_REVIEW_REQUIRED_COLUMNS,
    APEX_AWARE_QUEUE_BUCKETS,
    ASSESSABLE_FRACTION_MIN,
    BACKFILL_SEED_AUDIT_REQUIRED_COLUMNS,
    DISCOVERY_REQUIRED_COLUMNS,
    LOW_COVERAGE_CLASSIFICATION,
    REVIEW_REQUIRED_COLUMNS,
    SEED_APEX_DELTA_CONCERN_SEC,
    SEED_OVERLAY_QUEUE_BUCKETS,
    SEED_RT_SPAN_CONCERN_MIN,
    SELECTED_APEX_IN_WINDOW_MIN,
    SELECTED_APEX_OVERLAY_PADDING_MIN,
    TRACE_DISCOVERY_JOIN_COLUMNS,
    TRACE_REQUIRED_COLUMNS,
    ZERO_TRACE_INSIDE_WINDOW_FRACTION_MIN,
)
from tools.diagnostics.low_ms1_coverage_review_writers import (
    _apex_aware_queue_fields,
    _detail_fields,
    _format_value,
    _seed_aware_queue_fields,
    _summary_fields,
    _write_markdown,
    _write_tsv,
    write_outputs,
)

__all__ = (
    "ALIGNMENT_REVIEW_REQUIRED_COLUMNS",
    "APEX_AWARE_QUEUE_BUCKETS",
    "ASSESSABLE_FRACTION_MIN",
    "BACKFILL_SEED_AUDIT_REQUIRED_COLUMNS",
    "DISCOVERY_REQUIRED_COLUMNS",
    "LOW_COVERAGE_CLASSIFICATION",
    "REVIEW_REQUIRED_COLUMNS",
    "SEED_APEX_DELTA_CONCERN_SEC",
    "SEED_OVERLAY_QUEUE_BUCKETS",
    "SEED_RT_SPAN_CONCERN_MIN",
    "SELECTED_APEX_IN_WINDOW_MIN",
    "SELECTED_APEX_OVERLAY_PADDING_MIN",
    "TRACE_DISCOVERY_JOIN_COLUMNS",
    "TRACE_REQUIRED_COLUMNS",
    "ZERO_TRACE_INSIDE_WINDOW_FRACTION_MIN",
    "_apex_aware_queue_fields",
    "_backfill_seed_rows_by_family",
    "_detail_fields",
    "_format_value",
    "_load_discovery_candidate",
    "_read_csv",
    "_read_tsv",
    "_seed_aware_queue_fields",
    "_summary_fields",
    "_trace_summary_path",
    "_write_markdown",
    "_write_tsv",
    "build_audit",
    "main",
    "write_outputs",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = build_audit(
            review_candidates_tsv=args.review_candidates_tsv,
            alignment_dir=args.alignment_dir,
            overlay_dir=args.overlay_dir,
            discovery_dir=args.discovery_dir,
            backfill_seed_audit_tsv=args.backfill_seed_audit_tsv,
        )
        write_outputs(args.output_dir, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"low MS1 assessable coverage audit: {args.output_dir}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify low_ms1_assessable_coverage_review families as RT/window, "
            "single-center XIC, or primary-backfill support issues."
        ),
    )
    parser.add_argument("--review-candidates-tsv", required=True, type=Path)
    parser.add_argument("--alignment-dir", required=True, type=Path)
    parser.add_argument("--overlay-dir", required=True, type=Path)
    parser.add_argument("--discovery-dir", type=Path)
    parser.add_argument("--backfill-seed-audit-tsv", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
