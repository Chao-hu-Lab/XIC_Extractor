from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol, cast

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.csv_writer import write_discovery_candidates_csv
from xic_extractor.discovery.feature_family import assign_feature_families
from xic_extractor.discovery.grouping import group_discovery_seeds
from xic_extractor.discovery.models import DiscoverySettings
from xic_extractor.discovery.ms1_backfill import MS1XicSource, backfill_ms1_candidates
from xic_extractor.discovery.ms2_seeds import MS2ScanSource, collect_strict_nl_seeds


class DiscoveryRawHandle(MS1XicSource, MS2ScanSource, Protocol):
    """RAW reader surface needed by single-file discovery orchestration."""


RawOpener = Callable[[Path, Path], AbstractContextManager[DiscoveryRawHandle]]


def run_discovery(
    raw_path: Path,
    *,
    output_dir: Path,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
    raw_opener: RawOpener | None = None,
) -> Path:
    opener = raw_opener or _default_raw_opener
    output_path = output_dir / "discovery_candidates.csv"

    with opener(raw_path, peak_config.dll_dir) as raw:
        seeds = collect_strict_nl_seeds(raw, raw_file=raw_path, settings=settings)
        groups = group_discovery_seeds(seeds, settings=settings)
        candidates = backfill_ms1_candidates(
            raw,
            groups,
            settings=settings,
            peak_config=peak_config,
        )

    return write_discovery_candidates_csv(
        output_path,
        assign_feature_families(candidates),
    )


def _default_raw_opener(
    raw_path: Path,
    dll_dir: Path,
) -> AbstractContextManager[DiscoveryRawHandle]:
    from xic_extractor.raw_reader import open_raw

    return cast(AbstractContextManager[DiscoveryRawHandle], open_raw(raw_path, dll_dir))
