"""Run standard-peak backfill productization end to end."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.standard_peak_backfill_productization import (
    run_standard_peak_backfill_productization,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_standard_peak_backfill_productization(
            shadow_projection_cells_tsv=args.shadow_projection_cells_tsv,
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            alignment_matrix_identity_tsv=args.alignment_matrix_identity_tsv,
            alignment_review_tsv=args.alignment_review_tsv,
            output_dir=args.output_dir,
            source_run_id=args.source_run_id,
            write_gallery=args.write_gallery,
            alignment_cells_tsv=args.alignment_cells_tsv,
            backfill_seed_audit_tsv=args.backfill_seed_audit_tsv,
            overlay_batch_summary_tsvs=tuple(args.overlay_batch_summary_tsv or ()),
            shift_aware_standard_peak_gate_tsvs=tuple(
                args.shift_aware_standard_peak_gate_tsv or (),
            ),
            retained_backfill_gate_tsv=args.retained_backfill_gate_tsv,
            gallery_output_dir=args.gallery_output_dir,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Standard-peak productization summary TSV: {outputs.summary_tsv}")
    print(f"Standard-peak productization summary JSON: {outputs.summary_json}")
    print(
        "Standard-peak activation decisions TSV: "
        f"{outputs.activation_inputs.decisions_tsv}",
    )
    if outputs.activated_matrix_tsv is not None:
        print(f"Activated matrix TSV: {outputs.activated_matrix_tsv}")
    if outputs.activation_value_delta_tsv is not None:
        print(f"Activation value delta TSV: {outputs.activation_value_delta_tsv}")
    if outputs.reconciliation_gallery_html is not None:
        print(
            "Activation-synced reconciliation gallery HTML: "
            f"{outputs.reconciliation_gallery_html}",
        )
    return 0 if outputs.status == "pass" else 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shadow-projection-cells-tsv",
        type=Path,
        required=True,
        help="shadow_production_projection_cells.tsv.",
    )
    parser.add_argument("--alignment-matrix-tsv", type=Path, required=True)
    parser.add_argument(
        "--alignment-matrix-identity-tsv",
        type=Path,
        required=True,
    )
    parser.add_argument("--alignment-review-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--write-gallery",
        action="store_true",
        help=(
            "Also render an activation-synced reconciliation gallery. Requires "
            "--alignment-cells-tsv."
        ),
    )
    parser.add_argument(
        "--alignment-cells-tsv",
        type=Path,
        help="Cell evidence TSV for optional gallery rendering.",
    )
    parser.add_argument(
        "--backfill-seed-audit-tsv",
        type=Path,
        help="Optional alignment_owner_backfill_seed_audit.tsv for gallery.",
    )
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        action="append",
        type=Path,
        help="Optional family/seed overlay batch summary TSV; repeatable.",
    )
    parser.add_argument(
        "--shift-aware-standard-peak-gate-tsv",
        action="append",
        type=Path,
        help=(
            "Optional shift_aware_standard_peak_gate_calibration.tsv for "
            "gallery evidence display; repeatable."
        ),
    )
    parser.add_argument(
        "--retained-backfill-evidence-gate-tsv",
        dest="retained_backfill_gate_tsv",
        type=Path,
        help="Optional alignment_retained_backfill_evidence_gate.tsv for gallery.",
    )
    parser.add_argument(
        "--gallery-output-dir",
        type=Path,
        help="Optional output directory for the synced gallery.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
