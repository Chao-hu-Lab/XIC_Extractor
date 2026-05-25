"""P2 AsLS shadow baseline diagnostic gate."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median, stdev

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


ROW_FIELDS = (
    "target_label",
    "selected_feature_id",
    "sample_count",
    "linear_area_rsd_pct",
    "asls_area_rsd_pct",
    "area_rsd_delta_pct",
    "median_abs_relative_diff_pct",
    "diff_gt_5pct_count",
    "asls_reduced_area_count",
    "asls_exceeds_raw_area_count",
    "status",
    "failure_reasons",
)

SUMMARY_FIELDS = (
    "overall_status",
    "failed_count",
    "target_count",
    "max_area_rsd_delta_pct",
    "max_median_abs_relative_diff_pct",
    "max_asls_exceeds_raw_area_count",
    "max_rsd_regression_pct",
)

_AUDIT_REQUIRED_COLUMNS = {
    "feature_family_id",
    "sample_stem",
    "area",
    "area_baseline_corrected",
    "area_baseline_corrected_asls",
}
_SUMMARY_REQUIRED_COLUMNS = {
    "target_label",
    "role",
    "active_tag",
    "selected_feature_id",
    "coverage_denominator_count",
}
_MISSING_VALUES = {"", "ND", "NA", "N/A", "NONE", "NULL"}


@dataclass(frozen=True)
class P2AslsShadowGateOutputs:
    rows_tsv: Path
    summary_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class _SelectedIstdTarget:
    target_label: str
    selected_feature_id: str
    coverage_denominator_count: int


@dataclass(frozen=True)
class P2AslsShadowGateRow:
    target_label: str
    selected_feature_id: str
    sample_count: int
    linear_area_rsd_pct: float | None
    asls_area_rsd_pct: float | None
    area_rsd_delta_pct: float | None
    median_abs_relative_diff_pct: float | None
    diff_gt_5pct_count: int
    asls_reduced_area_count: int
    asls_exceeds_raw_area_count: int
    status: str
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class P2AslsShadowGateResult:
    overall_status: str
    failed_count: int
    target_count: int
    max_area_rsd_delta_pct: float | None
    max_median_abs_relative_diff_pct: float | None
    max_asls_exceeds_raw_area_count: int
    max_rsd_regression_pct: float
    rows: tuple[P2AslsShadowGateRow, ...]


def run_p2_asls_shadow_gate(
    *,
    alignment_integration_audit_tsv: Path,
    targeted_istd_benchmark_summary_tsv: Path,
    output_dir: Path,
    max_rsd_regression_pct: float = 0.3,
) -> tuple[P2AslsShadowGateOutputs, P2AslsShadowGateResult]:
    audit_rows = _read_tsv(alignment_integration_audit_tsv, _AUDIT_REQUIRED_COLUMNS)
    targets = _read_selected_istd_targets(targeted_istd_benchmark_summary_tsv)
    rows = tuple(
        _build_row(
            target,
            audit_rows=audit_rows,
            max_rsd_regression_pct=max_rsd_regression_pct,
        )
        for target in targets
    )
    result = P2AslsShadowGateResult(
        overall_status="FAIL" if any(row.status == "FAIL" for row in rows) else "PASS",
        failed_count=sum(row.status == "FAIL" for row in rows),
        target_count=len(rows),
        max_area_rsd_delta_pct=_max_present(row.area_rsd_delta_pct for row in rows),
        max_median_abs_relative_diff_pct=_max_present(
            row.median_abs_relative_diff_pct for row in rows
        ),
        max_asls_exceeds_raw_area_count=max(
            (row.asls_exceeds_raw_area_count for row in rows),
            default=0,
        ),
        max_rsd_regression_pct=max_rsd_regression_pct,
        rows=rows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = P2AslsShadowGateOutputs(
        rows_tsv=output_dir / "p2_asls_shadow_gate_rows.tsv",
        summary_tsv=output_dir / "p2_asls_shadow_gate_summary.tsv",
        json_path=output_dir / "p2_asls_shadow_gate.json",
        markdown_path=output_dir / "p2_asls_shadow_gate.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gate P2 AsLS shadow baseline columns against linear-edge integration "
            "audit rows for targeted ISTD benchmark selections."
        )
    )
    parser.add_argument("--alignment-integration-audit-tsv", type=Path, required=True)
    parser.add_argument("--targeted-istd-benchmark-summary-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-rsd-regression-pct", type=float, default=0.3)
    args = parser.parse_args(argv)

    try:
        outputs, result = run_p2_asls_shadow_gate(
            alignment_integration_audit_tsv=args.alignment_integration_audit_tsv,
            targeted_istd_benchmark_summary_tsv=(
                args.targeted_istd_benchmark_summary_tsv
            ),
            output_dir=args.output_dir,
            max_rsd_regression_pct=args.max_rsd_regression_pct,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Gate JSON: {outputs.json_path}")
    print(f"Gate report: {outputs.markdown_path}")
    return 0 if result.overall_status == "PASS" else 1


def _read_selected_istd_targets(path: Path) -> tuple[_SelectedIstdTarget, ...]:
    rows = _read_tsv(path, _SUMMARY_REQUIRED_COLUMNS)
    targets = tuple(
        _SelectedIstdTarget(
            target_label=row["target_label"].strip(),
            selected_feature_id=row["selected_feature_id"].strip(),
            coverage_denominator_count=_parse_non_negative_int(
                row.get("coverage_denominator_count", "")
            ),
        )
        for row in rows
        if row.get("target_label", "").strip()
        and row.get("selected_feature_id", "").strip()
        and row.get("role", "").strip().upper() == "ISTD"
        and _parse_bool(row.get("active_tag", ""))
    )
    if not targets:
        raise ValueError(f"{path}: no active ISTD rows with selected_feature_id")
    return targets


def _build_row(
    target: _SelectedIstdTarget,
    *,
    audit_rows: Sequence[Mapping[str, str]],
    max_rsd_regression_pct: float,
) -> P2AslsShadowGateRow:
    linear_areas: list[float] = []
    asls_areas: list[float] = []
    relative_diffs: list[float] = []
    diff_gt_5pct_count = 0
    asls_reduced_area_count = 0
    asls_exceeds_raw_area_count = 0

    for row in audit_rows:
        if row.get("feature_family_id", "").strip() != target.selected_feature_id:
            continue
        raw_area = _optional_float(row.get("area"))
        linear_area = _optional_float(row.get("area_baseline_corrected"))
        asls_area = _optional_float(row.get("area_baseline_corrected_asls"))
        if raw_area is None or linear_area is None or asls_area is None:
            continue
        linear_areas.append(linear_area)
        asls_areas.append(asls_area)
        if linear_area > 0:
            relative_diff = abs(asls_area - linear_area) / linear_area * 100.0
            relative_diffs.append(relative_diff)
            if relative_diff > 5.0:
                diff_gt_5pct_count += 1
        if asls_area < linear_area:
            asls_reduced_area_count += 1
        if asls_area > raw_area + 1e-9:
            asls_exceeds_raw_area_count += 1

    linear_rsd = _area_rsd_pct(linear_areas)
    asls_rsd = _area_rsd_pct(asls_areas)
    area_delta = None if linear_rsd is None or asls_rsd is None else asls_rsd - linear_rsd
    median_abs_relative_diff = median(relative_diffs) if relative_diffs else None
    reasons: list[str] = []
    if len(linear_areas) < 2:
        reasons.append("sample_count_lt_2")
    if len(linear_areas) < target.coverage_denominator_count:
        reasons.append("shadow_coverage_incomplete")
    if area_delta is None:
        reasons.append("area_rsd_unavailable")
    elif area_delta > max_rsd_regression_pct:
        reasons.append("area_rsd_regression")
    if asls_exceeds_raw_area_count:
        reasons.append("asls_area_exceeds_raw_area")
    return P2AslsShadowGateRow(
        target_label=target.target_label,
        selected_feature_id=target.selected_feature_id,
        sample_count=len(linear_areas),
        linear_area_rsd_pct=linear_rsd,
        asls_area_rsd_pct=asls_rsd,
        area_rsd_delta_pct=area_delta,
        median_abs_relative_diff_pct=median_abs_relative_diff,
        diff_gt_5pct_count=diff_gt_5pct_count,
        asls_reduced_area_count=asls_reduced_area_count,
        asls_exceeds_raw_area_count=asls_exceeds_raw_area_count,
        status="FAIL" if reasons else "PASS",
        failure_reasons=tuple(reasons),
    )


def _area_rsd_pct(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    return stdev(values) / mean * 100.0


def _write_outputs(
    outputs: P2AslsShadowGateOutputs,
    result: P2AslsShadowGateResult,
) -> None:
    _write_tsv(outputs.rows_tsv, ROW_FIELDS, (_row_dict(row) for row in result.rows))
    _write_tsv(outputs.summary_tsv, SUMMARY_FIELDS, (_summary_dict(result),))
    outputs.json_path.write_text(
        json.dumps(
            {
                **_summary_dict(result),
                "rows": [_row_dict(row) for row in result.rows],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_markdown(outputs.markdown_path, result)


def _row_dict(row: P2AslsShadowGateRow) -> dict[str, object]:
    return {
        **asdict(row),
        "failure_reasons": ";".join(row.failure_reasons),
    }


def _summary_dict(result: P2AslsShadowGateResult) -> dict[str, object]:
    return {
        "overall_status": result.overall_status,
        "failed_count": result.failed_count,
        "target_count": result.target_count,
        "max_area_rsd_delta_pct": result.max_area_rsd_delta_pct,
        "max_median_abs_relative_diff_pct": result.max_median_abs_relative_diff_pct,
        "max_asls_exceeds_raw_area_count": result.max_asls_exceeds_raw_area_count,
        "max_rsd_regression_pct": result.max_rsd_regression_pct,
    }


def _write_markdown(path: Path, result: P2AslsShadowGateResult) -> None:
    lines = [
        "# P2 AsLS Shadow Gate",
        "",
        f"Overall status: {result.overall_status}",
        "",
        "| Target | Feature | Samples | Area RSD delta pct | Median abs diff pct | Status | Reasons |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in result.rows:
        lines.append(
            "| "
            f"{row.target_label} | "
            f"{row.selected_feature_id} | "
            f"{row.sample_count} | "
            f"{_format_value(row.area_rsd_delta_pct)} | "
            f"{_format_value(row.median_abs_relative_diff_pct)} | "
            f"{row.status} | "
            f"{';'.join(row.failure_reasons)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tsv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field)) for field in fieldnames})


def _read_tsv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or ())
        missing = sorted(required_columns - columns)
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def _optional_float(value: object) -> float | None:
    text = "" if value is None else str(value).strip()
    if text.upper() in _MISSING_VALUES:
        return None
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"non-numeric numeric field value: {text}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite numeric field value: {text}")
    return parsed


def _parse_bool(value: object) -> bool:
    return str(value).strip().upper() in {"1", "TRUE", "YES", "Y"}


def _parse_non_negative_int(value: object) -> int:
    text = str(value).strip()
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValueError(f"coverage_denominator_count must be an integer: {text}") from exc
    if parsed < 0:
        raise ValueError("coverage_denominator_count must be >= 0")
    return parsed


def _max_present(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.6g}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
