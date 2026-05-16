"""Targeted peak reliability audit for benchmark eligibility."""

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
from statistics import median
from typing import Literal

from openpyxl import load_workbook

ReliabilityState = Literal[
    "benchmark_eligible",
    "targeted_review",
    "targeted_negative",
]

ROWS_COLUMNS = (
    "sample_name",
    "target_label",
    "role",
    "rt",
    "area",
    "confidence",
    "nl",
    "prior_rt",
    "prior_source",
    "total_severity",
    "quality_flags",
    "reliability_state",
    "risk_reasons",
    "known_exception",
)

SUMMARY_COLUMNS = (
    "target_label",
    "role",
    "benchmark_eligible_count",
    "targeted_review_count",
    "targeted_negative_count",
    "top_risk_reasons",
    "known_exception",
)


@dataclass(frozen=True)
class TargetedReliabilityOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class TargetedReliabilityRow:
    sample_name: str
    target_label: str
    role: str
    rt: float | None
    area: float | None
    confidence: str
    nl: str
    prior_rt: float | None
    prior_source: str
    total_severity: int | None
    quality_flags: str
    reliability_state: ReliabilityState
    risk_reasons: tuple[str, ...]
    known_exception: str


@dataclass(frozen=True)
class TargetedReliabilitySummary:
    target_label: str
    role: str
    benchmark_eligible_count: int
    targeted_review_count: int
    targeted_negative_count: int
    top_risk_reasons: str
    known_exception: str


@dataclass(frozen=True)
class TargetedReliabilityResult:
    rows: tuple[TargetedReliabilityRow, ...]
    summaries: tuple[TargetedReliabilitySummary, ...]

    @property
    def benchmark_eligible_count(self) -> int:
        return sum(row.reliability_state == "benchmark_eligible" for row in self.rows)

    @property
    def targeted_review_count(self) -> int:
        return sum(row.reliability_state == "targeted_review" for row in self.rows)

    @property
    def targeted_negative_count(self) -> int:
        return sum(row.reliability_state == "targeted_negative" for row in self.rows)


@dataclass(frozen=True)
class _TargetedInputRow:
    sample_name: str
    target_label: str
    role: str
    rt: float | None
    area: float | None
    confidence: str
    nl: str


@dataclass(frozen=True)
class _ScoreBreakdown:
    prior_rt: float | None
    prior_source: str
    total_severity: int | None
    quality_flags: str


def run_targeted_peak_reliability_audit(
    *,
    targeted_workbook: Path,
    output_dir: Path,
    known_target_exceptions: Sequence[str] = (),
) -> tuple[TargetedReliabilityOutputs, TargetedReliabilityResult]:
    rows, score_by_key = _load_targeted_workbook(targeted_workbook)
    known = _parse_known_exceptions(known_target_exceptions)
    weak_area_keys = _weak_area_keys(rows)
    reliability_rows = tuple(
        _classify_row(
            row,
            score=score_by_key.get((row.sample_name, row.target_label)),
            known_exception=known.get(row.target_label, ""),
            weak_area=(row.sample_name, row.target_label) in weak_area_keys,
        )
        for row in rows
    )
    result = TargetedReliabilityResult(
        rows=reliability_rows,
        summaries=_summarize_rows(reliability_rows),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = TargetedReliabilityOutputs(
        summary_tsv=output_dir / "targeted_peak_reliability_summary.tsv",
        rows_tsv=output_dir / "targeted_peak_reliability_rows.tsv",
        json_path=output_dir / "targeted_peak_reliability.json",
        markdown_path=output_dir / "targeted_peak_reliability.md",
    )
    _write_outputs(outputs, result, known_target_exceptions=known)
    return outputs, result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, result = run_targeted_peak_reliability_audit(
            targeted_workbook=args.targeted_workbook.resolve(),
            output_dir=args.output_dir.resolve(),
            known_target_exceptions=tuple(args.known_target_exception),
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Reliability JSON: {outputs.json_path}")
    print(f"Reliability report: {outputs.markdown_path}")
    return 0 if result.targeted_review_count == 0 else 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit targeted peak reliability for benchmark eligibility.",
    )
    parser.add_argument("--targeted-workbook", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--known-target-exception",
        action="append",
        default=[],
        help="Known targeted-side exception in TARGET:FAILURE_MODE form.",
    )
    return parser.parse_args(argv)


def _load_targeted_workbook(
    path: Path,
) -> tuple[tuple[_TargetedInputRow, ...], dict[tuple[str, str], _ScoreBreakdown]]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = _read_xic_results(workbook["XIC Results"])
        score_by_key = (
            _read_score_breakdown(workbook["Score Breakdown"])
            if "Score Breakdown" in workbook.sheetnames
            else {}
        )
        return rows, score_by_key
    finally:
        workbook.close()


def _read_xic_results(sheet: object) -> tuple[_TargetedInputRow, ...]:
    iterator = sheet.iter_rows(values_only=True)
    header = next(iterator)
    cols = _required_indexes(
        header,
        (
            "SampleName",
            "Target",
            "Role",
            "RT",
            "Area",
            "NL",
            "Confidence",
        ),
        "XIC Results",
    )
    current_sample = ""
    rows: list[_TargetedInputRow] = []
    for row in iterator:
        raw_sample = row[cols["SampleName"]]
        if raw_sample not in (None, ""):
            current_sample = _text(raw_sample)
        if not current_sample:
            continue
        target_label = _text(row[cols["Target"]])
        if not target_label:
            continue
        rows.append(
            _TargetedInputRow(
                sample_name=current_sample,
                target_label=target_label,
                role=_text(row[cols["Role"]]),
                rt=_float_value(row[cols["RT"]]),
                area=_float_value(row[cols["Area"]]),
                confidence=_text(row[cols["Confidence"]]).upper(),
                nl=_text(row[cols["NL"]]).upper(),
            )
        )
    return tuple(rows)


def _read_score_breakdown(sheet: object) -> dict[tuple[str, str], _ScoreBreakdown]:
    iterator = sheet.iter_rows(values_only=True)
    header = next(iterator)
    cols = _required_indexes(
        header,
        (
            "SampleName",
            "Target",
            "Prior RT",
            "Prior Source",
            "Total Severity",
            "Quality Flags",
        ),
        "Score Breakdown",
    )
    scores: dict[tuple[str, str], _ScoreBreakdown] = {}
    for row in iterator:
        sample = _text(row[cols["SampleName"]])
        target = _text(row[cols["Target"]])
        if not sample or not target:
            continue
        scores[(sample, target)] = _ScoreBreakdown(
            prior_rt=_float_value(row[cols["Prior RT"]]),
            prior_source=_text(row[cols["Prior Source"]]),
            total_severity=_int_value(row[cols["Total Severity"]]),
            quality_flags=_text(row[cols["Quality Flags"]]),
        )
    return scores


def _classify_row(
    row: _TargetedInputRow,
    *,
    score: _ScoreBreakdown | None,
    known_exception: str,
    weak_area: bool,
) -> TargetedReliabilityRow:
    if row.rt is None or row.area is None or row.area <= 0:
        return TargetedReliabilityRow(
            sample_name=row.sample_name,
            target_label=row.target_label,
            role=row.role,
            rt=row.rt,
            area=row.area,
            confidence=row.confidence,
            nl=row.nl,
            prior_rt=score.prior_rt if score is not None else None,
            prior_source=score.prior_source if score is not None else "",
            total_severity=score.total_severity if score is not None else None,
            quality_flags=score.quality_flags if score is not None else "",
            reliability_state="targeted_negative",
            risk_reasons=("no_usable_peak",),
            known_exception=known_exception,
        )

    risk_reasons: list[str] = []
    if row.confidence in {"LOW", "VERY_LOW"}:
        risk_reasons.append("low_confidence")
    if _is_nl_fail(row.nl):
        risk_reasons.append("nl_fail")
    elif _is_no_ms2(row.nl):
        risk_reasons.append("no_ms2")
    if score is None:
        risk_reasons.append("score_breakdown_unavailable")
    elif score.quality_flags:
        risk_reasons.append("quality_flags")
    if weak_area:
        risk_reasons.append("weak_area_rank")

    blocking_reasons = tuple(
        reason for reason in risk_reasons if reason != "score_breakdown_unavailable"
    )
    state: ReliabilityState = (
        "targeted_review" if blocking_reasons else "benchmark_eligible"
    )
    return TargetedReliabilityRow(
        sample_name=row.sample_name,
        target_label=row.target_label,
        role=row.role,
        rt=row.rt,
        area=row.area,
        confidence=row.confidence,
        nl=row.nl,
        prior_rt=score.prior_rt if score is not None else None,
        prior_source=score.prior_source if score is not None else "",
        total_severity=score.total_severity if score is not None else None,
        quality_flags=score.quality_flags if score is not None else "",
        reliability_state=state,
        risk_reasons=tuple(dict.fromkeys(risk_reasons)),
        known_exception=known_exception,
    )


def _weak_area_keys(rows: Sequence[_TargetedInputRow]) -> frozenset[tuple[str, str]]:
    by_target: dict[str, list[_TargetedInputRow]] = defaultdict(list)
    for row in rows:
        if row.area is not None and row.area > 0:
            by_target[row.target_label].append(row)
    weak: set[tuple[str, str]] = set()
    for target_rows in by_target.values():
        if len(target_rows) < 3:
            continue
        target_median = median(float(row.area) for row in target_rows if row.area)
        if target_median <= 0:
            continue
        threshold = target_median * 0.05
        for row in target_rows:
            if row.area is not None and row.area < threshold:
                weak.add((row.sample_name, row.target_label))
    return frozenset(weak)


def _summarize_rows(
    rows: Sequence[TargetedReliabilityRow],
) -> tuple[TargetedReliabilitySummary, ...]:
    grouped: dict[str, list[TargetedReliabilityRow]] = defaultdict(list)
    for row in rows:
        grouped[row.target_label].append(row)
    summaries: list[TargetedReliabilitySummary] = []
    for target_label in sorted(grouped):
        target_rows = grouped[target_label]
        reasons = Counter(
            reason for row in target_rows for reason in row.risk_reasons
        )
        top_reasons = ";".join(
            reason for reason, _count in reasons.most_common(5)
        )
        known_exception = next(
            (row.known_exception for row in target_rows if row.known_exception),
            "",
        )
        summaries.append(
            TargetedReliabilitySummary(
                target_label=target_label,
                role=target_rows[0].role,
                benchmark_eligible_count=sum(
                    row.reliability_state == "benchmark_eligible"
                    for row in target_rows
                ),
                targeted_review_count=sum(
                    row.reliability_state == "targeted_review"
                    for row in target_rows
                ),
                targeted_negative_count=sum(
                    row.reliability_state == "targeted_negative"
                    for row in target_rows
                ),
                top_risk_reasons=top_reasons,
                known_exception=known_exception,
            )
        )
    return tuple(summaries)


def _write_outputs(
    outputs: TargetedReliabilityOutputs,
    result: TargetedReliabilityResult,
    *,
    known_target_exceptions: Mapping[str, str],
) -> None:
    _write_tsv(outputs.rows_tsv, ROWS_COLUMNS, _row_dicts(result.rows))
    _write_tsv(
        outputs.summary_tsv,
        SUMMARY_COLUMNS,
        _summary_dicts(result.summaries),
    )
    outputs.json_path.write_text(
        json.dumps(
            _json_payload(result, known_target_exceptions=known_target_exceptions),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _write_markdown(outputs.markdown_path, result)


def _row_dicts(
    rows: Sequence[TargetedReliabilityRow],
) -> list[dict[str, object]]:
    return [
        {
            **asdict(row),
            "risk_reasons": ";".join(row.risk_reasons),
        }
        for row in rows
    ]


def _summary_dicts(
    summaries: Sequence[TargetedReliabilitySummary],
) -> list[dict[str, object]]:
    return [asdict(summary) for summary in summaries]


def _json_payload(
    result: TargetedReliabilityResult,
    *,
    known_target_exceptions: Mapping[str, str],
) -> dict[str, object]:
    return {
        "overall_status": "WARN" if result.targeted_review_count else "PASS",
        "summary": {
            "benchmark_eligible_count": result.benchmark_eligible_count,
            "targeted_review_count": result.targeted_review_count,
            "targeted_negative_count": result.targeted_negative_count,
        },
        "known_target_exceptions": dict(known_target_exceptions),
        "rows": _row_dicts(result.rows),
        "summaries": _summary_dicts(result.summaries),
    }


def _write_markdown(path: Path, result: TargetedReliabilityResult) -> None:
    lines = [
        "# Targeted Peak Reliability Audit",
        "",
        f"Overall status: {'WARN' if result.targeted_review_count else 'PASS'}",
        "",
        (
            "| Target | Eligible | Review | Negative | Known exception | "
            "Top risk reasons |"
        ),
        "|---|---:|---:|---:|---|---|",
    ]
    for summary in result.summaries:
        lines.append(
            "| "
            f"{summary.target_label} | "
            f"{summary.benchmark_eligible_count} | "
            f"{summary.targeted_review_count} | "
            f"{summary.targeted_negative_count} | "
            f"{summary.known_exception} | "
            f"{summary.top_risk_reasons} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tsv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: _format_value(row.get(key, "")) for key in fieldnames}
            )


def _parse_known_exceptions(values: Sequence[str]) -> dict[str, str]:
    known: dict[str, str] = {}
    for value in values:
        if ":" not in value:
            raise ValueError(
                "--known-target-exception must use TARGET:FAILURE_MODE form"
            )
        target, mode = value.split(":", 1)
        target = target.strip()
        mode = mode.strip()
        if not target or not mode:
            raise ValueError(
                "--known-target-exception must use TARGET:FAILURE_MODE form"
            )
        known[target] = mode
    return known


def _is_nl_fail(value: str) -> bool:
    token = value.strip().upper()
    return token == "NL_FAIL" or "NL_FAIL" in token or token.startswith("✗")


def _is_no_ms2(value: str) -> bool:
    token = value.strip().upper().replace(" ", "_")
    return token == "NO_MS2" or "NO_MS2" in token


def _required_indexes(
    header: Sequence[object],
    required: Sequence[str],
    sheet_name: str,
) -> dict[str, int]:
    indexes = {str(value).strip(): index for index, value in enumerate(header) if value}
    missing = [field for field in required if field not in indexes]
    if missing:
        raise ValueError(f"{sheet_name} is missing required columns: {missing}")
    return {field: indexes[field] for field in required}


def _float_value(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _int_value(value: object) -> int | None:
    numeric = _float_value(value)
    if numeric is None:
        return None
    return int(numeric)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.6g}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
