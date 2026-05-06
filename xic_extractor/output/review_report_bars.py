from __future__ import annotations

from html import escape


def target_bar_chart(
    items: list[tuple[str, int, str]],
    *,
    chart_class: str,
    bar_class: str,
) -> str:
    if not items:
        return ""
    width = 720
    left = 170
    right = 80
    top = 16
    row_height = 28
    bar_height = 14
    plot_width = width - left - right
    height = top * 2 + row_height * len(items)
    rows = []
    for index, (label, value, value_text) in enumerate(items):
        y = top + index * row_height
        bar_width = max(0, min(value, 100)) / 100 * plot_width
        rows.append(
            f'<text class="target-bar-label" x="10" y="{y + 12}">'
            f"{escape(label)}</text>"
            f'<rect class="target-bar {bar_class}" x="{left}" y="{y}" '
            f'width="{bar_width:.1f}" height="{bar_height}"></rect>'
            f'<text class="target-bar-value" x="{left + plot_width + 10}" '
            f'y="{y + 12}">{escape(value_text)}</text>'
        )
    return (
        f'<svg class="target-bar-chart {chart_class}" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" role="img">'
        f"{''.join(rows)}"
        "</svg>"
    )
