from __future__ import annotations

from html import escape
from pathlib import Path

from xic_extractor.output.review_metrics import ReviewMetrics, build_review_metrics


def review_report_path_for_excel(excel_path: Path) -> Path:
    return excel_path.with_name(
        excel_path.name.replace("xic_results_", "review_report_")
    ).with_suffix(".html")


def write_review_report(
    path: Path,
    rows: list[dict[str, str]],
    *,
    diagnostics: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    count_no_ms2_as_detected: bool,
) -> Path:
    metrics = build_review_metrics(
        rows,
        diagnostics=diagnostics,
        review_rows=review_rows,
        count_no_ms2_as_detected=count_no_ms2_as_detected,
    )
    samples = _ordered_values(rows, "SampleName")
    targets = _targets_by_detection(metrics)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                "<title>XIC Review Report</title>",
                f"<style>{_CSS}</style>",
                "</head>",
                "<body>",
                "<main>",
                "<h1>XIC Review Report</h1>",
                _batch_overview(metrics),
                _detection_rate_chart(metrics, targets),
                _flag_burden_chart(metrics, targets),
                _heatmap(metrics, samples, targets),
                _review_queue(review_rows),
                "</main>",
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )
    return path


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
.box{display:inline-block;width:14px;height:14px;border:1px solid #8c959f}
.clean-detected{background:#dafbe1}
.flagged-detected{background:#fff8c5}
.not-detected{background:#ffebe9}
.error{background:#ffd8d3}
.heatmap td{text-align:center;min-width:28px}
.bar-table td:nth-child(2){width:90px;font-weight:700}
.bar-track{height:14px;background:#eaeef2;border:1px solid #d0d7de}
.bar-fill{height:100%}
.bar-fill.detection{background:#2da44e}
.bar-fill.flagged{background:#cf222e}
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
    for target in targets:
        item = metrics.targets[target]
        detected_percent = _percent_value(item.detected_percent)
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
    return (
        "<section><h2>Detection Rate By Target</h2>"
        '<p class="dashboard-note">Lowest detection rates are listed first.</p>'
        '<table class="bar-table"><thead><tr><th>Target</th><th>Detected %</th>'
        "<th>Rate</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></section>"
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
    for item in flagged_targets:
        flagged_percent = _percent_value(item.flagged_percent)
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
    return (
        "<section><h2>Flag Burden By Target</h2>"
        '<p class="dashboard-note">Only targets with review rows are included.</p>'
        '<table class="bar-table"><thead><tr><th>Target</th><th>Flagged Rows</th>'
        "<th>Flagged %</th><th>Burden</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></section>"
    )


def _heatmap(metrics: ReviewMetrics, samples: list[str], targets: list[str]) -> str:
    legend = (
        '<div class="legend">'
        '<span class="chip"><span class="box clean-detected"></span>'
        "clean-detected</span>"
        '<span class="chip"><span class="box flagged-detected"></span>'
        "flagged-detected</span>"
        '<span class="chip"><span class="box not-detected"></span>'
        "not-detected</span>"
        '<span class="chip"><span class="box error"></span>error</span>'
        "</div>"
    )
    header = "".join(f"<th>{escape(sample)}</th>" for sample in samples)
    body_rows = []
    for target in targets:
        cells = []
        for sample in samples:
            state = metrics.heatmap.get((target, sample), "not-detected")
            cells.append(
                f'<td class="{state}" title="{state}">{_state_label(state)}</td>'
            )
        body_rows.append(f"<tr><th>{escape(target)}</th>{''.join(cells)}</tr>")
    body = "".join(body_rows) or '<tr><td colspan="2">None</td></tr>'
    return (
        "<section><h2>Detection / Flag Heatmap</h2>"
        f'{legend}<table class="heatmap"><thead><tr><th>Target</th>{header}</tr>'
        f"</thead><tbody>{body}</tbody></table></section>"
    )


def _review_queue(review_rows: list[dict[str, str]]) -> str:
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
        "<section><h2>Review Queue</h2>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
        "</section>"
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


def _state_label(state: str) -> str:
    return {
        "clean-detected": "OK",
        "flagged-detected": "Flag",
        "not-detected": "ND",
        "error": "Error",
    }.get(state, "")
