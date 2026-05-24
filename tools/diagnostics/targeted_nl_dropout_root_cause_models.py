"""Models and constants for targeted NL dropout root-cause audit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_RELIABILITY_COLUMNS = (
    "sample_name",
    "target_label",
    "role",
    "reliability_state",
    "risk_reasons",
)

_CANDIDATE_COLUMNS = (
    "sample_name",
    "target_label",
    "resolver_mode",
    "candidate_id",
    "proposal_sources",
    "rt_apex_min",
    "selected",
    "confidence",
    "raw_score",
    "support_labels",
    "concern_labels",
    "quality_flags",
    "ms2_present",
    "nl_match",
    "nl_status",
    "best_loss_ppm",
    "best_ms2_scan_rt_min",
    "apex_ms2_delta_min",
    "best_product_base_ratio",
    "trigger_scan_count",
    "strict_nl_scan_count",
    "ms2_alignment_source",
)

_OPTIONAL_CANDIDATE_COLUMNS = (
    "diagnostic_product_absence_reason",
    "nearest_product_loss_ppm",
    "nearest_product_base_ratio",
    "nearest_product_mz",
)

_SUMMARY_COLUMNS = (
    "rows_checked",
    "review_positive_count",
    "included_count",
    "missing_candidate_count",
    "bucket_counts",
    "target_counts",
    "product_absence_reason_counts",
)

_ROW_COLUMNS = (
    "sample_name",
    "target_label",
    "target_mz",
    "role",
    "reliability_state",
    "targeted_risk_reasons",
    "resolver_mode",
    "selected_candidate_id",
    "selected_rt_apex_min",
    "selected_raw_score",
    "selected_confidence",
    "proposal_sources",
    "support_labels",
    "concern_labels",
    "quality_flags",
    "ms2_present",
    "nl_match",
    "nl_status",
    "best_loss_ppm",
    "best_ms2_scan_rt_min",
    "apex_ms2_delta_min",
    "best_product_base_ratio",
    "trigger_scan_count",
    "strict_nl_scan_count",
    "ms2_alignment_source",
    "diagnostic_product_absence_reason",
    "nearest_product_loss_ppm",
    "nearest_product_base_ratio",
    "nearest_product_mz",
    "root_cause_bucket",
    "root_cause_reason",
)

_HARD_CONFLICT_LABELS = frozenset(
    {
        "hard_quality_flag",
        "hard_nl_conflict",
        "low_scan_support",
        "rt_centrality_poor",
        "shape_poor",
        "edge_clipped",
    }
)
_SOFT_TRACE_QUALITY_FLAGS = frozenset({"low_trace_continuity", "poor_edge_recovery"})
_BLOCKING_TRACE_QUALITY_FLAGS = frozenset({"low_scan_support"})


@dataclass(frozen=True)
class TargetedNLDropoutRootCauseOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class ReliabilityRow:
    sample_name: str
    target_label: str
    role: str
    reliability_state: str
    risk_reasons: tuple[str, ...]


@dataclass(frozen=True)
class CandidateRow:
    sample_name: str
    target_label: str
    resolver_mode: str
    candidate_id: str
    proposal_sources: tuple[str, ...]
    rt_apex_min: float | None
    selected: bool
    confidence: str
    raw_score: float | None
    support_labels: tuple[str, ...]
    concern_labels: tuple[str, ...]
    quality_flags: tuple[str, ...]
    ms2_present: bool | None
    nl_match: bool | None
    nl_status: str
    best_loss_ppm: float | None
    best_ms2_scan_rt_min: float | None
    apex_ms2_delta_min: float | None
    best_product_base_ratio: float | None
    trigger_scan_count: int | None
    strict_nl_scan_count: int | None
    ms2_alignment_source: str
    diagnostic_product_absence_reason: str
    nearest_product_loss_ppm: float | None
    nearest_product_base_ratio: float | None
    nearest_product_mz: float | None


@dataclass(frozen=True)
class RootCauseRow:
    sample_name: str
    target_label: str
    target_mz: float | None
    role: str
    reliability_state: str
    targeted_risk_reasons: str
    resolver_mode: str
    selected_candidate_id: str
    selected_rt_apex_min: float | None
    selected_raw_score: float | None
    selected_confidence: str
    proposal_sources: str
    support_labels: str
    concern_labels: str
    quality_flags: str
    ms2_present: bool | None
    nl_match: bool | None
    nl_status: str
    best_loss_ppm: float | None
    best_ms2_scan_rt_min: float | None
    apex_ms2_delta_min: float | None
    best_product_base_ratio: float | None
    trigger_scan_count: int | None
    strict_nl_scan_count: int | None
    ms2_alignment_source: str
    diagnostic_product_absence_reason: str
    nearest_product_loss_ppm: float | None
    nearest_product_base_ratio: float | None
    nearest_product_mz: float | None
    root_cause_bucket: str
    root_cause_reason: str


@dataclass(frozen=True)
class RootCauseSummary:
    rows_checked: int
    review_positive_count: int
    included_count: int
    missing_candidate_count: int
    bucket_counts: str
    target_counts: str
    product_absence_reason_counts: str


@dataclass(frozen=True)
class TargetedNLDropoutRootCauseResult:
    summary: RootCauseSummary
    rows: tuple[RootCauseRow, ...]
