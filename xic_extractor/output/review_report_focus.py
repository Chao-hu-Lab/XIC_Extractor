from __future__ import annotations

from html import escape

from xic_extractor.output.review_metrics import ReviewMetrics

_FOCUS_CSS = """
.focus-grid{display:grid;grid-template-columns:repeat(2,minmax(220px,1fr));gap:12px}
.focus-card{border:1px solid #d0d7de;background:#f6f8fa;padding:12px}
.focus-card h3{font-size:14px;margin:0 0 8px}
.focus-list{list-style:none;margin:0;padding:0}
.focus-list li{display:flex;justify-content:space-between;padding:4px 0}
.focus-list strong{font-size:16px}
.compact-heatmap{
display:block;border:1px solid #d0d7de;padding:10px;background:#fff;max-width:100%
}
.heatmap-row{
display:grid;grid-template-columns:minmax(140px,220px) minmax(0,1fr);gap:8px
}
.heatmap-row+.heatmap-row{margin-top:5px}
.heatmap-target{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.heatmap-cells{
display:grid;grid-template-columns:repeat(var(--sample-count),var(--heat-cell-size));
gap:var(--heat-cell-gap);align-items:center;flex-wrap:nowrap;overflow:hidden
}
.heat-cell{
box-sizing:border-box;width:var(--heat-cell-size);height:var(--heat-cell-size);
border:1px solid #8c959f;display:inline-block
}
.review-details{margin-top:12px}
.review-details summary{cursor:pointer;font-weight:700;margin-bottom:8px}
""".strip()


def _review_focus(review_rows: list[dict[str, str]]) -> str:
    target_rows = _ranked_counts(review_rows, "Target")
    sample_rows = _ranked_counts(review_rows, "Sample")
    return (
        "<section><h2>Review Focus</h2>"
        '<p class="dashboard-note">'
        "At-a-glance triage only. Excel workbook remains the row-level source."
        "</p>"
        '<div class="focus-grid">'
        f'{_focus_card("Top Targets", target_rows)}'
        f'{_focus_card("Top Samples", sample_rows)}'
        "</div></section>"
    )


def _compact_heatmap(
    metrics: ReviewMetrics,
    samples: list[str],
    targets: list[str],
) -> str:
    legend = (
        '<div class="legend">'
        '<span class="chip"><span class="box clean-detected"></span>Detected</span>'
        '<span class="chip"><span class="box flagged-detected"></span>Review</span>'
        '<span class="chip"><span class="box not-detected"></span>ND</span>'
        '<span class="chip"><span class="box error"></span>Error</span>'
        "</div>"
    )
    rows = "".join(_heatmap_row(metrics, target, samples) for target in targets)
    if not rows:
        rows = '<div class="heatmap-row">None</div>'
    cell_size, cell_gap = _heatmap_cell_metrics(len(samples))
    style = (
        f"--sample-count:{len(samples)};"
        f"--heat-cell-size:{cell_size}px;"
        f"--heat-cell-gap:{cell_gap}px"
    )
    return (
        "<section><h2>Detection / Flag Map</h2>"
        '<p class="dashboard-note">'
        "Each target stays on one row; hover for sample details."
        "</p>"
        f'{legend}<div class="compact-heatmap" style="{style}">{rows}</div></section>'
    )


def _review_queue_details(review_rows: list[dict[str, str]]) -> str:
    headers = [
        "Priority",
        "Sample",
        "Target",
        "Status",
        "Why",
        "Action",
        "Issue Count",
        "Evidence",
    ]
    body = []
    for row in review_rows:
        cells = "".join(f"<td>{escape(row.get(header, ''))}</td>" for header in headers)
        body.append(f"<tr>{cells}</tr>")
    rows = "".join(body) or f'<tr><td colspan="{len(headers)}">None</td></tr>'
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    return (
        '<details class="review-details">'
        f"<summary>Review Queue details ({len(review_rows)} rows)</summary>"
        '<p class="dashboard-note">'
        "Excel workbook remains the row-level source for final review."
        "</p>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
        "</details>"
    )


def _focus_card(title: str, rows: list[tuple[str, int]]) -> str:
    items = "".join(
        f"<li><span>{escape(label)}</span><strong>{count}</strong></li>"
        for label, count in rows[:5]
    )
    if not items:
        items = "<li><span>None</span><strong>0</strong></li>"
    return (
        '<div class="focus-card">'
        f"<h3>{escape(title)}</h3><ol class=\"focus-list\">{items}</ol>"
        "</div>"
    )


def _heatmap_row(metrics: ReviewMetrics, target: str, samples: list[str]) -> str:
    cells = []
    for sample in samples:
        state = metrics.heatmap.get((target, sample), "not-detected")
        title = f"{target} / {sample}: {_state_label(state)}"
        cells.append(
            f'<span class="heat-cell {state}" title="{escape(title)}" '
            f'aria-label="{escape(title)}"></span>'
        )
    return (
        '<div class="heatmap-row">'
        f'<span class="heatmap-target">{escape(target)}</span>'
        f'<span class="heatmap-cells">{"".join(cells)}</span></div>'
    )


def _ranked_counts(rows: list[dict[str, str]], key: str) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key, "")
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _heatmap_cell_metrics(sample_count: int) -> tuple[int, int]:
    if sample_count <= 24:
        return 18, 4
    if sample_count <= 60:
        return 12, 3
    if sample_count <= 100:
        return 8, 2
    return 6, 1


def _state_label(state: str) -> str:
    return {
        "clean-detected": "Detected",
        "flagged-detected": "Review",
        "not-detected": "ND",
        "error": "Error",
    }.get(state, state)
