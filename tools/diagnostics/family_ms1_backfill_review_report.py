"""Build a review queue for low-seed/high-backfill MS1-supported families."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

REVIEW_REQUIRED_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "detected_count",
    "accepted_rescue_count",
    "accepted_cell_count",
    "include_in_primary_matrix",
)
CELLS_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "height",
)

DEFAULT_TAG = "DNA_dR"
SUGGESTED_OVERLAY_HALF_WINDOW_MIN = 1.1


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = build_review_report(
            alignment_dir=args.alignment_dir,
            overlay_trace_data_dirs=args.overlay_trace_data_dir or (),
            overlay_trace_data_files=args.overlay_trace_data or (),
            neutral_loss_tag=args.neutral_loss_tag,
            max_detected_count=args.max_detected_count,
            min_rescue_count=args.min_rescue_count,
            min_accepted_count=args.min_accepted_count,
            image_queue_limit=args.image_queue_limit,
        )
        write_outputs(args.output_dir, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"family MS1 backfill review report: {args.output_dir}")
    return 0


def build_review_report(
    *,
    alignment_dir: Path,
    overlay_trace_data_dirs: Sequence[Path] = (),
    overlay_trace_data_files: Sequence[Path] = (),
    neutral_loss_tag: str = DEFAULT_TAG,
    max_detected_count: int = 8,
    min_rescue_count: int = 40,
    min_accepted_count: int = 60,
    image_queue_limit: int = 30,
) -> dict[str, Any]:
    review_rows = _read_tsv(
        alignment_dir / "alignment_review.tsv",
        required_columns=REVIEW_REQUIRED_COLUMNS,
    )
    cell_rows = _read_tsv(
        alignment_dir / "alignment_cells.tsv",
        required_columns=CELLS_REQUIRED_COLUMNS,
    )
    cells_by_family = _cells_by_family(cell_rows)
    overlay_by_family = _load_overlay_evidence(
        overlay_trace_data_dirs=overlay_trace_data_dirs,
        overlay_trace_data_files=overlay_trace_data_files,
    )

    candidates: list[dict[str, Any]] = []
    for review_row in review_rows:
        if not _is_candidate_review_row(
            review_row,
            neutral_loss_tag=neutral_loss_tag,
            max_detected_count=max_detected_count,
            min_rescue_count=min_rescue_count,
            min_accepted_count=min_accepted_count,
        ):
            continue
        family_id = review_row["feature_family_id"]
        family = _candidate_row(
            review_row,
            cells_by_family.get(family_id, ()),
            overlay_by_family.get(family_id),
        )
        candidates.append(family)

    candidates.sort(
        key=lambda row: (
            _classification_sort_key(str(row["review_classification"])),
            -float(row["review_priority_score"]),
            str(row["feature_family_id"]),
        )
    )
    queue = [
        row
        for row in sorted(
            candidates,
            key=lambda item: (
                _classification_sort_key(str(item["review_classification"])),
                -float(item["review_priority_score"]),
                item["feature_family_id"],
            ),
        )
        if row["overlay_status"] == "not_provided"
    ][:image_queue_limit]
    summary = _summary_rows(candidates, queue)
    return {
        "alignment_dir": str(alignment_dir),
        "neutral_loss_tag": neutral_loss_tag,
        "thresholds": {
            "max_detected_count": max_detected_count,
            "min_rescue_count": min_rescue_count,
            "min_accepted_count": min_accepted_count,
            "image_queue_limit": image_queue_limit,
        },
        "overlay_trace_data_dirs": [str(path) for path in overlay_trace_data_dirs],
        "overlay_trace_data_files": [str(path) for path in overlay_trace_data_files],
        "summary": summary,
        "candidates": candidates,
        "image_queue": queue,
    }


def write_outputs(output_dir: Path, result: Mapping[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = list(result["candidates"])
    queue = list(result["image_queue"])
    summary = list(result["summary"])
    _write_tsv(
        output_dir / "family_ms1_backfill_review_candidates.tsv",
        candidates,
        _candidate_fields(),
    )
    _write_tsv(
        output_dir / "family_ms1_backfill_review_queue.tsv",
        queue,
        _candidate_fields(),
    )
    _write_tsv(
        output_dir / "family_ms1_backfill_review_summary.tsv",
        summary,
        ("metric", "value"),
    )
    (output_dir / "family_ms1_backfill_review.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_markdown(output_dir / "family_ms1_backfill_review.md", result)


def _candidate_row(
    review_row: Mapping[str, str],
    cells: Sequence[Mapping[str, str]],
    overlay: Mapping[str, Any] | None,
) -> dict[str, Any]:
    detected = [row for row in cells if row.get("status") == "detected"]
    rescued = [row for row in cells if row.get("status") == "rescued"]
    detected_height_median = _median(_float(row.get("height")) for row in detected)
    rescued_height_median = _median(_float(row.get("height")) for row in rescued)
    detected_area_median = _median(_float(row.get("area")) for row in detected)
    rescued_area_median = _median(_float(row.get("area")) for row in rescued)
    detected_count = int(_float(review_row.get("detected_count")) or 0)
    rescue_count = int(_float(review_row.get("accepted_rescue_count")) or 0)
    accepted_count = int(_float(review_row.get("accepted_cell_count")) or 0)
    rescue_fraction = _safe_fraction(rescue_count, accepted_count) or 0.0
    rescue_per_detected_seed = _safe_ratio(rescue_count, detected_count) or 0.0
    height_ratio = _safe_ratio(detected_height_median, rescued_height_median)
    area_ratio = _safe_ratio(detected_area_median, rescued_area_median)
    overlay_summary = dict(overlay or {})
    classification = _review_classification(
        overlay_summary=overlay_summary,
        height_ratio=height_ratio,
        rescue_count=rescue_count,
    )
    priority = rescue_fraction * max(rescue_per_detected_seed, 1.0)
    if height_ratio is not None:
        priority *= min(height_ratio, 3.0)
    mz = review_row.get("family_center_mz", "")
    center_rt = review_row.get("family_center_rt", "")
    overlay_hint = _suggested_overlay_hint(
        family_id=review_row["feature_family_id"],
        mz=mz,
        center_rt=center_rt,
    )
    return {
        "feature_family_id": review_row["feature_family_id"],
        "neutral_loss_tag": review_row.get("neutral_loss_tag", ""),
        "family_center_mz": mz,
        "family_center_rt": center_rt,
        **overlay_hint,
        "detected_count": detected_count,
        "accepted_rescue_count": rescue_count,
        "accepted_cell_count": accepted_count,
        "rescue_fraction": rescue_fraction,
        "rescue_per_detected_seed": rescue_per_detected_seed,
        "detected_height_median": detected_height_median,
        "rescued_height_median": rescued_height_median,
        "detected_to_rescued_height_ratio": height_ratio,
        "detected_area_median": detected_area_median,
        "rescued_area_median": rescued_area_median,
        "detected_to_rescued_area_ratio": area_ratio,
        "overlay_status": "provided" if overlay is not None else "not_provided",
        "overlay_family_verdict": overlay_summary.get("family_verdict", ""),
        "dda_trigger_limited_ms2_support": overlay_summary.get(
            "dda_trigger_limited_ms2_support",
            "",
        ),
        "shape_supported_fraction": overlay_summary.get("shape_supported_fraction", ""),
        "global_apex_interference_fraction": overlay_summary.get(
            "global_apex_interference_fraction",
            "",
        ),
        "local_apex_supported_fraction": overlay_summary.get(
            "local_apex_supported_fraction",
            "",
        ),
        "review_classification": classification,
        "recommended_next_action": _recommended_next_action(classification),
        "review_priority_score": priority,
        "row_flags": review_row.get("row_flags", ""),
        "primary_evidence": review_row.get("primary_evidence", ""),
        "reason": review_row.get("reason", ""),
    }


def _review_classification(
    *,
    overlay_summary: Mapping[str, Any],
    height_ratio: float | None,
    rescue_count: int,
) -> str:
    verdict = str(overlay_summary.get("family_verdict", ""))
    if verdict == "ms1_shape_supports_family_backfill":
        if overlay_summary.get("dda_trigger_limited_ms2_support") is True:
            return "ms1_supported_dda_limited_backfill"
        return "ms1_supported_backfill"
    if verdict == "review_required_neighboring_ms1_interference":
        return "neighboring_interference_review"
    if verdict == "review_required_uncertain_ms1_shape":
        return "uncertain_shape_review"
    if verdict:
        return "overlay_review_required"
    if height_ratio is not None and height_ratio >= 1.25 and rescue_count >= 70:
        return "needs_ms1_overlay_high_priority"
    return "needs_ms1_overlay"


def _recommended_next_action(classification: str) -> str:
    if classification.startswith("ms1_supported"):
        return "keep_primary_candidate_with_ms1_support_note"
    if classification in {
        "neighboring_interference_review",
        "uncertain_shape_review",
        "overlay_review_required",
    }:
        return "manual_review_before_gate_change"
    if classification == "needs_ms1_overlay_high_priority":
        return "generate_overlay_first"
    return "generate_overlay_if_review_budget_allows"


def _suggested_overlay_hint(
    *,
    family_id: str,
    mz: str,
    center_rt: str,
) -> dict[str, str]:
    rt = _float(center_rt)
    if rt is None or not mz:
        return {
            "suggested_rt_min": "",
            "suggested_rt_max": "",
            "suggested_output_prefix": "",
            "suggested_overlay_command_args": "",
        }
    rt_min = max(0.0, rt - SUGGESTED_OVERLAY_HALF_WINDOW_MIN)
    rt_max = rt + SUGGESTED_OVERLAY_HALF_WINDOW_MIN
    prefix = f"{family_id.lower()}_ms1_overlay_review"
    args = (
        f"--family-id {family_id} "
        f"--mz {mz} "
        f"--rt-min {rt_min:.4f} "
        f"--rt-max {rt_max:.4f} "
        f"--family-center-rt {rt:.4f} "
        f"--output-prefix {prefix}"
    )
    return {
        "suggested_rt_min": f"{rt_min:.4f}",
        "suggested_rt_max": f"{rt_max:.4f}",
        "suggested_output_prefix": prefix,
        "suggested_overlay_command_args": args,
    }


def _load_overlay_evidence(
    *,
    overlay_trace_data_dirs: Sequence[Path],
    overlay_trace_data_files: Sequence[Path],
) -> dict[str, dict[str, Any]]:
    files: list[Path] = []
    for directory in overlay_trace_data_dirs:
        if directory.is_dir():
            files.extend(sorted(directory.glob("*_trace_data.json")))
    files.extend(overlay_trace_data_files)
    evidence: dict[str, dict[str, Any]] = {}
    for path in files:
        if not path.is_file():
            raise ValueError(f"Overlay trace data JSON not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        family_id = str(data.get("family_id", ""))
        if not family_id:
            raise ValueError(f"Overlay trace data missing family_id: {path}")
        evidence[family_id] = dict(data.get("evidence_summary") or {})
    return evidence


def _is_candidate_review_row(
    row: Mapping[str, str],
    *,
    neutral_loss_tag: str,
    max_detected_count: int,
    min_rescue_count: int,
    min_accepted_count: int,
) -> bool:
    if row.get("include_in_primary_matrix") != "TRUE":
        return False
    if row.get("neutral_loss_tag") != neutral_loss_tag:
        return False
    detected_count = int(_float(row.get("detected_count")) or 0)
    rescue_count = int(_float(row.get("accepted_rescue_count")) or 0)
    accepted_count = int(_float(row.get("accepted_cell_count")) or 0)
    return (
        2 <= detected_count <= max_detected_count
        and rescue_count >= min_rescue_count
        and accepted_count >= min_accepted_count
    )


def _summary_rows(
    candidates: Sequence[Mapping[str, Any]],
    queue: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    classifications = Counter(str(row["review_classification"]) for row in candidates)
    overlay_statuses = Counter(str(row["overlay_status"]) for row in candidates)
    summary = [
        {"metric": "candidate_count", "value": str(len(candidates))},
        {"metric": "image_queue_count", "value": str(len(queue))},
    ]
    summary.extend(
        {"metric": f"classification:{key}", "value": str(value)}
        for key, value in sorted(classifications.items())
    )
    summary.extend(
        {"metric": f"overlay_status:{key}", "value": str(value)}
        for key, value in sorted(overlay_statuses.items())
    )
    return summary


def _write_markdown(path: Path, result: Mapping[str, Any]) -> None:
    summary = {row["metric"]: row["value"] for row in result["summary"]}
    supported_count = _summary_int(
        summary,
        "classification:ms1_supported_dda_limited_backfill",
    ) + _summary_int(summary, "classification:ms1_supported_backfill")
    manual_review_count = (
        _summary_int(summary, "classification:neighboring_interference_review")
        + _summary_int(summary, "classification:uncertain_shape_review")
        + _summary_int(summary, "classification:overlay_review_required")
    )
    high_priority_count = _summary_int(
        summary,
        "classification:needs_ms1_overlay_high_priority",
    )
    pending_overlay_count = high_priority_count + _summary_int(
        summary,
        "classification:needs_ms1_overlay",
    )
    lines = [
        "# Family MS1 Backfill Review Report",
        "",
        "## Review Verdict",
        "",
        (
            f"- {summary.get('candidate_count', '0')} low-seed/high-backfill "
            "primary families need MS1 review discipline."
        ),
        (
            f"- {supported_count} already have overlay evidence supporting "
            "MS1-backed DDA-limited backfill."
        ),
        (
            f"- {manual_review_count} already show interference or uncertain "
            "shape and should not feed a production gate automatically."
        ),
        (
            f"- {pending_overlay_count} still need RAW-backed overlay evidence; "
            f"the first {summary.get('image_queue_count', '0')} are queued."
        ),
        "",
        "## Run Context",
        "",
        f"- Alignment dir: `{result['alignment_dir']}`",
        f"- Neutral loss tag: `{result['neutral_loss_tag']}`",
        "",
        "## Classification Counts",
        "",
    ]
    for key, value in summary.items():
        if key.startswith("classification:"):
            lines.append(f"- `{key.removeprefix('classification:')}`: {value}")
    lines.extend(
        [
            "",
            "## Top Image Queue",
            "",
            "| # | family | m/z | RT window | seeds/backfill | class | next action |",
            "|---:|---|---:|---|---:|---|---|",
        ]
    )
    for index, row in enumerate(result["image_queue"][:10], start=1):
        lines.append(_markdown_queue_row(index, row))
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            (
                "- `family_ms1_backfill_review_candidates.tsv`: full "
                "machine-readable candidate table."
            ),
            (
                "- `family_ms1_backfill_review_queue.tsv`: human review queue "
                "with overlay command arguments."
            ),
            "- `family_ms1_backfill_review_summary.tsv`: compact count summary.",
            "- `family_ms1_backfill_review.json`: complete structured report.",
            "",
            "## Intended Use",
            "",
            (
                "This report separates cheap alignment-level screening from RAW-backed "
                "MS1 overlay evidence. Generate plots only for queued or manually "
                "selected families. The queue TSV includes per-family overlay command "
                "arguments; add the run-level alignment-cells, RAW, DLL, and output "
                "paths when rendering plots."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _summary_int(summary: Mapping[str, str], key: str) -> int:
    return int(_float(summary.get(key)) or 0)


def _markdown_queue_row(index: int, row: Mapping[str, Any]) -> str:
    window = f"{row.get('suggested_rt_min', '')}-{row.get('suggested_rt_max', '')}"
    seeds = f"{row.get('detected_count', '')}/{row.get('accepted_rescue_count', '')}"
    return (
        f"| {index} | `{row.get('feature_family_id', '')}` "
        f"| {row.get('family_center_mz', '')} "
        f"| {window} "
        f"| {seeds} "
        f"| `{row.get('review_classification', '')}` "
        f"| `{row.get('recommended_next_action', '')}` |"
    )


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


def _candidate_fields() -> tuple[str, ...]:
    return (
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        "suggested_rt_min",
        "suggested_rt_max",
        "suggested_output_prefix",
        "suggested_overlay_command_args",
        "detected_count",
        "accepted_rescue_count",
        "accepted_cell_count",
        "rescue_fraction",
        "rescue_per_detected_seed",
        "detected_height_median",
        "rescued_height_median",
        "detected_to_rescued_height_ratio",
        "detected_area_median",
        "rescued_area_median",
        "detected_to_rescued_area_ratio",
        "overlay_status",
        "overlay_family_verdict",
        "dda_trigger_limited_ms2_support",
        "shape_supported_fraction",
        "global_apex_interference_fraction",
        "local_apex_supported_fraction",
        "review_classification",
        "recommended_next_action",
        "review_priority_score",
        "row_flags",
        "primary_evidence",
        "reason",
    )


def _cells_by_family(
    rows: Iterable[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["feature_family_id"])].append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _read_tsv(path: Path, *, required_columns: Sequence[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"Required TSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields = reader.fieldnames or ()
        missing = [field for field in required_columns if field not in fields]
        if missing:
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
        return list(reader)


def _classification_sort_key(classification: str) -> int:
    order = {
        "neighboring_interference_review": 0,
        "uncertain_shape_review": 1,
        "overlay_review_required": 2,
        "needs_ms1_overlay_high_priority": 3,
        "needs_ms1_overlay": 4,
        "ms1_supported_dda_limited_backfill": 5,
        "ms1_supported_backfill": 6,
    }
    return order.get(classification, 99)


def _median(values: Iterable[float | None]) -> float | None:
    finite = [value for value in values if value is not None]
    if not finite:
        return None
    finite.sort()
    midpoint = len(finite) // 2
    if len(finite) % 2:
        return finite[midpoint]
    return (finite[midpoint - 1] + finite[midpoint]) / 2.0


def _float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _safe_ratio(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _safe_fraction(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alignment-dir",
        type=Path,
        required=True,
        help=(
            "Alignment output directory containing alignment_review.tsv and "
            "alignment_cells.tsv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for review queue, summary, JSON, and Markdown outputs",
    )
    parser.add_argument(
        "--overlay-trace-data-dir",
        type=Path,
        action="append",
        help=(
            "Directory containing *_trace_data.json files from "
            "family_ms1_overlay_plot.py"
        ),
    )
    parser.add_argument(
        "--overlay-trace-data",
        type=Path,
        action="append",
        help="Single trace_data.json file from family_ms1_overlay_plot.py",
    )
    parser.add_argument(
        "--neutral-loss-tag",
        default=DEFAULT_TAG,
        help=(
            "Primary-row neutral loss tag scope for candidate screening "
            f"(default: {DEFAULT_TAG})"
        ),
    )
    parser.add_argument(
        "--max-detected-count",
        type=int,
        default=8,
        help=(
            "Maximum detected seed count for low-seed/high-backfill candidates "
            "(default: 8)"
        ),
    )
    parser.add_argument(
        "--min-rescue-count",
        type=int,
        default=40,
        help="Minimum rescued cell count for high-backfill candidates (default: 40)",
    )
    parser.add_argument(
        "--min-accepted-count",
        type=int,
        default=60,
        help="Minimum detected+rescued accepted cell count (default: 60)",
    )
    parser.add_argument(
        "--image-queue-limit",
        type=int,
        default=30,
        help=(
            "Maximum not-yet-overlayed families to place in the plotting queue "
            "(default: 30)"
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
