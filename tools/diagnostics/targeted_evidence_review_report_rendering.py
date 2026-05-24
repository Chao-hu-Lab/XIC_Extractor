"""HTML section rendering for the targeted evidence human review report."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from tools.diagnostics.targeted_evidence_review_report_components import (
    _bar_list,
    _bucket_count,
    _bucket_tone,
    _consistency_text,
    _h,
    _issue_tone,
    _metric_grid,
    _mini_fields,
    _missing_total,
    _section,
    _stacked_bar,
)
from tools.diagnostics.targeted_evidence_review_report_styles import report_css


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
            report_css(),
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
