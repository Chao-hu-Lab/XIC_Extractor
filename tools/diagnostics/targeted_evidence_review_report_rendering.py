"""HTML rendering for the targeted evidence human review report."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from typing import Any


def render_html(report: Mapping[str, Any]) -> str:
    title = str(report["title"])
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{_h(title)}</title>",
            "<style>",
            _css(),
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            f"<h1>{_h(title)}</h1>",
            _first_view(report),
            _review_queue_section(report["review_queue"]),
            _target_burden_section(report["target_reliability"]),
            _root_cause_section(report["root_cause"]),
            _consistency_section(report["consistency"]),
            _full_target_reliability_details(report["target_reliability"]),
            _sources_section(report["sources"]),
            "</main>",
            "</body>",
            "</html>",
        )
    )


def _first_view(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    consistency = report["consistency"]
    root_cause = report["root_cause"]
    verdict = str(report["verdict"])
    run_label = str(report.get("run_label", ""))
    return (
        '<section class="triage-board">'
        '<div class="triage-header">'
        '<div class="verdict-block">'
        '<span class="eyebrow">Run Verdict</span>'
        f'<div class="verdict verdict-{_h(verdict.lower())}">'
        f"Run Verdict: {_h(verdict)}</div>"
        f'<p class="verdict-message">{_h(report["verdict_message"])}</p>'
        "</div>"
        + (
            '<div class="run-badge"><span>Run</span>'
            f"<strong>{_h(run_label)}</strong></div>"
            if run_label
            else ""
        )
        + "</div>"
        '<div class="triage-layout">'
        '<div><h2>Action Summary</h2>'
        + _action_summary(root_cause, consistency)
        + "</div>"
        '<div><h2>Evidence Health</h2>'
        + _evidence_health(summary, consistency, root_cause)
        + "</div>"
        "</div></section>"
    )


def _target_burden_section(targets: Sequence[Mapping[str, Any]]) -> str:
    top_targets = targets[:10]
    body = "".join(_target_row(target, compact=True) for target in top_targets)
    return _section(
        "Target Burden Map",
        '<p class="muted">Top 10 targets by manual-review burden.</p>'
        + (body if body else '<p class="muted">No targets.</p>'),
    )


def _full_target_reliability_details(targets: Sequence[Mapping[str, Any]]) -> str:
    rows = "".join(_target_row(target, compact=False) for target in targets)
    body = rows if rows else '<p class="muted">No targets.</p>'
    return (
        '<details class="map-details">'
        '<summary>Full Target Reliability Map</summary>'
        + body
        + "</details>"
    )


def _target_row(target: Mapping[str, Any], *, compact: bool) -> str:
    risk = (
        ""
        if compact
        else f'<p class="risk">{_h(target.get("top_risk_reasons", ""))}</p>'
    )
    return (
        '<article class="target-row">'
        f'<header><strong>{_h(target["target_label"])}</strong>'
        f'<span>{_h(target.get("role", ""))}</span></header>'
        + _stacked_bar(
            (
                ("eligible", target["benchmark_eligible_count"], "pass"),
                (
                    "review-positive",
                    target["targeted_review_positive_count"],
                    "review-positive",
                ),
                ("review", target["targeted_review_count"], "review"),
                ("negative", target["targeted_negative_count"], "neutral"),
            )
        )
        + risk
        + "</article>"
    )


def _target_reliability_section(targets: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    for target in targets:
        rows.append(_target_row(target, compact=False))
    body = "".join(rows) if rows else '<p class="muted">No targets.</p>'
    return _section("Target Reliability Map", body)


def _action_summary(
    root_cause: Mapping[str, Any],
    consistency: Mapping[str, Any],
) -> str:
    mismatch_total = int(consistency["mismatch_count"]) + _missing_total(consistency)
    items = []
    if mismatch_total:
        items.append(
            _action_card(
                title="Fix evidence chain",
                count=mismatch_total,
                label="cross-report mismatch or missing row",
                tone="fail",
            )
        )
    items.extend(
        (
            _action_card(
                title="Inspect now",
                count=_bucket_count(root_cause, "ppm_gate_fail"),
                label="ppm_gate_fail",
                tone="fail",
            ),
            _action_card(
                title="Check MS2 timing",
                count=_bucket_count(root_cause, "off_apex_ms2"),
                label="off_apex_ms2",
                tone="warn",
            ),
            _action_card(
                title="Systemic dropout context",
                count=_bucket_count(root_cause, "no_diagnostic_product"),
                label="no_diagnostic_product",
                tone="audit",
            ),
        )
    )
    return '<div class="action-grid">' + "".join(items) + "</div>"


def _action_card(*, title: str, count: int, label: str, tone: str) -> str:
    return (
        f'<article class="action-card tone-{_h(tone)}">'
        f"<span>{_h(title)}</span>"
        f"<strong>{_h(count)}</strong>"
        f"<em>{_h(label)}</em>"
        "</article>"
    )


def _evidence_health(
    summary: Mapping[str, Any],
    consistency: Mapping[str, Any],
    root_cause: Mapping[str, Any],
) -> str:
    return (
        '<div class="health-grid">'
        + _health_item(
            label="Cross-report",
            value=_consistency_text(consistency),
            tone="pass" if int(consistency["mismatch_count"]) == 0 else "fail",
        )
        + _health_item(
            label="Missing candidate",
            value=consistency["missing_candidate_count"],
            tone="pass" if int(consistency["missing_candidate_count"]) == 0 else "fail",
        )
        + _health_item(
            label="Missing reliability",
            value=consistency["missing_reliability_count"],
            tone=(
                "pass"
                if int(consistency["missing_reliability_count"]) == 0
                else "fail"
            ),
        )
        + _health_item(
            label="Review-positive",
            value=summary["review_positive_count"],
            tone="warn" if int(summary["review_positive_count"]) else "pass",
        )
        + _health_item(
            label="Root-cause rows",
            value=root_cause["included_count"],
            tone="warn" if int(root_cause["included_count"]) else "pass",
        )
        + _health_item(
            label="Eligible",
            value=summary["eligible_count"],
            tone="pass",
        )
        + "</div>"
    )


def _health_item(*, label: str, value: Any, tone: str) -> str:
    return (
        f'<div class="health-item tone-{_h(tone)}">'
        f"<span>{_h(label)}</span><strong>{_h(value)}</strong>"
        "</div>"
    )


def _root_cause_section(root_cause: Mapping[str, Any]) -> str:
    target_rows = "".join(
        f'<span class="chip">{_h(label)} {_h(value)}</span>'
        for label, value in root_cause["top_targets"]
    )
    return _section(
        "NL Dropout Root Cause Detail",
        _metric_grid(
            (
                ("Rows checked", root_cause["rows_checked"]),
                ("Review-positive", root_cause["review_positive_count"]),
                ("Included", root_cause["included_count"]),
                ("Missing candidate", root_cause["missing_candidate_count"]),
            )
        )
        + _bar_list(
            (
                (label, value, _bucket_tone(label))
                for label, value in root_cause["bucket_counts"].items()
            ),
            empty="No targeted review-positive root-cause rows.",
        )
        + '<h3>Top Targets</h3><div class="chips">'
        + (target_rows or '<span class="muted">No target burden.</span>')
        + "</div>",
    )


def _consistency_section(consistency: Mapping[str, Any]) -> str:
    issue_rows = "".join(
        f'<span class="chip tone-fail">{_h(label)} {_h(value)}</span>'
        for label, value in consistency["issue_counts"].items()
    )
    issue_block = (
        '<h3>Top Issue Types</h3><div class="chips">'
        + (issue_rows or '<span class="muted">No mismatch issue types.</span>')
        + "</div>"
    )
    return _section(
        "Evidence Consistency",
        f'<p class="headline">{_h(_consistency_text(consistency))}</p>'
        + _metric_grid(
            (
                ("Rows checked", consistency["rows_checked"]),
                ("Consistent", consistency["consistent_count"]),
                ("Mismatch", consistency["mismatch_count"]),
                ("Missing candidate", consistency["missing_candidate_count"]),
                ("Missing reliability", consistency["missing_reliability_count"]),
            )
        )
        + issue_block,
    )


def _review_queue_section(queue: Sequence[Mapping[str, Any]]) -> str:
    if not queue:
        return _section(
            "Review Queue",
            '<p class="muted">No immediate manual review cases.</p>',
        )
    cards = "".join(_review_card(row) for row in queue)
    return _section(
        "Priority Review Queue",
        '<p class="muted">Top 30 cases, ordered by evidence-chain risk first. '
        "Full row tables are intentionally "
        "kept in TSV artifacts.</p>"
        + '<div class="queue-grid">'
        + cards
        + "</div>",
    )


def _review_card(row: Mapping[str, Any]) -> str:
    issue = str(row["root_cause"])
    return (
        f'<article class="queue-card queue-{_h(_issue_tone(issue))}">'
        "<header><div>"
        f'<strong>{_h(row["target"])}</strong>'
        f'<p>{_h(row["sample"])}</p></div>'
        f'<span class="mz">m/z {_h(row["mz"])}</span></header>'
        '<div class="issue-line">'
        f'<span class="issue-pill tone-{_h(_issue_tone(issue))}">{_h(issue)}</span>'
        f'<span class="state-pill">{_h(row["state"])}</span>'
        "</div>"
        + _mini_fields(
            (
                ("area ratio", row["area_ratio"]),
                ("apex delta", row["apex_delta_min"]),
                ("loss ppm", row["best_or_nearest_loss_ppm"]),
            )
        )
        + '<details class="row-source"><summary>row locator</summary>'
        + f'<p>{_h(row["source_file"])}</p>'
        + f'<p>source_key={_h(row["source_key"])}</p>'
        + f'<p>{_h(row["row_locator"])}</p>'
        + "</details>"
        + "</article>"
    )


def _sources_section(sources: Mapping[str, Any]) -> str:
    rows = "".join(
        f"<li><b>{_h(key)}</b>: {_h(value)}</li>"
        for key, value in sources.items()
        if value
    )
    return (
        '<details class="sources"><summary>Source artifacts</summary>'
        f"<ul>{rows}</ul></details>"
    )


def _section(title: str, body: str) -> str:
    return f"<section><h2>{_h(title)}</h2>{body}</section>"


def _status_cards(items: Sequence[tuple[str, Any, str]]) -> str:
    cards = "".join(
        f'<div class="status-card tone-{_h(tone)}">'
        f"<span>{_h(label)}</span><strong>{_h(value)}</strong></div>"
        for label, value, tone in items
    )
    return f'<div class="status-cards">{cards}</div>'


def _metric_grid(items: Sequence[tuple[str, Any]]) -> str:
    body = "".join(
        f"<div><dt>{_h(label)}</dt><dd>{_h(value)}</dd></div>"
        for label, value in items
    )
    return f'<dl class="metrics">{body}</dl>'


def _stacked_bar(segments: Sequence[tuple[str, Any, str]]) -> str:
    values = [(label, _float(value), tone) for label, value, tone in segments]
    total = sum(value for _label, value, _tone in values)
    if total <= 0:
        return '<p class="muted">No values to chart.</p>'
    bars = "".join(
        f'<span class="stack-segment tone-{_h(tone)}" '
        f'style="width:{_percent(value, total):.3f}%"></span>'
        for _label, value, tone in values
        if value > 0
    )
    legend = " ".join(
        f'<span><i class="legend-dot tone-{_h(tone)}"></i>'
        f"{_h(label)} {_h(_fmt(value))}</span>"
        for label, value, tone in values
        if value > 0
    )
    return f'<div class="stacked-bar">{bars}</div><div class="legend">{legend}</div>'


def _bar_list(
    rows: Sequence[tuple[str, Any, str]] | Any,
    *,
    empty: str,
) -> str:
    values = [(label, _float(value), tone) for label, value, tone in rows]
    max_value = max((value for _label, value, _tone in values), default=0.0)
    if max_value <= 0:
        return f'<p class="muted">{_h(empty)}</p>'
    body = "".join(
        '<div class="bar-row">'
        f'<span class="bar-label">{_h(label)} {_h(_fmt(value))}</span>'
        '<span class="bar-track">'
        f'<span class="bar-fill tone-{_h(tone)}" '
        f'style="width:{_percent(value, max_value):.3f}%"></span>'
        "</span>"
        "</div>"
        for label, value, tone in values
        if value > 0
    )
    return f'<div class="bar-list">{body}</div>'


def _mini_fields(items: Sequence[tuple[str, Any]]) -> str:
    fields = "".join(
        f"<span>{_h(label)}: <b>{_h(value)}</b></span>"
        for label, value in items
        if str(value)
    )
    return f'<div class="mini-fields">{fields}</div>' if fields else ""


def _consistency_text(consistency: Mapping[str, Any]) -> str:
    return (
        f"{consistency['consistent_count']} / {consistency['rows_checked']} "
        f"consistent"
    )


def _missing_total(consistency: Mapping[str, Any]) -> int:
    return int(consistency["missing_candidate_count"]) + int(
        consistency["missing_reliability_count"]
    )


def _bucket_tone(bucket: str) -> str:
    if bucket == "ppm_gate_fail":
        return "fail"
    if bucket == "off_apex_ms2":
        return "warn"
    if bucket == "no_diagnostic_product":
        return "audit"
    return "neutral"


def _issue_tone(issue: str) -> str:
    if issue in {
        "ppm_gate_fail",
        "targeted_review_candidate_suggests_dropout",
        "targeted_clean_candidate_conflict",
        "review_positive_not_supported_by_candidate",
        "targeted_negative_candidate_has_peak",
        "multiple_selected_candidates",
    }:
        return "fail"
    if issue in {
        "off_apex_ms2",
        "missing_selected_candidate",
        "missing_targeted_reliability",
    }:
        return "warn"
    if issue == "no_diagnostic_product":
        return "audit"
    return "neutral"


def _bucket_count(root_cause: Mapping[str, Any], bucket: str) -> int:
    return int(root_cause["bucket_counts"].get(bucket, 0))


def _percent(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min((value / total) * 100.0, 100.0))


def _float(value: Any) -> float:
    try:
        number = float(str(value))
    except ValueError:
        return 0.0
    return number if math.isfinite(number) else 0.0


def _fmt(value: Any) -> str:
    number = _float(value)
    if number.is_integer():
        return f"{number:.0f}"
    return f"{number:.4g}"


def _h(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
:root {
  color-scheme: light;
  font-family: "Aptos", "Segoe UI", sans-serif;
  --ink: #17202a;
  --muted: #64748b;
  --paper: #fbfcf9;
  --panel: #ffffff;
  --line: #d8ddd7;
  --pass: #2f855a;
  --review-positive: #dc2626;
  --review: #d97706;
  --audit: #64748b;
  --neutral: #8a948f;
  color: var(--ink);
  background: #f4f5f2;
}
body { margin: 0; }
main {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 48px;
}
h1 { margin: 0 0 16px; font-size: 30px; }
h2 { margin: 0 0 14px; font-size: 20px; }
h3 { margin: 18px 0 8px; font-size: 15px; }
section {
  background: #fff;
  border: 1px solid #d8ddd7;
  border-radius: 8px;
  margin-top: 18px;
  padding: 18px;
}
.triage-board {
  min-height: 420px;
  background: #15201b;
  border: 0;
  color: #f8fafc;
  padding: 24px;
}
.triage-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.triage-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
  gap: 18px;
  margin-top: 24px;
}
.eyebrow {
  display: block;
  color: #a7b4ad;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.verdict {
  display: inline-block;
  border-radius: 6px;
  font-weight: 800;
  margin-top: 7px;
  padding: 8px 12px;
  font-size: 36px;
  line-height: 1;
}
.verdict-pass { background: #dcfce7; color: #14532d; }
.verdict-warn { background: #fef3c7; color: #78350f; }
.verdict-fail { background: #fee2e2; color: #7f1d1d; }
.verdict-message {
  color: #d2dbd5;
  margin: 12px 0 0;
}
.run-badge {
  min-width: 120px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 8px;
  padding: 10px 12px;
  text-align: right;
}
.run-badge span {
  display: block;
  color: #a7b4ad;
  font-size: 12px;
}
.run-badge strong { display: block; margin-top: 4px; font-size: 20px; }
.muted { color: var(--muted); }
.action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(150px, 1fr));
  gap: 12px;
}
.action-card {
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-left-width: 7px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.07);
  min-height: 132px;
  padding: 14px;
}
.action-card span {
  display: block;
  color: #dbe4de;
  font-size: 13px;
  font-weight: 700;
}
.action-card strong {
  display: block;
  margin: 10px 0 4px;
  font-size: 46px;
  line-height: 1;
}
.action-card em {
  color: #aebbb4;
  font-size: 12px;
  font-style: normal;
}
.health-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(130px, 1fr));
  gap: 10px;
}
.health-item {
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-left-width: 5px;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.06);
  padding: 10px;
}
.health-item span {
  display: block;
  color: #aebbb4;
  font-size: 12px;
}
.health-item strong {
  display: block;
  margin-top: 4px;
  color: #f8fafc;
  overflow-wrap: anywhere;
}
.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.status-card {
  border-left: 6px solid #87929a;
  border-radius: 7px;
  background: #fbfcf9;
  padding: 10px 12px;
}
.status-card span { display: block; color: #59636f; font-size: 12px; }
.status-card strong { display: block; margin-top: 4px; font-size: 24px; }
.first-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
  margin-top: 16px;
}
.visual-panel {
  border: 1px solid #d9ded8;
  border-radius: 8px;
  background: #fbfcf9;
  padding: 14px;
}
.target-row, .queue-card {
  border: 1px solid #e1e6df;
  border-radius: 8px;
  padding: 12px;
  margin-top: 10px;
}
.queue-card {
  border-left-width: 7px;
  background: #fff;
}
.queue-card header {
  align-items: flex-start;
}
.target-row header, .queue-card header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.queue-card header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.mz {
  color: #475569;
  font-size: 12px;
  white-space: nowrap;
}
.risk, .source {
  color: var(--muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.issue-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.issue-pill, .state-pill {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 700;
}
.state-pill {
  background: #eef2f7;
  color: #475569;
}
.row-source {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}
.row-source summary {
  cursor: pointer;
  font-weight: 700;
}
.row-source p { margin: 4px 0; overflow-wrap: anywhere; }
.stacked-bar {
  display: flex;
  height: 22px;
  overflow: hidden;
  border-radius: 999px;
  background: #e7e9e4;
  border: 1px solid #d5d9d1;
  margin-top: 8px;
}
.stack-segment { min-width: 2px; }
.legend, .chips, .mini-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 8px;
  color: #4b5563;
  font-size: 12px;
}
.legend span, .chip { display: inline-flex; align-items: center; gap: 6px; }
.chip {
  background: #f1f5f9;
  border-radius: 999px;
  padding: 4px 8px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}
.bar-list { display: grid; gap: 8px; margin-top: 8px; }
.bar-row {
  display: grid;
  grid-template-columns: minmax(150px, 260px) 1fr;
  gap: 10px;
  align-items: center;
}
.bar-label { overflow-wrap: anywhere; font-size: 12px; color: #334155; }
.bar-track {
  display: block;
  height: 14px;
  border-radius: 999px;
  background: #e8ece7;
  overflow: hidden;
}
.bar-fill { display: block; height: 100%; border-radius: 999px; }
.queue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  margin: 12px 0;
}
.metrics div {
  border: 1px solid #e5e8e2;
  border-radius: 6px;
  padding: 10px;
}
dt { color: #64748b; font-size: 12px; margin-bottom: 5px; }
dd { margin: 0; font-weight: 700; overflow-wrap: anywhere; }
.tone-pass { border-color: var(--pass); }
.tone-pass.stack-segment, .tone-pass.bar-fill, .tone-pass.legend-dot {
  background: var(--pass);
}
.tone-review-positive { border-color: var(--review-positive); }
.tone-review-positive.stack-segment,
.tone-review-positive.bar-fill,
.tone-review-positive.legend-dot {
  background: var(--review-positive);
}
.tone-review { border-color: var(--review); }
.tone-review.stack-segment, .tone-review.bar-fill, .tone-review.legend-dot {
  background: var(--review);
}
.tone-warn { border-color: var(--review); }
.tone-warn.stack-segment, .tone-warn.bar-fill, .tone-warn.legend-dot {
  background: var(--review);
}
.tone-fail { border-color: var(--review-positive); }
.tone-fail.stack-segment, .tone-fail.bar-fill, .tone-fail.legend-dot {
  background: var(--review-positive);
}
.tone-audit { border-color: var(--audit); }
.tone-audit.stack-segment, .tone-audit.bar-fill, .tone-audit.legend-dot {
  background: var(--audit);
}
.tone-neutral { border-color: var(--neutral); }
.tone-neutral.stack-segment, .tone-neutral.bar-fill, .tone-neutral.legend-dot {
  background: var(--neutral);
}
.issue-pill.tone-fail { background: #fee2e2; color: #7f1d1d; }
.issue-pill.tone-warn { background: #fef3c7; color: #78350f; }
.issue-pill.tone-audit { background: #e2e8f0; color: #334155; }
.issue-pill.tone-neutral { background: #eef2f7; color: #475569; }
.queue-fail { border-left-color: var(--review-positive); }
.queue-warn { border-left-color: var(--review); }
.queue-audit { border-left-color: var(--audit); }
.queue-neutral { border-left-color: var(--neutral); }
.map-details {
  margin-top: 18px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 18px;
}
.map-details summary {
  cursor: pointer;
  font-weight: 800;
}
details.sources {
  margin-top: 18px;
  color: #334155;
}
details.sources summary { cursor: pointer; font-weight: 700; }
@media (max-width: 820px) {
  .triage-layout { grid-template-columns: 1fr; }
  .action-grid { grid-template-columns: 1fr; }
  .triage-header { display: block; }
  .run-badge { margin-top: 14px; text-align: left; }
}
""".strip()
