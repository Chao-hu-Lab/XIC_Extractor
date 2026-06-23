"""Build targeted MS1 shape-identity evidence from an own-max trace grid."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.diagnostics.diagnostic_io import (
    optional_float,
    read_tsv_required,
    text_value,
)
from xic_extractor.diagnostics.targeted_ms1_shape_identity import (
    TargetedMs1ShapeCandidate,
    build_targeted_ms1_shape_identity_rows,
    write_targeted_ms1_shape_identity_tsv,
)

SUMMARY_REQUIRED_COLUMNS = (
    "sample",
    "target",
    "paired_istd",
    "candidate_rt_min",
    "group_median_candidate_rt_min",
    "paired_istd_gaussian15_apex_rt_min",
    "source_summary_analyte_current_nl",
)
TRACE_GRID_REQUIRED_COLUMNS = (
    "sample",
    "rt_min",
    "analyte_gaussian15_own_max",
    "group_median_analyte_own_max",
)


@dataclass(frozen=True)
class TargetedMs1ShapeIdentityGridOutputs:
    evidence_tsv: Path


def run_targeted_ms1_shape_identity_from_grid(
    *,
    summary_tsv: Path,
    trace_grid_tsv: Path,
    output_tsv: Path,
    target_window_start_min: float | None = None,
    target_window_end_min: float | None = None,
    min_own_max_similarity: float = 0.80,
) -> TargetedMs1ShapeIdentityGridOutputs:
    summary_rows = read_tsv_required(summary_tsv, SUMMARY_REQUIRED_COLUMNS)
    trace_grid_rows = read_tsv_required(trace_grid_tsv, TRACE_GRID_REQUIRED_COLUMNS)
    candidates = build_candidates_from_own_max_trace_grid(
        summary_rows,
        trace_grid_rows,
        target_window_start_min=target_window_start_min,
        target_window_end_min=target_window_end_min,
    )
    rows = build_targeted_ms1_shape_identity_rows(
        candidates,
        min_own_max_similarity=min_own_max_similarity,
        smooth_points=1,
    )
    write_targeted_ms1_shape_identity_tsv(output_tsv, rows)
    return TargetedMs1ShapeIdentityGridOutputs(evidence_tsv=output_tsv)


def build_candidates_from_own_max_trace_grid(
    summary_rows: Sequence[Mapping[str, str]],
    trace_grid_rows: Sequence[Mapping[str, str]],
    *,
    target_window_start_min: float | None = None,
    target_window_end_min: float | None = None,
) -> tuple[TargetedMs1ShapeCandidate, ...]:
    grid_by_sample = _trace_grid_by_sample(trace_grid_rows)
    candidates: list[TargetedMs1ShapeCandidate] = []
    for row in summary_rows:
        sample = text_value(row.get("sample"))
        if not sample:
            raise ValueError("summary row is missing sample")
        trace = grid_by_sample.get(sample)
        if trace is None:
            raise ValueError(f"{sample}: trace grid rows are missing")
        candidates.append(
            TargetedMs1ShapeCandidate(
                sample_name=sample,
                target_name=text_value(row.get("target")),
                target_role="analyte",
                paired_istd=text_value(row.get("paired_istd")),
                source_row_id=f"{sample}|{text_value(row.get('target'))}",
                candidate_state=text_value(row.get("source_summary_analyte_current_nl")),
                reference_source="group_median_analyte_own_max_trace_grid",
                candidate_rt_min=optional_float(row.get("candidate_rt_min")),
                candidate_rt=trace["rt"],
                candidate_intensity=trace["analyte"],
                reference_rt_min=optional_float(
                    row.get("group_median_candidate_rt_min"),
                ),
                reference_rt=trace["rt"],
                reference_intensity=trace["reference"],
                paired_istd_rt_min=optional_float(
                    row.get("paired_istd_gaussian15_apex_rt_min"),
                ),
                target_window_start_min=target_window_start_min,
                target_window_end_min=target_window_end_min,
            )
        )
    return tuple(candidates)


def _trace_grid_by_sample(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, tuple[float, ...]]]:
    mutable: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"rt": [], "analyte": [], "reference": []},
    )
    for row in rows:
        sample = text_value(row.get("sample"))
        rt = optional_float(row.get("rt_min"))
        analyte = optional_float(row.get("analyte_gaussian15_own_max"))
        reference = optional_float(row.get("group_median_analyte_own_max"))
        if not sample or rt is None or analyte is None or reference is None:
            continue
        mutable[sample]["rt"].append(rt)
        mutable[sample]["analyte"].append(analyte)
        mutable[sample]["reference"].append(reference)
    return {
        sample: {
            "rt": tuple(values["rt"]),
            "analyte": tuple(values["analyte"]),
            "reference": tuple(values["reference"]),
        }
        for sample, values in mutable.items()
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build diagnostic targeted MS1 shape-identity evidence from an "
            "own-max trace grid."
        ),
    )
    parser.add_argument("--summary-tsv", type=Path, required=True)
    parser.add_argument("--trace-grid-tsv", type=Path, required=True)
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--target-window-start-min", type=float)
    parser.add_argument("--target-window-end-min", type=float)
    parser.add_argument("--min-own-max-similarity", type=float, default=0.80)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run_targeted_ms1_shape_identity_from_grid(
        summary_tsv=args.summary_tsv,
        trace_grid_tsv=args.trace_grid_tsv,
        output_tsv=args.output_tsv,
        target_window_start_min=args.target_window_start_min,
        target_window_end_min=args.target_window_end_min,
        min_own_max_similarity=args.min_own_max_similarity,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
