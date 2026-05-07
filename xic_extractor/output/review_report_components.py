from __future__ import annotations

from html import escape

from xic_extractor.output.review_metrics import ReviewMetrics
from xic_extractor.output.review_report_bars import target_bar_chart

_CSS = """
body{font-family:Arial,Helvetica,sans-serif;margin:24px;color:#1f2328;background:#fff}
main{max-width:1200px;margin:0 auto}
h1{font-size:24px;margin:0 0 18px}
h2{font-size:18px;margin:28px 0 10px}
table{border-collapse:collapse;width:100%;margin:8px 0 18px}
th,td{border:1px solid #d0d7de;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f6f8fa;font-weight:700}
.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px}
.metric{border:1px solid #d0d7de;padding:10px;background:#f6f8fa}
.metric strong{display:block;font-size:20px}
.legend{display:flex;gap:12px;flex-wrap:wrap;margin:8px 0 12px}
.chip{display:inline-flex;align-items:center;gap:6px}
.box{display:inline-block;width:14px;height:14px;border:1px solid #4b5563}
.clean-detected{background:#1f9d55}
.flagged-detected{background:#f59e0b}
.not-detected{background:#cbd5e1}
.error{background:#d1242f}
.heatmap td{text-align:center;min-width:28px}
.bar-table{table-layout:fixed}
.bar-table .target-col{width:36%}
.bar-table .count-col{width:110px}
.bar-table .percent-col{width:110px}
.bar-table .bar-col{width:auto}
.bar-table td:nth-child(2){width:90px;font-weight:700}
.chart-details{margin:8px 0 18px}
.chart-details summary{cursor:pointer;font-weight:700;color:#57606a}
.bar-track{height:14px;background:#eaeef2;border:1px solid #d0d7de}
.bar-fill{height:100%}
.bar-fill.detection{background:#2da44e}
.bar-fill.flagged{background:#cf222e}
.target-bar-chart{
display:block;width:720px;max-width:100%;height:auto;margin:8px 0 12px;
border:1px solid #d0d7de;background:#fff
}
.target-bar{rx:3;ry:3}
.target-bar.detection-bar{fill:#2da44e}
.target-bar.flag-bar{fill:#cf222e}
.target-bar-label{font-size:12px;fill:#24292f}
.target-bar-value{font-size:12px;fill:#57606a}
.trend-svg{
width:1100px;max-width:100%;height:auto;
border:1px solid #d0d7de;background:#fff}
.trend-axis{stroke:#57606a;stroke-width:1}
.trend-grid{stroke:#d8dee4;stroke-width:1;stroke-dasharray:2 2}
.trend-band{opacity:.16}
.trend-qc{stroke:#8c959f;stroke-width:1.5;stroke-dasharray:6 4}
.trend-line{fill:none;stroke-width:2}
.trend-point{stroke:#fff;stroke-width:1}
.trend-label{fill:#57606a;font-size:12px}
.trend-title{fill:#1f2328;font-size:18px;font-weight:700;text-anchor:middle}
.trend-axis-label{fill:#1f2328;font-size:13px;text-anchor:middle}
.trend-tick{fill:#57606a;font-size:11px}
.trend-x-tick{text-anchor:middle}
.trend-y-tick{text-anchor:end}
.trend-svg-legend text{fill:#1f2328;font-size:12px}
.trend-legend-line{stroke-width:2}
.trend-legend-qc{stroke:#8c959f;stroke-width:1.5;stroke-dasharray:6 4}
.trend-legend-band{fill:#8c959f;opacity:.22;stroke:#8c959f}
.area-stability-layout{display:flex;flex-direction:column;gap:10px}
.area-stability-chart{width:100%}
.area-stability-table-wrap{max-width:940px}
.area-stability-table{width:100%;min-width:900px;font-size:11px;margin:2px 0 8px}
.area-stability-table th,.area-stability-table td{padding:3px 6px}
.area-stability-table td:nth-child(n+3){font-variant-numeric:tabular-nums}
.area-stability-svg{
width:1200px;max-width:100%;height:auto;
border:1px solid #d0d7de;background:#fff}
.area-line{fill:none;stroke-width:2}
.area-qc{stroke:#8c959f;stroke-width:1.5;stroke-dasharray:6 4}
.area-point{stroke:#fff;stroke-width:1}
.dashboard-note{color:#57606a;font-size:13px;margin:4px 0 14px}
.small{color:#57606a;font-size:12px}
""".strip()


def _batch_overview(metrics: ReviewMetrics) -> str:
    values = [
        ("Samples", metrics.sample_count),
        ("Targets", metrics.target_count),
        ("Flagged Rows", metrics.flagged_rows),
        ("Diagnostics", metrics.diagnostics_count),
    ]
    cards = "".join(
        '<div class="metric">'
        f"<span>{escape(label)}</span><strong>{value}</strong>"
        "</div>"
        for label, value in values
    )
    return (
        "<section><h2>Batch Overview</h2>"
        f'<div class="metric-grid">{cards}</div></section>'
    )


def _detection_rate_chart(metrics: ReviewMetrics, targets: list[str]) -> str:
    rows = ""
    chart_items: list[tuple[str, int, str]] = []
    for target in targets:
        item = metrics.targets[target]
        detected_percent = _percent_value(item.detected_percent)
        chart_items.append((item.target, detected_percent, item.detected_percent))
        rows += (
            "<tr>"
            f"<td>{escape(item.target)}</td>"
            f"<td>{item.detected_percent}</td>"
            '<td><div class="bar-track">'
            f'<div class="bar-fill detection" style="width:{detected_percent}%">'
            "</div></div></td>"
            "</tr>"
        )
    if not rows:
        rows = '<tr><td colspan="3">None</td></tr>'
    chart_html = target_bar_chart(
        chart_items,
        chart_class="detection-chart",
        bar_class="detection-bar",
    )
    table = (
        '<table class="bar-table">'
        '<colgroup><col class="target-col"><col class="percent-col">'
        '<col class="bar-col"></colgroup>'
        "<thead><tr><th>Target</th><th>Detected %</th>"
        "<th>Rate</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return (
        "<section><h2>Detection Rate By Target</h2>"
        '<p class="dashboard-note">Lowest detection rates are listed first.</p>'
        f"{chart_html}"
        f'{_chart_details("Detection rate table", table)}</section>'
    )


def _flag_burden_chart(metrics: ReviewMetrics, targets: list[str]) -> str:
    flagged_targets = sorted(
        (
            metrics.targets[target]
            for target in targets
            if metrics.targets[target].flagged_rows > 0
        ),
        key=lambda item: (-_percent_value(item.flagged_percent), item.target),
    )
    rows = ""
    chart_items: list[tuple[str, int, str]] = []
    for item in flagged_targets:
        flagged_percent = _percent_value(item.flagged_percent)
        chart_items.append((item.target, flagged_percent, item.flagged_percent))
        rows += (
            "<tr>"
            f"<td>{escape(item.target)}</td>"
            f"<td>{item.flagged_rows}</td>"
            f"<td>{item.flagged_percent}</td>"
            '<td><div class="bar-track">'
            f'<div class="bar-fill flagged" style="width:{flagged_percent}%">'
            "</div></div></td>"
            "</tr>"
        )
    if not rows:
        rows = '<tr><td colspan="4">None</td></tr>'
    chart_html = target_bar_chart(
        chart_items,
        chart_class="flag-chart",
        bar_class="flag-bar",
    )
    table = (
        '<table class="bar-table">'
        '<colgroup><col class="target-col"><col class="count-col">'
        '<col class="percent-col"><col class="bar-col"></colgroup>'
        "<thead><tr><th>Target</th><th>Flagged Rows</th>"
        "<th>Flagged %</th><th>Burden</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return (
        "<section><h2>Flag Burden By Target</h2>"
        '<p class="dashboard-note">Only targets with review rows are included.</p>'
        f"{chart_html}"
        f'{_chart_details("Flag burden table", table)}</section>'
    )


def _ordered_values(rows: list[dict[str, str]], key: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(key, "")
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def _chart_details(summary: str, table: str) -> str:
    return (
        '<details class="chart-details">'
        f"<summary>{escape(summary)}</summary>"
        f"{table}"
        "</details>"
    )



def _targets_by_detection(metrics: ReviewMetrics) -> list[str]:
    return sorted(
        metrics.targets,
        key=lambda target: (
            _percent_value(metrics.targets[target].detected_percent),
            target,
        ),
    )


def _percent_value(text: str) -> int:
    try:
        return int(text.rstrip("%"))
    except ValueError:
        return 0
