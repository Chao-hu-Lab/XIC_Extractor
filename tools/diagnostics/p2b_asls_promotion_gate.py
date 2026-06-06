"""P2b revised AsLS promotion gate."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


ROW_FIELDS = (
    "target_label",
    "selected_feature_id",
    "old_status",
    "old_failure_reasons",
    "linear_area_rsd_pct",
    "asls_area_rsd_pct",
    "area_rsd_delta_pct",
    "asls_exceeds_raw_area_count",
    "baseline_truth_review_status",
    "baseline_truth_dominant_classification",
    "evidence_spine_status",
    "evidence_spine_sample_count",
    "evidence_spine_max_abs_rt_delta_sec",
    "evidence_spine_overwide_boundary_count",
    "evidence_spine_narrower_boundary_count",
    "target_rt_trend_status",
    "target_rt_trend_local_abs_delta_p95_min",
    "target_rt_trend_local_moderate_or_severe_count",
    "target_rt_trend_local_severe_count",
    "revised_status",
    "hard_blockers",
    "accepted_reasons",
)

SUMMARY_FIELDS = (
    "overall_status",
    "target_count",
    "hard_blocker_count",
    "review_accepted_count",
    "global_blockers",
    "area_uncertainty_unexplained_area_mismatch_count",
    "area_uncertainty_integration_context_incomplete_count",
)

_P2_REQUIRED_COLUMNS = {
    "target_label",
    "selected_feature_id",
    "status",
    "failure_reasons",
    "linear_area_rsd_pct",
    "asls_area_rsd_pct",
    "area_rsd_delta_pct",
    "asls_exceeds_raw_area_count",
}
_TRUTH_REQUIRED_COLUMNS = {
    "feature_family_id",
    "review_status",
    "dominant_classification",
}
_UNCERTAINTY_REQUIRED_COLUMNS = {
    "unexplained_area_mismatch_count",
    "integration_context_incomplete_count",
}
_EVIDENCE_SPINE_REQUIRED_COLUMNS = {
    "target_label",
    "untargeted_family_id",
    "rt_delta_min",
    "boundary_delta_start_min",
    "boundary_delta_end_min",
}
_TARGET_RT_TREND_REQUIRED_COLUMNS = {
    "target_label",
    "local_abs_delta_p95_min",
    "local_moderate_or_severe_count",
    "local_severe_count",
}
_HARD_FAILURE_REASONS = {
    "sample_count_lt_2",
    "shadow_coverage_incomplete",
    "area_rsd_unavailable",
    "asls_area_exceeds_raw_area",
}
_RT_BOUNDARY_MAX_RT_DELTA_SEC = 0.5
_RT_BOUNDARY_OVERWIDE_TOLERANCE_MIN = 0.10
_TARGET_RT_TREND_LOCAL_P95_MAX_MIN = 0.10


@dataclass(frozen=True)
class P2bAslsPromotionGateOutputs:
    rows_tsv: Path
    summary_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class P2bAslsPromotionGateRow:
    target_label: str
    selected_feature_id: str
    old_status: str
    old_failure_reasons: tuple[str, ...]
    linear_area_rsd_pct: float | None
    asls_area_rsd_pct: float | None
    area_rsd_delta_pct: float | None
    asls_exceeds_raw_area_count: int
    baseline_truth_review_status: str
    baseline_truth_dominant_classification: str
    evidence_spine_status: str
    evidence_spine_sample_count: int
    evidence_spine_max_abs_rt_delta_sec: float | None
    evidence_spine_overwide_boundary_count: int
    evidence_spine_narrower_boundary_count: int
    target_rt_trend_status: str
    target_rt_trend_local_abs_delta_p95_min: float | None
    target_rt_trend_local_moderate_or_severe_count: int | None
    target_rt_trend_local_severe_count: int | None
    revised_status: str
    hard_blockers: tuple[str, ...]
    accepted_reasons: tuple[str, ...]


@dataclass(frozen=True)
class _EvidenceSpineSummary:
    status: str
    sample_count: int
    max_abs_rt_delta_sec: float | None
    overwide_boundary_count: int
    narrower_boundary_count: int


@dataclass(frozen=True)
class _TargetRtTrendSummary:
    status: str
    local_abs_delta_p95_min: float | None
    local_moderate_or_severe_count: int | None
    local_severe_count: int | None


@dataclass(frozen=True)
class P2bAslsPromotionGateResult:
    overall_status: str
    target_count: int
    hard_blocker_count: int
    review_accepted_count: int
    global_blockers: tuple[str, ...]
    area_uncertainty_unexplained_area_mismatch_count: int
    area_uncertainty_integration_context_incomplete_count: int
    rows: tuple[P2bAslsPromotionGateRow, ...]


def run_p2b_asls_promotion_gate(
    *,
    p2_gate_rows_tsv: Path,
    baseline_truth_summary_tsv: Path,
    area_uncertainty_summary_tsv: Path,
    evidence_spine_rows_tsv: Path | None = None,
    target_rt_trend_summary_tsv: Path | None = None,
    output_dir: Path,
) -> tuple[P2bAslsPromotionGateOutputs, P2bAslsPromotionGateResult]:
    p2_rows = _read_tsv(p2_gate_rows_tsv, _P2_REQUIRED_COLUMNS)
    truth_rows = _read_tsv(baseline_truth_summary_tsv, _TRUTH_REQUIRED_COLUMNS)
    evidence_spine_rows = (
        None
        if evidence_spine_rows_tsv is None
        else _read_tsv(evidence_spine_rows_tsv, _EVIDENCE_SPINE_REQUIRED_COLUMNS)
    )
    target_rt_trend_by_label = (
        {}
        if target_rt_trend_summary_tsv is None
        else _read_target_rt_trend(target_rt_trend_summary_tsv)
    )
    uncertainty_row = _single_row(
        _read_tsv(area_uncertainty_summary_tsv, _UNCERTAINTY_REQUIRED_COLUMNS),
        area_uncertainty_summary_tsv,
    )
    truth_by_family = {
        row["feature_family_id"].strip(): row
        for row in truth_rows
        if row.get("feature_family_id", "").strip()
    }
    rows = tuple(
        _build_row(
            row,
            truth_by_family=truth_by_family,
            evidence_spine_rows=evidence_spine_rows,
            target_rt_trend_by_label=target_rt_trend_by_label,
        )
        for row in p2_rows
    )
    unexplained = _parse_non_negative_int(
        uncertainty_row.get("unexplained_area_mismatch_count", ""),
        "unexplained_area_mismatch_count",
    )
    incomplete = _parse_non_negative_int(
        uncertainty_row.get("integration_context_incomplete_count", ""),
        "integration_context_incomplete_count",
    )
    global_blockers: list[str] = []
    if unexplained > 0:
        global_blockers.append("area_uncertainty_unexplained_mismatch")
    if incomplete > 0:
        global_blockers.append("area_uncertainty_context_incomplete")
    hard_blocker_count = sum(1 for row in rows if row.hard_blockers)
    result = P2bAslsPromotionGateResult(
        overall_status=(
            "NO_GO"
            if hard_blocker_count or global_blockers
            else "GO_FOR_PRODUCTION_CANDIDATE"
        ),
        target_count=len(rows),
        hard_blocker_count=hard_blocker_count,
        review_accepted_count=sum(
            row.revised_status == "ACCEPTED_REVIEW" for row in rows
        ),
        global_blockers=tuple(global_blockers),
        area_uncertainty_unexplained_area_mismatch_count=unexplained,
        area_uncertainty_integration_context_incomplete_count=incomplete,
        rows=rows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = P2bAslsPromotionGateOutputs(
        rows_tsv=output_dir / "p2b_asls_promotion_gate_rows.tsv",
        summary_tsv=output_dir / "p2b_asls_promotion_gate_summary.tsv",
        json_path=output_dir / "p2b_asls_promotion_gate.json",
        markdown_path=output_dir / "p2b_asls_promotion_gate.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the revised P2b AsLS promotion gate."
    )
    parser.add_argument("--p2-gate-rows-tsv", type=Path, required=True)
    parser.add_argument("--baseline-truth-summary-tsv", type=Path, required=True)
    parser.add_argument("--area-uncertainty-summary-tsv", type=Path, required=True)
    parser.add_argument("--evidence-spine-rows-tsv", type=Path)
    parser.add_argument("--target-rt-trend-summary-tsv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        outputs, result = run_p2b_asls_promotion_gate(
            p2_gate_rows_tsv=args.p2_gate_rows_tsv,
            baseline_truth_summary_tsv=args.baseline_truth_summary_tsv,
            area_uncertainty_summary_tsv=args.area_uncertainty_summary_tsv,
            evidence_spine_rows_tsv=args.evidence_spine_rows_tsv,
            target_rt_trend_summary_tsv=args.target_rt_trend_summary_tsv,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Gate JSON: {outputs.json_path}")
    print(f"Gate report: {outputs.markdown_path}")
    return 0 if result.overall_status == "GO_FOR_PRODUCTION_CANDIDATE" else 1


def _build_row(
    row: Mapping[str, str],
    *,
    truth_by_family: Mapping[str, Mapping[str, str]],
    evidence_spine_rows: Sequence[Mapping[str, str]] | None,
    target_rt_trend_by_label: Mapping[str, _TargetRtTrendSummary],
) -> P2bAslsPromotionGateRow:
    family_id = row["selected_feature_id"].strip()
    target_label = row["target_label"].strip()
    old_reasons = _split_reasons(row.get("failure_reasons", ""))
    truth = truth_by_family.get(family_id)
    truth_status = "" if truth is None else truth.get("review_status", "").strip()
    truth_classification = (
        "" if truth is None else truth.get("dominant_classification", "").strip()
    )
    hard_blockers: list[str] = []
    accepted_reasons: list[str] = []
    asls_exceeds_raw_count = _parse_non_negative_int(
        row.get("asls_exceeds_raw_area_count", ""),
        "asls_exceeds_raw_area_count",
    )
    hard_blockers.extend(
        reason for reason in old_reasons if reason in _HARD_FAILURE_REASONS
    )
    if asls_exceeds_raw_count > 0 and "asls_area_exceeds_raw_area" not in hard_blockers:
        hard_blockers.append("asls_area_exceeds_raw_area")
    unknown_reasons = [
        reason
        for reason in old_reasons
        if reason not in _HARD_FAILURE_REASONS and reason != "area_rsd_regression"
    ]
    hard_blockers.extend(
        f"unsupported_old_failure_reason:{reason}" for reason in unknown_reasons
    )
    evidence_spine_summary = _empty_evidence_spine_summary()
    target_rt_trend = target_rt_trend_by_label.get(
        target_label,
        _empty_target_rt_trend_summary(),
    )
    if "area_rsd_regression" in old_reasons:
        if truth is None:
            hard_blockers.append("baseline_truth_missing")
        elif truth_status == "linear_edge_over_subtraction_plausible":
            accepted_reasons.append(
                "baseline_truth_supports_linear_edge_over_subtraction"
            )
        elif evidence_spine_rows is not None:
            evidence_spine_summary = _summarize_evidence_spine(
                evidence_spine_rows,
                target_label=target_label,
                family_id=family_id,
                expected_sample_count=_parse_non_negative_int(
                    row.get("sample_count", ""),
                    "sample_count",
                ),
                target_rt_trend=target_rt_trend,
            )
            if evidence_spine_summary.status == "rt_boundary_supported":
                accepted_reasons.append(
                    "rt_boundary_evidence_supports_area_variability"
                )
            elif (
                evidence_spine_summary.status
                == "rt_boundary_rt_delta_explained_by_target_trend"
            ):
                accepted_reasons.append("target_rt_trend_supports_large_rt_delta")
            else:
                hard_blockers.append(evidence_spine_summary.status)
        else:
            hard_blockers.append("baseline_truth_not_supportive")
    if hard_blockers:
        revised_status = "FAIL"
    elif accepted_reasons:
        revised_status = "ACCEPTED_REVIEW"
    else:
        revised_status = "PASS"
    return P2bAslsPromotionGateRow(
        target_label=target_label,
        selected_feature_id=family_id,
        old_status=row["status"].strip().upper(),
        old_failure_reasons=old_reasons,
        linear_area_rsd_pct=_optional_float(row.get("linear_area_rsd_pct")),
        asls_area_rsd_pct=_optional_float(row.get("asls_area_rsd_pct")),
        area_rsd_delta_pct=_optional_float(row.get("area_rsd_delta_pct")),
        asls_exceeds_raw_area_count=asls_exceeds_raw_count,
        baseline_truth_review_status=truth_status,
        baseline_truth_dominant_classification=truth_classification,
        evidence_spine_status=evidence_spine_summary.status,
        evidence_spine_sample_count=evidence_spine_summary.sample_count,
        evidence_spine_max_abs_rt_delta_sec=(
            evidence_spine_summary.max_abs_rt_delta_sec
        ),
        evidence_spine_overwide_boundary_count=(
            evidence_spine_summary.overwide_boundary_count
        ),
        evidence_spine_narrower_boundary_count=(
            evidence_spine_summary.narrower_boundary_count
        ),
        target_rt_trend_status=target_rt_trend.status,
        target_rt_trend_local_abs_delta_p95_min=(
            target_rt_trend.local_abs_delta_p95_min
        ),
        target_rt_trend_local_moderate_or_severe_count=(
            target_rt_trend.local_moderate_or_severe_count
        ),
        target_rt_trend_local_severe_count=target_rt_trend.local_severe_count,
        revised_status=revised_status,
        hard_blockers=tuple(hard_blockers),
        accepted_reasons=tuple(accepted_reasons),
    )


def _empty_evidence_spine_summary() -> _EvidenceSpineSummary:
    return _EvidenceSpineSummary(
        status="",
        sample_count=0,
        max_abs_rt_delta_sec=None,
        overwide_boundary_count=0,
        narrower_boundary_count=0,
    )


def _empty_target_rt_trend_summary() -> _TargetRtTrendSummary:
    return _TargetRtTrendSummary(
        status="",
        local_abs_delta_p95_min=None,
        local_moderate_or_severe_count=None,
        local_severe_count=None,
    )


def _summarize_evidence_spine(
    rows: Sequence[Mapping[str, str]],
    *,
    target_label: str,
    family_id: str,
    expected_sample_count: int,
    target_rt_trend: _TargetRtTrendSummary,
) -> _EvidenceSpineSummary:
    matched = [
        row
        for row in rows
        if row.get("target_label", "").strip() == target_label
        and row.get("untargeted_family_id", "").strip() == family_id
    ]
    if not matched or len(matched) < expected_sample_count:
        return _EvidenceSpineSummary(
            status="rt_boundary_evidence_missing",
            sample_count=len(matched),
            max_abs_rt_delta_sec=None,
            overwide_boundary_count=0,
            narrower_boundary_count=0,
        )

    rt_deltas_sec: list[float] = []
    overwide_count = 0
    narrower_count = 0
    for row in matched:
        rt_deltas_sec.append(abs(_required_float(row, "rt_delta_min")) * 60.0)
        start_delta = _required_float(row, "boundary_delta_start_min")
        end_delta = _required_float(row, "boundary_delta_end_min")
        if (
            start_delta < -_RT_BOUNDARY_OVERWIDE_TOLERANCE_MIN
            or end_delta > _RT_BOUNDARY_OVERWIDE_TOLERANCE_MIN
        ):
            overwide_count += 1
        if (
            start_delta > _RT_BOUNDARY_OVERWIDE_TOLERANCE_MIN
            or end_delta < -_RT_BOUNDARY_OVERWIDE_TOLERANCE_MIN
        ):
            narrower_count += 1

    max_abs_rt_delta_sec = max(rt_deltas_sec)
    if max_abs_rt_delta_sec > _RT_BOUNDARY_MAX_RT_DELTA_SEC:
        if _target_rt_trend_supports_large_rt_delta(target_rt_trend):
            status = "rt_boundary_rt_delta_explained_by_target_trend"
        else:
            status = "rt_boundary_rt_delta_exceeds_0.5_sec"
    elif overwide_count:
        status = "rt_boundary_alignment_overwide"
    else:
        status = "rt_boundary_supported"
    return _EvidenceSpineSummary(
        status=status,
        sample_count=len(matched),
        max_abs_rt_delta_sec=max_abs_rt_delta_sec,
        overwide_boundary_count=overwide_count,
        narrower_boundary_count=narrower_count,
    )


def _read_target_rt_trend(path: Path) -> dict[str, _TargetRtTrendSummary]:
    rows = _read_tsv(path, _TARGET_RT_TREND_REQUIRED_COLUMNS)
    return {
        row["target_label"].strip(): _target_rt_trend_summary(row)
        for row in rows
        if row.get("target_label", "").strip()
    }


def _target_rt_trend_summary(row: Mapping[str, str]) -> _TargetRtTrendSummary:
    local_p95 = _optional_float(row.get("local_abs_delta_p95_min"))
    moderate_or_severe = _parse_optional_non_negative_int(
        row.get("local_moderate_or_severe_count"),
        "local_moderate_or_severe_count",
    )
    severe = _parse_optional_non_negative_int(
        row.get("local_severe_count"),
        "local_severe_count",
    )
    status = (
        "locally_coherent"
        if (
            local_p95 is not None
            and local_p95 <= _TARGET_RT_TREND_LOCAL_P95_MAX_MIN
            and moderate_or_severe == 0
            and severe == 0
        )
        else "not_locally_coherent"
    )
    return _TargetRtTrendSummary(
        status=status,
        local_abs_delta_p95_min=local_p95,
        local_moderate_or_severe_count=moderate_or_severe,
        local_severe_count=severe,
    )


def _target_rt_trend_supports_large_rt_delta(
    summary: _TargetRtTrendSummary,
) -> bool:
    return summary.status == "locally_coherent"


def _write_outputs(
    outputs: P2bAslsPromotionGateOutputs,
    result: P2bAslsPromotionGateResult,
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


def _row_dict(row: P2bAslsPromotionGateRow) -> dict[str, object]:
    return {
        **asdict(row),
        "old_failure_reasons": ";".join(row.old_failure_reasons),
        "hard_blockers": ";".join(row.hard_blockers),
        "accepted_reasons": ";".join(row.accepted_reasons),
    }


def _summary_dict(result: P2bAslsPromotionGateResult) -> dict[str, object]:
    return {
        "overall_status": result.overall_status,
        "target_count": result.target_count,
        "hard_blocker_count": result.hard_blocker_count,
        "review_accepted_count": result.review_accepted_count,
        "global_blockers": ";".join(result.global_blockers),
        "area_uncertainty_unexplained_area_mismatch_count": (
            result.area_uncertainty_unexplained_area_mismatch_count
        ),
        "area_uncertainty_integration_context_incomplete_count": (
            result.area_uncertainty_integration_context_incomplete_count
        ),
    }


def _write_markdown(path: Path, result: P2bAslsPromotionGateResult) -> None:
    lines = [
        "# P2b Revised AsLS Promotion Gate",
        "",
        f"Overall status: {result.overall_status}",
        f"Hard blockers: {result.hard_blocker_count}",
        f"Accepted review rows: {result.review_accepted_count}",
        f"Global blockers: {';'.join(result.global_blockers)}",
        "",
        "| Target | Feature | Old status | Revised status | Hard blockers | "
        "Accepted reasons |",
        "|---|---|---|---|---|---|",
    ]
    for row in result.rows:
        lines.append(
            "| "
            f"{row.target_label} | "
            f"{row.selected_feature_id} | "
            f"{row.old_status} | "
            f"{row.revised_status} | "
            f"{';'.join(row.hard_blockers)} | "
            f"{';'.join(row.accepted_reasons)} |"
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
            writer.writerow(
                {field: _format_value(row.get(field)) for field in fieldnames}
            )


def _read_tsv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or ())
        missing = sorted(required_columns - columns)
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def _single_row(rows: Sequence[Mapping[str, str]], path: Path) -> Mapping[str, str]:
    if len(rows) != 1:
        raise ValueError(f"{path}: expected exactly one summary row, found {len(rows)}")
    return rows[0]


def _split_reasons(value: object) -> tuple[str, ...]:
    return tuple(part.strip() for part in str(value or "").split(";") if part.strip())


def _optional_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"non-numeric numeric field value: {text}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite numeric field value: {text}")
    return parsed


def _required_float(row: Mapping[str, str], field_name: str) -> float:
    parsed = _optional_float(row.get(field_name))
    if parsed is None:
        raise ValueError(f"{field_name} is required")
    return parsed


def _parse_non_negative_int(value: object, field_name: str) -> int:
    text = str(value or "").strip()
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer: {text}") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return parsed


def _parse_optional_non_negative_int(value: object, field_name: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _parse_non_negative_int(text, field_name)


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
