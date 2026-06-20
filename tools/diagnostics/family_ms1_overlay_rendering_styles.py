"""Plot style helpers for family MS1 overlay diagnostics."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from tools.diagnostics.family_ms1_overlay_models import TraceOverlayRow

PLOT_GAUSSIAN_SMOOTH_POINTS = 15
DETECTED_COLOR = "#D55E00"
RESCUED_COLOR = "#005AB5"
QC_COLOR = "#CC79A7"
OTHER_TRACE_COLOR = "#555555"
RESCUED_MEDIAN_COLOR = "#005A8D"


def _line_style(group: str) -> tuple[str, float, float, int]:
    if group == "detected_seed":
        return DETECTED_COLOR, 0.96, 2.2, 5
    if group == "top_rescued_ms1_area":
        return RESCUED_COLOR, 0.86, 1.65, 4
    if group == "pooled_qc":
        return QC_COLOR, 0.54, 1.0, 3
    return OTHER_TRACE_COLOR, 0.12, 0.55, 1


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


def _plot_unified_legend(ax: Any) -> None:
    from matplotlib.lines import Line2D

    ax.axis("off")
    handles = [
        Line2D([0], [0], color=DETECTED_COLOR, lw=2.2, label="detected NL seed"),
        Line2D(
            [0],
            [0],
            color=RESCUED_COLOR,
            lw=1.65,
            label="top rescued backfill",
        ),
        Line2D([0], [0], color=QC_COLOR, lw=1.0, label="pooled QC"),
        Line2D([0], [0], color=OTHER_TRACE_COLOR, lw=0.7, label="other context"),
        Line2D(
            [0],
            [0],
            color="black",
            lw=1,
            ls="--",
            alpha=0.6,
            label="family center",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="center",
        ncol=5,
        frameon=False,
        handlelength=3.0,
        columnspacing=1.4,
    )
