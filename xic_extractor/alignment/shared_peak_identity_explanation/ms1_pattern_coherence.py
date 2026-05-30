from __future__ import annotations

import json
import statistics
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.diagnostics.diagnostic_io import read_tsv_required, text_value, write_tsv
from xic_extractor.alignment.config import AlignmentConfig

from .machine_evidence_support import (
    MATRIX_RT_DRIFT_POLICY_REQUIRED_COLUMNS,
    MS1_PATTERN_COHERENCE_REQUIRED_COLUMNS,
)

MS1_PATTERN_COHERENCE_OPTIONAL_COLUMNS = (
    "shape_metric_source",
    "family_ms1_overlay_verdict",
    "cell_height",
    "local_window_max_intensity",
    "trace_max_intensity",
    "cell_to_local_window_max_ratio",
    "local_window_to_global_max_ratio",
    "local_window_apex_delta_sec",
    "global_trace_apex_delta_sec",
    "family_ms1_overlay_trace_data_json",
)
MS1_PATTERN_COHERENCE_COLUMNS = (
    *MS1_PATTERN_COHERENCE_REQUIRED_COLUMNS,
    *MS1_PATTERN_COHERENCE_OPTIONAL_COLUMNS,
)

_ALIGNMENT_CELL_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "rt_delta_sec",
    "trace_quality",
    "scan_support_score",
)
_PRESENT_STATUSES = frozenset(
    {
        "detected",
        "rescued",
        "selected",
        "present",
        "duplicate_assigned",
    }
)
_SUPPORTIVE_STATUSES = frozenset({"detected", "rescued", "selected", "present"})
_MIN_REFERENCE_PEAKS = 3
_MIN_BOUNDARY_WIDTH_SIMILARITY = 0.35
_SUPPORTIVE_BOUNDARY_WIDTH_SIMILARITY = 0.55
_HIGH_LOCAL_INTERFERENCE_SCORE = 0.80
_OVERLAY_SHAPE_SUPPORT_MIN = 0.50
_OVERLAY_LOCAL_DOMINANCE_MIN = 0.50
_OVERLAY_LOCAL_APEX_SUPPORT_SEC = 3.0


@dataclass(frozen=True)
class _PeakCell:
    feature_family_id: str
    sample_stem: str
    status: str
    apex_rt: float | None
    peak_start_rt: float | None
    peak_end_rt: float | None
    rt_delta_sec: float | None
    trace_quality: str
    scan_support_score: float | None

    @property
    def is_present(self) -> bool:
        return self.status in _PRESENT_STATUSES

    @property
    def has_boundary(self) -> bool:
        return (
            self.apex_rt is not None
            and self.peak_start_rt is not None
            and self.peak_end_rt is not None
            and self.peak_end_rt > self.peak_start_rt
        )

    @property
    def width_sec(self) -> float | None:
        if not self.has_boundary:
            return None
        if self.peak_start_rt is None or self.peak_end_rt is None:
            return None
        return max(0.0, (self.peak_end_rt - self.peak_start_rt) * 60.0)


@dataclass(frozen=True)
class _OverlayMetric:
    family_id: str
    sample_stem: str
    family_verdict: str
    shape_similarity: float | None
    cell_height: float | None
    local_window_max_intensity: float | None
    trace_max_intensity: float | None
    local_window_to_global_max_ratio: float | None
    local_window_apex_delta_sec: float | None
    global_trace_apex_delta_sec: float | None
    cell_apex_rt: float | None
    rt_min: float | None
    rt_max: float | None
    source_json: Path

    @property
    def cell_apex_inside_trace_window(self) -> bool:
        if self.cell_apex_rt is None or self.rt_min is None or self.rt_max is None:
            return True
        return self.rt_min <= self.cell_apex_rt <= self.rt_max


def build_ms1_pattern_coherence_rows(
    *,
    alignment_cells_tsv: Path,
    oracle_keys: Iterable[tuple[str, str]],
    matrix_rt_drift_policy_tsv: Path | None = None,
    family_ms1_overlay_trace_data_jsons: Sequence[Path] | None = None,
    config: AlignmentConfig | None = None,
) -> tuple[dict[str, str], ...]:
    """Build diagnostic-only MS1 boundary-constellation evidence.

    The current artifact set has peak apex and integration boundaries, but not
    raw trace vectors. Without RAW-backed overlay inputs this producer therefore
    emits a conservative sample-boundary constellation metric and leaves shape
    correlation empty. When family MS1 overlay JSON artifacts are supplied, the
    producer enriches matching rows with RAW-backed trace shape/local-window
    metrics from that existing diagnostic surface.
    """

    config = config or AlignmentConfig()
    cells = tuple(_peak_cell(row) for row in _read_cell_rows(alignment_cells_tsv))
    cell_by_key = {(cell.feature_family_id, cell.sample_stem): cell for cell in cells}
    cells_by_family = _group_cells(cells, key=lambda cell: cell.feature_family_id)
    cells_by_sample = _group_cells(cells, key=lambda cell: cell.sample_stem)
    matrix_drift = (
        _matrix_drift_by_key(
            read_tsv_required(
                matrix_rt_drift_policy_tsv,
                MATRIX_RT_DRIFT_POLICY_REQUIRED_COLUMNS,
            )
        )
        if matrix_rt_drift_policy_tsv is not None
        else {}
    )
    overlay_metrics = _overlay_metrics_by_key(
        family_ms1_overlay_trace_data_jsons or ()
    )

    rows = [
        _row_for_key(
            feature_family_id=feature_family_id,
            sample_stem=sample_stem,
            cell=cell_by_key.get((feature_family_id, sample_stem)),
            family_cells=cells_by_family.get(feature_family_id, ()),
            sample_cells=cells_by_sample.get(sample_stem, ()),
            matrix_drift_row=matrix_drift.get((feature_family_id, sample_stem)),
            overlay_metric=overlay_metrics.get((feature_family_id, sample_stem)),
            config=config,
        )
        for feature_family_id, sample_stem in oracle_keys
    ]
    return tuple(
        sorted(rows, key=lambda row: (row["feature_family_id"], row["sample_stem"]))
    )


def write_ms1_pattern_coherence_rows(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(path, rows, MS1_PATTERN_COHERENCE_COLUMNS, lineterminator="\n")


def _read_cell_rows(path: Path) -> tuple[Mapping[str, str], ...]:
    return read_tsv_required(path, _ALIGNMENT_CELL_COLUMNS)


def _peak_cell(row: Mapping[str, str]) -> _PeakCell:
    return _PeakCell(
        feature_family_id=text_value(row.get("feature_family_id")),
        sample_stem=text_value(row.get("sample_stem")),
        status=text_value(row.get("status")),
        apex_rt=_optional_float(row.get("apex_rt")),
        peak_start_rt=_optional_float(row.get("peak_start_rt")),
        peak_end_rt=_optional_float(row.get("peak_end_rt")),
        rt_delta_sec=_optional_float(row.get("rt_delta_sec")),
        trace_quality=text_value(row.get("trace_quality")),
        scan_support_score=_optional_float(row.get("scan_support_score")),
    )


def _group_cells(
    cells: Sequence[_PeakCell],
    *,
    key: Callable[[_PeakCell], str],
) -> dict[str, tuple[_PeakCell, ...]]:
    grouped: dict[str, list[_PeakCell]] = {}
    for cell in cells:
        grouped.setdefault(key(cell), []).append(cell)
    return {group_key: tuple(values) for group_key, values in grouped.items()}


def _matrix_drift_by_key(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, str], Mapping[str, str]]:
    return {(row["feature_family_id"], row["sample_stem"]): row for row in rows}


def _row_for_key(
    *,
    feature_family_id: str,
    sample_stem: str,
    cell: _PeakCell | None,
    family_cells: Sequence[_PeakCell],
    sample_cells: Sequence[_PeakCell],
    matrix_drift_row: Mapping[str, str] | None,
    overlay_metric: _OverlayMetric | None,
    config: AlignmentConfig,
) -> dict[str, str]:
    base = _base_row(feature_family_id, sample_stem)
    if cell is None:
        return {**base, "reason": "alignment_cell_missing"}
    if not cell.is_present:
        return {**base, "reason": "alignment_cell_not_present"}
    if not cell.has_boundary:
        return {**base, "reason": "alignment_cell_boundary_missing"}

    reference_cells = tuple(
        peer
        for peer in family_cells
        if peer.status in _SUPPORTIVE_STATUSES and peer.has_boundary
    )
    reference_count = len(reference_cells)
    median_width = _median_width(reference_cells)
    boundary_score = _boundary_width_similarity(cell.width_sec, median_width)
    apex_coherence_sec = _apex_coherence_sec(
        cell=cell,
        reference_cells=reference_cells,
        matrix_drift_row=matrix_drift_row,
    )
    drift_status = _drift_compatible_status(
        apex_coherence_sec=apex_coherence_sec,
        matrix_drift_row=matrix_drift_row,
        config=config,
    )
    local_count, local_interference = _local_interference(cell, sample_cells)
    stability_score = _relative_width_stability_score(reference_cells)
    status, reason = _status_and_reason(
        cell=cell,
        reference_count=reference_count,
        boundary_score=boundary_score,
        apex_coherence_sec=apex_coherence_sec,
        drift_status=drift_status,
        local_interference_score=local_interference,
        config=config,
    )
    row = {
        **base,
        "ms1_pattern_status": status,
        "ms1_pattern_evidence_level": (
            "sample_boundary_constellation"
            if status in {"supportive", "partial_support", "conflict"}
            else "not_available"
        ),
        "apex_coherence_sec": _format_float(apex_coherence_sec),
        "boundary_overlap_score": _format_float(boundary_score),
        "shape_correlation_score": "",
        "relative_pattern_stability_score": _format_float(stability_score),
        "local_interference_score": _format_float(local_interference),
        "constellation_peak_count": str(local_count + 1),
        "reference_peak_count": str(reference_count),
        "drift_compatible_status": drift_status,
        "reason": reason,
    }
    if overlay_metric is not None:
        row = _with_overlay_metric(row, overlay_metric)
    return row


def _base_row(feature_family_id: str, sample_stem: str) -> dict[str, str]:
    return {
        "feature_family_id": feature_family_id,
        "sample_stem": sample_stem,
        "ms1_pattern_status": "not_available",
        "ms1_pattern_evidence_level": "not_available",
        "apex_coherence_sec": "",
        "boundary_overlap_score": "",
        "shape_correlation_score": "",
        "relative_pattern_stability_score": "",
        "local_interference_score": "",
        "constellation_peak_count": "0",
        "reference_peak_count": "0",
        "drift_compatible_status": "not_available",
        "reason": "",
        "diagnostic_only": "TRUE",
        "shape_metric_source": "",
        "family_ms1_overlay_verdict": "",
        "cell_height": "",
        "local_window_max_intensity": "",
        "trace_max_intensity": "",
        "cell_to_local_window_max_ratio": "",
        "local_window_to_global_max_ratio": "",
        "local_window_apex_delta_sec": "",
        "global_trace_apex_delta_sec": "",
        "family_ms1_overlay_trace_data_json": "",
    }


def _median_width(cells: Sequence[_PeakCell]) -> float | None:
    widths = [width for cell in cells if (width := cell.width_sec) is not None]
    if not widths:
        return None
    return statistics.median(widths)


def _boundary_width_similarity(
    width_sec: float | None,
    median_width_sec: float | None,
) -> float | None:
    if width_sec is None or median_width_sec is None:
        return None
    larger = max(width_sec, median_width_sec)
    if larger <= 0:
        return None
    return max(0.0, min(width_sec, median_width_sec) / larger)


def _apex_coherence_sec(
    *,
    cell: _PeakCell,
    reference_cells: Sequence[_PeakCell],
    matrix_drift_row: Mapping[str, str] | None,
) -> float | None:
    corrected_delta = _optional_float(
        (matrix_drift_row or {}).get("drift_corrected_delta_sec")
    )
    if _matrix_drift_compatible(matrix_drift_row) and corrected_delta is not None:
        return abs(corrected_delta)
    if cell.rt_delta_sec is not None:
        return abs(cell.rt_delta_sec)
    apex_values = [
        peer.apex_rt
        for peer in reference_cells
        if peer.apex_rt is not None and peer is not cell
    ]
    if cell.apex_rt is None or not apex_values:
        return None
    return abs(cell.apex_rt - statistics.median(apex_values)) * 60.0


def _drift_compatible_status(
    *,
    apex_coherence_sec: float | None,
    matrix_drift_row: Mapping[str, str] | None,
    config: AlignmentConfig,
) -> str:
    if _matrix_drift_compatible(matrix_drift_row):
        return "compatible"
    if matrix_drift_row and matrix_drift_row.get("matrix_rt_drift_status") == (
        "drift_not_supported"
    ):
        return "conflict"
    if apex_coherence_sec is None:
        return "not_available"
    if apex_coherence_sec <= config.preferred_rt_sec:
        return "compatible"
    if apex_coherence_sec <= config.max_rt_sec:
        return "unmodeled_shift"
    return "conflict"


def _matrix_drift_compatible(row: Mapping[str, str] | None) -> bool:
    if not row:
        return False
    return (
        row.get("drift_compatible_status") == "compatible"
        and row.get("matrix_rt_drift_status") in {"rt_close", "drift_supported"}
    )


def _local_interference(
    cell: _PeakCell,
    sample_cells: Sequence[_PeakCell],
) -> tuple[int, float]:
    if (
        cell.peak_start_rt is None
        or cell.peak_end_rt is None
        or cell.apex_rt is None
    ):
        return 0, 0.0
    local_peers = [
        peer
        for peer in sample_cells
        if peer is not cell
        and peer.is_present
        and peer.has_boundary
        and peer.peak_start_rt is not None
        and peer.peak_end_rt is not None
        and _interval_overlap_fraction(
            cell.peak_start_rt,
            cell.peak_end_rt,
            peer.peak_start_rt,
            peer.peak_end_rt,
        )
        >= 0.5
    ]
    return len(local_peers), min(1.0, len(local_peers) / 25.0)


def _interval_overlap_fraction(
    left_start: float,
    left_end: float,
    right_start: float,
    right_end: float,
) -> float:
    overlap = max(0.0, min(left_end, right_end) - max(left_start, right_start))
    denominator = min(left_end - left_start, right_end - right_start)
    if denominator <= 0:
        return 0.0
    return overlap / denominator


def _relative_width_stability_score(cells: Sequence[_PeakCell]) -> float | None:
    widths = [width for cell in cells if (width := cell.width_sec) is not None]
    if len(widths) < 2:
        return None
    median_width = statistics.median(widths)
    if median_width <= 0:
        return None
    median_abs_deviation = statistics.median(
        abs(width - median_width) for width in widths
    )
    relative_deviation = median_abs_deviation / median_width
    return max(0.0, min(1.0, 1.0 - relative_deviation))


def _status_and_reason(
    *,
    cell: _PeakCell,
    reference_count: int,
    boundary_score: float | None,
    apex_coherence_sec: float | None,
    drift_status: str,
    local_interference_score: float,
    config: AlignmentConfig,
) -> tuple[str, str]:
    if drift_status == "conflict":
        return "conflict", "rt_or_matrix_drift_conflict"
    if apex_coherence_sec is not None and apex_coherence_sec > config.max_rt_sec:
        return "conflict", "apex_outside_max_rt_window"
    if boundary_score is None:
        return "inconclusive", "boundary_similarity_unavailable"
    if boundary_score < _MIN_BOUNDARY_WIDTH_SIMILARITY:
        return "inconclusive", "boundary_width_similarity_too_low"
    if reference_count < _MIN_REFERENCE_PEAKS:
        return "inconclusive", "insufficient_family_reference_peaks"
    if drift_status != "compatible":
        return "inconclusive", "rt_shift_requires_independent_drift_policy"
    if cell.status not in _SUPPORTIVE_STATUSES:
        return "partial_support", "non_primary_cell_status"
    if local_interference_score >= _HIGH_LOCAL_INTERFERENCE_SCORE:
        return "partial_support", "high_local_interference_context"
    if boundary_score >= _SUPPORTIVE_BOUNDARY_WIDTH_SIMILARITY:
        return "supportive", "alignment_cell_boundary_constellation_supported"
    return "partial_support", "boundary_constellation_partial"


def _overlay_metrics_by_key(
    paths: Sequence[Path],
) -> dict[tuple[str, str], _OverlayMetric]:
    metrics: dict[tuple[str, str], _OverlayMetric] = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        family_id = text_value(data.get("family_id"))
        if not family_id:
            raise ValueError(f"{path}: missing family_id")
        evidence_summary = data.get("evidence_summary")
        if not isinstance(evidence_summary, dict):
            evidence_summary = {}
        family_verdict = text_value(evidence_summary.get("family_verdict"))
        rt_min = _optional_float(data.get("rt_min"))
        rt_max = _optional_float(data.get("rt_max"))
        traces = data.get("traces")
        if not isinstance(traces, list):
            raise ValueError(f"{path}: missing traces array")
        for trace in traces:
            if not isinstance(trace, dict):
                continue
            sample_stem = text_value(trace.get("sample_stem"))
            if not sample_stem:
                continue
            metric = _OverlayMetric(
                family_id=family_id,
                sample_stem=sample_stem,
                family_verdict=family_verdict,
                shape_similarity=_optional_float(
                    trace.get("apex_aligned_shape_similarity")
                ),
                cell_height=_optional_float(trace.get("cell_height")),
                local_window_max_intensity=_optional_float(
                    trace.get("local_window_max_intensity")
                ),
                trace_max_intensity=_optional_float(trace.get("trace_max_intensity")),
                local_window_to_global_max_ratio=_optional_float(
                    trace.get("local_window_to_global_max_ratio")
                ),
                local_window_apex_delta_sec=_minutes_to_seconds(
                    _optional_float(trace.get("local_window_apex_delta_min"))
                ),
                global_trace_apex_delta_sec=_minutes_to_seconds(
                    _optional_float(trace.get("global_trace_apex_delta_min"))
                ),
                cell_apex_rt=_optional_float(trace.get("cell_apex_rt")),
                rt_min=rt_min,
                rt_max=rt_max,
                source_json=path,
            )
            metrics[(family_id, sample_stem)] = metric
    return metrics


def _with_overlay_metric(
    row: Mapping[str, str],
    metric: _OverlayMetric,
) -> dict[str, str]:
    enriched = {
        **row,
        "shape_correlation_score": _format_float(metric.shape_similarity),
        "shape_metric_source": (
            "family_ms1_overlay_raw_trace"
            if metric.shape_similarity is not None
            else "family_ms1_overlay_raw_trace_unscored"
        ),
        "family_ms1_overlay_verdict": metric.family_verdict,
        "cell_height": _format_float(metric.cell_height),
        "local_window_max_intensity": _format_float(
            metric.local_window_max_intensity
        ),
        "trace_max_intensity": _format_float(metric.trace_max_intensity),
        "cell_to_local_window_max_ratio": _format_float(
            _ratio_or_none(metric.cell_height, metric.local_window_max_intensity)
        ),
        "local_window_to_global_max_ratio": _format_float(
            metric.local_window_to_global_max_ratio
        ),
        "local_window_apex_delta_sec": _format_float(
            metric.local_window_apex_delta_sec
        ),
        "global_trace_apex_delta_sec": _format_float(
            metric.global_trace_apex_delta_sec
        ),
        "family_ms1_overlay_trace_data_json": str(metric.source_json),
    }
    if not metric.cell_apex_inside_trace_window:
        return {
            **enriched,
            "reason": _join_reason(
                enriched.get("reason", ""),
                "family_ms1_overlay_trace_window_does_not_cover_cell_apex",
            ),
        }
    if _overlay_lacks_complete_expected_peak(metric):
        return {
            **enriched,
            "ms1_pattern_status": "conflict",
            "ms1_pattern_evidence_level": "trace_constellation",
            "reason": "family_ms1_overlay_expected_window_lacks_complete_peak",
        }
    if _overlay_supports_shape(metric):
        if enriched.get("drift_compatible_status") == "conflict":
            return enriched
        status = (
            "supportive"
            if enriched.get("drift_compatible_status") == "compatible"
            else "partial_support"
        )
        reason = (
            "family_ms1_overlay_shape_supported"
            if status == "supportive"
            else "family_ms1_overlay_shape_supported_rt_policy_pending"
        )
        return {
            **enriched,
            "ms1_pattern_status": status,
            "ms1_pattern_evidence_level": "trace_constellation",
            "reason": reason,
        }
    if _overlay_shape_metric_inconclusive(metric):
        if enriched.get("drift_compatible_status") == "conflict":
            return enriched
        return {
            **enriched,
            "ms1_pattern_status": "partial_support",
            "ms1_pattern_evidence_level": "trace_constellation",
            "reason": "family_ms1_overlay_shape_metric_inconclusive_apex_or_height",
        }
    return enriched


def _overlay_supports_shape(metric: _OverlayMetric) -> bool:
    if metric.shape_similarity is None:
        return False
    if metric.shape_similarity < _OVERLAY_SHAPE_SUPPORT_MIN:
        return False
    if (
        metric.local_window_to_global_max_ratio is not None
        and metric.local_window_to_global_max_ratio < _OVERLAY_LOCAL_DOMINANCE_MIN
    ):
        return False
    if (
        metric.local_window_apex_delta_sec is not None
        and abs(metric.local_window_apex_delta_sec) > _OVERLAY_LOCAL_APEX_SUPPORT_SEC
    ):
        return False
    return metric.family_verdict == "ms1_shape_supports_family_backfill"


def _overlay_lacks_complete_expected_peak(metric: _OverlayMetric) -> bool:
    if not metric.cell_apex_inside_trace_window:
        return False
    if metric.local_window_to_global_max_ratio is not None:
        return metric.local_window_to_global_max_ratio < _OVERLAY_LOCAL_DOMINANCE_MIN
    return False


def _overlay_shape_metric_inconclusive(metric: _OverlayMetric) -> bool:
    if metric.family_verdict != "ms1_shape_supports_family_backfill":
        return False
    if (
        metric.local_window_to_global_max_ratio is not None
        and metric.local_window_to_global_max_ratio < _OVERLAY_LOCAL_DOMINANCE_MIN
    ):
        return False
    return (
        metric.shape_similarity is not None
        and metric.shape_similarity < _OVERLAY_SHAPE_SUPPORT_MIN
    ) or (
        metric.local_window_apex_delta_sec is not None
        and abs(metric.local_window_apex_delta_sec) > _OVERLAY_LOCAL_APEX_SUPPORT_SEC
    )


def _join_reason(left: str, right: str) -> str:
    if not left:
        return right
    if right in left.split(";"):
        return left
    return f"{left};{right}"


def _minutes_to_seconds(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 60.0


def _ratio_or_none(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _optional_float(value: object) -> float | None:
    text = text_value(value).strip("'")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6g}"
