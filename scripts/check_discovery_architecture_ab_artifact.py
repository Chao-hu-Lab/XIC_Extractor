"""Check CID-NL Discovery A/B candidate artifacts against successor facts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xic_extractor.alignment.csv_io import read_discovery_candidates_csv  # noqa: E402
from xic_extractor.tabular_io import (  # noqa: E402
    file_sha256,
    optional_float,
    optional_int,
    split_semicolon_labels,
    text_value,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_CANDIDATES_CSV = (
    ROOT
    / "output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312"
    / "discovery_candidates.csv"
)
DEFAULT_CANDIDATE_CANDIDATES_CSV = (
    ROOT
    / "output/discovery_architecture_ab/b_feature_primary/one_raw_tumorbc2312"
    / "discovery_candidates.csv"
)

DEFAULT_FOCUS_SAMPLE = "TumorBC2312_DNA"
DEFAULT_FOCUS_PRECURSOR_MZ = 300.1605
DEFAULT_FOCUS_PRODUCT_MZ = 184.113
DEFAULT_PRESERVE_PRECURSOR_MZ = 301.165
DEFAULT_PRESERVE_PRODUCT_MZ = 185.116
DEFAULT_TAG = "DNA_dR"
DEFAULT_RT_MIN = 22.0
DEFAULT_RT_MAX = 25.0
DEFAULT_MZ_TOLERANCE_DA = 0.01

REQUIRED_COLUMNS = (
    "candidate_id",
    "sample_stem",
    "precursor_mz",
    "product_mz",
    "best_seed_rt",
    "ms1_peak_found",
    "ms1_apex_rt",
    "ms1_area",
    "raw_file",
    "best_ms2_scan_id",
    "seed_scan_ids",
    "neutral_loss_tag",
    "neutral_loss_error_basis",
    "precursor_mz_basis",
    "ms1_peak_rt_start",
    "ms1_peak_rt_end",
    "feature_family_id",
    "feature_superfamily_id",
    "matched_tag_names",
    "primary_tag_name",
    "tag_evidence_json",
    "discovery_candidate_state",
    "ms1_feature_row_id",
)

ACCEPTABLE_ROW_STATES = {
    "ms1_feature_nl_supported",
    "ms1_feature_nl_rescued",
}
RESCUE_BASIS_VALUES = {"product_plus_neutral_loss", "mixed"}


@dataclass(frozen=True)
class PairExpectation:
    label: str
    precursor_mz: float
    product_mz: float
    tag: str
    require_product_plus_basis: bool = False
    min_abs_scan_precursor_delta_da: float | None = None


def check_discovery_architecture_ab_artifact(
    *,
    baseline_candidates_csv: Path,
    candidate_candidates_csv: Path,
    focus_sample: str = DEFAULT_FOCUS_SAMPLE,
    focus_precursor_mz: float = DEFAULT_FOCUS_PRECURSOR_MZ,
    focus_product_mz: float = DEFAULT_FOCUS_PRODUCT_MZ,
    preserve_precursor_mz: float = DEFAULT_PRESERVE_PRECURSOR_MZ,
    preserve_product_mz: float = DEFAULT_PRESERVE_PRODUCT_MZ,
    preserve_tag: str = DEFAULT_TAG,
    mz_tolerance_da: float = DEFAULT_MZ_TOLERANCE_DA,
    rt_min: float = DEFAULT_RT_MIN,
    rt_max: float = DEFAULT_RT_MAX,
    expected_candidate_row_count: int | None = None,
) -> list[str]:
    problems, _, _ = _check_and_collect(
        baseline_candidates_csv=baseline_candidates_csv,
        candidate_candidates_csv=candidate_candidates_csv,
        focus_sample=focus_sample,
        focus_precursor_mz=focus_precursor_mz,
        focus_product_mz=focus_product_mz,
        preserve_precursor_mz=preserve_precursor_mz,
        preserve_product_mz=preserve_product_mz,
        preserve_tag=preserve_tag,
        mz_tolerance_da=mz_tolerance_da,
        rt_min=rt_min,
        rt_max=rt_max,
        expected_candidate_row_count=expected_candidate_row_count,
    )
    return problems


def write_summary(
    summary_json: Path,
    *,
    baseline_candidates_csv: Path,
    candidate_candidates_csv: Path,
    problems: list[str],
    focus_sample: str = DEFAULT_FOCUS_SAMPLE,
    focus_precursor_mz: float = DEFAULT_FOCUS_PRECURSOR_MZ,
    focus_product_mz: float = DEFAULT_FOCUS_PRODUCT_MZ,
    preserve_precursor_mz: float = DEFAULT_PRESERVE_PRECURSOR_MZ,
    preserve_product_mz: float = DEFAULT_PRESERVE_PRODUCT_MZ,
    preserve_tag: str = DEFAULT_TAG,
    mz_tolerance_da: float = DEFAULT_MZ_TOLERANCE_DA,
    rt_min: float = DEFAULT_RT_MIN,
    rt_max: float = DEFAULT_RT_MAX,
    expected_candidate_row_count: int | None = None,
) -> None:
    _, baseline_summary, candidate_summary = _check_and_collect(
        baseline_candidates_csv=baseline_candidates_csv,
        candidate_candidates_csv=candidate_candidates_csv,
        focus_sample=focus_sample,
        focus_precursor_mz=focus_precursor_mz,
        focus_product_mz=focus_product_mz,
        preserve_precursor_mz=preserve_precursor_mz,
        preserve_product_mz=preserve_product_mz,
        preserve_tag=preserve_tag,
        mz_tolerance_da=mz_tolerance_da,
        rt_min=rt_min,
        rt_max=rt_max,
        expected_candidate_row_count=expected_candidate_row_count,
    )
    payload = {
        "schema_version": "discovery_architecture_ab_check_v1",
        "status": "pass" if not problems else "fail",
        "readiness_label": "diagnostic_only",
        "manual_eic_ms2_review": False,
        "focus_sample": focus_sample,
        "rt_window_min": rt_min,
        "rt_window_max": rt_max,
        "mz_tolerance_da": mz_tolerance_da,
        "baseline": baseline_summary,
        "candidate": candidate_summary,
        "problems": problems,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _check_and_collect(
    *,
    baseline_candidates_csv: Path,
    candidate_candidates_csv: Path,
    focus_sample: str,
    focus_precursor_mz: float,
    focus_product_mz: float,
    preserve_precursor_mz: float,
    preserve_product_mz: float,
    preserve_tag: str,
    mz_tolerance_da: float,
    rt_min: float,
    rt_max: float,
    expected_candidate_row_count: int | None,
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    problems: list[str] = []
    expectations = (
        PairExpectation(
            "focus_300_184",
            focus_precursor_mz,
            focus_product_mz,
            preserve_tag,
            require_product_plus_basis=True,
            min_abs_scan_precursor_delta_da=0.5,
        ),
        PairExpectation(
            "preserve_301_185",
            preserve_precursor_mz,
            preserve_product_mz,
            preserve_tag,
        ),
    )
    baseline_rows, baseline_fields = _read_rows(
        baseline_candidates_csv,
        problems,
        artifact_label="baseline",
    )
    candidate_rows, candidate_fields = _read_rows(
        candidate_candidates_csv,
        problems,
        artifact_label="candidate",
    )
    if problems:
        return (
            problems,
            _artifact_summary(baseline_candidates_csv, baseline_rows, {}),
            _artifact_summary(candidate_candidates_csv, candidate_rows, {}),
        )

    _append_missing_column_problems(
        baseline_candidates_csv,
        baseline_fields,
        problems,
        artifact_label="baseline",
    )
    _append_missing_column_problems(
        candidate_candidates_csv,
        candidate_fields,
        problems,
        artifact_label="candidate",
    )
    baseline_parser_status = _append_alignment_parser_problem(
        baseline_candidates_csv,
        problems,
        artifact_label="baseline",
    )
    candidate_parser_status = _append_alignment_parser_problem(
        candidate_candidates_csv,
        problems,
        artifact_label="candidate",
    )
    if expected_candidate_row_count is not None and (
        len(candidate_rows) != expected_candidate_row_count
    ):
        problems.append(
            "candidate: discovery candidate row count mismatch: "
            f"expected {expected_candidate_row_count}, observed {len(candidate_rows)}"
        )
    if problems:
        return (
            problems,
            _artifact_summary(
                baseline_candidates_csv,
                baseline_rows,
                {},
                alignment_parser_status=baseline_parser_status,
            ),
            _artifact_summary(
                candidate_candidates_csv,
                candidate_rows,
                {},
                alignment_parser_status=candidate_parser_status,
            ),
        )

    baseline_facts = _collect_pair_facts(
        rows=baseline_rows,
        expectations=expectations,
        focus_sample=focus_sample,
        mz_tolerance_da=mz_tolerance_da,
        rt_min=rt_min,
        rt_max=rt_max,
        artifact_label="baseline",
        problems=problems,
    )
    candidate_facts = _collect_pair_facts(
        rows=candidate_rows,
        expectations=expectations,
        focus_sample=focus_sample,
        mz_tolerance_da=mz_tolerance_da,
        rt_min=rt_min,
        rt_max=rt_max,
        artifact_label="candidate",
        problems=problems,
    )
    return (
        problems,
        _artifact_summary(
            baseline_candidates_csv,
            baseline_rows,
            baseline_facts,
            alignment_parser_status=baseline_parser_status,
        ),
        _artifact_summary(
            candidate_candidates_csv,
            candidate_rows,
            candidate_facts,
            alignment_parser_status=candidate_parser_status,
        ),
    )


def _read_rows(
    path: Path,
    problems: list[str],
    *,
    artifact_label: str,
) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return list(reader), tuple(reader.fieldnames or ())
    except OSError as exc:
        problems.append(f"{artifact_label}: {path}: could not read CSV: {exc}")
    return [], ()


def _append_missing_column_problems(
    path: Path,
    fieldnames: Sequence[str],
    problems: list[str],
    *,
    artifact_label: str,
) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        problems.append(
            f"{artifact_label}: {path}: missing required columns: "
            + ", ".join(missing)
        )


def _append_alignment_parser_problem(
    path: Path,
    problems: list[str],
    *,
    artifact_label: str,
) -> str:
    try:
        read_discovery_candidates_csv(path)
    except (OSError, ValueError) as exc:
        problems.append(f"{artifact_label}: alignment parser rejected CSV: {exc}")
        return "fail"
    return "pass"


def _collect_pair_facts(
    *,
    rows: Sequence[Mapping[str, str]],
    expectations: Sequence[PairExpectation],
    focus_sample: str,
    mz_tolerance_da: float,
    rt_min: float,
    rt_max: float,
    artifact_label: str,
    problems: list[str],
) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    for expected in expectations:
        pair_rows = [
            row
            for row in rows
            if _row_matches_pair(
                row,
                expected,
                focus_sample=focus_sample,
                mz_tolerance_da=mz_tolerance_da,
            )
        ]
        if len(pair_rows) != 1:
            problems.append(
                f"{artifact_label}: {expected.label}: expected exactly one "
                f"candidate row, observed {len(pair_rows)}"
            )
            continue
        row = pair_rows[0]
        fact = _row_fact(row, expected.tag)
        facts[expected.label] = fact
        _append_pair_contract_problems(
            row,
            fact,
            expected,
            artifact_label=artifact_label,
            problems=problems,
            rt_min=rt_min,
            rt_max=rt_max,
        )
    return facts


def _row_matches_pair(
    row: Mapping[str, str],
    expected: PairExpectation,
    *,
    focus_sample: str,
    mz_tolerance_da: float,
) -> bool:
    if text_value(row.get("sample_stem")) != focus_sample:
        return False
    precursor = optional_float(row.get("precursor_mz"))
    product = optional_float(row.get("product_mz"))
    return (
        precursor is not None
        and product is not None
        and abs(precursor - expected.precursor_mz) <= mz_tolerance_da
        and abs(product - expected.product_mz) <= mz_tolerance_da
        and _row_matches_expected_delta(row, expected)
    )


def _row_matches_expected_delta(
    row: Mapping[str, str],
    expected: PairExpectation,
) -> bool:
    if expected.min_abs_scan_precursor_delta_da is None:
        return True
    max_delta = _max_scan_precursor_abs_delta(row, expected.tag)
    return (
        max_delta is not None
        and max_delta >= expected.min_abs_scan_precursor_delta_da
    )


def _append_pair_contract_problems(
    row: Mapping[str, str],
    fact: Mapping[str, Any],
    expected: PairExpectation,
    *,
    artifact_label: str,
    problems: list[str],
    rt_min: float,
    rt_max: float,
) -> None:
    label = f"{artifact_label}: {expected.label}"
    tag_evidence = _tag_evidence(row, expected.tag, label, problems)
    if tag_evidence is None:
        return
    _append_tag_field_problems(row, expected.tag, label, problems)
    if fact["source_state"] not in ACCEPTABLE_ROW_STATES:
        problems.append(
            f"{label}: unacceptable row state {fact['source_state']!r}"
        )
    if not _bool_value(row.get("ms1_peak_found")):
        problems.append(f"{label}: ms1_peak_found must be TRUE")
    if not fact["row_identity"]:
        problems.append(f"{label}: missing row identity/provenance field")
    ms1_provenance_columns = (
        "ms1_apex_rt",
        "ms1_peak_rt_start",
        "ms1_peak_rt_end",
        "ms1_area",
    )
    missing_ms1 = [
        column
        for column in ms1_provenance_columns
        if optional_float(row.get(column)) is None
    ]
    if missing_ms1:
        problems.append(f"{label}: missing MS1 provenance: {', '.join(missing_ms1)}")
    if not _row_in_rt_window(row, rt_min=rt_min, rt_max=rt_max):
        problems.append(f"{label}: row RT is outside {rt_min:g}-{rt_max:g} min")
    if expected.require_product_plus_basis and not _has_rescue_basis(
        row,
        tag_evidence,
    ):
        problems.append(
            f"{label}: expected product_plus_neutral_loss or mixed basis"
        )
    if optional_int(row.get("best_ms2_scan_id")) is None:
        problems.append(f"{label}: best_ms2_scan_id is not numeric")
    if not split_semicolon_labels(row.get("seed_scan_ids")):
        problems.append(f"{label}: seed_scan_ids is empty")


def _append_tag_field_problems(
    row: Mapping[str, str],
    tag: str,
    label: str,
    problems: list[str],
) -> None:
    if text_value(row.get("neutral_loss_tag")) != tag:
        problems.append(f"{label}: neutral_loss_tag is not {tag}")
    if text_value(row.get("primary_tag_name")) != tag:
        problems.append(f"{label}: primary_tag_name is not {tag}")
    if tag not in split_semicolon_labels(row.get("matched_tag_names")):
        problems.append(f"{label}: matched_tag_names lacks {tag}")


def _tag_evidence(
    row: Mapping[str, str],
    tag: str,
    label: str,
    problems: list[str],
) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(text_value(row.get("tag_evidence_json")) or "{}")
    except json.JSONDecodeError as exc:
        problems.append(f"{label}: tag_evidence_json is not valid JSON: {exc}")
        return None
    if not isinstance(payload, dict) or tag not in payload:
        problems.append(f"{label}: lacks {tag} tag evidence")
        return None
    evidence = payload[tag]
    if not isinstance(evidence, dict):
        problems.append(f"{label}: {tag} tag evidence is not an object")
        return None
    return evidence


def _row_fact(row: Mapping[str, str], tag: str) -> dict[str, Any]:
    tag_evidence_basis = ""
    try:
        payload = json.loads(text_value(row.get("tag_evidence_json")) or "{}")
        evidence = payload.get(tag) if isinstance(payload, dict) else None
        if isinstance(evidence, dict):
            tag_evidence_basis = text_value(evidence.get("precursor_mz_basis"))
    except json.JSONDecodeError:
        tag_evidence_basis = ""
    return {
        "candidate_id": text_value(row.get("candidate_id")),
        "row_identity": _row_identity(row),
        "sample": text_value(row.get("sample_stem")),
        "tag": tag,
        "source_state": _row_state(row),
        "precursor_mz": optional_float(row.get("precursor_mz")),
        "product_mz": optional_float(row.get("product_mz")),
        "precursor_mz_basis": text_value(row.get("precursor_mz_basis")),
        "neutral_loss_error_basis": text_value(row.get("neutral_loss_error_basis")),
        "tag_evidence_precursor_mz_basis": tag_evidence_basis,
        "ms1_peak_found": _bool_value(row.get("ms1_peak_found")),
        "ms1_apex_rt": optional_float(row.get("ms1_apex_rt")),
        "ms1_peak_rt_start": optional_float(row.get("ms1_peak_rt_start")),
        "ms1_peak_rt_end": optional_float(row.get("ms1_peak_rt_end")),
        "ms1_area": optional_float(row.get("ms1_area")),
        "best_ms2_scan_id": optional_int(row.get("best_ms2_scan_id")),
        "seed_scan_ids": split_semicolon_labels(row.get("seed_scan_ids")),
        "feature_family_id": text_value(row.get("feature_family_id")),
        "feature_superfamily_id": text_value(row.get("feature_superfamily_id")),
        "raw_file": text_value(row.get("raw_file")),
    }


def _row_identity(row: Mapping[str, str]) -> str:
    return text_value(row.get("ms1_feature_row_id"))


def _row_state(row: Mapping[str, str]) -> str:
    return text_value(row.get("discovery_candidate_state"))


def _has_rescue_basis(
    row: Mapping[str, str],
    tag_evidence: Mapping[str, Any],
) -> bool:
    return (
        text_value(row.get("precursor_mz_basis")) in RESCUE_BASIS_VALUES
        or text_value(tag_evidence.get("precursor_mz_basis")) in RESCUE_BASIS_VALUES
    )


def _max_scan_precursor_abs_delta(
    row: Mapping[str, str],
    tag: str,
) -> float | None:
    row_delta = optional_float(row.get("max_scan_precursor_abs_delta_da"))
    tag_delta: float | None = None
    try:
        payload = json.loads(text_value(row.get("tag_evidence_json")) or "{}")
        evidence = payload.get(tag) if isinstance(payload, dict) else None
        if isinstance(evidence, dict):
            tag_delta = optional_float(evidence.get("max_scan_precursor_abs_delta_da"))
    except json.JSONDecodeError:
        tag_delta = None
    values = [value for value in (row_delta, tag_delta) if value is not None]
    return max(values) if values else None


def _row_in_rt_window(
    row: Mapping[str, str],
    *,
    rt_min: float,
    rt_max: float,
) -> bool:
    values = (
        optional_float(row.get("ms1_apex_rt")),
        optional_float(row.get("best_seed_rt")),
    )
    return any(value is not None and rt_min <= value <= rt_max for value in values)


def _bool_value(value: object) -> bool | None:
    normalized = text_value(value).upper()
    if normalized in {"TRUE", "T", "YES", "Y", "1"}:
        return True
    if normalized in {"FALSE", "F", "NO", "N", "0"}:
        return False
    return None


def _artifact_summary(
    path: Path,
    rows: Sequence[Mapping[str, str]],
    facts: Mapping[str, Mapping[str, Any]],
    *,
    alignment_parser_status: str = "not_checked",
) -> dict[str, Any]:
    return {
        "candidates_csv": _relative_or_absolute(path),
        "candidates_csv_sha256": file_sha256(path) if path.exists() else "",
        "alignment_parser_status": alignment_parser_status,
        "row_count": len(rows),
        "basis_counts": _counts(row.get("precursor_mz_basis", "") for row in rows),
        "state_counts": _counts(_row_state(row) for row in rows),
        "facts": facts,
    }


def _counts(values: Sequence[str] | Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = text_value(value) or "<blank>"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check CID-NL Discovery A/B candidate artifacts for successor-safe "
            "row identity, tag provenance, source state, and the 300/184 + "
            "301/185 TumorBC2312_DNA oracle."
        )
    )
    parser.add_argument(
        "--baseline-candidates",
        type=Path,
        default=DEFAULT_BASELINE_CANDIDATES_CSV,
    )
    parser.add_argument(
        "--candidate-candidates",
        type=Path,
        default=DEFAULT_CANDIDATE_CANDIDATES_CSV,
    )
    parser.add_argument("--focus-sample", default=DEFAULT_FOCUS_SAMPLE)
    parser.add_argument(
        "--focus-precursor-mz",
        type=float,
        default=DEFAULT_FOCUS_PRECURSOR_MZ,
    )
    parser.add_argument(
        "--focus-product-mz",
        type=float,
        default=DEFAULT_FOCUS_PRODUCT_MZ,
    )
    parser.add_argument(
        "--preserve-precursor-mz",
        type=float,
        default=DEFAULT_PRESERVE_PRECURSOR_MZ,
    )
    parser.add_argument(
        "--preserve-product-mz",
        type=float,
        default=DEFAULT_PRESERVE_PRODUCT_MZ,
    )
    parser.add_argument("--preserve-tag", default=DEFAULT_TAG)
    parser.add_argument("--rt-min", type=float, default=DEFAULT_RT_MIN)
    parser.add_argument("--rt-max", type=float, default=DEFAULT_RT_MAX)
    parser.add_argument(
        "--mz-tolerance-da",
        type=float,
        default=DEFAULT_MZ_TOLERANCE_DA,
    )
    parser.add_argument("--expected-candidate-row-count", type=int)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Accepted for symmetry with productization checkers.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    problems = check_discovery_architecture_ab_artifact(
        baseline_candidates_csv=args.baseline_candidates,
        candidate_candidates_csv=args.candidate_candidates,
        focus_sample=args.focus_sample,
        focus_precursor_mz=args.focus_precursor_mz,
        focus_product_mz=args.focus_product_mz,
        preserve_precursor_mz=args.preserve_precursor_mz,
        preserve_product_mz=args.preserve_product_mz,
        preserve_tag=args.preserve_tag,
        mz_tolerance_da=args.mz_tolerance_da,
        rt_min=args.rt_min,
        rt_max=args.rt_max,
        expected_candidate_row_count=args.expected_candidate_row_count,
    )
    if args.summary_json is not None:
        write_summary(
            args.summary_json,
            baseline_candidates_csv=args.baseline_candidates,
            candidate_candidates_csv=args.candidate_candidates,
            problems=problems,
            focus_sample=args.focus_sample,
            focus_precursor_mz=args.focus_precursor_mz,
            focus_product_mz=args.focus_product_mz,
            preserve_precursor_mz=args.preserve_precursor_mz,
            preserve_product_mz=args.preserve_product_mz,
            preserve_tag=args.preserve_tag,
            mz_tolerance_da=args.mz_tolerance_da,
            rt_min=args.rt_min,
            rt_max=args.rt_max,
            expected_candidate_row_count=args.expected_candidate_row_count,
        )
    if problems:
        for problem in problems:
            print(f"discovery_architecture_ab_problem: {problem}")
        return 1
    print(f"discovery_architecture_ab_baseline_csv: {args.baseline_candidates}")
    print(f"discovery_architecture_ab_candidate_csv: {args.candidate_candidates}")
    print("discovery_architecture_ab_readiness_label: diagnostic_only")
    print("discovery_architecture_ab_status: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
