"""Build a mode-aware review surface from changed-row family MS1 overlays."""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics.family_ms1_overlay_evidence import _gaussian_smooth_values
from tools.diagnostics.family_ms1_overlay_models import (
    APEX_ALIGN_GRID_SIZE,
    APEX_ALIGN_HALF_WINDOW_MIN,
    GLOBAL_APEX_CONFLICT_DELTA_MIN,
    LOCAL_APEX_SUPPORT_DELTA_MIN,
    SHAPE_SUPPORT_MIN,
)
from tools.diagnostics.family_ms1_overlay_rendering_styles import (
    PLOT_GAUSSIAN_SMOOTH_POINTS,
)
from xic_extractor.alignment.shared_peak_identity_explanation import (
    machine_evidence_support,
    ms1_peak_modes,
    peak_hypothesis_selection,
    rt_mode_evidence,
)
from xic_extractor.diagnostics.diagnostic_io import (
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)

OVERLAY_SUMMARY_REQUIRED_COLUMNS = (
    "rank",
    "feature_family_id",
    "status",
    "family_verdict",
    "png_path",
    "pdf_path",
    "trace_data_json",
)
CHANGED_ROW_REQUIRED_COLUMNS = ("stable_row_id",)
IDENTITY_REQUIRED_COLUMNS = (
    "peak_hypothesis_id",
    "row_identity_basis",
    "source_feature_family_ids",
)
MODE_GAP_MIN = 0.5
MIN_MODE_CLUSTER_SIZE = 2
SHAPE_STRONG_MIN = 0.80
ALIGNMENT_CENTER_MODE_DELTA_SEC = 30.0
MATRIX_RT_DRIFT_POLICY_REQUIRED_COLUMNS = (
    machine_evidence_support.MATRIX_RT_DRIFT_POLICY_REQUIRED_COLUMNS
)
ALIGNMENT_CELL_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "apex_rt",
    "rt_delta_sec",
)
MS1_PATTERN_COHERENCE_REQUIRED_COLUMNS = (
    machine_evidence_support.MS1_PATTERN_COHERENCE_REQUIRED_COLUMNS
)

SAMPLE_REVIEW_COLUMNS = (
    "rank",
    "feature_family_id",
    "sample_stem",
    "baseline_peak_hypothesis_ids",
    "active_peak_hypothesis_ids",
    "active_identity_status",
    "family_verdict",
    "cell_status",
    "cell_group",
    "cell_area",
    "cell_height",
    "cell_apex_rt",
    "trace_apex_rt",
    "trace_apex_delta_min",
    "apex_aligned_shape_similarity",
    "selected_mode_id",
    "rt_mode_status",
    "rt_mode_evidence_level",
    "selected_mode_role",
    "selected_mode_tag_status",
    "family_mode_class",
    "family_mode_count",
    "peak_hypothesis_id",
    "peak_hypothesis_status",
    "product_selection_action",
    "product_selection_blocker",
    "global_trace_mode_id",
    "alignment_mode_id",
    "alignment_mode_source",
    "alignment_apex_delta_sec",
    "alignment_mode_status",
    "display_mode_id",
    "mode_review_basis",
    "gaussian15_trace_mode_ids",
    "mode_review_warning",
    "trace_data_json",
    "original_png_path",
    "mode_plot_png_path",
)

SIMILARITY_REVIEW_COLUMNS = (
    "rank",
    "feature_family_id",
    "sample_stem",
    "peak_hypothesis_id",
    "selected_mode_id",
    "signal_rendering_source",
    "gaussian15_shape_similarity_to_mode",
    "shape_similarity_status",
    "global_apex_delta_sec",
    "global_apex_status",
    "matrix_rt_drift_status",
    "drift_corrected_rt_delta_sec",
    "drift_compatible_status",
    "ms1_pattern_status",
    "ms1_shape_correlation_score",
    "local_interference_score",
    "quick_review_score",
    "quick_review_badge",
    "quick_review_reasons",
    "diagnostic_only",
)

FAMILY_SUMMARY_COLUMNS = (
    "rank",
    "feature_family_id",
    "baseline_peak_hypothesis_ids",
    "active_peak_hypothesis_ids",
    "active_identity_status",
    "baseline_row_identity_basis",
    "active_row_identity_basis",
    "source_feature_family_ids",
    "family_verdict",
    "family_mode_count",
    "rt_mode_status_counts",
    "peak_hypothesis_status_counts",
    "selected_mode_counts",
    "global_trace_mode_counts",
    "alignment_mode_counts",
    "mode_review_basis",
    "gaussian15_trace_mode_counts",
    "gaussian15_trace_mode_windows",
    "mode_review_verdict",
    "mode_review_warning",
    "changed_row_reason",
    "presence_impact",
    "evidence_tier",
    "reviewer_verdict",
    "trace_data_json",
    "original_png_path",
    "original_pdf_path",
    "mode_plot_png_path",
    "mode_aligned_plot_png_path",
)

SIMILARITY_FAMILY_SUMMARY_COLUMNS = (
    "rank",
    "feature_family_id",
    "similarity_row_count",
    "quick_review_badge_counts",
    "shape_similarity_status_counts",
    "global_apex_status_counts",
    "matrix_rt_drift_status_counts",
    "median_gaussian15_shape_similarity_to_mode",
    "median_quick_review_score",
    "diagnostic_only",
)


@dataclass(frozen=True)
class ModeOverlayReviewOutputs:
    rt_mode_evidence_tsv: Path
    peak_hypothesis_selection_tsv: Path
    sample_review_tsv: Path
    family_summary_tsv: Path
    similarity_review_tsv: Path
    similarity_family_summary_tsv: Path
    review_gallery_html: Path


@dataclass(frozen=True)
class TraceData:
    family_id: str
    path: Path
    overlay_row: Mapping[str, str]
    payload: Mapping[str, Any]
    traces: tuple[Mapping[str, Any], ...]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_changed_row_mode_overlay_review(
            changed_row_bundle_tsv=args.changed_row_bundle_tsv,
            overlay_batch_summary_tsv=args.overlay_batch_summary_tsv,
            baseline_alignment_matrix_identity_tsv=(
                args.baseline_alignment_matrix_identity_tsv
            ),
            active_alignment_matrix_identity_tsv=args.active_alignment_matrix_identity_tsv,
            candidate_ms2_pattern_evidence_tsv=args.candidate_ms2_pattern_evidence_tsv,
            matrix_rt_drift_policy_tsv=args.matrix_rt_drift_policy_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            ms1_pattern_coherence_tsv=args.ms1_pattern_coherence_tsv,
            output_dir=args.output_dir,
            render_plots=not args.no_plots,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"mode-aware review gallery: {outputs.review_gallery_html}")
    return 0


def run_changed_row_mode_overlay_review(
    *,
    changed_row_bundle_tsv: Path,
    overlay_batch_summary_tsv: Path,
    baseline_alignment_matrix_identity_tsv: Path | None = None,
    active_alignment_matrix_identity_tsv: Path | None = None,
    candidate_ms2_pattern_evidence_tsv: Path | None = None,
    matrix_rt_drift_policy_tsv: Path | None = None,
    alignment_cells_tsv: Path | None = None,
    ms1_pattern_coherence_tsv: Path | None = None,
    output_dir: Path,
    render_plots: bool = True,
) -> ModeOverlayReviewOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_rows = read_tsv_required(
        overlay_batch_summary_tsv,
        OVERLAY_SUMMARY_REQUIRED_COLUMNS,
    )
    changed_rows = read_tsv_required(
        changed_row_bundle_tsv,
        CHANGED_ROW_REQUIRED_COLUMNS,
    )
    changed_by_family = {
        row["stable_row_id"]: row for row in changed_rows if row.get("stable_row_id")
    }
    baseline_identity = (
        _identity_by_family(baseline_alignment_matrix_identity_tsv) or {}
    )
    active_identity = _identity_by_family(active_alignment_matrix_identity_tsv)
    trace_data = _load_trace_data(
        overlay_rows,
        base_dir=overlay_batch_summary_tsv.parent,
    )
    trace_paths = tuple(item.path for item in trace_data)
    oracle_keys = _trace_oracle_keys(trace_data)
    rt_mode_rows = rt_mode_evidence.build_rt_mode_evidence_rows_from_overlay_trace_data(
        overlay_trace_data_jsons=trace_paths,
        oracle_keys=oracle_keys,
        candidate_ms2_pattern_evidence_tsv=candidate_ms2_pattern_evidence_tsv,
    )
    peak_hypothesis_rows = (
        peak_hypothesis_selection.build_peak_hypothesis_selection_rows(
            rt_mode_rows=rt_mode_rows,
            oracle_keys=oracle_keys,
        )
    )
    rt_mode_tsv = output_dir / "changed_row_rt_mode_evidence.tsv"
    peak_hypothesis_tsv = output_dir / "changed_row_peak_hypothesis_selection.tsv"
    rt_mode_evidence.write_rt_mode_evidence_rows(rt_mode_tsv, rt_mode_rows)
    peak_hypothesis_selection.write_peak_hypothesis_selection_rows(
        peak_hypothesis_tsv,
        peak_hypothesis_rows,
    )

    rt_rows_by_key = _rows_by_key(rt_mode_rows)
    hypothesis_rows_by_key = _rows_by_key(peak_hypothesis_rows)
    matrix_rt_drift_rows = _optional_rows_by_key(
        matrix_rt_drift_policy_tsv,
        MATRIX_RT_DRIFT_POLICY_REQUIRED_COLUMNS,
    )
    alignment_cell_rows = _optional_rows_by_key(
        alignment_cells_tsv,
        ALIGNMENT_CELL_REQUIRED_COLUMNS,
    )
    global_mode_ids_by_family = {
        item.family_id: _global_trace_mode_ids(item.traces) for item in trace_data
    }
    alignment_modes_by_family = {
        item.family_id: _alignment_mode_assignments(
            family_id=item.family_id,
            traces=item.traces,
            alignment_cell_rows=alignment_cell_rows,
            matrix_rt_drift_rows=matrix_rt_drift_rows,
        )
        for item in trace_data
    }
    gaussian15_modes_by_family = {
        item.family_id: _gaussian15_trace_mode_windows(item) for item in trace_data
    }
    mode_plot_paths: dict[str, Path] = {}
    mode_aligned_plot_paths: dict[str, Path] = {}
    sample_rows = _sample_review_rows(
        trace_data=trace_data,
        rt_rows_by_key=rt_rows_by_key,
        hypothesis_rows_by_key=hypothesis_rows_by_key,
        baseline_identity=baseline_identity,
        active_identity=active_identity,
        global_mode_ids_by_family=global_mode_ids_by_family,
        alignment_modes_by_family=alignment_modes_by_family,
        gaussian15_modes_by_family=gaussian15_modes_by_family,
        output_dir=output_dir,
    )
    if render_plots:
        for item in trace_data:
            family_sample_rows = [
                row
                for row in sample_rows
                if row["feature_family_id"] == item.family_id
            ]
            mode_plot_paths[item.family_id] = _render_mode_plot(
                trace_data=item,
                sample_rows=family_sample_rows,
                gaussian15_modes=gaussian15_modes_by_family.get(item.family_id, ()),
                output_dir=output_dir,
            )
            mode_aligned_plot_paths[item.family_id] = _render_mode_aligned_plot(
                trace_data=item,
                sample_rows=family_sample_rows,
                gaussian15_modes=gaussian15_modes_by_family.get(item.family_id, ()),
                output_dir=output_dir,
            )
    sample_rows = [
        {
            **row,
            "mode_plot_png_path": str(
                mode_plot_paths.get(row["feature_family_id"], ""),
            ),
        }
        for row in sample_rows
    ]
    ms1_pattern_rows = _optional_rows_by_key(
        ms1_pattern_coherence_tsv,
        MS1_PATTERN_COHERENCE_REQUIRED_COLUMNS,
    )
    similarity_rows = _similarity_review_rows(
        trace_data=trace_data,
        sample_rows=sample_rows,
        matrix_rt_drift_rows=matrix_rt_drift_rows,
        ms1_pattern_rows=ms1_pattern_rows,
    )
    similarity_family_rows = _similarity_family_summary_rows(similarity_rows)
    family_rows = _family_summary_rows(
        trace_data=trace_data,
        sample_rows=sample_rows,
        changed_by_family=changed_by_family,
        baseline_identity=baseline_identity,
        active_identity=active_identity,
        mode_plot_paths=mode_plot_paths,
        mode_aligned_plot_paths=mode_aligned_plot_paths,
        gaussian15_modes_by_family=gaussian15_modes_by_family,
    )

    sample_review_tsv = output_dir / "changed_row_mode_sample_review.tsv"
    family_summary_tsv = output_dir / "changed_row_mode_overlay_summary.tsv"
    similarity_review_tsv = output_dir / "changed_row_similarity_review.tsv"
    similarity_family_summary_tsv = output_dir / "changed_row_similarity_summary.tsv"
    gallery_html = output_dir / "mode_aware_review_gallery.html"
    write_tsv(
        sample_review_tsv,
        sample_rows,
        SAMPLE_REVIEW_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        family_summary_tsv,
        family_rows,
        FAMILY_SUMMARY_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        similarity_review_tsv,
        similarity_rows,
        SIMILARITY_REVIEW_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        similarity_family_summary_tsv,
        similarity_family_rows,
        SIMILARITY_FAMILY_SUMMARY_COLUMNS,
        lineterminator="\n",
    )
    _write_review_gallery(
        gallery_html,
        family_rows=family_rows,
        sample_rows=sample_rows,
        similarity_rows=similarity_rows,
        rt_mode_tsv=rt_mode_tsv,
        peak_hypothesis_tsv=peak_hypothesis_tsv,
        family_summary_tsv=family_summary_tsv,
        sample_review_tsv=sample_review_tsv,
        similarity_review_tsv=similarity_review_tsv,
        similarity_family_summary_tsv=similarity_family_summary_tsv,
    )
    return ModeOverlayReviewOutputs(
        rt_mode_evidence_tsv=rt_mode_tsv,
        peak_hypothesis_selection_tsv=peak_hypothesis_tsv,
        sample_review_tsv=sample_review_tsv,
        family_summary_tsv=family_summary_tsv,
        similarity_review_tsv=similarity_review_tsv,
        similarity_family_summary_tsv=similarity_family_summary_tsv,
        review_gallery_html=gallery_html,
    )


def _load_trace_data(
    overlay_rows: Sequence[Mapping[str, str]],
    *,
    base_dir: Path,
) -> tuple[TraceData, ...]:
    items: list[TraceData] = []
    for row in overlay_rows:
        if row.get("status") != "success":
            continue
        trace_json = text_value(row.get("trace_data_json"))
        if not trace_json:
            continue
        path = _resolve_path(trace_json, base_dir=base_dir)
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, Mapping):
            raise ValueError(f"{path}: trace data must be a JSON object")
        family_id = text_value(payload.get("family_id")) or text_value(
            row.get("feature_family_id"),
        )
        traces = payload.get("traces")
        if not isinstance(traces, list):
            raise ValueError(f"{path}: trace data missing traces array")
        trace_rows = tuple(trace for trace in traces if isinstance(trace, Mapping))
        items.append(
            TraceData(
                family_id=family_id,
                path=path,
                overlay_row=row,
                payload=payload,
                traces=trace_rows,
            )
        )
    if not items:
        raise ValueError(f"{base_dir}: no successful overlay trace data found")
    return tuple(items)


def _trace_oracle_keys(trace_data: Sequence[TraceData]) -> tuple[tuple[str, str], ...]:
    keys = {
        (item.family_id, text_value(trace.get("sample_stem")))
        for item in trace_data
        for trace in item.traces
        if text_value(trace.get("sample_stem"))
    }
    return tuple(sorted(keys))


def _sample_review_rows(
    *,
    trace_data: Sequence[TraceData],
    rt_rows_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    hypothesis_rows_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    baseline_identity: Mapping[str, tuple[Mapping[str, str], ...]],
    active_identity: Mapping[str, tuple[Mapping[str, str], ...]] | None,
    global_mode_ids_by_family: Mapping[str, Mapping[str, str]],
    alignment_modes_by_family: Mapping[str, Mapping[str, Mapping[str, str]]],
    gaussian15_modes_by_family: Mapping[
        str,
        Sequence[ms1_peak_modes.Gaussian15PeakModeWindow],
    ],
    output_dir: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in trace_data:
        family_id = item.family_id
        baseline_rows = baseline_identity.get(family_id, ())
        active_rows = (
            active_identity.get(family_id, ())
            if active_identity is not None
            else ()
        )
        identity_status = _active_identity_status(
            baseline_rows=baseline_rows,
            active_rows=active_rows,
            active_identity_supplied=active_identity is not None,
        )
        global_modes = global_mode_ids_by_family.get(family_id, {})
        alignment_modes = alignment_modes_by_family.get(family_id, {})
        gaussian15_modes = gaussian15_modes_by_family.get(family_id, ())
        for trace in item.traces:
            sample_stem = text_value(trace.get("sample_stem"))
            if not sample_stem:
                continue
            key = (family_id, sample_stem)
            rt_row = rt_rows_by_key.get(key, {})
            hypothesis_row = hypothesis_rows_by_key.get(key, {})
            alignment_row = alignment_modes.get(sample_stem, {})
            display_mode_id = _display_mode_id(
                alignment_row=alignment_row,
                raw_mode_id=text_value(rt_row.get("selected_mode_id")),
            )
            mode_basis = _mode_review_basis(alignment_row)
            gaussian15_trace_modes = _gaussian15_trace_mode_ids(
                trace=trace,
                gaussian15_modes=gaussian15_modes,
            )
            warning = _sample_mode_warning(
                rt_row=rt_row,
                global_mode_id=global_modes.get(sample_stem, ""),
                global_mode_count=len(set(global_modes.values())),
                alignment_mode_id=text_value(alignment_row.get("alignment_mode_id")),
                alignment_mode_count=_alignment_mode_count(alignment_modes),
                mode_basis=mode_basis,
                gaussian15_trace_mode_ids=gaussian15_trace_modes,
            )
            rows.append(
                {
                    "rank": text_value(item.overlay_row.get("rank")),
                    "feature_family_id": family_id,
                    "sample_stem": sample_stem,
                    "baseline_peak_hypothesis_ids": _identity_peak_ids(baseline_rows),
                    "active_peak_hypothesis_ids": _identity_peak_ids(active_rows),
                    "active_identity_status": identity_status,
                    "family_verdict": text_value(
                        item.overlay_row.get("family_verdict"),
                    ),
                    "cell_status": text_value(trace.get("status")),
                    "cell_group": text_value(trace.get("group")),
                    "cell_area": _float_text(trace.get("cell_area")),
                    "cell_height": _float_text(trace.get("cell_height")),
                    "cell_apex_rt": _float_text(trace.get("cell_apex_rt")),
                    "trace_apex_rt": _float_text(trace.get("trace_apex_rt")),
                    "trace_apex_delta_min": _float_text(
                        trace.get("global_trace_apex_delta_min"),
                    ),
                    "apex_aligned_shape_similarity": _float_text(
                        trace.get("apex_aligned_shape_similarity"),
                    ),
                    "selected_mode_id": text_value(rt_row.get("selected_mode_id")),
                    "rt_mode_status": text_value(rt_row.get("rt_mode_status")),
                    "rt_mode_evidence_level": text_value(
                        rt_row.get("rt_mode_evidence_level"),
                    ),
                    "selected_mode_role": text_value(rt_row.get("selected_mode_role")),
                    "selected_mode_tag_status": text_value(
                        rt_row.get("selected_mode_tag_status"),
                    ),
                    "family_mode_class": text_value(rt_row.get("family_mode_class")),
                    "family_mode_count": text_value(rt_row.get("family_mode_count")),
                    "peak_hypothesis_id": text_value(
                        hypothesis_row.get("peak_hypothesis_id"),
                    ),
                    "peak_hypothesis_status": text_value(
                        hypothesis_row.get("peak_hypothesis_status"),
                    ),
                    "product_selection_action": text_value(
                        hypothesis_row.get("product_selection_action"),
                    ),
                    "product_selection_blocker": text_value(
                        hypothesis_row.get("product_selection_blocker"),
                    ),
                    "global_trace_mode_id": global_modes.get(sample_stem, ""),
                    "alignment_mode_id": text_value(
                        alignment_row.get("alignment_mode_id"),
                    ),
                    "alignment_mode_source": text_value(
                        alignment_row.get("alignment_mode_source"),
                    ),
                    "alignment_apex_delta_sec": text_value(
                        alignment_row.get("alignment_apex_delta_sec"),
                    ),
                    "alignment_mode_status": text_value(
                        alignment_row.get("alignment_mode_status"),
                    ),
                    "display_mode_id": display_mode_id,
                    "mode_review_basis": mode_basis,
                    "gaussian15_trace_mode_ids": gaussian15_trace_modes,
                    "mode_review_warning": warning,
                    "trace_data_json": str(item.path),
                    "original_png_path": _resolve_optional_artifact(
                        item.overlay_row.get("png_path"),
                        base_dir=item.path.parent,
                    ),
                    "mode_plot_png_path": "",
                }
            )
    return rows


def _family_summary_rows(
    *,
    trace_data: Sequence[TraceData],
    sample_rows: Sequence[Mapping[str, str]],
    changed_by_family: Mapping[str, Mapping[str, str]],
    baseline_identity: Mapping[str, tuple[Mapping[str, str], ...]],
    active_identity: Mapping[str, tuple[Mapping[str, str], ...]] | None,
    mode_plot_paths: Mapping[str, Path],
    mode_aligned_plot_paths: Mapping[str, Path],
    gaussian15_modes_by_family: Mapping[
        str,
        Sequence[ms1_peak_modes.Gaussian15PeakModeWindow],
    ],
) -> list[dict[str, str]]:
    samples_by_family: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in sample_rows:
        samples_by_family[row["feature_family_id"]].append(row)
    rows: list[dict[str, str]] = []
    for item in trace_data:
        family_id = item.family_id
        family_sample_rows = samples_by_family.get(family_id, [])
        baseline_rows = baseline_identity.get(family_id, ())
        active_rows = (
            active_identity.get(family_id, ())
            if active_identity is not None
            else ()
        )
        gaussian15_modes = gaussian15_modes_by_family.get(family_id, ())
        changed_row = changed_by_family.get(family_id, {})
        rows.append(
            {
                "rank": text_value(item.overlay_row.get("rank")),
                "feature_family_id": family_id,
                "baseline_peak_hypothesis_ids": _identity_peak_ids(baseline_rows),
                "active_peak_hypothesis_ids": _identity_peak_ids(active_rows),
                "active_identity_status": _active_identity_status(
                    baseline_rows=baseline_rows,
                    active_rows=active_rows,
                    active_identity_supplied=active_identity is not None,
                ),
                "baseline_row_identity_basis": _identity_basis_text(baseline_rows),
                "active_row_identity_basis": _identity_basis_text(active_rows),
                "source_feature_family_ids": _source_family_text(baseline_rows)
                or family_id,
                "family_verdict": text_value(item.overlay_row.get("family_verdict")),
                "family_mode_count": _dominant_text(
                    row.get("family_mode_count") for row in family_sample_rows
                ),
                "rt_mode_status_counts": _counts_text(
                    row.get("rt_mode_status") for row in family_sample_rows
                ),
                "peak_hypothesis_status_counts": _counts_text(
                    row.get("peak_hypothesis_status") for row in family_sample_rows
                ),
                "selected_mode_counts": _counts_text(
                    row.get("selected_mode_id") for row in family_sample_rows
                ),
                "global_trace_mode_counts": _counts_text(
                    row.get("global_trace_mode_id") for row in family_sample_rows
                ),
                "alignment_mode_counts": _counts_text(
                    row.get("alignment_mode_id") for row in family_sample_rows
                ),
                "mode_review_basis": _dominant_text(
                    row.get("mode_review_basis") for row in family_sample_rows
                ),
                "gaussian15_trace_mode_counts": _counts_text(
                    mode.mode_id for mode in gaussian15_modes
                ),
                "gaussian15_trace_mode_windows": _gaussian15_mode_windows_text(
                    gaussian15_modes,
                ),
                "mode_review_verdict": _family_mode_verdict(family_sample_rows),
                "mode_review_warning": _family_mode_warning(
                    family_sample_rows=family_sample_rows,
                    baseline_rows=baseline_rows,
                ),
                "changed_row_reason": text_value(changed_row.get("reason")),
                "presence_impact": text_value(changed_row.get("presence_impact")),
                "evidence_tier": text_value(changed_row.get("evidence_tier")),
                "reviewer_verdict": text_value(changed_row.get("reviewer_verdict")),
                "trace_data_json": str(item.path),
                "original_png_path": _resolve_optional_artifact(
                    item.overlay_row.get("png_path"),
                    base_dir=item.path.parent,
                ),
                "original_pdf_path": _resolve_optional_artifact(
                    item.overlay_row.get("pdf_path"),
                    base_dir=item.path.parent,
                ),
                "mode_plot_png_path": str(mode_plot_paths.get(family_id, "")),
                "mode_aligned_plot_png_path": str(
                    mode_aligned_plot_paths.get(family_id, ""),
                ),
            }
        )
    return rows


def _identity_by_family(
    path: Path | None,
) -> dict[str, tuple[Mapping[str, str], ...]] | None:
    if path is None:
        return None
    rows = read_tsv_required(path, IDENTITY_REQUIRED_COLUMNS)
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        families = _split_identity_list(row.get("source_feature_family_ids"))
        peak_hypothesis_id = text_value(row.get("peak_hypothesis_id"))
        if not families and peak_hypothesis_id.startswith("FAM"):
            families = (peak_hypothesis_id.split("::", 1)[0],)
        for family_id in families:
            grouped[family_id].append(row)
    return {family_id: tuple(rows) for family_id, rows in grouped.items()}


def _rows_by_key(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    return {
        (row["feature_family_id"], row["sample_stem"]): row
        for row in rows
        if row.get("feature_family_id") and row.get("sample_stem")
    }


def _optional_rows_by_key(
    path: Path | None,
    required_columns: Sequence[str],
) -> dict[tuple[str, str], Mapping[str, str]]:
    if path is None:
        return {}
    return _rows_by_key(read_tsv_required(path, required_columns))


def _similarity_review_rows(
    *,
    trace_data: Sequence[TraceData],
    sample_rows: Sequence[Mapping[str, str]],
    matrix_rt_drift_rows: Mapping[tuple[str, str], Mapping[str, str]],
    ms1_pattern_rows: Mapping[tuple[str, str], Mapping[str, str]],
) -> list[dict[str, str]]:
    shape_by_key = _gaussian15_shape_similarity_by_key(
        trace_data=trace_data,
        sample_rows=sample_rows,
    )
    rows: list[dict[str, str]] = []
    for sample_row in sample_rows:
        family_id = sample_row["feature_family_id"]
        sample_stem = sample_row["sample_stem"]
        key = (family_id, sample_stem)
        drift_row = matrix_rt_drift_rows.get(key, {})
        ms1_row = ms1_pattern_rows.get(key, {})
        shape_similarity = shape_by_key.get(key)
        global_apex_delta_sec = _minutes_to_seconds(
            optional_float(sample_row.get("trace_apex_delta_min")),
        )
        shape_status = _shape_similarity_status(shape_similarity)
        global_status = _global_apex_status(global_apex_delta_sec)
        quick_score = _quick_review_score(
            shape_similarity=shape_similarity,
            global_apex_status=global_status,
            drift_row=drift_row,
            ms1_row=ms1_row,
        )
        badge, reasons = _quick_review_badge(
            shape_status=shape_status,
            global_apex_status=global_status,
            drift_row=drift_row,
            ms1_row=ms1_row,
            mode_review_warning=sample_row.get("mode_review_warning", ""),
        )
        rows.append(
            {
                "rank": sample_row.get("rank", ""),
                "feature_family_id": family_id,
                "sample_stem": sample_stem,
                "peak_hypothesis_id": sample_row.get("peak_hypothesis_id", ""),
                "selected_mode_id": sample_row.get("selected_mode_id", ""),
                "signal_rendering_source": (
                    "Gaussian15-smoothed apex-aligned MS1 trace"
                ),
                "gaussian15_shape_similarity_to_mode": _float_text(
                    shape_similarity,
                ),
                "shape_similarity_status": shape_status,
                "global_apex_delta_sec": _float_text(global_apex_delta_sec),
                "global_apex_status": global_status,
                "matrix_rt_drift_status": drift_row.get(
                    "matrix_rt_drift_status",
                    "not_available",
                ),
                "drift_corrected_rt_delta_sec": _float_text(
                    drift_row.get("drift_corrected_delta_sec"),
                ),
                "drift_compatible_status": drift_row.get(
                    "drift_compatible_status",
                    "not_available",
                ),
                "ms1_pattern_status": ms1_row.get(
                    "ms1_pattern_status",
                    "not_available",
                ),
                "ms1_shape_correlation_score": _float_text(
                    ms1_row.get("shape_correlation_score"),
                ),
                "local_interference_score": _float_text(
                    ms1_row.get("local_interference_score"),
                ),
                "quick_review_score": _float_text(quick_score),
                "quick_review_badge": badge,
                "quick_review_reasons": ";".join(reasons),
                "diagnostic_only": "TRUE",
            }
        )
    return rows


def _similarity_family_summary_rows(
    similarity_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    rows_by_family: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in similarity_rows:
        rows_by_family[row["feature_family_id"]].append(row)
    summaries: list[dict[str, str]] = []
    for family_id in sorted(rows_by_family):
        rows = rows_by_family[family_id]
        summaries.append(
            {
                "rank": rows[0].get("rank", ""),
                "feature_family_id": family_id,
                "similarity_row_count": str(len(rows)),
                "quick_review_badge_counts": _counts_text(
                    row.get("quick_review_badge") for row in rows
                ),
                "shape_similarity_status_counts": _counts_text(
                    row.get("shape_similarity_status") for row in rows
                ),
                "global_apex_status_counts": _counts_text(
                    row.get("global_apex_status") for row in rows
                ),
                "matrix_rt_drift_status_counts": _counts_text(
                    row.get("matrix_rt_drift_status") for row in rows
                ),
                "median_gaussian15_shape_similarity_to_mode": _float_text(
                    _median_float(
                        row.get("gaussian15_shape_similarity_to_mode")
                        for row in rows
                    ),
                ),
                "median_quick_review_score": _float_text(
                    _median_float(row.get("quick_review_score") for row in rows),
                ),
                "diagnostic_only": "TRUE",
            }
        )
    return sorted(
        summaries,
        key=lambda row: (
            (
                _safe_int(row.get("rank"))
                if _safe_int(row.get("rank")) is not None
                else 10**9
            ),
            row.get("feature_family_id", ""),
        ),
    )


def _gaussian15_shape_similarity_by_key(
    *,
    trace_data: Sequence[TraceData],
    sample_rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], float | None]:
    sample_rows_by_key = {
        (row["feature_family_id"], row["sample_stem"]): row for row in sample_rows
    }
    grouped_vectors: dict[
        tuple[str, str],
        dict[tuple[str, str], list[float]],
    ] = defaultdict(dict)
    for item in trace_data:
        for trace in item.traces:
            sample_stem = text_value(trace.get("sample_stem"))
            if not sample_stem:
                continue
            key = (item.family_id, sample_stem)
            sample_row = sample_rows_by_key.get(key)
            if sample_row is None:
                continue
            mode_id = text_value(sample_row.get("selected_mode_id")) or "unassigned"
            vector = _gaussian15_apex_aligned_vector(trace)
            if vector:
                grouped_vectors[(item.family_id, mode_id)][key] = vector

    similarities: dict[tuple[str, str], float | None] = {}
    for vectors_by_key in grouped_vectors.values():
        for key, vector in vectors_by_key.items():
            reference_vectors = [
                other
                for other_key, other in vectors_by_key.items()
                if other_key != key
            ]
            if not reference_vectors:
                similarities[key] = None
                continue
            reference = _median_vector(reference_vectors)
            similarities[key] = _pearson(vector, reference)
    return similarities


def _gaussian15_apex_aligned_vector(trace: Mapping[str, Any]) -> list[float]:
    import numpy as np

    apex_rt = optional_float(trace.get("cell_apex_rt")) or optional_float(
        trace.get("trace_apex_rt"),
    )
    if apex_rt is None:
        return []
    rt = np.asarray(_float_list(trace.get("rt")), dtype=float)
    intensity = np.asarray(_float_list(trace.get("intensity")), dtype=float)
    limit = min(rt.size, intensity.size)
    if limit < 3:
        return []
    rt = rt[:limit] - apex_rt
    intensity = _gaussian_smooth_values(
        intensity[:limit],
        points=PLOT_GAUSSIAN_SMOOTH_POINTS,
    )
    mask = (
        np.isfinite(rt)
        & np.isfinite(intensity)
        & (rt >= -APEX_ALIGN_HALF_WINDOW_MIN)
        & (rt <= APEX_ALIGN_HALF_WINDOW_MIN)
    )
    if not np.any(mask):
        return []
    local_rt = rt[mask]
    local_intensity = intensity[mask]
    local_max = float(np.max(local_intensity)) if local_intensity.size else 0.0
    if local_max <= 0:
        return []
    grid = np.linspace(
        -APEX_ALIGN_HALF_WINDOW_MIN,
        APEX_ALIGN_HALF_WINDOW_MIN,
        APEX_ALIGN_GRID_SIZE,
    )
    vector = np.interp(
        grid,
        local_rt,
        local_intensity / local_max,
        left=np.nan,
        right=np.nan,
    )
    return [float(value) for value in vector]


def _median_vector(vectors: Sequence[Sequence[float]]) -> list[float]:
    import numpy as np

    stack = np.asarray(vectors, dtype=float)
    finite_columns = np.isfinite(stack).any(axis=0)
    if not np.any(finite_columns):
        return []
    median = np.full(stack.shape[1], np.nan, dtype=float)
    median[finite_columns] = np.nanmedian(stack[:, finite_columns], axis=0)
    return [float(value) for value in median]


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    import numpy as np

    if not left or not right:
        return None
    limit = min(len(left), len(right))
    left_array = np.asarray(left[:limit], dtype=float)
    right_array = np.asarray(right[:limit], dtype=float)
    mask = np.isfinite(left_array) & np.isfinite(right_array)
    if int(np.sum(mask)) < 5:
        return None
    x = left_array[mask]
    y = right_array[mask]
    if float(np.std(x)) <= 1e-12 or float(np.std(y)) <= 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _shape_similarity_status(value: float | None) -> str:
    if value is None:
        return "unavailable"
    if value >= SHAPE_STRONG_MIN:
        return "strong"
    if value >= SHAPE_SUPPORT_MIN:
        return "supportive"
    return "conflict"


def _global_apex_status(delta_sec: float | None) -> str:
    if delta_sec is None:
        return "unavailable"
    abs_delta_min = abs(delta_sec) / 60.0
    if abs_delta_min <= LOCAL_APEX_SUPPORT_DELTA_MIN:
        return "aligned"
    if abs_delta_min <= GLOBAL_APEX_CONFLICT_DELTA_MIN:
        return "nearby"
    return "conflict"


def _quick_review_score(
    *,
    shape_similarity: float | None,
    global_apex_status: str,
    drift_row: Mapping[str, str],
    ms1_row: Mapping[str, str],
) -> float:
    shape_component = max(0.0, min(1.0, shape_similarity or 0.0)) * 70.0
    apex_component = {
        "aligned": 20.0,
        "nearby": 10.0,
        "unavailable": 8.0,
        "conflict": 0.0,
    }.get(global_apex_status, 0.0)
    drift_component = _drift_score_component(drift_row)
    ms1_status = text_value(ms1_row.get("ms1_pattern_status"))
    if ms1_status == "conflict":
        shape_component *= 0.75
    return shape_component + apex_component + drift_component


def _drift_score_component(row: Mapping[str, str]) -> float:
    status = text_value(row.get("matrix_rt_drift_status"))
    compatible = text_value(row.get("drift_compatible_status"))
    if status in {"rt_close", "drift_supported"} and compatible != "conflict":
        return 10.0
    if status in {"drift_not_supported"} or compatible == "conflict":
        return 0.0
    return 5.0


def _quick_review_badge(
    *,
    shape_status: str,
    global_apex_status: str,
    drift_row: Mapping[str, str],
    ms1_row: Mapping[str, str],
    mode_review_warning: object,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    drift_status = text_value(drift_row.get("matrix_rt_drift_status"))
    drift_compatible = text_value(drift_row.get("drift_compatible_status"))
    ms1_status = text_value(ms1_row.get("ms1_pattern_status"))
    warning = text_value(mode_review_warning)
    if global_apex_status == "conflict":
        reasons.append("global_trace_apex_far_from_selected_cell")
        return "review_required_wrong_apex_risk", tuple(reasons)
    if shape_status == "conflict":
        reasons.append("gaussian15_shape_similarity_below_support_threshold")
        return "review_required_shape_conflict", tuple(reasons)
    if drift_status == "drift_not_supported" or drift_compatible == "conflict":
        reasons.append("matrix_rt_drift_not_supportive")
        return "review_required_rt_drift_conflict", tuple(reasons)
    if ms1_status == "conflict":
        reasons.append("ms1_pattern_sidecar_conflict")
        return "review_required_ms1_pattern_conflict", tuple(reasons)
    if "global_trace_apex_multimodal" in warning:
        reasons.append("family_global_trace_apex_multimodal")
        return "review_required_multimodal_family", tuple(reasons)
    if shape_status == "strong" and global_apex_status in {"aligned", "nearby"}:
        reasons.append("gaussian15_shape_and_apex_coherent")
        return "shape_coherent_review_only", tuple(reasons)
    if shape_status == "supportive":
        reasons.append("gaussian15_shape_partial_support")
        return "review_required_partial_similarity", tuple(reasons)
    reasons.append("similarity_evidence_inconclusive")
    return "review_required_inconclusive_similarity", tuple(reasons)


def _global_trace_mode_ids(
    traces: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    values = {
        text_value(trace.get("sample_stem")): optional_float(trace.get("trace_apex_rt"))
        for trace in traces
        if text_value(trace.get("sample_stem"))
    }
    return _cluster_modes(values, prefix="global_trace_mode")


def _gaussian15_trace_mode_windows(
    trace_data: TraceData,
) -> tuple[ms1_peak_modes.Gaussian15PeakModeWindow, ...]:
    return ms1_peak_modes.infer_gaussian15_peak_mode_windows(
        trace_data.traces,
        rt_min=optional_float(trace_data.payload.get("rt_min")),
        rt_max=optional_float(trace_data.payload.get("rt_max")),
    )


def _gaussian15_trace_mode_ids(
    *,
    trace: Mapping[str, Any],
    gaussian15_modes: Sequence[ms1_peak_modes.Gaussian15PeakModeWindow],
) -> str:
    mode_ids = [
        mode.mode_id
        for mode in gaussian15_modes
        if ms1_peak_modes.trace_has_gaussian15_peak_in_window(
            trace,
            start_rt=mode.start_rt,
            end_rt=mode.end_rt,
        )
    ]
    return ";".join(mode_ids)


def _family_gaussian15_trace_modes(rows: Sequence[Mapping[str, str]]) -> set[str]:
    return {
        mode_id
        for row in rows
        for mode_id in _split_semicolon_values(row.get("gaussian15_trace_mode_ids"))
    }


def _gaussian15_mode_windows_text(
    modes: Sequence[ms1_peak_modes.Gaussian15PeakModeWindow],
) -> str:
    return ";".join(
        (
            f"{mode.mode_id}="
            f"{mode.start_rt:.4f}-{mode.end_rt:.4f}"
            f"|peaks={mode.trace_peak_count}"
            f"|detected={mode.detected_seed_count}"
        )
        for mode in modes
    )


def _alignment_mode_assignments(
    *,
    family_id: str,
    traces: Sequence[Mapping[str, Any]],
    alignment_cell_rows: Mapping[tuple[str, str], Mapping[str, str]],
    matrix_rt_drift_rows: Mapping[tuple[str, str], Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    details: dict[str, dict[str, str]] = {}
    cluster_values: dict[str, float | None] = {}
    for trace in traces:
        sample = text_value(trace.get("sample_stem"))
        if not sample:
            continue
        key = (family_id, sample)
        detail = _alignment_mode_detail(
            trace=trace,
            alignment_cell=alignment_cell_rows.get(key, {}),
            drift_row=matrix_rt_drift_rows.get(key, {}),
        )
        details[sample] = detail
        delta_sec = _numeric_float(detail.get("alignment_apex_delta_sec"))
        if delta_sec is not None and detail.get("alignment_mode_status") in {
            "alignment_cell_supported",
            "drift_supported",
            "rt_close",
        }:
            cluster_values[sample] = delta_sec / 60.0
    mode_ids = _alignment_delta_mode_ids(cluster_values)
    for sample, mode_id in mode_ids.items():
        details.setdefault(sample, {})["alignment_mode_id"] = mode_id
    for sample, detail in details.items():
        detail.setdefault("alignment_mode_id", "")
        if not detail["alignment_mode_id"] and detail.get("alignment_mode_status"):
            detail["alignment_mode_id"] = "alignment_unassigned"
    return details


def _alignment_delta_mode_ids(
    values: Mapping[str, float | None],
) -> dict[str, str]:
    finite = {
        sample: delta_min
        for sample, delta_min in values.items()
        if delta_min is not None
    }
    if (
        finite
        and max(abs(delta_min) * 60.0 for delta_min in finite.values())
        <= ALIGNMENT_CENTER_MODE_DELTA_SEC
    ):
        return {sample: "alignment_mode_1" for sample in finite}
    return _cluster_modes(finite, prefix="alignment_mode")


def _alignment_mode_detail(
    *,
    trace: Mapping[str, Any],
    alignment_cell: Mapping[str, str],
    drift_row: Mapping[str, str],
) -> dict[str, str]:
    drift_status = text_value(drift_row.get("matrix_rt_drift_status"))
    drift_compatible = text_value(drift_row.get("drift_compatible_status"))
    signed_delta = _signed_alignment_delta_sec(alignment_cell, trace)
    if (
        drift_status in {"rt_close", "drift_supported"}
        and drift_compatible != "conflict"
    ):
        corrected_delta = _numeric_float(drift_row.get("drift_corrected_delta_sec"))
        if corrected_delta is not None:
            sign = _delta_sign(signed_delta)
            return {
                "alignment_mode_source": "matrix_rt_drift_policy",
                "alignment_apex_delta_sec": _float_text(sign * abs(corrected_delta)),
                "alignment_mode_status": drift_status,
            }
    if drift_status == "drift_not_supported" or drift_compatible == "conflict":
        return {
            "alignment_mode_source": "matrix_rt_drift_policy",
            "alignment_apex_delta_sec": "",
            "alignment_mode_status": "drift_conflict",
        }
    if signed_delta is not None:
        return {
            "alignment_mode_source": "alignment_cell_delta",
            "alignment_apex_delta_sec": _float_text(signed_delta),
            "alignment_mode_status": "alignment_cell_supported",
        }
    if drift_status:
        return {
            "alignment_mode_source": "matrix_rt_drift_policy",
            "alignment_apex_delta_sec": "",
            "alignment_mode_status": "drift_inconclusive",
        }
    return {
        "alignment_mode_source": "raw_overlay_only",
        "alignment_apex_delta_sec": "",
        "alignment_mode_status": "not_available",
    }


def _signed_alignment_delta_sec(
    alignment_cell: Mapping[str, str],
    trace: Mapping[str, Any],
) -> float | None:
    cell_delta = _numeric_float(alignment_cell.get("rt_delta_sec"))
    if cell_delta is not None:
        return cell_delta
    apex_rt = _numeric_float(alignment_cell.get("apex_rt"))
    center_rt = _numeric_float(trace.get("family_center_rt"))
    if apex_rt is not None and center_rt is not None:
        return (apex_rt - center_rt) * 60.0
    return None


def _delta_sign(value: float | None) -> float:
    if value is None or value >= 0:
        return 1.0
    return -1.0


def _cluster_modes(
    values: Mapping[str, float | None],
    *,
    prefix: str,
) -> dict[str, str]:
    indexed = tuple(
        (sample, value) for sample, value in values.items() if value is not None
    )
    mode_ids = rt_mode_evidence.cluster_raw_overlay_rt_modes(
        indexed,
        prefix=prefix,
        outlier_mode_id=f"{prefix}_outlier",
        min_cluster_size=MIN_MODE_CLUSTER_SIZE,
    )
    return {str(sample): mode_id for sample, mode_id in mode_ids.items()}


def _family_mode_verdict(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return "mode_evidence_missing"
    statuses = {text_value(row.get("rt_mode_status")) for row in rows}
    hypothesis_statuses = {
        text_value(row.get("peak_hypothesis_status")) for row in rows
    }
    family_mode_count = _max_int_field(rows, "family_mode_count")
    global_modes = {
        text_value(row.get("global_trace_mode_id"))
        for row in rows
        if text_value(row.get("global_trace_mode_id"))
    }
    alignment_modes = {
        text_value(row.get("alignment_mode_id"))
        for row in rows
        if _alignment_row_is_supported(row)
        and text_value(row.get("alignment_mode_id"))
        and text_value(row.get("alignment_mode_id")) != "alignment_unassigned"
    }
    alignment_supported_count = sum(
        1 for row in rows if _alignment_row_is_supported(row)
    )
    gaussian15_modes = _family_gaussian15_trace_modes(rows)
    if len(gaussian15_modes) > 1:
        return "review_required_gaussian15_trace_multipeak"
    if alignment_supported_count == len(rows) and len(alignment_modes) == 1:
        return "single_mode_supported_alignment_review_only"
    if statuses & {"mode_conflict", "consolidation_no_go", "mode_split_required"}:
        return "block_or_split_required"
    if (
        "raw_mode_review_only" in statuses
        or "raw_mode_review_only" in hypothesis_statuses
    ):
        if family_mode_count > 1 or len(global_modes) > 1:
            return "review_required_raw_multimodal_family"
        if statuses == {"mode_supported"}:
            return "single_mode_supported_raw_review_only"
        return "review_required_raw_mode"
    if family_mode_count > 1 or len(global_modes) > 1:
        return "review_required_multimodal_family"
    if statuses == {"mode_supported"}:
        return "single_mode_supported"
    return "review_required_inconclusive_mode"


def _sample_mode_warning(
    *,
    rt_row: Mapping[str, str],
    global_mode_id: str,
    global_mode_count: int,
    alignment_mode_id: str,
    alignment_mode_count: int,
    mode_basis: str,
    gaussian15_trace_mode_ids: str,
) -> str:
    warnings = []
    if len(_split_semicolon_values(gaussian15_trace_mode_ids)) > 1:
        warnings.append("gaussian15_trace_multipeak")
    if text_value(rt_row.get("rt_mode_evidence_level")) == "raw_selected_apex_modes":
        warnings.append("raw_overlay_mode_review_only")
    if text_value(rt_row.get("rt_mode_status")) in {
        "raw_mode_review_only",
        "mode_conflict",
        "consolidation_no_go",
        "mode_split_required",
    }:
        warnings.append(text_value(rt_row.get("rt_mode_status")))
    if (
        global_mode_count > 1
        and global_mode_id
        and not (
            alignment_mode_count == 1
            and alignment_mode_id
            and mode_basis in {"alignment_cell_delta", "matrix_rt_drift_policy"}
        )
    ):
        warnings.append("global_trace_apex_multimodal")
    if (
        global_mode_count > 1
        and alignment_mode_count == 1
        and alignment_mode_id
        and mode_basis in {"alignment_cell_delta", "matrix_rt_drift_policy"}
    ):
        warnings.append("raw_multimodal_but_alignment_single")
    if mode_basis == "raw_overlay":
        warnings.append("alignment_not_supplied_raw_only")
    return ";".join(dict.fromkeys(warnings))


def _family_mode_warning(
    *,
    family_sample_rows: Sequence[Mapping[str, str]],
    baseline_rows: Sequence[Mapping[str, str]],
) -> str:
    warnings = []
    if any(
        row.get("row_identity_basis") == "no_split_peak_hypothesis"
        for row in baseline_rows
    ):
        mode_count = _max_int_field(family_sample_rows, "family_mode_count")
        if mode_count > 1:
            warnings.append("baseline_no_split_but_selected_apex_multimodal")
    global_modes = {
        text_value(row.get("global_trace_mode_id"))
        for row in family_sample_rows
        if text_value(row.get("global_trace_mode_id"))
    }
    alignment_modes = {
        text_value(row.get("alignment_mode_id"))
        for row in family_sample_rows
        if _alignment_row_is_supported(row)
        and text_value(row.get("alignment_mode_id"))
        and text_value(row.get("alignment_mode_id")) != "alignment_unassigned"
    }
    alignment_supported_count = sum(
        1 for row in family_sample_rows if _alignment_row_is_supported(row)
    )
    if (
        len(global_modes) > 1
        and alignment_supported_count == len(family_sample_rows)
        and len(alignment_modes) == 1
    ):
        warnings.append("raw_multimodal_but_alignment_single")
    elif len(global_modes) > 1:
        warnings.append("global_trace_apex_multimodal")
    if any(
        text_value(row.get("rt_mode_evidence_level")) == "raw_selected_apex_modes"
        for row in family_sample_rows
    ):
        warnings.append("raw_overlay_mode_is_review_only_not_irt")
    if alignment_supported_count == 0:
        warnings.append("alignment_not_supplied_raw_only")
    if len(_family_gaussian15_trace_modes(family_sample_rows)) > 1:
        warnings.append("gaussian15_trace_multipeak")
    return ";".join(warnings)


def _display_mode_id(
    *,
    alignment_row: Mapping[str, str],
    raw_mode_id: str,
) -> str:
    alignment_mode = text_value(alignment_row.get("alignment_mode_id"))
    if (
        alignment_mode
        and alignment_mode != "alignment_unassigned"
        and _alignment_status_is_supported(
            text_value(alignment_row.get("alignment_mode_status"))
        )
    ):
        return alignment_mode
    return raw_mode_id


def _display_mode_from_row(row: Mapping[str, str]) -> str:
    return text_value(row.get("display_mode_id")) or "unassigned"


def _mode_review_basis(alignment_row: Mapping[str, str]) -> str:
    if not _alignment_status_is_supported(
        text_value(alignment_row.get("alignment_mode_status"))
    ):
        return "raw_overlay"
    source = text_value(alignment_row.get("alignment_mode_source"))
    if source in {"alignment_cell_delta", "matrix_rt_drift_policy"}:
        return source
    return "raw_overlay"


def _alignment_mode_count(rows: Mapping[str, Mapping[str, str]]) -> int:
    modes = {
        text_value(row.get("alignment_mode_id"))
        for row in rows.values()
        if _alignment_status_is_supported(text_value(row.get("alignment_mode_status")))
        and text_value(row.get("alignment_mode_id"))
        and text_value(row.get("alignment_mode_id")) != "alignment_unassigned"
    }
    return len(modes)


def _alignment_row_is_supported(row: Mapping[str, str]) -> bool:
    return _alignment_status_is_supported(text_value(row.get("alignment_mode_status")))


def _alignment_status_is_supported(status: str) -> bool:
    return status in {"alignment_cell_supported", "drift_supported", "rt_close"}


def _active_identity_status(
    *,
    baseline_rows: Sequence[Mapping[str, str]],
    active_rows: Sequence[Mapping[str, str]],
    active_identity_supplied: bool,
) -> str:
    if not active_identity_supplied:
        return "active_identity_not_supplied"
    if baseline_rows and not active_rows:
        return "removed_by_active_gate"
    if active_rows:
        return "present_after_active_gate"
    return "identity_absent_before_and_after"


def _render_mode_plot(
    *,
    trace_data: TraceData,
    sample_rows: Sequence[Mapping[str, str]],
    gaussian15_modes: Sequence[ms1_peak_modes.Gaussian15PeakModeWindow],
    output_dir: Path,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_sample = {row["sample_stem"]: row for row in sample_rows}
    png_path = output_dir / f"{trace_data.family_id.lower()}_mode_overlay.png"
    modes = sorted(
        {
            text_value(row.get("display_mode_id")) or "unassigned"
            for row in sample_rows
        }
    )
    mode_basis = _dominant_text(row.get("mode_review_basis") for row in sample_rows)
    colors = _mode_colors(modes)
    fig, (ax_trace, ax_apex) = plt.subplots(
        2,
        1,
        figsize=(12, 7),
        gridspec_kw={"height_ratios": [2.2, 1.0]},
        constrained_layout=True,
    )
    for trace in trace_data.traces:
        sample = text_value(trace.get("sample_stem"))
        row = by_sample.get(sample, {})
        rt = _float_list(trace.get("rt"))
        intensity = _float_list(trace.get("intensity"))
        if not rt or not intensity:
            continue
        limit = min(len(rt), len(intensity))
        plot_intensity = _smoothed_plot_intensity(intensity[:limit])
        color = colors.get(_display_mode_from_row(row), "#666666")
        ax_trace.plot(
            rt[:limit],
            plot_intensity,
            color=color,
            linewidth=1.2,
            alpha=0.72,
        )
        selected_rt = optional_float(trace.get("cell_apex_rt"))
        selected_height = optional_float(trace.get("cell_height"))
        if selected_rt is not None and selected_height is not None:
            ax_trace.scatter(
                [selected_rt],
                [selected_height],
                color=color,
                edgecolor="black",
                linewidth=0.4,
                s=20,
                zorder=3,
            )
    family_center = optional_float(trace_data.payload.get("family_center_rt"))
    rt_min = optional_float(trace_data.payload.get("rt_min"))
    rt_max = optional_float(trace_data.payload.get("rt_max"))
    if rt_min is not None and rt_max is not None:
        ax_trace.axvspan(rt_min, rt_max, color="#eeeeee", alpha=0.35)
    if family_center is not None:
        ax_trace.axvline(
            family_center,
            color="black",
            linestyle="--",
            linewidth=1.0,
            alpha=0.75,
        )
    mode_span_colors = _mode_colors([mode.mode_id for mode in gaussian15_modes])
    for mode in gaussian15_modes:
        ax_trace.axvspan(
            mode.start_rt,
            mode.end_rt,
            color=mode_span_colors.get(mode.mode_id, "#bbbbbb"),
            alpha=0.12,
        )
        ax_trace.text(
            mode.apex_rt,
            0.98,
            mode.mode_id,
            transform=ax_trace.get_xaxis_transform(),
            rotation=90,
            va="top",
            ha="center",
            fontsize=7,
            color=mode_span_colors.get(mode.mode_id, "#555555"),
        )
    ax_trace.set_title(
        f"{trace_data.family_id} mode-colored MS1 overlay "
        f"({len(sample_rows)} cells; basis={mode_basis or 'raw_overlay'})",
    )
    ax_trace.set_xlabel("Retention time (min)")
    ax_trace.set_ylabel("Intensity")
    handles = [
        plt.Line2D([0], [0], color=colors[mode], lw=2, label=mode)
        for mode in modes
    ]
    if handles:
        ax_trace.legend(handles=handles, loc="upper right", fontsize=8)

    ordered = sorted(
        sample_rows,
        key=lambda row: (
            optional_float(row.get("cell_apex_rt")) is None,
            optional_float(row.get("cell_apex_rt")) or 0.0,
            row.get("sample_stem", ""),
        ),
    )
    y_positions = list(range(len(ordered)))
    for y_pos, row in zip(y_positions, ordered, strict=True):
        mode_id = _display_mode_from_row(row)
        color = colors.get(mode_id, "#666666")
        selected_rt = optional_float(row.get("cell_apex_rt"))
        trace_rt = optional_float(row.get("trace_apex_rt"))
        if selected_rt is not None and trace_rt is not None:
            ax_apex.plot([selected_rt, trace_rt], [y_pos, y_pos], color="#999999")
        if selected_rt is not None:
            ax_apex.scatter([selected_rt], [y_pos], color=color, marker="o", s=28)
        if trace_rt is not None:
            ax_apex.scatter(
                [trace_rt],
                [y_pos],
                color=color,
                marker="x",
                s=36,
            )
    ax_apex.set_yticks(y_positions)
    ax_apex.set_yticklabels([row["sample_stem"] for row in ordered], fontsize=7)
    ax_apex.set_xlabel(
        "Apex RT (circle=selected cell, x=global trace apex; color=display mode)"
    )
    ax_apex.set_ylabel("Sample")
    ax_apex.grid(axis="x", alpha=0.2)
    fig.savefig(png_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path


def _plot_alignment_rt(
    *,
    trace: Mapping[str, Any],
    mode_id: str,
    gaussian15_modes: Sequence[ms1_peak_modes.Gaussian15PeakModeWindow],
) -> float | None:
    mode = next((item for item in gaussian15_modes if item.mode_id == mode_id), None)
    if mode is None:
        return optional_float(trace.get("cell_apex_rt"))
    peaks = [
        peak
        for peak in ms1_peak_modes.gaussian15_peak_observations(trace)
        if mode.start_rt <= peak.apex_rt <= mode.end_rt
    ]
    if not peaks:
        return None
    return max(peaks, key=lambda peak: peak.height).apex_rt


def _render_mode_aligned_plot(
    *,
    trace_data: TraceData,
    sample_rows: Sequence[Mapping[str, str]],
    gaussian15_modes: Sequence[ms1_peak_modes.Gaussian15PeakModeWindow],
    output_dir: Path,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    by_sample = {row["sample_stem"]: row for row in sample_rows}
    png_path = output_dir / f"{trace_data.family_id.lower()}_mode_aligned_overlay.png"
    mode_ids = [mode.mode_id for mode in gaussian15_modes]
    rows_by_mode: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    if gaussian15_modes:
        for row in sample_rows:
            row_modes = _split_semicolon_values(row.get("gaussian15_trace_mode_ids"))
            for mode_id in row_modes:
                rows_by_mode[mode_id].append(row)
    else:
        for row in sample_rows:
            rows_by_mode[_display_mode_from_row(row)].append(row)
        mode_ids = sorted(rows_by_mode) or ["unassigned"]
    modes = tuple(mode_ids)
    fig_height = max(3.6, 2.6 * len(modes))
    fig, axes = plt.subplots(
        len(modes),
        1,
        figsize=(12, fig_height),
        squeeze=False,
        constrained_layout=True,
    )
    for axis_row, mode_id in zip(axes, modes, strict=True):
        ax = axis_row[0]
        mode_rows = rows_by_mode.get(mode_id, [])
        mode_samples = {row["sample_stem"] for row in mode_rows}
        detected_count = 0
        plotted_count = 0
        for trace in trace_data.traces:
            sample = text_value(trace.get("sample_stem"))
            if sample not in mode_samples:
                continue
            selected_rt = _plot_alignment_rt(
                trace=trace,
                mode_id=mode_id,
                gaussian15_modes=gaussian15_modes,
            )
            rt = _float_list(trace.get("rt"))
            intensity = _float_list(trace.get("intensity"))
            if selected_rt is None or not rt or not intensity:
                continue
            limit = min(len(rt), len(intensity))
            if limit < 2:
                continue
            smoothed = np.asarray(
                _smoothed_plot_intensity(intensity[:limit]),
                dtype=float,
            )
            max_intensity = float(np.max(smoothed)) if smoothed.size else 0.0
            if max_intensity <= 0:
                continue
            relative_rt = np.asarray(rt[:limit], dtype=float) - selected_rt
            row = by_sample.get(sample, {})
            is_detected = text_value(row.get("cell_status")) == "detected"
            detected_count += 1 if is_detected else 0
            color = "#005f73" if is_detected else "#c75b12"
            alpha = 0.86 if is_detected else 0.52
            line_width = 1.5 if is_detected else 1.0
            ax.plot(
                relative_rt,
                smoothed / max_intensity,
                color=color,
                alpha=alpha,
                lw=line_width,
            )
            plotted_count += 1
        ax.axvline(0.0, color="black", lw=1.0, ls="--", alpha=0.65)
        ax.set_xlim(-APEX_ALIGN_HALF_WINDOW_MIN, APEX_ALIGN_HALF_WINDOW_MIN)
        ax.set_ylim(-0.03, 1.08)
        ax.set_ylabel("Scaled MS1")
        ax.grid(True, alpha=0.2)
        ax.set_title(
            f"{mode_id}: apex-aligned Gaussian15 MS1 traces "
            f"(n={plotted_count}, detected={detected_count})",
            fontsize=10,
        )
    axes[-1][0].set_xlabel("RT relative to selected apex (min)")
    fig.suptitle(
        f"{trace_data.family_id} mode-level aligned MS1 overlays",
        fontsize=12,
    )
    fig.savefig(png_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path


def _smoothed_plot_intensity(values: Sequence[float]) -> list[float]:
    import numpy as np

    if not values:
        return []
    smoothed = _gaussian_smooth_values(
        np.asarray(values, dtype=float),
        points=PLOT_GAUSSIAN_SMOOTH_POINTS,
    )
    return [float(value) for value in smoothed]


def _mode_colors(modes: Sequence[str]) -> dict[str, str]:
    palette = (
        "#1b9e77",
        "#d95f02",
        "#7570b3",
        "#e7298a",
        "#66a61e",
        "#e6ab02",
        "#a6761d",
        "#0072b2",
        "#cc79a7",
    )
    return {mode: palette[index % len(palette)] for index, mode in enumerate(modes)}


def _write_review_gallery(
    path: Path,
    *,
    family_rows: Sequence[Mapping[str, str]],
    sample_rows: Sequence[Mapping[str, str]],
    similarity_rows: Sequence[Mapping[str, str]],
    rt_mode_tsv: Path,
    peak_hypothesis_tsv: Path,
    family_summary_tsv: Path,
    sample_review_tsv: Path,
    similarity_review_tsv: Path,
    similarity_family_summary_tsv: Path,
) -> None:
    samples_by_family: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in sample_rows:
        samples_by_family[row["feature_family_id"]].append(row)
    similarity_by_family: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in similarity_rows:
        similarity_by_family[row["feature_family_id"]].append(row)
    row_blocks = [
        _family_html_block(
            row,
            sample_rows=samples_by_family.get(row["feature_family_id"], []),
            similarity_rows=similarity_by_family.get(row["feature_family_id"], []),
            html_dir=path.parent,
        )
        for row in family_rows
    ]
    body = "\n".join(row_blocks)
    links = " ".join(
        _artifact_link(label, target, html_dir=path.parent)
        for label, target in (
            ("RT mode TSV", rt_mode_tsv),
            ("PeakHypothesis TSV", peak_hypothesis_tsv),
            ("Family summary TSV", family_summary_tsv),
            ("Sample review TSV", sample_review_tsv),
            ("Similarity TSV", similarity_review_tsv),
            ("Similarity summary TSV", similarity_family_summary_tsv),
        )
    )
    path.write_text(
        "\n".join(
            [
                "<!doctype html>",
                "<html lang=\"en\">",
                "<head>",
                "<meta charset=\"utf-8\">",
                "<title>Changed-row mode-aware overlay review</title>",
                "<style>",
                _gallery_css(),
                "</style>",
                "</head>",
                "<body>",
                "<main>",
                "<h1>Changed-row mode-aware overlay review</h1>",
                (
                    "<p class=\"note\">Family ID is provenance here. The review "
                    "surface shows raw selected-apex modes plus an optional "
                    "alignment-aware display mode from alignment cells or matrix "
                    "RT drift policy. Raw overlay modes are review-only, not typed "
                    "iRT authority.</p>"
                ),
                f"<p class=\"links\">{links}</p>",
                _gallery_overview_html(similarity_rows),
                body,
                "</main>",
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )


def _family_html_block(
    row: Mapping[str, str],
    *,
    sample_rows: Sequence[Mapping[str, str]],
    similarity_rows: Sequence[Mapping[str, str]],
    html_dir: Path,
) -> str:
    family = html.escape(row["feature_family_id"])
    mode_plot = _image_html(row.get("mode_plot_png_path"), html_dir=html_dir)
    mode_aligned_plot = _image_html(
        row.get("mode_aligned_plot_png_path"),
        html_dir=html_dir,
    )
    original_plot = _image_html(row.get("original_png_path"), html_dir=html_dir)
    warning = html.escape(row.get("mode_review_warning", ""))
    sample_table = _sample_table_html(sample_rows, similarity_rows=similarity_rows)
    median_shape = _float_text(
        _median_float(
            row.get("gaussian15_shape_similarity_to_mode") for row in similarity_rows
        )
    )
    median_score = _float_text(
        _median_float(row.get("quick_review_score") for row in similarity_rows)
    )
    badge_counts = _counts_text(
        row.get("quick_review_badge") for row in similarity_rows
    )
    dominant_badge = _dominant_text(
        row.get("quick_review_badge") for row in similarity_rows
    )
    return "\n".join(
        [
            f"<article class=\"family {_risk_class(dominant_badge)}\">",
            (
                f"<h2>{html.escape(row.get('rank', ''))}. {family} "
                f"<span>{html.escape(row.get('mode_review_verdict', ''))}</span>"
                "</h2>"
            ),
            "<div class=\"badge-row\">",
            _badge_html(dominant_badge or "mixed_review_queue"),
            _badge_html(row.get("active_identity_status")),
            _badge_html(row.get("family_verdict")),
            "</div>",
            "<section class=\"score-strip\" aria-label=\"Review similarity summary\">",
            _score_card("median shape similarity", median_shape, kind="shape"),
            _score_card("median quick score", median_score, kind="score"),
            _score_card("quick review badge counts", badge_counts),
            "</section>",
            "<section class=\"plots\">",
            (
                "<figure class=\"primary-plot\">"
                "<figcaption>Mode-colored diagnostic</figcaption>"
                f"{mode_plot}</figure>"
            ),
            (
                "<figure class=\"primary-plot\">"
                "<figcaption>Mode-level aligned MS1 overlays</figcaption>"
                f"{mode_aligned_plot}</figure>"
            ),
            (
                "<figure class=\"primary-plot\">"
                "<figcaption>Original family MS1 overlay</figcaption>"
                f"{original_plot}</figure>"
            ),
            "</section>",
            "<details class=\"context-panel\" open>",
            "<summary>Sample evidence table</summary>",
            sample_table,
            "</details>",
            "<details class=\"context-panel compact-details\">",
            "<summary>Technical metadata</summary>",
            "<dl class=\"facts\">",
            _fact("baseline PeakHypothesis", row.get("baseline_peak_hypothesis_ids")),
            _fact("active identity", row.get("active_identity_status")),
            _fact("row identity basis", row.get("baseline_row_identity_basis")),
            _fact("family verdict", row.get("family_verdict")),
            _fact("mode count", row.get("family_mode_count")),
            _fact("selected modes", row.get("selected_mode_counts")),
            _fact("global apex modes", row.get("global_trace_mode_counts")),
            _fact("alignment modes", row.get("alignment_mode_counts")),
            _fact("review basis", row.get("mode_review_basis")),
            _fact("mode aligned plot", row.get("mode_aligned_plot_png_path")),
            _fact("quick review badges", badge_counts),
            _fact("warning", warning),
            "</dl>",
            "</details>",
            "</article>",
        ]
    )


def _sample_table_html(
    rows: Sequence[Mapping[str, str]],
    *,
    similarity_rows: Sequence[Mapping[str, str]],
) -> str:
    similarity_by_sample = {row["sample_stem"]: row for row in similarity_rows}
    ordered = sorted(
        rows,
        key=lambda row: (
            row.get("display_mode_id", ""),
            optional_float(row.get("cell_apex_rt")) or math.inf,
            row.get("sample_stem", ""),
        ),
    )
    headers = (
        "sample",
        "cell RT",
        "trace RT",
        "raw mode",
        "global mode",
        "display mode",
        "basis",
        "alignment delta",
        "quick badge",
        "shape similarity",
        "quick score",
        "drift status",
        "RT mode status",
        "PeakHypothesis",
        "action",
        "warning",
    )
    header_html = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body_rows = []
    for row in ordered:
        similarity = similarity_by_sample.get(row["sample_stem"], {})
        badge = similarity.get("quick_review_badge", "")
        cells = (
            _table_cell(row.get("sample_stem", ""), "sample-cell"),
            _table_cell(row.get("cell_apex_rt", "")),
            _table_cell(row.get("trace_apex_rt", "")),
            _table_cell(row.get("selected_mode_id", "")),
            _table_cell(row.get("global_trace_mode_id", "")),
            _table_cell(row.get("display_mode_id", "")),
            _table_cell(row.get("mode_review_basis", "")),
            _table_cell(row.get("alignment_apex_delta_sec", "")),
            _table_cell(_badge_html(badge), "badge-cell", raw_html=True),
            _table_cell(
                _metric_html(
                    similarity.get("gaussian15_shape_similarity_to_mode", ""),
                    kind="shape",
                ),
                "metric-cell",
                raw_html=True,
            ),
            _table_cell(
                _metric_html(similarity.get("quick_review_score", ""), kind="score"),
                "metric-cell",
                raw_html=True,
            ),
            _table_cell(
                _badge_html(similarity.get("matrix_rt_drift_status", "")),
                "badge-cell",
                raw_html=True,
            ),
            _table_cell(row.get("rt_mode_status", "")),
            _table_cell(row.get("peak_hypothesis_id", "")),
            _table_cell(row.get("product_selection_action", "")),
            _table_cell(row.get("mode_review_warning", "")),
        )
        body_rows.append(
            f"<tr class=\"{_risk_class(badge)}\">" + "".join(cells) + "</tr>"
        )
    return (
        "<div class=\"table-wrap\"><table><thead><tr>"
        + header_html
        + "</tr></thead><tbody>"
        + "\n".join(body_rows)
        + "</tbody></table></div>"
    )


def _gallery_css() -> str:
    return """
body {
  margin: 0;
  font-family: Segoe UI, Arial, sans-serif;
  background: #f3f5f7;
  color: #16202a;
}
main {
  max-width: 1460px;
  margin: 0 auto;
  padding: 28px 30px 44px;
}
h1 {
  margin: 0 0 8px;
  font-size: 28px;
}
.note {
  max-width: 960px;
  line-height: 1.45;
}
.links a {
  display: inline-block;
  margin: 0 12px 8px 0;
}
.overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 10px;
  margin: 18px 0;
  padding: 10px;
  border: 1px solid #c9d4de;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 6px 24px rgba(34, 46, 58, 0.08);
}
.family {
  background: white;
  border: 1px solid #d6dde6;
  border-left: 6px solid #6b7c8f;
  border-radius: 8px;
  padding: 16px;
  margin: 18px 0 24px;
}
.family.risk-low {
  border-left-color: #16855b;
}
.family.risk-medium {
  border-left-color: #b07800;
}
.family.risk-high {
  border-left-color: #b33a3a;
}
.family h2 {
  margin: 0 0 8px;
  font-size: 20px;
}
.family h2 span {
  margin-left: 10px;
  color: #8a2d2d;
  font-size: 14px;
  font-weight: 600;
}
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  max-width: 100%;
  border: 1px solid #cbd6df;
  border-radius: 999px;
  background: #f6f8fa;
  color: #314151;
  padding: 2px 9px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.badge.risk-low {
  border-color: #9fd0bb;
  background: #eaf7f0;
  color: #116444;
}
.badge.risk-medium {
  border-color: #e0c178;
  background: #fff6da;
  color: #795200;
}
.badge.risk-high {
  border-color: #e0a1a1;
  background: #fff0f0;
  color: #8f2727;
}
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 16px;
  margin: 10px 0 0;
}
.score-strip {
  display: grid;
  grid-template-columns:
    minmax(160px, 0.55fr)
    minmax(160px, 0.55fr)
    minmax(280px, 1.4fr);
  gap: 10px;
  margin: 0 0 14px;
}
.score-card {
  border: 1px solid #ccd8e2;
  border-left: 5px solid #2d7fb8;
  border-radius: 6px;
  background: #f8fbfc;
  padding: 10px 12px;
}
.score-card dt {
  color: #526171;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}
.score-card dd {
  margin: 4px 0 0;
  color: #13212f;
  font-size: 18px;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.meter {
  display: block;
  height: 5px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #dbe3ea;
}
.meter span {
  display: block;
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, #b33a3a, #b07800 45%, #16855b);
}
.score-card:last-child dd {
  font-size: 13px;
  line-height: 1.35;
}
.facts dt {
  color: #5b6876;
  font-size: 12px;
}
.facts dd {
  margin: 2px 0 0;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.plots {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  margin-top: 10px;
}
figure {
  margin: 0;
}
figcaption {
  margin-bottom: 6px;
  color: #5b6876;
  font-size: 13px;
}
img {
  width: 100%;
  border: 1px solid #ccd4dd;
  border-radius: 6px;
  background: white;
}
.primary-plot img {
  display: block;
}
.context-panel {
  margin-top: 12px;
  border: 1px solid #dde5ec;
  border-radius: 6px;
  background: #fbfcfd;
}
.context-panel summary {
  cursor: pointer;
  padding: 10px 12px;
  color: #273747;
  font-size: 13px;
  font-weight: 700;
}
.context-panel > figure,
.context-panel > .table-wrap,
.context-panel > .facts {
  margin: 0;
  padding: 0 12px 12px;
}
.compact-details {
  background: #f8fafb;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  min-width: 1160px;
}
th, td {
  border-bottom: 1px solid #e3e8ef;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #eef2f6;
  color: #304050;
}
td {
  overflow-wrap: anywhere;
}
tbody tr.risk-high {
  background: #fff7f7;
}
tbody tr.risk-medium {
  background: #fffaf0;
}
.metric-cell {
  min-width: 120px;
}
.metric-value {
  display: inline-block;
  min-width: 64px;
  font-weight: 700;
}
.sample-cell {
  font-weight: 700;
  color: #1d3042;
}
@media (max-width: 820px) {
  main {
    padding: 18px 12px 32px;
  }
  .score-strip {
    grid-template-columns: 1fr;
  }
}
"""


def _gallery_overview_html(similarity_rows: Sequence[Mapping[str, str]]) -> str:
    median_shape = _float_text(
        _median_float(
            row.get("gaussian15_shape_similarity_to_mode") for row in similarity_rows
        )
    )
    median_score = _float_text(
        _median_float(row.get("quick_review_score") for row in similarity_rows)
    )
    badge_counts = _counts_text(
        row.get("quick_review_badge") for row in similarity_rows
    )
    return "\n".join(
        [
            "<section class=\"overview\" aria-label=\"Gallery review summary\">",
            _score_card("sample review rows", str(len(similarity_rows))),
            _score_card("global median shape similarity", median_shape, kind="shape"),
            _score_card("global median quick score", median_score, kind="score"),
            _score_card("badge distribution", badge_counts),
            "</section>",
        ]
    )


def _score_card(label: str, value: object, *, kind: str = "") -> str:
    meter = _metric_meter(value, kind=kind)
    return (
        "<dl class=\"score-card\">"
        f"<dt>{html.escape(label)}</dt>"
        f"<dd>{html.escape(text_value(value)) or '&nbsp;'}</dd>"
        f"{meter}"
        "</dl>"
    )


def _table_cell(value: object, class_name: str = "", *, raw_html: bool = False) -> str:
    class_attr = f" class=\"{html.escape(class_name)}\"" if class_name else ""
    content = text_value(value) if raw_html else html.escape(text_value(value))
    return f"<td{class_attr}>{content or '&nbsp;'}</td>"


def _badge_html(value: object) -> str:
    text = text_value(value)
    if not text:
        return ""
    return (
        f"<span class=\"badge {_risk_class(text)}\">"
        f"{html.escape(text)}"
        "</span>"
    )


def _metric_html(value: object, *, kind: str) -> str:
    text = text_value(value)
    if not text:
        return ""
    return (
        f"<span class=\"metric-value\">{html.escape(text)}</span>"
        f"{_metric_meter(value, kind=kind)}"
    )


def _metric_meter(value: object, *, kind: str) -> str:
    parsed = optional_float(value)
    if parsed is None or kind not in {"shape", "score"}:
        return ""
    if kind == "shape":
        percent = max(0.0, min(100.0, ((parsed + 1.0) / 2.0) * 100.0))
    else:
        percent = max(0.0, min(100.0, parsed))
    return f"<span class=\"meter\"><span style=\"width:{percent:.1f}%\"></span></span>"


def _risk_class(value: object) -> str:
    text = text_value(value)
    if any(
        token in text
        for token in (
            "wrong_apex",
            "shape_conflict",
            "drift_conflict",
            "conflict",
        )
    ):
        return "risk-high"
    if any(
        token in text
        for token in (
            "partial",
            "multimodal",
            "inconclusive",
            "review_required",
            "warning",
        )
    ):
        return "risk-medium"
    if any(token in text for token in ("coherent", "supported", "rt_close")):
        return "risk-low"
    return "risk-neutral"


def _fact(label: str, value: object) -> str:
    return (
        f"<div><dt>{html.escape(label)}</dt>"
        f"<dd>{html.escape(text_value(value)) or '&nbsp;'}</dd></div>"
    )


def _artifact_link(label: str, target: Path, *, html_dir: Path) -> str:
    rel = _relative_path(target, html_dir)
    return f"<a href=\"{html.escape(rel)}\">{html.escape(label)}</a>"


def _image_html(path_value: object, *, html_dir: Path) -> str:
    path_text = text_value(path_value)
    if not path_text:
        return "<p class=\"note\">No image.</p>"
    rel = _relative_path(Path(path_text), html_dir)
    escaped = html.escape(rel)
    return f"<a href=\"{escaped}\"><img src=\"{escaped}\" alt=\"\"></a>"


def _resolve_path(value: str, *, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path
    base_path = base_dir / path
    if base_path.exists():
        return base_path
    sibling_path = base_dir / path.name
    if sibling_path.exists():
        return sibling_path
    return cwd_path


def _resolve_optional_artifact(value: object, *, base_dir: Path) -> str:
    text = text_value(value)
    if not text:
        return ""
    return str(_resolve_path(text, base_dir=base_dir))


def _relative_path(path: Path, start: Path) -> str:
    try:
        rel = os.path.relpath(path.resolve(), start.resolve())
    except OSError:
        rel = str(path)
    return rel.replace("\\", "/")


def _identity_peak_ids(rows: Sequence[Mapping[str, str]]) -> str:
    return ";".join(
        sorted(
            {
                text_value(row.get("peak_hypothesis_id"))
                for row in rows
                if text_value(row.get("peak_hypothesis_id"))
            }
        )
    )


def _identity_basis_text(rows: Sequence[Mapping[str, str]]) -> str:
    return ";".join(
        sorted(
            {
                text_value(row.get("row_identity_basis"))
                for row in rows
                if text_value(row.get("row_identity_basis"))
            }
        )
    )


def _source_family_text(rows: Sequence[Mapping[str, str]]) -> str:
    families = {
        family
        for row in rows
        for family in _split_identity_list(row.get("source_feature_family_ids"))
    }
    return ";".join(sorted(families))


def _split_identity_list(value: object) -> tuple[str, ...]:
    raw = text_value(value)
    if not raw:
        return ()
    normalized = raw.replace(",", ";").replace("|", ";")
    return tuple(part.strip() for part in normalized.split(";") if part.strip())


def _split_semicolon_values(value: object) -> tuple[str, ...]:
    raw = text_value(value)
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(";") if part.strip())


def _counts_text(values: Iterable[object]) -> str:
    counts = Counter(text_value(value) for value in values if text_value(value))
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _dominant_text(values: Iterable[object]) -> str:
    counts = Counter(text_value(value) for value in values if text_value(value))
    if not counts:
        return ""
    value, _count = counts.most_common(1)[0]
    return value


def _safe_int(value: object) -> int | None:
    parsed = optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _max_int_field(rows: Sequence[Mapping[str, str]], field: str) -> int:
    values = [_safe_int(row.get(field)) for row in rows]
    return max((value for value in values if value is not None), default=0)


def _minutes_to_seconds(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 60.0


def _median_float(values: Iterable[object]) -> float | None:
    import numpy as np

    parsed = [optional_float(value) for value in values]
    finite = [value for value in parsed if value is not None]
    if not finite:
        return None
    return float(np.median(np.asarray(finite, dtype=float)))


def _float_text(value: object) -> str:
    parsed = _numeric_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.6g}"


def _numeric_float(value: object) -> float | None:
    if isinstance(value, str):
        return optional_float(value.strip().lstrip("'"))
    return optional_float(value)


def _float_list(value: object) -> list[float]:
    if not isinstance(value, list):
        return []
    result: list[float] = []
    for item in value:
        parsed = optional_float(item)
        if parsed is not None:
            result.append(parsed)
    return result


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed-row-bundle-tsv", type=Path, required=True)
    parser.add_argument("--overlay-batch-summary-tsv", type=Path, required=True)
    parser.add_argument("--baseline-alignment-matrix-identity-tsv", type=Path)
    parser.add_argument("--active-alignment-matrix-identity-tsv", type=Path)
    parser.add_argument("--candidate-ms2-pattern-evidence-tsv", type=Path)
    parser.add_argument("--matrix-rt-drift-policy-tsv", type=Path)
    parser.add_argument("--alignment-cells-tsv", type=Path)
    parser.add_argument("--ms1-pattern-coherence-tsv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Write TSV/HTML without rendering mode-colored PNGs.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
