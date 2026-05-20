"""Models and constants for targeted peak reliability audit."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

ReliabilityState = Literal[
    "benchmark_eligible",
    "targeted_review_positive",
    "targeted_review",
    "targeted_negative",
]

ROWS_COLUMNS = (
    "sample_name",
    "target_label",
    "role",
    "rt",
    "area",
    "confidence",
    "nl",
    "prior_rt",
    "prior_source",
    "total_severity",
    "quality_flags",
    "reliability_state",
    "risk_reasons",
    "known_exception",
    "target_area_median",
    "area_to_target_median_ratio",
    "weak_area_threshold_ratio",
)

SUMMARY_COLUMNS = (
    "target_label",
    "role",
    "benchmark_eligible_count",
    "targeted_review_positive_count",
    "targeted_review_count",
    "targeted_negative_count",
    "top_risk_reasons",
    "known_exception",
)

_PEAK_CANDIDATE_COLUMNS = (
    "sample_name",
    "target_label",
    "proposal_sources",
    "selected",
    "raw_score",
    "support_labels",
    "concern_labels",
    "quality_flags",
    "ms2_present",
    "nl_match",
)

_WEAK_AREA_THRESHOLD_RATIO = 0.05
_SOFT_TRACE_QUALITY_FLAGS = {"low_trace_continuity", "poor_edge_recovery"}
_BLOCKING_TRACE_QUALITY_FLAGS = {"low_scan_support"}
_COHERENT_ISTD_SOFT_TRACE_MIN_RAW_SCORE = 35.0


@dataclass(frozen=True)
class TargetedReliabilityOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class TargetedReliabilityRow:
    sample_name: str
    target_label: str
    role: str
    rt: float | None
    area: float | None
    confidence: str
    nl: str
    prior_rt: float | None
    prior_source: str
    total_severity: int | None
    quality_flags: str
    reliability_state: ReliabilityState
    risk_reasons: tuple[str, ...]
    known_exception: str
    target_area_median: float | None = None
    area_to_target_median_ratio: float | None = None
    weak_area_threshold_ratio: float | None = None


@dataclass(frozen=True)
class TargetedReliabilitySummary:
    target_label: str
    role: str
    benchmark_eligible_count: int
    targeted_review_positive_count: int
    targeted_review_count: int
    targeted_negative_count: int
    top_risk_reasons: str
    known_exception: str


@dataclass(frozen=True)
class TargetedReliabilityResult:
    rows: tuple[TargetedReliabilityRow, ...]
    summaries: tuple[TargetedReliabilitySummary, ...]

    @property
    def benchmark_eligible_count(self) -> int:
        return sum(row.reliability_state == "benchmark_eligible" for row in self.rows)

    @property
    def targeted_review_count(self) -> int:
        return sum(row.reliability_state == "targeted_review" for row in self.rows)

    @property
    def targeted_review_positive_count(self) -> int:
        return sum(
            row.reliability_state == "targeted_review_positive" for row in self.rows
        )

    @property
    def targeted_negative_count(self) -> int:
        return sum(row.reliability_state == "targeted_negative" for row in self.rows)


@dataclass(frozen=True)
class _TargetedInputRow:
    sample_name: str
    target_label: str
    role: str
    rt: float | None
    area: float | None
    confidence: str
    nl: str
    reason: str


@dataclass(frozen=True)
class _ScoreBreakdown:
    prior_rt: float | None
    prior_source: str
    total_severity: int | None
    quality_flags: str


@dataclass(frozen=True)
class _CandidateEvidence:
    support_labels: tuple[str, ...]
    concern_labels: tuple[str, ...]
    proposal_sources: tuple[str, ...]
    quality_flags: tuple[str, ...]
    ms2_present: bool | None
    nl_match: bool | None
    raw_score: float | None
    diagnostic_product_absence_reason: str = ""


@dataclass(frozen=True)
class _AreaContext:
    target_area_median: float
    area_to_target_median_ratio: float
    weak_area_threshold_ratio: float = _WEAK_AREA_THRESHOLD_RATIO

    @property
    def weak_area(self) -> bool:
        return self.area_to_target_median_ratio < self.weak_area_threshold_ratio


class _WorksheetLike(Protocol):
    def iter_rows(
        self,
        *,
        values_only: bool = False,
    ) -> Iterator[tuple[object, ...]]: ...
