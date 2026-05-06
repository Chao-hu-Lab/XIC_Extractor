from __future__ import annotations

import statistics
from collections.abc import Iterable
from html import escape
from typing import TypeVar

T = TypeVar("T")

_TREND_PALETTE = (
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#17becf",
    "#7f7f7f",
)

def _istd_rt_trend(
    rows: list[dict[str, str]], injection_order: dict[str, int] | None
) -> str:
    if not injection_order:
        return ""

    points: list[tuple[int, float, str, str]] = []
    for row in rows:
        if row.get("Role") != "ISTD":
            continue
        sample = row.get("SampleName", "")
        order = injection_order.get(sample)
        rt = _float_value(row.get("RT", ""))
        target = row.get("Target", "")
        if order is None or rt is None or not target:
            continue
        points.append((order, rt, target, sample))

    if len(points) < 2:
        return ""
    x_values = _ordered_unique(order for order, _, _, _ in points)
    y_values = _ordered_unique(rt for _, rt, _, _ in points)
    if len(x_values) < 2:
        return ""

    points.sort(key=lambda item: (item[0], item[2], item[3]))
    targets = _ordered_unique(point[2] for point in points)
    target_colors = {
        target: _TREND_PALETTE[index % len(_TREND_PALETTE)]
        for index, target in enumerate(targets)
    }
    target_points_by_name = {
        target: [point for point in points if point[2] == target] for target in targets
    }
    band_edges = []
    for target_points in target_points_by_name.values():
        median_rt = statistics.median(point[1] for point in target_points)
        band_edges.extend([median_rt - 0.5, median_rt + 0.5])

    width = 1100
    height = 560
    left = 78
    legend_left = 872
    top = 58
    bottom = 70
    plot_width = legend_left - left - 32
    plot_height = height - top - bottom
    min_x = min(x_values)
    max_x = max(x_values)
    min_y = min([*y_values, *band_edges])
    max_y = max([*y_values, *band_edges])
    if min_y == max_y:
        min_y -= 0.0005
        max_y += 0.0005

    def x_pos(order: int) -> float:
        return left + ((order - min_x) / (max_x - min_x)) * plot_width

    def y_pos(rt: float) -> float:
        return top + ((max_y - rt) / (max_y - min_y)) * plot_height

    x_ticks = _integer_ticks(min_x, max_x, count=7)
    y_ticks = _float_ticks(min_y, max_y, count=6)
    horizontal_grid = [
        f'<line class="trend-grid" x1="{left}" y1="{y_pos(tick):.1f}" '
        f'x2="{left + plot_width}" y2="{y_pos(tick):.1f}"></line>'
        for tick in y_ticks
    ]
    vertical_grid = [
        f'<line class="trend-grid" x1="{x_pos(tick):.1f}" y1="{top}" '
        f'x2="{x_pos(tick):.1f}" y2="{top + plot_height}"></line>'
        for tick in x_ticks
    ]
    x_tick_labels = [
        f'<text class="trend-tick trend-x-tick" x="{x_pos(tick):.1f}" '
        f'y="{top + plot_height + 20}">{tick}</text>'
        for tick in x_ticks
    ]
    y_tick_labels = [
        f'<text class="trend-tick trend-y-tick" x="{left - 8}" '
        f'y="{y_pos(tick) + 4:.1f}">{tick:.1f}</text>'
        for tick in y_ticks
    ]

    qc_orders = sorted(
        {order for order, _, _, sample in points if "QC" in sample.upper()}
    )
    qc_markers = [
        f'<line class="trend-qc" x1="{x_pos(order):.1f}" y1="{top}" '
        f'x2="{x_pos(order):.1f}" y2="{top + plot_height}">'
        f"<title>QC Injection {order}</title></line>"
        for order in qc_orders
    ]

    bands = []
    for target, target_points in target_points_by_name.items():
        color = target_colors[target]
        median_rt = statistics.median(point[1] for point in target_points)
        y_high = y_pos(median_rt + 0.5)
        y_low = y_pos(median_rt - 0.5)
        bands.append(
            '<rect class="trend-band" '
            f'data-target="{escape(target)}" '
            f'x="{left}" y="{min(y_high, y_low):.1f}" '
            f'width="{plot_width}" height="{abs(y_low - y_high):.1f}" '
            f'fill="{color}">'
            f"<title>{escape(target)} Acceptable Range (Median +/- 0.5 min)</title>"
            "</rect>"
        )

    lines = []
    circles = []
    for target in targets:
        target_points = target_points_by_name[target]
        target_points.sort(key=lambda item: (item[0], item[3]))
        if len(target_points) < 2:
            continue
        color = target_colors[target]
        line_points = [
            f"{x_pos(order):.1f},{y_pos(rt):.1f}" for order, rt, _, _ in target_points
        ]
        lines.append(
            '<polyline class="trend-line" '
            f'data-target="{escape(target)}" '
            f'stroke="{color}" '
            f'points="{" ".join(line_points)}"></polyline>'
        )
    for order, rt, target, sample in points:
        x = x_pos(order)
        y = y_pos(rt)
        color = target_colors[target]
        title = (
            f"{escape(target)}: Injection {order}, RT {rt:.4f} min ({escape(sample)})"
        )
        circles.append(
            f'<circle class="trend-point" cx="{x:.1f}" cy="{y:.1f}" r="4" '
            f'fill="{color}">'
            f"<title>{title}</title></circle>"
        )

    legend = _trend_legend(target_colors, x=legend_left + 16, y=58)
    return (
        "<section><h2>ISTD RT Injection Trend</h2>"
        '<p class="dashboard-note">'
        "Acceptable bands show each ISTD median +/- 0.5 min; dashed lines mark QC "
        "injections.</p>"
        f'<svg class="trend-svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        'role="img" aria-label="ISTD RT by injection order">'
        f'<text class="trend-title" x="{left + plot_width / 2:.1f}" y="28">'
        "Internal Standard (ISTD) Retention Time Trend</text>"
        f"{''.join(horizontal_grid)}"
        f"{''.join(vertical_grid)}"
        f'<line class="trend-axis" x1="{left}" y1="{top}" x2="{left}" '
        f'y2="{top + plot_height}"></line>'
        f'<line class="trend-axis" x1="{left}" y1="{top + plot_height}" '
        f'x2="{left + plot_width}" y2="{top + plot_height}"></line>'
        f"{''.join(x_tick_labels)}"
        f"{''.join(y_tick_labels)}"
        f"{''.join(bands)}"
        f"{''.join(qc_markers)}"
        f"{''.join(lines)}"
        f"{''.join(circles)}"
        f'<text class="trend-axis-label trend-x-label" '
        f'x="{left + plot_width / 2:.1f}" y="{height - 20}">Injection Order</text>'
        f'<text class="trend-axis-label trend-y-label" '
        f'transform="translate(18 {top + plot_height / 2:.1f}) rotate(-90)">'
        "Retention Time (min)</text>"
        f"{legend}"
        "</svg></section>"
    )


def _trend_legend(target_colors: dict[str, str], *, x: int, y: int) -> str:
    rows = [
        (
            f'<line class="trend-legend-qc" x1="{x}" y1="{y + 6}" '
            f'x2="{x + 26}" y2="{y + 6}"></line>'
            f'<text x="{x + 34}" y="{y + 10}">QC Injection</text>'
        ),
        (
            f'<rect class="trend-legend-band" x="{x}" y="{y + 24}" '
            'width="26" height="12"></rect>'
            f'<text x="{x + 34}" y="{y + 34}">Acceptable Range</text>'
            f'<text x="{x + 34}" y="{y + 48}">(Median +/- 0.5 min)</text>'
        ),
    ]
    target_y = y + 74
    for index, (target, color) in enumerate(target_colors.items()):
        row_y = target_y + index * 22
        rows.append(
            f'<line class="trend-legend-line" stroke="{color}" '
            f'x1="{x}" y1="{row_y}" x2="{x + 26}" y2="{row_y}"></line>'
            f'<text x="{x + 34}" y="{row_y + 4}">{escape(target)}</text>'
        )
    return f'<g class="trend-svg-legend">{"".join(rows)}</g>'


def _integer_ticks(min_value: int, max_value: int, *, count: int) -> list[int]:
    if count <= 1 or min_value == max_value:
        return [min_value]
    span = max_value - min_value
    ticks = [round(min_value + span * index / (count - 1)) for index in range(count)]
    ticks[0] = min_value
    ticks[-1] = max_value
    return _ordered_unique(ticks)


def _float_ticks(min_value: float, max_value: float, *, count: int) -> list[float]:
    if count <= 1 or min_value == max_value:
        return [min_value]
    span = max_value - min_value
    return [min_value + span * index / (count - 1) for index in range(count)]

def _ordered_unique(values: Iterable[T]) -> list[T]:
    ordered: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered

def _float_value(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None
