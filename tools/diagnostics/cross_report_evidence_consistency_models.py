from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_RELIABILITY_COLUMNS = (
    "sample_name",
    "target_label",
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
)


_SUMMARY_COLUMNS = (
    "rows_checked",
    "consistent_count",
    "mismatch_count",
    "missing_candidate_count",
    "missing_reliability_count",
    "issue_counts",
)


_ROW_COLUMNS = (
    "sample_name",
    "target_label",
    "target_mz",
    "reliability_state",
    "targeted_risk_reasons",
    "resolver_mode",
    "selected_candidate_id",
    "selected_rt_apex_min",
    "selected_raw_score",
    "selected_confidence",
    "targeted_area_to_median_ratio",
    "candidate_support_labels",
    "candidate_concern_labels",
    "candidate_consistency_labels",
    "consistency_status",
    "issue_type",
    "reason",
)


@dataclass(frozen=True)
class CrossReportConsistencyOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class ReliabilityRow:
    sample_name: str
    target_label: str
    reliability_state: str
    risk_reasons: tuple[str, ...]
    area_to_target_median_ratio: float | None = None


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


@dataclass(frozen=True)
class ConsistencyRow:
    sample_name: str
    target_label: str
    target_mz: float | None
    reliability_state: str
    targeted_risk_reasons: str
    resolver_mode: str
    selected_candidate_id: str
    selected_rt_apex_min: float | None
    selected_raw_score: float | None
    selected_confidence: str
    targeted_area_to_median_ratio: float | None
    candidate_support_labels: str
    candidate_concern_labels: str
    candidate_consistency_labels: str
    consistency_status: str
    issue_type: str
    reason: str


@dataclass(frozen=True)
class ConsistencySummary:
    rows_checked: int
    consistent_count: int
    mismatch_count: int
    missing_candidate_count: int
    missing_reliability_count: int
    issue_counts: str


@dataclass(frozen=True)
class ConsistencyResult:
    summary: ConsistencySummary
    rows: tuple[ConsistencyRow, ...]
