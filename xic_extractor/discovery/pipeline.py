from __future__ import annotations

import csv
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol, cast

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.csv_writer import (
    format_discovery_csv_value,
    write_discovery_candidates_csv,
    write_discovery_review_csv,
)
from xic_extractor.discovery.feature_family import assign_feature_families
from xic_extractor.discovery.grouping import group_discovery_seeds
from xic_extractor.discovery.models import (
    DiscoveryBatchOutputs,
    DiscoveryCandidate,
    DiscoveryRunOutputs,
    DiscoverySettings,
    ReviewPriority,
)
from xic_extractor.discovery.ms1_backfill import MS1XicSource, backfill_ms1_candidates
from xic_extractor.discovery.ms2_seeds import MS2ScanSource, collect_strict_nl_seeds

_BATCH_INDEX_COLUMNS = (
    "sample_stem",
    "raw_file",
    "candidate_csv",
    "review_csv",
    "candidate_count",
    "high_count",
    "medium_count",
    "low_count",
)


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
) -> DiscoveryRunOutputs:
    opener = raw_opener or _default_raw_opener
    candidates = assign_feature_families(
        _discover_raw_file(
            raw_path,
            settings=settings,
            peak_config=peak_config,
            raw_opener=opener,
        )
    )
    return _write_dual_csvs(output_dir, candidates)


def run_discovery_batch(
    raw_paths: tuple[Path, ...],
    *,
    output_dir: Path,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
    raw_opener: RawOpener | None = None,
) -> DiscoveryBatchOutputs:
    opener = raw_opener or _default_raw_opener
    index_rows: list[dict[str, str]] = []
    per_sample: list[DiscoveryRunOutputs] = []
    for raw_path in raw_paths:
        candidates = assign_feature_families(
            _discover_raw_file(
                raw_path,
                settings=settings,
                peak_config=peak_config,
                raw_opener=opener,
            )
        )
        sample_output_dir = output_dir / raw_path.stem
        outputs = _write_dual_csvs(sample_output_dir, candidates)
        per_sample.append(outputs)
        index_rows.append(
            _batch_index_row(
                raw_path=raw_path,
                outputs=outputs,
                candidates=candidates,
            )
        )

    return DiscoveryBatchOutputs(
        batch_index_csv=_write_batch_index(
            output_dir / "discovery_batch_index.csv", index_rows
        ),
        per_sample=tuple(per_sample),
    )


def _write_dual_csvs(
    output_dir: Path,
    candidates: tuple[DiscoveryCandidate, ...],
) -> DiscoveryRunOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = output_dir / "discovery_candidates.csv"
    review_path = output_dir / "discovery_review.csv"
    candidates_tmp = candidates_path.with_name(f"{candidates_path.name}.tmp")
    review_tmp = review_path.with_name(f"{review_path.name}.tmp")

    try:
        write_discovery_candidates_csv(candidates_tmp, candidates)
        write_discovery_review_csv(review_tmp, candidates)
        candidates_tmp.replace(candidates_path)
        review_tmp.replace(review_path)
    except Exception:
        candidates_tmp.unlink(missing_ok=True)
        review_tmp.unlink(missing_ok=True)
        raise

    return DiscoveryRunOutputs(
        candidates_csv=candidates_path,
        review_csv=review_path,
    )


def _batch_index_row(
    *,
    raw_path: Path,
    outputs: DiscoveryRunOutputs,
    candidates: tuple[DiscoveryCandidate, ...],
) -> dict[str, str]:
    counts = _priority_counts(candidates)
    return {
        "sample_stem": format_discovery_csv_value("sample_stem", raw_path.stem),
        "raw_file": format_discovery_csv_value("raw_file", raw_path),
        "candidate_csv": format_discovery_csv_value(
            "candidate_csv", outputs.candidates_csv
        ),
        "review_csv": format_discovery_csv_value("review_csv", outputs.review_csv),
        "candidate_count": str(len(candidates)),
        "high_count": str(counts["HIGH"]),
        "medium_count": str(counts["MEDIUM"]),
        "low_count": str(counts["LOW"]),
    }


def _priority_counts(
    candidates: tuple[DiscoveryCandidate, ...],
) -> dict[ReviewPriority, int]:
    counts: dict[ReviewPriority, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for candidate in candidates:
        counts[candidate.review_priority] += 1
    return counts


def _write_batch_index(output_path: Path, rows: list[dict[str, str]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_BATCH_INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _discover_raw_file(
    raw_path: Path,
    *,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
    raw_opener: RawOpener,
) -> tuple[DiscoveryCandidate, ...]:
    with raw_opener(raw_path, peak_config.dll_dir) as raw:
        seeds = collect_strict_nl_seeds(raw, raw_file=raw_path, settings=settings)
        groups = group_discovery_seeds(seeds, settings=settings)
        return backfill_ms1_candidates(
            raw,
            groups,
            settings=settings,
            peak_config=peak_config,
        )


def _default_raw_opener(
    raw_path: Path,
    dll_dir: Path,
) -> AbstractContextManager[DiscoveryRawHandle]:
    from xic_extractor.raw_reader import open_raw

    return cast(AbstractContextManager[DiscoveryRawHandle], open_raw(raw_path, dll_dir))
