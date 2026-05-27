"""P2 baseline truth audit for AsLS shadow gate targets."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.baseline import asls_baseline
from xic_extractor.peak_detection.baseline import bounded_trace_interval

ROW_FIELDS = (
    "target_label",
    "feature_family_id",
    "sample_stem",
    "status",
    "raw_area",
    "linear_area",
    "asls_area",
    "linear_raw_pct",
    "asls_raw_pct",
    "asls_vs_linear_pct",
    "linear_baseline_subtracted_pct",
    "asls_baseline_subtracted_pct",
    "linear_edge_delta_pct",
    "outside_background_pct",
    "peak_start_rt",
    "apex_rt",
    "peak_end_rt",
    "trace_point_count",
    "classification",
    "review_reason",
    "plot_path",
)

SUMMARY_FIELDS = (
    "target_label",
    "feature_family_id",
    "row_count",
    "dominant_classification",
    "classification_counts",
    "median_linear_baseline_subtracted_pct",
    "median_asls_baseline_subtracted_pct",
    "median_asls_vs_linear_pct",
    "max_asls_vs_linear_pct",
    "median_linear_edge_delta_pct",
    "median_outside_background_pct",
    "review_status",
    "plot_path",
)

_GATE_REQUIRED_COLUMNS = {
    "target_label",
    "selected_feature_id",
    "status",
}
_AUDIT_REQUIRED_COLUMNS = {
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "area_baseline_corrected",
    "family_center_mz",
    "peak_start_rt",
    "apex_rt",
    "peak_end_rt",
}
_MISSING_VALUES = {"", "ND", "NA", "N/A", "NONE", "NULL"}

TraceLoader = Callable[
    [str, float, float, float, float],
    tuple[np.ndarray, np.ndarray],
]


@dataclass(frozen=True)
class AreaMetrics:
    linear_raw_pct: float | None
    asls_raw_pct: float | None
    asls_vs_linear_pct: float | None
    linear_baseline_subtracted_pct: float | None
    asls_baseline_subtracted_pct: float | None


@dataclass(frozen=True)
class BaselineTruthRow:
    target_label: str
    feature_family_id: str
    sample_stem: str
    status: str
    raw_area: float | None
    linear_area: float | None
    asls_area: float | None
    linear_raw_pct: float | None
    asls_raw_pct: float | None
    asls_vs_linear_pct: float | None
    linear_baseline_subtracted_pct: float | None
    asls_baseline_subtracted_pct: float | None
    linear_edge_delta_pct: float | None
    outside_background_pct: float | None
    peak_start_rt: float | None
    apex_rt: float | None
    peak_end_rt: float | None
    trace_point_count: int
    classification: str
    review_reason: str
    plot_path: str


@dataclass(frozen=True)
class BaselineTruthOutputs:
    rows_tsv: Path
    summary_tsv: Path
    json_path: Path
    markdown_path: Path
    plot_dir: Path


@dataclass(frozen=True)
class BaselineTruthResult:
    row_count: int
    family_count: int
    rows: tuple[BaselineTruthRow, ...]
    summary_rows: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class _GateTarget:
    target_label: str
    feature_family_id: str


@dataclass(frozen=True)
class _TracePlotRow:
    row: BaselineTruthRow
    rt: np.ndarray
    intensity: np.ndarray


def compute_area_metrics(
    *,
    raw_area: float | None,
    linear_area: float | None,
    asls_area: float | None,
) -> AreaMetrics:
    linear_raw_pct = _ratio_pct(linear_area, raw_area)
    asls_raw_pct = _ratio_pct(asls_area, raw_area)
    asls_vs_linear_pct = (
        None
        if linear_area is None or linear_area <= 0 or asls_area is None
        else (asls_area - linear_area) / linear_area * 100.0
    )
    return AreaMetrics(
        linear_raw_pct=linear_raw_pct,
        asls_raw_pct=asls_raw_pct,
        asls_vs_linear_pct=asls_vs_linear_pct,
        linear_baseline_subtracted_pct=(
            None if linear_raw_pct is None else 100.0 - linear_raw_pct
        ),
        asls_baseline_subtracted_pct=(
            None if asls_raw_pct is None else 100.0 - asls_raw_pct
        ),
    )


def classify_baseline_truth_row(
    metrics: AreaMetrics,
    *,
    trace_point_count: int,
    linear_edge_delta_pct: float | None,
    outside_background_pct: float | None = None,
) -> tuple[str, str]:
    reasons: list[str] = []
    if trace_point_count < 3:
        return "not_assessable", "trace_point_count_lt_3"
    if metrics.asls_vs_linear_pct is None:
        return "not_assessable", "area_metric_unavailable"
    if abs(metrics.asls_vs_linear_pct) <= 5.0:
        return "methods_similar", "asls_vs_linear_within_5pct"
    if metrics.asls_raw_pct is not None and metrics.asls_raw_pct >= 98.0:
        reasons.append("asls_near_raw")
    if (
        metrics.linear_baseline_subtracted_pct is not None
        and metrics.linear_baseline_subtracted_pct >= 5.0
    ):
        reasons.append("linear_subtracts_gt_5pct")
    if (
        metrics.linear_baseline_subtracted_pct is not None
        and metrics.linear_baseline_subtracted_pct >= 10.0
    ):
        reasons.append("linear_subtracts_gt_10pct")
    if linear_edge_delta_pct is not None and abs(linear_edge_delta_pct) >= 10.0:
        reasons.append("linear_edge_elevated")
    elif linear_edge_delta_pct is not None:
        reasons.append("linear_edge_not_elevated")
    if outside_background_pct is not None and outside_background_pct <= 5.0:
        reasons.append("outside_background_low")
    elif outside_background_pct is not None and outside_background_pct >= 10.0:
        reasons.append("outside_background_elevated")
    reason_set = set(reasons)
    if "asls_near_raw" in reason_set and "outside_background_elevated" in reason_set:
        return "asls_under_subtraction_plausible", ";".join(reasons)
    if (
        "asls_near_raw" in reason_set
        and "linear_subtracts_gt_5pct" in reason_set
        and "outside_background_low" in reason_set
    ):
        return "linear_edge_over_subtraction_plausible", ";".join(reasons)
    if {
        "asls_near_raw",
        "linear_subtracts_gt_10pct",
        "linear_edge_elevated",
    } <= reason_set:
        return "linear_edge_over_subtraction_plausible", ";".join(reasons)
    return "mixed_or_review_required", ";".join(reasons)


def _ratio_pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    value = numerator / denominator * 100.0
    return value if math.isfinite(value) else None


def build_baseline_truth_row(
    *,
    target_label: str,
    feature_family_id: str,
    sample_stem: str,
    status: str,
    raw_area: float | None,
    linear_area: float | None,
    asls_area: float | None,
    mz: float,
    peak_start_rt: float | None,
    apex_rt: float | None,
    peak_end_rt: float | None,
    rt: object,
    intensity: object,
    plot_path: str,
) -> BaselineTruthRow:
    _ = mz
    rt_array = np.asarray(rt, dtype=float)
    intensity_array = np.asarray(intensity, dtype=float)
    left, right = _rt_window_indices(rt_array, peak_start_rt, peak_end_rt)
    trace_point_count = len(rt_array[left:right])
    linear_delta = _linear_edge_delta_pct(intensity_array, left, right)
    outside_background = _outside_background_pct(intensity_array, left, right)
    metrics = compute_area_metrics(
        raw_area=raw_area,
        linear_area=linear_area,
        asls_area=asls_area,
    )
    classification, reason = classify_baseline_truth_row(
        metrics,
        trace_point_count=trace_point_count,
        linear_edge_delta_pct=linear_delta,
        outside_background_pct=outside_background,
    )
    return BaselineTruthRow(
        target_label=target_label,
        feature_family_id=feature_family_id,
        sample_stem=sample_stem,
        status=status,
        raw_area=raw_area,
        linear_area=linear_area,
        asls_area=asls_area,
        linear_raw_pct=metrics.linear_raw_pct,
        asls_raw_pct=metrics.asls_raw_pct,
        asls_vs_linear_pct=metrics.asls_vs_linear_pct,
        linear_baseline_subtracted_pct=metrics.linear_baseline_subtracted_pct,
        asls_baseline_subtracted_pct=metrics.asls_baseline_subtracted_pct,
        linear_edge_delta_pct=linear_delta,
        outside_background_pct=outside_background,
        peak_start_rt=peak_start_rt,
        apex_rt=apex_rt,
        peak_end_rt=peak_end_rt,
        trace_point_count=trace_point_count,
        classification=classification,
        review_reason=reason,
        plot_path=plot_path,
    )


def _rt_window_indices(
    rt: np.ndarray,
    peak_start_rt: float | None,
    peak_end_rt: float | None,
) -> tuple[int, int]:
    if rt.ndim != 1 or len(rt) < 2:
        raise ValueError("rt must be a one-dimensional array with at least 2 points")
    if peak_start_rt is None or peak_end_rt is None:
        return 0, len(rt)
    left = int(np.searchsorted(rt, peak_start_rt, side="left"))
    right = int(np.searchsorted(rt, peak_end_rt, side="right"))
    return bounded_trace_interval(left, right, len(rt))


def _linear_edge_delta_pct(
    intensity: np.ndarray,
    left: int,
    right: int,
) -> float | None:
    if right - left < 2:
        return None
    segment = intensity[left:right]
    edge_mean = (float(segment[0]) + float(segment[-1])) / 2.0
    apex = float(np.max(segment))
    if apex <= 0:
        return None
    return edge_mean / apex * 100.0


def _outside_background_pct(
    intensity: np.ndarray,
    left: int,
    right: int,
) -> float | None:
    if right - left < 2:
        return None
    segment = intensity[left:right]
    apex = float(np.max(segment))
    if apex <= 0:
        return None
    outside = np.concatenate((intensity[:left], intensity[right:]))
    if len(outside) == 0:
        return None
    background = float(np.median(np.maximum(outside, 0.0)))
    return background / apex * 100.0


def run_p2_baseline_truth_audit(
    *,
    p2_gate_rows_tsv: Path,
    alignment_integration_audit_tsv: Path,
    output_dir: Path,
    raw_dir: Path | None = None,
    dll_dir: Path | None = None,
    ppm: float = 10.0,
    rt_margin_min: float = 0.4,
    trace_loader: TraceLoader | None = None,
    include_gate_statuses: Sequence[str] = ("FAIL",),
) -> tuple[BaselineTruthOutputs, BaselineTruthResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_dir = output_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    outputs = BaselineTruthOutputs(
        rows_tsv=output_dir / "baseline_truth_audit_rows.tsv",
        summary_tsv=output_dir / "baseline_truth_audit_summary.tsv",
        json_path=output_dir / "baseline_truth_audit.json",
        markdown_path=output_dir / "baseline_truth_audit.md",
        plot_dir=plot_dir,
    )
    loader = trace_loader or _default_trace_loader(raw_dir=raw_dir, dll_dir=dll_dir)
    gate_targets = _read_gate_targets(
        p2_gate_rows_tsv,
        include_statuses=include_gate_statuses,
    )
    audit_rows = _read_tsv(alignment_integration_audit_tsv, _AUDIT_REQUIRED_COLUMNS)
    targets_by_family = {target.feature_family_id: target for target in gate_targets}
    rows: list[BaselineTruthRow] = []
    plot_rows_by_family: dict[str, list[_TracePlotRow]] = defaultdict(list)

    for audit_row in audit_rows:
        family_id = audit_row["feature_family_id"].strip()
        target = targets_by_family.get(family_id)
        if target is None:
            continue
        mz = _required_float(audit_row.get("family_center_mz"), "family_center_mz")
        peak_start_rt = _optional_float(audit_row.get("peak_start_rt"))
        apex_rt = _optional_float(audit_row.get("apex_rt"))
        peak_end_rt = _optional_float(audit_row.get("peak_end_rt"))
        rt_min, rt_max = _trace_bounds(
            peak_start_rt=peak_start_rt,
            apex_rt=apex_rt,
            peak_end_rt=peak_end_rt,
            margin_min=rt_margin_min,
        )
        rt, intensity = loader(
            audit_row["sample_stem"].strip(),
            mz,
            rt_min,
            rt_max,
            ppm,
        )
        linear_area, asls_area = _linear_and_asls_area(audit_row)
        plot_rel_path = f"plots/{_safe_filename(target.target_label)}__{family_id}.png"
        row = build_baseline_truth_row(
            target_label=target.target_label,
            feature_family_id=family_id,
            sample_stem=audit_row["sample_stem"].strip(),
            status=audit_row["status"].strip(),
            raw_area=_optional_float(audit_row.get("area")),
            linear_area=linear_area,
            asls_area=asls_area,
            mz=mz,
            peak_start_rt=peak_start_rt,
            apex_rt=apex_rt,
            peak_end_rt=peak_end_rt,
            rt=rt,
            intensity=intensity,
            plot_path=plot_rel_path,
        )
        rows.append(row)
        plot_rows_by_family[family_id].append(
            _TracePlotRow(
                row=row,
                rt=np.asarray(rt, dtype=float),
                intensity=np.asarray(intensity, dtype=float),
            )
        )

    for family_rows in plot_rows_by_family.values():
        _write_family_plot(
            output_dir / family_rows[0].row.plot_path,
            rows=family_rows,
        )

    summary_rows = tuple(_build_summary_rows(rows))
    result = BaselineTruthResult(
        row_count=len(rows),
        family_count=len(summary_rows),
        rows=tuple(rows),
        summary_rows=summary_rows,
    )
    _write_tsv(outputs.rows_tsv, ROW_FIELDS, (_row_dict(row) for row in result.rows))
    _write_tsv(outputs.summary_tsv, SUMMARY_FIELDS, result.summary_rows)
    _write_json(outputs.json_path, result)
    _write_markdown(outputs.markdown_path, result)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a diagnostic-only baseline truth audit for P2 AsLS shadow "
            "gate ISTD families."
        )
    )
    parser.add_argument("--p2-gate-rows-tsv", type=Path, required=True)
    parser.add_argument("--alignment-integration-audit-tsv", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--dll-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--rt-margin-min", type=float, default=0.4)
    parser.add_argument(
        "--include-gate-status",
        action="append",
        dest="include_gate_statuses",
        help=(
            "Gate row status to include in the audit. Repeat to include multiple "
            "statuses. Defaults to FAIL."
        ),
    )
    args = parser.parse_args(argv)

    try:
        outputs, result = run_p2_baseline_truth_audit(
            p2_gate_rows_tsv=args.p2_gate_rows_tsv,
            alignment_integration_audit_tsv=args.alignment_integration_audit_tsv,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            output_dir=args.output_dir,
            ppm=args.ppm,
            rt_margin_min=args.rt_margin_min,
            include_gate_statuses=tuple(args.include_gate_statuses or ("FAIL",)),
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Audit JSON: {outputs.json_path}")
    print(f"Audit report: {outputs.markdown_path}")
    print(f"Plot directory: {outputs.plot_dir}")
    print(f"Rows: {result.row_count}; Families: {result.family_count}")
    return 0


def _linear_and_asls_area(row: Mapping[str, str]) -> tuple[float | None, float | None]:
    promoted_linear = _optional_float(row.get("area_baseline_corrected_linear_edge"))
    reported_area = _optional_float(row.get("area_baseline_corrected"))
    if promoted_linear is not None:
        return promoted_linear, reported_area
    return reported_area, _optional_float(row.get("area_baseline_corrected_asls"))


def _read_gate_targets(
    path: Path,
    *,
    include_statuses: Sequence[str],
) -> tuple[_GateTarget, ...]:
    normalized_statuses = _normalize_gate_statuses(include_statuses)
    rows = _read_tsv(path, _GATE_REQUIRED_COLUMNS)
    return tuple(
        _GateTarget(
            target_label=row["target_label"].strip(),
            feature_family_id=row["selected_feature_id"].strip(),
        )
        for row in rows
        if row.get("status", "").strip().upper() in normalized_statuses
        and row.get("target_label", "").strip()
        and row.get("selected_feature_id", "").strip()
    )


def _normalize_gate_statuses(statuses: Sequence[str]) -> frozenset[str]:
    normalized = frozenset(
        status.strip().upper() for status in statuses if status.strip()
    )
    if not normalized:
        raise ValueError("include_gate_statuses must contain at least one status")
    return normalized


def _default_trace_loader(
    *,
    raw_dir: Path | None,
    dll_dir: Path | None,
) -> TraceLoader:
    if raw_dir is None or dll_dir is None:
        raise ValueError("raw_dir and dll_dir are required when trace_loader is absent")

    def load_trace(
        sample_stem: str,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        from xic_extractor.raw_reader import open_raw
        from xic_extractor.xic_models import XICRequest

        raw_path = raw_dir / f"{sample_stem}.raw"
        if not raw_path.is_file():
            raise FileNotFoundError(f"RAW file not found: {raw_path}")
        with open_raw(raw_path, dll_dir) as raw:
            trace = raw.extract_xic_many(
                (XICRequest(mz=mz, rt_min=rt_min, rt_max=rt_max, ppm_tol=ppm),)
            )[0]
        return np.asarray(trace.rt, dtype=float), np.asarray(trace.intensity, dtype=float)

    return load_trace


def _trace_bounds(
    *,
    peak_start_rt: float | None,
    apex_rt: float | None,
    peak_end_rt: float | None,
    margin_min: float,
) -> tuple[float, float]:
    if peak_start_rt is not None and peak_end_rt is not None:
        return max(0.0, peak_start_rt - margin_min), peak_end_rt + margin_min
    if apex_rt is not None:
        return max(0.0, apex_rt - margin_min), apex_rt + margin_min
    raise ValueError("peak_start_rt/peak_end_rt or apex_rt is required for trace extraction")


def _build_summary_rows(rows: Sequence[BaselineTruthRow]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[BaselineTruthRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.target_label, row.feature_family_id)].append(row)

    summaries: list[dict[str, object]] = []
    for (target_label, family_id), family_rows in sorted(grouped.items()):
        class_counts = Counter(row.classification for row in family_rows)
        dominant = class_counts.most_common(1)[0][0] if class_counts else ""
        summaries.append(
            {
                "target_label": target_label,
                "feature_family_id": family_id,
                "row_count": len(family_rows),
                "dominant_classification": dominant,
                "classification_counts": ";".join(
                    f"{name}:{count}" for name, count in sorted(class_counts.items())
                ),
                "median_linear_baseline_subtracted_pct": _median_present(
                    row.linear_baseline_subtracted_pct for row in family_rows
                ),
                "median_asls_baseline_subtracted_pct": _median_present(
                    row.asls_baseline_subtracted_pct for row in family_rows
                ),
                "median_asls_vs_linear_pct": _median_present(
                    row.asls_vs_linear_pct for row in family_rows
                ),
                "max_asls_vs_linear_pct": _max_present(
                    row.asls_vs_linear_pct for row in family_rows
                ),
                "median_linear_edge_delta_pct": _median_present(
                    row.linear_edge_delta_pct for row in family_rows
                ),
                "median_outside_background_pct": _median_present(
                    row.outside_background_pct for row in family_rows
                ),
                "review_status": _review_status(class_counts),
                "plot_path": family_rows[0].plot_path,
            }
        )
    return summaries


def _review_status(class_counts: Counter[str]) -> str:
    if not class_counts:
        return "not_assessable"
    if class_counts.get("asls_under_subtraction_plausible", 0):
        return "manual_review_required"
    if class_counts.get("mixed_or_review_required", 0):
        return "manual_review_required"
    if class_counts.get("linear_edge_over_subtraction_plausible", 0):
        return "linear_edge_over_subtraction_plausible"
    if class_counts.get("methods_similar", 0) == sum(class_counts.values()):
        return "methods_similar"
    return "manual_review_required"


def _write_json(path: Path, result: BaselineTruthResult) -> None:
    payload = {
        "row_count": result.row_count,
        "family_count": result.family_count,
        "summary_rows": list(result.summary_rows),
        "rows": [_row_dict(row) for row in result.rows],
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_markdown(path: Path, result: BaselineTruthResult) -> None:
    lines = [
        "# P2 Baseline Truth Audit",
        "",
        "Gate status: diagnostic_only",
        "",
        f"Rows: {result.row_count}",
        f"Families: {result.family_count}",
        "",
        "| Target | Family | Dominant classification | Median linear subtraction % | Median AsLS subtraction % | Median outside background % | Review status | Plot |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in result.summary_rows:
        plot_path = str(row.get("plot_path", ""))
        lines.append(
            "| "
            f"{row.get('target_label', '')} | "
            f"{row.get('feature_family_id', '')} | "
            f"{row.get('dominant_classification', '')} | "
            f"{_format_value(row.get('median_linear_baseline_subtracted_pct'))} | "
            f"{_format_value(row.get('median_asls_baseline_subtracted_pct'))} | "
            f"{_format_value(row.get('median_outside_background_pct'))} | "
            f"{row.get('review_status', '')} | "
            f"[plot]({plot_path}) |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_family_plot(path: Path, *, rows: Sequence[_TracePlotRow]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    n_rows = max(1, len(rows))
    fig, axes = plt.subplots(
        n_rows,
        1,
        figsize=(9, max(2.2, 1.8 * n_rows)),
        sharex=False,
        squeeze=False,
    )
    for axis, plot_row in zip(axes[:, 0], rows):
        rt = plot_row.rt
        intensity = plot_row.intensity
        row = plot_row.row
        left, right = _rt_window_indices(rt, row.peak_start_rt, row.peak_end_rt)
        axis.plot(rt, intensity, color="#222222", linewidth=1.0, label="raw")
        _plot_baselines(axis, rt, intensity, left, right)
        for value, color, label in (
            (row.peak_start_rt, "#666666", "start"),
            (row.apex_rt, "#1f77b4", "apex"),
            (row.peak_end_rt, "#666666", "end"),
        ):
            if value is not None:
                axis.axvline(value, color=color, linewidth=0.8, alpha=0.75)
        axis.set_title(
            (
                f"{row.sample_stem} | {row.classification} | "
                f"AsLS/linear={_format_value(row.asls_vs_linear_pct)}%"
            ),
            fontsize=8,
        )
        axis.set_ylabel("intensity")
    axes[0, 0].legend(loc="upper right", fontsize=7)
    axes[-1, 0].set_xlabel("RT (min)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_baselines(
    axis: object,
    rt: np.ndarray,
    intensity: np.ndarray,
    left: int,
    right: int,
) -> None:
    segment = intensity[left:right]
    segment_rt = rt[left:right]
    if len(segment) >= 2:
        linear = np.linspace(float(segment[0]), float(segment[-1]), len(segment))
        axis.plot(
            segment_rt,
            linear,
            color="#d62728",
            linewidth=0.9,
            linestyle="--",
            label="linear edge",
        )
    if len(intensity) >= 3 and np.all(np.isfinite(intensity)):
        baseline = asls_baseline(intensity)
        axis.plot(
            rt,
            baseline,
            color="#2ca02c",
            linewidth=0.9,
            linestyle=":",
            label="AsLS",
        )


def _write_tsv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field)) for field in fieldnames})


def _read_tsv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or ())
        missing = sorted(required_columns - columns)
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def _row_dict(row: BaselineTruthRow) -> dict[str, object]:
    return asdict(row)


def _optional_float(value: object) -> float | None:
    text = "" if value is None else str(value).strip()
    if text.upper() in _MISSING_VALUES:
        return None
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"non-numeric numeric field value: {text}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite numeric field value: {text}")
    return parsed


def _required_float(value: object, field_name: str) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        raise ValueError(f"{field_name} is required")
    return parsed


def _median_present(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return median(present) if present else None


def _max_present(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.6g}"
    return str(value)


def _safe_filename(value: str) -> str:
    chars = [char if char.isalnum() or char in {"-", "_"} else "_" for char in value]
    safe = "".join(chars).strip("_")
    return safe or "target"


if __name__ == "__main__":
    raise SystemExit(main())
