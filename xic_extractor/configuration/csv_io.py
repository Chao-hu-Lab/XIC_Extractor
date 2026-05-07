import csv
from pathlib import Path

from xic_extractor.configuration.models import ConfigError
from xic_extractor.configuration.parsing import _require_columns

TARGET_FIELDS = (
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


def _config_input_path(config_dir: Path, name: str) -> Path:
    runtime_path = config_dir / f"{name}.csv"
    if runtime_path.exists():
        return runtime_path
    example_path = config_dir / f"{name}.example.csv"
    if example_path.exists():
        return example_path
    return runtime_path


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


def _read_target_rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    if not path.exists():
        raise ConfigError(f"{path}: file is missing")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        _require_columns(path, rows.fieldnames, TARGET_FIELDS)
        return [(row_number, row) for row_number, row in enumerate(rows, start=2)]
