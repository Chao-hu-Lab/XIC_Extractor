"""Guardrail diagnostics for untargeted alignment checkpoint outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

PRODUCTION_STATUSES = {"detected", "rescued"}
COMPARISON_METRICS = [
    "duplicate_only_families",
    "zero_present_families",
    "review_rescue_count",
    "rescue_only_review_families",
    "identity_anchor_lost_families",
    "duplicate_claim_pressure_families",
    "negative_checkpoint_production_families",
]
CASE_SUMMARY_COLUMNS = [
    "case",
    "production_family_count",
    "owner_count",
    "event_count",
    "supporting_event_count",
    "strong_edge_count",
    "preserved_split_or_ambiguous",
    "status",
    "reason",
]


@dataclass(frozen=True)
class CaseWindow:
    name: str
    mz: float
    ppm: float
    rt_min: float
    rt_max: float


@dataclass(frozen=True)
class CaseAssertion:
    production_family_count: int
    owner_count: int
    event_count: int
    supporting_event_count: int
    strong_edge_count: int
    preserved_split_or_ambiguous: bool
    status: str
    reason: str


@dataclass(frozen=True)
class GuardrailMetrics:
    zero_present_families: int
    duplicate_only_families: int
    high_backfill_dependency_families: int
    negative_8oxodg_production_families: int
    negative_checkpoint_production_families: int
    accepted_quantitative_cells: int
    accepted_rescue_cells: int
    accepted_rescue_rate: float
    review_rescue_count: int
    rescue_only_review_families: int
    identity_anchor_lost_families: int
    duplicate_claim_pressure_families: int
    istd_false_missing_recovery: int
    case_assertions: dict[str, CaseAssertion]


CASE_WINDOWS = [
    CaseWindow("case1_mz242_5medC_like", 242.114, 20.0, 11.0, 13.2),
    CaseWindow("case2_mz296_dense_duplicate", 296.074, 20.0, 19.2, 20.0),
    CaseWindow("case3_mz322_dense_duplicate", 322.143, 20.0, 22.4, 24.1),
    CaseWindow("case4_mz251_anchor_shadow_duplicates", 251.084, 20.0, 8.0, 9.0),
]


def compute_guardrails(alignment_dir: Path) -> GuardrailMetrics:
    review_rows = _read_required_tsv(alignment_dir / "alignment_review.tsv")
    cell_rows = _read_required_tsv(alignment_dir / "alignment_cells.tsv")
    edge_rows = _read_optional_tsv(alignment_dir / "owner_edge_evidence.tsv")

    status_counts = _status_counts_by_family(cell_rows)
    review_has_warning_column = any("warning" in row for row in review_rows)
    review_by_family = {
        row.get("feature_family_id", ""): row
        for row in review_rows
        if row.get("feature_family_id", "")
    }
    family_ids = set(review_by_family) | set(status_counts)

    zero_present = 0
    duplicate_only = 0
    high_backfill = 0
    negative_8oxodg = 0
    negative_checkpoint = 0
    accepted_quantitative_cells = 0
    accepted_rescue_cells = 0
    review_rescue_count = 0
    rescue_only_review = 0
    identity_anchor_lost = 0
    duplicate_claim_pressure = 0
    for family_id in family_ids:
        counts = status_counts[family_id]
        detected_count = counts["detected"]
        rescued_count = counts["rescued"]
        production_present_count = detected_count + rescued_count
        duplicate_assigned_count = counts["duplicate_assigned"]
        review_row = review_by_family.get(family_id, {})
        accepted_cells = _int_value(review_row.get("accepted_cell_count"))
        accepted_rescues = _int_value(review_row.get("accepted_rescue_count"))
        review_rescues = _int_value(review_row.get("review_rescue_count"))
        row_flags = _row_flags(review_row)
        accepted_quantitative_cells += accepted_cells
        accepted_rescue_cells += accepted_rescues
        review_rescue_count += review_rescues
        if "rescue_only_review" in row_flags:
            rescue_only_review += 1
        if "identity_anchor_lost" in row_flags:
            identity_anchor_lost += 1
        if "duplicate_claim_pressure" in row_flags:
            duplicate_claim_pressure += 1

        production_family = _is_production_family(review_row, counts)
        if not production_family:
            zero_present += 1
        if not production_family and duplicate_assigned_count > 0:
            duplicate_only += 1
        if _is_high_backfill_dependency(
            review_row,
            detected_count,
            rescued_count,
            review_has_warning_column,
        ):
            high_backfill += 1
        if production_family and _row_in_mz_window(
            review_row,
            "family_center_mz",
            284.0989,
            20.0,
        ):
            negative_8oxodg += 1
        if production_family and _row_in_mz_window(
            review_row,
            "family_center_mz",
            284.0989,
            20.0,
        ):
            negative_checkpoint += 1

    return GuardrailMetrics(
        zero_present_families=zero_present,
        duplicate_only_families=duplicate_only,
        high_backfill_dependency_families=high_backfill,
        negative_8oxodg_production_families=negative_8oxodg,
        negative_checkpoint_production_families=negative_checkpoint,
        accepted_quantitative_cells=accepted_quantitative_cells,
        accepted_rescue_cells=accepted_rescue_cells,
        accepted_rescue_rate=(
            accepted_rescue_cells / accepted_quantitative_cells
            if accepted_quantitative_cells
            else 0.0
        ),
        review_rescue_count=review_rescue_count,
        rescue_only_review_families=rescue_only_review,
        identity_anchor_lost_families=identity_anchor_lost,
        duplicate_claim_pressure_families=duplicate_claim_pressure,
        istd_false_missing_recovery=0,
        case_assertions=_compute_case_assertions(
            review_rows,
            status_counts,
            edge_rows,
        ),
    )


def compare_guardrails(
    baseline: Mapping[str, int],
    candidate: Mapping[str, int],
) -> list[dict[str, str]]:
    rows = []
    for metric in COMPARISON_METRICS:
        baseline_count = int(baseline.get(metric, 0))
        candidate_count = int(candidate.get(metric, 0))
        delta = candidate_count - baseline_count
        rows.append(
            {
                "metric": metric,
                "baseline_count": str(baseline_count),
                "candidate_count": str(candidate_count),
                "delta": str(delta),
                "status": "FAIL" if delta > 0 else "PASS",
            },
        )
    return rows


def write_case_assertion_summary_tsv(
    path: Path,
    cases: Mapping[str, CaseAssertion],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CASE_SUMMARY_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for case_name, assertion in cases.items():
            writer.writerow(_case_summary_row(case_name, assertion))
    return path


def compare_targeted_audit_counts(
    baseline_csv: Path,
    candidate_csv: Path,
    *,
    target_label: str,
) -> list[dict[str, str]]:
    baseline_counts = _targeted_failure_counts(baseline_csv, target_label)
    candidate_counts = _targeted_failure_counts(candidate_csv, target_label)
    rows = []
    for failure_mode in ("SPLIT", "MISS"):
        baseline_count = baseline_counts[failure_mode]
        candidate_count = candidate_counts[failure_mode]
        delta = candidate_count - baseline_count
        rows.append(
            {
                "target_label": target_label,
                "failure_mode": failure_mode,
                "baseline_count": str(baseline_count),
                "candidate_count": str(candidate_count),
                "delta": str(delta),
                "status": "FAIL" if delta > 0 else "PASS",
            },
        )
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        _validate_args(args)
        if args.alignment_dir:
            metrics = compute_guardrails(args.alignment_dir)
            if args.output_json:
                _write_json(args.output_json, _metrics_to_json(metrics))
            if args.case_summary_tsv:
                write_case_assertion_summary_tsv(
                    args.case_summary_tsv,
                    metrics.case_assertions,
                )

        if args.baseline_dir and args.candidate_dir:
            baseline_metrics = compute_guardrails(args.baseline_dir)
            candidate_metrics = compute_guardrails(args.candidate_dir)
            _write_dict_csv(
                args.comparison_csv,
                compare_guardrails(
                    _metrics_for_comparison(baseline_metrics),
                    _metrics_for_comparison(candidate_metrics),
                ),
            )

        if args.baseline_targeted_comparison and args.candidate_targeted_comparison:
            if not args.target_label:
                raise ValueError("--target-label is required for targeted comparison")
            _write_dict_csv(
                args.targeted_comparison_csv,
                compare_targeted_audit_counts(
                    args.baseline_targeted_comparison,
                    args.candidate_targeted_comparison,
                    target_label=args.target_label,
                ),
            )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute and compare untargeted alignment guardrails.",
    )
    parser.add_argument("--alignment-dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--case-summary-tsv", type=Path)
    parser.add_argument("--comparison-csv", type=Path)
    parser.add_argument("--baseline-targeted-comparison", type=Path)
    parser.add_argument("--candidate-targeted-comparison", type=Path)
    parser.add_argument("--target-label")
    parser.add_argument("--targeted-comparison-csv", type=Path)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
    baseline_group = (
        args.baseline_dir,
        args.candidate_dir,
        args.comparison_csv,
    )
    targeted_group = (
        args.baseline_targeted_comparison,
        args.candidate_targeted_comparison,
        args.target_label,
        args.targeted_comparison_csv,
    )
    alignment_group = (
        args.alignment_dir,
        args.output_json,
        args.case_summary_tsv,
    )
    has_alignment_group = any(value is not None for value in alignment_group)
    has_baseline_group = any(value is not None for value in baseline_group)
    has_targeted_group = any(value is not None for value in targeted_group)

    if has_alignment_group and (
        args.alignment_dir is None or args.output_json is None
    ):
        raise ValueError(
            "Alignment group requires --alignment-dir and --output-json",
        )
    if has_baseline_group and not all(value is not None for value in baseline_group):
        raise ValueError(
            "Guardrail comparison requires --baseline-dir, --candidate-dir, "
            "and --comparison-csv",
        )
    if has_targeted_group and not all(value is not None for value in targeted_group):
        raise ValueError(
            "Targeted comparison requires --baseline-targeted-comparison, "
            "--candidate-targeted-comparison, --target-label, and "
            "--targeted-comparison-csv",
        )
    if not (has_alignment_group or has_baseline_group or has_targeted_group):
        raise ValueError(
            "Provide at least one actionable option group: "
            "--alignment-dir with --output-json; --baseline-dir with "
            "--candidate-dir and --comparison-csv; or "
            "--baseline-targeted-comparison with --candidate-targeted-comparison, "
            "--target-label, and --targeted-comparison-csv.",
        )


def _compute_case_assertions(
    review_rows: list[dict[str, str]],
    status_counts: Mapping[str, Counter[str]],
    edge_rows: list[dict[str, str]],
) -> dict[str, CaseAssertion]:
    assertions = {}
    for window in CASE_WINDOWS:
        review_in_window = [
            row for row in review_rows if _review_row_in_window(row, window)
        ]
        production_family_count = sum(
            1
            for row in review_in_window
            if _is_production_family(
                row,
                status_counts[row.get("feature_family_id", "")],
            )
        )
        owner_count = sum(_int_value(row.get("event_cluster_count")) for row in review_in_window)
        event_count = sum(_int_value(row.get("event_member_count")) for row in review_in_window)
        supporting_event_count = max(event_count - owner_count, 0)
        ambiguous_count = sum(
            status_counts[row.get("feature_family_id", "")]["ambiguous_ms1_owner"]
            for row in review_in_window
        )
        preserved_split_or_ambiguous = (
            window.name == "case2_mz296_dense_duplicate"
            and (len(review_in_window) > 1 or ambiguous_count > 0)
        )
        strong_edge_count = _strong_edge_count(edge_rows, window)
        status, reason = _case_status_reason(
            window.name,
            production_family_count,
            supporting_event_count,
            strong_edge_count,
            preserved_split_or_ambiguous,
        )
        assertions[window.name] = CaseAssertion(
            production_family_count=production_family_count,
            owner_count=owner_count,
            event_count=event_count,
            supporting_event_count=supporting_event_count,
            strong_edge_count=strong_edge_count,
            preserved_split_or_ambiguous=preserved_split_or_ambiguous,
            status=status,
            reason=reason,
        )
    return assertions


def _case_status_reason(
    case_name: str,
    production_family_count: int,
    supporting_event_count: int,
    strong_edge_count: int,
    preserved_split_or_ambiguous: bool,
) -> tuple[str, str]:
    if case_name == "case1_mz242_5medC_like":
        if production_family_count > 0 and supporting_event_count > 0:
            return "PASS", "production family retains supporting events"
        return "WARN", "missing production family or supporting events"
    if case_name == "case2_mz296_dense_duplicate":
        if preserved_split_or_ambiguous:
            return "PASS", "split or ambiguous ownership is preserved"
        return "WARN", "dense duplicate case collapsed without ambiguity marker"
    if case_name == "case3_mz322_dense_duplicate":
        if strong_edge_count > 0:
            return "PASS", "strong owner edge evidence is present"
        return "WARN", "no strong owner edge evidence in case window"
    if production_family_count == 0:
        return "PASS", "shadow duplicate case has no production family"
    return "WARN", "shadow duplicate case still has production family"


def _status_counts_by_family(
    cell_rows: list[dict[str, str]],
) -> defaultdict[str, Counter[str]]:
    counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in cell_rows:
        family_id = row.get("feature_family_id", "")
        if family_id:
            counts[family_id][row.get("status", "")] += 1
    return counts


def _is_high_backfill_dependency(
    review_row: Mapping[str, str],
    detected_count: int,
    rescued_count: int,
    review_has_warning_column: bool,
) -> bool:
    if review_has_warning_column:
        return review_row.get("warning") == "high_backfill_dependency"
    return rescued_count > detected_count and rescued_count >= 2


def _production_present_count(counts: Counter[str]) -> int:
    return sum(counts[status] for status in PRODUCTION_STATUSES)


def _is_production_family(
    review_row: Mapping[str, str],
    counts: Counter[str],
) -> bool:
    if "include_in_primary_matrix" in review_row:
        return _is_trueish(review_row.get("include_in_primary_matrix"))
    if "accepted_cell_count" in review_row:
        return _int_value(review_row.get("accepted_cell_count")) > 0
    return _production_present_count(counts) > 0


def _is_trueish(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def _review_row_in_window(row: Mapping[str, str], window: CaseWindow) -> bool:
    return _row_in_mz_window(
        row,
        "family_center_mz",
        window.mz,
        window.ppm,
    ) and _float_in_range(
        _first_present(row, ("family_center_rt", "family_center_rt_min")),
        window.rt_min,
        window.rt_max,
    )


def _strong_edge_count(rows: list[dict[str, str]], window: CaseWindow) -> int:
    count = 0
    for row in rows:
        if row.get("decision") != "strong_edge":
            continue
        real_schema_match = _edge_endpoint_in_window(
            row,
            "left",
            window,
            mz_keys=("left_precursor_mz", "left_mz", "left_family_center_mz"),
            rt_keys=(
                "left_rt_min",
                "left_family_center_rt",
                "left_family_center_rt_min",
            ),
        ) and _edge_endpoint_in_window(
            row,
            "right",
            window,
            mz_keys=("right_precursor_mz", "right_mz", "right_family_center_mz"),
            rt_keys=(
                "right_rt_min",
                "right_family_center_rt",
                "right_family_center_rt_min",
            ),
        )
        legacy_schema_match = _edge_endpoint_in_window(
            row,
            "endpoint_a",
            window,
        ) and _edge_endpoint_in_window(
            row,
            "endpoint_b",
            window,
        )
        if real_schema_match or legacy_schema_match:
            count += 1
    return count


def _edge_endpoint_in_window(
    row: Mapping[str, str],
    prefix: str,
    window: CaseWindow,
    *,
    mz_keys: Sequence[str] | None = None,
    rt_keys: Sequence[str] | None = None,
) -> bool:
    if mz_keys is None:
        mz_keys = (f"{prefix}_mz", f"{prefix}_family_center_mz")
    if rt_keys is None:
        rt_keys = (
            f"{prefix}_rt_min",
            f"{prefix}_family_center_rt",
            f"{prefix}_family_center_rt_min",
        )
    mz_value = _first_present(row, mz_keys)
    rt_value = _first_present(row, rt_keys)
    return _mz_in_ppm(mz_value, window.mz, window.ppm) and _float_in_range(
        rt_value,
        window.rt_min,
        window.rt_max,
    )


def _row_in_mz_window(
    row: Mapping[str, str],
    key: str,
    center_mz: float,
    ppm: float,
) -> bool:
    return _mz_in_ppm(row.get(key), center_mz, ppm)


def _mz_in_ppm(value: str | None, center_mz: float, ppm: float) -> bool:
    parsed = _float_value(value)
    if parsed is None:
        return False
    return abs(parsed - center_mz) <= center_mz * ppm / 1_000_000


def _float_in_range(value: str | None, minimum: float, maximum: float) -> bool:
    parsed = _float_value(value)
    return parsed is not None and minimum <= parsed <= maximum


def _float_value(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _int_value(value: str | None) -> int:
    parsed = _float_value(value)
    if parsed is None or not math.isfinite(parsed):
        return 0
    return int(parsed)


def _row_flags(row: Mapping[str, str | None]) -> set[str]:
    value = row.get("row_flags", "")
    if value in (None, ""):
        return set()
    return {part.strip() for part in value.split(";") if part.strip()}


def _first_present(row: Mapping[str, str], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _read_required_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return _read_tsv(path)


def _read_optional_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return _read_tsv(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _targeted_failure_counts(path: Path, target_label: str) -> Counter[str]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    counts: Counter[str] = Counter()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if "failure_mode" not in fieldnames:
            raise ValueError(f"{path} is missing required column: failure_mode")
        has_target_label = "target_label" in fieldnames
        for row in reader:
            if not has_target_label or row.get("target_label") == target_label:
                counts[row.get("failure_mode", "")] += 1
    return counts


def _case_summary_row(case_name: str, assertion: CaseAssertion) -> dict[str, str]:
    return {
        "case": case_name,
        "production_family_count": str(assertion.production_family_count),
        "owner_count": str(assertion.owner_count),
        "event_count": str(assertion.event_count),
        "supporting_event_count": str(assertion.supporting_event_count),
        "strong_edge_count": str(assertion.strong_edge_count),
        "preserved_split_or_ambiguous": _bool_text(
            assertion.preserved_split_or_ambiguous,
        ),
        "status": assertion.status,
        "reason": assertion.reason,
    }


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _metrics_for_comparison(metrics: GuardrailMetrics) -> dict[str, int]:
    return {metric: int(getattr(metrics, metric)) for metric in COMPARISON_METRICS}


def _metrics_to_json(metrics: GuardrailMetrics) -> dict[str, object]:
    payload = asdict(metrics)
    payload["case_assertions"] = {
        case_name: asdict(assertion)
        for case_name, assertion in metrics.case_assertions.items()
    }
    return payload


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_dict_csv(path: Path | None, rows: list[dict[str, str]]) -> None:
    if path is None:
        raise ValueError("comparison output path is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
