from __future__ import annotations

import csv
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from xic_extractor.diagnostics.targeted_ms1_shape_identity_expected_diff import (
    EXPECTED_DIFF_REQUIRED_COLUMNS,
    MATRIX_DIFF_REQUIRED_COLUMNS,
    evaluate_limited_targeted_ms1_shape_identity_expected_diff_paths,
    write_expected_diff_gate_summary,
)
from xic_extractor.tabular_io import read_delimited_rows, write_tsv

EXPECTED_DIFF_SUMMARY_NAME = "expected_diff_summary.tsv"
MATRIX_DIFF_SUMMARY_NAME = "matrix_diff_summary.tsv"
EXPECTED_DIFF_GATE_SUMMARY_NAME = "limited_default_expected_diff_gate_summary.tsv"
_KeyT = TypeVar("_KeyT", bound=Hashable)

_LONG_REQUIRED_COLUMNS = (
    "SampleName",
    "Target",
    "Role",
    "RT",
    "Area",
    "Int",
    "PeakStart",
    "PeakEnd",
    "PeakWidth",
    "Confidence",
    "NL",
    "Reason",
    "Product State",
    "Counted Detection",
    "Projection Support Reasons",
    "Projection Not Counted Reasons",
)
_LONG_DIFF_FIELDS = (
    ("Product State", "baseline_product_state", "optin_product_state"),
    ("Counted Detection", "baseline_counted_detection", "optin_counted_detection"),
    ("RT", "baseline_rt", "optin_rt"),
    ("Area", "baseline_area", "optin_area"),
    ("Int", None, None),
    ("PeakStart", None, None),
    ("PeakEnd", None, None),
    ("PeakWidth", None, None),
    ("Confidence", None, None),
    ("Reason", "baseline_reason", "optin_reason"),
    ("Projection Support Reasons", None, None),
    ("Projection Not Counted Reasons", None, None),
)


@dataclass(frozen=True)
class TargetedMs1ShapeIdentityAutoDiffOutputs:
    expected_diff_summary_tsv: Path
    matrix_diff_summary_tsv: Path
    expected_diff_gate_summary_tsv: Path
    expected_diff_row_count: int
    matrix_diff_cell_count: int
    gate_status: str


def write_targeted_ms1_shape_identity_auto_diff_artifacts(
    *,
    baseline_output_dir: Path,
    optin_output_dir: Path,
    support_tsv: Path,
    output_dir: Path,
) -> TargetedMs1ShapeIdentityAutoDiffOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_diff_rows = build_expected_diff_rows(
        baseline_output_dir / "xic_results_long.csv",
        optin_output_dir / "xic_results_long.csv",
    )
    matrix_diff_rows = build_matrix_diff_rows(
        baseline_output_dir / "xic_results.csv",
        optin_output_dir / "xic_results.csv",
    )
    expected_diff_summary_tsv = output_dir / EXPECTED_DIFF_SUMMARY_NAME
    matrix_diff_summary_tsv = output_dir / MATRIX_DIFF_SUMMARY_NAME
    gate_summary_tsv = output_dir / EXPECTED_DIFF_GATE_SUMMARY_NAME
    write_tsv(
        expected_diff_summary_tsv,
        expected_diff_rows,
        EXPECTED_DIFF_REQUIRED_COLUMNS,
    )
    write_tsv(matrix_diff_summary_tsv, matrix_diff_rows, MATRIX_DIFF_REQUIRED_COLUMNS)
    gate_summary = evaluate_limited_targeted_ms1_shape_identity_expected_diff_paths(
        expected_diff_summary_tsv=expected_diff_summary_tsv,
        matrix_diff_summary_tsv=matrix_diff_summary_tsv,
        support_tsv=support_tsv,
    )
    write_expected_diff_gate_summary(gate_summary_tsv, gate_summary)
    return TargetedMs1ShapeIdentityAutoDiffOutputs(
        expected_diff_summary_tsv=expected_diff_summary_tsv,
        matrix_diff_summary_tsv=matrix_diff_summary_tsv,
        expected_diff_gate_summary_tsv=gate_summary_tsv,
        expected_diff_row_count=len(expected_diff_rows),
        matrix_diff_cell_count=len(matrix_diff_rows),
        gate_status=gate_summary.gate_status,
    )


def build_expected_diff_rows(
    baseline_long_csv: Path,
    optin_long_csv: Path,
) -> tuple[dict[str, str], ...]:
    baseline_rows = _read_long_rows(baseline_long_csv)
    optin_rows = _read_long_rows(optin_long_csv)
    baseline_index = _index_rows(baseline_rows, path=baseline_long_csv)
    optin_index = _index_rows(optin_rows, path=optin_long_csv)
    _require_same_keys(baseline_index, optin_index)
    diff_rows: list[dict[str, str]] = []
    for key in sorted(baseline_index):
        baseline = baseline_index[key]
        optin = optin_index[key]
        changed_fields = tuple(
            field
            for field, _baseline_column, _optin_column in _LONG_DIFF_FIELDS
            if _clean(baseline.get(field)) != _clean(optin.get(field))
        )
        if not changed_fields:
            continue
        diff_rows.append(_expected_diff_row(baseline, optin, changed_fields))
    return tuple(diff_rows)


def build_matrix_diff_rows(
    baseline_wide_csv: Path,
    optin_wide_csv: Path,
) -> tuple[dict[str, str], ...]:
    baseline_rows, baseline_header = _read_wide_rows(baseline_wide_csv)
    optin_rows, optin_header = _read_wide_rows(optin_wide_csv)
    if baseline_header != optin_header:
        raise ValueError("baseline and opt-in wide CSV headers differ")
    baseline_index = _index_by_column(
        baseline_rows,
        "SampleName",
        path=baseline_wide_csv,
    )
    optin_index = _index_by_column(optin_rows, "SampleName", path=optin_wide_csv)
    _require_same_keys(baseline_index, optin_index)
    diff_rows: list[dict[str, str]] = []
    for sample_name in sorted(baseline_index):
        baseline = baseline_index[sample_name]
        optin = optin_index[sample_name]
        for column in baseline_header:
            if column == "SampleName":
                continue
            baseline_value = _clean(baseline.get(column))
            optin_value = _clean(optin.get(column))
            if baseline_value == optin_value:
                continue
            diff_rows.append(
                {
                    "row_key": sample_name,
                    "column": column,
                    "baseline_value": baseline_value,
                    "optin_value": optin_value,
                }
            )
    return tuple(diff_rows)


def _read_long_rows(path: Path) -> tuple[dict[str, str], ...]:
    return tuple(
        read_delimited_rows(
            path,
            required_columns=_LONG_REQUIRED_COLUMNS,
            delimiter=",",
            encoding="utf-8-sig",
        )
    )


def _read_wide_rows(path: Path) -> tuple[tuple[dict[str, str], ...], tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if "SampleName" not in header:
            raise ValueError(f"{path}: missing required column: SampleName")
        return tuple(dict(row) for row in reader), header


def _index_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    path: Path,
) -> dict[tuple[str, str], Mapping[str, str]]:
    index: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        key = (_clean(row.get("SampleName")), _clean(row.get("Target")))
        if not key[0] or not key[1]:
            raise ValueError(f"{path}: SampleName and Target are required")
        if key in index:
            raise ValueError(f"{path}: duplicate SampleName/Target row: {key}")
        index[key] = row
    return index


def _index_by_column(
    rows: Sequence[Mapping[str, str]],
    column: str,
    *,
    path: Path,
) -> dict[str, Mapping[str, str]]:
    index: dict[str, Mapping[str, str]] = {}
    for row in rows:
        key = _clean(row.get(column))
        if not key:
            raise ValueError(f"{path}: {column} is required")
        if key in index:
            raise ValueError(f"{path}: duplicate {column} row: {key}")
        index[key] = row
    return index


def _require_same_keys(
    baseline_index: Mapping[_KeyT, object],
    optin_index: Mapping[_KeyT, object],
) -> None:
    baseline_keys = set(baseline_index)
    optin_keys = set(optin_index)
    missing = baseline_keys - optin_keys
    unexpected = optin_keys - baseline_keys
    if missing or unexpected:
        raise ValueError(
            "baseline and opt-in outputs have different row keys: "
            f"missing={_sorted_key_reprs(missing)!r}; "
            f"unexpected={_sorted_key_reprs(unexpected)!r}"
        )


def _sorted_key_reprs(keys: set[_KeyT]) -> list[str]:
    return sorted(repr(key) for key in keys)


def _expected_diff_row(
    baseline: Mapping[str, str],
    optin: Mapping[str, str],
    changed_fields: Sequence[str],
) -> dict[str, str]:
    return {
        "sample_name": _clean(baseline.get("SampleName")),
        "target_name": _clean(baseline.get("Target")),
        "role": _clean(baseline.get("Role")),
        "changed_fields": ";".join(changed_fields),
        "baseline_product_state": _clean(baseline.get("Product State")),
        "optin_product_state": _clean(optin.get("Product State")),
        "baseline_counted_detection": _clean(baseline.get("Counted Detection")),
        "optin_counted_detection": _clean(optin.get("Counted Detection")),
        "baseline_rt": _clean(baseline.get("RT")),
        "optin_rt": _clean(optin.get("RT")),
        "baseline_area": _clean(baseline.get("Area")),
        "optin_area": _clean(optin.get("Area")),
        "baseline_nl": _clean(baseline.get("NL")),
        "optin_nl": _clean(optin.get("NL")),
        "baseline_reason": _clean(baseline.get("Reason")),
        "optin_reason": _clean(optin.get("Reason")),
    }


def _clean(value: object | None) -> str:
    return "" if value is None else str(value).strip()


__all__ = [
    "EXPECTED_DIFF_GATE_SUMMARY_NAME",
    "EXPECTED_DIFF_SUMMARY_NAME",
    "MATRIX_DIFF_SUMMARY_NAME",
    "TargetedMs1ShapeIdentityAutoDiffOutputs",
    "build_expected_diff_rows",
    "build_matrix_diff_rows",
    "write_targeted_ms1_shape_identity_auto_diff_artifacts",
]
