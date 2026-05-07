from dataclasses import dataclass
from typing import Literal

PeakStatus = Literal["OK", "NO_SIGNAL", "WINDOW_TOO_SHORT", "PEAK_NOT_FOUND"]
LocalMinimumQualityFlag = Literal[
    "edge_clipped",
    "too_broad",
    "too_short",
    "low_scan_count",
    "low_top_edge_ratio",
    "low_scan_support",
    "low_trace_continuity",
    "poor_edge_recovery",
]


@dataclass(frozen=True)
class PeakResult:
    rt: float
    intensity: float
    intensity_smoothed: float
    area: float
    peak_start: float
    peak_end: float


@dataclass(frozen=True)
class PeakCandidate:
    peak: PeakResult
    selection_apex_rt: float
    selection_apex_intensity: float
    selection_apex_index: int
    raw_apex_rt: float
    raw_apex_intensity: float
    raw_apex_index: int
    prominence: float
    quality_flags: tuple[LocalMinimumQualityFlag, ...] = ()
    region_scan_count: int | None = None
    region_duration_min: float | None = None
    region_edge_ratio: float | None = None
    region_trace_continuity: float | None = None


@dataclass(frozen=True)
class LocalMinimumRegionQuality:
    flags: tuple[LocalMinimumQualityFlag, ...]
    scan_count: int
    duration_min: float
    edge_ratio: float | None
    trace_continuity: float | None


@dataclass(frozen=True)
class PeakCandidatesResult:
    status: PeakStatus
    candidates: tuple[PeakCandidate, ...]
    n_points: int
    max_smoothed: float | None
    n_prominent_peaks: int


@dataclass(frozen=True)
class PeakDetectionResult:
    status: PeakStatus
    peak: PeakResult | None
    n_points: int
    max_smoothed: float | None
    n_prominent_peaks: int
    candidates: tuple[PeakCandidate, ...] = ()
    confidence: str | None = None
    reason: str | None = None
    severities: tuple[tuple[int, str], ...] = ()
