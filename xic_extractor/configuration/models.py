from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExtractionConfig:
    data_dir: Path
    dll_dir: Path
    output_csv: Path
    diagnostics_csv: Path
    smooth_window: int
    smooth_polyorder: int
    peak_rel_height: float
    peak_min_prominence_ratio: float
    ms2_precursor_tol_da: float
    nl_min_intensity_ratio: float
    resolver_mode: str = "legacy_savgol"
    resolver_chrom_threshold: float = 0.05
    resolver_min_search_range_min: float = 0.08
    resolver_min_relative_height: float = 0.02
    resolver_min_absolute_height: float = 25.0
    resolver_min_ratio_top_edge: float = 1.7
    resolver_peak_duration_min: float = 0.0
    resolver_peak_duration_max: float = 2.0
    resolver_min_scans: int = 5
    count_no_ms2_as_detected: bool = False
    nl_rt_anchor_search_margin_min: float = 2.0
    nl_rt_anchor_half_window_min: float = 1.0
    nl_fallback_half_window_min: float = 2.0
    injection_order_source: Path | None = None
    rolling_window_size: int = 5
    dirty_matrix_mode: bool = False
    rt_prior_library_path: Path | None = None
    emit_score_breakdown: bool = False
    emit_review_report: bool = False
    keep_intermediate_csv: bool = False
    parallel_mode: str = "serial"
    parallel_workers: int = 1
    config_hash: str = ""


@dataclass(frozen=True)
class Target:
    label: str
    mz: float
    rt_min: float
    rt_max: float
    ppm_tol: float
    neutral_loss_da: float | None
    nl_ppm_warn: float | None
    nl_ppm_max: float | None
    is_istd: bool
    istd_pair: str


class ConfigError(Exception):
    """Raised when settings.csv or targets.csv contains invalid values."""

