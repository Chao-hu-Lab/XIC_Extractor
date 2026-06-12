from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from time import perf_counter
from typing import Any, TypedDict

from scripts.run_alignment import (
    _alignment_production_resolver_mode,
    _peak_config,
)
from tools.diagnostics.diagnostic_io import write_tsv
from xic_extractor.alignment.backfill_scope import (
    backfill_seed_centers,
    select_backfill_features,
    skipped_evidence_summary,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.csv_io import (
    read_discovery_batch_index,
    read_discovery_candidates_csv,
)
from xic_extractor.alignment.output_levels import (
    AlignmentOutputLevel,
    artifact_names_for_output_level,
    parse_alignment_output_level,
)
from xic_extractor.alignment.owner_backfill import _scan_window_aware_chunks
from xic_extractor.alignment.owner_backfill_request_plan import (
    build_owner_backfill_request_plan,
)
from xic_extractor.alignment.owner_clustering import (
    cluster_sample_local_owners,
    review_only_features_from_ambiguous_records,
)
from xic_extractor.alignment.owner_group_delivery import (
    OwnerGroupDeliveryFeatures,
)
from xic_extractor.alignment.pre_backfill_consolidation import (
    consolidate_pre_backfill_identity_families,
)
from xic_extractor.alignment.process_backend import run_owner_build_process
from xic_extractor.alignment.raw_sources import existing_raw_paths
from xic_extractor.raw_reader import open_raw
from xic_extractor.xic_models import XICRequest


class _RequestSummary(TypedDict):
    totals: dict[str, object]
    sample_rows: list[dict[str, object]]
    feature_rows: list[dict[str, object]]


class _LocalitySummary(TypedDict):
    totals: dict[str, object]
    sample_rows: list[dict[str, object]]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "backfill_scope_probe_status.json"
    timings: list[dict[str, object]] = []

    def checkpoint(stage: str, **metrics: object) -> None:
        timings.append({"stage": stage, **metrics})
        status_path.write_text(
            json.dumps({"status": "running", "timings": timings}, indent=2),
            encoding="utf-8",
        )
        print(f"{stage}: {metrics}", flush=True)

    started = perf_counter()
    alignment_config = AlignmentConfig()
    output_level = parse_alignment_output_level(args.output_level)
    emit_region_audit = _emit_region_audit(output_level)
    peak_config = _peak_config(
        args.raw_dir.resolve(),
        args.dll_dir.resolve(),
        output_dir,
        _alignment_production_resolver_mode(args.resolver_mode),
    )

    with _stage("read_batch_index", timings):
        batch = read_discovery_batch_index(args.discovery_batch_index.resolve())
    checkpoint("read_batch_index", sample_count=len(batch.sample_order))

    with _stage("read_candidates", timings) as metrics:
        candidates = tuple(
            candidate
            for sample_stem in batch.sample_order
            for candidate in read_discovery_candidates_csv(
                batch.candidate_csvs[sample_stem]
            )
        )
        metrics["candidate_count"] = len(candidates)
    checkpoint("read_candidates", candidate_count=len(candidates))

    with _stage("resolve_raw_paths", timings):
        raw_paths = existing_raw_paths(
            sample_order=batch.sample_order,
            raw_files=batch.raw_files,
            raw_dir=args.raw_dir.resolve(),
        )
    checkpoint("resolve_raw_paths", raw_count=len(raw_paths))

    with _stage("build_owners", timings):
        owner_output = run_owner_build_process(
            candidates,
            sample_order=batch.sample_order,
            raw_paths=raw_paths,
            dll_dir=args.dll_dir.resolve(),
            alignment_config=alignment_config,
            peak_config=peak_config,
            max_workers=args.raw_workers,
            raw_xic_batch_size=args.raw_xic_batch_size,
            emit_region_audit=emit_region_audit,
        )
    checkpoint(
        "build_owners",
        owner_count=len(owner_output.ownership.owners),
        ambiguous_record_count=len(owner_output.ownership.ambiguous_records),
    )

    with _stage("cluster_owners", timings):
        owner_features = cluster_sample_local_owners(
            owner_output.ownership.owners,
            config=alignment_config,
        )
        owner_features = (
            *owner_features,
            *review_only_features_from_ambiguous_records(
                owner_output.ownership.ambiguous_records,
                start_index=len(owner_features) + 1,
            ),
        )
    checkpoint("cluster_owners", feature_count=len(owner_features))

    if args.preconsolidate_owner_families:
        with _stage("pre_backfill_consolidation", timings):
            owner_features = consolidate_pre_backfill_identity_families(
                owner_features,
                config=alignment_config,
            )
        checkpoint("pre_backfill_consolidation", feature_count=len(owner_features))

    with _stage("backfill_scope", timings):
        scope_selection = select_backfill_features(
            owner_features,
            sample_order=batch.sample_order,
            raw_sample_stems=frozenset(raw_paths),
            alignment_config=alignment_config,
            scope=args.backfill_scope,
        )
        request_summary = _request_summary(
            scope_selection.features,
            sample_order=batch.sample_order,
            raw_sample_stems=frozenset(raw_paths),
            alignment_config=alignment_config,
        )
    checkpoint(
        "backfill_scope",
        input_feature_count=len(owner_features),
        backfill_feature_count=len(scope_selection.features),
        skipped_feature_count=len(owner_features) - len(scope_selection.features),
        **skipped_evidence_summary(scope_selection.skipped),
        **request_summary["totals"],
    )
    locality_summary: _LocalitySummary | None = None
    if args.emit_locality:
        with _stage("backfill_locality", timings):
            locality_summary = _locality_summary(
                scope_selection.features,
                sample_order=batch.sample_order,
                raw_paths=raw_paths,
                dll_dir=args.dll_dir.resolve(),
                alignment_config=alignment_config,
                raw_xic_batch_size=args.raw_xic_batch_size,
            )
        checkpoint(
            "backfill_locality",
            **locality_summary["totals"],  # type: ignore[arg-type]
        )

    result = {
        "status": "complete",
        "elapsed_sec": perf_counter() - started,
        "discovery_batch_index": str(args.discovery_batch_index.resolve()),
        "raw_dir": str(args.raw_dir.resolve()),
        "dll_dir": str(args.dll_dir.resolve()),
        "raw_workers": args.raw_workers,
        "raw_xic_batch_size": args.raw_xic_batch_size,
        "output_level": output_level,
        "backfill_scope": args.backfill_scope,
        "candidate_count": len(candidates),
        "raw_count": len(raw_paths),
        "owner_count": len(owner_output.ownership.owners),
        "ambiguous_record_count": len(owner_output.ownership.ambiguous_records),
        "input_feature_count": len(owner_features),
        "backfill_feature_count": len(scope_selection.features),
        "skipped_feature_count": len(owner_features) - len(scope_selection.features),
        **skipped_evidence_summary(scope_selection.skipped),
        **request_summary["totals"],
        "locality": locality_summary["totals"] if locality_summary else {},
        "timings": timings,
    }
    _write_tsv(
        output_dir / "backfill_scope_probe_sample_requests.tsv",
        request_summary["sample_rows"],
    )
    _write_tsv(
        output_dir / "backfill_scope_probe_feature_requests.tsv",
        request_summary["feature_rows"],
    )
    if locality_summary is not None:
        _write_tsv(
            output_dir / "backfill_scope_probe_sample_locality.tsv",
            locality_summary["sample_rows"],  # type: ignore[arg-type]
        )
    (output_dir / "backfill_scope_probe.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    status_path.write_text(
        json.dumps({"status": "complete", "result": result}, indent=2),
        encoding="utf-8",
    )
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe alignment backfill scope size without running owner backfill."
        ),
    )
    parser.add_argument("--discovery-batch-index", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--output-level",
        default="validation",
        choices=(
            "production",
            "machine",
            "debug",
            "validation",
            "validation-minimal",
        ),
    )
    parser.add_argument(
        "--resolver-mode",
        default="region_first_safe_merge",
        choices=("local_minimum", "region_first_safe_merge"),
    )
    parser.add_argument(
        "--backfill-scope",
        default="production-equivalent",
        choices=("full-audit", "production-equivalent"),
    )
    parser.add_argument("--raw-workers", type=int, default=1)
    parser.add_argument("--raw-xic-batch-size", type=int, default=1)
    parser.add_argument("--preconsolidate-owner-families", action="store_true")
    parser.add_argument(
        "--emit-locality",
        action="store_true",
        help=(
            "Open RAW files only for scan-window lookups and estimate owner "
            "backfill raw chromatogram call locality without extracting XICs."
        ),
    )
    return parser.parse_args(argv)


def _emit_region_audit(output_level: AlignmentOutputLevel) -> bool:
    artifacts = set(artifact_names_for_output_level(output_level))
    return "alignment_cells.tsv" in artifacts


class _stage:
    def __init__(self, name: str, timings: list[dict[str, object]]) -> None:
        self.name = name
        self.timings = timings
        self.metrics: dict[str, object] = {}
        self._start = 0.0

    def __enter__(self) -> dict[str, object]:
        self._start = perf_counter()
        return self.metrics

    def __exit__(self, *_exc: object) -> None:
        self.timings.append(
            {
                "stage": self.name,
                "elapsed_sec": perf_counter() - self._start,
                "metrics": dict(self.metrics),
            }
        )


def _request_summary(
    features: OwnerGroupDeliveryFeatures,
    *,
    sample_order: tuple[str, ...],
    raw_sample_stems: frozenset[str],
    alignment_config: AlignmentConfig,
) -> _RequestSummary:
    request_plan = build_owner_backfill_request_plan(
        features,
        sample_order=sample_order,
        raw_sample_stems=raw_sample_stems,
        alignment_config=alignment_config,
    )
    feature_rows: list[dict[str, object]] = []
    feature_request_samples: dict[int, set[str]] = defaultdict(set)
    feature_extract_counts: Counter[int] = Counter()
    sample_counts: Counter[str] = Counter()
    sample_seed_counts: Counter[str] = Counter()
    for sample_stem in sample_order:
        sample_feature_ids: set[int] = set()
        for item in request_plan.requests_for_sample(sample_stem):
            feature_id = id(item.feature)
            sample_feature_ids.add(feature_id)
            feature_request_samples[feature_id].add(sample_stem)
            feature_extract_counts[feature_id] += 1
            sample_seed_counts[sample_stem] += 1
        sample_counts[sample_stem] = len(sample_feature_ids)

    for feature in features:
        feature_id = id(feature)
        seed_count = len(backfill_seed_centers(feature))
        request_target_count = len(feature_request_samples.get(feature_id, ()))
        extract_request_count = feature_extract_counts[feature_id]
        feature_rows.append(
            {
                "feature_family_id": feature.feature_family_id,
                "neutral_loss_tag": feature.neutral_loss_tag,
                "evidence": feature.evidence,
                "review_only": feature.review_only,
                "detected_sample_count": len(
                    {owner.sample_stem for owner in feature.owners}
                ),
                "seed_center_count": seed_count,
                "request_target_count": request_target_count,
                "extract_request_count": extract_request_count,
            }
        )
    sample_rows = [
        {
            "sample_stem": sample,
            "request_target_count": sample_counts[sample],
            "extract_request_count": sample_seed_counts[sample],
        }
        for sample in sample_order
    ]
    totals: dict[str, object] = {
        "request_target_count": sum(sample_counts.values()),
        "extract_request_count": sum(sample_seed_counts.values()),
        "max_sample_extract_request_count": (
            max(sample_seed_counts.values()) if sample_seed_counts else 0
        ),
        "median_sample_extract_request_count": _median_counter(sample_seed_counts),
    }
    return {
        "totals": totals,
        "sample_rows": sample_rows,
        "feature_rows": sorted(
            feature_rows,
            key=_feature_request_row_sort_key,
        ),
    }


def _feature_request_row_sort_key(row: Mapping[str, object]) -> tuple[int, str]:
    extract_request_count = row.get("extract_request_count", 0)
    if not isinstance(extract_request_count, int):
        extract_request_count = int(str(extract_request_count))
    return -extract_request_count, str(row["feature_family_id"])


def _locality_summary(
    features: OwnerGroupDeliveryFeatures,
    *,
    sample_order: tuple[str, ...],
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    alignment_config: AlignmentConfig,
    raw_xic_batch_size: int,
    open_raw_func=open_raw,
) -> _LocalitySummary:
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    raw_sample_stems = frozenset(raw_paths)
    request_plan = build_owner_backfill_request_plan(
        features,
        sample_order=sample_order,
        raw_sample_stems=raw_sample_stems,
        alignment_config=alignment_config,
    )
    sample_rows: list[dict[str, object]] = []
    total_requests = 0
    total_chunks = 0
    total_chunked_raw_calls = 0
    total_unique_windows = 0
    total_overlap_components = 0
    total_superwindow_x1 = 0
    total_superwindow_x2 = 0
    total_superwindow_x4 = 0
    max_overlap_component_span = 0
    max_individual_span = 0
    for sample_stem in sample_order:
        items = request_plan.requests_for_sample(sample_stem)
        raw_path = raw_paths.get(sample_stem)
        if raw_path is None or not items:
            row = _locality_sample_row(
                sample_stem=sample_stem,
                request_count=0,
                chunk_count=0,
                chunked_raw_call_count=0,
                unique_scan_window_count=0,
            )
            sample_rows.append(row)
            continue
        with open_raw_func(raw_path, dll_dir) as source:
            chunks = _scan_window_aware_chunks(
                source,
                items,
                raw_xic_batch_size,
            )
            windows_by_request = {
                item.request: _scan_window_for_request(source, item.request)
                for item in items
            }
            windows = tuple(windows_by_request[item.request] for item in items)
            chunked_raw_call_count = sum(
                len({windows_by_request[item.request] for item in chunk})
                for chunk in chunks
            )
        overlap = _overlap_window_summary(windows)
        request_count = len(items)
        chunk_count = len(chunks)
        unique_scan_window_count = len(set(windows))
        total_requests += request_count
        total_chunks += chunk_count
        total_chunked_raw_calls += chunked_raw_call_count
        total_unique_windows += unique_scan_window_count
        total_overlap_components += overlap["overlap_component_count"]
        total_superwindow_x1 += overlap["superwindow_call_count_span_x1"]
        total_superwindow_x2 += overlap["superwindow_call_count_span_x2"]
        total_superwindow_x4 += overlap["superwindow_call_count_span_x4"]
        max_overlap_component_span = max(
            max_overlap_component_span,
            overlap["max_overlap_component_scan_span"],
        )
        max_individual_span = max(
            max_individual_span,
            overlap["max_individual_scan_span"],
        )
        sample_rows.append(
            _locality_sample_row(
                sample_stem=sample_stem,
                request_count=request_count,
                chunk_count=chunk_count,
                chunked_raw_call_count=chunked_raw_call_count,
                unique_scan_window_count=unique_scan_window_count,
            )
        )
    return {
        "totals": {
            "extract_request_count": total_requests,
            "scan_window_aware_chunk_count": total_chunks,
            "chunked_raw_chromatogram_call_count": total_chunked_raw_calls,
            "unique_scan_window_count": total_unique_windows,
            "mean_xic_per_chunked_raw_call": _safe_ratio(
                total_requests,
                total_chunked_raw_calls,
            ),
            "overlap_component_count": total_overlap_components,
            "max_overlap_component_scan_span": max_overlap_component_span,
            "max_individual_scan_span": max_individual_span,
            "superwindow_call_count_span_x1": total_superwindow_x1,
            "superwindow_call_count_span_x2": total_superwindow_x2,
            "superwindow_call_count_span_x4": total_superwindow_x4,
        },
        "sample_rows": sample_rows,
    }


def _scan_window_for_request(source: object, request: XICRequest) -> tuple[int, int]:
    resolver = getattr(source, "scan_window_for_request", None)
    if callable(resolver):
        start_scan, end_scan = resolver(request)
        return int(start_scan), int(end_scan)
    raw_file = getattr(source, "_raw_file", source)
    scan_number_from_rt = getattr(raw_file, "ScanNumberFromRetentionTime", None)
    if not callable(scan_number_from_rt):
        raise AttributeError("RAW source cannot resolve scan number from RT")
    return (
        int(scan_number_from_rt(request.rt_min)),
        int(scan_number_from_rt(request.rt_max)),
    )


def _locality_sample_row(
    *,
    sample_stem: str,
    request_count: int,
    chunk_count: int,
    chunked_raw_call_count: int,
    unique_scan_window_count: int,
) -> dict[str, object]:
    return {
        "sample_stem": sample_stem,
        "extract_request_count": request_count,
        "scan_window_aware_chunk_count": chunk_count,
        "chunked_raw_chromatogram_call_count": chunked_raw_call_count,
        "unique_scan_window_count": unique_scan_window_count,
        "mean_xic_per_chunked_raw_call": _safe_ratio(
            request_count,
            chunked_raw_call_count,
        ),
    }


def _overlap_window_summary(windows: tuple[tuple[int, int], ...]) -> dict[str, int]:
    if not windows:
        return {
            "overlap_component_count": 0,
            "max_overlap_component_scan_span": 0,
            "max_individual_scan_span": 0,
            "superwindow_call_count_span_x1": 0,
            "superwindow_call_count_span_x2": 0,
            "superwindow_call_count_span_x4": 0,
        }
    sorted_windows = tuple(sorted(windows))
    components = _merge_overlapping_windows(sorted_windows)
    max_individual_span = max(_scan_span(window) for window in sorted_windows)
    return {
        "overlap_component_count": len(components),
        "max_overlap_component_scan_span": max(
            _scan_span(window) for window in components
        ),
        "max_individual_scan_span": max_individual_span,
        "superwindow_call_count_span_x1": _capped_overlap_window_count(
            sorted_windows,
            max_span=max_individual_span,
        ),
        "superwindow_call_count_span_x2": _capped_overlap_window_count(
            sorted_windows,
            max_span=max_individual_span * 2,
        ),
        "superwindow_call_count_span_x4": _capped_overlap_window_count(
            sorted_windows,
            max_span=max_individual_span * 4,
        ),
    }


def _merge_overlapping_windows(
    sorted_windows: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    merged: list[tuple[int, int]] = []
    current_start, current_end = sorted_windows[0]
    for start, end in sorted_windows[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
            continue
        merged.append((current_start, current_end))
        current_start, current_end = start, end
    merged.append((current_start, current_end))
    return tuple(merged)


def _capped_overlap_window_count(
    sorted_windows: tuple[tuple[int, int], ...],
    *,
    max_span: int,
) -> int:
    count = 0
    current_start, current_end = sorted_windows[0]
    for start, end in sorted_windows[1:]:
        merged_end = max(current_end, end)
        if start <= current_end and merged_end - current_start <= max_span:
            current_end = merged_end
            continue
        count += 1
        current_start, current_end = start, end
    return count + 1


def _scan_span(window: tuple[int, int]) -> int:
    return max(0, window[1] - window[0])


def _safe_ratio(numerator: int, denominator: int) -> float | str:
    if denominator == 0:
        return ""
    return numerator / denominator


def _median_counter(counter: Counter[str]) -> float:
    values = sorted(counter.values())
    if not values:
        return 0.0
    midpoint = len(values) // 2
    if len(values) % 2:
        return float(values[midpoint])
    return (values[midpoint - 1] + values[midpoint]) / 2.0


def _write_tsv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    write_tsv(
        path,
        rows,
        tuple(rows[0]),
        extrasaction="raise",
        formatter=_format_tsv_value,
    )


def _format_tsv_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
