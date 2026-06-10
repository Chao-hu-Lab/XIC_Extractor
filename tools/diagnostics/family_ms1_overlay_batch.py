"""Render queued family MS1 overlays from a backfill review report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics import family_ms1_overlay_plot as overlay_plot

_DEFAULT_LOAD_FAMILY_CELLS = overlay_plot.load_family_cells
_DEFAULT_EXTRACT_FAMILY_TRACE_ROWS = overlay_plot.extract_family_trace_rows

REQUIRED_QUEUE_COLUMNS = (
    "feature_family_id",
    "family_center_mz",
    "family_center_rt",
    "suggested_rt_min",
    "suggested_rt_max",
    "suggested_output_prefix",
)
SUPPORT_FAMILY_VERDICT = "ms1_shape_supports_family_backfill"
TOP30_EXPANSION_ELIGIBLE = "eligible"
TOP30_EXPANSION_BLOCKED = "blocked"
OVERLAY_BATCH_SOURCE = "family_ms1_overlay_batch_v1"
OVERLAY_SUPERWINDOW_SPAN_FACTOR = 2
OverlayTraceItem = tuple[int, overlay_plot.FamilyCell, str, Any]
WindowedOverlayTraceItem = tuple[int, OverlayTraceItem, tuple[int, int]]


@dataclass(frozen=True)
class OverlayBatchRequest:
    rank: int
    family_id: str
    seed_group_id: str
    mz: float
    ppm: float
    rt_min: float
    rt_max: float
    family_center_rt: float | None
    output_prefix: str


@dataclass
class OverlayExtractionStats:
    sample_stems: set[str]
    raw_open_count: int = 0
    extract_xic_batch_count: int = 0
    extract_xic_count: int = 0
    raw_chromatogram_call_count: int = 0
    trace_point_count: int = 0
    exact_scan_window_count: int = 0
    superwindow_group_count: int = 0
    superwindow_fallback_sample_count: int = 0

    @classmethod
    def empty(cls) -> "OverlayExtractionStats":
        return cls(sample_stems=set())

    def to_metrics(self) -> dict[str, int | float | str]:
        raw_calls = self.raw_chromatogram_call_count
        return {
            "sample_count": len(self.sample_stems),
            "sample_stems": ",".join(sorted(self.sample_stems)),
            "raw_open_count": self.raw_open_count,
            "extract_xic_batch_count": self.extract_xic_batch_count,
            "extract_xic_count": self.extract_xic_count,
            "raw_chromatogram_call_count": raw_calls,
            "mean_xic_per_raw_chromatogram_call": (
                0.0 if raw_calls == 0 else self.extract_xic_count / raw_calls
            ),
            "trace_point_count": self.trace_point_count,
            "exact_scan_window_count": self.exact_scan_window_count,
            "superwindow_group_count": self.superwindow_group_count,
            "superwindow_fallback_sample_count": self.superwindow_fallback_sample_count,
            "superwindow_span_factor": OVERLAY_SUPERWINDOW_SPAN_FACTOR,
        }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        metrics: dict[str, Any] = {}
        rows = run_overlay_batch(
            review_queue_tsv=args.review_queue_tsv,
            alignment_cells=args.alignment_cells,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            output_dir=args.output_dir,
            limit=args.limit,
            start_rank=args.start_rank,
            ppm=args.ppm,
            max_highlight_rescued=args.max_highlight_rescued,
            reuse_existing=args.reuse_existing,
            write_pdf=not args.no_pdf,
            evidence_only=args.evidence_only,
            write_incremental=True,
            metrics=metrics,
        )
        _write_outputs(args.output_dir, rows, metrics=metrics)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    failed = [row for row in rows if row["status"] == "failed"]
    print(f"family MS1 overlay batch: {args.output_dir}")
    return 2 if failed else 0


def run_overlay_batch(
    *,
    review_queue_tsv: Path,
    alignment_cells: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    limit: int = 10,
    start_rank: int = 1,
    ppm: float = 10.0,
    max_highlight_rescued: int = 8,
    reuse_existing: bool = False,
    write_pdf: bool = True,
    evidence_only: bool = False,
    write_incremental: bool = False,
    metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("--limit must be >= 1")
    if start_rank < 1:
        raise ValueError("--start-rank must be >= 1")

    requests = _load_requests(
        review_queue_tsv,
        start_rank=start_rank,
        limit=limit,
        default_ppm=ppm,
    )
    source_provenance = _source_provenance(
        review_queue_tsv=review_queue_tsv,
        alignment_cells=alignment_cells,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    pending_requests: list[OverlayBatchRequest] = []
    existing_by_rank: dict[int, dict[str, Any]] = {}
    reused_existing_count = 0
    for request in requests:
        try:
            existing = (
                _existing_success_row(
                    request,
                    output_dir,
                    source_provenance=source_provenance,
                    write_pdf=write_pdf,
                    evidence_only=evidence_only,
                )
                if reuse_existing
                else None
            )
            if existing is not None:
                existing_by_rank[request.rank] = existing
                reused_existing_count += 1
            else:
                pending_requests.append(request)
        except Exception as exc:  # noqa: BLE001 - diagnostic batch must continue.
            existing_by_rank[request.rank] = _failure_row(request, exc)
    extraction_stats = OverlayExtractionStats.empty()
    fast_trace_rows = _batch_trace_rows_for_requests(
        pending_requests,
        alignment_cells=alignment_cells,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        max_highlight_rescued=max_highlight_rescued,
        extraction_stats=extraction_stats,
    )
    for request in requests:
        if request.rank in existing_by_rank:
            rows.append(existing_by_rank[request.rank])
        else:
            try:
                rows.append(
                    _render_family(
                        request,
                        alignment_cells=alignment_cells,
                        raw_dir=raw_dir,
                        dll_dir=dll_dir,
                        output_dir=output_dir,
                        max_highlight_rescued=max_highlight_rescued,
                        source_provenance=source_provenance,
                        write_pdf=write_pdf,
                        evidence_only=evidence_only,
                        trace_rows=fast_trace_rows.get(request.rank),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - diagnostic batch must continue.
                rows.append(_failure_row(request, exc))
        if write_incremental:
            _write_outputs(output_dir, rows)
    if metrics is not None:
        metrics.update(
            {
                "selected_row_count": len(requests),
                "pending_row_count": len(pending_requests),
                "reused_existing_row_count": reused_existing_count,
                "failed_existing_probe_count": sum(
                    1
                    for row in existing_by_rank.values()
                    if row.get("status") == "failed"
                ),
                "fast_path_used": bool(pending_requests and fast_trace_rows),
            }
        )
        metrics.update(extraction_stats.to_metrics())
    return rows


def _existing_success_row(
    request: OverlayBatchRequest,
    output_dir: Path,
    *,
    source_provenance: Mapping[str, object],
    write_pdf: bool,
    evidence_only: bool,
) -> dict[str, Any] | None:
    outputs = _request_output_paths(
        request,
        output_dir,
        write_pdf=write_pdf,
        evidence_only=evidence_only,
    )
    required_outputs = [path for path in outputs.values() if path is not None]
    if any(not path.exists() for path in required_outputs):
        return None
    trace_data_json = outputs["trace_data_json"]
    if trace_data_json is None:
        return None
    try:
        payload = json.loads(trace_data_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not _existing_payload_matches_request(
        payload,
        request,
        source_provenance=source_provenance,
    ):
        return None
    evidence = payload.get("evidence_summary")
    if not isinstance(evidence, Mapping):
        return None
    return _success_row_from_evidence(
        request,
        outputs=outputs,
        evidence=evidence,
        evidence_only=evidence_only,
    )


def _existing_payload_matches_request(
    payload: Mapping[str, Any],
    request: OverlayBatchRequest,
    *,
    source_provenance: Mapping[str, object],
) -> bool:
    provenance = payload.get("provenance")
    if not isinstance(provenance, Mapping):
        return False
    return (
        str(payload.get("family_id", "")).strip() == request.family_id
        and _existing_provenance_matches_request(
            provenance,
            request,
            source_provenance=source_provenance,
        )
        and _payload_float_matches(payload.get("mz"), request.mz)
        and _payload_float_matches(payload.get("ppm"), request.ppm)
        and _payload_float_matches(payload.get("rt_min"), request.rt_min)
        and _payload_float_matches(payload.get("rt_max"), request.rt_max)
    )


def _payload_float_matches(value: object, expected: float) -> bool:
    observed = _optional_float(value)
    if observed is None:
        return False
    tolerance = max(1e-6, abs(expected) * 1e-9)
    return abs(observed - expected) <= tolerance


def _render_family(
    request: OverlayBatchRequest,
    *,
    alignment_cells: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    max_highlight_rescued: int,
    source_provenance: Mapping[str, object],
    write_pdf: bool,
    evidence_only: bool,
    trace_rows: Sequence[overlay_plot.TraceOverlayRow] | None = None,
) -> dict[str, Any]:
    if trace_rows is None:
        cells = overlay_plot.load_family_cells(alignment_cells, request.family_id)
        trace_rows = overlay_plot.extract_family_trace_rows(
            cells=cells,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            mz=request.mz,
            rt_min=request.rt_min,
            rt_max=request.rt_max,
            ppm=request.ppm,
            max_highlight_rescued=max_highlight_rescued,
        )
    provenance = _request_provenance(
        request,
        source_provenance=source_provenance,
    )
    if evidence_only:
        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = _request_output_paths(
            request,
            output_dir,
            write_pdf=False,
            evidence_only=True,
        )
        summary_tsv = outputs["trace_summary_tsv"]
        trace_data_json = outputs["trace_data_json"]
        if summary_tsv is None or trace_data_json is None:
            raise ValueError("evidence-only row requires summary TSV and trace JSON")
        overlay_plot._write_summary(summary_tsv, trace_rows)
        overlay_plot._write_trace_data(
            trace_data_json,
            rows=trace_rows,
            family_id=request.family_id,
            mz=request.mz,
            ppm=request.ppm,
            rt_min=request.rt_min,
            rt_max=request.rt_max,
            family_center_rt=request.family_center_rt,
            provenance=provenance,
        )
    else:
        outputs = overlay_plot.write_family_ms1_overlay_outputs(
            rows=trace_rows,
            output_dir=output_dir,
            output_prefix=request.output_prefix,
            family_id=request.family_id,
            mz=request.mz,
            ppm=request.ppm,
            rt_min=request.rt_min,
            rt_max=request.rt_max,
            family_center_rt=request.family_center_rt,
            provenance=provenance,
            write_pdf=write_pdf,
        )
    evidence = overlay_plot.build_family_ms1_evidence_summary(trace_rows)
    return _success_row_from_evidence(
        request,
        outputs=outputs,
        evidence=evidence,
        evidence_only=evidence_only,
    )


def _batch_trace_rows_for_requests(
    requests: Sequence[OverlayBatchRequest],
    *,
    alignment_cells: Path,
    raw_dir: Path,
    dll_dir: Path,
    max_highlight_rescued: int,
    extraction_stats: OverlayExtractionStats | None = None,
) -> dict[int, list[overlay_plot.TraceOverlayRow]]:
    if not requests:
        return {}
    if (
        overlay_plot.load_family_cells is not _DEFAULT_LOAD_FAMILY_CELLS
        or overlay_plot.extract_family_trace_rows
        is not _DEFAULT_EXTRACT_FAMILY_TRACE_ROWS
    ):
        return {}
    cells_by_family = overlay_plot.load_family_cells_for_families(
        alignment_cells,
        tuple(request.family_id for request in requests),
    )
    return _extract_batch_family_trace_rows(
        requests,
        cells_by_family=cells_by_family,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        max_highlight_rescued=max_highlight_rescued,
        extraction_stats=extraction_stats,
    )


def _extract_batch_family_trace_rows(
    requests: Sequence[OverlayBatchRequest],
    *,
    cells_by_family: Mapping[str, Sequence[overlay_plot.FamilyCell]],
    raw_dir: Path,
    dll_dir: Path,
    max_highlight_rescued: int,
    open_raw_func: Any | None = None,
    extraction_stats: OverlayExtractionStats | None = None,
) -> dict[int, list[overlay_plot.TraceOverlayRow]]:
    from xic_extractor.raw_reader import open_raw as default_open_raw
    from xic_extractor.xic_models import XICRequest

    open_raw_func = open_raw_func or default_open_raw
    sample_items: dict[
        str,
        list[tuple[int, overlay_plot.FamilyCell, str, XICRequest]],
    ] = {}
    order_by_rank: dict[int, dict[str, int]] = {}
    for request in requests:
        cells = tuple(cells_by_family.get(request.family_id, ()))
        if not cells:
            raise ValueError(
                f"No alignment cells found for family `{request.family_id}`"
            )
        groups = overlay_plot.assign_highlight_groups(
            cells,
            max_highlight_rescued=max_highlight_rescued,
        )
        order_by_rank[request.rank] = {
            cell.sample_stem: index for index, cell in enumerate(cells)
        }
        xic_request = XICRequest(
            mz=request.mz,
            rt_min=request.rt_min,
            rt_max=request.rt_max,
            ppm_tol=request.ppm,
        )
        for cell in cells:
            sample_items.setdefault(cell.sample_stem, []).append(
                (request.rank, cell, groups[cell.sample_stem], xic_request)
            )

    rows_by_rank: dict[int, list[overlay_plot.TraceOverlayRow]] = {
        request.rank: [] for request in requests
    }
    for sample_stem in sorted(sample_items):
        raw_path = raw_dir / f"{sample_stem}.raw"
        if not raw_path.is_file():
            raise FileNotFoundError(f"RAW file not found: {raw_path}")
        items = sample_items[sample_stem]
        with open_raw_func(raw_path, dll_dir) as raw:
            raw_call_count_before = _raw_chromatogram_call_count(raw)
            traces = _extract_overlay_traces(
                raw,
                items,
                extraction_stats=extraction_stats,
            )
            raw_call_count_after = _raw_chromatogram_call_count(raw)
        if extraction_stats is not None:
            extraction_stats.sample_stems.add(sample_stem)
            extraction_stats.raw_open_count += 1
            extraction_stats.extract_xic_count += len(items)
            extraction_stats.raw_chromatogram_call_count += _raw_call_delta(
                raw_call_count_before,
                raw_call_count_after,
            )
            extraction_stats.trace_point_count += sum(
                len(trace.intensity) for trace in traces
            )
        for (rank, cell, group, _request), trace in zip(
            items,
            traces,
            strict=True,
        ):
            rows_by_rank[rank].append(
                overlay_plot.trace_row_from_arrays(
                    cell,
                    group,
                    trace.rt,
                    trace.intensity,
                )
            )
    for rank, rows in rows_by_rank.items():
        sample_order = order_by_rank[rank]
        rows.sort(key=lambda row: sample_order.get(row.sample_stem, len(sample_order)))
    return rows_by_rank


def _extract_overlay_traces(
    raw: object,
    items: Sequence[OverlayTraceItem],
    *,
    extraction_stats: OverlayExtractionStats | None = None,
):
    groups = _overlay_superwindow_groups(
        raw,
        items,
        superwindow_span_factor=OVERLAY_SUPERWINDOW_SPAN_FACTOR,
    )
    if groups is None:
        if extraction_stats is not None:
            extraction_stats.superwindow_fallback_sample_count += 1
            extraction_stats.extract_xic_batch_count += 1 if items else 0
        return tuple(raw.extract_xic_many(tuple(item[3] for item in items)))

    from xic_extractor.raw_reader import RawReaderError
    from xic_extractor.xic_models import XICRequest

    if extraction_stats is not None:
        extraction_stats.exact_scan_window_count += len(
            {
                scan_window
                for group in groups
                for _index, _item, scan_window in group
            }
        )
        extraction_stats.superwindow_group_count += len(groups)
        extraction_stats.extract_xic_batch_count += len(groups)

    traces: list[Any | None] = [None] * len(items)
    for group in groups:
        union_start = min(scan_window[0] for _index, _item, scan_window in group)
        union_end = max(scan_window[1] for _index, _item, scan_window in group)
        union_rt_min = _retention_time_for_scan(raw, union_start)
        union_rt_max = _retention_time_for_scan(raw, union_end)
        if union_rt_min is None or union_rt_max is None:
            raise RawReaderError("overlay super-window RT lookup became unavailable")
        if union_rt_min > union_rt_max:
            union_rt_min, union_rt_max = union_rt_max, union_rt_min
        union_requests = tuple(
            XICRequest(
                mz=item[3].mz,
                rt_min=union_rt_min,
                rt_max=union_rt_max,
                ppm_tol=item[3].ppm_tol,
            )
            for _index, item, _scan_window in group
        )
        union_traces = tuple(raw.extract_xic_many(union_requests))
        for trace, (index, _item, scan_window) in zip(
            union_traces,
            group,
            strict=True,
        ):
            traces[index] = _crop_trace_to_scan_window(raw, trace, scan_window)
    if any(trace is None for trace in traces):
        raise RawReaderError(
            "overlay super-window extraction returned incomplete traces",
        )
    return tuple(trace for trace in traces if trace is not None)


def _overlay_superwindow_groups(
    raw: object,
    items: Sequence[OverlayTraceItem],
    *,
    superwindow_span_factor: int,
) -> tuple[tuple[WindowedOverlayTraceItem, ...], ...] | None:
    windowed_items: list[WindowedOverlayTraceItem] = []
    for index, item in enumerate(items):
        scan_window = _scan_window_for_request(raw, item[3])
        if scan_window is None:
            return None
        if _retention_time_for_scan(raw, scan_window[0]) is None:
            return None
        if _retention_time_for_scan(raw, scan_window[1]) is None:
            return None
        windowed_items.append((index, item, scan_window))
    if not windowed_items:
        return ()

    ordered = tuple(
        sorted(
            windowed_items,
            key=lambda item: (
                item[2][0],
                item[2][1],
                item[1][3].mz,
                item[1][1].sample_stem,
                item[0],
            ),
        )
    )
    groups: list[WindowedOverlayTraceItem] = []
    output: list[tuple[WindowedOverlayTraceItem, ...]] = []
    current_start = 0
    current_end = 0
    current_max_span = 1
    for windowed_item in ordered:
        scan_start, scan_end = windowed_item[2]
        item_span = _scan_span(scan_start, scan_end)
        if not groups:
            groups = [windowed_item]
            current_start = scan_start
            current_end = scan_end
            current_max_span = item_span
            continue

        proposed_start = min(current_start, scan_start)
        proposed_end = max(current_end, scan_end)
        proposed_max_span = max(current_max_span, item_span)
        overlaps_current = scan_start <= current_end
        within_span_limit = (
            _scan_span(proposed_start, proposed_end)
            <= proposed_max_span * superwindow_span_factor
        )
        if overlaps_current and within_span_limit:
            groups.append(windowed_item)
            current_start = proposed_start
            current_end = proposed_end
            current_max_span = proposed_max_span
            continue

        output.append(tuple(groups))
        groups = [windowed_item]
        current_start = scan_start
        current_end = scan_end
        current_max_span = item_span
    if groups:
        output.append(tuple(groups))
    return tuple(output)


def _crop_trace_to_scan_window(
    raw: object,
    trace: Any,
    scan_window: tuple[int, int],
):
    from xic_extractor.xic_models import XICTrace

    rt_min = _retention_time_for_scan(raw, scan_window[0])
    rt_max = _retention_time_for_scan(raw, scan_window[1])
    if rt_min is None or rt_max is None:
        return trace
    if rt_min > rt_max:
        rt_min, rt_max = rt_max, rt_min
    mask = (trace.rt >= rt_min) & (trace.rt <= rt_max)
    return XICTrace.from_arrays(trace.rt[mask], trace.intensity[mask])


def _scan_window_for_request(raw: object, request: Any) -> tuple[int, int] | None:
    resolver = getattr(raw, "scan_window_for_request", None)
    if not callable(resolver):
        return None
    try:
        start_scan, end_scan = resolver(request)
    except (AttributeError, NotImplementedError):
        return None
    return int(start_scan), int(end_scan)


def _retention_time_for_scan(raw: object, scan_number: int) -> float | None:
    resolver = getattr(raw, "retention_time_for_scan", None)
    if not callable(resolver):
        return None
    try:
        return float(resolver(scan_number))
    except (AttributeError, NotImplementedError):
        return None


def _scan_span(start_scan: int, end_scan: int) -> int:
    return max(1, abs(end_scan - start_scan) + 1)


def _raw_chromatogram_call_count(raw: object) -> int | None:
    value = getattr(raw, "raw_chromatogram_call_count", None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _raw_call_delta(before: int | None, after: int | None) -> int:
    if before is None or after is None:
        return 0
    return max(0, after - before)


def _request_output_paths(
    request: OverlayBatchRequest,
    output_dir: Path,
    *,
    write_pdf: bool,
    evidence_only: bool = False,
) -> dict[str, Path | None]:
    prefix = request.output_prefix
    return {
        "png_path": None if evidence_only else output_dir / f"{prefix}.png",
        "pdf_path": (
            output_dir / f"{prefix}.pdf" if write_pdf and not evidence_only else None
        ),
        "trace_summary_tsv": output_dir / f"{prefix}_trace_summary.tsv",
        "trace_data_json": output_dir / f"{prefix}_trace_data.json",
    }


def _success_row_from_evidence(
    request: OverlayBatchRequest,
    *,
    outputs: Mapping[str, Path | None] | overlay_plot.FamilyMs1OverlayOutputs,
    evidence: Mapping[str, Any],
    evidence_only: bool = False,
) -> dict[str, Any]:
    if isinstance(outputs, Mapping):
        png_path = outputs["png_path"]
        pdf_path = outputs["pdf_path"]
        summary_tsv = outputs["trace_summary_tsv"]
        trace_data_json = outputs["trace_data_json"]
    else:
        png_path = outputs.png_path
        pdf_path = outputs.pdf_path
        summary_tsv = outputs.summary_tsv
        trace_data_json = outputs.trace_data_json
    if summary_tsv is None or trace_data_json is None:
        raise ValueError("overlay success row requires summary TSV and trace JSON")
    if not evidence_only and png_path is None:
        raise ValueError(
            "overlay success row requires PNG, summary TSV, and trace JSON",
        )
    return {
        **_request_row(request),
        "status": "success",
        "family_verdict": evidence.get("family_verdict", ""),
        "dda_trigger_limited_ms2_support": evidence.get(
            "dda_trigger_limited_ms2_support",
            "",
        ),
        "detected_count": evidence.get("detected_count", ""),
        "rescued_count": evidence.get("rescued_count", ""),
        "detected_rescued_count": evidence.get("detected_rescued_count", ""),
        "evaluable_trace_count": evidence.get("evaluable_trace_count", ""),
        "global_apex_assessable_trace_count": evidence.get(
            "global_apex_assessable_trace_count",
            "",
        ),
        "global_apex_assessable_fraction": evidence.get(
            "global_apex_assessable_fraction",
            "",
        ),
        "selected_apex_in_trace_window_count": evidence.get(
            "selected_apex_in_trace_window_count",
            "",
        ),
        "selected_apex_in_trace_window_fraction": evidence.get(
            "selected_apex_in_trace_window_fraction",
            "",
        ),
        "local_apex_assessable_trace_count": evidence.get(
            "local_apex_assessable_trace_count",
            "",
        ),
        "global_apex_interference_count": evidence.get(
            "global_apex_interference_count",
            "",
        ),
        "shape_supported_fraction": evidence.get("shape_supported_fraction", ""),
        "absolute_own_max_evaluable_trace_count": evidence.get(
            "absolute_own_max_evaluable_trace_count",
            "",
        ),
        "absolute_own_max_shape_supported_count": evidence.get(
            "absolute_own_max_shape_supported_count",
            "",
        ),
        "absolute_own_max_shape_supported_fraction": evidence.get(
            "absolute_own_max_shape_supported_fraction",
            "",
        ),
        "absolute_trace_apex_assessable_count": evidence.get(
            "absolute_trace_apex_assessable_count",
            "",
        ),
        "absolute_trace_apex_cluster_count": evidence.get(
            "absolute_trace_apex_cluster_count",
            "",
        ),
        "absolute_trace_apex_cluster_fraction": evidence.get(
            "absolute_trace_apex_cluster_fraction",
            "",
        ),
        "absolute_trace_apex_delta_abs_median_min": evidence.get(
            "absolute_trace_apex_delta_abs_median_min",
            "",
        ),
        "global_apex_interference_fraction": evidence.get(
            "global_apex_interference_fraction",
            "",
        ),
        "local_apex_supported_count": evidence.get("local_apex_supported_count", ""),
        "local_apex_supported_fraction": evidence.get(
            "local_apex_supported_fraction",
            "",
        ),
        "png_path": str(png_path) if png_path is not None else "",
        "pdf_path": str(pdf_path) if pdf_path is not None else "",
        "trace_summary_tsv": str(summary_tsv),
        "trace_data_json": str(trace_data_json),
        "failure_reason": "",
    }


def _failure_row(
    request: OverlayBatchRequest,
    exc: Exception,
) -> dict[str, Any]:
    return {
        **_request_row(request),
        "status": "failed",
        "family_verdict": "",
        "dda_trigger_limited_ms2_support": "",
        "detected_count": "",
        "rescued_count": "",
        "detected_rescued_count": "",
        "evaluable_trace_count": "",
        "global_apex_assessable_trace_count": "",
        "global_apex_assessable_fraction": "",
        "selected_apex_in_trace_window_count": "",
        "selected_apex_in_trace_window_fraction": "",
        "local_apex_assessable_trace_count": "",
        "global_apex_interference_count": "",
        "shape_supported_fraction": "",
        "absolute_own_max_evaluable_trace_count": "",
        "absolute_own_max_shape_supported_count": "",
        "absolute_own_max_shape_supported_fraction": "",
        "absolute_trace_apex_assessable_count": "",
        "absolute_trace_apex_cluster_count": "",
        "absolute_trace_apex_cluster_fraction": "",
        "absolute_trace_apex_delta_abs_median_min": "",
        "global_apex_interference_fraction": "",
        "local_apex_supported_count": "",
        "local_apex_supported_fraction": "",
        "png_path": "",
        "pdf_path": "",
        "trace_summary_tsv": "",
        "trace_data_json": "",
        "failure_reason": f"{type(exc).__name__}: {exc}",
    }


def _request_row(request: OverlayBatchRequest) -> dict[str, Any]:
    return {
        "rank": request.rank,
        "feature_family_id": request.family_id,
        "seed_group_id": request.seed_group_id,
        "mz": request.mz,
        "ppm": request.ppm,
        "rt_min": request.rt_min,
        "rt_max": request.rt_max,
        "family_center_rt": request.family_center_rt,
        "output_prefix": request.output_prefix,
    }


def _source_provenance(
    *,
    review_queue_tsv: Path,
    alignment_cells: Path,
    raw_dir: Path,
    dll_dir: Path,
) -> dict[str, object]:
    return {
        "overlay_batch_source": OVERLAY_BATCH_SOURCE,
        "review_queue_tsv": str(review_queue_tsv),
        "review_queue_sha256": _sha256_file(review_queue_tsv),
        "alignment_cells_tsv": str(alignment_cells),
        "alignment_cells_sha256": _sha256_file(alignment_cells),
        "raw_dir": str(raw_dir),
        "dll_dir": str(dll_dir),
    }


def _request_provenance(
    request: OverlayBatchRequest,
    *,
    source_provenance: Mapping[str, object],
) -> dict[str, object]:
    return {
        **dict(source_provenance),
        "seed_group_id": request.seed_group_id,
        "output_prefix": request.output_prefix,
    }


def _existing_provenance_matches_request(
    provenance: Mapping[str, object],
    request: OverlayBatchRequest,
    *,
    source_provenance: Mapping[str, object],
) -> bool:
    expected = _request_provenance(
        request,
        source_provenance=source_provenance,
    )
    return all(
        str(provenance.get(key, "")).strip() == str(value)
        for key, value in expected.items()
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_requests(
    review_queue_tsv: Path,
    *,
    start_rank: int,
    limit: int,
    default_ppm: float,
) -> list[OverlayBatchRequest]:
    with review_queue_tsv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        _require_columns(review_queue_tsv, reader.fieldnames or ())
        rows = list(reader)
    selected = rows[start_rank - 1 : start_rank - 1 + limit]
    requests: list[OverlayBatchRequest] = []
    for offset, row in enumerate(selected, start=start_rank):
        requests.append(
            OverlayBatchRequest(
                rank=offset,
                family_id=_required_text(row, "feature_family_id"),
                seed_group_id=str(row.get("seed_group_id", "")).strip(),
                mz=_queue_mz(row),
                ppm=_queue_ppm(row, default_ppm),
                rt_min=_required_float(row, "suggested_rt_min"),
                rt_max=_required_float(row, "suggested_rt_max"),
                family_center_rt=_optional_float(row.get("family_center_rt")),
                output_prefix=_required_text(row, "suggested_output_prefix"),
            )
        )
    return requests


def _queue_mz(row: Mapping[str, str]) -> float:
    if row.get("backfill_seed_mz"):
        return _required_float(row, "backfill_seed_mz")
    return _required_float(row, "family_center_mz")


def _queue_ppm(row: Mapping[str, str], default_ppm: float) -> float:
    row_ppm = _optional_float(row.get("ppm"))
    if row_ppm is not None:
        return row_ppm
    return default_ppm


def _write_outputs(
    output_dir: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    metrics: Mapping[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = _with_top30_expansion_gate(rows)
    _write_tsv(
        output_dir / "family_ms1_overlay_batch_summary.tsv",
        summary_rows,
        _summary_fields(),
    )
    _write_markdown(
        output_dir / "family_ms1_overlay_batch.md",
        summary_rows,
    )
    if metrics is not None:
        _write_summary_json(
            output_dir / "family_ms1_overlay_batch_summary.json",
            summary_rows,
            metrics=metrics,
        )


def _write_summary_json(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    metrics: Mapping[str, Any],
) -> None:
    statuses = Counter(str(row["status"]) for row in rows)
    path.write_text(
        json.dumps(
            {
                "schema_version": "family_ms1_overlay_batch_summary_v1",
                "requested_row_count": len(rows),
                "status_counts": dict(sorted(statuses.items())),
                "metrics": dict(metrics),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _write_markdown(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    statuses = Counter(str(row["status"]) for row in rows)
    verdicts = Counter(
        str(row.get("family_verdict", ""))
        for row in rows
        if row.get("family_verdict")
    )
    gate = _top30_expansion_gate(rows)
    lines = [
        "# Family MS1 Overlay Batch",
        "",
        "## Verdict",
        "",
        f"- Requested families: {len(rows)}",
        f"- Succeeded: {statuses.get('success', 0)}",
        f"- Failed: {statuses.get('failed', 0)}",
        f"- Top 30 expansion: `{gate}`",
        (
            "- Gate rule: eligible only when every row succeeds with "
            f"`{SUPPORT_FAMILY_VERDICT}`; failed rows, `review_required_*`, "
            "and `insufficient_nl_seed_support` block expansion."
        ),
        f"- Blocking families: {_format_markdown_blockers(rows)}",
        "",
        "## Family Verdict Counts",
        "",
    ]
    if verdicts:
        lines.extend(f"- `{key}`: {value}" for key, value in sorted(verdicts.items()))
    else:
        lines.append("- No successful family verdicts.")
    lines.extend(
        [
            "",
            "## Families",
            "",
            (
                "| rank | family | m/z | RT window | status | family verdict | "
                "coverage | own-max shape | global conflict | DDA-height signal | "
                "failure |"
            ),
            "|---:|---|---:|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(_markdown_family_row(row))
    path.write_text("\n".join(lines), encoding="utf-8")


def _markdown_family_row(row: Mapping[str, Any]) -> str:
    rt_window = f"{_format_value(row.get('rt_min'))}-{_format_value(row.get('rt_max'))}"
    failure = str(row.get("failure_reason", "")).replace("|", "/")
    return (
        f"| {row.get('rank', '')} "
        f"| `{row.get('feature_family_id', '')}` "
        f"| {_format_value(row.get('mz'))} "
        f"| {rt_window} "
        f"| `{row.get('status', '')}` "
        f"| `{row.get('family_verdict', '')}` "
        f"| {_format_value(row.get('selected_apex_in_trace_window_fraction'))} "
        f"| {_format_value(row.get('absolute_own_max_shape_supported_fraction'))} "
        f"| {_format_value(row.get('global_apex_interference_fraction'))} "
        f"| `{row.get('dda_trigger_limited_ms2_support', '')}` "
        f"| {failure} |"
    )


def _with_top30_expansion_gate(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    gate = _top30_expansion_gate(rows)
    blockers = _format_tsv_blockers(rows)
    return [
        {
            **row,
            "top30_expansion_gate": gate,
            "top30_expansion_blocker": _row_top30_expansion_blocker(row),
            "top30_expansion_blockers": blockers,
        }
        for row in rows
    ]


def _top30_expansion_gate(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return TOP30_EXPANSION_BLOCKED
    if any(_row_top30_expansion_blocker(row) for row in rows):
        return TOP30_EXPANSION_BLOCKED
    return TOP30_EXPANSION_ELIGIBLE


def _row_top30_expansion_blocker(row: Mapping[str, Any]) -> str:
    status = str(row.get("status", ""))
    verdict = str(row.get("family_verdict", ""))
    if status != "success":
        return "failed_row"
    if verdict.startswith("review_required_"):
        return "review_required_family_verdict"
    if verdict == "insufficient_nl_seed_support":
        return "insufficient_nl_seed_support"
    if verdict != SUPPORT_FAMILY_VERDICT:
        return "non_support_family_verdict"
    return ""


def _format_markdown_blockers(rows: Sequence[Mapping[str, Any]]) -> str:
    blockers = []
    for row in rows:
        blocker = _row_top30_expansion_blocker(row)
        if not blocker:
            continue
        family = row.get("feature_family_id", "")
        rank = row.get("rank", "")
        verdict = row.get("family_verdict", "") or row.get("status", "")
        blockers.append(f"rank {rank} `{family}` (`{verdict}`)")
    if not blockers:
        return "none"
    return "; ".join(blockers)


def _format_tsv_blockers(rows: Sequence[Mapping[str, Any]]) -> str:
    blockers = []
    for row in rows:
        blocker = _row_top30_expansion_blocker(row)
        if not blocker:
            continue
        family = _format_value(row.get("feature_family_id"))
        rank = _format_value(row.get("rank"))
        verdict = _format_value(row.get("family_verdict") or row.get("status"))
        blockers.append(f"rank {rank} {family} {verdict}")
    return "; ".join(blockers)


def _write_tsv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field)) for field in fields})


def _summary_fields() -> tuple[str, ...]:
    return (
        "rank",
        "feature_family_id",
        "seed_group_id",
        "mz",
        "ppm",
        "rt_min",
        "rt_max",
        "family_center_rt",
        "output_prefix",
        "status",
        "family_verdict",
        "dda_trigger_limited_ms2_support",
        "detected_count",
        "rescued_count",
        "detected_rescued_count",
        "evaluable_trace_count",
        "global_apex_assessable_trace_count",
        "global_apex_assessable_fraction",
        "selected_apex_in_trace_window_count",
        "selected_apex_in_trace_window_fraction",
        "local_apex_assessable_trace_count",
        "global_apex_interference_count",
        "shape_supported_fraction",
        "absolute_own_max_evaluable_trace_count",
        "absolute_own_max_shape_supported_count",
        "absolute_own_max_shape_supported_fraction",
        "absolute_trace_apex_assessable_count",
        "absolute_trace_apex_cluster_count",
        "absolute_trace_apex_cluster_fraction",
        "absolute_trace_apex_delta_abs_median_min",
        "global_apex_interference_fraction",
        "local_apex_supported_count",
        "local_apex_supported_fraction",
        "png_path",
        "pdf_path",
        "trace_summary_tsv",
        "trace_data_json",
        "failure_reason",
        "top30_expansion_gate",
        "top30_expansion_blocker",
        "top30_expansion_blockers",
    )


def _require_columns(path: Path, fields: Sequence[str]) -> None:
    missing = [field for field in REQUIRED_QUEUE_COLUMNS if field not in fields]
    if missing:
        raise ValueError(f"{path} missing required columns: {', '.join(missing)}")


def _required_text(row: Mapping[str, str], field: str) -> str:
    value = row.get(field, "")
    if not value:
        raise ValueError(f"Queue row missing {field}")
    return value


def _required_float(row: Mapping[str, str], field: str) -> float:
    value = _optional_float(row.get(field))
    if value is None:
        raise ValueError(f"Queue row has invalid {field}: {row.get(field)!r}")
    return value


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue-tsv", type=Path, required=True)
    parser.add_argument(
        "--alignment-cells",
        "--alignment-cell-evidence",
        dest="alignment_cells",
        type=Path,
        required=True,
        help=(
            "Cell evidence TSV: compact alignment_backfill_cell_evidence.tsv "
            "or legacy alignment_cells.tsv."
        ),
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--max-highlight-rescued", type=int, default=8)
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help=(
            "Reuse completed overlay outputs in output-dir when PNG/trace "
            "summary/trace JSON and any requested PDF already exist for a "
            "queued output prefix."
        ),
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Write PNG, TSV, and JSON overlay artifacts only; skip PDF outputs.",
    )
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help=(
            "Write RAW-backed trace TSV/JSON and summary rows without rendering "
            "PNG/PDF overlays."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
