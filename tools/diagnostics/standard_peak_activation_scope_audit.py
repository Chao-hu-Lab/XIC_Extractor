"""Audit high-signal clean coverage for standard-peak activation writes."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.standard_peak_activation_scope_audit import (
    run_activation_scope_audit,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_activation_scope_audit(
            activation_value_delta_tsv=args.activation_value_delta_tsv,
            shadow_projection_cells_tsv=args.shadow_projection_cells_tsv,
            output_dir=args.output_dir,
            source_run_id=args.source_run_id,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Activation scope audit TSV: {outputs.audit_tsv}")
    print(f"Activation scope summary JSON: {outputs.summary_json}")
    print(
        "Eligible activation value delta TSV: "
        f"{outputs.eligible_activation_value_delta_tsv}",
    )
    print(
        "Narrow expected-diff acceptance JSON: "
        f"{outputs.narrow_expected_diff_acceptance_json}",
    )
    print(
        "Low-scan clean activation value delta TSV: "
        f"{outputs.low_scan_clean_activation_value_delta_tsv}",
    )
    print(
        "Low-scan clean expected-diff acceptance JSON: "
        f"{outputs.low_scan_expected_diff_acceptance_json}",
    )
    print(
        "Low-height clean activation value delta TSV: "
        f"{outputs.low_height_clean_activation_value_delta_tsv}",
    )
    print(
        "Low-height clean diagnostic/candidate-only expected-diff acceptance JSON: "
        f"{outputs.low_height_expected_diff_acceptance_json}",
    )
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation-value-delta-tsv", type=Path, required=True)
    parser.add_argument("--shadow-projection-cells-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
