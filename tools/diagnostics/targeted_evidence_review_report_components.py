"""Reusable HTML components for the targeted evidence review report."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from typing import Any


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
