"""Build a diagnostic-only backfill evidence reconciliation gallery."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.backfill_reconciliation_gallery import (
    run_reconciliation_gallery,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_reconciliation_gallery(
            alignment_review_tsv=args.alignment_review_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            output_dir=args.output_dir,
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            backfill_seed_audit_tsv=args.backfill_seed_audit_tsv,
            overlay_batch_summary_tsvs=tuple(args.overlay_batch_summary_tsv or ()),
            seed_aware_family_tsv=args.seed_aware_family_tsv,
            seed_aware_summary_tsv=args.seed_aware_summary_tsv,
            candidate_gate_tsv=args.candidate_gate_tsv,
            tier2_trace_evidence_tsv=args.tier2_trace_evidence_tsv,
            source_run_id=args.source_run_id or "",
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"backfill evidence reconciliation groups TSV: {outputs.groups_tsv}")
    print(
        "backfill evidence reconciliation representative cells TSV: "
        f"{outputs.representative_cells_tsv}",
    )
    print(f"backfill evidence reconciliation summary JSON: {outputs.summary_json}")
    print(f"backfill evidence reconciliation gallery HTML: {outputs.gallery_html}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment-review-tsv",
        required=True,
        type=Path,
        help="Source alignment_review.tsv.",
    )
    parser.add_argument(
        "--alignment-cells-tsv",
        required=True,
        type=Path,
        help="Source alignment_cells.tsv.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for TSV, JSON, and HTML review outputs.",
    )
    parser.add_argument(
        "--alignment-matrix-tsv",
        type=Path,
        help="Optional alignment_matrix.tsv for matrix inclusion context only.",
    )
    parser.add_argument(
        "--backfill-seed-audit-tsv",
        type=Path,
        help="Optional alignment_owner_backfill_seed_audit.tsv.",
    )
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        action="append",
        type=Path,
        help="Optional family/seed overlay batch summary TSV; repeatable.",
    )
    parser.add_argument(
        "--seed-aware-family-tsv",
        type=Path,
        help="Optional seed_aware_backfill_review_families.tsv.",
    )
    parser.add_argument(
        "--seed-aware-summary-tsv",
        type=Path,
        help="Optional seed_aware_backfill_review_summary.tsv.",
    )
    parser.add_argument(
        "--candidate-gate-tsv",
        type=Path,
        help="Optional alignment_production_candidate_gate.tsv.",
    )
    parser.add_argument(
        "--tier2-trace-evidence-tsv",
        type=Path,
        help="Optional alignment_tier2_trace_evidence.tsv for provenance display.",
    )
    parser.add_argument(
        "--source-run-id",
        help="Optional run label displayed as provenance only.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
