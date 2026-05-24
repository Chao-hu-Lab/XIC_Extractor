"""Anchor-based RT normalization diagnostic for untargeted alignment outputs."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    # Keep `python tools\diagnostics\analyze_rt_normalization_anchors.py` working.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.rt_normalization_anchor_analysis import (
    _build_result,
    _leave_one_anchor_out,
    _summarize_families,
)
from tools.diagnostics.rt_normalization_anchor_loaders import (
    _read_alignment_cells,
    _read_alignment_review,
    _read_anchor_definitions,
    _read_anchor_points,
    _read_optional_injection_order,
)
from tools.diagnostics.rt_normalization_anchor_models import (
    RtNormalizationOutputs,
    RtNormalizationResult,
)
from tools.diagnostics.rt_normalization_anchor_writers import (
    write_rt_normalization_outputs,
)
from xic_extractor.alignment.rt_normalization import (
    apply_anchor_reference_source,
    fit_sample_rt_models,
)

ACTIVE_NEUTRAL_LOSS_DA = 116.0474
ACTIVE_NEUTRAL_LOSS_TOLERANCE_DA = 0.01


def run_rt_normalization_anchor_diagnostic(
    *,
    targeted_workbook: Path,
    alignment_dir: Path,
    output_dir: Path,
    active_neutral_loss_da: float = ACTIVE_NEUTRAL_LOSS_DA,
    active_neutral_loss_tolerance_da: float = ACTIVE_NEUTRAL_LOSS_TOLERANCE_DA,
    reference_source: str = "observed-median",
    model_type: str = "auto",
    anchor_residual_max_min: float = 0.30,
    anchor_slope_min: float = 0.50,
    anchor_slope_max: float = 1.50,
    sample_info: Path | None = None,
    injection_window: int = 4,
    loess_frac: float = 0.25,
    loess_min_neighbors: int = 7,
) -> tuple[RtNormalizationOutputs, RtNormalizationResult]:
    anchors = _read_anchor_definitions(
        targeted_workbook,
        active_neutral_loss_da=active_neutral_loss_da,
        active_neutral_loss_tolerance_da=active_neutral_loss_tolerance_da,
    )
    points = _read_anchor_points(targeted_workbook, anchors)
    injection_order = _read_optional_injection_order(
        sample_info,
        reference_source=reference_source,
    )
    points = apply_anchor_reference_source(
        points,
        reference_source,
        injection_order=injection_order,
        injection_window=injection_window,
        loess_frac=loess_frac,
        loess_min_neighbors=loess_min_neighbors,
    )
    models, residuals, sample_count = fit_sample_rt_models(
        points,
        model_type=model_type,
        anchor_residual_max_min=anchor_residual_max_min,
        anchor_slope_min=anchor_slope_min,
        anchor_slope_max=anchor_slope_max,
    )
    leave_one_out = _leave_one_anchor_out(
        points,
        model_type=model_type,
        anchor_residual_max_min=anchor_residual_max_min,
        anchor_slope_min=anchor_slope_min,
        anchor_slope_max=anchor_slope_max,
    )
    features = _read_alignment_review(alignment_dir / "alignment_review.tsv")
    cells = _read_alignment_cells(alignment_dir / "alignment_cells.tsv")
    families = _summarize_families(
        features,
        cells,
        models,
        residuals,
        anchor_residual_max_min=anchor_residual_max_min,
    )
    result = _build_result(
        reference_source=reference_source,
        model_type=model_type,
        anchor_residual_max_min=anchor_residual_max_min,
        anchor_label_count=len(anchors),
        sample_count=sample_count,
        models=models,
        residuals=residuals,
        families=families,
        leave_one_out=leave_one_out,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = RtNormalizationOutputs(
        summary_tsv=output_dir / "rt_normalization_summary.tsv",
        sample_tsv=output_dir / "rt_normalization_samples.tsv",
        anchor_tsv=output_dir / "rt_normalization_anchors.tsv",
        leave_one_out_tsv=(output_dir / "rt_normalization_leave_one_anchor_out.tsv"),
        family_tsv=output_dir / "rt_normalization_families.tsv",
        json_path=output_dir / "rt_normalization.json",
        markdown_path=output_dir / "rt_normalization.md",
    )
    write_rt_normalization_outputs(outputs, result)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, result = run_rt_normalization_anchor_diagnostic(
            targeted_workbook=args.targeted_workbook.resolve(),
            alignment_dir=args.alignment_dir.resolve(),
            output_dir=args.output_dir.resolve(),
            active_neutral_loss_da=args.active_neutral_loss_da,
            active_neutral_loss_tolerance_da=(args.active_neutral_loss_tolerance_da),
            reference_source=args.reference_source,
            model_type=args.model_type,
            anchor_residual_max_min=args.anchor_residual_max_min,
            anchor_slope_min=args.anchor_slope_min,
            anchor_slope_max=args.anchor_slope_max,
            sample_info=args.sample_info.resolve() if args.sample_info else None,
            injection_window=args.injection_window,
            loess_frac=args.loess_frac,
            loess_min_neighbors=args.loess_min_neighbors,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Sample models TSV: {outputs.sample_tsv}")
    print(f"Anchor residuals TSV: {outputs.anchor_tsv}")
    print(f"Family RT TSV: {outputs.family_tsv}")
    print(f"Diagnostic JSON: {outputs.json_path}")
    print(f"Diagnostic report: {outputs.markdown_path}")
    return 0 if result.overall_status == "PASS" else 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze anchor-based RT normalization for alignment outputs.",
    )
    parser.add_argument("--targeted-workbook", type=Path, required=True)
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--active-neutral-loss-da", type=float, default=116.0474)
    parser.add_argument(
        "--active-neutral-loss-tolerance-da",
        type=float,
        default=0.01,
    )
    parser.add_argument(
        "--reference-source",
        choices=(
            "observed-median",
            "target-window",
            "injection-local-median",
            "injection-loess",
        ),
        default="observed-median",
    )
    parser.add_argument(
        "--model-type",
        choices=("auto", "affine", "piecewise"),
        default="auto",
    )
    parser.add_argument("--anchor-residual-max-min", type=float, default=0.30)
    parser.add_argument("--anchor-slope-min", type=float, default=0.50)
    parser.add_argument("--anchor-slope-max", type=float, default=1.50)
    parser.add_argument("--sample-info", type=Path)
    parser.add_argument("--injection-window", type=int, default=4)
    parser.add_argument("--loess-frac", type=float, default=0.25)
    parser.add_argument("--loess-min-neighbors", type=int, default=7)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
