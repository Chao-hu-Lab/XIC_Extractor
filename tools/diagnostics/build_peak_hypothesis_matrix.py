"""Build a PeakHypothesis-assigned matrix from alignment and sidecar TSVs."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.alignment.shared_peak_identity_explanation import (
    peak_hypothesis_matrix,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_construction(
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            alignment_review_tsv=args.alignment_review_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            peak_hypothesis_selection_tsv=args.peak_hypothesis_selection_tsv,
            output_dir=args.output_dir,
            hypothesis_consistency_tsv=args.hypothesis_consistency_tsv,
            overlay_trace_data_jsons=args.overlay_trace_data_json,
            allow_overwrite_source=args.allow_overwrite_source,
            require_complete_peak_hypothesis_identity=(
                args.require_complete_peak_hypothesis_identity
            ),
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


def run_construction(
    *,
    alignment_matrix_tsv: Path,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    peak_hypothesis_selection_tsv: Path,
    output_dir: Path,
    hypothesis_consistency_tsv: Path | None = None,
    overlay_trace_data_jsons: Sequence[Path] = (),
    allow_overwrite_source: bool = False,
    require_complete_peak_hypothesis_identity: bool = False,
) -> Mapping[str, Path]:
    outputs = peak_hypothesis_matrix.build_peak_hypothesis_matrix_outputs(
        alignment_matrix_tsv=alignment_matrix_tsv,
        alignment_review_tsv=alignment_review_tsv,
        alignment_cells_tsv=alignment_cells_tsv,
        peak_hypothesis_selection_tsv=peak_hypothesis_selection_tsv,
        hypothesis_consistency_tsv=hypothesis_consistency_tsv,
        overlay_trace_data_jsons=overlay_trace_data_jsons,
        output_dir=output_dir,
        allow_overwrite_source=allow_overwrite_source,
        require_complete_peak_hypothesis_identity=(
            require_complete_peak_hypothesis_identity
        ),
    )
    return {
        "alignment_matrix": outputs.matrix_tsv,
        "peak_hypothesis_inventory": outputs.inventory_tsv,
        "peak_hypothesis_cell_assignments": outputs.assignments_tsv,
        "peak_hypothesis_matrix_summary": outputs.summary_tsv,
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-matrix-tsv", type=Path, required=True)
    parser.add_argument("--alignment-review-tsv", type=Path, required=True)
    parser.add_argument("--alignment-cells-tsv", type=Path, required=True)
    parser.add_argument("--peak-hypothesis-selection-tsv", type=Path, required=True)
    parser.add_argument("--hypothesis-consistency-tsv", type=Path)
    parser.add_argument(
        "--overlay-trace-data-json",
        type=Path,
        action="append",
        default=[],
        help=(
            "Optional family_ms1_overlay trace-data JSON with typed mode_windows. "
            "Each mode window with signal is enumerated as an expanded "
            "PeakHypothesis candidate row before matrix output. Untyped or "
            "raw-inferred windows remain review-only and do not make the "
            "canonical row identity ready. Repeatable."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-overwrite-source",
        action="store_true",
        help=(
            "Allow output alignment_matrix.tsv to overwrite the input matrix. "
            "Use only after preserving source artifacts elsewhere."
        ),
    )
    parser.add_argument(
        "--require-complete-peak-hypothesis-identity",
        action="store_true",
        help=(
            "Fail unless matrix construction can emit only explicit "
            "PeakHypothesis row identities without family projection, raw-mode "
            "review-only, hard-blocked, or source-missing blockers."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
