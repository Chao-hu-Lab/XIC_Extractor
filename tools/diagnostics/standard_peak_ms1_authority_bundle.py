"""Build a standard-peak MS1 product-authority candidate bundle."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.standard_peak_ms1_authority_bundle import (
    AUTHORITY_MODE_MANUAL_ORACLE,
    AUTHORITY_MODES,
    run_standard_peak_ms1_authority_bundle,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_standard_peak_ms1_authority_bundle(
            standard_peak_gate_tsv=args.standard_peak_gate_tsv,
            overlay_batch_summary_tsv=args.overlay_batch_summary_tsv,
            output_dir=args.output_dir,
            authority_source=args.authority_source,
            authority_mode=args.authority_mode,
            min_anchor_own_max_shape_similarity=(
                args.min_anchor_own_max_shape_similarity
            ),
            selective_shift_cells_tsv=args.selective_shift_cells_tsv,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"MS1 pattern evidence TSV: {outputs.ms1_pattern_evidence_tsv}")
    print(f"MS1 product authority allowlist TSV: {outputs.authority_allowlist_tsv}")
    print(f"Product-authorized MS1 pattern TSV: {outputs.authorized_ms1_pattern_tsv}")
    print(f"MS1 product authority audit TSV: {outputs.authority_audit_tsv}")
    print(f"Summary JSON: {outputs.summary_json}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--standard-peak-gate-tsv",
        type=Path,
        required=True,
        help=(
            "shift_aware_standard_peak_gate_calibration.tsv. In machine-gate "
            "mode, manual label columns may be blank."
        ),
    )
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        type=Path,
        required=True,
        help="family_ms1_overlay_batch_summary.tsv with trace summary/json paths.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for authority candidate bundle outputs.",
    )
    parser.add_argument(
        "--authority-source",
        default=None,
        help=(
            "Authority source written into allowlist and authorized rows. "
            "Defaults to a mode-specific source."
        ),
    )
    parser.add_argument(
        "--authority-mode",
        choices=AUTHORITY_MODES,
        default=AUTHORITY_MODE_MANUAL_ORACLE,
        help=(
            "manual-oracle preserves the reviewed allowlist behavior; "
            "machine-gate authorizes any standard_peak_gate_supported row "
            "after provenance/hash validation."
        ),
    )
    parser.add_argument(
        "--min-anchor-own-max-shape-similarity",
        type=float,
        default=0.5,
        help="Minimum per-cell own-max shape similarity required by authority.",
    )
    parser.add_argument(
        "--selective-shift-cells-tsv",
        type=Path,
        default=None,
        help=(
            "Selective source-family shift-aware cell TSV. Required when "
            "--authority-mode machine-selective-source-gate is used."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
