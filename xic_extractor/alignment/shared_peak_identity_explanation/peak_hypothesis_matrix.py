from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.tabular_io import (
    read_tsv_required,
    text_value,
    write_tsv,
)

from . import ms1_peak_modes
from .schema import (
    HYPOTHESIS_CONSISTENCY_COLUMNS,
    PEAK_HYPOTHESIS_CELL_ASSIGNMENT_COLUMNS,
    PEAK_HYPOTHESIS_CELL_ASSIGNMENT_SCHEMA_VERSION,
    PEAK_HYPOTHESIS_INVENTORY_COLUMNS,
    PEAK_HYPOTHESIS_INVENTORY_SCHEMA_VERSION,
    PEAK_HYPOTHESIS_MATRIX_SUMMARY_COLUMNS,
    PEAK_HYPOTHESIS_MATRIX_SUMMARY_SCHEMA_VERSION,
    PEAK_HYPOTHESIS_SELECTION_COLUMNS,
    validate_row_tokens,
)

_SOURCE_MATRIX_META = frozenset(
    {
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        "peak_hypothesis_id",
        "candidate_container_id",
        "row_identity_basis",
        "legacy_rt_row_context_id",
    }
)
_FORMAL_MATRIX_META = (
    "peak_hypothesis_id",
    "feature_family_id",
    "candidate_container_id",
    "row_identity_basis",
    "legacy_rt_row_context_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
)
_HARD_PEAK_STATUSES = frozenset(
    {"cross_mode_rescue_blocked", "mode_split_required", "consolidation_no_go"}
)
_HARD_CONSISTENCY_STATUSES = frozenset({"conflict", "split_required"})
_PRODUCT_CANDIDATE_STATUS = "product_candidate_core"
_SUPPORT_FAMILY_VERDICT = "ms1_shape_supports_family_backfill"
_GAUSSIAN15_TRACE_MODE_VERDICTS = frozenset(
    {
        "ms1_shape_supports_family_backfill",
        "review_required_neighboring_ms1_interference",
    }
)
_INFERRED_MODE_GAP_MIN = 0.5
_INFERRED_MODE_MIN_CLUSTER_SIZE = 2
_INFERRED_MODE_OUTER_MARGIN_MIN = 0.25

_MATRIX_REQUIRED_COLUMNS = ("feature_family_id",)
_REVIEW_REQUIRED_COLUMNS = ("feature_family_id",)
_CELL_REQUIRED_COLUMNS = ("feature_family_id", "sample_stem", "status")
_PEAK_SELECTION_REQUIRED_COLUMNS = tuple(
    column
    for column in PEAK_HYPOTHESIS_SELECTION_COLUMNS
    if column != "peak_hypothesis_selection_schema_version"
)
_HYPOTHESIS_CONSISTENCY_REQUIRED_COLUMNS = tuple(
    column
    for column in HYPOTHESIS_CONSISTENCY_COLUMNS
    if column != "hypothesis_consistency_schema_version"
)


@dataclass(frozen=True)
class PeakHypothesisMatrixConstruction:
    matrix_header: tuple[str, ...]
    matrix_rows: tuple[dict[str, str], ...]
    inventory_rows: tuple[dict[str, str], ...]
    assignment_rows: tuple[dict[str, str], ...]
    summary_row: dict[str, str]


@dataclass(frozen=True)
class PeakHypothesisMatrixOutputs:
    matrix_tsv: Path
    inventory_tsv: Path
    assignments_tsv: Path
    summary_tsv: Path


@dataclass(frozen=True)
class _AssignmentDecision:
    peak_hypothesis_id: str
    status: str
    action: str
    row_identity_basis: str
    matrix_value_effect: str
    write_matrix_value: bool
    reason: str


@dataclass(frozen=True)
class _ExpandedPeakCandidate:
    feature_family_id: str
    sample_id: str
    peak_hypothesis_id: str
    mode_id: str
    start_rt: float
    end_rt: float
    peak_rt: float
    peak_height: float
    area: float
    source_artifact: str
    peak_hypothesis_status: str
    product_selection_action: str
    product_selection_blocker: str
    evidence_consistency_status: str
    split_readiness_status: str
    consistency_blockers: str
    matrix_value_effect: str
    reason: str
    candidate_value_basis: str


@dataclass(frozen=True)
class _ModeWindow:
    mode_id: str
    start_rt: float
    end_rt: float
    peak_hypothesis_status: str = "raw_mode_review_only"
    product_selection_action: str = "require_raw_mode_review"
    product_selection_blocker: str = "raw_mode_review_only"
    evidence_consistency_status: str = "review_only"
    split_readiness_status: str = "review_required"
    consistency_blockers: str = "raw_mode_review_only"
    matrix_value_effect: str = "written"
    reason: str = "raw_overlay_multi_peak_candidate_enumerated"
    candidate_value_basis: str = "raw_overlay_window_trapezoid_area"


def build_peak_hypothesis_matrix_outputs(
    *,
    alignment_matrix_tsv: Path,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    peak_hypothesis_selection_tsv: Path,
    output_dir: Path,
    hypothesis_consistency_tsv: Path | None = None,
    overlay_trace_data_jsons: Sequence[Path] = (),
    allow_overwrite_source: bool = False,
    require_complete_peak_hypothesis_identity: bool = False,
) -> PeakHypothesisMatrixOutputs:
    matrix_header, matrix_rows = _read_tsv_with_header(
        alignment_matrix_tsv,
        required_columns=_MATRIX_REQUIRED_COLUMNS,
    )
    review_rows = read_tsv_required(alignment_review_tsv, _REVIEW_REQUIRED_COLUMNS)
    cell_rows = read_tsv_required(alignment_cells_tsv, _CELL_REQUIRED_COLUMNS)
    peak_hypothesis_rows = read_tsv_required(
        peak_hypothesis_selection_tsv,
        _PEAK_SELECTION_REQUIRED_COLUMNS,
    )
    consistency_rows = (
        read_tsv_required(
            hypothesis_consistency_tsv,
            _HYPOTHESIS_CONSISTENCY_REQUIRED_COLUMNS,
        )
        if hypothesis_consistency_tsv is not None
        else ()
    )
    expanded_candidates = load_overlay_peak_candidate_rows(overlay_trace_data_jsons)

    construction = construct_peak_hypothesis_matrix(
        matrix_header=matrix_header,
        matrix_rows=matrix_rows,
        review_rows=review_rows,
        cell_rows=cell_rows,
        peak_hypothesis_selection_rows=peak_hypothesis_rows,
        hypothesis_consistency_rows=consistency_rows,
        expanded_peak_candidate_rows=expanded_candidates,
    )
    if (
        require_complete_peak_hypothesis_identity
        and construction.summary_row["canonical_row_identity_ready"] != "TRUE"
    ):
        raise ValueError(
            "complete PeakHypothesis identity requires canonical row identity "
            "readiness; blockers="
            f"{construction.summary_row['canonical_row_identity_blockers']}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / "alignment_matrix.tsv"
    inventory_path = output_dir / "peak_hypothesis_inventory.tsv"
    assignments_path = output_dir / "peak_hypothesis_cell_assignments.tsv"
    summary_path = output_dir / "peak_hypothesis_matrix_summary.tsv"
    if not allow_overwrite_source:
        _reject_source_overwrite(
            output_paths=(matrix_path,),
            source_paths=(alignment_matrix_tsv,),
        )

    write_tsv(
        matrix_path,
        construction.matrix_rows,
        construction.matrix_header,
        lineterminator="\n",
    )
    write_tsv(
        inventory_path,
        construction.inventory_rows,
        PEAK_HYPOTHESIS_INVENTORY_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        assignments_path,
        construction.assignment_rows,
        PEAK_HYPOTHESIS_CELL_ASSIGNMENT_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        summary_path,
        [construction.summary_row],
        PEAK_HYPOTHESIS_MATRIX_SUMMARY_COLUMNS,
        lineterminator="\n",
    )
    return PeakHypothesisMatrixOutputs(
        matrix_tsv=matrix_path,
        inventory_tsv=inventory_path,
        assignments_tsv=assignments_path,
        summary_tsv=summary_path,
    )


def construct_peak_hypothesis_matrix(
    *,
    matrix_header: Sequence[str],
    matrix_rows: Sequence[Mapping[str, str]],
    review_rows: Sequence[Mapping[str, str]],
    cell_rows: Sequence[Mapping[str, str]],
    peak_hypothesis_selection_rows: Sequence[Mapping[str, str]],
    hypothesis_consistency_rows: Sequence[Mapping[str, str]] = (),
    expanded_peak_candidate_rows: Sequence[Mapping[str, str]] = (),
) -> PeakHypothesisMatrixConstruction:
    sample_columns = _sample_columns(matrix_header)
    matrix_by_family = _rows_by_family(matrix_rows)
    review_by_family = _rows_by_family(review_rows)
    cells_by_key = _best_cells_by_key(cell_rows)
    peak_hypotheses_by_key = _rows_by_key(peak_hypothesis_selection_rows)
    consistency_by_key = _rows_by_key(hypothesis_consistency_rows)
    expanded_candidates = _expanded_candidates_by_key(expanded_peak_candidate_rows)
    expanded_sample_keys = frozenset(
        (candidate.feature_family_id, candidate.sample_id)
        for candidate in expanded_candidates
    )

    rows_by_hypothesis: dict[str, dict[str, str]] = {}
    assignment_rows: list[dict[str, str]] = []
    matrix_value_conflict_cells = 0
    for family_id, sample_id in _assignment_keys(
        matrix_by_family,
        cells_by_key,
        peak_hypotheses_by_key,
        sample_columns=sample_columns,
    ):
        if (
            (family_id, sample_id) in expanded_sample_keys
            and (family_id, sample_id) not in peak_hypotheses_by_key
        ):
            continue
        matrix_row = matrix_by_family.get(family_id, {})
        review_row = review_by_family.get(family_id, {})
        source_matrix_value = text_value(matrix_row.get(sample_id))
        source_cell = cells_by_key.get((family_id, sample_id), {})
        peak_hypothesis = peak_hypotheses_by_key.get((family_id, sample_id), {})
        consistency = consistency_by_key.get((family_id, sample_id), {})
        decision = _assignment_decision(
            family_id=family_id,
            peak_hypothesis=peak_hypothesis,
            consistency=consistency,
            source_matrix_value=source_matrix_value,
        )
        assignment_row = _assignment_row(
            family_id=family_id,
            sample_id=sample_id,
            source_matrix_value=source_matrix_value,
            source_cell=source_cell,
            peak_hypothesis=peak_hypothesis,
            consistency=consistency,
            decision=decision,
        )
        assignment_rows.append(assignment_row)

        if not decision.write_matrix_value:
            continue
        if decision.row_identity_basis == "family_projection_no_split_evidence":
            continue
        _reject_multi_family_hypothesis_collapse(
            rows_by_hypothesis.get(decision.peak_hypothesis_id),
            peak_hypothesis_id=decision.peak_hypothesis_id,
            family_id=family_id,
        )
        output_row = rows_by_hypothesis.setdefault(
            decision.peak_hypothesis_id,
            _new_matrix_row(
                decision.peak_hypothesis_id,
                family_id=family_id,
                row_identity_basis=decision.row_identity_basis,
                review_row=review_row,
                sample_columns=sample_columns,
            ),
        )
        _append_unique(output_row, "feature_family_id", family_id)
        _append_unique(output_row, "candidate_container_id", family_id)
        previous = output_row.get(sample_id, "")
        value = source_matrix_value
        if previous and previous != value:
            value = _select_conflicting_matrix_value(previous, value)
            matrix_value_conflict_cells += 1
        output_row[sample_id] = value

    for candidate in expanded_candidates:
        assignment_row = _expanded_assignment_row(candidate)
        assignment_rows.append(assignment_row)
        _reject_multi_family_hypothesis_collapse(
            rows_by_hypothesis.get(candidate.peak_hypothesis_id),
            peak_hypothesis_id=candidate.peak_hypothesis_id,
            family_id=candidate.feature_family_id,
        )
        output_row = rows_by_hypothesis.setdefault(
            candidate.peak_hypothesis_id,
            _new_matrix_row(
                candidate.peak_hypothesis_id,
                family_id=candidate.feature_family_id,
                row_identity_basis="matrix_construction_peak_hypothesis",
                review_row=review_by_family.get(candidate.feature_family_id, {}),
                sample_columns=sample_columns,
            ),
        )
        _append_unique(output_row, "feature_family_id", candidate.feature_family_id)
        _append_unique(
            output_row,
            "candidate_container_id",
            candidate.feature_family_id,
        )
        previous = output_row.get(candidate.sample_id, "")
        value = _format_number(candidate.area)
        if previous and previous != value:
            value = _select_conflicting_matrix_value(previous, value)
            matrix_value_conflict_cells += 1
        output_row[candidate.sample_id] = value

    matrix_output_rows = tuple(
        row
        for row in (rows_by_hypothesis[key] for key in sorted(rows_by_hypothesis))
        if _has_sample_value(row, sample_columns)
    )
    inventory_rows = _inventory_rows(assignment_rows)
    summary_row = _summary_row(
        source_matrix_rows=len(matrix_rows),
        output_matrix_rows=len(matrix_output_rows),
        sample_columns=sample_columns,
        inventory_rows=inventory_rows,
        assignment_rows=assignment_rows,
        matrix_value_conflict_cells=matrix_value_conflict_cells,
    )
    return PeakHypothesisMatrixConstruction(
        matrix_header=(*_FORMAL_MATRIX_META, *sample_columns),
        matrix_rows=matrix_output_rows,
        inventory_rows=inventory_rows,
        assignment_rows=tuple(assignment_rows),
        summary_row=summary_row,
    )


def load_overlay_peak_candidate_rows(
    paths: Sequence[Path],
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"overlay trace data must be a JSON object: {path}")
        family_id = text_value(
            payload.get("family_id") or payload.get("feature_family_id")
        )
        if not family_id:
            raise ValueError(f"overlay trace data does not declare family_id: {path}")
        trace_rows = _overlay_trace_rows(payload)
        mode_windows = _mode_windows(payload.get("mode_windows"))
        if not mode_windows and _supports_gaussian15_trace_mode_windows(payload):
            mode_windows = _infer_gaussian15_mode_windows_from_trace_rows(
                trace_rows,
                payload,
            )
        if not mode_windows and _supports_inferred_mode_windows(payload):
            mode_windows = _infer_mode_windows_from_trace_rows(trace_rows, payload)
        mode_windows = _mode_windows_with_detected_seed(mode_windows, trace_rows)
        if not mode_windows:
            continue
        for trace_row in trace_rows:
            sample_id = text_value(trace_row.get("sample_stem"))
            if not sample_id:
                continue
            rt_values, intensity_values = _numeric_trace(trace_row)
            if not rt_values or not intensity_values:
                continue
            for mode_window in mode_windows:
                candidate = _candidate_from_window(
                    family_id=family_id,
                    sample_id=sample_id,
                    mode_window=mode_window,
                    rt_values=rt_values,
                    intensity_values=intensity_values,
                    source_artifact=str(path),
                )
                if candidate is None:
                    continue
                rows.append(_expanded_candidate_to_row(candidate))
    return tuple(rows)


def _mode_windows(value: object) -> tuple[_ModeWindow, ...]:
    if not isinstance(value, Mapping):
        return ()
    windows: list[_ModeWindow] = []
    for mode_id, bounds in value.items():
        parsed = _mode_window_from_value(text_value(mode_id), bounds)
        if parsed is not None:
            windows.append(parsed)
    return tuple(windows)


def _mode_window_from_value(mode_id: str, value: object) -> _ModeWindow | None:
    if isinstance(value, Mapping):
        start_rt = _first_float(
            value,
            ("start_rt", "raw_start_rt", "candidate_peak_start_rt", "rt_start"),
        )
        end_rt = _first_float(
            value,
            ("end_rt", "raw_end_rt", "candidate_peak_end_rt", "rt_end"),
        )
        if start_rt is None or end_rt is None or end_rt <= start_rt:
            return None
        reason = _default(value.get("reason"), "explicit_mode_hypothesis_window")
        return _ModeWindow(
            mode_id=mode_id,
            start_rt=start_rt,
            end_rt=end_rt,
            peak_hypothesis_status="raw_mode_review_only",
            product_selection_action="require_raw_mode_review",
            product_selection_blocker="raw_mode_review_only",
            evidence_consistency_status="review_only",
            split_readiness_status="review_required",
            consistency_blockers="raw_overlay_mode_window_not_product_authority",
            matrix_value_effect=_default(value.get("matrix_value_effect"), "written"),
            reason=_default(
                f"{reason}_review_only_product_status_ignored",
                "explicit_mode_hypothesis_window_review_only",
            ),
            candidate_value_basis=_default(
                value.get("candidate_value_basis"),
                "explicit_mode_hypothesis_raw_overlay_area",
            ),
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        bounds = value
        if not isinstance(bounds, Sequence) or isinstance(bounds, str | bytes):
            return None
        if len(bounds) != 2:
            return None
        start_rt = _float_or_none(bounds[0])
        end_rt = _float_or_none(bounds[1])
        if start_rt is None or end_rt is None or end_rt <= start_rt:
            return None
        return _ModeWindow(mode_id=mode_id, start_rt=start_rt, end_rt=end_rt)
    return None


def _mode_windows_with_detected_seed(
    mode_windows: Sequence[_ModeWindow],
    trace_rows: Sequence[Mapping[str, object]],
) -> tuple[_ModeWindow, ...]:
    return tuple(
        mode_window
        for mode_window in mode_windows
        if _mode_window_has_detected_seed(mode_window, trace_rows)
    )


def _mode_window_has_detected_seed(
    mode_window: _ModeWindow,
    trace_rows: Sequence[Mapping[str, object]],
) -> bool:
    if ms1_peak_modes.detected_seed_has_gaussian15_peak_in_window(
        trace_rows,
        start_rt=mode_window.start_rt,
        end_rt=mode_window.end_rt,
    ):
        return True
    for trace_row in trace_rows:
        if not _trace_is_detected_seed(trace_row):
            continue
        apex_rt = _first_float(
            trace_row,
            ("cell_apex_rt", "raw_selected_rt", "trace_apex_rt"),
        )
        if apex_rt is None:
            continue
        if mode_window.start_rt <= apex_rt <= mode_window.end_rt:
            return True
    return False


def _trace_is_detected_seed(trace_row: Mapping[str, object]) -> bool:
    return (
        text_value(trace_row.get("status")) == "detected"
        or text_value(trace_row.get("group")) == "detected_seed"
    )


def _supports_inferred_mode_windows(payload: Mapping[str, object]) -> bool:
    evidence = payload.get("evidence_summary")
    if not isinstance(evidence, Mapping):
        return False
    return text_value(evidence.get("family_verdict")) == _SUPPORT_FAMILY_VERDICT


def _supports_gaussian15_trace_mode_windows(payload: Mapping[str, object]) -> bool:
    evidence = payload.get("evidence_summary")
    if not isinstance(evidence, Mapping):
        return False
    return text_value(evidence.get("family_verdict")) in _GAUSSIAN15_TRACE_MODE_VERDICTS


def _infer_gaussian15_mode_windows_from_trace_rows(
    trace_rows: Sequence[Mapping[str, object]],
    payload: Mapping[str, object],
) -> tuple[_ModeWindow, ...]:
    windows = ms1_peak_modes.infer_gaussian15_peak_mode_windows(
        trace_rows,
        rt_min=_float_or_none(payload.get("rt_min")),
        rt_max=_float_or_none(payload.get("rt_max")),
    )
    return tuple(
        _ModeWindow(
            mode_id=window.mode_id,
            start_rt=window.start_rt,
            end_rt=window.end_rt,
            reason="gaussian15_trace_multipeak_mode_window_review_only",
            candidate_value_basis="gaussian15_trace_mode_window_area",
        )
        for window in windows
    )


def _infer_mode_windows_from_trace_rows(
    trace_rows: Sequence[Mapping[str, object]],
    payload: Mapping[str, object],
) -> tuple[_ModeWindow, ...]:
    apex_values = _infer_mode_apex_values(trace_rows)
    if not apex_values:
        return ()

    clusters: list[list[float]] = []
    current: list[float] = []
    for value in apex_values:
        if current and value - current[-1] > _INFERRED_MODE_GAP_MIN:
            clusters.append(current)
            current = []
        current.append(value)
    if current:
        clusters.append(current)

    clusters = [
        cluster
        for cluster in clusters
        if len(cluster) >= _INFERRED_MODE_MIN_CLUSTER_SIZE
    ]
    if len(clusters) <= 1:
        return ()

    medians = [cluster[len(cluster) // 2] for cluster in clusters]
    trace_min = _float_or_none(payload.get("rt_min"))
    trace_max = _float_or_none(payload.get("rt_max"))
    windows: list[_ModeWindow] = []
    for index, cluster in enumerate(clusters):
        median = medians[index]
        if index == 0:
            start_rt = min(cluster) - _INFERRED_MODE_OUTER_MARGIN_MIN
            if trace_min is not None:
                start_rt = max(trace_min, start_rt)
        else:
            start_rt = (medians[index - 1] + median) / 2.0

        if index == len(clusters) - 1:
            end_rt = max(cluster) + _INFERRED_MODE_OUTER_MARGIN_MIN
            if trace_max is not None:
                end_rt = min(trace_max, end_rt)
        else:
            end_rt = (median + medians[index + 1]) / 2.0

        if end_rt > start_rt:
            mode_id = f"raw_mode_{index + 1}_{median:.2f}min"
            windows.append(
                _ModeWindow(
                    mode_id=mode_id,
                    start_rt=start_rt,
                    end_rt=end_rt,
                    reason="raw_apex_gap_inferred_mode_window_review_only",
                )
            )
    return tuple(windows)


def _infer_mode_apex_values(
    trace_rows: Sequence[Mapping[str, object]],
) -> tuple[float, ...]:
    for fields in (
        ("cell_apex_rt", "raw_selected_rt"),
        ("trace_apex_rt",),
    ):
        values = sorted(
            parsed
            for row in trace_rows
            for field in fields
            if (parsed := _float_or_none(row.get(field))) is not None
        )
        if len(values) >= _INFERRED_MODE_MIN_CLUSTER_SIZE:
            return tuple(values)
    return ()


def _overlay_trace_rows(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    rows = payload.get("traces")
    if not isinstance(rows, list):
        rows = payload.get("samples")
    if not isinstance(rows, list):
        raise ValueError("overlay trace data missing traces/samples array")
    return tuple(row for row in rows if isinstance(row, Mapping))


def _numeric_trace(
    trace_row: Mapping[str, object],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    rt_values = _float_values(trace_row.get("rt") or trace_row.get("raw_rt"))
    intensity_values = _float_values(
        trace_row.get("intensity") or trace_row.get("raw_intensity")
    )
    count = min(len(rt_values), len(intensity_values))
    return rt_values[:count], intensity_values[:count]


def _candidate_from_window(
    *,
    family_id: str,
    sample_id: str,
    mode_window: _ModeWindow,
    rt_values: Sequence[float],
    intensity_values: Sequence[float],
    source_artifact: str,
) -> _ExpandedPeakCandidate | None:
    points = tuple(
        (rt, max(intensity, 0.0))
        for rt, intensity in zip(rt_values, intensity_values, strict=False)
        if mode_window.start_rt <= rt <= mode_window.end_rt
    )
    if not points:
        return None
    peak_rt, peak_height = max(points, key=lambda item: item[1])
    if peak_height <= 0:
        return None
    area = _trapezoid_area(points)
    if area <= 0:
        area = peak_height
    return _ExpandedPeakCandidate(
        feature_family_id=family_id,
        sample_id=sample_id,
        peak_hypothesis_id=f"{family_id}::{mode_window.mode_id}",
        mode_id=mode_window.mode_id,
        start_rt=mode_window.start_rt,
        end_rt=mode_window.end_rt,
        peak_rt=peak_rt,
        peak_height=peak_height,
        area=area,
        source_artifact=source_artifact,
        peak_hypothesis_status=mode_window.peak_hypothesis_status,
        product_selection_action=mode_window.product_selection_action,
        product_selection_blocker=mode_window.product_selection_blocker,
        evidence_consistency_status=mode_window.evidence_consistency_status,
        split_readiness_status=mode_window.split_readiness_status,
        consistency_blockers=mode_window.consistency_blockers,
        matrix_value_effect=mode_window.matrix_value_effect,
        reason=mode_window.reason,
        candidate_value_basis=mode_window.candidate_value_basis,
    )


def _expanded_candidate_to_row(candidate: _ExpandedPeakCandidate) -> dict[str, str]:
    return {
        "feature_family_id": candidate.feature_family_id,
        "sample_id": candidate.sample_id,
        "peak_hypothesis_id": candidate.peak_hypothesis_id,
        "mode_id": candidate.mode_id,
        "candidate_peak_start_rt": _format_number(candidate.start_rt),
        "candidate_peak_end_rt": _format_number(candidate.end_rt),
        "candidate_peak_rt": _format_number(candidate.peak_rt),
        "candidate_peak_height": _format_number(candidate.peak_height),
        "candidate_area": _format_number(candidate.area),
        "candidate_value_source": candidate.source_artifact,
        "candidate_value_basis": candidate.candidate_value_basis,
        "peak_hypothesis_status": candidate.peak_hypothesis_status,
        "product_selection_action": candidate.product_selection_action,
        "product_selection_blocker": candidate.product_selection_blocker,
        "evidence_consistency_status": candidate.evidence_consistency_status,
        "split_readiness_status": candidate.split_readiness_status,
        "consistency_blockers": candidate.consistency_blockers,
        "matrix_value_effect": candidate.matrix_value_effect,
        "reason": candidate.reason,
    }


def _assignment_decision(
    *,
    family_id: str,
    peak_hypothesis: Mapping[str, str],
    consistency: Mapping[str, str],
    source_matrix_value: str,
) -> _AssignmentDecision:
    peak_hypothesis_id = text_value(peak_hypothesis.get("peak_hypothesis_id"))
    peak_status = text_value(peak_hypothesis.get("peak_hypothesis_status"))
    consistency_status = text_value(consistency.get("evidence_consistency_status"))
    split_readiness = text_value(consistency.get("split_readiness_status"))
    blocker = text_value(peak_hypothesis.get("product_selection_blocker"))

    if not source_matrix_value:
        return _AssignmentDecision(
            peak_hypothesis_id=peak_hypothesis_id or _projection_id(family_id),
            status="recorded_no_source_matrix_value",
            action="record_cell_no_matrix_value",
            row_identity_basis=(
                "matrix_construction_peak_hypothesis"
                if peak_hypothesis_id
                else "family_projection_no_split_evidence"
            ),
            matrix_value_effect="source_matrix_value_missing",
            write_matrix_value=False,
            reason="assignment_recorded_but_source_matrix_value_missing",
        )
    if (
        peak_status in _HARD_PEAK_STATUSES
        or blocker
        in {"cross_mode_rescue", "mode_split_required", "consolidation_no_go"}
        or consistency_status in _HARD_CONSISTENCY_STATUSES
        or split_readiness
        in {"cross_mode_rescue_blocked", "mode_split_required", "consolidation_no_go"}
    ):
        return _AssignmentDecision(
            peak_hypothesis_id=peak_hypothesis_id or _projection_id(family_id),
            status="blocked",
            action="skip_blocked_cell",
            row_identity_basis=(
                "matrix_construction_peak_hypothesis"
                if peak_hypothesis_id
                else "family_projection_no_split_evidence"
            ),
            matrix_value_effect="blanked",
            write_matrix_value=False,
            reason="hard_peak_hypothesis_or_consistency_blocker",
        )
    if peak_hypothesis_id and peak_status == _PRODUCT_CANDIDATE_STATUS:
        return _AssignmentDecision(
            peak_hypothesis_id=peak_hypothesis_id,
            status="assigned",
            action="write_peak_hypothesis_cell",
            row_identity_basis="matrix_construction_peak_hypothesis",
            matrix_value_effect="written",
            write_matrix_value=True,
            reason="product_candidate_peak_hypothesis_selected_before_matrix_output",
        )
    return _AssignmentDecision(
        peak_hypothesis_id=_projection_id(family_id),
        status="family_projection",
        action="write_family_projection_cell",
        row_identity_basis="family_projection_no_split_evidence",
        matrix_value_effect="written",
        write_matrix_value=True,
        reason="no_product_candidate_peak_hypothesis_available_before_matrix_output",
    )


def _reject_multi_family_hypothesis_collapse(
    existing_row: Mapping[str, str] | None,
    *,
    peak_hypothesis_id: str,
    family_id: str,
) -> None:
    if existing_row is None:
        return
    source_ids = tuple(
        part.strip()
        for part in existing_row.get("feature_family_id", "").split(";")
        if part.strip()
    )
    if not source_ids or family_id in source_ids:
        return
    collapsed_ids = ";".join((*source_ids, family_id))
    raise ValueError(
        f"{peak_hypothesis_id}: peak hypothesis matrix row requires exactly one "
        f"source_feature_family_id, got {collapsed_ids}"
    )


def _assignment_row(
    *,
    family_id: str,
    sample_id: str,
    source_matrix_value: str,
    source_cell: Mapping[str, str],
    peak_hypothesis: Mapping[str, str],
    consistency: Mapping[str, str],
    decision: _AssignmentDecision,
) -> dict[str, str]:
    row = {
        "peak_hypothesis_cell_assignment_schema_version": (
            PEAK_HYPOTHESIS_CELL_ASSIGNMENT_SCHEMA_VERSION
        ),
        "feature_family_id": family_id,
        "candidate_container_id": family_id,
        "sample_id": sample_id,
        "peak_hypothesis_id": decision.peak_hypothesis_id,
        "construction_assignment_status": decision.status,
        "construction_assignment_action": decision.action,
        "row_identity_basis": decision.row_identity_basis,
        "source_matrix_value": source_matrix_value,
        "source_cell_area": text_value(source_cell.get("area")),
        "source_cell_status": text_value(source_cell.get("status")),
        "candidate_peak_rt": "",
        "candidate_peak_start_rt": "",
        "candidate_peak_end_rt": "",
        "candidate_peak_height": "",
        "candidate_value_basis": "",
        "candidate_value_source": "",
        "peak_hypothesis_status": _default(
            peak_hypothesis.get("peak_hypothesis_status"),
            "not_available",
        ),
        "product_selection_action": _default(
            peak_hypothesis.get("product_selection_action"),
            "no_product_action",
        ),
        "product_selection_blocker": _default(
            peak_hypothesis.get("product_selection_blocker"),
            "not_available",
        ),
        "evidence_consistency_status": _default(
            consistency.get("evidence_consistency_status"),
            "not_available",
        ),
        "split_readiness_status": _default(
            consistency.get("split_readiness_status"),
            "not_available",
        ),
        "consistency_blockers": text_value(consistency.get("consistency_blockers")),
        "matrix_value_effect": decision.matrix_value_effect,
        "reason": decision.reason,
        "diagnostic_only": "TRUE",
    }
    validate_row_tokens(row)
    return row


def _expanded_assignment_row(candidate: _ExpandedPeakCandidate) -> dict[str, str]:
    row = {
        "peak_hypothesis_cell_assignment_schema_version": (
            PEAK_HYPOTHESIS_CELL_ASSIGNMENT_SCHEMA_VERSION
        ),
        "feature_family_id": candidate.feature_family_id,
        "candidate_container_id": candidate.feature_family_id,
        "sample_id": candidate.sample_id,
        "peak_hypothesis_id": candidate.peak_hypothesis_id,
        "construction_assignment_status": "expanded_candidate",
        "construction_assignment_action": "write_expanded_peak_hypothesis_cell",
        "row_identity_basis": "matrix_construction_peak_hypothesis",
        "source_matrix_value": _format_number(candidate.area),
        "source_cell_area": "",
        "source_cell_status": "raw_overlay_candidate",
        "candidate_peak_rt": _format_number(candidate.peak_rt),
        "candidate_peak_start_rt": _format_number(candidate.start_rt),
        "candidate_peak_end_rt": _format_number(candidate.end_rt),
        "candidate_peak_height": _format_number(candidate.peak_height),
        "candidate_value_basis": candidate.candidate_value_basis,
        "candidate_value_source": candidate.source_artifact,
        "peak_hypothesis_status": candidate.peak_hypothesis_status,
        "product_selection_action": candidate.product_selection_action,
        "product_selection_blocker": candidate.product_selection_blocker,
        "evidence_consistency_status": candidate.evidence_consistency_status,
        "split_readiness_status": candidate.split_readiness_status,
        "consistency_blockers": candidate.consistency_blockers,
        "matrix_value_effect": candidate.matrix_value_effect,
        "reason": candidate.reason,
        "diagnostic_only": "TRUE",
    }
    validate_row_tokens(row)
    return row


def _inventory_rows(
    assignment_rows: Sequence[Mapping[str, str]],
) -> tuple[dict[str, str], ...]:
    rows_by_hypothesis: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in assignment_rows:
        rows_by_hypothesis[row["peak_hypothesis_id"]].append(row)

    inventory: list[dict[str, str]] = []
    for peak_hypothesis_id in sorted(rows_by_hypothesis):
        assignments = rows_by_hypothesis[peak_hypothesis_id]
        assignment_counts = Counter(
            row["construction_assignment_status"] for row in assignments
        )
        consistency_counts = Counter(
            row["evidence_consistency_status"] for row in assignments
        )
        row_identity_basis = _first_non_empty(assignments, "row_identity_basis")
        row = {
            "peak_hypothesis_inventory_schema_version": (
                PEAK_HYPOTHESIS_INVENTORY_SCHEMA_VERSION
            ),
            "peak_hypothesis_id": peak_hypothesis_id,
            "feature_family_id": _unique_values(assignments, "feature_family_id"),
            "candidate_container_id": _unique_values(
                assignments,
                "candidate_container_id",
            ),
            "product_unit_scope": _inventory_product_unit_scope(assignments),
            "row_identity_basis": row_identity_basis,
            "peak_hypothesis_status": _first_non_empty(
                assignments,
                "peak_hypothesis_status",
                default="not_available",
            ),
            "selected_mode_id": _selected_mode_id(peak_hypothesis_id),
            "selected_mode_role": "unknown",
            "selected_mode_tag_status": "unknown",
            "family_mode_class": "inconclusive",
            "assigned_cell_count": str(assignment_counts["assigned"]),
            "expanded_candidate_cell_count": str(
                assignment_counts["expanded_candidate"]
            ),
            "blocked_cell_count": str(assignment_counts["blocked"]),
            "source_matrix_value_count": str(
                sum(
                    1
                    for assignment in assignments
                    if assignment["source_matrix_value"]
                )
            ),
            "projected_family_count": str(
                len(_split_semicolon(_unique_values(assignments, "feature_family_id")))
                if row_identity_basis == "family_projection_no_split_evidence"
                else 0
            ),
            "assignment_status_counts": _format_counts(assignment_counts),
            "consistency_status_counts": _format_counts(consistency_counts),
            "reason": _inventory_reason(assignment_counts, row_identity_basis),
            "diagnostic_only": "TRUE",
        }
        validate_row_tokens(row)
        inventory.append(row)
    return tuple(inventory)


def _summary_row(
    *,
    source_matrix_rows: int,
    output_matrix_rows: int,
    sample_columns: Sequence[str],
    inventory_rows: Sequence[Mapping[str, str]],
    assignment_rows: Sequence[Mapping[str, str]],
    matrix_value_conflict_cells: int,
) -> dict[str, str]:
    assignment_counts = Counter(
        row["construction_assignment_status"] for row in assignment_rows
    )
    explicit_peak_hypothesis_rows = sum(
        1
        for row in inventory_rows
        if row["row_identity_basis"] == "matrix_construction_peak_hypothesis"
    )
    family_projection_rows = sum(
        1
        for row in inventory_rows
        if row["row_identity_basis"] == "family_projection_no_split_evidence"
    )
    has_projection = family_projection_rows > 0
    hard_blocks = assignment_counts["blocked"]
    missing_source_values = assignment_counts["recorded_no_source_matrix_value"]
    expanded_candidates = assignment_counts["expanded_candidate"]
    canonical_blocker = _canonical_row_identity_blocker(
        family_projection_rows=family_projection_rows,
        expanded_candidates=expanded_candidates,
        hard_blocks=hard_blocks,
        missing_source_values=missing_source_values,
    )
    row = {
        "peak_hypothesis_matrix_summary_schema_version": (
            PEAK_HYPOTHESIS_MATRIX_SUMMARY_SCHEMA_VERSION
        ),
        "construction_mode": "peak_hypothesis_assignment",
        "source_matrix_rows": str(source_matrix_rows),
        "output_matrix_rows": str(output_matrix_rows),
        "sample_count": str(len(sample_columns)),
        "inventory_rows": str(len(inventory_rows)),
        "assignment_rows": str(len(assignment_rows)),
        "explicit_peak_hypothesis_rows": str(explicit_peak_hypothesis_rows),
        "family_projection_rows": str(family_projection_rows),
        "assigned_cell_count": str(assignment_counts["assigned"]),
        "expanded_candidate_cell_count": str(expanded_candidates),
        "projected_cell_count": str(assignment_counts["family_projection"]),
        "blocked_cell_count": str(hard_blocks),
        "missing_source_matrix_value_count": str(missing_source_values),
        "matrix_value_conflict_cells": str(matrix_value_conflict_cells),
        "matrix_value_conflict_policy": (
            "max_area_pending_baseline"
            if matrix_value_conflict_cells
            else "not_applicable"
        ),
        "matrix_row_identity": "peak_hypothesis_id",
        "canonical_row_identity_ready": (
            "TRUE" if canonical_blocker == "none" else "FALSE"
        ),
        "canonical_row_identity_blockers": canonical_blocker,
        "canonical_row_identity_scope": (
            "matrix_construction_peak_hypothesis_with_family_projections"
        ),
        "family_projection_semantics": (
            "projection_not_split_proof"
            if has_projection
            else "explicit_hypothesis_only"
        ),
        "all_family_split_science_ready": (
            "FALSE"
            if (
                has_projection
                or hard_blocks
                or missing_source_values
                or expanded_candidates
            )
            else "TRUE"
        ),
        "construction_gate_status": _construction_gate_status(
            expanded_candidates=expanded_candidates,
            hard_blocks=hard_blocks,
        ),
        "summary_reason": "peak_hypothesis_assignment_layer_built_before_matrix_output",
        "diagnostic_only": "TRUE",
    }
    validate_row_tokens(row)
    return row


def _canonical_row_identity_blocker(
    *,
    family_projection_rows: int,
    expanded_candidates: int,
    hard_blocks: int,
    missing_source_values: int,
) -> str:
    if family_projection_rows:
        return "family_projection_present"
    if expanded_candidates:
        return "raw_mode_review_only"
    if hard_blocks:
        return "matrix_construction_blocked"
    if missing_source_values:
        return "source_matrix_value_missing"
    return "none"


def _construction_gate_status(
    *,
    expanded_candidates: int,
    hard_blocks: int,
) -> str:
    if hard_blocks:
        return "blocked"
    if expanded_candidates:
        return "diagnostic_only"
    return "construction_ready"


def _read_tsv_with_header(
    path: Path,
    *,
    required_columns: Sequence[str],
) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = tuple(reader.fieldnames or ())
        missing = [column for column in required_columns if column not in header]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return header, tuple(dict(row) for row in reader)


def _sample_columns(matrix_header: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        column for column in matrix_header if column not in _SOURCE_MATRIX_META
    )


def _rows_by_family(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    return {
        text_value(row.get("feature_family_id")): row
        for row in rows
        if text_value(row.get("feature_family_id"))
    }


def _rows_by_key(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        family_id = text_value(row.get("feature_family_id"))
        sample_id = text_value(row.get("sample_stem") or row.get("sample_id"))
        if family_id and sample_id:
            by_key[(family_id, sample_id)] = row
    return by_key


def _expanded_candidates_by_key(
    rows: Sequence[Mapping[str, str]],
) -> tuple[_ExpandedPeakCandidate, ...]:
    candidates: dict[tuple[str, str, str], _ExpandedPeakCandidate] = {}
    for row in rows:
        family_id = text_value(row.get("feature_family_id"))
        sample_id = text_value(row.get("sample_id") or row.get("sample_stem"))
        peak_hypothesis_id = text_value(row.get("peak_hypothesis_id"))
        mode_id = text_value(row.get("mode_id")) or _selected_mode_id(
            peak_hypothesis_id
        )
        start_rt = _float_or_none(row.get("candidate_peak_start_rt"))
        end_rt = _float_or_none(row.get("candidate_peak_end_rt"))
        peak_rt = _float_or_none(row.get("candidate_peak_rt"))
        peak_height = _float_or_none(row.get("candidate_peak_height"))
        area = _float_or_none(row.get("candidate_area"))
        if not (
            family_id
            and sample_id
            and peak_hypothesis_id
            and mode_id
            and start_rt is not None
            and end_rt is not None
            and peak_rt is not None
            and peak_height is not None
            and area is not None
        ):
            continue
        key = (family_id, sample_id, peak_hypothesis_id)
        candidate = _ExpandedPeakCandidate(
            feature_family_id=family_id,
            sample_id=sample_id,
            peak_hypothesis_id=peak_hypothesis_id,
            mode_id=mode_id,
            start_rt=start_rt,
            end_rt=end_rt,
            peak_rt=peak_rt,
            peak_height=peak_height,
            area=area,
            source_artifact=text_value(row.get("candidate_value_source")),
            peak_hypothesis_status=_default(
                row.get("peak_hypothesis_status"),
                "raw_mode_review_only",
            ),
            product_selection_action=_default(
                row.get("product_selection_action"),
                "require_raw_mode_review",
            ),
            product_selection_blocker=_default(
                row.get("product_selection_blocker"),
                "raw_mode_review_only",
            ),
            evidence_consistency_status=_default(
                row.get("evidence_consistency_status"),
                "review_only",
            ),
            split_readiness_status=_default(
                row.get("split_readiness_status"),
                "review_required",
            ),
            consistency_blockers=text_value(row.get("consistency_blockers")),
            matrix_value_effect=_default(row.get("matrix_value_effect"), "written"),
            reason=_default(
                row.get("reason"),
                "raw_overlay_multi_peak_candidate_enumerated",
            ),
            candidate_value_basis=_default(
                row.get("candidate_value_basis"),
                "raw_overlay_window_trapezoid_area",
            ),
        )
        existing = candidates.get(key)
        if existing is None or candidate.peak_height > existing.peak_height:
            candidates[key] = candidate
    return tuple(
        candidates[key]
        for key in sorted(
            candidates,
            key=lambda item: (item[0], item[2], item[1]),
        )
    )


def _best_cells_by_key(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    best: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        family_id = text_value(row.get("feature_family_id"))
        sample_id = text_value(row.get("sample_stem"))
        if not family_id or not sample_id:
            continue
        key = (family_id, sample_id)
        if key not in best or _cell_sort_key(row) > _cell_sort_key(best[key]):
            best[key] = row
    return best


def _cell_sort_key(row: Mapping[str, str]) -> tuple[int, float]:
    status_priority = {
        "detected": 4,
        "rescued": 3,
        "supported_rescue": 3,
        "provisional": 2,
    }.get(text_value(row.get("status")), 1)
    return status_priority, _float_or_zero(row.get("area"))


def _assignment_keys(
    matrix_by_family: Mapping[str, Mapping[str, str]],
    cells_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    peak_hypotheses_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    *,
    sample_columns: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    del cells_by_key
    keys: set[tuple[str, str]] = set(peak_hypotheses_by_key)
    keys.update(peak_hypotheses_by_key)
    for family_id, row in matrix_by_family.items():
        for sample_id in sample_columns:
            if text_value(row.get(sample_id)):
                keys.add((family_id, sample_id))
    return tuple(sorted(keys))


def _new_matrix_row(
    peak_hypothesis_id: str,
    *,
    family_id: str,
    row_identity_basis: str,
    review_row: Mapping[str, str],
    sample_columns: Sequence[str],
) -> dict[str, str]:
    row = {
        "peak_hypothesis_id": peak_hypothesis_id,
        "feature_family_id": family_id,
        "candidate_container_id": family_id,
        "row_identity_basis": row_identity_basis,
        "legacy_rt_row_context_id": "",
        "neutral_loss_tag": text_value(review_row.get("neutral_loss_tag")),
        "family_center_mz": text_value(review_row.get("family_center_mz")),
        "family_center_rt": text_value(review_row.get("family_center_rt")),
    }
    row.update({sample: "" for sample in sample_columns})
    validate_row_tokens(row)
    return row


def _projection_id(family_id: str) -> str:
    return f"{family_id}::family_projection"


def _append_unique(row: dict[str, str], column: str, value: str) -> None:
    if not value:
        return
    existing = tuple(part for part in row.get(column, "").split(";") if part)
    if value not in existing:
        row[column] = ";".join((*existing, value))


def _select_conflicting_matrix_value(existing: str, incoming: str) -> str:
    existing_value = _float_or_none(existing)
    incoming_value = _float_or_none(incoming)
    if existing_value is None or incoming_value is None:
        return existing
    return incoming if incoming_value > existing_value else existing


def _has_sample_value(row: Mapping[str, str], sample_columns: Sequence[str]) -> bool:
    return any(text_value(row.get(sample)) for sample in sample_columns)


def _inventory_product_unit_scope(assignments: Sequence[Mapping[str, str]]) -> str:
    basis = _first_non_empty(assignments, "row_identity_basis")
    if basis == "family_projection_no_split_evidence":
        return "candidate_container"
    if any(row["construction_assignment_status"] == "assigned" for row in assignments):
        return "mode_level"
    return "review_only"


def _selected_mode_id(peak_hypothesis_id: str) -> str:
    if "::" not in peak_hypothesis_id:
        return ""
    return peak_hypothesis_id.split("::", 1)[1]


def _inventory_reason(counts: Counter[str], row_identity_basis: str) -> str:
    if counts["blocked"]:
        return "inventory_contains_hard_blocked_assignments"
    if counts["expanded_candidate"]:
        return "inventory_contains_raw_overlay_expanded_candidates"
    if row_identity_basis == "family_projection_no_split_evidence":
        return "inventory_contains_family_projection_assignments"
    if counts["recorded_no_source_matrix_value"]:
        return "inventory_records_candidate_without_source_matrix_value"
    return "inventory_contains_explicit_peak_hypothesis_assignments"


def _first_non_empty(
    rows: Sequence[Mapping[str, str]],
    column: str,
    *,
    default: str = "",
) -> str:
    for row in rows:
        value = text_value(row.get(column))
        if value:
            return value
    return default


def _unique_values(rows: Sequence[Mapping[str, str]], column: str) -> str:
    values: list[str] = []
    for row in rows:
        for part in _split_semicolon(text_value(row.get(column))):
            if part not in values:
                values.append(part)
    return ";".join(values)


def _format_counts(counter: Counter[str]) -> str:
    return ";".join(
        f"{key}:{counter[key]}" for key in sorted(counter) if key and counter[key]
    )


def _split_semicolon(value: str) -> tuple[str, ...]:
    return tuple(part for part in value.split(";") if part)


def _default(value: object, default: str) -> str:
    text = text_value(value)
    return text if text else default


def _first_float(row: Mapping[str, object], keys: Sequence[str]) -> float | None:
    for key in keys:
        parsed = _float_or_none(row.get(key))
        if parsed is not None:
            return parsed
    return None


def _float_or_none(value: object) -> float | None:
    text = text_value(value)
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _float_or_zero(value: object) -> float:
    return _float_or_none(value) or 0.0


def _float_values(value: object) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    values: list[float] = []
    for item in value:
        parsed = _float_or_none(item)
        if parsed is not None:
            values.append(parsed)
    return tuple(values)


def _trapezoid_area(points: Sequence[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    area = 0.0
    for (left_rt, left_y), (right_rt, right_y) in zip(
        points,
        points[1:],
        strict=False,
    ):
        width = right_rt - left_rt
        if width <= 0:
            continue
        area += width * (left_y + right_y) / 2.0
    return area


def _format_number(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.6g}"


def _reject_source_overwrite(
    *,
    output_paths: Sequence[Path],
    source_paths: Sequence[Path],
) -> None:
    output_resolved = {path.resolve() for path in output_paths}
    source_resolved = {path.resolve() for path in source_paths}
    overlap = sorted(str(path) for path in output_resolved & source_resolved)
    if overlap:
        raise ValueError(
            "PeakHypothesis construction output would overwrite source alignment "
            "artifacts; write to a separate directory or pass "
            f"--allow-overwrite-source. Overlap: {', '.join(overlap)}"
        )
