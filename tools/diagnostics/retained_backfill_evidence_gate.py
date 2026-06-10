"""Write a diagnostic-only evidence gate for product-retained backfill rows."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.diagnostics.retained_backfill_evidence_gate import (
    run_retained_backfill_evidence_gate,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        output_dir = args.output_dir or args.alignment_dir
        cell_evidence_tsv = _default_cell_evidence_path(
            args.alignment_cell_evidence_tsv,
            args.alignment_dir,
        )
        seed_audit_tsv = _default_optional_path(
            args.backfill_seed_audit_tsv,
            args.alignment_dir / "alignment_owner_backfill_seed_audit.tsv",
        )
        outputs = run_retained_backfill_evidence_gate(
            alignment_review_tsv=args.alignment_dir / "alignment_review.tsv",
            alignment_cells_tsv=cell_evidence_tsv,
            alignment_matrix_tsv=args.alignment_dir / "alignment_matrix.tsv",
            backfill_seed_audit_tsv=seed_audit_tsv,
            overlay_batch_summary_tsvs=tuple(args.overlay_batch_summary_tsv),
            output_dir=output_dir,
            source_run_id=args.source_run_id,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"retained backfill evidence gate TSV: {outputs.tsv}")
    print(f"retained backfill evidence gate JSON: {outputs.json}")
    print(
        "retained backfill missing overlay queue TSV: "
        f"{outputs.missing_overlay_queue_tsv}",
    )
    print(
        "retained backfill review overlay queue TSV: "
        f"{outputs.review_overlay_queue_tsv}",
    )
    return 0


def _default_optional_path(explicit: Path | None, default: Path) -> Path | None:
    if explicit is not None:
        return explicit
    return default if default.exists() else None


def _default_cell_evidence_path(explicit: Path | None, alignment_dir: Path) -> Path:
    if explicit is not None:
        return explicit
    light_path = alignment_dir / "alignment_backfill_cell_evidence.tsv"
    if light_path.exists():
        return light_path
    return alignment_dir / "alignment_cells.tsv"


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment-dir",
        type=Path,
        required=True,
        help=(
            "Alignment output directory containing alignment_review.tsv, "
            "alignment_matrix.tsv, and either alignment_backfill_cell_evidence.tsv "
            "or alignment_cells.tsv."
        ),
    )
    parser.add_argument(
        "--alignment-cell-evidence-tsv",
        type=Path,
        help=(
            "Optional compact alignment_backfill_cell_evidence.tsv or legacy "
            "alignment_cells.tsv. Defaults to alignment_backfill_cell_evidence.tsv "
            "in --alignment-dir when present, otherwise alignment_cells.tsv."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Output directory for alignment_retained_backfill_evidence_gate.tsv "
            "and alignment_retained_backfill_evidence_gate.json. Defaults to "
            "--alignment-dir."
        ),
    )
    parser.add_argument(
        "--backfill-seed-audit-tsv",
        type=Path,
        help=(
            "Optional alignment_owner_backfill_seed_audit.tsv. Defaults to the "
            "file in --alignment-dir when present."
        ),
    )
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        action="append",
        type=Path,
        default=[],
        help=(
            "Optional family_ms1_overlay_batch_summary.tsv. Repeat to merge "
            "multiple overlay review batches."
        ),
    )
    parser.add_argument(
        "--source-run-id",
        default="",
        help="Optional source run label written to the JSON summary.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
