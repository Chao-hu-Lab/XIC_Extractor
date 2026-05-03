from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata

from xic_extractor.config import ExtractionConfig


def app_version() -> str:
    try:
        return metadata.version("xic-extractor")
    except metadata.PackageNotFoundError:
        return "unknown"


def build_metadata_rows(config: ExtractionConfig) -> list[tuple[str, object]]:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [
        ("config_hash", config.config_hash),
        ("app_version", app_version()),
        ("generated_at", generated_at),
        ("resolver_mode", config.resolver_mode),
        ("smooth_window", config.smooth_window),
        ("smooth_polyorder", config.smooth_polyorder),
        ("peak_min_prominence_ratio", config.peak_min_prominence_ratio),
        ("nl_min_intensity_ratio", config.nl_min_intensity_ratio),
        ("ms2_precursor_tol_da", config.ms2_precursor_tol_da),
    ]
