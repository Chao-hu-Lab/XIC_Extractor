import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
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
]


def read_settings() -> dict[str, str]:
    with (CONFIG_DIR / "settings.csv").open(newline="", encoding="utf-8-sig") as handle:
        return {row["key"]: row["value"] for row in csv.DictReader(handle)}


def write_settings(settings: dict[str, str]) -> None:
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
                    "description": existing.get(key, {}).get("description", ""),
                }
            )


def read_targets() -> list[dict[str, str]]:
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
