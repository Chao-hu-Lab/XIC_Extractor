"""Convert backfill PeakHypothesis promotion sidecars to activation inputs."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics import backfill_peakhypothesis_activation_bridge
from xic_extractor.diagnostics.diagnostic_io import read_tsv_required


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        promotion_rows = read_tsv_required(
            args.promotion_cells_tsv,
            backfill_peakhypothesis_activation_bridge.PROMOTION_INPUT_REQUIRED_COLUMNS,
        )
        normal_peak_decision_rows = (
            read_tsv_required(
                args.normal_peak_decisions_tsv,
                (
                    backfill_peakhypothesis_activation_bridge
                    .NORMAL_PEAK_DECISION_INPUT_REQUIRED_COLUMNS
                ),
            )
            if args.normal_peak_decisions_tsv is not None
            else ()
        )
        public_matrix_rows = _read_optional_tsv(args.alignment_matrix_tsv)
        matrix_identity_rows = _read_optional_tsv(args.alignment_matrix_identity_tsv)
        index = backfill_peakhypothesis_activation_bridge.build_activation_bridge(
            promotion_rows,
            public_matrix_rows=public_matrix_rows,
            matrix_identity_rows=matrix_identity_rows,
            normal_peak_decision_rows=normal_peak_decision_rows,
            source_run_id=args.source_run_id,
        )
        outputs = (
            backfill_peakhypothesis_activation_bridge.write_activation_bridge_outputs(
                args.output_dir,
                index,
            )
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Activation decisions TSV: {outputs.activation_decisions_tsv}")
    print(f"Activation acceptance TSV: {outputs.activation_acceptance_tsv}")
    print(f"Activation matrix preflight TSV: {outputs.activation_matrix_preflight_tsv}")
    print(f"Activation bridge summary JSON: {outputs.summary_json}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promotion-cells-tsv", type=Path, required=True)
    parser.add_argument("--normal-peak-decisions-tsv", type=Path)
    parser.add_argument(
        "--alignment-matrix-tsv",
        type=Path,
        help=(
            "Optional public matrix for preflight cross-check. Rows already "
            "written in this matrix are not converted into activation decisions."
        ),
    )
    parser.add_argument(
        "--alignment-matrix-identity-tsv",
        type=Path,
        help=(
            "Required with public Mz/RT matrices when --alignment-matrix-tsv is "
            "provided."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    return parser.parse_args(argv)


def _read_optional_tsv(path: Path | None) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle, delimiter="\t"))


if __name__ == "__main__":
    raise SystemExit(main())
