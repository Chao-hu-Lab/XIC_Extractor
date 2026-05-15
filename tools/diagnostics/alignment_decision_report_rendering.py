"""HTML rendering for the alignment decision diagnostic report."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from typing import Any


def render_html(report: Mapping[str, Any]) -> str:
    verdict = str(report["verdict"])
    title = "Alignment Decision Report"
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            "<title>Alignment Decision Report</title>",
            "<style>",
            _css(),
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            f"<h1>{_h(title)}</h1>",
            (
                f'<div class="verdict verdict-{_h(verdict.lower())}">'
                f"Run Verdict: {_h(verdict)}</div>"
            ),
            _run_verdict_section(report),
            _istd_section(report["istd"]),
            _cleanliness_section(report["cleanliness"]),
            _economics_section(report["economics"]),
            _rt_normalization_section(report["rt_normalization"]),
            "</main>",
            "</body>",
            "</html>",
        )
    )


def _run_verdict_section(report: Mapping[str, Any]) -> str:
    run = report["run"]
    identity = run["identity_counts"]
    runtime = run["runtime"]
    top_stage_rows = [
        (
            row.get("stage", ""),
            _fmt(row.get("elapsed_sec", "")),
        )
        for row in runtime.get("top_stages", ())
        if isinstance(row, Mapping)
    ]
    runtime_table = ""
    if top_stage_rows:
        runtime_table = "<h3>Runtime Stages</h3>" + _bar_list(
            (
                (str(row[0]), _float_value(row[1], default=0.0), "runtime")
                for row in top_stage_rows
            ),
            empty="Runtime stages not provided.",
        ) + _details_table(
            ("Stage", "Elapsed Sec"),
            top_stage_rows,
            label="Runtime stage table",
        )
    visual = (
        '<div class="visual-panel">'
        + _status_cards(
            (
                ("Matrix Rows", run["matrix_row_count"], "neutral"),
                ("Samples", run["sample_count"], "neutral"),
                ("ISTD Pass", run["istd_pass_count"], "pass"),
                ("ISTD Known", run["istd_known_count"], "warn"),
                ("ISTD Fail", run["istd_fail_count"], "fail"),
            )
        )
        + "<h3>Identity Mix</h3>"
        + _stacked_bar(
            (
                (
                    "production_family",
                    identity.get("production_family", 0),
                    "production",
                ),
                (
                    "provisional_discovery",
                    identity.get("provisional_discovery", 0),
                    "provisional",
                ),
                ("audit_family", identity.get("audit_family", 0), "audit"),
            )
        )
        + "</div>"
    )
    return _section(
        "Run Verdict",
        visual
        + _metric_grid(
            (
                ("Verdict", report["verdict"]),
                ("Alignment Dir", report["alignment_dir"]),
                ("Matrix Rows", run["matrix_row_count"]),
                ("Samples", run["sample_count"]),
                ("production_family", identity.get("production_family", 0)),
                ("provisional_discovery", identity.get("provisional_discovery", 0)),
                ("audit_family", identity.get("audit_family", 0)),
                ("ISTD Pass", run["istd_pass_count"]),
                ("ISTD Known", run["istd_known_count"]),
                ("ISTD Fail", run["istd_fail_count"]),
                ("Runtime", _runtime_text(runtime)),
            )
        )
        + runtime_table,
    )


def _istd_section(istd: Mapping[str, Any]) -> str:
    if not istd["provided"]:
        return _section("ISTD Benchmark", _not_provided_html(istd["reason"]))
    tiles = "".join(_istd_tile(row) for row in istd["rows"])
    headers = (
        "Target",
        "Status",
        "Known",
        "Selected Family",
        "Primary Hits",
        "RT Mean Delta",
        "RT p95",
        "Spearman",
        "Pearson",
        "Coverage",
        "Failure Modes",
    )
    rows = [
        (
            row["target_label"],
            row["status"],
            "KNOWN" if row["known"] else "",
            row["selected_family"],
            row["primary_hit_count"],
            _fmt(row["rt_mean_delta"]),
            _fmt(row["rt_p95"]),
            _fmt(row["spearman"]),
            _fmt(row["pearson"]),
            row["coverage"],
            row["failure_modes"],
        )
        for row in istd["rows"]
    ]
    return _section(
        "ISTD Benchmark",
        f'<div class="istd-board">{tiles}</div>'
        + _details_table(headers, rows, label="ISTD benchmark table"),
    )


def _cleanliness_section(cleanliness: Mapping[str, Any]) -> str:
    flags = cleanliness["flag_counts"]
    identity = cleanliness["identity_counts"]
    visual = (
        '<div class="visual-panel">'
        + "<h3>Primary Matrix Warning Load</h3>"
        + _bar_list(
            (
                (
                    "Zero-present rows",
                    cleanliness["zero_present_row_count"],
                    "fail",
                ),
                (
                    "duplicate_claim_pressure",
                    flags["duplicate_claim_pressure"],
                    "warn",
                ),
                (
                    "high_backfill_dependency",
                    flags["high_backfill_dependency"],
                    "warn",
                ),
                ("rescue_heavy", flags["rescue_heavy"], "rescue"),
            ),
            empty="No matrix cleanliness warnings.",
        )
        + "<h3>All Review Row Identity Mix</h3>"
        + _stacked_bar(
            (
                (
                    "production_family",
                    identity.get("production_family", 0),
                    "production",
                ),
                (
                    "provisional_discovery",
                    identity.get("provisional_discovery", 0),
                    "provisional",
                ),
                ("audit_family", identity.get("audit_family", 0), "audit"),
            )
        )
        + "</div>"
    )
    metrics = _metric_grid(
        (
            ("Primary Rows", cleanliness["primary_row_count"]),
            ("Review Primary Rows", cleanliness["review_primary_row_count"]),
            ("Zero-present Rows", cleanliness["zero_present_row_count"]),
            ("duplicate_claim_pressure", flags["duplicate_claim_pressure"]),
            ("high_backfill_dependency", flags["high_backfill_dependency"]),
            ("rescue_heavy", flags["rescue_heavy"]),
        )
    )
    rows = [
        (
            row["feature_family_id"],
            row["identity_decision"],
            row["present_rate"],
            row["detected_count"],
            row["accepted_rescue_count"],
            row["row_flags"],
            row["warning"],
        )
        for row in cleanliness["top_warning_rows"]
    ]
    table = _details_table(
        (
            "Feature",
            "Identity",
            "Present Rate",
            "Detected",
            "Accepted Rescue",
            "Flags",
            "Warning",
        ),
        rows,
        empty="No primary cleanliness warnings.",
        label="Top warning rows table",
    )
    return _section("Matrix Cleanliness", visual + metrics + table)


def _economics_section(economics: Mapping[str, Any]) -> str:
    if not economics["provided"]:
        return _section("Backfill Economics", _not_provided_html(economics["reason"]))
    totals = economics["totals"]
    request_total = _float_value(totals.get("request_target_count", 0), default=0.0)
    production = _float_value(
        totals.get("production_request_target_count", 0),
        default=0.0,
    )
    non_primary = _float_value(
        totals.get("non_primary_request_target_count", 0),
        default=0.0,
    )
    rescued = _float_value(totals.get("rescued_target_count", 0), default=0.0)
    absent = _float_value(totals.get("absent_target_count", 0), default=0.0)
    duplicate = _float_value(
        totals.get("duplicate_assigned_target_count", 0),
        default=0.0,
    )
    outcome_other = max(request_total - rescued - absent - duplicate, 0.0)
    visual = (
        '<div class="visual-panel">'
        + "<h3>Request Ownership</h3>"
        + _stacked_bar(
            (
                ("Production", production, "production"),
                ("Non-primary", non_primary, "audit"),
            )
        )
        + "<h3>Request Outcomes</h3>"
        + _stacked_bar(
            (
                ("Rescued", rescued, "production"),
                ("Absent", absent, "fail"),
                ("Duplicate", duplicate, "warn"),
                ("Other", outcome_other, "neutral"),
            )
        )
        + "<h3>Largest Feature Costs</h3>"
        + _bar_list(
            (
                (
                    str(row.get("feature_family_id", "")),
                    _float_value(
                        row.get("request_extract_count_estimate", 0),
                        default=0.0,
                    ),
                    _identity_color(str(row.get("identity_decision", ""))),
                )
                for row in economics["top_expensive_families"][:12]
            ),
            empty="No feature-level economics rows.",
        )
        + "</div>"
    )
    metrics = _metric_grid(
        (
            ("Request Targets", totals.get("request_target_count", 0)),
            ("Extract Estimate", totals.get("request_extract_count_estimate", 0)),
            (
                "Production Requests",
                totals.get("production_request_target_count", 0),
            ),
            ("Non-primary Requests", totals.get("non_primary_request_target_count", 0)),
            ("Rescued Targets", totals.get("rescued_target_count", 0)),
            ("Absent Targets", totals.get("absent_target_count", 0)),
            ("Duplicate Targets", totals.get("duplicate_assigned_target_count", 0)),
        )
    )
    summary_rows = [
        (
            row.get("identity_decision", ""),
            row.get("neutral_loss_tag", ""),
            row.get("include_in_primary_matrix", ""),
            row.get("eligible_group_family_count", ""),
            row.get("request_target_count", ""),
            row.get("request_extract_count_estimate", ""),
            row.get("rescued_target_count", ""),
            row.get("absent_target_count", ""),
            row.get("duplicate_assigned_target_count", ""),
        )
        for row in economics["summary"]
    ]
    feature_rows = [
        (
            row.get("feature_family_id", ""),
            row.get("neutral_loss_tag", ""),
            row.get("identity_decision", ""),
            row.get("include_in_primary_matrix", ""),
            row.get("request_target_count", ""),
            row.get("request_extract_count_estimate", ""),
            row.get("rescued_target_count", ""),
            row.get("absent_target_count", ""),
            row.get("duplicate_assigned_target_count", ""),
            row.get("row_flags", ""),
        )
        for row in economics["top_expensive_families"]
    ]
    return _section(
        "Backfill Economics",
        visual
        + metrics
        + "<h3>By Identity / Tag</h3>"
        + _bar_list(
            (
                (
                    f"{row.get('identity_decision', '')} / "
                    f"{row.get('neutral_loss_tag', '')}",
                    _float_value(row.get("request_target_count", 0), default=0.0),
                    _identity_color(str(row.get("identity_decision", ""))),
                )
                for row in economics["summary"]
            ),
            empty="No eligible backfill requests.",
        )
        + _details_table(
            (
                "Identity",
                "Tag",
                "Primary",
                "Families",
                "Targets",
                "Extracts",
                "Rescued",
                "Absent",
                "Duplicate",
            ),
            summary_rows,
            empty="No eligible backfill requests.",
            label="Backfill identity and tag table",
        )
        + "<h3>Top Expensive Families</h3>"
        + _details_table(
            (
                "Feature",
                "Tag",
                "Identity",
                "Primary",
                "Targets",
                "Extracts",
                "Rescued",
                "Absent",
                "Duplicate",
                "Flags",
            ),
            feature_rows,
            empty="No feature-level economics rows.",
            label="Top expensive families table",
        ),
    )


def _rt_normalization_section(rt_norm: Mapping[str, Any]) -> str:
    if not rt_norm.get("provided"):
        return ""
    loo_rows = [
        (
            str(row.get("target_label", "")),
            _float_value(row.get("p95_abs_error_min", 0), default=0.0),
            "pass" if str(row.get("status", "")).upper() == "PASS" else "warn",
        )
        for row in rt_norm["leave_one_anchor_out"]
    ]
    band_rows: list[tuple[str, float, str]] = []
    for band, counts in rt_norm["rt_band_summary"].items():
        for outcome, tone in (
            ("improved", "production"),
            ("worsened", "fail"),
            ("stable", "neutral"),
            ("unmodelled", "audit"),
        ):
            value = _float_value(counts.get(outcome, 0), default=0.0)
            if value > 0:
                band_rows.append((f"{band} / {outcome}", value, tone))
    metrics = _metric_grid(
        (
            ("Status", rt_norm.get("overall_status", "")),
            ("Reference Source", rt_norm.get("reference_source", "")),
            ("Model Type", rt_norm.get("model_type", "")),
            ("Anchor Labels", rt_norm.get("anchor_label_count", "")),
            ("Modelled Samples", rt_norm.get("modelled_sample_count", "")),
            ("Unmodelled Samples", rt_norm.get("unmodelled_sample_count", "")),
            ("Excluded Anchors", rt_norm.get("excluded_anchor_count", "")),
            (
                "Median RT Range Improvement",
                rt_norm.get("median_rt_range_improvement_min", ""),
            ),
        )
    )
    loo_table_rows = [
        (
            row.get("target_label", ""),
            row.get("status", ""),
            row.get("evaluated_count", ""),
            _fmt(row.get("median_abs_error_min", "")),
            _fmt(row.get("p95_abs_error_min", "")),
            _fmt(row.get("max_abs_error_min", "")),
        )
        for row in rt_norm["leave_one_anchor_out"]
    ]
    return _section(
        "RT Warping Evidence",
        '<div class="visual-panel">'
        + "<h3>RT Band Outcome</h3>"
        + _bar_list(band_rows, empty="No RT band outcome rows.")
        + "<h3>Leave-one-anchor-out p95 error</h3>"
        + _bar_list(loo_rows, empty="No leave-one-anchor-out rows.")
        + "</div>"
        + metrics
        + _details_table(
            (
                "Anchor",
                "Status",
                "Evaluated",
                "Median Abs Error",
                "p95 Abs Error",
                "Max Abs Error",
            ),
            loo_table_rows,
            label="Leave-one-anchor-out table",
            empty="No leave-one-anchor-out rows.",
        ),
    )


def _section(title: str, body: str) -> str:
    return f"<section><h2>{_h(title)}</h2>{body}</section>"


def _metric_grid(items: Sequence[tuple[str, Any]]) -> str:
    body = "".join(
        f"<div><dt>{_h(label)}</dt><dd>{_h(_fmt(value))}</dd></div>"
        for label, value in items
    )
    return f'<dl class="metrics">{body}</dl>'


def _table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    empty: str = "No rows.",
) -> str:
    if not rows:
        return f'<p class="muted">{_h(empty)}</p>'
    head = "".join(f"<th>{_h(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_h(_fmt(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _details_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    label: str,
    empty: str = "No rows.",
) -> str:
    return (
        f'<details class="data-table"><summary>{_h(label)}</summary>'
        + _table(headers, rows, empty=empty)
        + "</details>"
    )


def _status_cards(items: Sequence[tuple[str, Any, str]]) -> str:
    cards = "".join(
        f'<div class="status-card tone-{_h(tone)}">'
        f"<span>{_h(label)}</span><strong>{_h(_fmt(value))}</strong></div>"
        for label, value, tone in items
    )
    return f'<div class="status-cards">{cards}</div>'


def _stacked_bar(segments: Sequence[tuple[str, Any, str]]) -> str:
    values = [
        (label, max(_float_value(value, default=0.0), 0.0), tone)
        for label, value, tone in segments
    ]
    total = sum(value for _label, value, _tone in values)
    if total <= 0:
        return '<p class="muted">No values to chart.</p>'
    bars = "".join(
        f'<span class="stack-segment tone-{_h(tone)}" '
        f'style="width:{_percent(value, total):.3f}%"></span>'
        for _label, value, tone in values
        if value > 0
    )
    legend = "".join(
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
    values = [
        (label, max(_float_value(value, default=0.0), 0.0), tone)
        for label, value, tone in rows
    ]
    if not values:
        return f'<p class="muted">{_h(empty)}</p>'
    max_value = max((value for _label, value, _tone in values), default=0.0)
    if max_value <= 0:
        return f'<p class="muted">{_h(empty)}</p>'
    body = "".join(
        '<div class="bar-row">'
        f'<span class="bar-label">{_h(label)}</span>'
        '<span class="bar-track">'
        f'<span class="bar-fill tone-{_h(tone)}" '
        f'style="width:{_percent(value, max_value):.3f}%"></span>'
        "</span>"
        f'<strong>{_h(_fmt(value))}</strong>'
        "</div>"
        for label, value, tone in values
    )
    return f'<div class="bar-list">{body}</div>'


def _istd_tile(row: Mapping[str, Any]) -> str:
    status = str(row.get("status", "UNKNOWN")).lower()
    if row.get("known"):
        tone = "warn"
    elif status == "pass":
        tone = "pass"
    else:
        tone = "fail"
    known = '<span class="known-chip">KNOWN</span>' if row.get("known") else ""
    spearman = _float_value(row.get("spearman", ""), default=0.0)
    pearson = _float_value(row.get("pearson", ""), default=0.0)
    rt_p95 = _float_value(row.get("rt_p95", ""), default=0.0)
    rt_score = max(0.0, 1.0 - min(rt_p95 / 0.30, 1.0))
    return (
        f'<article class="istd-tile tone-{_h(tone)}">'
        f"<header><strong>{_h(row.get('target_label', ''))}</strong>{known}</header>"
        f'<div class="tile-meta">{_h(row.get("status", ""))} · '
        f'{_h(row.get("selected_family", ""))}</div>'
        + _mini_meter("Spearman", spearman)
        + _mini_meter("Pearson", pearson)
        + _mini_meter("RT p95 score", rt_score)
        + f'<div class="tile-foot">{_h(row.get("coverage", ""))}</div>'
        + f'<div class="tile-foot">{_h(row.get("failure_modes", ""))}</div>'
        "</article>"
    )


def _mini_meter(label: str, value: float) -> str:
    clamped = max(0.0, min(value, 1.0))
    return (
        '<div class="mini-meter">'
        f"<span>{_h(label)}</span>"
        '<span class="mini-track">'
        f'<span style="width:{clamped * 100:.3f}%"></span>'
        "</span>"
        f"<b>{_h(_fmt(value))}</b>"
        "</div>"
    )


def _identity_color(identity_decision: str) -> str:
    if identity_decision == "production_family":
        return "production"
    if identity_decision == "provisional_discovery":
        return "provisional"
    if identity_decision == "audit_family":
        return "audit"
    return "neutral"


def _percent(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min((value / total) * 100.0, 100.0))


def _not_provided_html(reason: str) -> str:
    return f'<p class="not-provided">Not provided: {_h(reason)}</p>'

def _runtime_text(runtime: Mapping[str, Any]) -> str:
    if not runtime:
        return "Not provided"
    total = _float_value(runtime.get("total_elapsed_sec", ""), default=0.0)
    pipeline = runtime.get("pipeline", "")
    if total <= 0:
        return str(pipeline or "Provided")
    return f"{pipeline} {_fmt(total)} sec".strip()


def _float_value(value: Any, *, default: float) -> float:
    try:
        number = float(str(value))
    except ValueError:
        return default
    return number if math.isfinite(number) else default


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if abs(value) >= 1000 and value.is_integer():
            return f"{value:,.0f}"
        return f"{value:.4g}"
    text = str(value)
    try:
        number = float(text)
    except ValueError:
        return text
    if not math.isfinite(number):
        return text
    if abs(number) >= 1000 and number.is_integer():
        return f"{number:,.0f}"
    if any(ch in text for ch in ".eE"):
        return f"{number:.4g}"
    return text


def _h(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
:root {
  color-scheme: light;
  font-family: "Aptos", "Segoe UI", sans-serif;
  color: #17202a;
  background: #f3f4f1;
}
body {
  margin: 0;
}
main {
  max-width: 1240px;
  margin: 0 auto;
  padding: 30px 28px 52px;
}
h1 {
  margin: 0 0 16px;
  font-size: 30px;
}
h2 {
  margin: 0 0 16px;
  font-size: 20px;
}
h3 {
  margin: 20px 0 10px;
  font-size: 15px;
}
section {
  background: #fff;
  border: 1px solid #d8ddd7;
  border-radius: 8px;
  margin-top: 18px;
  padding: 18px;
  box-shadow: 0 12px 24px rgba(24, 35, 43, 0.05);
}
.verdict {
  display: inline-block;
  border-radius: 6px;
  font-weight: 700;
  letter-spacing: 0;
  padding: 8px 12px;
}
.verdict-pass { background: #dcfce7; color: #14532d; }
.verdict-warn { background: #fef3c7; color: #78350f; }
.verdict-fail { background: #fee2e2; color: #7f1d1d; }
.visual-panel {
  border: 1px solid #d9ded8;
  border-radius: 8px;
  background: #fbfcf9;
  padding: 14px;
  margin-bottom: 14px;
}
.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(138px, 1fr));
  gap: 10px;
}
.status-card {
  border-left: 6px solid #87929a;
  border-radius: 7px;
  background: #fff;
  padding: 10px 12px;
}
.status-card span {
  display: block;
  color: #59636f;
  font-size: 12px;
}
.status-card strong {
  display: block;
  margin-top: 4px;
  font-size: 24px;
}
.stacked-bar {
  display: flex;
  height: 24px;
  overflow: hidden;
  border-radius: 999px;
  background: #e7e9e4;
  border: 1px solid #d5d9d1;
}
.stack-segment {
  min-width: 2px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-top: 9px;
  color: #4b5563;
  font-size: 12px;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}
.bar-list {
  display: grid;
  gap: 8px;
}
.bar-row {
  display: grid;
  grid-template-columns: minmax(130px, 230px) 1fr minmax(54px, auto);
  gap: 10px;
  align-items: center;
}
.bar-label {
  overflow-wrap: anywhere;
  font-size: 12px;
  color: #334155;
}
.bar-track {
  display: block;
  height: 14px;
  border-radius: 999px;
  background: #e8ece7;
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
}
.bar-row strong {
  text-align: right;
  font-size: 12px;
}
.istd-board {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.istd-tile {
  border: 1px solid #dce1db;
  border-top: 5px solid #87929a;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
}
.istd-tile header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.known-chip {
  background: #fef3c7;
  border-radius: 999px;
  color: #78350f;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 7px;
}
.tile-meta, .tile-foot {
  color: #64748b;
  font-size: 12px;
  margin-top: 6px;
  overflow-wrap: anywhere;
}
.mini-meter {
  display: grid;
  grid-template-columns: 80px 1fr 44px;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
}
.mini-track {
  display: block;
  height: 7px;
  border-radius: 999px;
  background: #e9ece7;
  overflow: hidden;
}
.mini-track span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #2f855a;
}
.tone-pass,
.tone-production { border-color: #2f855a; }
.tone-pass.stack-segment,
.tone-production.stack-segment,
.tone-pass.bar-fill,
.tone-production.bar-fill,
.tone-pass.legend-dot,
.tone-production.legend-dot {
  background: #2f855a;
}
.tone-warn { border-color: #d97706; }
.tone-warn.stack-segment,
.tone-warn.bar-fill,
.tone-warn.legend-dot {
  background: #d97706;
}
.tone-fail { border-color: #dc2626; }
.tone-fail.stack-segment,
.tone-fail.bar-fill,
.tone-fail.legend-dot {
  background: #dc2626;
}
.tone-provisional { border-color: #2563eb; }
.tone-provisional.stack-segment,
.tone-provisional.bar-fill,
.tone-provisional.legend-dot {
  background: #2563eb;
}
.tone-audit { border-color: #6b7280; }
.tone-audit.stack-segment,
.tone-audit.bar-fill,
.tone-audit.legend-dot {
  background: #6b7280;
}
.tone-rescue { border-color: #7c3aed; }
.tone-rescue.stack-segment,
.tone-rescue.bar-fill,
.tone-rescue.legend-dot {
  background: #7c3aed;
}
.tone-neutral { border-color: #64748b; }
.tone-neutral.stack-segment,
.tone-neutral.bar-fill,
.tone-neutral.legend-dot {
  background: #64748b;
}
.tone-runtime { border-color: #0f766e; }
.tone-runtime.stack-segment,
.tone-runtime.bar-fill,
.tone-runtime.legend-dot {
  background: #0f766e;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin: 14px 0 0;
}
.metrics div {
  border: 1px solid #e5e8e2;
  border-radius: 6px;
  padding: 10px;
  min-width: 0;
}
dt {
  color: #64748b;
  font-size: 12px;
  margin-bottom: 5px;
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-weight: 650;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 10px;
}
th, td {
  border-bottom: 1px solid #e5e8e2;
  padding: 7px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
}
.muted, .not-provided {
  color: #64748b;
}
details.data-table {
  margin-top: 14px;
}
details.data-table summary {
  cursor: pointer;
  color: #334155;
  font-weight: 700;
}
""".strip()
