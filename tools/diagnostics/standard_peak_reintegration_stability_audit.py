"""Audit standard-peak reintegration stability from activation scope rows."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.standard_peak_reintegration_stability_audit import (
    DEFAULT_EXPECTED_WINDOW_PADDING_MIN,
    audit_reintegration_stability,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = audit_reintegration_stability(
            activation_scope_audit_tsv=args.activation_scope_audit_tsv,
            output_dir=args.output_dir,
            source_run_id=args.source_run_id,
            expected_window_padding_min=args.expected_window_padding_min,
            max_rows=args.max_rows,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Reintegration stability summary JSON: {outputs.summary_json}")
    print(f"Reintegration stability audit TSV: {outputs.audit_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--activation-scope-audit-tsv",
        type=Path,
        required=True,
        help="activation_high_signal_clean_scope_audit.tsv from scope audit.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--expected-window-padding-min",
        type=float,
        default=DEFAULT_EXPECTED_WINDOW_PADDING_MIN,
        help="Padding around the stored reference boundary for bounded reintegration.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional row cap for probes; omit for the full audit.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
