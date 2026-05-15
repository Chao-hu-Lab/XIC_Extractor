"""Render a static HTML decision report from alignment diagnostic artifacts."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REVIEW_REQUIRED_COLUMNS = (
    "feature_family_id",
    "identity_decision",
    "include_in_primary_matrix",
    "present_rate",
    "detected_count",
    "accepted_rescue_count",
    "row_flags",
)
_MATRIX_REQUIRED_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
)
_MATRIX_METADATA_COLUMNS = frozenset(_MATRIX_REQUIRED_COLUMNS)
_CLEANLINESS_WARNING_FLAGS = (
    "duplicate_claim_pressure",
    "high_backfill_dependency",
    "rescue_heavy",
)


@dataclass(frozen=True)
class TsvTable:
    fieldnames: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_report(
            alignment_dir=args.alignment_dir,
            targeted_istd_benchmark_json=args.targeted_istd_benchmark_json,
            owner_backfill_economics_json=args.owner_backfill_economics_json,
            timing_json=args.timing_json,
            known_istd_exceptions=tuple(args.known_istd_exception),
        )
        write_report(args.output_html, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Alignment decision report: {args.output_html}")
    print(f"Verdict: {report['verdict']}")
    return 0


def build_report(
    *,
    alignment_dir: Path,
    targeted_istd_benchmark_json: Path | None = None,
    owner_backfill_economics_json: Path | None = None,
    timing_json: Path | None = None,
    known_istd_exceptions: tuple[str, ...] = (),
) -> dict[str, Any]:
    review = _read_tsv(
        alignment_dir / "alignment_review.tsv",
        required_columns=_REVIEW_REQUIRED_COLUMNS,
    )
    matrix = _read_tsv(
        alignment_dir / "alignment_matrix.tsv",
        required_columns=_MATRIX_REQUIRED_COLUMNS,
    )
    known = _parse_known_istd_exceptions(known_istd_exceptions)
    cleanliness = _matrix_cleanliness(review, matrix)
    istd = _istd_benchmark(targeted_istd_benchmark_json, known)
    economics = _backfill_economics(owner_backfill_economics_json)
    timing = _timing_summary(timing_json)
    verdict = _verdict(
        istd=istd,
        cleanliness=cleanliness,
        economics=economics,
        timing=timing,
    )
    return {
        "alignment_dir": str(alignment_dir),
        "verdict": verdict,
        "run": {
            "matrix_row_count": len(matrix.rows),
            "sample_count": _sample_count(matrix.fieldnames),
            "identity_counts": cleanliness["identity_counts"],
            "istd_pass_count": istd["pass_count"],
            "istd_fail_count": istd["fail_count"],
            "istd_known_count": istd["known_count"],
            "runtime": timing["summary"],
        },
        "istd": istd,
        "cleanliness": cleanliness,
        "economics": economics,
        "timing": timing,
    }


def write_report(output_html: Path, report: Mapping[str, Any]) -> Path:
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(_render_html(report), encoding="utf-8")
    return output_html


def _verdict(
    *,
    istd: Mapping[str, Any],
    cleanliness: Mapping[str, Any],
    economics: Mapping[str, Any],
    timing: Mapping[str, Any],
) -> str:
    if istd["unhandled_failures"]:
        return "FAIL"
    if (
        not istd["provided"]
        or not economics["provided"]
        or not timing["provided"]
        or istd["known_count"]
        or cleanliness["warning_count"]
    ):
        return "WARN"
    return "PASS"


def _matrix_cleanliness(
    review: TsvTable,
    matrix: TsvTable,
) -> dict[str, Any]:
    identity_counts = Counter(
        row.get("identity_decision", "") or "unknown" for row in review.rows
    )
    primary_rows = [
        row for row in review.rows if _is_true(row["include_in_primary_matrix"])
    ]
    zero_present_rows = [row for row in primary_rows if _is_zero_present(row)]
    flag_counts: Counter[str] = Counter()
    warning_rows: list[dict[str, Any]] = []
    for row in primary_rows:
        flags = _split_list(row.get("row_flags", ""))
        flag_counts.update(flag for flag in flags if flag in _CLEANLINESS_WARNING_FLAGS)
        warning_flags = [flag for flag in flags if flag in _CLEANLINESS_WARNING_FLAGS]
        if _is_zero_present(row) or warning_flags:
            warning_rows.append(
                {
                    "feature_family_id": row["feature_family_id"],
                    "identity_decision": row.get("identity_decision", ""),
                    "present_rate": row.get("present_rate", ""),
                    "detected_count": row.get("detected_count", ""),
                    "accepted_rescue_count": row.get("accepted_rescue_count", ""),
                    "row_flags": row.get("row_flags", ""),
                    "warning": row.get("warning", ""),
                }
            )
    warning_rows.sort(
        key=lambda row: (
            -len(_split_list(str(row["row_flags"]))),
            _float_value(str(row["present_rate"]), default=math.inf),
            str(row["feature_family_id"]),
        )
    )
    return {
        "primary_row_count": len(matrix.rows),
        "review_primary_row_count": len(primary_rows),
        "identity_counts": dict(sorted(identity_counts.items())),
        "zero_present_row_count": len(zero_present_rows),
        "flag_counts": {
            flag: flag_counts.get(flag, 0)
            for flag in _CLEANLINESS_WARNING_FLAGS
        },
        "warning_count": len(zero_present_rows) + sum(flag_counts.values()),
        "top_warning_rows": warning_rows[:20],
    }


def _istd_benchmark(
    path: Path | None,
    known_exceptions: Mapping[str, set[str]],
) -> dict[str, Any]:
    if path is None:
        return _not_provided("ISTD benchmark JSON was not provided.")
    payload = _read_json(path)
    summaries = payload.get("summaries", ())
    if not isinstance(summaries, Sequence) or isinstance(summaries, (str, bytes)):
        raise ValueError(f"{path}: summaries must be a list")
    rows: list[dict[str, Any]] = []
    pass_count = 0
    known_count = 0
    unhandled: list[dict[str, Any]] = []
    for item in summaries:
        if not isinstance(item, Mapping):
            continue
        target = str(item.get("target_label", ""))
        status = str(item.get("status", "")).upper()
        active = _is_active(item)
        modes = _failure_modes(item.get("failure_modes", ()))
        known = active and status != "PASS" and _is_known_exception(
            target,
            modes,
            known_exceptions,
        )
        if active and status == "PASS":
            pass_count += 1
        elif known:
            known_count += 1
        elif active and status != "PASS":
            unhandled.append(
                {
                    "target_label": target,
                    "status": status,
                    "failure_modes": modes,
                }
            )
        rows.append(
            {
                "target_label": target,
                "status": status or "UNKNOWN",
                "active": active,
                "known": known,
                "selected_family": item.get("selected_feature_id", ""),
                "primary_hit_count": item.get("primary_match_count", ""),
                "rt_mean_delta": item.get("family_mean_rt_delta_min", ""),
                "rt_p95": item.get("sample_rt_p95_abs_delta_min", ""),
                "spearman": item.get("log_area_spearman", ""),
                "pearson": item.get("log_area_pearson", ""),
                "coverage": _coverage_text(item),
                "failure_modes": ";".join(modes),
            }
        )
    return {
        "provided": True,
        "source": str(path),
        "pass_count": pass_count,
        "known_count": known_count,
        "fail_count": len(unhandled),
        "unhandled_failures": unhandled,
        "rows": rows,
    }


def _backfill_economics(path: Path | None) -> dict[str, Any]:
    if path is None:
        return _not_provided("Owner-backfill economics JSON was not provided.")
    payload = _read_json(path)
    totals = payload.get("totals", {})
    summary = payload.get("summary", ())
    features = payload.get("features", ())
    if not isinstance(totals, Mapping):
        raise ValueError(f"{path}: totals must be an object")
    if not isinstance(summary, Sequence) or isinstance(summary, (str, bytes)):
        raise ValueError(f"{path}: summary must be a list")
    if not isinstance(features, Sequence) or isinstance(features, (str, bytes)):
        raise ValueError(f"{path}: features must be a list")
    return {
        "provided": True,
        "source": str(path),
        "totals": dict(totals),
        "summary": [dict(row) for row in summary if isinstance(row, Mapping)],
        "top_expensive_families": [
            dict(row) for row in features if isinstance(row, Mapping)
        ][:20],
    }


def _timing_summary(path: Path | None) -> dict[str, Any]:
    if path is None:
        return _not_provided("Timing JSON was not provided.")
    payload = _read_json(path)
    records = payload.get("records", ())
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ValueError(f"{path}: records must be a list")
    by_stage: Counter[str] = Counter()
    for item in records:
        if not isinstance(item, Mapping):
            continue
        stage = str(item.get("stage", "unknown"))
        by_stage[stage] += _float_value(item.get("elapsed_sec", ""), default=0.0)
    top_stages = [
        {"stage": stage, "elapsed_sec": elapsed}
        for stage, elapsed in by_stage.most_common(10)
    ]
    total = sum(by_stage.values())
    return {
        "provided": True,
        "source": str(path),
        "summary": {
            "pipeline": payload.get("pipeline", ""),
            "run_id": payload.get("run_id", ""),
            "total_elapsed_sec": total,
            "top_stages": top_stages,
        },
    }


def _render_html(report: Mapping[str, Any]) -> str:
    verdict = str(report["verdict"])
    title = "Alignment Decision Report"
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            "<title>Alignment Decision Report</title>",
            "<style>",
            _css(),
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            f"<h1>{_h(title)}</h1>",
            (
                f'<div class="verdict verdict-{_h(verdict.lower())}">'
                f"Run Verdict: {_h(verdict)}</div>"
            ),
            _run_verdict_section(report),
            _istd_section(report["istd"]),
            _cleanliness_section(report["cleanliness"]),
            _economics_section(report["economics"]),
            "</main>",
            "</body>",
            "</html>",
        )
    )


def _run_verdict_section(report: Mapping[str, Any]) -> str:
    run = report["run"]
    identity = run["identity_counts"]
    runtime = run["runtime"]
    top_stage_rows = [
        (
            row.get("stage", ""),
            _fmt(row.get("elapsed_sec", "")),
        )
        for row in runtime.get("top_stages", ())
        if isinstance(row, Mapping)
    ]
    runtime_table = ""
    if top_stage_rows:
        runtime_table = "<h3>Runtime Stages</h3>" + _table(
            ("Stage", "Elapsed Sec"),
            top_stage_rows,
        )
    return _section(
        "Run Verdict",
        _metric_grid(
            (
                ("Verdict", report["verdict"]),
                ("Alignment Dir", report["alignment_dir"]),
                ("Matrix Rows", run["matrix_row_count"]),
                ("Samples", run["sample_count"]),
                ("production_family", identity.get("production_family", 0)),
                ("provisional_discovery", identity.get("provisional_discovery", 0)),
                ("audit_family", identity.get("audit_family", 0)),
                ("ISTD Pass", run["istd_pass_count"]),
                ("ISTD Known", run["istd_known_count"]),
                ("ISTD Fail", run["istd_fail_count"]),
                ("Runtime", _runtime_text(runtime)),
            )
        )
        + runtime_table,
    )


def _istd_section(istd: Mapping[str, Any]) -> str:
    if not istd["provided"]:
        return _section("ISTD Benchmark", _not_provided_html(istd["reason"]))
    headers = (
        "Target",
        "Status",
        "Known",
        "Selected Family",
        "Primary Hits",
        "RT Mean Delta",
        "RT p95",
        "Spearman",
        "Pearson",
        "Coverage",
        "Failure Modes",
    )
    rows = [
        (
            row["target_label"],
            row["status"],
            "KNOWN" if row["known"] else "",
            row["selected_family"],
            row["primary_hit_count"],
            _fmt(row["rt_mean_delta"]),
            _fmt(row["rt_p95"]),
            _fmt(row["spearman"]),
            _fmt(row["pearson"]),
            row["coverage"],
            row["failure_modes"],
        )
        for row in istd["rows"]
    ]
    return _section("ISTD Benchmark", _table(headers, rows))


def _cleanliness_section(cleanliness: Mapping[str, Any]) -> str:
    flags = cleanliness["flag_counts"]
    metrics = _metric_grid(
        (
            ("Primary Rows", cleanliness["primary_row_count"]),
            ("Review Primary Rows", cleanliness["review_primary_row_count"]),
            ("Zero-present Rows", cleanliness["zero_present_row_count"]),
            ("duplicate_claim_pressure", flags["duplicate_claim_pressure"]),
            ("high_backfill_dependency", flags["high_backfill_dependency"]),
            ("rescue_heavy", flags["rescue_heavy"]),
        )
    )
    rows = [
        (
            row["feature_family_id"],
            row["identity_decision"],
            row["present_rate"],
            row["detected_count"],
            row["accepted_rescue_count"],
            row["row_flags"],
            row["warning"],
        )
        for row in cleanliness["top_warning_rows"]
    ]
    table = _table(
        (
            "Feature",
            "Identity",
            "Present Rate",
            "Detected",
            "Accepted Rescue",
            "Flags",
            "Warning",
        ),
        rows,
        empty="No primary cleanliness warnings.",
    )
    return _section("Matrix Cleanliness", metrics + table)


def _economics_section(economics: Mapping[str, Any]) -> str:
    if not economics["provided"]:
        return _section("Backfill Economics", _not_provided_html(economics["reason"]))
    totals = economics["totals"]
    metrics = _metric_grid(
        (
            ("Request Targets", totals.get("request_target_count", 0)),
            ("Extract Estimate", totals.get("request_extract_count_estimate", 0)),
            (
                "Production Requests",
                totals.get("production_request_target_count", 0),
            ),
            ("Non-primary Requests", totals.get("non_primary_request_target_count", 0)),
            ("Rescued Targets", totals.get("rescued_target_count", 0)),
            ("Absent Targets", totals.get("absent_target_count", 0)),
            ("Duplicate Targets", totals.get("duplicate_assigned_target_count", 0)),
        )
    )
    summary_rows = [
        (
            row.get("identity_decision", ""),
            row.get("neutral_loss_tag", ""),
            row.get("include_in_primary_matrix", ""),
            row.get("eligible_group_family_count", ""),
            row.get("request_target_count", ""),
            row.get("request_extract_count_estimate", ""),
            row.get("rescued_target_count", ""),
            row.get("absent_target_count", ""),
            row.get("duplicate_assigned_target_count", ""),
        )
        for row in economics["summary"]
    ]
    feature_rows = [
        (
            row.get("feature_family_id", ""),
            row.get("neutral_loss_tag", ""),
            row.get("identity_decision", ""),
            row.get("include_in_primary_matrix", ""),
            row.get("request_target_count", ""),
            row.get("request_extract_count_estimate", ""),
            row.get("rescued_target_count", ""),
            row.get("absent_target_count", ""),
            row.get("duplicate_assigned_target_count", ""),
            row.get("row_flags", ""),
        )
        for row in economics["top_expensive_families"]
    ]
    return _section(
        "Backfill Economics",
        metrics
        + "<h3>By Identity / Tag</h3>"
        + _table(
            (
                "Identity",
                "Tag",
                "Primary",
                "Families",
                "Targets",
                "Extracts",
                "Rescued",
                "Absent",
                "Duplicate",
            ),
            summary_rows,
            empty="No eligible backfill requests.",
        )
        + "<h3>Top Expensive Families</h3>"
        + _table(
            (
                "Feature",
                "Tag",
                "Identity",
                "Primary",
                "Targets",
                "Extracts",
                "Rescued",
                "Absent",
                "Duplicate",
                "Flags",
            ),
            feature_rows,
            empty="No feature-level economics rows.",
        ),
    )


def _section(title: str, body: str) -> str:
    return f"<section><h2>{_h(title)}</h2>{body}</section>"


def _metric_grid(items: Sequence[tuple[str, Any]]) -> str:
    body = "".join(
        f"<div><dt>{_h(label)}</dt><dd>{_h(_fmt(value))}</dd></div>"
        for label, value in items
    )
    return f'<dl class="metrics">{body}</dl>'


def _table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    empty: str = "No rows.",
) -> str:
    if not rows:
        return f'<p class="muted">{_h(empty)}</p>'
    head = "".join(f"<th>{_h(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_h(_fmt(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _not_provided_html(reason: str) -> str:
    return f'<p class="not-provided">Not provided: {_h(reason)}</p>'


def _not_provided(reason: str) -> dict[str, Any]:
    return {
        "provided": False,
        "reason": reason,
        "pass_count": 0,
        "known_count": 0,
        "fail_count": 0,
        "unhandled_failures": [],
        "rows": [],
        "summary": {},
        "totals": {},
        "top_expensive_families": [],
    }


def _runtime_text(runtime: Mapping[str, Any]) -> str:
    if not runtime:
        return "Not provided"
    total = _float_value(runtime.get("total_elapsed_sec", ""), default=0.0)
    pipeline = runtime.get("pipeline", "")
    if total <= 0:
        return str(pipeline or "Provided")
    return f"{pipeline} {_fmt(total)} sec".strip()


def _coverage_text(row: Mapping[str, Any]) -> str:
    observed = row.get("untargeted_positive_count", "")
    minimum = row.get("coverage_minimum", "")
    targeted = row.get("targeted_positive_count", "")
    return f"{observed}/{targeted} (min {minimum})"


def _sample_count(fieldnames: Sequence[str]) -> int:
    return sum(1 for field in fieldnames if field not in _MATRIX_METADATA_COLUMNS)


def _is_zero_present(row: Mapping[str, str]) -> bool:
    return (
        _float_value(row.get("present_rate", ""), default=0.0) == 0.0
        and _int_value(row.get("detected_count", "")) == 0
        and _int_value(row.get("accepted_rescue_count", "")) == 0
    )


def _is_active(row: Mapping[str, Any]) -> bool:
    value = row.get("active_tag")
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return _is_true(str(value))


def _is_known_exception(
    target: str,
    modes: tuple[str, ...],
    known_exceptions: Mapping[str, set[str]],
) -> bool:
    if not modes:
        return False
    return all(mode in known_exceptions.get(target, set()) for mode in modes)


def _parse_known_istd_exceptions(values: tuple[str, ...]) -> dict[str, set[str]]:
    known: dict[str, set[str]] = {}
    for value in values:
        if ":" not in value:
            raise ValueError(
                "--known-istd-exception must use TARGET:FAILURE_MODE format"
            )
        target, mode = value.split(":", 1)
        target = target.strip()
        mode = mode.strip()
        if not target or not mode:
            raise ValueError(
                "--known-istd-exception must use TARGET:FAILURE_MODE format"
            )
        known.setdefault(target, set()).add(mode)
    return known


def _failure_modes(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part for part in _split_list(value) if part)
    if isinstance(value, Sequence):
        return tuple(str(part).strip() for part in value if str(part).strip())
    return ()


def _split_list(value: str) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part in value.replace(",", ";").split(";")
        if part.strip()
    )


def _read_tsv(path: Path, *, required_columns: tuple[str, ...]) -> TsvTable:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = tuple(reader.fieldnames or ())
            missing = tuple(
                column for column in required_columns if column not in fieldnames
            )
            if missing:
                raise ValueError(
                    f"{path}: missing required columns: {', '.join(missing)}"
                )
            return TsvTable(
                fieldnames=fieldnames,
                rows=tuple(dict(row) for row in reader),
            )
    except OSError as exc:
        raise ValueError(f"{path}: could not read TSV: {exc}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return payload


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def _int_value(value: Any) -> int:
    try:
        return int(float(str(value)))
    except ValueError:
        return 0


def _float_value(value: Any, *, default: float) -> float:
    try:
        number = float(str(value))
    except ValueError:
        return default
    return number if math.isfinite(number) else default


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4g}"
    text = str(value)
    try:
        number = float(text)
    except ValueError:
        return text
    if math.isfinite(number) and any(ch in text for ch in ".eE"):
        return f"{number:.4g}"
    return text


def _h(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
:root {
  color-scheme: light;
  font-family: "Segoe UI", Arial, sans-serif;
  color: #1f2933;
  background: #f7f8fa;
}
body {
  margin: 0;
}
main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 28px 48px;
}
h1 {
  margin: 0 0 16px;
  font-size: 28px;
}
h2 {
  margin: 0 0 14px;
  font-size: 20px;
}
h3 {
  margin: 20px 0 8px;
  font-size: 15px;
}
section {
  background: #fff;
  border: 1px solid #d9dee7;
  border-radius: 8px;
  margin-top: 18px;
  padding: 18px;
}
.verdict {
  display: inline-block;
  border-radius: 6px;
  font-weight: 700;
  letter-spacing: 0;
  padding: 8px 12px;
}
.verdict-pass { background: #dcfce7; color: #14532d; }
.verdict-warn { background: #fef3c7; color: #78350f; }
.verdict-fail { background: #fee2e2; color: #7f1d1d; }
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin: 0;
}
.metrics div {
  border: 1px solid #e5e9f0;
  border-radius: 6px;
  padding: 10px;
  min-width: 0;
}
dt {
  color: #64748b;
  font-size: 12px;
  margin-bottom: 5px;
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-weight: 650;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th, td {
  border-bottom: 1px solid #e5e9f0;
  padding: 7px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
}
.muted, .not-provided {
  color: #64748b;
}
""".strip()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an HTML decision report from alignment diagnostics.",
    )
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-html", type=Path, required=True)
    parser.add_argument("--targeted-istd-benchmark-json", type=Path)
    parser.add_argument("--owner-backfill-economics-json", type=Path)
    parser.add_argument("--timing-json", type=Path)
    parser.add_argument(
        "--known-istd-exception",
        action="append",
        default=[],
        help="Known ISTD exception in TARGET:FAILURE_MODE format.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
