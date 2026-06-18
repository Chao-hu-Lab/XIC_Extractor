"""Build the static lockbox review UX bundle.

The bundle is a human-review surface for the 72-case lockbox. It renders
Gaussian15-smoothed trace plots from existing trace JSON artifacts and writes
HTML pages that point back to the label template. It never grants product
authority and never writes matrix/workbook/product outputs.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from xic_extractor.peak_detection.chrom_peak_segments import (
    ChromPeakSegment,
    ChromPeakSegmentPolicy,
    enumerate_chrom_peak_segments,
    select_segment_by_apex_rt,
)
from xic_extractor.peak_detection.ms1_morphology import (
    DEFAULT_GAUSSIAN15_WINDOW_POINTS,
    MS1_MORPHOLOGY_AREA_SOURCE,
    MS1_MORPHOLOGY_TRACE_METHOD,
    gaussian15_morphology_trace,
)
from xic_extractor.tabular_io import (
    file_sha256,
    optional_float,
    read_tsv_required,
    read_tsv_with_header,
    write_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET_INDEX = (
    ROOT / "docs/superpowers/validation/lockbox_review_packets_v1/packet_index.tsv"
)
LABEL_TEMPLATE = ROOT / "docs/superpowers/validation/lockbox_label_template_v1.tsv"
OUTPUT_DIR = ROOT / "docs/superpowers/validation/lockbox_static_review_v1"

SCHEMA_VERSION = "lockbox_static_review_bundle_v1"
PLOT_STATUS_PLOTTED = "plotted_gaussian15"
PLOT_STATUS_BOUNDARY_UNAVAILABLE = "gaussian_review_boundary_unavailable"
NO_AUTHORITY = "FALSE"

BUNDLE_INDEX_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "case_html_path",
    "review_plot_png_path",
    "plot_status",
    "plot_sha256",
    "plotted_trace_sample_stem",
    "gaussian_smoothing_method",
    "gaussian_window_points",
    "gaussian_review_boundary_start_rt",
    "gaussian_review_boundary_end_rt",
    "gaussian_review_apex_rt",
    "gaussian_review_area",
    "gaussian_review_area_source",
    "gaussian_review_boundary_source",
    "gaussian_review_segment_class",
    "source_stratum",
    "current_machine_decision",
    "evidence_status",
    "missing_evidence_reason",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "label_template_path",
    "label_template_sha256",
    "source_packet_index_sha256",
    "source_artifact_hashes",
    "may_touch_matrix",
    "may_grant_product_authority",
]


def build_lockbox_static_review_bundle(
    *,
    packet_index_path: Path = PACKET_INDEX,
    label_template_path: Path = LABEL_TEMPLATE,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, object]:
    packet_rows = list(
        read_tsv_required(packet_index_path, required_columns=("lockbox_case_id",))
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    case_dir = output_dir / "cases"
    plot_dir = output_dir / "plots"
    case_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)
    _clear_generated_files(case_dir, "*.html")
    _clear_generated_files(plot_dir, "*.png")

    bundle_rows: list[dict[str, str]] = []
    for packet in sorted(packet_rows, key=lambda row: row["lockbox_case_id"]):
        row = _bundle_index_row(
            packet,
            packet_index_path=packet_index_path,
            label_template_path=label_template_path,
            output_dir=output_dir,
            case_dir=case_dir,
            plot_dir=plot_dir,
        )
        bundle_rows.append(row)
        _write_case_html(packet, row, case_dir=case_dir, output_dir=output_dir)

    index_path = output_dir / "bundle_index.tsv"
    write_tsv(
        index_path,
        bundle_rows,
        BUNDLE_INDEX_HEADER,
        extrasaction="raise",
        lineterminator="\n",
    )
    _write_index_html(bundle_rows, output_dir=output_dir)
    status_counts = Counter(row["plot_status"] for row in bundle_rows)
    return {
        "output_dir": output_dir,
        "index_html": output_dir / "index.html",
        "bundle_index": index_path,
        "case_count": len(bundle_rows),
        "plot_count": status_counts[PLOT_STATUS_PLOTTED],
        "plot_status_counts": dict(status_counts),
    }


def check_lockbox_static_review_bundle(
    *,
    packet_index_path: Path = PACKET_INDEX,
    label_template_path: Path = LABEL_TEMPLATE,
    output_dir: Path = OUTPUT_DIR,
    expected_case_count: int = 72,
) -> list[str]:
    problems: list[str] = []
    source_rows = list(
        read_tsv_required(
            packet_index_path,
            required_columns=("lockbox_case_id",),
        )
    )
    source_ids = [row["lockbox_case_id"] for row in source_rows]
    source_rows_by_id = {row["lockbox_case_id"]: row for row in source_rows}
    if len(source_rows_by_id) != len(source_ids):
        problems.append("packet index case IDs must be unique")
    packet_index_sha = _checked_file_sha256(packet_index_path, "packet index", problems)
    label_template_sha = _checked_file_sha256(
        label_template_path,
        "label template",
        problems,
    )
    header, rows = _read_bundle_index(output_dir / "bundle_index.tsv", problems)
    if list(header) != BUNDLE_INDEX_HEADER:
        problems.append("bundle index header must match static review schema")
    if len(rows) != expected_case_count:
        problems.append(f"bundle index must contain {expected_case_count} rows")
    case_ids = [row.get("lockbox_case_id", "") for row in rows]
    if set(case_ids) != set(source_ids):
        problems.append("bundle case IDs must match packet index")
    if len(set(case_ids)) != len(case_ids):
        problems.append("bundle case IDs must be unique")
    index_html = output_dir / "index.html"
    if not index_html.exists():
        problems.append("index.html missing")
    elif "Gaussian15" not in index_html.read_text(encoding="utf-8"):
        problems.append("index.html must mention Gaussian15")
    for row_number, row in enumerate(rows, start=2):
        source_row = source_rows_by_id.get(row.get("lockbox_case_id", ""))
        _check_source_binding(
            row,
            row_number,
            source_row,
            packet_index_path=packet_index_path,
            packet_index_sha=packet_index_sha,
            label_template_path=label_template_path,
            label_template_sha=label_template_sha,
            problems=problems,
        )
        _check_bundle_row(row, row_number, output_dir, problems)
    return problems


def _bundle_index_row(
    packet: Mapping[str, str],
    *,
    packet_index_path: Path,
    label_template_path: Path,
    output_dir: Path,
    case_dir: Path,
    plot_dir: Path,
) -> dict[str, str]:
    case_id = packet["lockbox_case_id"]
    plot_result = _write_review_plot(packet, plot_dir / f"{case_id}_gaussian15.png")
    case_html_path = case_dir / f"{case_id}.html"
    return {
        "schema_version": SCHEMA_VERSION,
        "lockbox_case_id": case_id,
        "case_html_path": _relative_to(case_html_path, ROOT),
        "review_plot_png_path": (
            _relative_to(plot_result.path, ROOT) if plot_result.path else ""
        ),
        "plot_status": plot_result.status,
        "plot_sha256": file_sha256(plot_result.path) if plot_result.path else "",
        "plotted_trace_sample_stem": plot_result.sample_stem,
        "gaussian_smoothing_method": MS1_MORPHOLOGY_TRACE_METHOD,
        "gaussian_window_points": str(DEFAULT_GAUSSIAN15_WINDOW_POINTS),
        "gaussian_review_boundary_start_rt": plot_result.boundary_start_rt,
        "gaussian_review_boundary_end_rt": plot_result.boundary_end_rt,
        "gaussian_review_apex_rt": plot_result.apex_rt,
        "gaussian_review_area": plot_result.area,
        "gaussian_review_area_source": plot_result.area_source,
        "gaussian_review_boundary_source": plot_result.boundary_source,
        "gaussian_review_segment_class": plot_result.segment_class,
        "source_stratum": packet.get("source_stratum", ""),
        "current_machine_decision": packet.get("current_machine_decision", ""),
        "evidence_status": packet.get("evidence_status", ""),
        "missing_evidence_reason": packet.get("missing_evidence_reason", ""),
        "row_id": packet.get("row_id", ""),
        "family_id": packet.get("family_id", ""),
        "sample_id": packet.get("sample_id", ""),
        "analyte": packet.get("analyte", ""),
        "label_template_path": _relative_to(label_template_path, ROOT),
        "label_template_sha256": file_sha256(label_template_path),
        "source_packet_index_sha256": file_sha256(packet_index_path),
        "source_artifact_hashes": packet.get("source_artifact_hashes", ""),
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
    }


class _PlotResult:
    def __init__(
        self,
        status: str,
        path: Path | None,
        sample_stem: str = "",
        segment: ChromPeakSegment | None = None,
    ) -> None:
        self.status = status
        self.path = path
        self.sample_stem = sample_stem
        self.boundary_start_rt = _format_optional_float(
            None if segment is None else segment.interval.rt_start_min,
        )
        self.boundary_end_rt = _format_optional_float(
            None if segment is None else segment.interval.rt_end_min,
        )
        self.apex_rt = _format_optional_float(
            None if segment is None else segment.apex_rt_min,
        )
        self.area = _format_optional_float(
            None if segment is None else segment.morphology_area_shadow,
        )
        self.area_source = MS1_MORPHOLOGY_AREA_SOURCE if segment is not None else ""
        self.boundary_source = (
            "" if segment is None else segment.boundary_stop_reason
        )
        self.segment_class = "" if segment is None else segment.segment_class


def _write_review_plot(packet: Mapping[str, str], png_path: Path) -> _PlotResult:
    if packet.get("evidence_status") == "missing_evidence_recorded":
        return _PlotResult("missing_evidence_recorded", None)
    trace_path = _resolve_path(packet.get("trace_data_path", ""))
    if not trace_path.exists():
        return _PlotResult("trace_file_missing", None)
    try:
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _PlotResult("trace_json_unreadable", None)
    trace = _select_sample_trace(payload, packet.get("sample_id", ""))
    if trace is None:
        return _PlotResult("sample_trace_missing", None)
    try:
        rt = np.asarray(trace["rt"], dtype=float)
        intensity = np.asarray(trace["intensity"], dtype=float)
    except (KeyError, TypeError, ValueError):
        return _PlotResult("invalid_trace_arrays", None)
    if rt.ndim != 1 or intensity.ndim != 1 or len(rt) != len(intensity) or len(rt) < 2:
        return _PlotResult("invalid_trace_arrays", None)
    if not (np.all(np.isfinite(rt)) and np.all(np.isfinite(intensity))):
        return _PlotResult("invalid_trace_arrays", None)
    try:
        baseline = _baseline_values(trace, intensity)
    except ValueError:
        return _PlotResult("invalid_trace_arrays", None)
    gaussian_segment = _select_gaussian_review_segment(
        packet,
        trace,
        rt,
        intensity,
        baseline,
    )
    if gaussian_segment is None:
        return _PlotResult(
            PLOT_STATUS_BOUNDARY_UNAVAILABLE,
            None,
            str(trace.get("sample_stem", "")),
        )
    _plot_gaussian_review(
        packet,
        trace,
        rt,
        intensity,
        baseline,
        gaussian_segment,
        png_path,
    )
    return _PlotResult(
        PLOT_STATUS_PLOTTED,
        png_path,
        str(trace.get("sample_stem", "")),
        gaussian_segment,
    )


def _plot_gaussian_review(
    packet: Mapping[str, str],
    trace: Mapping[str, Any],
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    gaussian_segment: ChromPeakSegment | None,
    png_path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    residual = np.maximum(intensity - baseline, 0.0)
    smoothed_residual = gaussian15_morphology_trace(
        residual,
        window_points=DEFAULT_GAUSSIAN15_WINDOW_POINTS,
    )
    smoothed = baseline + smoothed_residual
    peak = _parse_candidate_peak_summary(packet.get("candidate_peak_summary", ""))
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(10.8, 6.4),
        sharex=True,
        constrained_layout=True,
        height_ratios=(1.3, 0.9),
    )
    raw_ax, norm_ax = axes
    raw_ax.plot(
        rt,
        intensity,
        color="#64748b",
        alpha=0.35,
        linewidth=0.8,
        label="raw trace",
    )
    raw_ax.plot(
        rt,
        smoothed,
        color="#0f766e",
        linewidth=1.7,
        label="Gaussian15 smooth",
    )
    norm_ax.plot(
        rt,
        _normalize(smoothed_residual),
        color="#0f766e",
        linewidth=1.5,
        label="Gaussian15 normalized",
    )
    _draw_gaussian_boundary_marks(raw_ax, gaussian_segment)
    _draw_gaussian_boundary_marks(norm_ax, gaussian_segment)
    _draw_candidate_reference_marks(raw_ax, peak)
    _draw_candidate_reference_marks(norm_ax, peak)
    trace_apex = optional_float(trace.get("trace_apex_rt"))
    if trace_apex is not None:
        for ax in axes:
            ax.axvline(
                trace_apex,
                color="#7c3aed",
                linestyle=":",
                linewidth=1.05,
                label="trace apex",
            )
    for ax in axes:
        ax.grid(alpha=0.18)
    raw_ax.set_ylabel("Intensity")
    norm_ax.set_ylabel("Normalized")
    norm_ax.set_xlabel("Retention time (min)")
    raw_ax.set_title(
        (
            f"{packet.get('lockbox_case_id')}  {packet.get('family_id')} / "
            f"{packet.get('sample_id')}\n"
            f"{packet.get('source_stratum')} | {packet.get('current_machine_decision')}"
        ),
        loc="left",
        fontsize=10.0,
    )
    handles, labels = raw_ax.get_legend_handles_labels()
    deduped = dict(zip(labels, handles, strict=False))
    fig.legend(
        deduped.values(),
        deduped.keys(),
        loc="outside lower center",
        ncol=4,
        frameon=False,
        fontsize=8,
    )
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=135, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _select_gaussian_review_segment(
    packet: Mapping[str, str],
    trace: Mapping[str, Any],
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
) -> ChromPeakSegment | None:
    enumeration = enumerate_chrom_peak_segments(
        rt,
        intensity,
        baseline,
        policy=ChromPeakSegmentPolicy(
            morphology_trace_window_points=DEFAULT_GAUSSIAN15_WINDOW_POINTS,
        ),
    )
    if enumeration.status != "OK" or not enumeration.segments:
        return None
    peak = _parse_candidate_peak_summary(packet.get("candidate_peak_summary", ""))
    target_apex = peak.get("apex_rt_min")
    if target_apex is None:
        target_apex = optional_float(trace.get("trace_apex_rt"))
    if target_apex is not None:
        return select_segment_by_apex_rt(enumeration.segments, target_apex)
    return max(enumeration.segments, key=lambda segment: segment.morphology_area_shadow)


def _baseline_values(trace: Mapping[str, Any], intensity: np.ndarray) -> np.ndarray:
    baseline_payload = trace.get("baseline")
    if baseline_payload is None:
        baseline_payload = trace.get("baseline_values")
    if baseline_payload is None:
        return np.zeros_like(intensity, dtype=float)
    baseline = np.asarray(baseline_payload, dtype=float)
    if (
        baseline.ndim != 1
        or len(baseline) != len(intensity)
        or not np.all(np.isfinite(baseline))
    ):
        raise ValueError("invalid baseline")
    return baseline


def _draw_gaussian_boundary_marks(
    ax: Any,
    segment: ChromPeakSegment | None,
) -> None:
    if segment is None:
        return
    start = segment.interval.rt_start_min
    end = segment.interval.rt_end_min
    apex = segment.apex_rt_min
    if end > start:
        ax.axvspan(
            start,
            end,
            color="#14b8a6",
            alpha=0.14,
            label="Gaussian15 review boundary",
        )
    ax.axvline(
        apex,
        color="#0f766e",
        linestyle="--",
        linewidth=1.2,
        label="Gaussian15 segment apex",
    )


def _draw_candidate_reference_marks(ax: Any, peak: Mapping[str, float]) -> None:
    start = peak.get("start_rt_min")
    end = peak.get("end_rt_min")
    apex = peak.get("apex_rt_min")
    if start is not None and end is not None and end > start:
        for value in (start, end):
            ax.axvline(
                value,
                color="#b45309",
                linestyle=":",
                linewidth=0.9,
                label="candidate/raw boundary reference",
            )
    if apex is not None:
        ax.axvline(
            apex,
            color="#b45309",
            linestyle="--",
            linewidth=1.05,
            label="candidate apex",
        )


def _parse_candidate_peak_summary(summary: str) -> dict[str, float]:
    parsed: dict[str, float] = {}
    key_map = {
        "apex_rt_min": "apex_rt_min",
        "start_rt_min": "start_rt_min",
        "end_rt_min": "end_rt_min",
    }
    for part in summary.split(";"):
        if "=" not in part:
            continue
        key, raw_value = [item.strip() for item in part.split("=", 1)]
        mapped = key_map.get(key)
        if not mapped:
            continue
        value = optional_float(raw_value)
        if value is not None:
            parsed[mapped] = value
    return parsed


def _select_sample_trace(
    payload: Mapping[str, Any],
    sample_id: str,
) -> Mapping[str, Any] | None:
    traces = payload.get("traces")
    if not isinstance(traces, Sequence):
        return None
    for trace in traces:
        if isinstance(trace, Mapping) and trace.get("sample_stem") == sample_id:
            return trace
    return None


def _write_index_html(
    rows: Sequence[Mapping[str, str]],
    *,
    output_dir: Path,
) -> None:
    status_counts = Counter(row["plot_status"] for row in rows)
    lines = [
        "<!doctype html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Lockbox Review UX v1</title>",
        "<style>",
        _css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>Lockbox Review UX v1</h1>",
        '<p class="authority">只供人工標註。Gaussian15 是 review/morphology '
        "trace，不是 matrix area，也不是 ProductWriter authority。</p>",
        '<section class="summary" aria-label="summary">',
        _metric("Cases", str(len(rows))),
        _metric("Gaussian15 plots", str(status_counts[PLOT_STATUS_PLOTTED])),
        _metric("Missing evidence", str(status_counts["missing_evidence_recorded"])),
        _metric(
            "Boundary unavailable",
            str(status_counts[PLOT_STATUS_BOUNDARY_UNAVAILABLE]),
        ),
        _metric("Authority", "no matrix/write authority"),
        "</section>",
        '<table class="case-table">',
        "<thead><tr><th>Case</th><th>Stratum</th><th>Decision</th>"
        "<th>Evidence</th><th>Plot</th><th>Label</th></tr></thead>",
        "<tbody>",
    ]
    for row in rows:
        lines.append(_index_row_html(row, output_dir=output_dir))
    lines.extend(["</tbody>", "</table>", "</main>", "</body>", "</html>"])
    (output_dir / "index.html").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_case_html(
    packet: Mapping[str, str],
    bundle_row: Mapping[str, str],
    *,
    case_dir: Path,
    output_dir: Path,
) -> None:
    case_id = packet["lockbox_case_id"]
    plot_rel = _relative_link(bundle_row.get("review_plot_png_path", ""), case_dir)
    index_rel = _relative_link(output_dir / "index.html", case_dir)
    label_rel = _relative_link(LABEL_TEMPLATE, case_dir)
    packet_rel = _relative_link(_resolve_path(packet.get("packet_path", "")), case_dir)
    lines = [
        "<!doctype html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_e(case_id)}</title>",
        "<style>",
        _css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        f'<p><a href="{_a(index_rel)}">Back to index</a></p>',
        f"<h1>{_e(case_id)}</h1>",
        '<p class="authority">人工 review packet only。不要在這裡輸入 replacement '
        "value；不要把 label 當成 ProductWriter authority。</p>",
        '<section class="details-grid">',
        _fact("Family", packet.get("family_id", "")),
        _fact("Sample", packet.get("sample_id", "")),
        _fact("Stratum", packet.get("source_stratum", "")),
        _fact("Machine decision", packet.get("current_machine_decision", "")),
        _fact("Evidence", packet.get("evidence_status", "")),
        _fact("Plot status", bundle_row.get("plot_status", "")),
        _fact(
            "Gaussian review boundary",
            _gaussian_boundary_summary(bundle_row),
        ),
        _fact(
            "Gaussian review area source",
            bundle_row.get("gaussian_review_area_source", ""),
        ),
        "</section>",
        "<h2>Gaussian15 Review Plot</h2>",
    ]
    if plot_rel:
        lines.append(
            f'<img class="review-plot" src="{_a(plot_rel)}" '
            f'alt="{_a(case_id)} Gaussian15 review plot">'
        )
    else:
        lines.append(_missing_plot_message(bundle_row))
    lines.extend(
        [
            "<h2>Review Question</h2>",
            f"<p>{_e(packet.get('reviewer_question', ''))}</p>",
            "<h2>Label Cheat Sheet</h2>",
            "<ul>",
            "<li><strong>peak_choice_label</strong>: correct / wrong_peak / "
            "wrong_family / unresolved / insufficient_evidence</li>",
            "<li><strong>area_label</strong>: acceptable / unacceptable / "
            "not_assessable</li>",
            "<li><strong>boundary_label</strong>: acceptable / too_wide / "
            "too_narrow / shifted / not_assessable. Judge this against the "
            "Gaussian15 review boundary, not the candidate/raw boundary "
            "reference lines.</li>",
            "<li><strong>evidence_viewed</strong>: "
            f"{_e(_evidence_viewed_suggestion(packet))}</li>",
            "</ul>",
            "<h2>Links</h2>",
            "<ul>",
            f'<li><a href="{_a(label_rel)}">Label template TSV</a></li>',
            f'<li><a href="{_a(packet_rel)}">Markdown packet</a></li>',
            _artifact_link("Original overlay PNG", packet.get("overlay_png_path", "")),
            _artifact_link(
                "Original hypothesis PNG",
                packet.get("hypothesis_png_path", ""),
            ),
            _artifact_link("Trace JSON", packet.get("trace_data_path", "")),
            "</ul>",
            "<h2>Source Hashes</h2>",
            f"<pre>{_e(packet.get('source_artifact_hashes', ''))}</pre>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    (case_dir / f"{case_id}.html").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _index_row_html(row: Mapping[str, str], *, output_dir: Path) -> str:
    case_href = _relative_link(row["case_html_path"], output_dir)
    label_href = _relative_link(row["label_template_path"], output_dir)
    plot_value = _plot_status_label(row["plot_status"])
    return (
        "<tr>"
        f'<td><a href="{_a(case_href)}">{_e(row["lockbox_case_id"])}</a></td>'
        f"<td>{_badge(row['source_stratum'])}</td>"
        f"<td>{_e(row['current_machine_decision'])}</td>"
        f"<td>{_e(row['evidence_status'])}</td>"
        f"<td>{_e(plot_value)}</td>"
        f'<td><a href="{_a(label_href)}">template</a></td>'
        "</tr>"
    )


def _plot_status_label(status: str) -> str:
    if status == PLOT_STATUS_PLOTTED:
        return "Gaussian15 boundary"
    if status == PLOT_STATUS_BOUNDARY_UNAVAILABLE:
        return "boundary unavailable"
    return "missing"


def _missing_plot_message(row: Mapping[str, str]) -> str:
    if row.get("plot_status") == PLOT_STATUS_BOUNDARY_UNAVAILABLE:
        return (
            '<p class="missing">Trace exists but Gaussian15 review boundary is '
            "unavailable, usually because there is no positive signal in the "
            "trace. Mark boundary/area as not assessable unless independent "
            "evidence resolves it.</p>"
        )
    return (
        '<p class="missing">沒有可畫 trace；請依 packet 標成 insufficient '
        "evidence 或 not assessable，除非你另有獨立證據。</p>"
    )


def _metric(label: str, value: str) -> str:
    return (
        '<div class="metric">'
        f"<span>{_e(label)}</span>"
        f"<strong>{_e(value)}</strong>"
        "</div>"
    )


def _fact(label: str, value: object) -> str:
    return f"<div><dt>{_e(label)}</dt><dd>{_e(value)}</dd></div>"


def _artifact_link(label: str, path_value: str) -> str:
    if not path_value:
        return f"<li>{_e(label)}: not available</li>"
    path = _resolve_path(path_value)
    href = path.resolve().as_uri() if path.is_absolute() else str(path)
    return f'<li>{_e(label)}: <a href="{_a(href)}">{_e(path_value)}</a></li>'


def _gaussian_boundary_summary(row: Mapping[str, str]) -> str:
    start = row.get("gaussian_review_boundary_start_rt", "")
    end = row.get("gaussian_review_boundary_end_rt", "")
    apex = row.get("gaussian_review_apex_rt", "")
    source = row.get("gaussian_review_boundary_source", "")
    segment_class = row.get("gaussian_review_segment_class", "")
    if not start or not end:
        return "not available"
    return (
        f"start={start}; end={end}; apex={apex}; "
        f"source={source}; segment={segment_class}"
    )


def _badge(value: object) -> str:
    text = _e(value)
    return f'<span class="badge">{text}</span>'


def _evidence_viewed_suggestion(packet: Mapping[str, str]) -> str:
    status = packet.get("evidence_status", "")
    if status == "complete_visual_evidence":
        return "packet_trace_overlay_hypothesis"
    if status == "recovered_visual_evidence":
        return "packet_recovered_trace_overlay_hypothesis"
    return "packet_missing_evidence_record"


def _check_source_binding(
    row: Mapping[str, str],
    row_number: int,
    source_row: Mapping[str, str] | None,
    *,
    packet_index_path: Path,
    packet_index_sha: str,
    label_template_path: Path,
    label_template_sha: str,
    problems: list[str],
) -> None:
    if source_row is None:
        problems.append(f"bundle row {row_number}: no matching packet index row")
        return
    if row.get("source_packet_index_sha256") != packet_index_sha:
        problems.append(
            f"bundle row {row_number}: source_packet_index_sha256 mismatch",
        )
    if row.get("label_template_sha256") != label_template_sha:
        problems.append(f"bundle row {row_number}: label_template_sha256 mismatch")
    expected_label_template = _relative_to(label_template_path, ROOT)
    if row.get("label_template_path") != expected_label_template:
        problems.append(f"bundle row {row_number}: label_template_path mismatch")
    expected_bindings = {
        "source_artifact_hashes": source_row.get("source_artifact_hashes", ""),
        "row_id": source_row.get("row_id", ""),
        "family_id": source_row.get("family_id", ""),
        "sample_id": source_row.get("sample_id", ""),
        "analyte": source_row.get("analyte", ""),
        "source_stratum": source_row.get("source_stratum", ""),
        "current_machine_decision": source_row.get("current_machine_decision", ""),
        "evidence_status": source_row.get("evidence_status", ""),
        "missing_evidence_reason": source_row.get("missing_evidence_reason", ""),
    }
    for field, expected in expected_bindings.items():
        if row.get(field, "") != expected:
            problems.append(f"bundle row {row_number}: {field} mismatch")


def _check_bundle_row(
    row: Mapping[str, str],
    row_number: int,
    output_dir: Path,
    problems: list[str],
) -> None:
    if row.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"bundle row {row_number}: invalid schema_version")
    if row.get("may_touch_matrix") != NO_AUTHORITY:
        problems.append(f"bundle row {row_number}: may_touch_matrix must be FALSE")
    if row.get("may_grant_product_authority") != NO_AUTHORITY:
        problems.append(
            f"bundle row {row_number}: may_grant_product_authority must be FALSE",
        )
    if row.get("gaussian_smoothing_method") != MS1_MORPHOLOGY_TRACE_METHOD:
        problems.append(f"bundle row {row_number}: smoothing method must be Gaussian15")
    if row.get("gaussian_window_points") != str(DEFAULT_GAUSSIAN15_WINDOW_POINTS):
        problems.append(f"bundle row {row_number}: smoothing window must be 15")
    case_path = _resolve_path(row.get("case_html_path", ""))
    if not case_path.exists():
        problems.append(f"bundle row {row_number}: case HTML missing")
    else:
        text = case_path.read_text(encoding="utf-8")
        if row.get("lockbox_case_id", "") not in text:
            problems.append(f"bundle row {row_number}: case HTML missing case id")
        if "ProductWriter authority" not in text:
            problems.append(
                f"bundle row {row_number}: case HTML missing authority text",
            )
    plot_status = row.get("plot_status", "")
    plot_path_value = row.get("review_plot_png_path", "")
    if plot_status not in {
        PLOT_STATUS_PLOTTED,
        PLOT_STATUS_BOUNDARY_UNAVAILABLE,
        "missing_evidence_recorded",
    }:
        problems.append(f"bundle row {row_number}: unknown plot_status")
    if plot_status == PLOT_STATUS_PLOTTED:
        _check_gaussian_review_boundary(row, row_number, problems)
        plot_path = _resolve_path(plot_path_value)
        if not plot_path.exists():
            problems.append(f"bundle row {row_number}: plot PNG missing")
        else:
            if not plot_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                problems.append(f"bundle row {row_number}: plot is not a PNG")
            if file_sha256(plot_path) != row.get("plot_sha256", ""):
                problems.append(f"bundle row {row_number}: plot_sha256 mismatch")
    elif plot_path_value:
        problems.append(f"bundle row {row_number}: non-plotted row must not have plot")
    elif _has_gaussian_review_boundary(row):
        problems.append(
            f"bundle row {row_number}: non-plotted row must not have Gaussian boundary",
        )


def _check_gaussian_review_boundary(
    row: Mapping[str, str],
    row_number: int,
    problems: list[str],
) -> None:
    required_fields = (
        "gaussian_review_boundary_start_rt",
        "gaussian_review_boundary_end_rt",
        "gaussian_review_apex_rt",
        "gaussian_review_area",
        "gaussian_review_area_source",
        "gaussian_review_boundary_source",
        "gaussian_review_segment_class",
    )
    for field in required_fields:
        if not row.get(field, ""):
            problems.append(f"bundle row {row_number}: {field} missing")
    start = optional_float(row.get("gaussian_review_boundary_start_rt", ""))
    end = optional_float(row.get("gaussian_review_boundary_end_rt", ""))
    apex = optional_float(row.get("gaussian_review_apex_rt", ""))
    area = optional_float(row.get("gaussian_review_area", ""))
    if start is not None and end is not None and end <= start:
        problems.append(f"bundle row {row_number}: Gaussian boundary is empty")
    if (
        start is not None
        and end is not None
        and apex is not None
        and not (start <= apex <= end)
    ):
        problems.append(f"bundle row {row_number}: Gaussian apex outside boundary")
    if area is not None and area <= 0.0:
        problems.append(f"bundle row {row_number}: Gaussian review area not positive")
    if row.get("gaussian_review_area_source") != MS1_MORPHOLOGY_AREA_SOURCE:
        problems.append(
            f"bundle row {row_number}: Gaussian review area source mismatch",
        )


def _has_gaussian_review_boundary(row: Mapping[str, str]) -> bool:
    return any(
        row.get(field, "")
        for field in (
            "gaussian_review_boundary_start_rt",
            "gaussian_review_boundary_end_rt",
            "gaussian_review_apex_rt",
            "gaussian_review_area",
            "gaussian_review_area_source",
            "gaussian_review_boundary_source",
            "gaussian_review_segment_class",
        )
    )


def _checked_file_sha256(path: Path, label: str, problems: list[str]) -> str:
    try:
        return file_sha256(path)
    except OSError as exc:
        problems.append(f"could not hash {label} {path}: {exc}")
        return ""


def _read_bundle_index(
    path: Path,
    problems: list[str],
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    try:
        return read_tsv_with_header(path)
    except OSError as exc:
        problems.append(f"could not read {path}: {exc}")
    except ValueError as exc:
        problems.append(str(exc))
    return (), []


def _clear_generated_files(directory: Path, pattern: str) -> None:
    for path in directory.glob(pattern):
        if path.is_file():
            path.unlink()


def _normalize(values: np.ndarray) -> np.ndarray:
    if not len(values):
        return values
    maximum = float(np.nanmax(values))
    if maximum <= 0:
        return np.zeros_like(values)
    return values / maximum


def _format_optional_float(value: float | None) -> str:
    if value is None or not np.isfinite(float(value)):
        return ""
    return f"{float(value):.6g}"


def _relative_link(path_value: str | Path, base: Path) -> str:
    if not path_value:
        return ""
    path = _resolve_path(str(path_value))
    try:
        return Path(os.path.relpath(path.resolve(), start=base.resolve())).as_posix()
    except ValueError:
        return path.resolve().as_uri() if path.is_absolute() else str(path)


def _relative_to(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT / path


def _e(value: object) -> str:
    return html.escape(str(value), quote=False)


def _a(value: object) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
:root {
  color-scheme: light;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --line: #d8dee6;
  --text: #16202a;
  --muted: #607080;
  --teal: #0f766e;
  --amber: #b45309;
  --red: #9f2f2f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Segoe UI, Arial, sans-serif;
  line-height: 1.45;
}
main {
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px;
}
h1 { margin: 0 0 12px; font-size: 28px; }
h2 { margin: 24px 0 10px; font-size: 18px; }
a { color: #155e75; }
.authority {
  border-left: 5px solid var(--red);
  background: #fff7f7;
  padding: 10px 12px;
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin: 16px 0;
}
.metric,
.details-grid div {
  border: 1px solid var(--line);
  background: var(--surface);
  padding: 10px 12px;
}
.metric span,
dt {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.metric strong,
dd {
  margin: 3px 0 0;
  font-weight: 650;
}
.case-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--surface);
}
.case-table th,
.case-table td {
  border-bottom: 1px solid var(--line);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}
.case-table th { background: #edf2f7; }
.badge {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 2px 6px;
  background: #f8fafc;
}
.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 10px;
}
.review-plot {
  display: block;
  width: 100%;
  max-width: 1120px;
  border: 1px solid var(--line);
  background: white;
}
.missing {
  border: 1px solid var(--line);
  background: #fff8e8;
  padding: 14px;
}
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #111827;
  color: #e5e7eb;
  padding: 12px;
}
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-index", type=Path, default=PACKET_INDEX)
    parser.add_argument("--label-template", type=Path, default=LABEL_TEMPLATE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    if args.check_only:
        problems = check_lockbox_static_review_bundle(
            packet_index_path=args.packet_index,
            label_template_path=args.label_template,
            output_dir=args.output_dir,
        )
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        print("Lockbox static review bundle is valid and non-authoritative.")
        return 0
    result = build_lockbox_static_review_bundle(
        packet_index_path=args.packet_index,
        label_template_path=args.label_template,
        output_dir=args.output_dir,
    )
    print(
        "Built lockbox static review bundle: "
        f"{result['case_count']} cases, {result['plot_count']} Gaussian15 plots.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
