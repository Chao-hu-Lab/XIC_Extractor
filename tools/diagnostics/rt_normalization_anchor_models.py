"""Models for the RT normalization anchor diagnostic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xic_extractor.alignment.rt_normalization import AnchorResidual, SampleRtModel


@dataclass(frozen=True)
class RtNormalizationOutputs:
    summary_tsv: Path
    sample_tsv: Path
    anchor_tsv: Path
    leave_one_out_tsv: Path
    family_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class AnchorDefinition:
    label: str
    role: str
    neutral_loss_da: float
    reference_rt_min: float


@dataclass(frozen=True)
class AlignmentFeature:
    feature_family_id: str
    include_in_primary_matrix: bool
    family_center_mz: float | None
    family_center_rt: float | None


@dataclass(frozen=True)
class AlignmentCell:
    feature_family_id: str
    sample_stem: str
    apex_rt: float


@dataclass(frozen=True)
class FamilyRtSummary:
    feature_family_id: str
    include_in_primary_matrix: bool
    family_center_mz: float | None
    family_center_rt: float | None
    raw_cell_count: int
    modelled_cell_count: int
    unmodelled_cell_count: int
    raw_rt_range_min: float | None
    normalized_rt_range_min: float | None
    rt_range_improvement_min: float | None
    raw_rt_median_min: float | None
    normalized_rt_median_min: float | None
    rt_band: str
    normalized_rt_support: str
    anchor_scope: str
    anchor_support_level: str
    local_residual_window_min: float | None


@dataclass(frozen=True)
class LeaveOneAnchorOutSummary:
    target_label: str
    evaluated_count: int
    median_abs_error_min: float | None
    p95_abs_error_min: float | None
    max_abs_error_min: float | None
    status: str


@dataclass(frozen=True)
class SampleAnchorContext:
    observed_min_rt: float
    observed_max_rt: float
    abs_residuals: tuple[float, ...]


@dataclass(frozen=True)
class RtNormalizationResult:
    overall_status: str
    reference_source: str
    model_type: str
    anchor_residual_max_min: float
    anchor_label_count: int
    sample_count: int
    modelled_sample_count: int
    unmodelled_sample_count: int
    excluded_anchor_count: int
    family_count: int
    families_improved_count: int
    families_worsened_count: int
    median_raw_rt_range_min: float | None
    median_normalized_rt_range_min: float | None
    median_rt_range_improvement_min: float | None
    rt_band_summary: dict[str, dict[str, int]]
    leave_one_anchor_out: tuple[LeaveOneAnchorOutSummary, ...]
    samples: tuple[SampleRtModel, ...]
    anchors: tuple[AnchorResidual, ...]
    families: tuple[FamilyRtSummary, ...]
