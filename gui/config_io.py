import csv
import shutil
import sys
from pathlib import Path

from xic_extractor.config import CANONICAL_SETTINGS_DESCRIPTIONS

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


def _ensure_config(name: str) -> None:
    """若 {name}.csv 不存在，從 bundle 內的 {name}.example.csv 複製一份。"""
    dst = CONFIG_DIR / f"{name}.csv"
    if not dst.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        src = _BUNDLE_CONFIG / f"{name}.example.csv"
        if src.exists():
            shutil.copy2(src, dst)


def read_settings() -> dict[str, str]:
    _ensure_config("settings")
    with (CONFIG_DIR / "settings.csv").open(newline="", encoding="utf-8-sig") as handle:
        return {row["key"]: row["value"] for row in csv.DictReader(handle)}


def write_settings(settings: dict[str, str]) -> None:
    _ensure_config("settings")
    path = CONFIG_DIR / "settings.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
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
    _ensure_config("targets")
    with (CONFIG_DIR / "targets.csv").open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_targets(targets: list[dict[str, str]]) -> None:
    with (CONFIG_DIR / "targets.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=_TARGETS_FIELDS)
        writer.writeheader()
        for target in targets:
            writer.writerow({field: target.get(field, "") for field in _TARGETS_FIELDS})
