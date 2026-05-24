from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RAW_AREA_RATIO_MIN = 0.80


RAW_AREA_RATIO_MAX = 1.25


HIGH_UNCERTAINTY_FRACTION = 0.20


LOW_BASELINE_FRACTION = 0.30


BOUNDARY_DELTA_CONCERN_MIN = 0.10


ROW_FIELDS = (
    "sample",
    "target_label",
    "role",
    "targeted_candidate_id",
    "untargeted_family_id",
    "target_mz",
    "untargeted_family_mz",
    "targeted_area",
    "untargeted_area",
    "raw_area_ratio",
    "targeted_baseline_area",
    "untargeted_baseline_area",
    "baseline_area_ratio",
    "targeted_uncertainty_fraction",
    "untargeted_uncertainty_fraction",
    "targeted_baseline_fraction",
    "untargeted_baseline_fraction",
    "boundary_delta_start_min",
    "boundary_delta_end_min",
    "boundary_alternative_area_ratio",
    "targeted_region_verdict",
    "untargeted_region_verdict",
    "targeted_local_mixture_verdict",
    "untargeted_local_mixture_verdict",
    "evidence_spine_mismatch_reason",
    "integration_bucket",
    "integration_reason",
)


SUMMARY_FIELDS = (
    "rows_checked",
    "bucket_counts",
    "missing_alignment_match_count",
    "integration_context_incomplete_count",
    "unexplained_area_mismatch_count",
)


@dataclass(frozen=True)
class AreaIntegrationUncertaintyOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class EvidenceRow:
    sample: str
    target_label: str
    role: str
    targeted_candidate_id: str
    untargeted_family_id: str
    target_mz: float | None
    untargeted_family_mz: float | None
    targeted_area: float | None
    untargeted_area: float | None
    raw_area_ratio: float | None
    boundary_delta_start_min: float | None
    boundary_delta_end_min: float | None
    targeted_region_verdict: str
    untargeted_region_verdict: str
    targeted_local_mixture_verdict: str
    untargeted_local_mixture_verdict: str
    mismatch_reason: str


@dataclass(frozen=True)
class TargetedAudit:
    sample: str
    target_label: str
    candidate_id: str
    area: float | None
    baseline_area: float | None
    area_uncertainty: float | None
    uncertainty_fraction: float | None
    baseline_fraction: float | None


@dataclass(frozen=True)
class AlignmentIntegrationAudit:
    family_id: str
    sample: str
    area: float | None
    baseline_area: float | None
    area_uncertainty: float | None
    uncertainty_fraction: float | None
    baseline_fraction: float | None


@dataclass(frozen=True)
class AreaIntegrationRow:
    sample: str
    target_label: str
    role: str
    targeted_candidate_id: str
    untargeted_family_id: str
    target_mz: float | None
    untargeted_family_mz: float | None
    targeted_area: float | None
    untargeted_area: float | None
    raw_area_ratio: float | None
    targeted_baseline_area: float | None
    untargeted_baseline_area: float | None
    baseline_area_ratio: float | None
    targeted_uncertainty_fraction: float | None
    untargeted_uncertainty_fraction: float | None
    targeted_baseline_fraction: float | None
    untargeted_baseline_fraction: float | None
    boundary_delta_start_min: float | None
    boundary_delta_end_min: float | None
    boundary_alternative_area_ratio: float | None
    targeted_region_verdict: str
    untargeted_region_verdict: str
    targeted_local_mixture_verdict: str
    untargeted_local_mixture_verdict: str
    evidence_spine_mismatch_reason: str
    integration_bucket: str
    integration_reason: str


@dataclass(frozen=True)
class AreaIntegrationSummary:
    rows_checked: int
    bucket_counts: str
    missing_alignment_match_count: int
    integration_context_incomplete_count: int
    unexplained_area_mismatch_count: int


@dataclass(frozen=True)
class AreaIntegrationUncertaintyResult:
    summary: AreaIntegrationSummary
    rows: tuple[AreaIntegrationRow, ...]
