from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


COMPARISON_FIELDS = (
    "sample_name",
    "target_label",
    "target_mz",
    "is_istd",
    "default_rt_min",
    "safe_merge_rt_min",
    "rt_delta_min",
    "default_area",
    "safe_merge_area",
    "area_ratio",
    "default_peak_start",
    "safe_merge_peak_start",
    "default_peak_end",
    "safe_merge_peak_end",
    "default_nl",
    "safe_merge_nl",
    "promotion_reason",
    "safe_merge_note",
    "shadow_verdict",
    "merge_suggestion_source",
    "selected_interval_count",
    "selected_interval_gap_max_min",
)

SUMMARY_FIELDS = (
    "compared_rows",
    "changed_rows",
    "promoted_rows",
    "changed_istd_rows",
    "affected_target_labels",
    "area_ratio_min",
    "area_ratio_median",
    "area_ratio_max",
    "max_abs_rt_delta_min",
)


@dataclass(frozen=True)
class TargetInfo:
    label: str
    mz: str
    is_istd: str


@dataclass(frozen=True)
class ResultCell:
    sample_name: str
    target_label: str
    rt: str
    area: str
    peak_start: str
    peak_end: str
    nl: str


@dataclass(frozen=True)
class ComparisonOutputs:
    comparison_tsv: Path
    summary_tsv: Path
    markdown: Path


def run_region_first_safe_merge_comparison(
    *,
    default_dir: Path,
    safe_merge_dir: Path,
    targets_csv: Path,
    output_dir: Path,
) -> ComparisonOutputs:
    target_info = _read_targets(targets_csv)
    default_cells = _read_xic_results(default_dir / "xic_results.csv", target_info)
    safe_cells = _read_xic_results(safe_merge_dir / "xic_results.csv", target_info)
    safe_candidates = _read_selected_candidates(safe_merge_dir / "peak_candidates.tsv")
    shadow_rows = _read_shadow_summary(
        safe_merge_dir / "peak_region_selection_shadow_summary.tsv"
    )

    rows: list[dict[str, str]] = []
    compared_keys = sorted(set(default_cells) & set(safe_cells))
    for key in compared_keys:
        default = default_cells.get(key)
        safe = safe_cells.get(key)
        if default is None or safe is None:
            continue
        if not _cell_changed(default, safe):
            continue
        sample_name, target_label = key
        target = target_info.get(target_label, TargetInfo(target_label, "", ""))
        candidate = safe_candidates.get(key, {})
        shadow = shadow_rows.get(key, {})
        merge_suggestion_source = _merge_suggestion_source(candidate, shadow)
        rows.append(
            {
                "sample_name": sample_name,
                "target_label": target_label,
                "target_mz": target.mz or candidate.get("target_mz", ""),
                "is_istd": target.is_istd
                or _bool_text(candidate.get("role") == "ISTD"),
                "default_rt_min": default.rt,
                "safe_merge_rt_min": safe.rt,
                "rt_delta_min": _format_delta(default.rt, safe.rt),
                "default_area": default.area,
                "safe_merge_area": safe.area,
                "area_ratio": _format_ratio(safe.area, default.area),
                "default_peak_start": default.peak_start,
                "safe_merge_peak_start": safe.peak_start,
                "default_peak_end": default.peak_end,
                "safe_merge_peak_end": safe.peak_end,
                "default_nl": default.nl,
                "safe_merge_nl": safe.nl,
                "promotion_reason": _promotion_reason(candidate),
                "safe_merge_note": candidate.get("merge_note", ""),
                "shadow_verdict": shadow.get("shadow_verdict", ""),
                "merge_suggestion_source": merge_suggestion_source,
                "selected_interval_count": shadow.get("selected_interval_count", ""),
                "selected_interval_gap_max_min": shadow.get(
                    "selected_interval_gap_max_min", ""
                ),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_tsv = output_dir / "region_first_safe_merge_comparison.tsv"
    summary_tsv = output_dir / "region_first_safe_merge_comparison_summary.tsv"
    markdown = output_dir / "region_first_safe_merge_comparison.md"
    _write_tsv(comparison_tsv, COMPARISON_FIELDS, rows)
    summary = _summary_row(rows, compared_count=len(compared_keys))
    _write_tsv(summary_tsv, SUMMARY_FIELDS, [summary])
    _write_markdown(markdown, summary, rows)
    return ComparisonOutputs(
        comparison_tsv=comparison_tsv,
        summary_tsv=summary_tsv,
        markdown=markdown,
    )


def _read_targets(path: Path) -> dict[str, TargetInfo]:
    _require_file(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        _require_columns(path, reader.fieldnames, {"label", "mz"})
        targets: dict[str, TargetInfo] = {}
        for row in reader:
            label = row.get("label", "").strip()
            if not label:
                continue
            targets[label] = TargetInfo(
                label=label,
                mz=row.get("mz", "").strip(),
                is_istd=_bool_text(_parse_bool(row.get("is_istd", ""))),
            )
    return targets


def _read_xic_results(
    path: Path, target_info: dict[str, TargetInfo]
) -> dict[tuple[str, str], ResultCell]:
    _require_file(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        _require_columns(path, reader.fieldnames, {"SampleName"})
        labels = _result_labels(reader.fieldnames or (), target_info)
        cells: dict[tuple[str, str], ResultCell] = {}
        for row in reader:
            sample_name = row.get("SampleName", "").strip()
            if not sample_name:
                continue
            for label in labels:
                cells[(sample_name, label)] = ResultCell(
                    sample_name=sample_name,
                    target_label=label,
                    rt=row.get(f"{label}_RT", "").strip(),
                    area=row.get(f"{label}_Area", "").strip(),
                    peak_start=row.get(f"{label}_PeakStart", "").strip(),
                    peak_end=row.get(f"{label}_PeakEnd", "").strip(),
                    nl=row.get(f"{label}_NL", "").strip(),
                )
    return cells


def _result_labels(
    fieldnames: Sequence[str], target_info: dict[str, TargetInfo]
) -> tuple[str, ...]:
    labels = [
        label
        for label in target_info
        if f"{label}_RT" in fieldnames and f"{label}_Area" in fieldnames
    ]
    if labels:
        return tuple(labels)
    inferred = [
        field.removesuffix("_RT")
        for field in fieldnames
        if field.endswith("_RT") and f"{field.removesuffix('_RT')}_Area" in fieldnames
    ]
    return tuple(inferred)


def _read_selected_candidates(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        _require_columns(path, reader.fieldnames, {"sample_name", "target_label"})
        rows: dict[tuple[str, str], dict[str, str]] = {}
        for row in reader:
            if row.get("selected", "").upper() != "TRUE":
                continue
            rows[(row.get("sample_name", ""), row.get("target_label", ""))] = dict(row)
    return rows


def _read_shadow_summary(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        _require_columns(path, reader.fieldnames, {"sample_name", "target_label"})
        rows: dict[tuple[str, str], dict[str, str]] = {}
        for row in reader:
            rows[(row.get("sample_name", ""), row.get("target_label", ""))] = dict(row)
    return rows


def _cell_changed(default: ResultCell, safe: ResultCell) -> bool:
    return any(
        default_value != safe_value
        for default_value, safe_value in (
            (default.rt, safe.rt),
            (default.area, safe.area),
            (default.peak_start, safe.peak_start),
            (default.peak_end, safe.peak_end),
            (default.nl, safe.nl),
        )
    )


def _promotion_reason(candidate: dict[str, str]) -> str:
    merge_note = candidate.get("merge_note", "")
    if "region_first_safe_merge" in merge_note.split(";"):
        return "region_first_safe_merge"
    if "region_first_safe_merge" in merge_note:
        return "region_first_safe_merge"
    if merge_note:
        return "changed_with_other_merge_note"
    return "changed_without_selected_candidate_note"


def _merge_suggestion_source(
    candidate: dict[str, str],
    shadow: dict[str, str],
) -> str:
    merge_notes = {
        value
        for value in candidate.get("merge_note", "").split(";")
        if value
    }
    if "adjacent_wis_local_minimum_merge" in merge_notes:
        return "adjacent_wis_local_minimum_merge"
    if "same_apex_wider_boundary_merge" in merge_notes:
        return "same_apex_wider_boundary_merge"
    return shadow.get("merge_suggestion_source", "")


def _summary_row(
    rows: Sequence[dict[str, str]], *, compared_count: int
) -> dict[str, str]:
    ratios = [_as_float(row["area_ratio"]) for row in rows]
    ratios = [value for value in ratios if value is not None]
    rt_deltas = [_as_float(row["rt_delta_min"]) for row in rows]
    rt_deltas = [abs(value) for value in rt_deltas if value is not None]
    promoted_rows = [
        row for row in rows if row["promotion_reason"] == "region_first_safe_merge"
    ]
    return {
        "compared_rows": str(compared_count),
        "changed_rows": str(len(rows)),
        "promoted_rows": str(len(promoted_rows)),
        "changed_istd_rows": str(
            sum(1 for row in rows if _parse_bool(row.get("is_istd", "")))
        ),
        "affected_target_labels": ";".join(
            sorted({row["target_label"] for row in rows})
        ),
        "area_ratio_min": _format_float(min(ratios)) if ratios else "",
        "area_ratio_median": _format_float(median(ratios)) if ratios else "",
        "area_ratio_max": _format_float(max(ratios)) if ratios else "",
        "max_abs_rt_delta_min": _format_float(max(rt_deltas)) if rt_deltas else "",
    }


def _write_tsv(
    path: Path, fieldnames: Sequence[str], rows: Sequence[dict[str, str]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_markdown(
    path: Path, summary: dict[str, str], rows: Sequence[dict[str, str]]
) -> None:
    lines = [
        "# Region-first Safe Merge Comparison",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {field}: {summary.get(field, '')}" for field in SUMMARY_FIELDS)
    lines.extend(["", "## Top Changed Rows", ""])
    for row in rows[:25]:
        lines.append(
            "- "
            f"{row['sample_name']} | {row['target_label']} | m/z {row['target_mz']} | "
            f"RT {row['default_rt_min']} -> {row['safe_merge_rt_min']} | "
            f"area {row['default_area']} -> {row['safe_merge_area']} | "
            f"ratio {row['area_ratio']} | {row['promotion_reason']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_delta(left: str, right: str) -> str:
    left_value = _as_float(left)
    right_value = _as_float(right)
    if left_value is None or right_value is None:
        return ""
    return _format_float(right_value - left_value)


def _format_ratio(numerator: str, denominator: str) -> str:
    top = _as_float(numerator)
    bottom = _as_float(denominator)
    if top is None or bottom is None or bottom == 0:
        return ""
    return _format_float(top / bottom)


def _format_float(value: float) -> str:
    return f"{value:.5f}"


def _as_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() in {"TRUE", "YES", "1"}


def _bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")


def _require_columns(
    path: Path, fieldnames: Sequence[str] | None, required: set[str]
) -> None:
    available = set(fieldnames or ())
    missing = sorted(required - available)
    if missing:
        raise ValueError(f"{path} missing required columns: {', '.join(missing)}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare default XIC output with opt-in region-first safe merge."
    )
    parser.add_argument("--default-dir", required=True, type=Path)
    parser.add_argument("--safe-merge-dir", required=True, type=Path)
    parser.add_argument("--targets-csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    outputs = run_region_first_safe_merge_comparison(
        default_dir=args.default_dir,
        safe_merge_dir=args.safe_merge_dir,
        targets_csv=args.targets_csv,
        output_dir=args.output_dir,
    )
    print(f"Wrote {outputs.comparison_tsv}")
    print(f"Wrote {outputs.summary_tsv}")
    print(f"Wrote {outputs.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
