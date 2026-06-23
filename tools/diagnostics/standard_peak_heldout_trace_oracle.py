"""Build a standard-peak held-out trace reintegration oracle packet."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.standard_peak_heldout_trace_oracle import (
    DEFAULT_EXPECTED_WINDOW_PADDING_MIN,
    FULL_TRACE_REINTEGRATION_MODE,
    HIGH_SIGNAL_CLEAN_SCOPE,
    SUPPORTED_OBSERVED_REINTEGRATION_MODES,
    SUPPORTED_TARGET_SHAPE_CLASSES,
    run_heldout_trace_oracle,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_heldout_trace_oracle(
            alignment_backfill_cell_evidence_tsv=(
                args.alignment_backfill_cell_evidence_tsv
            ),
            trace_root=args.trace_root,
            output_dir=args.output_dir,
            source_run_id=args.source_run_id,
            target_shape_class=args.target_shape_class,
            observed_reintegration_mode=args.observed_reintegration_mode,
            expected_window_padding_min=args.expected_window_padding_min,
            max_cases=args.max_cases,
            max_cases_per_family=args.max_cases_per_family,
            reintegration_stability_audit_tsv=args.reintegration_stability_audit_tsv,
            activation_scope_audit_tsv=args.activation_scope_audit_tsv,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Held-out trace oracle summary JSON: {outputs.summary_json}")
    print(f"Held-out trace oracle manifest TSV: {outputs.manifest_tsv}")
    print(f"Held-out observed results TSV: {outputs.observed_results_tsv}")
    print(f"Held-out oracle results TSV: {outputs.oracle_results_tsv}")
    print(f"Full eligible pool TSV: {outputs.full_eligible_pool_tsv}")
    return 0 if outputs.status == "pass" else 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment-backfill-cell-evidence-tsv",
        type=Path,
        required=True,
        help="alignment_backfill_cell_evidence.tsv from the source alignment run.",
    )
    parser.add_argument(
        "--trace-root",
        type=Path,
        required=True,
        help="Root directory containing *_trace_data.json artifacts.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--target-shape-class",
        choices=SUPPORTED_TARGET_SHAPE_CLASSES,
        default=HIGH_SIGNAL_CLEAN_SCOPE,
    )
    parser.add_argument(
        "--observed-reintegration-mode",
        choices=SUPPORTED_OBSERVED_REINTEGRATION_MODES,
        default=FULL_TRACE_REINTEGRATION_MODE,
        help=(
            "How to reintegrate stored trace arrays for observed heldout results. "
            "Default full_trace preserves existing oracle behavior; "
            "expected_window_bounded clips to oracle_start/end plus padding."
        ),
    )
    parser.add_argument(
        "--expected-window-padding-min",
        type=float,
        default=DEFAULT_EXPECTED_WINDOW_PADDING_MIN,
        help=(
            "RT padding used only by --observed-reintegration-mode "
            "expected_window_bounded."
        ),
    )
    parser.add_argument("--max-cases", type=int, default=20)
    parser.add_argument("--max-cases-per-family", type=int, default=1)
    parser.add_argument(
        "--reintegration-stability-audit-tsv",
        type=Path,
        default=None,
        help=(
            "Required only for the low-height reintegration-stable candidate "
            "family target scope."
        ),
    )
    parser.add_argument(
        "--activation-scope-audit-tsv",
        type=Path,
        default=None,
        help=(
            "Matching activation_high_signal_clean_scope_audit.tsv used to "
            "classify low-height rows for the reintegration-stable candidate "
            "family target scope."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
