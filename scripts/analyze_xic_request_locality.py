from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xic_extractor.raw_reader import open_raw


@dataclass(frozen=True)
class BatchArtifacts:
    sample_order: tuple[str, ...]
    raw_paths: dict[str, Path]
    candidate_csvs: dict[str, Path]


@dataclass(frozen=True)
class RequestRecord:
    stage: str
    sample_stem: str
    mz: float
    rt_min: float
    rt_max: float
    ppm_tol: float


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    batch = read_batch_index(args.discovery_batch_index, args.raw_dir)
    build_requests = collect_build_owner_requests(
        batch,
        max_rt_sec=args.max_rt_sec,
        preferred_ppm=args.preferred_ppm,
    )
    result: dict[str, Any] = {
        "raw_xic_batch_size": args.raw_xic_batch_size,
        "stages": {
            "build_owners": summarize_locality(
                build_requests,
                raw_paths=batch.raw_paths,
                dll_dir=args.dll_dir,
                batch_size=args.raw_xic_batch_size,
            )
        },
    }
    if args.alignment_review is not None and args.alignment_cells is not None:
        backfill_requests = collect_owner_backfill_requests(
            batch,
            alignment_review=args.alignment_review,
            alignment_cells=args.alignment_cells,
            max_rt_sec=args.max_rt_sec,
            preferred_ppm=args.preferred_ppm,
            owner_backfill_min_detected_samples=(
                args.owner_backfill_min_detected_samples
            ),
        )
        result["stages"]["owner_backfill"] = summarize_locality(
            backfill_requests,
            raw_paths=batch.raw_paths,
            dll_dir=args.dll_dir,
            batch_size=args.raw_xic_batch_size,
        )
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")
    return 0


def read_batch_index(path: Path, raw_dir: Path) -> BatchArtifacts:
    rows = _read_delimited_rows(path, delimiter=",")
    sample_order: list[str] = []
    raw_paths: dict[str, Path] = {}
    candidate_csvs: dict[str, Path] = {}
    for row in rows:
        sample_stem = _machine_text(row.get("sample_stem", ""))
        if not sample_stem:
            continue
        sample_order.append(sample_stem)
        raw_file = Path(_machine_text(row.get("raw_file", "")))
        raw_name = raw_file.name if raw_file.name else f"{sample_stem}.raw"
        raw_paths[sample_stem] = raw_dir / raw_name
        candidate_csv = Path(_machine_text(row.get("candidate_csv", "")))
        if not candidate_csv.is_absolute():
            candidate_csv = path.parent / candidate_csv
        candidate_csvs[sample_stem] = candidate_csv
    return BatchArtifacts(
        sample_order=tuple(sample_order),
        raw_paths=raw_paths,
        candidate_csvs=candidate_csvs,
    )


def collect_build_owner_requests(
    batch: BatchArtifacts,
    *,
    max_rt_sec: float,
    preferred_ppm: float,
) -> tuple[RequestRecord, ...]:
    rt_window_min = max_rt_sec / 60.0
    records: list[RequestRecord] = []
    for sample_stem in batch.sample_order:
        candidate_csv = batch.candidate_csvs.get(sample_stem)
        if candidate_csv is None or not candidate_csv.is_file():
            continue
        for row in _read_delimited_rows(candidate_csv, delimiter=","):
            seed_rt = _first_float(row, ("best_seed_rt", "ms1_apex_rt"))
            mz = _optional_float(row.get("precursor_mz", ""))
            if seed_rt is None or mz is None:
                continue
            records.append(
                RequestRecord(
                    stage="build_owners",
                    sample_stem=sample_stem,
                    mz=mz,
                    rt_min=seed_rt - rt_window_min,
                    rt_max=seed_rt + rt_window_min,
                    ppm_tol=preferred_ppm,
                )
            )
    return tuple(records)


def collect_owner_backfill_requests(
    batch: BatchArtifacts,
    *,
    alignment_review: Path,
    alignment_cells: Path,
    max_rt_sec: float,
    preferred_ppm: float,
    owner_backfill_min_detected_samples: int,
) -> tuple[RequestRecord, ...]:
    detected_by_feature: dict[str, set[str]] = defaultdict(set)
    for row in _read_delimited_rows(alignment_cells, delimiter="\t"):
        if row.get("status") == "detected":
            detected_by_feature[row.get("feature_family_id", "")].add(
                row.get("sample_stem", "")
            )

    rt_window_min = max_rt_sec / 60.0
    records: list[RequestRecord] = []
    for row in _read_delimited_rows(alignment_review, delimiter="\t"):
        feature_id = row.get("feature_family_id", "")
        detected_samples = {
            sample for sample in detected_by_feature.get(feature_id, set()) if sample
        }
        if len(detected_samples) < owner_backfill_min_detected_samples:
            continue
        mz = _optional_float(row.get("family_center_mz", ""))
        rt = _optional_float(row.get("family_center_rt", ""))
        if mz is None or rt is None:
            continue
        for sample_stem in batch.sample_order:
            if sample_stem in detected_samples:
                continue
            if sample_stem not in batch.raw_paths:
                continue
            records.append(
                RequestRecord(
                    stage="owner_backfill",
                    sample_stem=sample_stem,
                    mz=mz,
                    rt_min=rt - rt_window_min,
                    rt_max=rt + rt_window_min,
                    ppm_tol=preferred_ppm,
                )
            )
    return tuple(records)


def summarize_locality(
    records: Sequence[RequestRecord],
    *,
    raw_paths: dict[str, Path],
    dll_dir: Path,
    batch_size: int,
    open_raw_func: Callable[[Path, Path], Any] = open_raw,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    by_sample: dict[str, list[RequestRecord]] = defaultdict(list)
    for record in records:
        by_sample[record.sample_stem].append(record)

    sample_summaries: dict[str, dict[str, int]] = {}
    totals = {
        "request_count": 0,
        "original_chunk_call_count": 0,
        "sorted_chunk_call_count": 0,
        "upper_bound_call_count": 0,
        "unique_scan_window_count": 0,
    }
    for sample_stem, sample_records in by_sample.items():
        raw_path = raw_paths.get(sample_stem)
        if raw_path is None:
            continue
        with open_raw_func(raw_path, dll_dir) as raw:
            windows = tuple(_scan_window(raw, record) for record in sample_records)
        original_calls = _chunked_unique_count(windows, batch_size)
        sorted_windows = tuple(sorted(windows))
        sorted_calls = _chunked_unique_count(sorted_windows, batch_size)
        upper_bound = len(set(windows))
        sample_summary = {
            "request_count": len(windows),
            "original_chunk_call_count": original_calls,
            "sorted_chunk_call_count": sorted_calls,
            "upper_bound_call_count": upper_bound,
            "unique_scan_window_count": upper_bound,
        }
        sample_summaries[sample_stem] = sample_summary
        for key in totals:
            totals[key] += sample_summary[key]
    totals["sample_count"] = len(sample_summaries)
    return {**totals, "samples": sample_summaries}


def _scan_window(raw: Any, record: RequestRecord) -> tuple[int, int]:
    raw_file = getattr(raw, "_raw_file", raw)
    return (
        int(raw_file.ScanNumberFromRetentionTime(record.rt_min)),
        int(raw_file.ScanNumberFromRetentionTime(record.rt_max)),
    )


def _chunked_unique_count(windows: tuple[tuple[int, int], ...], chunk_size: int) -> int:
    total = 0
    for index in range(0, len(windows), chunk_size):
        total += len(set(windows[index : index + chunk_size]))
    return total


def _read_delimited_rows(path: Path, *, delimiter: str) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle, delimiter=delimiter))


def _first_float(row: dict[str, str], columns: tuple[str, ...]) -> float | None:
    for column in columns:
        value = _optional_float(row.get(column, ""))
        if value is not None:
            return value
    return None


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(_machine_text(value))
    except ValueError:
        return None


def _machine_text(value: str) -> str:
    if len(value) >= 2 and value[0] == "'" and value[1] in ("=", "+", "-", "@"):
        return value[1:]
    return value


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze RAW XIC request scan-window locality.",
    )
    parser.add_argument("--discovery-batch-index", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--alignment-review", type=Path)
    parser.add_argument("--alignment-cells", type=Path)
    parser.add_argument("--max-rt-sec", type=float, default=180.0)
    parser.add_argument("--preferred-ppm", type=float, default=20.0)
    parser.add_argument("--raw-xic-batch-size", type=int, default=64)
    parser.add_argument("--owner-backfill-min-detected-samples", type=int, default=1)
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
