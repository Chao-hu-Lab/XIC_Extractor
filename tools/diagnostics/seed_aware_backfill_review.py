"""Build a seed-aware shadow review for rescued-heavy backfill families."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

SUPPORT_VERDICT = "ms1_shape_supports_family_backfill"
NEIGHBOR_VERDICT = "review_required_neighboring_ms1_interference"

NEIGHBOR_INTERFERENCE_FRACTION_MAX = 0.25
MIN_RESCUE_COUNT = 40
MIN_ACCEPTED_COUNT = 60
SEED_OVERLAY_PATTERN = re.compile(r"_seed\d+_")

CLASS_SEED_SUPPORTED = "seed_shape_supported_review_candidate"
CLASS_NEIGHBOR = "neighbor_interference_review"
CLASS_SHAPE = "shape_insufficient_review"
CLASS_SEED_MISSING = "seed_context_missing"
CLASS_NOT_ASSESSABLE = "not_assessable"
CLASS_NOT_RESCUED_HEAVY = "not_rescued_heavy"

WITHHOLD_CLASSES = frozenset({CLASS_NEIGHBOR, CLASS_SHAPE})

REVIEW_REQUIRED_COLUMNS = (
    "feature_family_id",
    "family_center_mz",
    "family_center_rt",
    "detected_count",
    "accepted_rescue_count",
    "accepted_cell_count",
    "review_classification",
)

OVERLAY_REQUIRED_COLUMNS = (
    "feature_family_id",
    "status",
    "family_verdict",
    "global_apex_interference_fraction",
    "selected_apex_in_trace_window_fraction",
    "global_apex_assessable_fraction",
    "shape_supported_fraction",
    "png_path",
    "pdf_path",
)

LOW_COVERAGE_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
)

SEED_AUDIT_REQUIRED_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "backfill_seed_mz",
    "backfill_seed_rt",
    "backfill_request_rt_min",
    "backfill_request_rt_max",
    "backfill_request_ppm",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = build_seed_aware_review(
            review_candidates_tsv=args.review_candidates_tsv,
            overlay_batch_summary_tsv=args.overlay_batch_summary_tsv,
            low_ms1_rows_tsv=args.low_ms1_rows_tsv,
            backfill_seed_audit_tsv=args.backfill_seed_audit_tsv,
            protected_family_ids=tuple(args.protected_family_id or ()),
            min_rescue_count=args.min_rescue_count,
            min_accepted_count=args.min_accepted_count,
        )
        write_outputs(args.output_dir, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"seed-aware backfill review: {args.output_dir}")
    return 0


def build_seed_aware_review(
    *,
    review_candidates_tsv: Path,
    overlay_batch_summary_tsv: Path | Sequence[Path],
    low_ms1_rows_tsv: Path,
    backfill_seed_audit_tsv: Path,
    protected_family_ids: Sequence[str] = (),
    min_rescue_count: int = MIN_RESCUE_COUNT,
    min_accepted_count: int = MIN_ACCEPTED_COUNT,
) -> dict[str, Any]:
    review_rows = _read_tsv(
        review_candidates_tsv,
        required_columns=REVIEW_REQUIRED_COLUMNS,
    )
    overlay_paths = _normalize_paths(overlay_batch_summary_tsv)
    overlay_rows = [
        row
        for path in overlay_paths
        for row in _read_tsv(path, required_columns=OVERLAY_REQUIRED_COLUMNS)
    ]
    low_rows = _read_tsv(
        low_ms1_rows_tsv,
        required_columns=LOW_COVERAGE_REQUIRED_COLUMNS,
    )
    seed_rows = _read_tsv(
        backfill_seed_audit_tsv,
        required_columns=SEED_AUDIT_REQUIRED_COLUMNS,
    )
    overlay_by_family = _group_by_family(overlay_rows)
    low_by_family = _group_by_family(low_rows)
    seed_by_family = _group_by_family(seed_rows)
    protected = {str(family_id) for family_id in protected_family_ids}

    families = [
        _family_review_row(
            row,
            overlay_rows=overlay_by_family.get(row["feature_family_id"], ()),
            low_rows=low_by_family.get(row["feature_family_id"], ()),
            seed_rows=seed_by_family.get(row["feature_family_id"], ()),
            protected_family=row["feature_family_id"] in protected,
            min_rescue_count=min_rescue_count,
            min_accepted_count=min_accepted_count,
        )
        for row in review_rows
    ]
    families.sort(
        key=lambda row: (
            _classification_sort_key(str(row["review_classification"])),
            -int(row["would_withhold_rescued_cells"]),
            str(row["feature_family_id"]),
        )
    )
    blast_rows = [_blast_radius_row(row) for row in families]
    summary = _summary_rows(families, blast_rows)
    return {
        "inputs": {
            "review_candidates_tsv": str(review_candidates_tsv),
            "overlay_batch_summary_tsv": [str(path) for path in overlay_paths],
            "low_ms1_rows_tsv": str(low_ms1_rows_tsv),
            "backfill_seed_audit_tsv": str(backfill_seed_audit_tsv),
        },
        "thresholds": {
            "neighbor_interference_fraction_max": (
                NEIGHBOR_INTERFERENCE_FRACTION_MAX
            ),
            "min_rescue_count": min_rescue_count,
            "min_accepted_count": min_accepted_count,
        },
        "families": families,
        "blast_radius": blast_rows,
        "summary": summary,
    }


def write_outputs(output_dir: Path, result: Mapping[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    families = list(result["families"])
    blast_rows = list(result["blast_radius"])
    summary = list(result["summary"])
    _write_tsv(
        output_dir / "seed_aware_backfill_review_families.tsv",
        families,
        _family_fields(),
    )
    _write_tsv(
        output_dir / "seed_aware_backfill_review_summary.tsv",
        summary,
        ("metric", "value"),
    )
    _write_tsv(
        output_dir / "seed_aware_backfill_blast_radius.tsv",
        blast_rows,
        _blast_fields(),
    )
    (output_dir / "seed_aware_backfill_review.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_markdown(output_dir / "seed_aware_backfill_review.md", result)
    _write_blast_markdown(
        output_dir / "seed_aware_backfill_blast_radius.md",
        result,
    )


def _family_review_row(
    review_row: Mapping[str, str],
    *,
    overlay_rows: Sequence[Mapping[str, str]],
    low_rows: Sequence[Mapping[str, str]],
    seed_rows: Sequence[Mapping[str, str]],
    protected_family: bool,
    min_rescue_count: int,
    min_accepted_count: int,
) -> dict[str, Any]:
    family_id = review_row["feature_family_id"]
    detected_count = int(_float(review_row.get("detected_count")) or 0)
    rescue_count = int(_float(review_row.get("accepted_rescue_count")) or 0)
    accepted_count = int(_float(review_row.get("accepted_cell_count")) or 0)
    seed_overlay_rows = _seed_specific_overlay_rows(overlay_rows)
    decision_overlay_rows = seed_overlay_rows or tuple(overlay_rows)
    overlay_summary = _overlay_summary(decision_overlay_rows)
    all_overlay_summary = _overlay_summary(overlay_rows)
    seed_summary = _seed_summary(seed_rows)
    classification = _classify_family(
        rescue_count=rescue_count,
        accepted_count=accepted_count,
        overlay_summary=overlay_summary,
        seed_summary=seed_summary,
        min_rescue_count=min_rescue_count,
        min_accepted_count=min_accepted_count,
    )
    reason = _review_reason(classification, overlay_summary, seed_summary)
    would_withhold = rescue_count if classification in WITHHOLD_CLASSES else 0
    if protected_family and would_withhold:
        action = "manual_review_required"
    else:
        action = _recommended_action(classification)
    return {
        "feature_family_id": family_id,
        "neutral_loss_tag": review_row.get("neutral_loss_tag", ""),
        "family_center_mz": review_row.get("family_center_mz", ""),
        "family_center_rt": review_row.get("family_center_rt", ""),
        "detected_count": detected_count,
        "accepted_rescue_count": rescue_count,
        "accepted_cell_count": accepted_count,
        "input_review_classification": review_row.get("review_classification", ""),
        "all_overlay_row_count": all_overlay_summary["overlay_row_count"],
        "seed_overlay_row_count": len(seed_overlay_rows),
        "overlay_row_count": overlay_summary["overlay_row_count"],
        "overlay_success_count": overlay_summary["overlay_success_count"],
        "overlay_support_count": overlay_summary["overlay_support_count"],
        "overlay_neighbor_count": overlay_summary["overlay_neighbor_count"],
        "overlay_failed_count": overlay_summary["overlay_failed_count"],
        "max_global_apex_interference_fraction": overlay_summary[
            "max_global_apex_interference_fraction"
        ],
        "min_selected_apex_in_trace_window_fraction": overlay_summary[
            "min_selected_apex_in_trace_window_fraction"
        ],
        "min_global_apex_assessable_fraction": overlay_summary[
            "min_global_apex_assessable_fraction"
        ],
        "min_shape_supported_fraction": overlay_summary[
            "min_shape_supported_fraction"
        ],
        "seed_audit_row_count": seed_summary["seed_audit_row_count"],
        "seed_group_count": seed_summary["seed_group_count"],
        "seed_rt_span": seed_summary["seed_rt_span"],
        "low_ms1_detail_row_count": len(low_rows),
        "protected_family": protected_family,
        "review_classification": classification,
        "recommended_next_action": action,
        "review_reason": reason,
        "would_withhold_rescued_cells": would_withhold,
        "png_paths": _joined_paths(decision_overlay_rows, "png_path"),
        "pdf_paths": _joined_paths(decision_overlay_rows, "pdf_path"),
        "row_flags": review_row.get("row_flags", ""),
        "primary_evidence": review_row.get("primary_evidence", ""),
        "reason": review_row.get("reason", ""),
    }


def _classify_family(
    *,
    rescue_count: int,
    accepted_count: int,
    overlay_summary: Mapping[str, Any],
    seed_summary: Mapping[str, Any],
    min_rescue_count: int,
    min_accepted_count: int,
) -> str:
    if rescue_count < min_rescue_count or accepted_count < min_accepted_count:
        return CLASS_NOT_RESCUED_HEAVY
    if _has_high_neighbor_interference(overlay_summary):
        return CLASS_NEIGHBOR
    if seed_summary["seed_audit_row_count"] == 0:
        return CLASS_SEED_MISSING
    if overlay_summary["overlay_row_count"] == 0:
        return CLASS_NOT_ASSESSABLE
    if overlay_summary["overlay_failed_count"]:
        return CLASS_NOT_ASSESSABLE
    if overlay_summary["overlay_support_count"] != overlay_summary["overlay_row_count"]:
        return CLASS_SHAPE
    return CLASS_SEED_SUPPORTED


def _has_high_neighbor_interference(overlay_summary: Mapping[str, Any]) -> bool:
    if overlay_summary["overlay_neighbor_count"] > 0:
        return True
    fraction = overlay_summary["max_global_apex_interference_fraction"]
    return (
        isinstance(fraction, float)
        and fraction >= NEIGHBOR_INTERFERENCE_FRACTION_MAX
    )


def _review_reason(
    classification: str,
    overlay_summary: Mapping[str, Any],
    seed_summary: Mapping[str, Any],
) -> str:
    if classification == CLASS_SEED_SUPPORTED:
        return (
            "seed-specific overlays support MS1 shape with no high neighboring "
            "interference"
        )
    if classification == CLASS_NEIGHBOR:
        return "neighboring MS1 apex interference blocks automatic escalation"
    if classification == CLASS_SHAPE:
        return "seed-specific overlays were present but not all supported MS1 shape"
    if classification == CLASS_SEED_MISSING:
        return "owner-backfill seed provenance is missing for this family"
    if classification == CLASS_NOT_ASSESSABLE:
        if overlay_summary["overlay_row_count"] == 0:
            return "seed-specific overlay evidence has not been generated"
        return "seed-specific overlay failed or is not assessable"
    if classification == CLASS_NOT_RESCUED_HEAVY:
        return "family does not meet rescued-heavy shadow review thresholds"
    return (
        "unclassified seed-aware review state; "
        f"seed rows={seed_summary['seed_audit_row_count']}"
    )


def _recommended_action(classification: str) -> str:
    if classification == CLASS_SEED_SUPPORTED:
        return "keep_as_shadow_gate_candidate"
    if classification in {CLASS_NEIGHBOR, CLASS_SHAPE}:
        return "manual_review_before_gate_change"
    if classification == CLASS_SEED_MISSING:
        return "rerun_alignment_with_seed_audit"
    if classification == CLASS_NOT_ASSESSABLE:
        return "generate_seed_specific_overlay"
    return "no_seed_aware_action"


def _blast_radius_row(row: Mapping[str, Any]) -> dict[str, Any]:
    would_withhold = int(row["would_withhold_rescued_cells"])
    protected = bool(row["protected_family"])
    if protected and would_withhold:
        blast_action = "manual_review_required"
    elif would_withhold:
        blast_action = "would_withhold_shadow_only"
    else:
        blast_action = "no_shadow_withhold"
    return {
        "feature_family_id": row["feature_family_id"],
        "family_center_mz": row["family_center_mz"],
        "family_center_rt": row["family_center_rt"],
        "review_classification": row["review_classification"],
        "detected_count": row["detected_count"],
        "accepted_rescue_count": row["accepted_rescue_count"],
        "accepted_cell_count": row["accepted_cell_count"],
        "would_withhold_family": bool(would_withhold),
        "would_withhold_rescued_cells": would_withhold,
        "protected_family": protected,
        "blast_radius_action": blast_action,
        "review_reason": row["review_reason"],
    }


def _overlay_summary(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    support_count = 0
    neighbor_count = 0
    failed_count = 0
    success_count = 0
    selected_fractions: list[float] = []
    assessable_fractions: list[float] = []
    shape_fractions: list[float] = []
    interference_fractions: list[float] = []
    for row in rows:
        verdict = str(row.get("family_verdict", ""))
        status = str(row.get("status", ""))
        if status == "success":
            success_count += 1
        else:
            failed_count += 1
        if verdict == SUPPORT_VERDICT:
            support_count += 1
        if verdict == NEIGHBOR_VERDICT:
            neighbor_count += 1
        _append_float(
            selected_fractions,
            row.get("selected_apex_in_trace_window_fraction"),
        )
        _append_float(
            assessable_fractions,
            row.get("global_apex_assessable_fraction"),
        )
        _append_float(shape_fractions, row.get("shape_supported_fraction"))
        _append_float(
            interference_fractions,
            row.get("global_apex_interference_fraction"),
        )
    return {
        "overlay_row_count": len(rows),
        "overlay_success_count": success_count,
        "overlay_support_count": support_count,
        "overlay_neighbor_count": neighbor_count,
        "overlay_failed_count": failed_count,
        "min_selected_apex_in_trace_window_fraction": _min_or_blank(
            selected_fractions
        ),
        "min_global_apex_assessable_fraction": _min_or_blank(assessable_fractions),
        "min_shape_supported_fraction": _min_or_blank(shape_fractions),
        "max_global_apex_interference_fraction": _max_or_blank(
            interference_fractions
        ),
    }


def _seed_summary(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    grouped = {
        (
            row.get("backfill_seed_mz", ""),
            row.get("backfill_seed_rt", ""),
            row.get("backfill_request_rt_min", ""),
            row.get("backfill_request_rt_max", ""),
            row.get("backfill_request_ppm", ""),
        )
        for row in rows
    }
    seed_rts = _numeric_values(row.get("backfill_seed_rt") for row in rows)
    return {
        "seed_audit_row_count": len(rows),
        "seed_group_count": len(grouped),
        "seed_rt_span": _span(seed_rts),
    }


def _seed_specific_overlay_rows(
    rows: Sequence[Mapping[str, str]],
) -> tuple[Mapping[str, str], ...]:
    return tuple(row for row in rows if _is_seed_specific_overlay(row))


def _is_seed_specific_overlay(row: Mapping[str, str]) -> bool:
    for field in ("output_prefix", "png_path", "pdf_path", "trace_summary_tsv"):
        value = str(row.get(field, "")).lower()
        if SEED_OVERLAY_PATTERN.search(value):
            return True
    return False


def _summary_rows(
    families: Sequence[Mapping[str, Any]],
    blast_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    classifications = Counter(str(row["review_classification"]) for row in families)
    would_withhold = sum(int(row["would_withhold_rescued_cells"]) for row in blast_rows)
    protected_withhold = sum(
        1
        for row in blast_rows
        if row["protected_family"] and row["would_withhold_family"]
    )
    rows = [
        {"metric": "family_count", "value": str(len(families))},
        {"metric": "would_withhold_rescued_cells", "value": str(would_withhold)},
        {"metric": "protected_family_withhold_count", "value": str(protected_withhold)},
    ]
    rows.extend(
        {"metric": f"classification:{key}", "value": str(value)}
        for key, value in sorted(classifications.items())
    )
    return rows


def _write_markdown(path: Path, result: Mapping[str, Any]) -> None:
    summary = {row["metric"]: row["value"] for row in result["summary"]}
    families = list(result["families"])
    lines = [
        "# Seed-Aware Backfill Review",
        "",
        "## Verdict",
        "",
        f"- Reviewed families: `{summary.get('family_count', '0')}`",
        (
            "- Shadow-supported candidates: "
            f"`{summary.get('classification:' + CLASS_SEED_SUPPORTED, '0')}`"
        ),
        (
            "- Neighboring interference review: "
            f"`{summary.get('classification:' + CLASS_NEIGHBOR, '0')}`"
        ),
        (
            "- Shape insufficient review: "
            f"`{summary.get('classification:' + CLASS_SHAPE, '0')}`"
        ),
        "- Production matrix changes: `none`",
        "",
        "## Inputs",
        "",
    ]
    for name, value in result["inputs"].items():
        if isinstance(value, list):
            joined = "; ".join(str(item) for item in value)
        else:
            joined = str(value)
        lines.append(f"- {name}: `{joined}`")
    lines.extend(
        [
            "",
            "## Top Families",
            "",
            (
                "| family | m/z | RT | class | rescued | max interference "
                "| overlay | reason |"
            ),
            "|---|---:|---:|---|---:|---:|---|---|",
        ]
    )
    for row in families[:20]:
        lines.append(_markdown_family_row(row))
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            "- `seed_aware_backfill_review_summary.tsv`",
            "- `seed_aware_backfill_review_families.tsv`",
            "- `seed_aware_backfill_review.json`",
            "- `seed_aware_backfill_blast_radius.tsv`",
            "- `seed_aware_backfill_blast_radius.md`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_blast_markdown(path: Path, result: Mapping[str, Any]) -> None:
    blast_rows = list(result["blast_radius"])
    affected = [
        row
        for row in blast_rows
        if row["blast_radius_action"] != "no_shadow_withhold"
    ]
    lines = [
        "# Seed-Aware Backfill Blast Radius",
        "",
        "## Verdict",
        "",
        f"- Families reviewed: `{len(blast_rows)}`",
        f"- Families with shadow withheld rescued cells: `{len(affected)}`",
        (
            "- Shadow-withheld rescued cells: "
            f"`{sum(int(row['would_withhold_rescued_cells']) for row in affected)}`"
        ),
        "- Production matrix changes: `none`",
        "",
        "## Affected Families",
        "",
        "| family | m/z | RT | class | withheld rescued cells | action | reason |",
        "|---|---:|---:|---|---:|---|---|",
    ]
    for row in affected[:30]:
        lines.append(_markdown_blast_row(row))
    if not affected:
        lines.append("| none |  |  |  |  |  |  |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _markdown_family_row(row: Mapping[str, Any]) -> str:
    return (
        f"| `{row['feature_family_id']}` "
        f"| {_format_value(row.get('family_center_mz'))} "
        f"| {_format_value(row.get('family_center_rt'))} "
        f"| `{row['review_classification']}` "
        f"| {row['accepted_rescue_count']} "
        f"| {_format_value(row.get('max_global_apex_interference_fraction'))} "
        f"| {_first_path(row.get('png_paths'))} "
        f"| {str(row['review_reason']).replace('|', '/')} |"
    )


def _markdown_blast_row(row: Mapping[str, Any]) -> str:
    return (
        f"| `{row['feature_family_id']}` "
        f"| {_format_value(row.get('family_center_mz'))} "
        f"| {_format_value(row.get('family_center_rt'))} "
        f"| `{row['review_classification']}` "
        f"| {row['would_withhold_rescued_cells']} "
        f"| `{row['blast_radius_action']}` "
        f"| {str(row['review_reason']).replace('|', '/')} |"
    )


def _family_fields() -> tuple[str, ...]:
    return (
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        "detected_count",
        "accepted_rescue_count",
        "accepted_cell_count",
        "input_review_classification",
        "all_overlay_row_count",
        "seed_overlay_row_count",
        "overlay_row_count",
        "overlay_success_count",
        "overlay_support_count",
        "overlay_neighbor_count",
        "overlay_failed_count",
        "max_global_apex_interference_fraction",
        "min_selected_apex_in_trace_window_fraction",
        "min_global_apex_assessable_fraction",
        "min_shape_supported_fraction",
        "seed_audit_row_count",
        "seed_group_count",
        "seed_rt_span",
        "low_ms1_detail_row_count",
        "protected_family",
        "review_classification",
        "recommended_next_action",
        "review_reason",
        "would_withhold_rescued_cells",
        "png_paths",
        "pdf_paths",
        "row_flags",
        "primary_evidence",
        "reason",
    )


def _blast_fields() -> tuple[str, ...]:
    return (
        "feature_family_id",
        "family_center_mz",
        "family_center_rt",
        "review_classification",
        "detected_count",
        "accepted_rescue_count",
        "accepted_cell_count",
        "would_withhold_family",
        "would_withhold_rescued_cells",
        "protected_family",
        "blast_radius_action",
        "review_reason",
    )


def _group_by_family(
    rows: Iterable[Mapping[str, str]],
) -> dict[str, tuple[Mapping[str, str], ...]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["feature_family_id"]].append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _read_tsv(path: Path, *, required_columns: Sequence[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"Required TSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields = reader.fieldnames or ()
        missing = [column for column in required_columns if column not in fields]
        if missing:
            raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
        return list(reader)


def _normalize_paths(path_or_paths: Path | Sequence[Path]) -> tuple[Path, ...]:
    if isinstance(path_or_paths, Path):
        return (path_or_paths,)
    return tuple(path_or_paths)


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


def _classification_sort_key(classification: str) -> int:
    order = {
        CLASS_NEIGHBOR: 0,
        CLASS_SHAPE: 1,
        CLASS_SEED_MISSING: 2,
        CLASS_NOT_ASSESSABLE: 3,
        CLASS_NOT_RESCUED_HEAVY: 4,
        CLASS_SEED_SUPPORTED: 5,
    }
    return order.get(classification, 99)


def _joined_paths(rows: Sequence[Mapping[str, str]], field: str) -> str:
    return ";".join(row[field] for row in rows if row.get(field))


def _first_path(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return text.split(";", 1)[0]


def _append_float(values: list[float], value: object) -> None:
    parsed = _float(value)
    if parsed is not None:
        values.append(parsed)


def _numeric_values(values: Iterable[object]) -> list[float]:
    parsed: list[float] = []
    for value in values:
        _append_float(parsed, value)
    return parsed


def _min_or_blank(values: Sequence[float]) -> float | str:
    return min(values) if values else ""


def _max_or_blank(values: Sequence[float]) -> float | str:
    return max(values) if values else ""


def _span(values: Sequence[float]) -> float | str:
    if not values:
        return ""
    return max(values) - min(values)


def _float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-candidates-tsv", required=True, type=Path)
    parser.add_argument(
        "--overlay-batch-summary-tsv",
        required=True,
        action="append",
        type=Path,
        help=(
            "family_ms1_overlay_batch_summary.tsv; repeat to merge top-review "
            "and seed-specific overlay batches"
        ),
    )
    parser.add_argument("--low-ms1-rows-tsv", required=True, type=Path)
    parser.add_argument("--backfill-seed-audit-tsv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--protected-family-id",
        action="append",
        help=(
            "Family id that should never be treated as automatically safe to "
            "withhold in the blast-radius report"
        ),
    )
    parser.add_argument("--min-rescue-count", type=int, default=MIN_RESCUE_COUNT)
    parser.add_argument("--min-accepted-count", type=int, default=MIN_ACCEPTED_COUNT)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
