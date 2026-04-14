import csv
import logging
import math
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS

LOGGER = logging.getLogger(__name__)

_TARGET_FIELDS = (
    "label",
    "mz",
    "rt_min",
    "rt_max",
    "ppm_tol",
    "neutral_loss_da",
    "nl_ppm_warn",
    "nl_ppm_max",
    "is_istd",
    "istd_pair",
)
_REQUIRED_SETTING_FIELDS = ("key", "value")
_MIGRATION_DEFAULT_KEYS = tuple(
    key for key in CANONICAL_SETTINGS_DEFAULTS if key not in {"data_dir", "dll_dir"}
)


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
    count_no_ms2_as_detected: bool = False


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


@dataclass(frozen=True)
class _ParsedSettings:
    data_dir: Path
    dll_dir: Path
    smooth_window: int
    smooth_polyorder: int
    peak_rel_height: float
    peak_min_prominence_ratio: float
    ms2_precursor_tol_da: float
    nl_min_intensity_ratio: float
    count_no_ms2_as_detected: bool


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


def load_config(config_dir: Path) -> tuple[ExtractionConfig, list[Target]]:
    settings_path = config_dir / "settings.csv"
    targets_path = config_dir / "targets.csv"

    raw_settings = _read_settings(settings_path)
    migrated, warnings = migrate_settings_dict(raw_settings)
    for warning in warnings:
        LOGGER.warning(warning)

    output_dir = config_dir.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = _validate_settings(migrated, settings_path, output_dir)
    targets = _read_targets(targets_path)
    return config, targets


def _read_settings(path: Path) -> dict[str, str]:
    if not path.exists():
        raise ConfigError(f"{path}: file is missing")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        _require_columns(path, rows.fieldnames, _REQUIRED_SETTING_FIELDS)
        return {
            str(row.get("key", "")).strip(): str(row.get("value", "")).strip()
            for row in rows
            if str(row.get("key", "")).strip()
        }


def _validate_settings(
    settings: dict[str, str], settings_path: Path, output_dir: Path
) -> ExtractionConfig:
    parsed = _parse_settings_values(settings, settings_path)
    _validate_settings_ranges(settings, settings_path, parsed)
    return _build_config(parsed, output_dir)


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


def _build_config(parsed: _ParsedSettings, output_dir: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=parsed.data_dir,
        dll_dir=parsed.dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=parsed.smooth_window,
        smooth_polyorder=parsed.smooth_polyorder,
        peak_rel_height=parsed.peak_rel_height,
        peak_min_prominence_ratio=parsed.peak_min_prominence_ratio,
        ms2_precursor_tol_da=parsed.ms2_precursor_tol_da,
        nl_min_intensity_ratio=parsed.nl_min_intensity_ratio,
        count_no_ms2_as_detected=parsed.count_no_ms2_as_detected,
    )


def _read_targets(path: Path) -> list[Target]:
    if not path.exists():
        raise ConfigError(f"{path}: file is missing")
    targets: list[Target] = []
    seen: set[str] = set()

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        _require_columns(path, rows.fieldnames, _TARGET_FIELDS)
        for row_number, row in enumerate(rows, start=2):
            target = _parse_target_row(path, row_number, row)
            if target.label in seen:
                raise _config_error(
                    path, row_number, "label", target.label, "must be unique"
                )
            seen.add(target.label)
            targets.append(target)
    if not targets:
        raise _config_error(path, 2, "label", "", "at least one target row is required")

    by_label = {target.label: target for target in targets}
    for row_number, target in enumerate(targets, start=2):
        if not target.istd_pair:
            continue
        pair = by_label.get(target.istd_pair)
        if pair is None or not pair.is_istd:
            raise _config_error(
                path,
                row_number,
                "istd_pair",
                target.istd_pair,
                "must reference a target with is_istd=true",
            )

    return targets


def _parse_target_row(path: Path, row_number: int, row: dict[str, str]) -> Target:
    values = {field: str(row.get(field, "")).strip() for field in _TARGET_FIELDS}
    label = values["label"]
    if not label:
        raise _config_error(path, row_number, "label", label, "must not be empty")

    mz = _parse_float(path, row_number, "mz", values["mz"])
    rt_min = _parse_float(path, row_number, "rt_min", values["rt_min"])
    rt_max = _parse_float(path, row_number, "rt_max", values["rt_max"])
    ppm_tol = _parse_float(path, row_number, "ppm_tol", values["ppm_tol"])
    is_istd = _parse_bool(path, row_number, "is_istd", values["is_istd"] or "false")

    if mz <= 0:
        raise _config_error(path, row_number, "mz", values["mz"], "must be > 0")
    if ppm_tol <= 0:
        raise _config_error(
            path, row_number, "ppm_tol", values["ppm_tol"], "must be > 0"
        )
    if rt_min < 0 or rt_max < 0 or rt_min >= rt_max:
        raise _config_error(
            path,
            row_number,
            "rt_min",
            values["rt_min"],
            "must be non-negative and < rt_max",
        )

    neutral_loss_da, nl_ppm_warn, nl_ppm_max = _parse_neutral_loss(
        path, row_number, values, mz
    )

    return Target(
        label=label,
        mz=mz,
        rt_min=rt_min,
        rt_max=rt_max,
        ppm_tol=ppm_tol,
        neutral_loss_da=neutral_loss_da,
        nl_ppm_warn=nl_ppm_warn,
        nl_ppm_max=nl_ppm_max,
        is_istd=is_istd,
        istd_pair=values["istd_pair"],
    )


def _parse_neutral_loss(
    path: Path, row_number: int, values: dict[str, str], mz: float
) -> tuple[float | None, float | None, float | None]:
    if values["neutral_loss_da"] == "":
        if values["nl_ppm_warn"] or values["nl_ppm_max"]:
            LOGGER.warning(
                "%s row %s has NL thresholds without neutral_loss_da; "
                "thresholds ignored",
                path,
                row_number,
            )
        return None, None, None

    neutral_loss_da = _parse_float(
        path, row_number, "neutral_loss_da", values["neutral_loss_da"]
    )
    nl_ppm_warn = _parse_float(path, row_number, "nl_ppm_warn", values["nl_ppm_warn"])
    nl_ppm_max = _parse_float(path, row_number, "nl_ppm_max", values["nl_ppm_max"])

    if neutral_loss_da <= 0 or neutral_loss_da >= mz:
        raise _config_error(
            path,
            row_number,
            "neutral_loss_da",
            values["neutral_loss_da"],
            "must be > 0 and < mz",
        )
    if nl_ppm_warn <= 0:
        raise _config_error(
            path, row_number, "nl_ppm_warn", values["nl_ppm_warn"], "must be > 0"
        )
    if nl_ppm_max <= 0:
        raise _config_error(
            path, row_number, "nl_ppm_max", values["nl_ppm_max"], "must be > 0"
        )
    if nl_ppm_warn > nl_ppm_max:
        raise _config_error(
            path,
            row_number,
            "nl_ppm_warn",
            values["nl_ppm_warn"],
            "must be <= nl_ppm_max",
        )

    return neutral_loss_da, nl_ppm_warn, nl_ppm_max


def _parse_existing_dir(path: Path, column: str, value: str) -> Path:
    directory = Path(value).expanduser()
    if not directory.is_dir():
        raise _config_error(path, None, column, value, "must exist as a directory")
    return directory


def _setting_value(settings: dict[str, str], path: Path, column: str) -> str:
    value = settings.get(column, "")
    if value == "":
        raise _config_error(path, None, column, value, "is required")
    return value


def _require_columns(
    path: Path, fieldnames: list[str] | None, required: tuple[str, ...]
) -> None:
    available = set(fieldnames or [])
    for column in required:
        if column not in available:
            raise _config_error(path, None, column, "", "required column is missing")


def _parse_int(path: Path, row_number: int | None, column: str, value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise _config_error(
            path, row_number, column, value, "must be an integer"
        ) from exc


def _parse_float(path: Path, row_number: int | None, column: str, value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise _config_error(path, row_number, column, value, "must be numeric") from exc
    if not math.isfinite(parsed):
        raise _config_error(path, row_number, column, value, "must be finite")
    return parsed


def _parse_bool(path: Path, row_number: int | None, column: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise _config_error(path, row_number, column, value, "must be true or false")


def _require_range(
    path: Path, column: str, value: str, parsed: float, minimum: float, maximum: float
) -> None:
    if not minimum <= parsed <= maximum:
        raise _config_error(
            path, None, column, value, f"must be between {minimum} and {maximum}"
        )


def _config_error(
    path: Path, row_number: int | None, column: str, value: str, message: str
) -> ConfigError:
    row = f" row {row_number}" if row_number is not None else ""
    return ConfigError(f"{path}{row} column {column} value {value!r}: {message}")
