"""Write a diagnostic-only MS1+RT shadow policy report for backfill cells."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.diagnostics.backfill_shadow_policy import (
    run_backfill_shadow_policy_report,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        matrix_tsv = _default_optional_path(
            args.alignment_matrix_tsv,
            args.alignment_dir / "alignment_matrix.tsv",
        )
        outputs = run_backfill_shadow_policy_report(
            alignment_cells_tsv=args.alignment_dir / "alignment_cells.tsv",
            alignment_matrix_tsv=matrix_tsv,
            retained_gate_tsv=args.retained_gate_tsv,
            overlay_batch_summary_tsvs=tuple(args.overlay_batch_summary_tsv),
            output_dir=args.output_dir,
            source_run_id=args.source_run_id,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"backfill shadow policy cells TSV: {outputs.tsv}")
    print(f"backfill shadow policy summary JSON: {outputs.json}")
    print(f"backfill shadow policy HTML: {outputs.html}")
    return 0


def _default_optional_path(explicit: Path | None, default: Path) -> Path | None:
    if explicit is not None:
        return explicit
    return default if default.exists() else None


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment-dir",
        type=Path,
        required=True,
        help="Alignment output directory containing alignment_cells.tsv.",
    )
    parser.add_argument(
        "--retained-gate-tsv",
        type=Path,
        required=True,
        help="alignment_retained_backfill_evidence_gate.tsv from retained gate.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for backfill shadow policy TSV/JSON/HTML.",
    )
    parser.add_argument(
        "--alignment-matrix-tsv",
        type=Path,
        help="Optional alignment_matrix.tsv path used only for source hashing.",
    )
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        action="append",
        type=Path,
        default=[],
        help=(
            "Optional family_ms1_overlay_batch_summary.tsv. Repeat to merge "
            "multiple overlay review batches and expose own-max metrics."
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
