"""Audit targeted and untargeted shared evidence semantics."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.evidence_spine_consistency_analysis import (
    _best_alignment_match,
    _build_rows,
    _consistency_row,
    _format_counter,
    _format_rt_window,
    _mismatch_reasons,
    _ppm,
    _ratio,
    _summarize,
)
from tools.diagnostics.evidence_spine_consistency_io import (
    _bool_value,
    _optional_float,
    _optional_int,
    _read_alignment_cells,
    _read_required_tsv,
    _read_target_mz,
    _read_targeted_candidates,
    _read_targeted_shadows,
)
from tools.diagnostics.evidence_spine_consistency_models import (
    DEFAULT_FOCUS_LABELS,
    ROW_FIELDS,
    SUMMARY_FIELDS,
    AlignmentCell,
    ConsistencyRow,
    ConsistencySummary,
    EvidenceSpineConsistencyOutputs,
    EvidenceSpineConsistencyResult,
    TargetedCandidate,
    TargetedShadow,
)
from tools.diagnostics.evidence_spine_consistency_writers import (
    _fmt,
    _format_value,
    _write_markdown,
    _write_outputs,
    _write_tsv,
)

__all__ = [
    "DEFAULT_FOCUS_LABELS",
    "ROW_FIELDS",
    "SUMMARY_FIELDS",
    "AlignmentCell",
    "ConsistencyRow",
    "ConsistencySummary",
    "EvidenceSpineConsistencyOutputs",
    "EvidenceSpineConsistencyResult",
    "TargetedCandidate",
    "TargetedShadow",
    "_best_alignment_match",
    "_bool_value",
    "_build_rows",
    "_consistency_row",
    "_fmt",
    "_format_counter",
    "_format_rt_window",
    "_format_value",
    "_mismatch_reasons",
    "_optional_float",
    "_optional_int",
    "_parse_args",
    "_ppm",
    "_ratio",
    "_read_alignment_cells",
    "_read_required_tsv",
    "_read_target_mz",
    "_read_targeted_candidates",
    "_read_targeted_shadows",
    "_summarize",
    "_write_markdown",
    "_write_outputs",
    "_write_tsv",
    "main",
    "run_evidence_spine_consistency",
]


def run_evidence_spine_consistency(
    *,
    targeted_dir: Path,
    alignment_dir: Path,
    output_dir: Path,
    target_labels: Sequence[str] = DEFAULT_FOCUS_LABELS,
    include_istd: bool = True,
    match_ppm: float = 20.0,
    match_rt_min: float = 0.75,
) -> tuple[EvidenceSpineConsistencyOutputs, EvidenceSpineConsistencyResult]:
    targeted = _read_targeted_candidates(targeted_dir / "peak_candidates.tsv")
    target_mz = _read_target_mz(targeted_dir / "peak_candidate_boundaries.tsv")
    shadows = _read_targeted_shadows(
        targeted_dir / "peak_region_selection_shadow_summary.tsv"
    )
    cells = _read_alignment_cells(alignment_dir / "alignment_cells.tsv")
    rows = _build_rows(
        targeted,
        target_mz=target_mz,
        shadows=shadows,
        alignment_cells=cells,
        target_labels=tuple(target_labels),
        include_istd=include_istd,
        match_ppm=match_ppm,
        match_rt_min=match_rt_min,
    )
    result = EvidenceSpineConsistencyResult(
        summary=_summarize(rows, target_labels=tuple(target_labels)),
        rows=tuple(rows),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = EvidenceSpineConsistencyOutputs(
        summary_tsv=output_dir / "evidence_spine_consistency_summary.tsv",
        rows_tsv=output_dir / "evidence_spine_consistency_rows.tsv",
        json_path=output_dir / "evidence_spine_consistency.json",
        markdown_path=output_dir / "evidence_spine_consistency.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare targeted candidate and untargeted alignment evidence.",
    )
    parser.add_argument("--targeted-dir", type=Path, required=True)
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--target-label",
        action="append",
        default=[],
        help="Target label to include. Defaults to key high-value targets.",
    )
    parser.add_argument(
        "--exclude-istd",
        action="store_true",
        help="Do not automatically include all selected ISTD candidates.",
    )
    parser.add_argument("--match-ppm", type=float, default=20.0)
    parser.add_argument("--match-rt-min", type=float, default=0.75)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    labels = tuple(args.target_label) or DEFAULT_FOCUS_LABELS
    try:
        outputs, _result = run_evidence_spine_consistency(
            targeted_dir=args.targeted_dir,
            alignment_dir=args.alignment_dir,
            output_dir=args.output_dir,
            target_labels=labels,
            include_istd=not args.exclude_istd,
            match_ppm=args.match_ppm,
            match_rt_min=args.match_rt_min,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Consistency JSON: {outputs.json_path}")
    print(f"Consistency report: {outputs.markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
