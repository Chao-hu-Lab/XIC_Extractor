from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS

_ADVANCED_SETTING_KEYS = (
    "keep_intermediate_csv",
    "emit_score_breakdown",
    "emit_review_report",
    "dirty_matrix_mode",
    "count_no_ms2_as_detected",
    "rolling_window_size",
    "rt_prior_library_path",
    "injection_order_source",
    "resolver_mode",
    "resolver_chrom_threshold",
    "resolver_min_search_range_min",
    "resolver_min_relative_height",
    "resolver_min_absolute_height",
    "resolver_min_ratio_top_edge",
    "resolver_peak_duration_min",
    "resolver_peak_duration_max",
    "resolver_min_scans",
    "nl_rt_anchor_search_margin_min",
    "nl_rt_anchor_half_window_min",
    "nl_fallback_half_window_min",
    "parallel_mode",
    "parallel_workers",
)

_GUI_UNBOUNDED_FLOAT_MAX = 1e12

_LOCAL_MINIMUM_PRESET_KEYS = (
    "resolver_chrom_threshold",
    "resolver_min_search_range_min",
    "resolver_min_relative_height",
    "resolver_min_absolute_height",
    "resolver_min_ratio_top_edge",
    "resolver_peak_duration_min",
    "resolver_peak_duration_max",
    "resolver_min_scans",
)

_LOCAL_MINIMUM_GUI_PRESET = {
    key: CANONICAL_SETTINGS_DEFAULTS[key] for key in _LOCAL_MINIMUM_PRESET_KEYS
}
