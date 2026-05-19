"""Render queued family MS1 overlays from a backfill review report."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.diagnostics import family_ms1_overlay_plot as overlay_plot

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


@dataclass(frozen=True)
class OverlayBatchRequest:
    rank: int
    family_id: str
    mz: float
    ppm: float
    rt_min: float
    rt_max: float
    family_center_rt: float | None
    output_prefix: str


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
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
        )
        _write_outputs(args.output_dir, rows)
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
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for request in requests:
        try:
            rows.append(
                _render_family(
                    request,
                    alignment_cells=alignment_cells,
                    raw_dir=raw_dir,
                    dll_dir=dll_dir,
                    output_dir=output_dir,
                    max_highlight_rescued=max_highlight_rescued,
                )
            )
        except Exception as exc:  # noqa: BLE001 - diagnostic batch must continue.
            rows.append(_failure_row(request, exc))
    return rows


def _render_family(
    request: OverlayBatchRequest,
    *,
    alignment_cells: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    max_highlight_rescued: int,
) -> dict[str, Any]:
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
    )
    evidence = overlay_plot.build_family_ms1_evidence_summary(trace_rows)
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
        "global_apex_interference_fraction": evidence.get(
            "global_apex_interference_fraction",
            "",
        ),
        "local_apex_supported_count": evidence.get("local_apex_supported_count", ""),
        "local_apex_supported_fraction": evidence.get(
            "local_apex_supported_fraction",
            "",
        ),
        "png_path": str(outputs.png_path),
        "pdf_path": str(outputs.pdf_path),
        "trace_summary_tsv": str(outputs.summary_tsv),
        "trace_data_json": str(outputs.trace_data_json),
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
        "mz": request.mz,
        "ppm": request.ppm,
        "rt_min": request.rt_min,
        "rt_max": request.rt_max,
        "family_center_rt": request.family_center_rt,
        "output_prefix": request.output_prefix,
    }


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


def _write_outputs(output_dir: Path, rows: Sequence[Mapping[str, Any]]) -> None:
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
                "coverage | global conflict | DDA-height signal | failure |"
            ),
            "|---:|---|---:|---|---|---|---:|---:|---|---|",
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
    parser.add_argument("--alignment-cells", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument("--ppm", type=float, default=10.0)
    parser.add_argument("--max-highlight-rescued", type=int, default=8)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
