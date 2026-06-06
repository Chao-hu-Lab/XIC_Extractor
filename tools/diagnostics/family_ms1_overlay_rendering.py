"""Matplotlib rendering helpers for family MS1 overlay diagnostics."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from xic_extractor.alignment.edge_scoring import DriftLookupProtocol

from tools.diagnostics.family_ms1_overlay_evidence import (
    _apex_aligned_normalized_trace,
    _apex_aligned_shape_similarity,
    _gaussian_smooth_values,
    _global_trace_apex_delta,
)
from tools.diagnostics.family_ms1_overlay_models import (
    APEX_ALIGN_HALF_WINDOW_MIN,
    GLOBAL_APEX_CONFLICT_DELTA_MIN,
    SHAPE_SUPPORT_MIN,
    TraceOverlayRow,
)
from tools.diagnostics.family_ms1_overlay_rendering_styles import (
    DETECTED_COLOR,
    DETECTED_MEDIAN_COLOR,
    PLOT_GAUSSIAN_SMOOTH_POINTS,
    RESCUED_COLOR,
    RESCUED_MEDIAN_COLOR,
    _draw_center_rt,
    _line_style,
    _plot_unified_legend,
    _point_style,
    _stable_jitter,
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
    drift_lookup: DriftLookupProtocol | None = None,
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
            ["irt", "irt", "irt"],
            ["legend", "legend", "legend"],
        ],
        figsize=(18, 13),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.0, 1.0, 1.0, 0.12]},
    )
    _plot_normalized_overlay(
        axes["norm"],
        rows,
        family_center_rt=family_center_rt,
        rt_min=rt_min,
        rt_max=rt_max,
    )
    _plot_irt_overlay(
        axes["irt"],
        rows,
        drift_lookup=drift_lookup,
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


def _plot_irt_overlay(
    ax: Any,
    rows: Sequence[TraceOverlayRow],
    *,
    drift_lookup: DriftLookupProtocol | None,
    rt_min: float,
    rt_max: float,
) -> None:
    plotted = 0
    corrected_min = math.inf
    corrected_max = -math.inf
    for row in rows:
        delta = (
            drift_lookup.sample_delta_min(row.sample_stem)
            if drift_lookup is not None
            else None
        )
        if delta is None:
            continue
        rt = np.asarray(row.rt, dtype=float) - delta
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
        plotted += 1
        corrected_min = min(corrected_min, float(rt.min()))
        corrected_max = max(corrected_max, float(rt.max()))
    ax.set_title(
        "Drift-corrected (iRT) RT context: per-sample shift = -ISTD drift "
        "(traces collapsing here = same peak with drift)",
    )
    ax.set_xlabel("Drift-corrected RT (min)")
    ax.set_ylabel("Per-trace scaled intensity (0-1)")
    ax.set_ylim(-0.03, 1.08)
    ax.grid(True, alpha=0.2)
    if plotted == 0:
        ax.text(
            0.5,
            0.5,
            "drift evidence not supplied — iRT panel unavailable",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            color="#888888",
        )
    else:
        # Frame the drift-corrected data so no shifted trace is clipped, while
        # still spanning at least the original RT window for comparability.
        ax.set_xlim(min(rt_min, corrected_min), max(rt_max, corrected_max))
        _add_panel_note(
            ax,
            "Compare against the absolute-RT panel: convergence here means the "
            "apparent split is drift, not separate peaks.",
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
