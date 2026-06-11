"""Render selected-envelope boundary review plots from diagnostic rows."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.config import Target, load_config
from xic_extractor.diagnostics.selected_envelope_gallery import (
    write_review_gallery_html as _write_review_gallery_html,
)
from xic_extractor.peak_detection.baseline import asls_baseline
from xic_extractor.peak_detection.chrom_peak_segments import (
    ChromPeakSegment,
    enumerate_chrom_peak_segments,
)
from xic_extractor.peak_detection.selected_envelope import gaussian15_morphology_trace
from xic_extractor.peak_detection.selected_envelope_diagnostics import (
    SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS,
)
from xic_extractor.peak_detection.selected_envelope_oracle import BoundaryOracle
from xic_extractor.peak_detection.selected_envelope_oracle_artifacts import (
    SELECTED_ENVELOPE_BOUNDARY_ORACLE_HEADERS,
    parse_selected_envelope_boundary_oracle_rows,
)
from xic_extractor.raw_reader import open_raw
from xic_extractor.tabular_io import write_tsv  # noqa: E402,I001

PLOT_INDEX_HEADERS = (
    "plot_rank",
    "plot_group",
    "sample_name",
    "target_label",
    "role",
    "selected_candidate_id",
    "row_boundary_decision",
    "boundary_change_class",
    "boundary_stop_reason",
    "area_delta_ratio",
    "resolver_rt_start",
    "resolver_rt_end",
    "envelope_rt_start",
    "envelope_rt_end",
    "quantitation_context_rt_start",
    "quantitation_context_rt_end",
    "chrom_peak_segment_status",
    "chrom_peak_segment_count",
    "selected_chrom_peak_segment_id",
    "selected_chrom_peak_segment_class",
    "selected_chrom_peak_segment_rt_start",
    "selected_chrom_peak_segment_rt_end",
    "selected_chrom_peak_segment_area_asls",
    "selected_chrom_peak_segment_stop_reason",
    "selected_chrom_peak_segment_projection",
    "oracle_row_id",
    "oracle_status",
    "oracle_source",
    "oracle_rt_start",
    "oracle_rt_end",
    "png_path",
    "pdf_path",
)

_TARGET_WINDOW_COLOR = "#f59e0b"
_CONTEXT_WINDOW_COLOR = "#64748b"
_RESOLVER_INTERVAL_COLOR = "#16a34a"
_RESOLVER_BOUNDARY_COLOR = "#15803d"
_SELECTED_ENVELOPE_COLOR = "#f97316"
_MANUAL_ORACLE_COLOR = "#7c3aed"
_CHROM_SEGMENT_COLOR = "#0ea5e9"
_SELECTED_CHROM_SEGMENT_COLOR = "#e11d48"
@dataclass(frozen=True)
class SelectedEnvelopePlotRequest:
    row: dict[str, str]
    plot_group: str


@dataclass(frozen=True)
class SelectedEnvelopePlotOutputs:
    index_tsv: Path
    plot_dir: Path
    gallery_html: Path


def run_selected_envelope_plot_review(
    *,
    selected_envelope_diagnostics_tsv: Path,
    chrom_peak_segment_review_rows_tsv: Path | None = None,
    boundary_oracle_tsv: Path | None = None,
    raw_dir: Path,
    dll_dir: Path,
    config_dir: Path,
    output_dir: Path,
    max_high_risk: int = 8,
    max_accepted_increase: int = 4,
    max_accepted_decrease: int = 2,
) -> SelectedEnvelopePlotOutputs:
    rows = _read_tsv(selected_envelope_diagnostics_tsv)
    chrom_peak_segment_review_rows = (
        _read_chrom_peak_segment_review_rows(chrom_peak_segment_review_rows_tsv)
        if chrom_peak_segment_review_rows_tsv is not None
        else None
    )
    boundary_oracles = _read_boundary_oracles(boundary_oracle_tsv)
    targets = _targets_by_label(config_dir, raw_dir=raw_dir, dll_dir=dll_dir)
    requests = select_selected_envelope_plot_requests(
        rows,
        chrom_peak_segment_review_rows=chrom_peak_segment_review_rows,
        max_high_risk=max_high_risk,
        max_accepted_increase=max_accepted_increase,
        max_accepted_decrease=max_accepted_decrease,
    )
    plot_dir = output_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    index_rows = _render_requests(
        requests,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        targets=targets,
        boundary_oracles=boundary_oracles,
        plot_dir=plot_dir,
    )
    index_tsv = output_dir / "selected_envelope_plot_index.tsv"
    _write_tsv(index_tsv, PLOT_INDEX_HEADERS, index_rows)
    gallery_html = output_dir / "review_gallery.html"
    _write_review_gallery_html(gallery_html, index_rows, index_tsv=index_tsv)
    return SelectedEnvelopePlotOutputs(
        index_tsv=index_tsv,
        plot_dir=plot_dir,
        gallery_html=gallery_html,
    )


def select_selected_envelope_plot_requests(
    rows: Iterable[Mapping[str, str]],
    *,
    chrom_peak_segment_review_rows: Iterable[Mapping[str, str]] | None = None,
    max_high_risk: int,
    max_accepted_increase: int,
    max_accepted_decrease: int,
) -> tuple[SelectedEnvelopePlotRequest, ...]:
    materialized = [dict(row) for row in rows]
    selected_ids: set[str] = set()
    requests: list[SelectedEnvelopePlotRequest] = []
    group_counts: dict[str, int] = {}

    def add(group: str, candidates: Sequence[dict[str, str]], limit: int) -> None:
        for row in candidates:
            if group_counts.get(group, 0) >= limit:
                return
            row_id = _row_identity(row)
            if row_id in selected_ids:
                continue
            selected_ids.add(row_id)
            requests.append(SelectedEnvelopePlotRequest(row=row, plot_group=group))
            group_counts[group] = group_counts.get(group, 0) + 1

    high_risk = [
        row
        for row in materialized
        if row.get("row_boundary_decision", "") != "accept_candidate"
    ]
    add(
        "high_risk_externalized",
        sorted(high_risk, key=_absolute_area_delta, reverse=True),
        max_high_risk,
    )

    accepted = [
        row
        for row in materialized
        if row.get("row_boundary_decision", "") == "accept_candidate"
    ]
    add(
        "accepted_area_increase",
        sorted(accepted, key=_area_delta, reverse=True),
        max_accepted_increase,
    )
    add(
        "accepted_area_decrease",
        sorted(
            (row for row in accepted if _area_delta(row) < 0.0),
            key=_area_delta,
        ),
        max_accepted_decrease,
    )
    if chrom_peak_segment_review_rows is not None:
        review_rows = _selected_diagnostic_rows_for_chrom_review(
            materialized,
            chrom_peak_segment_review_rows,
        )
        add(
            "chrom_peak_segment_review_only",
            review_rows,
            len(review_rows),
        )
    return tuple(requests)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-envelope-diagnostics-tsv", type=Path, required=True)
    parser.add_argument("--chrom-peak-segment-review-rows-tsv", type=Path)
    parser.add_argument("--boundary-oracle-tsv", type=Path)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-high-risk", type=_non_negative_int, default=8)
    parser.add_argument("--max-accepted-increase", type=_non_negative_int, default=4)
    parser.add_argument("--max-accepted-decrease", type=_non_negative_int, default=2)
    args = parser.parse_args(argv)

    try:
        outputs = run_selected_envelope_plot_review(
            selected_envelope_diagnostics_tsv=(
                args.selected_envelope_diagnostics_tsv
            ),
            chrom_peak_segment_review_rows_tsv=(
                args.chrom_peak_segment_review_rows_tsv
            ),
            boundary_oracle_tsv=args.boundary_oracle_tsv,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            config_dir=args.config_dir,
            output_dir=args.output_dir,
            max_high_risk=args.max_high_risk,
            max_accepted_increase=args.max_accepted_increase,
            max_accepted_decrease=args.max_accepted_decrease,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Plot index TSV: {outputs.index_tsv}")
    print(f"Plot directory: {outputs.plot_dir}")
    print(f"Review gallery HTML: {outputs.gallery_html}")
    return 0


def _render_requests(
    requests: Sequence[SelectedEnvelopePlotRequest],
    *,
    raw_dir: Path,
    dll_dir: Path,
    targets: Mapping[str, Target],
    boundary_oracles: Mapping[str, BoundaryOracle],
    plot_dir: Path,
) -> list[dict[str, str]]:
    index_rows: list[dict[str, str]] = []
    for rank, request in enumerate(requests, start=1):
        row = request.row
        target = _target_for_row(row, targets)
        raw_path = raw_dir / f"{_required_text(row, 'sample_name')}.raw"
        if not raw_path.is_file():
            raise ValueError(f"{raw_path}: RAW file does not exist")
        plot_row = {
            **row,
            "target_rt_start": _format_float(target.rt_min),
            "target_rt_end": _format_float(target.rt_max),
        }
        extraction_start, extraction_end = _plot_extraction_bounds(
            row,
            target,
        )
        with open_raw(raw_path, dll_dir) as raw:
            rt, intensity = raw.extract_xic(
                target.mz,
                extraction_start,
                extraction_end,
                target.ppm_tol,
            )
        baseline = asls_baseline(np.asarray(intensity, dtype=float))
        chrom_segments = enumerate_chrom_peak_segments(
            np.asarray(rt, dtype=float),
            np.asarray(intensity, dtype=float),
            baseline,
            quantitation_context_rt_start=extraction_start,
            quantitation_context_rt_end=extraction_end,
        )
        selected_chrom_segment = _select_chrom_peak_segment_for_row(
            plot_row,
            chrom_segments.segments,
        )
        boundary_oracle = boundary_oracles.get(
            _required_text(row, "selected_candidate_id")
        )
        stem = _plot_stem(rank, request)
        png_path = plot_dir / f"{stem}.png"
        pdf_path = plot_dir / f"{stem}.pdf"
        write_selected_envelope_boundary_plot(
            png_path=png_path,
            pdf_path=pdf_path,
            row=plot_row,
            boundary_oracle=boundary_oracle,
            rt=np.asarray(rt, dtype=float),
            intensity=np.asarray(intensity, dtype=float),
            baseline=baseline,
            plot_group=request.plot_group,
            chrom_peak_segments=chrom_segments.segments,
            selected_chrom_peak_segment=selected_chrom_segment,
        )
        index_rows.append(
            _plot_index_row(
                rank=rank,
                request=request,
                boundary_oracle=boundary_oracle,
                chrom_peak_segment_status=chrom_segments.status,
                chrom_peak_segments=chrom_segments.segments,
                selected_chrom_peak_segment=selected_chrom_segment,
                png_path=png_path,
                pdf_path=pdf_path,
            )
        )
    return index_rows


def write_selected_envelope_boundary_plot(
    *,
    png_path: Path,
    pdf_path: Path,
    row: Mapping[str, str],
    boundary_oracle: BoundaryOracle | None = None,
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    plot_group: str,
    chrom_peak_segments: Sequence[ChromPeakSegment] = (),
    selected_chrom_peak_segment: ChromPeakSegment | None = None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    residual = intensity - baseline
    gaussian15_residual = gaussian15_smoothed_residual(intensity, baseline)
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(11.0, 7.2),
        sharex=True,
        constrained_layout=True,
        height_ratios=(2.2, 1.0),
    )
    ax = axes[0]
    residual_ax = axes[1]
    ax.plot(rt, intensity, color="#111111", linewidth=1.35, label="raw XIC")
    ax.plot(rt, baseline, color="#2563eb", linewidth=1.2, label="AsLS baseline")
    ax.plot(
        rt,
        baseline + gaussian15_residual,
        color="#f97316",
        linewidth=1.1,
        linestyle="--",
        label="Gaussian15 morphology",
    )
    residual_ax.plot(rt, residual, color="#475569", linewidth=1.15, label="raw - AsLS")
    residual_ax.plot(
        rt,
        gaussian15_residual,
        color="#f97316",
        linewidth=1.05,
        linestyle="--",
        label="Gaussian15 residual",
    )
    residual_ax.axhline(0.0, color="#94a3b8", linewidth=0.8)
    _draw_windows(ax, row, boundary_oracle=boundary_oracle)
    _draw_windows(residual_ax, row, boundary_oracle=boundary_oracle)
    _draw_chrom_peak_segments(
        ax,
        chrom_peak_segments,
        selected_chrom_peak_segment=selected_chrom_peak_segment,
    )
    _draw_chrom_peak_segments(
        residual_ax,
        chrom_peak_segments,
        selected_chrom_peak_segment=selected_chrom_peak_segment,
    )
    title = (
        f"{row.get('sample_name', '')} / {row.get('target_label', '')} "
        f"({row.get('role', '')})"
    )
    subtitle = (
        f"{plot_group}; decision={row.get('row_boundary_decision', '')}; "
        f"class={row.get('boundary_change_class', '')}; "
        f"delta={row.get('area_delta_ratio', '')}"
    )
    ax.set_title(f"{title}\n{subtitle}", loc="left", fontsize=10.5)
    ax.set_ylabel("Intensity")
    residual_ax.set_ylabel("Residual")
    residual_ax.set_xlabel("Retention time (min)")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    residual_ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.grid(alpha=0.22)
    residual_ax.grid(alpha=0.22)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gaussian15_smoothed_residual(
    intensity: np.ndarray,
    baseline: np.ndarray,
) -> np.ndarray:
    residual = np.asarray(intensity, dtype=float) - np.asarray(baseline, dtype=float)
    if residual.ndim != 1:
        raise ValueError("intensity and baseline must be one-dimensional")
    return gaussian15_morphology_trace(residual)


def _draw_windows(
    ax: Any,
    row: Mapping[str, str],
    *,
    boundary_oracle: BoundaryOracle | None,
) -> None:
    target_start = _optional_float(row, "target_rt_start")
    target_end = _optional_float(row, "target_rt_end")
    resolver_start = _required_float(row, "resolver_rt_start")
    resolver_end = _required_float(row, "resolver_rt_end")
    envelope_start = _required_float(row, "envelope_rt_start")
    envelope_end = _required_float(row, "envelope_rt_end")
    context_start = _required_float(row, "quantitation_context_rt_start")
    context_end = _required_float(row, "quantitation_context_rt_end")
    if target_start is not None and target_end is not None:
        ax.axvspan(
            min(target_start, target_end),
            max(target_start, target_end),
            facecolor=_TARGET_WINDOW_COLOR,
            alpha=0.10,
            zorder=0,
            label="target RT window",
        )
    ax.axvspan(
        context_start,
        context_end,
        facecolor=_CONTEXT_WINDOW_COLOR,
        alpha=0.07,
        zorder=0,
        label="quantitation context",
    )
    ax.axvspan(
        resolver_start,
        resolver_end,
        facecolor=_RESOLVER_INTERVAL_COLOR,
        edgecolor=_RESOLVER_INTERVAL_COLOR,
        linewidth=2.2,
        alpha=0.24,
        zorder=10,
        label="ACTIVE selected/product interval",
    )
    ax.axvline(
        resolver_start,
        color=_RESOLVER_BOUNDARY_COLOR,
        linewidth=2.8,
        alpha=0.96,
        zorder=12,
    )
    ax.axvline(
        resolver_end,
        color=_RESOLVER_BOUNDARY_COLOR,
        linewidth=2.8,
        alpha=0.96,
        zorder=12,
    )
    ax.axvspan(
        envelope_start,
        envelope_end,
        facecolor=_SELECTED_ENVELOPE_COLOR,
        edgecolor=_SELECTED_ENVELOPE_COLOR,
        linewidth=1.0,
        alpha=0.14,
        zorder=2,
        label="selected envelope (legacy)",
    )
    if boundary_oracle is not None:
        ax.axvspan(
            boundary_oracle.rt_start_min,
            boundary_oracle.rt_end_min,
            facecolor=_MANUAL_ORACLE_COLOR,
            edgecolor=_MANUAL_ORACLE_COLOR,
            linewidth=1.3,
            alpha=0.24,
            zorder=7,
            label="manual/expert oracle",
        )


def _draw_chrom_peak_segments(
    ax: Any,
    segments: Sequence[ChromPeakSegment],
    *,
    selected_chrom_peak_segment: ChromPeakSegment | None,
) -> None:
    labeled_any = False
    labeled_selected = False
    selected_id = (
        selected_chrom_peak_segment.segment_id
        if selected_chrom_peak_segment is not None
        else ""
    )
    for segment in segments:
        is_selected = bool(selected_id and segment.segment_id == selected_id)
        color = (
            _SELECTED_CHROM_SEGMENT_COLOR
            if is_selected
            else _CHROM_SEGMENT_COLOR
        )
        alpha = 0.36 if is_selected else 0.07
        zorder = 8 if is_selected else 3
        label = None
        if is_selected and not labeled_selected:
            label = "selected chrom segment"
            labeled_selected = True
        elif not is_selected and not labeled_any:
            label = "chrom peak segment"
            labeled_any = True
        ax.axvspan(
            segment.interval.rt_start_min,
            segment.interval.rt_end_min,
            facecolor=color,
            edgecolor=color if is_selected else "none",
            linewidth=1.8 if is_selected else 0.0,
            alpha=alpha,
            label=label,
            zorder=zorder,
        )
        if is_selected:
            ax.axvline(
                segment.interval.rt_start_min,
                color=color,
                linewidth=1.4,
                alpha=0.95,
                zorder=zorder + 1,
            )
            ax.axvline(
                segment.interval.rt_end_min,
                color=color,
                linewidth=1.4,
                alpha=0.95,
                zorder=zorder + 1,
            )
        ax.axvline(
            segment.apex_rt_min,
            color=color,
            linewidth=1.2 if is_selected else 0.7,
            linestyle=":",
            alpha=0.95 if is_selected else 0.70,
            zorder=zorder + 1,
        )


def _plot_index_row(
    *,
    rank: int,
    request: SelectedEnvelopePlotRequest,
    boundary_oracle: BoundaryOracle | None,
    chrom_peak_segment_status: str = "",
    chrom_peak_segments: Sequence[ChromPeakSegment] = (),
    selected_chrom_peak_segment: ChromPeakSegment | None = None,
    png_path: Path,
    pdf_path: Path,
) -> dict[str, str]:
    row = request.row
    chrom_values = _chrom_peak_segment_index_values(
        row,
        chrom_peak_segment_status=chrom_peak_segment_status,
        chrom_peak_segments=chrom_peak_segments,
        selected_chrom_peak_segment=selected_chrom_peak_segment,
    )
    values = {
        "plot_rank": str(rank),
        "plot_group": request.plot_group,
        "sample_name": row.get("sample_name", ""),
        "target_label": row.get("target_label", ""),
        "role": row.get("role", ""),
        "selected_candidate_id": row.get("selected_candidate_id", ""),
        "row_boundary_decision": row.get("row_boundary_decision", ""),
        "boundary_change_class": row.get("boundary_change_class", ""),
        "boundary_stop_reason": row.get("boundary_stop_reason", ""),
        "area_delta_ratio": row.get("area_delta_ratio", ""),
        "resolver_rt_start": row.get("resolver_rt_start", ""),
        "resolver_rt_end": row.get("resolver_rt_end", ""),
        "envelope_rt_start": row.get("envelope_rt_start", ""),
        "envelope_rt_end": row.get("envelope_rt_end", ""),
        "quantitation_context_rt_start": row.get("quantitation_context_rt_start", ""),
        "quantitation_context_rt_end": row.get("quantitation_context_rt_end", ""),
        **chrom_values,
        "oracle_row_id": "",
        "oracle_status": "",
        "oracle_source": "",
        "oracle_rt_start": "",
        "oracle_rt_end": "",
        "png_path": str(png_path),
        "pdf_path": str(pdf_path),
    }
    if boundary_oracle is not None:
        values.update(
            {
                "oracle_row_id": boundary_oracle.oracle_row_id,
                "oracle_status": boundary_oracle.oracle_status,
                "oracle_source": boundary_oracle.oracle_source,
                "oracle_rt_start": _format_float(boundary_oracle.rt_start_min),
                "oracle_rt_end": _format_float(boundary_oracle.rt_end_min),
            }
        )
    return {header: values[header] for header in PLOT_INDEX_HEADERS}


def _chrom_peak_segment_index_values(
    row: Mapping[str, str],
    *,
    chrom_peak_segment_status: str,
    chrom_peak_segments: Sequence[ChromPeakSegment],
    selected_chrom_peak_segment: ChromPeakSegment | None,
) -> dict[str, str]:
    values = {
        "chrom_peak_segment_status": chrom_peak_segment_status,
        "chrom_peak_segment_count": str(len(chrom_peak_segments)),
        "selected_chrom_peak_segment_id": "",
        "selected_chrom_peak_segment_class": "",
        "selected_chrom_peak_segment_rt_start": "",
        "selected_chrom_peak_segment_rt_end": "",
        "selected_chrom_peak_segment_area_asls": "",
        "selected_chrom_peak_segment_stop_reason": "",
        "selected_chrom_peak_segment_projection": "",
    }
    if selected_chrom_peak_segment is None:
        return values
    segment = selected_chrom_peak_segment
    values.update(
        {
            "selected_chrom_peak_segment_id": segment.segment_id,
            "selected_chrom_peak_segment_class": segment.segment_class,
            "selected_chrom_peak_segment_rt_start": _format_float(
                segment.interval.rt_start_min
            ),
            "selected_chrom_peak_segment_rt_end": _format_float(
                segment.interval.rt_end_min
            ),
            "selected_chrom_peak_segment_area_asls": _format_float(
                segment.area_baseline_corrected
            ),
            "selected_chrom_peak_segment_stop_reason": segment.boundary_stop_reason,
            "selected_chrom_peak_segment_projection": (
                _chrom_peak_segment_projection_basis(row, segment)
            ),
        }
    )
    return values


def _select_chrom_peak_segment_for_row(
    row: Mapping[str, str],
    segments: Sequence[ChromPeakSegment],
) -> ChromPeakSegment | None:
    if not segments:
        return None
    resolver_midpoint = _optional_interval_midpoint(
        row,
        "resolver_rt_start",
        "resolver_rt_end",
    )
    if resolver_midpoint is not None:
        resolver_start = _required_float(row, "resolver_rt_start")
        resolver_end = _required_float(row, "resolver_rt_end")
        overlapping = _segments_overlapping_rt_interval(
            segments,
            min(resolver_start, resolver_end),
            max(resolver_start, resolver_end),
        )
        if overlapping:
            return max(
                overlapping,
                key=lambda segment: (
                    segment.morphology_area_shadow,
                    _interval_overlap(
                        min(resolver_start, resolver_end),
                        max(resolver_start, resolver_end),
                        segment.interval.rt_start_min,
                        segment.interval.rt_end_min,
                    ),
                ),
            )
        return _segment_for_reference_rt(segments, resolver_midpoint)
    selected_apex_rt = _selected_candidate_apex_rt(row)
    if selected_apex_rt is not None:
        return _segment_for_reference_rt(segments, selected_apex_rt)
    envelope_start = _required_float(row, "envelope_rt_start")
    envelope_end = _required_float(row, "envelope_rt_end")
    envelope_left = min(envelope_start, envelope_end)
    envelope_right = max(envelope_start, envelope_end)
    envelope_midpoint = (envelope_left + envelope_right) / 2.0
    envelope_overlaps = [
        (
            _interval_overlap(
                envelope_left,
                envelope_right,
                segment.interval.rt_start_min,
                segment.interval.rt_end_min,
            ),
            -abs(segment.apex_rt_min - envelope_midpoint),
            segment,
        )
        for segment in segments
    ]
    positive_overlaps = [entry for entry in envelope_overlaps if entry[0] > 0.0]
    if positive_overlaps:
        return max(positive_overlaps, key=lambda entry: (entry[0], entry[1]))[2]
    return min(
        segments,
        key=lambda segment: abs(segment.apex_rt_min - envelope_midpoint),
    )


def _segments_overlapping_rt_interval(
    segments: Sequence[ChromPeakSegment],
    start: float,
    end: float,
) -> tuple[ChromPeakSegment, ...]:
    return tuple(
        segment
        for segment in segments
        if _interval_overlap(
            start,
            end,
            segment.interval.rt_start_min,
            segment.interval.rt_end_min,
        )
        > 0.0
    )


def _chrom_peak_segment_projection_basis(
    row: Mapping[str, str],
    segment: ChromPeakSegment,
) -> str:
    selected_apex_rt = _selected_candidate_apex_rt(row)
    if selected_apex_rt is not None:
        if _segment_contains_rt(segment, selected_apex_rt):
            return "selected_apex_contains"
        return "nearest_selected_apex"
    resolver_midpoint = _optional_interval_midpoint(
        row,
        "resolver_rt_start",
        "resolver_rt_end",
    )
    if resolver_midpoint is not None:
        if _segment_contains_rt(segment, resolver_midpoint):
            return "resolver_midpoint_contains"
        return "nearest_resolver_midpoint"
    envelope_start = _required_float(row, "envelope_rt_start")
    envelope_end = _required_float(row, "envelope_rt_end")
    overlap = _interval_overlap(
        min(envelope_start, envelope_end),
        max(envelope_start, envelope_end),
        segment.interval.rt_start_min,
        segment.interval.rt_end_min,
    )
    return "envelope_overlap" if overlap > 0.0 else "nearest_envelope_midpoint"


def _selected_candidate_apex_rt(row: Mapping[str, str]) -> float | None:
    candidate_id = row.get("selected_candidate_id", "")
    fields = candidate_id.split("|")
    if len(fields) < 3:
        return None
    try:
        float(fields[-2])
        float(fields[-1])
        return float(fields[-3])
    except ValueError:
        return None


def _optional_interval_midpoint(
    row: Mapping[str, str],
    start_field: str,
    end_field: str,
) -> float | None:
    try:
        start = float(row.get(start_field, "") or "")
        end = float(row.get(end_field, "") or "")
    except ValueError:
        return None
    return (min(start, end) + max(start, end)) / 2.0


def _segment_for_reference_rt(
    segments: Sequence[ChromPeakSegment],
    reference_rt: float,
) -> ChromPeakSegment:
    containing = [
        segment for segment in segments if _segment_contains_rt(segment, reference_rt)
    ]
    candidates = containing or list(segments)
    return min(candidates, key=lambda segment: abs(segment.apex_rt_min - reference_rt))


def _segment_contains_rt(segment: ChromPeakSegment, reference_rt: float) -> bool:
    left = min(segment.interval.rt_start_min, segment.interval.rt_end_min)
    right = max(segment.interval.rt_start_min, segment.interval.rt_end_min)
    return left <= reference_rt <= right


def _interval_overlap(
    left_start: float,
    left_end: float,
    right_start: float,
    right_end: float,
) -> float:
    return max(0.0, min(left_end, right_end) - max(left_start, right_start))


def _read_boundary_oracles(
    path: Path | None,
) -> dict[str, BoundaryOracle]:
    if path is None:
        return {}
    rows = _read_tsv_with_required_columns(
        path,
        required_columns=set(SELECTED_ENVELOPE_BOUNDARY_ORACLE_HEADERS),
    )
    parsed = parse_selected_envelope_boundary_oracle_rows(rows)
    return selected_boundary_oracles_by_candidate_id(parsed)


def selected_boundary_oracles_by_candidate_id(
    oracles: Iterable[BoundaryOracle],
) -> dict[str, BoundaryOracle]:
    by_candidate: dict[str, BoundaryOracle] = {}
    for oracle in oracles:
        if oracle.oracle_status != "expert_reviewed":
            raise ValueError("plot boundary oracle rows must be expert_reviewed")
        if oracle.oracle_source not in {
            "manual_overlay",
            "expert_overlay",
            "manual_2raw",
        }:
            raise ValueError(
                "plot boundary oracle source must be manual/expert reviewed"
            )
        if oracle.selected_candidate_id in by_candidate:
            raise ValueError(
                "boundary oracle rows must be unique by selected_candidate_id"
            )
        by_candidate[oracle.selected_candidate_id] = oracle
    return by_candidate


def _targets_by_label(
    config_dir: Path,
    *,
    raw_dir: Path,
    dll_dir: Path,
) -> dict[str, Target]:
    _config, targets = load_config(
        config_dir,
        settings_overrides={
            "data_dir": str(raw_dir),
            "dll_dir": str(dll_dir),
        },
    )
    return {target.label: target for target in targets}


def _target_for_row(row: Mapping[str, str], targets: Mapping[str, Target]) -> Target:
    label = _required_text(row, "target_label")
    target = targets.get(label)
    if target is None:
        raise ValueError(f"{label}: target_label is not present in config targets")
    return target


def _plot_extraction_bounds(
    row: Mapping[str, str],
    target: Target,
) -> tuple[float, float]:
    context_start = _required_float(row, "quantitation_context_rt_start")
    context_end = _required_float(row, "quantitation_context_rt_end")
    left = min(context_start, context_end, target.rt_min, target.rt_max)
    right = max(context_start, context_end, target.rt_min, target.rt_max)
    return left, right


def _read_tsv(path: Path) -> list[dict[str, str]]:
    return _read_tsv_with_required_columns(
        path,
        required_columns=set(SELECTED_ENVELOPE_DIAGNOSTIC_HEADERS),
    )


def _read_chrom_peak_segment_review_rows(path: Path) -> list[dict[str, str]]:
    return _read_tsv_with_required_columns(
        path,
        required_columns={"sample_name", "target_label", "role"},
    )


def _read_tsv_with_required_columns(
    path: Path,
    *,
    required_columns: set[str],
) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or ())
        missing = sorted(required_columns - columns)
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return list(reader)


def _write_tsv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(path, tuple(rows), fieldnames, extrasaction="raise")


def _selected_diagnostic_rows_for_chrom_review(
    diagnostic_rows: Sequence[dict[str, str]],
    review_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in diagnostic_rows:
        key = _chrom_review_key(row)
        if key in by_key:
            raise ValueError(
                "chrom review diagnostic key is ambiguous: "
                f"{' / '.join(key)}"
            )
        by_key[key] = row

    selected: list[dict[str, str]] = []
    for review_row in review_rows:
        key = _chrom_review_key(review_row)
        diagnostic_row = by_key.get(key)
        if diagnostic_row is None:
            raise ValueError(
                "chrom review row not found in selected-envelope diagnostics: "
                f"{' / '.join(key)}"
            )
        selected.append(diagnostic_row)
    return selected


def _chrom_review_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        row.get("sample_name", ""),
        row.get("target_label", ""),
        row.get("role", ""),
    )


def _plot_stem(rank: int, request: SelectedEnvelopePlotRequest) -> str:
    row = request.row
    return "_".join(
        (
            f"{rank:02d}",
            _safe_slug(request.plot_group),
            _safe_slug(row.get("sample_name", "")),
            _safe_slug(row.get("target_label", "")),
        )
    )


def _row_identity(row: Mapping[str, str]) -> str:
    return "|".join(
        (
            row.get("sample_name", ""),
            row.get("target_label", ""),
            row.get("selected_candidate_id", ""),
        )
    )


def _absolute_area_delta(row: Mapping[str, str]) -> float:
    return abs(_area_delta(row))


def _area_delta(row: Mapping[str, str]) -> float:
    try:
        return float(row.get("area_delta_ratio", "") or "0")
    except ValueError:
        return 0.0


def _required_text(row: Mapping[str, str], field: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ValueError(f"{field} is required")
    return value


def _required_float(row: Mapping[str, str], field: str) -> float:
    value = _required_text(row, field)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric") from exc


def _optional_float(row: Mapping[str, str], field: str) -> float | None:
    value = row.get(field, "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _format_float(value: float) -> str:
    return f"{value:.5f}"


def _safe_slug(value: str) -> str:
    cleaned = []
    for character in value:
        if character.isalnum():
            cleaned.append(character)
        else:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    return slug[:80] or "row"


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
