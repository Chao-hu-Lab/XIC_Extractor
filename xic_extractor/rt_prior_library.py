from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

LIBRARY_FIELDNAMES = (
    "config_hash",
    "target_label",
    "role",
    "istd_pair",
    "median_delta_rt",
    "sigma_delta_rt",
    "median_abs_rt",
    "sigma_abs_rt",
    "n_samples",
    "updated_at",
)


@dataclass(frozen=True)
class LibraryEntry:
    config_hash: str
    target_label: str
    role: str
    istd_pair: str
    median_delta_rt: float | None
    sigma_delta_rt: float | None
    median_abs_rt: float | None
    sigma_abs_rt: float | None
    n_samples: int
    updated_at: str


def load_library(path: Path, config_hash: str) -> dict[tuple[str, str], LibraryEntry]:
    if not path.exists():
        return {}
    out: dict[tuple[str, str], LibraryEntry] = {}
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("config_hash") != config_hash:
                continue
            entry = LibraryEntry(
                config_hash=row["config_hash"],
                target_label=row["target_label"],
                role=row["role"],
                istd_pair=row.get("istd_pair") or "",
                median_delta_rt=_opt_float(row.get("median_delta_rt")),
                sigma_delta_rt=_opt_float(row.get("sigma_delta_rt")),
                median_abs_rt=_opt_float(row.get("median_abs_rt")),
                sigma_abs_rt=_opt_float(row.get("sigma_abs_rt")),
                n_samples=int((row.get("n_samples") or "0").strip() or 0),
                updated_at=row.get("updated_at") or "",
            )
            out[(entry.target_label, entry.role)] = entry
    return out


def write_pending_update(library_path: Path, entries: list[LibraryEntry]) -> Path:
    """Write proposed library rows without mutating the main library."""
    pending = library_path.with_suffix(".pending.csv")
    pending.parent.mkdir(parents=True, exist_ok=True)
    with pending.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LIBRARY_FIELDNAMES)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "config_hash": entry.config_hash,
                    "target_label": entry.target_label,
                    "role": entry.role,
                    "istd_pair": entry.istd_pair,
                    "median_delta_rt": _format_optional_float(
                        entry.median_delta_rt
                    ),
                    "sigma_delta_rt": _format_optional_float(entry.sigma_delta_rt),
                    "median_abs_rt": _format_optional_float(entry.median_abs_rt),
                    "sigma_abs_rt": _format_optional_float(entry.sigma_abs_rt),
                    "n_samples": str(entry.n_samples),
                    "updated_at": entry.updated_at,
                }
            )
    return pending


def _opt_float(value: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    return float(normalized)


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"
