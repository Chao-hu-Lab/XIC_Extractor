"""Shared models and thresholds for family MS1 overlay diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REQUIRED_ALIGNMENT_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "height",
    "peak_start_rt",
    "peak_end_rt",
)

APEX_ALIGN_HALF_WINDOW_MIN = 0.35
APEX_ALIGN_GRID_SIZE = 175
GLOBAL_APEX_CONFLICT_DELTA_MIN = 0.20
GLOBAL_APEX_REVIEW_FRACTION_MIN = 0.25
LOCAL_APEX_SUPPORT_DELTA_MIN = 0.05
SHAPE_SUPPORT_MIN = 0.50
MS1_ASSESSABLE_COVERAGE_MIN = 0.70
LOW_LOCAL_TO_GLOBAL_RATIO = 0.50
DDA_TRIGGER_HEIGHT_RATIO_MIN = 1.25
DDA_TRIGGER_SHAPE_SUPPORT_FRACTION_MIN = 0.50


@dataclass(frozen=True)
class FamilyCell:
    sample_stem: str
    status: str
    area: float | None
    height: float | None
    apex_rt: float | None
    peak_start_rt: float | None
    peak_end_rt: float | None
    region_shadow_verdict: str
    source_candidate_id: str


@dataclass(frozen=True)
class TraceOverlayRow:
    sample_stem: str
    status: str
    group: str
    cell_area: float | None
    cell_height: float | None
    cell_apex_rt: float | None
    cell_start_rt: float | None
    cell_end_rt: float | None
    trace_max_intensity: float
    trace_apex_rt: float | None
    region_shadow_verdict: str
    source_candidate_id: str
    rt: tuple[float, ...]
    intensity: tuple[float, ...]


@dataclass(frozen=True)
class FamilyMs1OverlayOutputs:
    png_path: Path
    pdf_path: Path
    summary_tsv: Path
    trace_data_json: Path
