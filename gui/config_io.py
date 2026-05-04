import csv
import sys
from pathlib import Path

from xic_extractor.settings_schema import CANONICAL_SETTINGS_DESCRIPTIONS

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent  # user-writable: config/, output/
    _BUNDLE = Path(sys._MEIPASS)  # read-only bundle: example CSVs
else:
    ROOT = Path(__file__).resolve().parent.parent
    _BUNDLE = ROOT

CONFIG_DIR = ROOT / "config"
_BUNDLE_CONFIG = _BUNDLE / "config"
_SETTINGS_FIELDS = ["key", "value", "description"]
_TARGETS_FIELDS = [
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
]


def _read_path(name: str) -> Path:
    runtime_path = CONFIG_DIR / f"{name}.csv"
    if runtime_path.exists():
        return runtime_path
    return _BUNDLE_CONFIG / f"{name}.example.csv"


def read_settings() -> dict[str, str]:
    with _read_path("settings").open(newline="", encoding="utf-8-sig") as handle:
        return {row["key"]: row["value"] for row in csv.DictReader(handle)}


def write_settings(settings: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "settings.csv"
    source_path = path if path.exists() else _read_path("settings")
    with source_path.open(newline="", encoding="utf-8-sig") as handle:
        existing = {row["key"]: row for row in csv.DictReader(handle)}

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=_SETTINGS_FIELDS)
        writer.writeheader()
        for key, value in settings.items():
            writer.writerow(
                {
                    "key": key,
                    "value": value,
                    "description": existing.get(key, {}).get("description", "")
                    or CANONICAL_SETTINGS_DESCRIPTIONS.get(key, ""),
                }
            )


def read_targets() -> list[dict[str, str]]:
    with _read_path("targets").open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_targets(targets: list[dict[str, str]]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with (CONFIG_DIR / "targets.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=_TARGETS_FIELDS)
        writer.writeheader()
        for target in targets:
            writer.writerow({field: target.get(field, "") for field in _TARGETS_FIELDS})
