"""Render target-pair RT candidate review plots from RAW XIC traces."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.config import Target, load_config
from xic_extractor.peak_detection.baseline import asls_baseline
from xic_extractor.peak_detection.selected_envelope import (
    gaussian15_morphology_trace,
)
from xic_extractor.raw_reader import open_raw
from xic_extractor.tabular_io import write_tsv
from xic_extractor.xic_models import XICRequest

PLOT_INDEX_HEADERS = (
    "plot_rank",
    "plot_group",
    "sample_name",
    "target_label",
    "paired_istd_label",
    "previous_candidate_rt",
    "previous_candidate_rt_start",
    "previous_candidate_rt_end",
    "selected_candidate_rt",
    "selected_candidate_rt_start",
    "selected_candidate_rt_end",
    "paired_istd_rt",
    "paired_istd_product_rt",
    "paired_istd_product_rt_start",
    "paired_istd_product_rt_end",
    "paired_istd_product_state",
    "paired_istd_counted_detection",
    "expected_analyte_rt",
    "pair_rt_delta_expected",
    "pair_rt_delta_observed",
    "pair_rt_delta_error",
    "paired_area_ratio_observed",
    "paired_area_ratio_reference_median",
    "paired_area_ratio_status",
    "missing_ms2_explanation",
    "false_positive_review_status",
    "false_positive_review_reasons",
    "selection_status",
    "product_switch_allowed",
    "gate_decision",
    "png_path",
    "pdf_path",
)


@dataclass(frozen=True)
class CandidateInterval:
    apex_rt: float
    rt_start: float
    rt_end: float


@dataclass(frozen=True)
class IstdProductInterval:
    apex_rt: float
    rt_start: float
    rt_end: float
    product_state: str
    counted_detection: str


@dataclass(frozen=True)
class TargetPairPlotRequest:
    row: dict[str, str]
    plot_group: str


@dataclass(frozen=True)
class TargetPairPlotOutputs:
    index_tsv: Path
    plot_dir: Path


def run_target_pair_rt_candidate_plot_review(
    *,
    target_pair_tsv: Path,
    raw_dir: Path,
    dll_dir: Path,
    config_dir: Path,
    output_dir: Path,
    long_csv: Path | None = None,
    max_8oxodg_contradicted: int = 8,
    per_target: int = 2,
    max_outside_area_ratio: int = 4,
    max_total: int = 24,
    plot_all_candidates: bool = False,
    plot_input_rows: bool = False,
    include_sample_inapplicable: bool = False,
) -> TargetPairPlotOutputs:
    rows = _read_tsv(target_pair_tsv)
    istd_intervals = _read_istd_product_intervals(long_csv)
    targets = _targets_by_label(config_dir, raw_dir=raw_dir, dll_dir=dll_dir)
    requests = select_target_pair_plot_requests(
        rows,
        max_8oxodg_contradicted=max_8oxodg_contradicted,
        per_target=per_target,
        max_outside_area_ratio=max_outside_area_ratio,
        max_total=max_total,
        plot_all_candidates=plot_all_candidates,
        plot_input_rows=plot_input_rows,
        include_sample_inapplicable=include_sample_inapplicable,
    )
    plot_dir = output_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    index_rows = _render_requests(
        requests,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        targets=targets,
        plot_dir=plot_dir,
        istd_intervals=istd_intervals,
    )
    index_tsv = output_dir / "target_pair_rt_candidate_plot_index.tsv"
    _write_tsv(index_tsv, PLOT_INDEX_HEADERS, index_rows)
    return TargetPairPlotOutputs(index_tsv=index_tsv, plot_dir=plot_dir)


def select_target_pair_plot_requests(
    rows: Iterable[Mapping[str, str]],
    *,
    max_8oxodg_contradicted: int,
    per_target: int,
    max_outside_area_ratio: int,
    max_total: int,
    plot_all_candidates: bool = False,
    plot_input_rows: bool = False,
    include_sample_inapplicable: bool = False,
) -> tuple[TargetPairPlotRequest, ...]:
    materialized = [
        dict(row)
        for row in rows
        if include_sample_inapplicable or not _is_sample_inapplicable_blocked(row)
    ]
    if plot_input_rows:
        return tuple(
            TargetPairPlotRequest(row=row, plot_group=_plot_group_for_row(row))
            for row in materialized
            if row.get("previous_candidate_id", "")
            and row.get("selected_candidate_id", "")
        )
    candidate_rows = [
        row
        for row in materialized
        if row.get("false_positive_review_status", "")
        in {"row_approval_candidate", "false_positive_review_required"}
    ]
    accepted_rows = [
        row
        for row in materialized
        if row.get("false_positive_review_status", "") == "product_switch_accepted"
        or row.get("selection_status", "") == "auto_reselected"
        or row.get("product_switch_allowed", "").upper() == "TRUE"
    ]
    if plot_all_candidates:
        return tuple(
            TargetPairPlotRequest(row=row, plot_group=_plot_group_for_row(row))
            for row in [*accepted_rows, *candidate_rows]
        )

    selected_ids: set[str] = set()
    requests: list[TargetPairPlotRequest] = []

    def add(group: str, candidates: Sequence[dict[str, str]], limit: int) -> None:
        nonlocal requests
        if len(requests) >= max_total:
            return
        count = 0
        for row in candidates:
            if count >= limit or len(requests) >= max_total:
                return
            row_id = _row_identity(row)
            if row_id in selected_ids:
                continue
            selected_ids.add(row_id)
            requests.append(TargetPairPlotRequest(row=row, plot_group=group))
            count += 1

    add("product_switch_accepted_reference", accepted_rows, len(accepted_rows))

    oxodg_contradicted = [
        row
        for row in candidate_rows
        if row.get("target_label", "") == "8-oxodG"
        and row.get("missing_ms2_explanation", "") == "contradicted"
    ]
    add(
        "8_oxodg_ms2_nl_contradicted_high_delta",
        sorted(oxodg_contradicted, key=_abs_pair_rt_delta_error, reverse=True),
        max_8oxodg_contradicted,
    )

    outside_area_ratio = [
        row
        for row in candidate_rows
        if row.get("paired_area_ratio_status", "") == "outside_robust_range"
    ]
    add(
        "paired_area_ratio_outside_active",
        sorted(outside_area_ratio, key=_abs_pair_rt_delta_error, reverse=True),
        max_outside_area_ratio,
    )

    rows_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        target_label = row.get("target_label", "")
        if not target_label:
            continue
        rows_by_target[target_label].append(row)
    for target_label in sorted(rows_by_target):
        add(
            f"per_target_high_delta_{_safe_stem(target_label)}",
            sorted(
                rows_by_target[target_label],
                key=_abs_pair_rt_delta_error,
                reverse=True,
            ),
            per_target,
        )
    return tuple(requests)


def parse_candidate_interval(candidate_id: str) -> CandidateInterval:
    fields = candidate_id.split("|")
    if len(fields) < 7:
        raise ValueError(f"candidate id has too few fields: {candidate_id}")
    try:
        apex_rt = float(fields[-3])
        rt_start = float(fields[-2])
        rt_end = float(fields[-1])
    except ValueError as exc:
        raise ValueError(
            f"candidate id does not end with numeric RT bounds: {candidate_id}"
        ) from exc
    return CandidateInterval(
        apex_rt=apex_rt,
        rt_start=min(rt_start, rt_end),
        rt_end=max(rt_start, rt_end),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-pair-tsv", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--long-csv", type=Path)
    parser.add_argument("--max-8oxodg-contradicted", type=_non_negative_int, default=8)
    parser.add_argument("--per-target", type=_non_negative_int, default=2)
    parser.add_argument("--max-outside-area-ratio", type=_non_negative_int, default=4)
    parser.add_argument("--max-total", type=_positive_int, default=24)
    parser.add_argument("--plot-all-candidates", action="store_true")
    parser.add_argument("--plot-input-rows", action="store_true")
    parser.add_argument(
        "--include-sample-inapplicable",
        action="store_true",
        help=(
            "Include rows already blocked by target sample applicability. "
            "Use only for explicit false-positive audits, not product review."
        ),
    )
    args = parser.parse_args(argv)

    try:
        outputs = run_target_pair_rt_candidate_plot_review(
            target_pair_tsv=args.target_pair_tsv,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            config_dir=args.config_dir,
            output_dir=args.output_dir,
            long_csv=args.long_csv,
            max_8oxodg_contradicted=args.max_8oxodg_contradicted,
            per_target=args.per_target,
            max_outside_area_ratio=args.max_outside_area_ratio,
            max_total=args.max_total,
            plot_all_candidates=args.plot_all_candidates,
            plot_input_rows=args.plot_input_rows,
            include_sample_inapplicable=args.include_sample_inapplicable,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Plot index TSV: {outputs.index_tsv}")
    print(f"Plot directory: {outputs.plot_dir}")
    return 0


def _render_requests(
    requests: Sequence[TargetPairPlotRequest],
    *,
    raw_dir: Path,
    dll_dir: Path,
    targets: Mapping[str, Target],
    plot_dir: Path,
    istd_intervals: Mapping[tuple[str, str], IstdProductInterval],
) -> list[dict[str, str]]:
    index_rows: list[dict[str, str]] = []
    for rank, request in enumerate(requests, start=1):
        row = request.row
        target = _target_for_row(row, targets)
        istd_target = _paired_istd_target(target, targets)
        previous_interval = parse_candidate_interval(
            _required_text(row, "previous_candidate_id")
        )
        selected_interval = parse_candidate_interval(
            _required_text(row, "selected_candidate_id")
        )
        paired_istd_rt = _optional_float(row.get("paired_istd_rt", ""))
        istd_product_interval = istd_intervals.get(
            (_required_text(row, "sample_name"), istd_target.label)
        )
        expected_analyte_rt = _expected_analyte_rt(row)
        rt_min, rt_max = _plot_rt_window(
            target,
            istd_target,
            previous_interval=previous_interval,
            selected_interval=selected_interval,
            paired_istd_rt=paired_istd_rt,
            istd_product_interval=istd_product_interval,
            expected_analyte_rt=expected_analyte_rt,
        )
        raw_path = raw_dir / f"{_required_text(row, 'sample_name')}.raw"
        if not raw_path.is_file():
            raise ValueError(f"{raw_path}: RAW file does not exist")
        with open_raw(raw_path, dll_dir) as raw:
            target_trace, istd_trace = raw.extract_xic_many(
                (
                    XICRequest(
                        mz=target.mz,
                        rt_min=rt_min,
                        rt_max=rt_max,
                        ppm_tol=target.ppm_tol,
                    ),
                    XICRequest(
                        mz=istd_target.mz,
                        rt_min=rt_min,
                        rt_max=rt_max,
                        ppm_tol=istd_target.ppm_tol,
                    ),
                )
            )
        stem = _plot_stem(rank, request)
        png_path = plot_dir / f"{stem}.png"
        pdf_path = plot_dir / f"{stem}.pdf"
        write_target_pair_rt_candidate_plot(
            png_path=png_path,
            pdf_path=pdf_path,
            row=row,
            target=target,
            istd_target=istd_target,
            target_rt=np.asarray(target_trace.rt, dtype=float),
            target_intensity=np.asarray(target_trace.intensity, dtype=float),
            istd_rt=np.asarray(istd_trace.rt, dtype=float),
            istd_intensity=np.asarray(istd_trace.intensity, dtype=float),
            previous_interval=previous_interval,
            selected_interval=selected_interval,
            paired_istd_rt=paired_istd_rt,
            istd_product_interval=istd_product_interval,
            expected_analyte_rt=expected_analyte_rt,
            plot_group=request.plot_group,
        )
        index_rows.append(
            _plot_index_row(
                rank=rank,
                request=request,
                target=target,
                istd_target=istd_target,
                previous_interval=previous_interval,
                selected_interval=selected_interval,
                paired_istd_rt=paired_istd_rt,
                istd_product_interval=istd_product_interval,
                expected_analyte_rt=expected_analyte_rt,
                png_path=png_path,
                pdf_path=pdf_path,
            )
        )
    return index_rows


def write_target_pair_rt_candidate_plot(
    *,
    png_path: Path,
    pdf_path: Path,
    row: Mapping[str, str],
    target: Target,
    istd_target: Target,
    target_rt: np.ndarray,
    target_intensity: np.ndarray,
    istd_rt: np.ndarray,
    istd_intensity: np.ndarray,
    previous_interval: CandidateInterval,
    selected_interval: CandidateInterval,
    paired_istd_rt: float | None,
    istd_product_interval: IstdProductInterval | None,
    expected_analyte_rt: float | None,
    plot_group: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    target_baseline = _safe_asls(target_intensity)
    istd_baseline = _safe_asls(istd_intensity)
    target_smooth = _baseline_plus_gaussian15(target_intensity, target_baseline)
    istd_smooth = _baseline_plus_gaussian15(istd_intensity, istd_baseline)
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(11.5, 7.4),
        sharex=True,
        constrained_layout=True,
        height_ratios=(1.45, 1.0),
    )
    target_ax, istd_ax = axes
    _plot_trace_panel(
        target_ax,
        rt=target_rt,
        intensity=target_intensity,
        baseline=target_baseline,
        smooth=target_smooth,
        panel_label=f"Analyte {target.label}  m/z {target.mz:.4f}",
    )
    _plot_trace_panel(
        istd_ax,
        rt=istd_rt,
        intensity=istd_intensity,
        baseline=istd_baseline,
        smooth=istd_smooth,
        panel_label=f"Paired ISTD {istd_target.label}  m/z {istd_target.mz:.4f}",
    )
    _draw_analyte_candidate_marks(
        target_ax,
        previous_interval=previous_interval,
        selected_interval=selected_interval,
        paired_istd_rt=paired_istd_rt,
        expected_analyte_rt=expected_analyte_rt,
    )
    _draw_istd_anchor_marks(
        istd_ax,
        paired_istd_rt=paired_istd_rt,
        istd_product_interval=istd_product_interval,
    )
    for ax in axes:
        ax.grid(alpha=0.20)
        ax.set_ylabel("Intensity")

    title = f"{row.get('sample_name', '')} / {target.label}"
    missing_ms2 = row.get("missing_ms2_explanation", "") or "blank"
    subtitle = (
        f"{plot_group}; missing_MS2={missing_ms2}; "
        f"area_ratio={row.get('paired_area_ratio_observed', '')} "
        f"({row.get('paired_area_ratio_status', '')}); "
        f"delta_error={row.get('pair_rt_delta_error', '')}"
    )
    target_ax.set_title(f"{title}\n{subtitle}", loc="left", fontsize=10.5)
    istd_ax.set_xlabel("Retention time (min)")
    handles, labels = _dedup_legend_handles(axes)
    fig.legend(
        handles,
        labels,
        loc="outside lower center",
        ncol=4,
        frameon=False,
        fontsize=8,
    )
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_trace_panel(
    ax: Any,
    *,
    rt: np.ndarray,
    intensity: np.ndarray,
    baseline: np.ndarray,
    smooth: np.ndarray,
    panel_label: str,
) -> None:
    ax.plot(rt, intensity, color="#111827", linewidth=1.2, label="raw XIC")
    ax.plot(rt, baseline, color="#2563eb", linewidth=1.0, label="AsLS baseline")
    ax.plot(
        rt,
        smooth,
        color="#f97316",
        linewidth=1.05,
        linestyle="--",
        label="Gaussian15 morphology",
    )
    ax.text(
        0.01,
        0.92,
        panel_label,
        transform=ax.transAxes,
        fontsize=9,
        color="#334155",
        ha="left",
        va="top",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72},
    )


def _draw_analyte_candidate_marks(
    ax: Any,
    *,
    previous_interval: CandidateInterval,
    selected_interval: CandidateInterval,
    paired_istd_rt: float | None,
    expected_analyte_rt: float | None,
) -> None:
    ax.axvspan(
        previous_interval.rt_start,
        previous_interval.rt_end,
        color="#ef4444",
        alpha=0.16,
        label="previous interval",
    )
    ax.axvspan(
        selected_interval.rt_start,
        selected_interval.rt_end,
        color="#14b8a6",
        alpha=0.20,
        label="selected/proposed interval",
    )
    ax.axvline(
        previous_interval.apex_rt,
        color="#b91c1c",
        linewidth=0.95,
        linestyle="--",
        label="previous apex",
    )
    ax.axvline(
        selected_interval.apex_rt,
        color="#0f766e",
        linewidth=1.1,
        linestyle="-.",
        label="selected/proposed apex",
    )
    if paired_istd_rt is not None:
        ax.axvline(
            paired_istd_rt,
            color="#0284c7",
            linewidth=1.0,
            linestyle=":",
            label="paired ISTD RT",
        )
    if expected_analyte_rt is not None:
        ax.axvline(
            expected_analyte_rt,
            color="#7c3aed",
            linewidth=1.0,
            linestyle=(0, (3, 2, 1, 2)),
            label="expected analyte RT",
        )


def _draw_istd_anchor_marks(
    ax: Any,
    *,
    paired_istd_rt: float | None,
    istd_product_interval: IstdProductInterval | None,
) -> None:
    if istd_product_interval is not None:
        ax.axvspan(
            istd_product_interval.rt_start,
            istd_product_interval.rt_end,
            color="#38bdf8",
            alpha=0.20,
            label="ISTD product interval",
        )
        ax.axvline(
            istd_product_interval.apex_rt,
            color="#0369a1",
            linewidth=1.1,
            linestyle="-.",
            label="ISTD product apex",
        )
    if paired_istd_rt is None:
        return
    ax.axvline(
        paired_istd_rt,
        color="#0284c7",
        linewidth=1.2,
        linestyle=":",
        label="paired ISTD RT",
    )


def _plot_index_row(
    *,
    rank: int,
    request: TargetPairPlotRequest,
    target: Target,
    istd_target: Target,
    previous_interval: CandidateInterval,
    selected_interval: CandidateInterval,
    paired_istd_rt: float | None,
    istd_product_interval: IstdProductInterval | None,
    expected_analyte_rt: float | None,
    png_path: Path,
    pdf_path: Path,
) -> dict[str, str]:
    row = request.row
    return {
        "plot_rank": str(rank),
        "plot_group": request.plot_group,
        "sample_name": row.get("sample_name", ""),
        "target_label": target.label,
        "paired_istd_label": istd_target.label,
        "previous_candidate_rt": _fmt(previous_interval.apex_rt),
        "previous_candidate_rt_start": _fmt(previous_interval.rt_start),
        "previous_candidate_rt_end": _fmt(previous_interval.rt_end),
        "selected_candidate_rt": _fmt(selected_interval.apex_rt),
        "selected_candidate_rt_start": _fmt(selected_interval.rt_start),
        "selected_candidate_rt_end": _fmt(selected_interval.rt_end),
        "paired_istd_rt": _fmt(paired_istd_rt),
        "paired_istd_product_rt": _fmt(
            None if istd_product_interval is None else istd_product_interval.apex_rt
        ),
        "paired_istd_product_rt_start": _fmt(
            None if istd_product_interval is None else istd_product_interval.rt_start
        ),
        "paired_istd_product_rt_end": _fmt(
            None if istd_product_interval is None else istd_product_interval.rt_end
        ),
        "paired_istd_product_state": (
            "" if istd_product_interval is None else istd_product_interval.product_state
        ),
        "paired_istd_counted_detection": (
            ""
            if istd_product_interval is None
            else istd_product_interval.counted_detection
        ),
        "expected_analyte_rt": _fmt(expected_analyte_rt),
        "pair_rt_delta_expected": row.get("pair_rt_delta_expected", ""),
        "pair_rt_delta_observed": row.get("pair_rt_delta_observed", ""),
        "pair_rt_delta_error": row.get("pair_rt_delta_error", ""),
        "paired_area_ratio_observed": row.get("paired_area_ratio_observed", ""),
        "paired_area_ratio_reference_median": row.get(
            "paired_area_ratio_reference_median", ""
        ),
        "paired_area_ratio_status": row.get("paired_area_ratio_status", ""),
        "missing_ms2_explanation": row.get("missing_ms2_explanation", ""),
        "false_positive_review_status": row.get("false_positive_review_status", ""),
        "false_positive_review_reasons": row.get("false_positive_review_reasons", ""),
        "selection_status": row.get("selection_status", ""),
        "product_switch_allowed": row.get("product_switch_allowed", ""),
        "gate_decision": row.get("gate_decision", ""),
        "png_path": str(png_path),
        "pdf_path": str(pdf_path),
    }


def _safe_asls(intensity: np.ndarray) -> np.ndarray:
    values = np.asarray(intensity, dtype=float)
    if len(values) < 3:
        return np.zeros_like(values)
    return asls_baseline(values)


def _baseline_plus_gaussian15(
    intensity: np.ndarray,
    baseline: np.ndarray,
) -> np.ndarray:
    residual = np.asarray(intensity, dtype=float) - np.asarray(baseline, dtype=float)
    return np.asarray(baseline, dtype=float) + gaussian15_morphology_trace(residual)


def _plot_rt_window(
    target: Target,
    istd_target: Target,
    *,
    previous_interval: CandidateInterval,
    selected_interval: CandidateInterval,
    paired_istd_rt: float | None,
    istd_product_interval: IstdProductInterval | None,
    expected_analyte_rt: float | None,
) -> tuple[float, float]:
    values = [
        target.rt_min,
        target.rt_max,
        istd_target.rt_min,
        istd_target.rt_max,
        previous_interval.rt_start,
        previous_interval.rt_end,
        selected_interval.rt_start,
        selected_interval.rt_end,
    ]
    if istd_product_interval is not None:
        values.extend(
            (
                istd_product_interval.rt_start,
                istd_product_interval.rt_end,
            )
        )
    values.extend(
        value
        for value in (paired_istd_rt, expected_analyte_rt)
        if value is not None
    )
    return min(values) - 0.25, max(values) + 0.25


def _expected_analyte_rt(row: Mapping[str, str]) -> float | None:
    paired_rt = _optional_float(row.get("paired_istd_rt", ""))
    expected_delta = _optional_float(row.get("pair_rt_delta_expected", ""))
    if paired_rt is None or expected_delta is None:
        return None
    return paired_rt + expected_delta


def _target_for_row(row: Mapping[str, str], targets: Mapping[str, Target]) -> Target:
    label = _required_text(row, "target_label")
    try:
        return targets[label]
    except KeyError as exc:
        raise ValueError(f"target not found in config: {label}") from exc


def _paired_istd_target(target: Target, targets: Mapping[str, Target]) -> Target:
    if not target.istd_pair:
        raise ValueError(f"{target.label}: target has no paired ISTD")
    try:
        return targets[target.istd_pair]
    except KeyError as exc:
        raise ValueError(
            f"{target.label}: paired ISTD not found: {target.istd_pair}"
        ) from exc


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


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"{path}: TSV file does not exist")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter="\t")]


def _read_istd_product_intervals(
    long_csv: Path | None,
) -> dict[tuple[str, str], IstdProductInterval]:
    if long_csv is None:
        return {}
    if not long_csv.is_file():
        raise ValueError(f"{long_csv}: long CSV file does not exist")
    intervals: dict[tuple[str, str], IstdProductInterval] = {}
    with long_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("Role", "") != "ISTD":
                continue
            rt = _optional_float(row.get("RT", ""))
            rt_start = _optional_float(row.get("PeakStart", ""))
            rt_end = _optional_float(row.get("PeakEnd", ""))
            sample = row.get("SampleName", "")
            target = row.get("Target", "")
            if (
                not sample
                or not target
                or rt is None
                or rt_start is None
                or rt_end is None
            ):
                continue
            intervals[(sample, target)] = IstdProductInterval(
                apex_rt=rt,
                rt_start=min(rt_start, rt_end),
                rt_end=max(rt_start, rt_end),
                product_state=row.get("Product State", ""),
                counted_detection=row.get("Counted Detection", ""),
            )
    return intervals


def _write_tsv(
    path: Path,
    headers: Sequence[str],
    rows: Sequence[Mapping[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(path, rows, headers, extrasaction="raise")


def _plot_group_for_row(row: Mapping[str, str]) -> str:
    if row.get("false_positive_review_status", "") == "product_switch_accepted":
        return "product_switch_accepted_reference"
    if (
        row.get("false_positive_review_status", "")
        == "false_positive_review_required"
    ):
        return "false_positive_review_required"
    if row.get("paired_area_ratio_status", "") == "outside_robust_range":
        return "paired_area_ratio_outside_active"
    return "row_approval_candidate"


def _is_sample_inapplicable_blocked(row: Mapping[str, str]) -> bool:
    for field in (
        "block_reason",
        "false_positive_review_reasons",
        "Projection Exclusion Reasons",
        "projection_exclusion_reasons",
    ):
        if "target_sample_applicability:" in row.get(field, ""):
            return True
    return False


def _row_identity(row: Mapping[str, str]) -> str:
    return (
        row.get("expected_diff_stable_row_id")
        or f"{row.get('sample_name', '')}|{row.get('target_label', '')}|"
        f"{row.get('selected_candidate_id', '')}"
    )


def _plot_stem(rank: int, request: TargetPairPlotRequest) -> str:
    row = request.row
    return (
        f"{rank:02d}_{_safe_stem(request.plot_group)}_"
        f"{_safe_stem(row.get('sample_name', 'sample'))}_"
        f"{_safe_stem(row.get('target_label', 'target'))}"
    )


def _safe_stem(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return stem.strip("._") or "value"


def _required_text(row: Mapping[str, str], key: str) -> str:
    value = row.get(key, "")
    if value == "":
        raise ValueError(f"missing required column value: {key}")
    return value


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if not np.isfinite(parsed):
        return None
    return parsed


def _abs_pair_rt_delta_error(row: Mapping[str, str]) -> float:
    value = _optional_float(row.get("pair_rt_delta_error", ""))
    return abs(value) if value is not None else -1.0


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.5f}"


def _dedup_legend_handles(axes: Sequence[Any]) -> tuple[list[Any], list[str]]:
    by_label: dict[str, Any] = {}
    for ax in axes:
        handles, labels = ax.get_legend_handles_labels()
        for handle, label in zip(handles, labels, strict=True):
            if label and label not in by_label:
                by_label[label] = handle
    return list(by_label.values()), list(by_label.keys())


def _non_negative_int(raw: str) -> int:
    value = int(raw)
    if value < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return value


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
