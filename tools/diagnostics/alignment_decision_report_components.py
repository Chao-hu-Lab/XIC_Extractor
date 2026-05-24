"""Reusable HTML components for the alignment decision report."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from typing import Any


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
