"""Gate reviewed PeakHypothesis backfill promotions against 85RAW artifacts."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics import backfill_peakhypothesis_raw85_slice_gate


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        index = backfill_peakhypothesis_raw85_slice_gate.build_raw85_slice_gate(
            promotion_rows=_read_tsv(args.promotion_cells_tsv),
            raw85_review_rows=_read_tsv(args.raw85_alignment_review_tsv),
            raw85_cell_rows=_read_tsv(args.raw85_alignment_cells_tsv),
            source_run_id=args.source_run_id,
        )
        outputs = (
            backfill_peakhypothesis_raw85_slice_gate.write_raw85_slice_gate_outputs(
                args.output_dir,
                index,
            )
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"85RAW slice gate TSV: {outputs.cells_tsv}")
    print(f"85RAW slice gate summary JSON: {outputs.summary_json}")
    return 0 if index.summary["gate_status"] == "pass" else 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promotion-cells-tsv", type=Path, required=True)
    parser.add_argument("--raw85-alignment-review-tsv", type=Path, required=True)
    parser.add_argument("--raw85-alignment-cells-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    return parser.parse_args(argv)


def _read_tsv(path: Path) -> tuple[dict[str, str], ...]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle, delimiter="\t"))


if __name__ == "__main__":
    raise SystemExit(main())
