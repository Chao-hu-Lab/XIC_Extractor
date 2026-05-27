from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_FOCUS_LABELS = (
    "15N5-8-oxodG",
    "d3-N6-medA",
    "5-medC",
    "5-hmdC",
)


ROW_FIELDS = (
    "sample",
    "target_label",
    "role",
    "targeted_candidate_id",
    "untargeted_family_id",
    "target_mz",
    "untargeted_family_mz",
    "mz_delta_ppm",
    "trace_scan_count",
    "rt_window_min",
    "targeted_selected_rt",
    "untargeted_selected_rt",
    "rt_delta_min",
    "targeted_boundary_start",
    "targeted_boundary_end",
    "untargeted_boundary_start",
    "untargeted_boundary_end",
    "boundary_delta_start_min",
    "boundary_delta_end_min",
    "targeted_area",
    "untargeted_area",
    "area_ratio_untargeted_to_targeted",
    "baseline_corrected_area_available",
    "targeted_region_verdict",
    "untargeted_region_verdict",
    "targeted_local_mixture_verdict",
    "untargeted_local_mixture_verdict",
    "mismatch_reason",
)


SUMMARY_FIELDS = (
    "rows_checked",
    "matched_rows",
    "consistent_rows",
    "mismatch_rows",
    "missing_alignment_rows",
    "focused_target_labels",
    "included_istd_rows",
    "mismatch_reason_counts",
)


@dataclass(frozen=True)
class EvidenceSpineConsistencyOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class TargetedCandidate:
    sample: str
    target_label: str
    role: str
    candidate_id: str
    rt: float | None
    left: float | None
    right: float | None
    area: float | None
    baseline_area: float | None
    scan_count: int | None


@dataclass(frozen=True)
class TargetedShadow:
    shadow_verdict: str
    local_mixture_diagnostic: str


@dataclass(frozen=True)
class AlignmentCell:
    sample: str
    family_id: str
    status: str
    mz: float | None
    rt: float | None
    area: float | None
    left: float | None
    right: float | None
    region_verdict: str
    local_mixture_diagnostic: str
    reason: str = ""


@dataclass(frozen=True)
class ConsistencyRow:
    sample: str
    target_label: str
    role: str
    targeted_candidate_id: str
    untargeted_family_id: str
    target_mz: float | None
    untargeted_family_mz: float | None
    mz_delta_ppm: float | None
    trace_scan_count: int | None
    rt_window_min: str
    targeted_selected_rt: float | None
    untargeted_selected_rt: float | None
    rt_delta_min: float | None
    targeted_boundary_start: float | None
    targeted_boundary_end: float | None
    untargeted_boundary_start: float | None
    untargeted_boundary_end: float | None
    boundary_delta_start_min: float | None
    boundary_delta_end_min: float | None
    targeted_area: float | None
    untargeted_area: float | None
    area_ratio_untargeted_to_targeted: float | None
    baseline_corrected_area_available: bool
    targeted_region_verdict: str
    untargeted_region_verdict: str
    targeted_local_mixture_verdict: str
    untargeted_local_mixture_verdict: str
    mismatch_reason: str


@dataclass(frozen=True)
class ConsistencySummary:
    rows_checked: int
    matched_rows: int
    consistent_rows: int
    mismatch_rows: int
    missing_alignment_rows: int
    focused_target_labels: str
    included_istd_rows: int
    mismatch_reason_counts: str


@dataclass(frozen=True)
class EvidenceSpineConsistencyResult:
    summary: ConsistencySummary
    rows: tuple[ConsistencyRow, ...]
