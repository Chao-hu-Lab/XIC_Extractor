import logging
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.configuration.models import ExtractionConfig
from xic_extractor.configuration.parsing import (
    _config_error,
    _parse_bool,
    _parse_existing_dir,
    _parse_float,
    _parse_int,
    _parse_optional_path,
    _require_range,
)
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS

LOGGER = logging.getLogger(__name__)

_MIGRATION_DEFAULT_KEYS = tuple(
    key for key in CANONICAL_SETTINGS_DEFAULTS if key not in {"data_dir", "dll_dir"}
)


@dataclass(frozen=True)
class _ParsedSettings:
    data_dir: Path
    dll_dir: Path
    smooth_window: int
    smooth_polyorder: int
    peak_rel_height: float
    peak_min_prominence_ratio: float
    resolver_mode: str
    resolver_chrom_threshold: float
    resolver_min_search_range_min: float
    resolver_min_relative_height: float
    resolver_min_absolute_height: float
    resolver_min_ratio_top_edge: float
    resolver_peak_duration_min: float
    resolver_peak_duration_max: float
    resolver_min_scans: int
    ms2_precursor_tol_da: float
    nl_min_intensity_ratio: float
    count_no_ms2_as_detected: bool
    nl_rt_anchor_search_margin_min: float
    nl_rt_anchor_half_window_min: float
    nl_fallback_half_window_min: float
    injection_order_source: Path | None
    rolling_window_size: int
    dirty_matrix_mode: bool
    rt_prior_library_path: Path | None
    emit_score_breakdown: bool
    emit_review_report: bool
    keep_intermediate_csv: bool
    parallel_mode: str
    parallel_workers: int


def migrate_settings_dict(raw: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    migrated = dict(raw)
    warnings: list[str] = []

    if "smooth_points" in migrated:
        if "smooth_window" not in migrated:
            migrated["smooth_window"] = migrated["smooth_points"]
            warnings.append("Renamed smooth_points to smooth_window.")
        else:
            warnings.append(
                "Ignored legacy smooth_points because smooth_window exists."
            )
        migrated.pop("smooth_points", None)

    if "smooth_sigma" in migrated:
        migrated.pop("smooth_sigma", None)
        warnings.append(
            "Dropped smooth_sigma because Savitzky-Golay smoothing has no sigma."
        )

    for key in _MIGRATION_DEFAULT_KEYS:
        default = CANONICAL_SETTINGS_DEFAULTS[key]
        if key not in migrated or migrated[key] == "":
            migrated[key] = default
            warnings.append(f"Filled missing {key} with default {default}.")

    return migrated, warnings


def _validate_settings(
    settings: dict[str, str],
    settings_path: Path,
    output_dir: Path,
    config_hash: str,
) -> ExtractionConfig:
    parsed = _parse_settings_values(settings, settings_path)
    _validate_settings_ranges(settings, settings_path, parsed)
    return _build_config(parsed, output_dir, config_hash)


def _parse_settings_values(
    settings: dict[str, str], settings_path: Path
) -> _ParsedSettings:
    return _ParsedSettings(
        data_dir=_parse_existing_dir(
            settings_path,
            "data_dir",
            _setting_value(settings, settings_path, "data_dir"),
        ),
        dll_dir=_parse_existing_dir(
            settings_path, "dll_dir", _setting_value(settings, settings_path, "dll_dir")
        ),
        smooth_window=_parse_int(
            settings_path,
            None,
            "smooth_window",
            _setting_value(settings, settings_path, "smooth_window"),
        ),
        smooth_polyorder=_parse_int(
            settings_path,
            None,
            "smooth_polyorder",
            _setting_value(settings, settings_path, "smooth_polyorder"),
        ),
        peak_rel_height=_parse_float(
            settings_path,
            None,
            "peak_rel_height",
            _setting_value(settings, settings_path, "peak_rel_height"),
        ),
        peak_min_prominence_ratio=_parse_float(
            settings_path,
            None,
            "peak_min_prominence_ratio",
            _setting_value(settings, settings_path, "peak_min_prominence_ratio"),
        ),
        resolver_mode=_setting_value(settings, settings_path, "resolver_mode"),
        resolver_chrom_threshold=_parse_float(
            settings_path,
            None,
            "resolver_chrom_threshold",
            _setting_value(settings, settings_path, "resolver_chrom_threshold"),
        ),
        resolver_min_search_range_min=_parse_float(
            settings_path,
            None,
            "resolver_min_search_range_min",
            _setting_value(settings, settings_path, "resolver_min_search_range_min"),
        ),
        resolver_min_relative_height=_parse_float(
            settings_path,
            None,
            "resolver_min_relative_height",
            _setting_value(settings, settings_path, "resolver_min_relative_height"),
        ),
        resolver_min_absolute_height=_parse_float(
            settings_path,
            None,
            "resolver_min_absolute_height",
            _setting_value(settings, settings_path, "resolver_min_absolute_height"),
        ),
        resolver_min_ratio_top_edge=_parse_float(
            settings_path,
            None,
            "resolver_min_ratio_top_edge",
            _setting_value(settings, settings_path, "resolver_min_ratio_top_edge"),
        ),
        resolver_peak_duration_min=_parse_float(
            settings_path,
            None,
            "resolver_peak_duration_min",
            _setting_value(settings, settings_path, "resolver_peak_duration_min"),
        ),
        resolver_peak_duration_max=_parse_float(
            settings_path,
            None,
            "resolver_peak_duration_max",
            _setting_value(settings, settings_path, "resolver_peak_duration_max"),
        ),
        resolver_min_scans=_parse_int(
            settings_path,
            None,
            "resolver_min_scans",
            _setting_value(settings, settings_path, "resolver_min_scans"),
        ),
        ms2_precursor_tol_da=_parse_float(
            settings_path,
            None,
            "ms2_precursor_tol_da",
            _setting_value(settings, settings_path, "ms2_precursor_tol_da"),
        ),
        nl_min_intensity_ratio=_parse_float(
            settings_path,
            None,
            "nl_min_intensity_ratio",
            _setting_value(settings, settings_path, "nl_min_intensity_ratio"),
        ),
        count_no_ms2_as_detected=_parse_bool(
            settings_path,
            None,
            "count_no_ms2_as_detected",
            _setting_value(settings, settings_path, "count_no_ms2_as_detected"),
        ),
        nl_rt_anchor_search_margin_min=_parse_float(
            settings_path,
            None,
            "nl_rt_anchor_search_margin_min",
            _setting_value(settings, settings_path, "nl_rt_anchor_search_margin_min"),
        ),
        nl_rt_anchor_half_window_min=_parse_float(
            settings_path,
            None,
            "nl_rt_anchor_half_window_min",
            _setting_value(settings, settings_path, "nl_rt_anchor_half_window_min"),
        ),
        nl_fallback_half_window_min=_parse_float(
            settings_path,
            None,
            "nl_fallback_half_window_min",
            _setting_value(settings, settings_path, "nl_fallback_half_window_min"),
        ),
        injection_order_source=_parse_optional_path(
            settings.get("injection_order_source", "")
        ),
        rolling_window_size=_parse_int(
            settings_path,
            None,
            "rolling_window_size",
            _setting_value(settings, settings_path, "rolling_window_size"),
        ),
        dirty_matrix_mode=_parse_bool(
            settings_path,
            None,
            "dirty_matrix_mode",
            _setting_value(settings, settings_path, "dirty_matrix_mode"),
        ),
        rt_prior_library_path=_parse_optional_path(
            settings.get("rt_prior_library_path", "")
        ),
        emit_score_breakdown=_parse_bool(
            settings_path,
            None,
            "emit_score_breakdown",
            _setting_value(settings, settings_path, "emit_score_breakdown"),
        ),
        emit_review_report=_parse_bool(
            settings_path,
            None,
            "emit_review_report",
            _setting_value(settings, settings_path, "emit_review_report"),
        ),
        keep_intermediate_csv=_parse_bool(
            settings_path,
            None,
            "keep_intermediate_csv",
            _setting_value(settings, settings_path, "keep_intermediate_csv"),
        ),
        parallel_mode=_setting_value(settings, settings_path, "parallel_mode"),
        parallel_workers=_parse_int(
            settings_path,
            None,
            "parallel_workers",
            _setting_value(settings, settings_path, "parallel_workers"),
        ),
    )


def _validate_settings_ranges(
    settings: dict[str, str], settings_path: Path, parsed: _ParsedSettings
) -> None:
    if parsed.smooth_window < 3 or parsed.smooth_window % 2 == 0:
        raise _config_error(
            settings_path,
            None,
            "smooth_window",
            settings["smooth_window"],
            "must be odd and >= 3",
        )
    if parsed.smooth_polyorder < 1 or parsed.smooth_polyorder >= parsed.smooth_window:
        raise _config_error(
            settings_path,
            None,
            "smooth_polyorder",
            settings["smooth_polyorder"],
            "must be >= 1 and < smooth_window",
        )
    _require_range(
        settings_path,
        "peak_rel_height",
        settings["peak_rel_height"],
        parsed.peak_rel_height,
        0.5,
        0.99,
    )
    _require_range(
        settings_path,
        "peak_min_prominence_ratio",
        settings["peak_min_prominence_ratio"],
        parsed.peak_min_prominence_ratio,
        0.01,
        0.50,
    )
    if parsed.resolver_mode not in {"legacy_savgol", "local_minimum"}:
        raise _config_error(
            settings_path,
            None,
            "resolver_mode",
            settings["resolver_mode"],
            "must be legacy_savgol or local_minimum",
        )
    if not 0 <= parsed.resolver_chrom_threshold <= 1:
        raise _config_error(
            settings_path,
            None,
            "resolver_chrom_threshold",
            settings["resolver_chrom_threshold"],
            "must be between 0 and 1",
        )
    if parsed.resolver_min_search_range_min <= 0:
        raise _config_error(
            settings_path,
            None,
            "resolver_min_search_range_min",
            settings["resolver_min_search_range_min"],
            "must be > 0",
        )
    if not 0 <= parsed.resolver_min_relative_height <= 1:
        raise _config_error(
            settings_path,
            None,
            "resolver_min_relative_height",
            settings["resolver_min_relative_height"],
            "must be >= 0 and <= 1",
        )
    if parsed.resolver_min_absolute_height < 0:
        raise _config_error(
            settings_path,
            None,
            "resolver_min_absolute_height",
            settings["resolver_min_absolute_height"],
            "must be >= 0",
        )
    if parsed.resolver_min_ratio_top_edge <= 1:
        raise _config_error(
            settings_path,
            None,
            "resolver_min_ratio_top_edge",
            settings["resolver_min_ratio_top_edge"],
            "must be > 1",
        )
    if parsed.resolver_peak_duration_min < 0:
        raise _config_error(
            settings_path,
            None,
            "resolver_peak_duration_min",
            settings["resolver_peak_duration_min"],
            "must be >= 0",
        )
    if parsed.resolver_peak_duration_max <= 0:
        raise _config_error(
            settings_path,
            None,
            "resolver_peak_duration_max",
            settings["resolver_peak_duration_max"],
            "must be > 0",
        )
    if parsed.resolver_peak_duration_min > parsed.resolver_peak_duration_max:
        raise _config_error(
            settings_path,
            None,
            "resolver_peak_duration_min",
            settings["resolver_peak_duration_min"],
            "must be <= resolver_peak_duration_max",
        )
    if parsed.resolver_min_scans < 1:
        raise _config_error(
            settings_path,
            None,
            "resolver_min_scans",
            settings["resolver_min_scans"],
            "must be >= 1",
        )
    if parsed.ms2_precursor_tol_da <= 0:
        raise _config_error(
            settings_path,
            None,
            "ms2_precursor_tol_da",
            settings["ms2_precursor_tol_da"],
            "must be > 0",
        )
    if not 0 < parsed.nl_min_intensity_ratio <= 1:
        raise _config_error(
            settings_path,
            None,
            "nl_min_intensity_ratio",
            settings["nl_min_intensity_ratio"],
            "must be > 0 and <= 1",
        )
    for column, parsed_value in (
        (
            "nl_rt_anchor_search_margin_min",
            parsed.nl_rt_anchor_search_margin_min,
        ),
        (
            "nl_rt_anchor_half_window_min",
            parsed.nl_rt_anchor_half_window_min,
        ),
        (
            "nl_fallback_half_window_min",
            parsed.nl_fallback_half_window_min,
        ),
    ):
        if parsed_value <= 0:
            raise _config_error(
                settings_path,
                None,
                column,
                settings[column],
                "must be > 0",
            )
    if parsed.rolling_window_size < 1:
        raise _config_error(
            settings_path,
            None,
            "rolling_window_size",
            settings["rolling_window_size"],
            "must be >= 1",
        )
    if parsed.parallel_mode not in {"serial", "process"}:
        raise _config_error(
            settings_path,
            None,
            "parallel_mode",
            settings["parallel_mode"],
            "must be serial or process",
        )
    if parsed.parallel_workers < 1:
        raise _config_error(
            settings_path,
            None,
            "parallel_workers",
            settings["parallel_workers"],
            "must be >= 1",
        )


def _build_config(
    parsed: _ParsedSettings, output_dir: Path, config_hash: str
) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=parsed.data_dir,
        dll_dir=parsed.dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=parsed.smooth_window,
        smooth_polyorder=parsed.smooth_polyorder,
        peak_rel_height=parsed.peak_rel_height,
        peak_min_prominence_ratio=parsed.peak_min_prominence_ratio,
        resolver_mode=parsed.resolver_mode,
        resolver_chrom_threshold=parsed.resolver_chrom_threshold,
        resolver_min_search_range_min=parsed.resolver_min_search_range_min,
        resolver_min_relative_height=parsed.resolver_min_relative_height,
        resolver_min_absolute_height=parsed.resolver_min_absolute_height,
        resolver_min_ratio_top_edge=parsed.resolver_min_ratio_top_edge,
        resolver_peak_duration_min=parsed.resolver_peak_duration_min,
        resolver_peak_duration_max=parsed.resolver_peak_duration_max,
        resolver_min_scans=parsed.resolver_min_scans,
        ms2_precursor_tol_da=parsed.ms2_precursor_tol_da,
        nl_min_intensity_ratio=parsed.nl_min_intensity_ratio,
        count_no_ms2_as_detected=parsed.count_no_ms2_as_detected,
        nl_rt_anchor_search_margin_min=parsed.nl_rt_anchor_search_margin_min,
        nl_rt_anchor_half_window_min=parsed.nl_rt_anchor_half_window_min,
        nl_fallback_half_window_min=parsed.nl_fallback_half_window_min,
        injection_order_source=parsed.injection_order_source,
        rolling_window_size=parsed.rolling_window_size,
        dirty_matrix_mode=parsed.dirty_matrix_mode,
        rt_prior_library_path=parsed.rt_prior_library_path,
        emit_score_breakdown=parsed.emit_score_breakdown,
        emit_review_report=parsed.emit_review_report,
        keep_intermediate_csv=parsed.keep_intermediate_csv,
        parallel_mode=parsed.parallel_mode,
        parallel_workers=parsed.parallel_workers,
        config_hash=config_hash,
    )


def _setting_value(settings: dict[str, str], path: Path, column: str) -> str:
    value = settings.get(column, "")
    if value == "":
        raise _config_error(path, None, column, value, "is required")
    return value
