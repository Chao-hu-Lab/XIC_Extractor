"""Render MS1 overlay evidence for one alignment feature family."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.family_ms1_overlay_evidence import (
    _apex_aligned_normalized_trace,
    _apex_aligned_shape_similarity,
    _gaussian_smooth_values,
    _global_trace_apex_delta,
    _local_to_global_max_ratio,
    _local_window_peak,
    _median_value,
    build_family_ms1_evidence_summary,
)
from tools.diagnostics.family_ms1_overlay_models import (
    APEX_ALIGN_HALF_WINDOW_MIN,
    GLOBAL_APEX_CONFLICT_DELTA_MIN,
    REQUIRED_ALIGNMENT_COLUMNS,
    SHAPE_SUPPORT_MIN,
    FamilyCell,
    FamilyMs1OverlayOutputs,
    TraceOverlayRow,
)

PLOT_GAUSSIAN_SMOOTH_POINTS = 15
DETECTED_COLOR = "#D55E00"
RESCUED_COLOR = "#0072B2"
QC_COLOR = "#009E73"
OTHER_TRACE_COLOR = "0.65"
DETECTED_MEDIAN_COLOR = "#A04000"
RESCUED_MEDIAN_COLOR = "#005A8D"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    cells = load_family_cells(args.alignment_cells, args.family_id)
    rows = extract_family_trace_rows(
        cells=cells,
        raw_dir=args.raw_dir,
        dll_dir=args.dll_dir,
        mz=args.mz,
        rt_min=args.rt_min,
        rt_max=args.rt_max,
        ppm=args.ppm,
        max_highlight_rescued=args.max_highlight_rescued,
    )
    center_rt = (
        args.family_center_rt
        if args.family_center_rt is not None
        else _median_value(row.cell_apex_rt for row in rows)
    )
    prefix = args.output_prefix or f"{args.family_id.lower()}_ms1_overlay"
    outputs = write_family_ms1_overlay_outputs(
        rows=rows,
        output_dir=args.output_dir,
        output_prefix=prefix,
        family_id=args.family_id,
        mz=args.mz,
        ppm=args.ppm,
        rt_min=args.rt_min,
        rt_max=args.rt_max,
        family_center_rt=center_rt,
    )
    print(f"MS1 overlay PNG: {outputs.png_path}")
    print(f"MS1 overlay PDF: {outputs.pdf_path}")
    print(f"Trace summary TSV: {outputs.summary_tsv}")
    print(f"Trace data JSON: {outputs.trace_data_json}")
    evidence_summary = build_family_ms1_evidence_summary(rows)
    print(f"Family MS1 verdict: {evidence_summary['family_verdict']}")
    return 0


def load_family_cells(alignment_cells: Path, family_id: str) -> list[FamilyCell]:
    with alignment_cells.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        _require_columns(reader.fieldnames or (), REQUIRED_ALIGNMENT_COLUMNS)
        rows = [
            FamilyCell(
                sample_stem=row["sample_stem"],
                status=row["status"],
                area=_parse_float(row.get("area")),
                height=_parse_float(row.get("height")),
                apex_rt=_parse_float(row.get("apex_rt")),
                peak_start_rt=_parse_float(row.get("peak_start_rt")),
                peak_end_rt=_parse_float(row.get("peak_end_rt")),
                region_shadow_verdict=row.get("region_shadow_verdict", ""),
                source_candidate_id=row.get("source_candidate_id", ""),
            )
            for row in reader
            if row.get("feature_family_id") == family_id
        ]
    if not rows:
        raise ValueError(f"No alignment cells found for family `{family_id}`")
    return sorted(rows, key=lambda row: row.area or 0.0, reverse=True)


def extract_family_trace_rows(
    *,
    cells: Sequence[FamilyCell],
    raw_dir: Path,
    dll_dir: Path,
    mz: float,
    rt_min: float,
    rt_max: float,
    ppm: float,
    max_highlight_rescued: int = 8,
) -> list[TraceOverlayRow]:
    from xic_extractor.raw_reader import open_raw
    from xic_extractor.xic_models import XICRequest

    groups = assign_highlight_groups(
        cells,
        max_highlight_rescued=max_highlight_rescued,
    )
    rows: list[TraceOverlayRow] = []
    for cell in cells:
        raw_path = raw_dir / f"{cell.sample_stem}.raw"
        if not raw_path.is_file():
            raise FileNotFoundError(f"RAW file not found: {raw_path}")
        with open_raw(raw_path, dll_dir) as raw:
            trace = raw.extract_xic_many(
                (XICRequest(mz=mz, rt_min=rt_min, rt_max=rt_max, ppm_tol=ppm),)
            )[0]
        rows.append(
            trace_row_from_arrays(
                cell,
                groups[cell.sample_stem],
                trace.rt,
                trace.intensity,
            )
        )
    return rows


def assign_highlight_groups(
    cells: Sequence[FamilyCell],
    *,
    max_highlight_rescued: int = 8,
) -> dict[str, str]:
    detected = {cell.sample_stem for cell in cells if cell.status == "detected"}
    top_rescued = {
        cell.sample_stem
        for cell in sorted(
            (
                cell
                for cell in cells
                if cell.status == "rescued" and "QC" not in cell.sample_stem
            ),
            key=lambda item: item.area or 0.0,
            reverse=True,
        )[:max(0, max_highlight_rescued)]
    }
    groups: dict[str, str] = {}
    for cell in cells:
        if cell.sample_stem in detected:
            groups[cell.sample_stem] = "detected_seed"
        elif "QC" in cell.sample_stem:
            groups[cell.sample_stem] = "pooled_qc"
        elif cell.sample_stem in top_rescued:
            groups[cell.sample_stem] = "top_rescued_ms1_area"
        else:
            groups[cell.sample_stem] = "rescued_other"
    return groups


def trace_row_from_arrays(
    cell: FamilyCell,
    group: str,
    rt: object,
    intensity: object,
) -> TraceOverlayRow:
    rt_array = np.asarray(rt, dtype=float)
    intensity_array = np.asarray(intensity, dtype=float)
    if rt_array.ndim != 1 or intensity_array.ndim != 1:
        raise ValueError("Trace arrays must be one-dimensional")
    if rt_array.shape != intensity_array.shape:
        raise ValueError("Trace RT and intensity arrays must have equal length")
    max_intensity = float(np.max(intensity_array)) if intensity_array.size else 0.0
    if intensity_array.size and max_intensity > 0:
        apex_index = int(np.argmax(intensity_array))
        trace_apex_rt: float | None = float(rt_array[apex_index])
    else:
        trace_apex_rt = None
    return TraceOverlayRow(
        sample_stem=cell.sample_stem,
        status=cell.status,
        group=group,
        cell_area=cell.area,
        cell_height=cell.height,
        cell_apex_rt=cell.apex_rt,
        cell_start_rt=cell.peak_start_rt,
        cell_end_rt=cell.peak_end_rt,
        trace_max_intensity=max_intensity,
        trace_apex_rt=trace_apex_rt,
        region_shadow_verdict=cell.region_shadow_verdict,
        source_candidate_id=cell.source_candidate_id,
        rt=tuple(float(value) for value in rt_array),
        intensity=tuple(float(value) for value in intensity_array),
    )


def write_family_ms1_overlay_outputs(
    *,
    rows: Sequence[TraceOverlayRow],
    output_dir: Path,
    output_prefix: str,
    family_id: str,
    mz: float,
    ppm: float,
    rt_min: float,
    rt_max: float,
    family_center_rt: float | None,
) -> FamilyMs1OverlayOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_tsv = output_dir / f"{output_prefix}_trace_summary.tsv"
    trace_data_json = output_dir / f"{output_prefix}_trace_data.json"
    png_path = output_dir / f"{output_prefix}.png"
    pdf_path = output_dir / f"{output_prefix}.pdf"

    _write_summary(summary_tsv, rows)
    _write_trace_data(
        trace_data_json,
        rows=rows,
        family_id=family_id,
        mz=mz,
        ppm=ppm,
        rt_min=rt_min,
        rt_max=rt_max,
        family_center_rt=family_center_rt,
    )
    render_family_ms1_overlay(
        rows=rows,
        png_path=png_path,
        pdf_path=pdf_path,
        family_id=family_id,
        mz=mz,
        ppm=ppm,
        rt_min=rt_min,
        rt_max=rt_max,
        family_center_rt=family_center_rt,
    )
    return FamilyMs1OverlayOutputs(
        png_path=png_path,
        pdf_path=pdf_path,
        summary_tsv=summary_tsv,
        trace_data_json=trace_data_json,
    )


def render_family_ms1_overlay(
    *,
    rows: Sequence[TraceOverlayRow],
    png_path: Path,
    pdf_path: Path,
    family_id: str,
    mz: float,
    ppm: float,
    rt_min: float,
    rt_max: float,
    family_center_rt: float | None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    detected = [row for row in rows if row.group == "detected_seed"]
    top_rescued = [row for row in rows if row.group == "top_rescued_ms1_area"]
    rescued = [row for row in rows if row.status == "rescued"]

    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "figure.titlesize": 13,
        }
    )
    fig, axes = plt.subplot_mosaic(
        [
            ["aligned", "rt", "area"],
            ["norm", "raw", "shape"],
            ["legend", "legend", "legend"],
        ],
        figsize=(18, 10),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.0, 1.0, 0.12]},
    )
    _plot_normalized_overlay(
        axes["norm"],
        rows,
        family_center_rt=family_center_rt,
        rt_min=rt_min,
        rt_max=rt_max,
    )
    _plot_raw_highlights(
        axes["raw"],
        [*detected, *top_rescued],
        family_center_rt=family_center_rt,
        rt_min=rt_min,
        rt_max=rt_max,
    )
    shape_similarity = _apex_aligned_shape_similarity(rows)
    _plot_apex_aligned_overlay(axes["aligned"], rows)
    _plot_area_distribution(axes["area"], rows)
    _plot_trace_apex_delta_distribution(
        axes["rt"],
        detected,
        rescued,
    )
    _plot_shape_similarity(axes["shape"], rows, shape_similarity)
    _plot_unified_legend(axes["legend"])

    fig.suptitle(
        (
            f"{family_id} MS1 evidence review: m/z {mz:g} +/-{ppm:g} ppm\n"
            f"{len(rows)} traces; {len(detected)} detected NL seeds; "
            f"{len(rescued)} rescued MS1 backfill cells"
        ),
    )
    fig.savefig(png_path, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_normalized_overlay(
    ax: Any,
    rows: Sequence[TraceOverlayRow],
    *,
    family_center_rt: float | None,
    rt_min: float,
    rt_max: float,
) -> None:
    for row in rows:
        rt = np.asarray(row.rt, dtype=float)
        intensity = _gaussian_smooth(
            np.asarray(row.intensity, dtype=float),
            points=PLOT_GAUSSIAN_SMOOTH_POINTS,
        )
        if rt.size == 0 or row.trace_max_intensity <= 0:
            continue
        max_intensity = float(np.max(intensity)) if intensity.size else 0.0
        if max_intensity <= 0:
            continue
        color, alpha, line_width, zorder = _line_style(row.group)
        ax.plot(
            rt,
            intensity / max_intensity,
            color=color,
            alpha=alpha,
            lw=line_width,
            zorder=zorder,
        )
    _plot_group_median_trace(
        ax,
        rows,
        group="detected_seed",
        color=DETECTED_MEDIAN_COLOR,
        label="detected median",
        rt_min=rt_min,
        rt_max=rt_max,
    )
    _plot_group_median_trace(
        ax,
        rows,
        group="rescued",
        color=RESCUED_MEDIAN_COLOR,
        label="rescued median",
        rt_min=rt_min,
        rt_max=rt_max,
        linestyle="--",
    )
    _draw_center_rt(ax, family_center_rt)
    ax.set_title("Absolute RT context: each trace scaled to its own max")
    ax.set_xlabel("RT (min)")
    ax.set_ylabel("Per-trace scaled intensity (0-1; not abundance)")
    ax.set_xlim(rt_min, rt_max)
    ax.set_ylim(-0.03, 1.08)
    ax.grid(True, alpha=0.2)
    _add_panel_note(
        ax,
        "RT/shape context only; compare abundance in raw intensity panel.",
    )


def _plot_raw_highlights(
    ax: Any,
    rows: Sequence[TraceOverlayRow],
    *,
    family_center_rt: float | None,
    rt_min: float,
    rt_max: float,
) -> None:
    labels_seen: set[str] = set()
    for row in rows:
        rt = np.asarray(row.rt, dtype=float)
        intensity = _gaussian_smooth(
            np.asarray(row.intensity, dtype=float),
            points=PLOT_GAUSSIAN_SMOOTH_POINTS,
        )
        if rt.size == 0:
            continue
        if row.group == "detected_seed":
            color, line_width, alpha, label = (
                DETECTED_COLOR,
                1.65,
                0.88,
                "detected NL seed",
            )
        else:
            color, line_width, alpha, label = (
                RESCUED_COLOR,
                1.05,
                0.65,
                "top rescued MS1 area",
            )
        ax.plot(
            rt,
            intensity,
            color=color,
            lw=line_width,
            alpha=alpha,
            label=None if label in labels_seen else label,
        )
        labels_seen.add(label)
    _draw_center_rt(ax, family_center_rt)
    ax.set_title("Raw intensity context: DDA trigger / signal height")
    ax.set_xlabel("RT (min)")
    ax.set_ylabel("Raw MS1 intensity (smoothed)")
    ax.set_xlim(rt_min, rt_max)
    ax.grid(True, alpha=0.2)
    _add_panel_note(
        ax,
        "Use this panel for height differences; strong traces can hide weak peaks.",
    )


def _plot_apex_aligned_overlay(
    ax: Any,
    rows: Sequence[TraceOverlayRow],
) -> None:
    for row in rows:
        rt, normalized = _apex_aligned_normalized_trace(
            row,
            smooth_points=PLOT_GAUSSIAN_SMOOTH_POINTS,
        )
        if rt.size == 0:
            continue
        color, alpha, line_width, zorder = _line_style(row.group)
        ax.plot(
            rt,
            normalized,
            color=color,
            alpha=alpha,
            lw=line_width,
            zorder=zorder,
        )
    _plot_group_median_trace(
        ax,
        rows,
        group="detected_seed",
        color=DETECTED_MEDIAN_COLOR,
        label="detected median",
        rt_min=-APEX_ALIGN_HALF_WINDOW_MIN,
        rt_max=APEX_ALIGN_HALF_WINDOW_MIN,
        align_to_apex=True,
    )
    _plot_group_median_trace(
        ax,
        rows,
        group="rescued",
        color=RESCUED_MEDIAN_COLOR,
        label="rescued median",
        rt_min=-APEX_ALIGN_HALF_WINDOW_MIN,
        rt_max=APEX_ALIGN_HALF_WINDOW_MIN,
        linestyle="--",
        align_to_apex=True,
    )
    ax.axvline(0.0, color="black", lw=1, ls="--", alpha=0.6)
    ax.set_title("Main decision: apex-aligned MS1 shape")
    ax.set_xlabel("RT relative to selected apex (min)")
    ax.set_ylabel("Per-trace scaled intensity (0-1)")
    ax.set_xlim(-APEX_ALIGN_HALF_WINDOW_MIN, APEX_ALIGN_HALF_WINDOW_MIN)
    ax.set_ylim(-0.03, 1.08)
    ax.grid(True, alpha=0.2)


def _add_panel_note(ax: Any, text: str) -> None:
    ax.text(
        0.01,
        0.02,
        text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.5,
        color="0.25",
        bbox={
            "boxstyle": "round,pad=0.22",
            "facecolor": "white",
            "edgecolor": "0.82",
            "alpha": 0.86,
        },
    )


def _plot_unified_legend(ax: Any) -> None:
    from matplotlib.lines import Line2D

    ax.axis("off")
    handles = [
        Line2D([0], [0], color=DETECTED_COLOR, lw=1.9, label="detected NL seed"),
        Line2D(
            [0],
            [0],
            color=RESCUED_COLOR,
            lw=1.25,
            label="top rescued MS1 area",
        ),
        Line2D([0], [0], color=QC_COLOR, lw=0.9, label="pooled QC"),
        Line2D([0], [0], color=OTHER_TRACE_COLOR, lw=0.7, label="other rescued"),
        Line2D(
            [0],
            [0],
            color=DETECTED_MEDIAN_COLOR,
            lw=2.6,
            label="detected median",
        ),
        Line2D(
            [0],
            [0],
            color=RESCUED_MEDIAN_COLOR,
            lw=2.6,
            ls="--",
            label="rescued median",
        ),
        Line2D(
            [0],
            [0],
            color="black",
            lw=1,
            ls="--",
            alpha=0.6,
            label="family center / aligned apex",
        ),
        Line2D(
            [0],
            [0],
            color="0.35",
            lw=1,
            ls=":",
            alpha=0.7,
            label="review threshold",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="center",
        ncol=4,
        frameon=False,
        handlelength=3.0,
        columnspacing=1.8,
    )


def _plot_group_median_trace(
    ax: Any,
    rows: Sequence[TraceOverlayRow],
    *,
    group: str,
    color: str,
    label: str,
    rt_min: float,
    rt_max: float,
    linestyle: str = "-",
    align_to_apex: bool = False,
    smooth_points: int = PLOT_GAUSSIAN_SMOOTH_POINTS,
) -> None:
    grid = np.linspace(rt_min, rt_max, 250)
    normalized_traces: list[np.ndarray] = []
    for row in rows:
        if group == "rescued":
            include = row.status == "rescued"
        else:
            include = row.group == group
        if not include or row.trace_max_intensity <= 0:
            continue
        if align_to_apex:
            rt, normalized = _apex_aligned_normalized_trace(
                row,
                smooth_points=smooth_points,
            )
        else:
            rt = np.asarray(row.rt, dtype=float)
            intensity = _gaussian_smooth(
                np.asarray(row.intensity, dtype=float),
                points=smooth_points,
            )
            max_intensity = float(np.max(intensity)) if intensity.size else 0.0
            if max_intensity <= 0:
                continue
            normalized = intensity / max_intensity
        if rt.size < 2:
            continue
        interp = np.interp(grid, rt, normalized, left=np.nan, right=np.nan)
        normalized_traces.append(interp)
    if not normalized_traces:
        return
    stack = np.vstack(normalized_traces)
    finite_columns = np.isfinite(stack).any(axis=0)
    if not np.any(finite_columns):
        return
    plot_grid = grid[finite_columns]
    median = np.nanmedian(stack[:, finite_columns], axis=0)
    ax.plot(
        plot_grid,
        median,
        color=color,
        lw=2.6,
        ls=linestyle,
        alpha=0.95,
        label=label,
        zorder=6,
    )


def _plot_area_distribution(ax: Any, rows: Sequence[TraceOverlayRow]) -> None:
    detected_areas = [
        row.cell_area
        for row in rows
        if row.status == "detected" and row.cell_area is not None
    ]
    min_detected_area = min(detected_areas) if detected_areas else None
    rescued_above_min = 0
    for row in rows:
        if row.status not in {"detected", "rescued"} or row.cell_area is None:
            continue
        if (
            row.status == "rescued"
            and min_detected_area is not None
            and row.cell_area >= min_detected_area
        ):
            rescued_above_min += 1
        x_pos = 0 if row.status == "detected" else 1
        jitter = _stable_jitter(row.sample_stem, width=0.18)
        color, alpha, size = _point_style(row)
        ax.scatter(
            x_pos + jitter,
            row.cell_area,
            s=size,
            color=color,
            alpha=alpha,
            edgecolors="none",
        )
    if min_detected_area is not None and min_detected_area > 0:
        ax.axhline(
            min_detected_area,
            color=DETECTED_COLOR,
            lw=1,
            ls=":",
            alpha=0.65,
        )
        ax.text(
            1.02,
            min_detected_area,
            f"{rescued_above_min} rescued >= min detected",
            va="bottom",
            ha="left",
            fontsize=8,
            color=DETECTED_MEDIAN_COLOR,
        )
    ax.set_yscale("log")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["detected\nNL seed", "rescued\nMS1 backfill"])
    ax.set_ylabel("Integrated cell area, log scale")
    ax.set_title("Cell area by evidence source")
    ax.grid(True, axis="y", alpha=0.2)


def _plot_trace_apex_delta_distribution(
    ax: Any,
    detected: Sequence[TraceOverlayRow],
    rescued: Sequence[TraceOverlayRow],
) -> None:
    for row in [*detected, *rescued]:
        delta = _global_trace_apex_delta(row)
        if delta is None or not math.isfinite(delta):
            continue
        x_pos = 1 if row.status == "detected" else 2
        jitter = _stable_jitter(row.sample_stem, width=0.16)
        color, alpha, _size = _point_style(row)
        ax.scatter(
            x_pos + jitter,
            delta,
            s=24,
            color=color,
            alpha=alpha,
            edgecolors="none",
        )
    ax.axhline(0.0, color="black", lw=1, ls="-", alpha=0.45)
    ax.axhline(
        GLOBAL_APEX_CONFLICT_DELTA_MIN,
        color="0.35",
        lw=1,
        ls=":",
        alpha=0.7,
    )
    ax.axhline(
        -GLOBAL_APEX_CONFLICT_DELTA_MIN,
        color="0.35",
        lw=1,
        ls=":",
        alpha=0.7,
    )
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["detected\nNL seed", "rescued\nMS1 backfill"])
    ax.set_ylabel("Global trace apex - selected apex (min)")
    ax.set_title("Neighboring MS1 apex interference")
    ax.grid(True, axis="y", alpha=0.2)


def _plot_shape_similarity(
    ax: Any,
    rows: Sequence[TraceOverlayRow],
    shape_similarity: Mapping[str, float | None],
) -> None:
    for row in rows:
        value = shape_similarity.get(row.sample_stem)
        if value is None or not math.isfinite(value):
            continue
        if row.status not in {"detected", "rescued"}:
            continue
        x_pos = 0 if row.status == "detected" else 1
        jitter = _stable_jitter(row.sample_stem, width=0.18)
        color, alpha, size = _point_style(row)
        ax.scatter(
            x_pos + jitter,
            value,
            s=size,
            color=color,
            alpha=alpha,
            edgecolors="none",
        )
    ax.axhline(0.80, color="0.35", lw=1, ls=":", alpha=0.7)
    ax.axhline(SHAPE_SUPPORT_MIN, color="0.45", lw=1, ls="--", alpha=0.55)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["detected\nNL seed", "rescued\nMS1 backfill"])
    ax.set_ylim(-1.05, 1.05)
    ax.set_ylabel("Apex-aligned shape similarity")
    ax.set_title("Shape similarity after apex alignment")
    ax.grid(True, axis="y", alpha=0.2)


def _gaussian_smooth(values: np.ndarray, *, points: int) -> np.ndarray:
    return _gaussian_smooth_values(values, points=points)


def _write_summary(path: Path, rows: Sequence[TraceOverlayRow]) -> None:
    shape_similarity = _apex_aligned_shape_similarity(rows)
    fields = (
        "sample_stem",
        "status",
        "cell_area",
        "cell_height",
        "cell_apex_rt",
        "cell_start_rt",
        "cell_end_rt",
        "trace_max_intensity",
        "trace_apex_rt",
        "global_trace_apex_delta_min",
        "local_window_max_intensity",
        "local_window_apex_delta_min",
        "local_window_to_global_max_ratio",
        "region_shadow_verdict",
        "source_candidate_id",
        "highlight_group",
        "apex_aligned_shape_similarity",
    )
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "sample_stem": row.sample_stem,
                    "status": row.status,
                    "cell_area": _format_float(row.cell_area),
                    "cell_height": _format_float(row.cell_height),
                    "cell_apex_rt": _format_float(row.cell_apex_rt, digits=6),
                    "cell_start_rt": _format_float(row.cell_start_rt, digits=6),
                    "cell_end_rt": _format_float(row.cell_end_rt, digits=6),
                    "trace_max_intensity": _format_float(row.trace_max_intensity),
                    "trace_apex_rt": _format_float(row.trace_apex_rt, digits=6),
                    "global_trace_apex_delta_min": _format_float(
                        _global_trace_apex_delta(row),
                    ),
                    "local_window_max_intensity": _format_float(
                        _local_window_peak(row)[1],
                    ),
                    "local_window_apex_delta_min": _format_float(
                        _local_window_peak(row)[0],
                    ),
                    "local_window_to_global_max_ratio": _format_float(
                        _local_to_global_max_ratio(row),
                    ),
                    "region_shadow_verdict": row.region_shadow_verdict,
                    "source_candidate_id": row.source_candidate_id,
                    "highlight_group": row.group,
                    "apex_aligned_shape_similarity": _format_float(
                        shape_similarity.get(row.sample_stem),
                    ),
                }
            )


def _write_trace_data(
    path: Path,
    *,
    rows: Sequence[TraceOverlayRow],
    family_id: str,
    mz: float,
    ppm: float,
    rt_min: float,
    rt_max: float,
    family_center_rt: float | None,
) -> None:
    shape_similarity = _apex_aligned_shape_similarity(rows)
    data = {
        "family_id": family_id,
        "mz": mz,
        "ppm": ppm,
        "rt_min": rt_min,
        "rt_max": rt_max,
        "family_center_rt": family_center_rt,
        "trace_count": len(rows),
        "evidence_summary": build_family_ms1_evidence_summary(rows),
        "traces": [
            {
                "sample_stem": row.sample_stem,
                "status": row.status,
                "group": row.group,
                "cell_area": row.cell_area,
                "cell_height": row.cell_height,
                "cell_apex_rt": row.cell_apex_rt,
                "cell_start_rt": row.cell_start_rt,
                "cell_end_rt": row.cell_end_rt,
                "trace_max_intensity": row.trace_max_intensity,
                "trace_apex_rt": row.trace_apex_rt,
                "global_trace_apex_delta_min": _json_float(
                    _global_trace_apex_delta(row),
                ),
                "local_window_max_intensity": _json_float(
                    _local_window_peak(row)[1],
                ),
                "local_window_apex_delta_min": _json_float(
                    _local_window_peak(row)[0],
                ),
                "local_window_to_global_max_ratio": _json_float(
                    _local_to_global_max_ratio(row),
                ),
                "region_shadow_verdict": row.region_shadow_verdict,
                "source_candidate_id": row.source_candidate_id,
                "apex_aligned_shape_similarity": _json_float(
                    shape_similarity.get(row.sample_stem),
                ),
                "rt": row.rt,
                "intensity": row.intensity,
            }
            for row in rows
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-cells", type=Path, required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--mz", type=float, required=True)
    parser.add_argument("--rt-min", type=float, required=True)
    parser.add_argument("--rt-max", type=float, required=True)
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--max-highlight-rescued", type=int, default=8)
    parser.add_argument("--family-center-rt", type=float)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-prefix")
    return parser.parse_args(argv)


def _line_style(group: str) -> tuple[str, float, float, int]:
    if group == "detected_seed":
        return DETECTED_COLOR, 0.92, 1.7, 4
    if group == "top_rescued_ms1_area":
        return RESCUED_COLOR, 0.72, 1.15, 3
    if group == "pooled_qc":
        return QC_COLOR, 0.38, 0.85, 2
    return OTHER_TRACE_COLOR, 0.15, 0.65, 1


def _point_style(row: TraceOverlayRow) -> tuple[str, float, int]:
    if row.status == "detected":
        return DETECTED_COLOR, 0.92, 42
    if row.group == "top_rescued_ms1_area":
        return RESCUED_COLOR, 0.78, 34
    return "0.55", 0.45, 24


def _draw_center_rt(
    ax: Any,
    family_center_rt: float | None,
    *,
    horizontal: bool = False,
) -> None:
    if family_center_rt is None or not math.isfinite(family_center_rt):
        return
    if horizontal:
        ax.axhline(family_center_rt, color="black", lw=1, ls="--", alpha=0.6)
    else:
        ax.axvline(family_center_rt, color="black", lw=1, ls="--", alpha=0.6)


def _stable_jitter(value: str, *, width: float) -> float:
    digest = hashlib.sha1(value.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], byteorder="big") / 2**32
    return (bucket - 0.5) * width


def _require_columns(actual: Sequence[str], required: Sequence[str]) -> None:
    missing = [field for field in required if field not in actual]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _format_float(value: float | None, *, digits: int = 6) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{digits}g}"


def _json_float(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return float(value)


if __name__ == "__main__":
    raise SystemExit(main())
