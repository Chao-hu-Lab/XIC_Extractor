from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

GATE_VERSION = "chrom_peak_segment_candidate_gate_v1"
CHROM_SOURCE = "chrom_peak_segment"
KEY_FIELDS = ("sample_name", "target_label", "role")
_CHANGED_ROW_FIELDS = [
    "sample_name",
    "target_label",
    "role",
    "old_proposal_sources",
    "new_proposal_sources",
    "old_area_raw_counts_seconds",
    "new_area_raw_counts_seconds",
    "delta_ratio",
    "old_rt_left_min",
    "old_rt_right_min",
    "new_rt_left_min",
    "new_rt_right_min",
    "new_confidence",
]
_REVIEW_ROW_FIELDS = [
    "sample_name",
    "target_label",
    "role",
    "review_reason",
    "manual_presence_verdict",
    "manual_review_basis",
    "manual_product_action",
    "manual_review_note",
    "proposal_sources",
    "confidence",
    "reason",
    "concern_labels",
    "cap_labels",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "area_raw_counts_seconds",
    "delta_ratio",
    "selected_envelope_decision",
    "selected_envelope_boundary_class",
    "selected_envelope_stop_reason",
]


def build_gate_report(
    peak_candidate_rows: Sequence[dict[str, str]],
    *,
    baseline_peak_candidate_rows: Sequence[dict[str, str]] = (),
    selected_envelope_rows: Sequence[dict[str, str]] = (),
    manual_presence_review_rows: Sequence[dict[str, str]] = (),
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    selected_rows = [row for row in peak_candidate_rows if _is_selected(row)]
    chrom_rows = [row for row in peak_candidate_rows if _has_chrom_source(row)]
    selected_chrom_rows = [
        row for row in selected_rows if _has_chrom_source(row)
    ]
    selected_chrom_review_only = [
        row for row in selected_chrom_rows if _is_review_only(row)
    ]
    selected_envelope_externalized = [
        row
        for row in selected_envelope_rows
        if row.get("row_boundary_decision", "") == "externalize"
    ]

    selected_envelope_by_key = {
        _row_key(row): row
        for row in selected_envelope_rows
        if _row_key(row)
    }
    changed_rows = _selected_area_changes(
        selected_rows,
        baseline_peak_candidate_rows,
    )
    changed_rows_by_key = {
        _row_key(row): row
        for row in changed_rows
        if _row_key(row)
    }
    manual_presence_review_by_key = {
        _row_key(row): row
        for row in manual_presence_review_rows
        if _row_key(row)
    }
    review_rows = _selected_chrom_review_rows(
        selected_chrom_review_only,
        selected_envelope_by_key=selected_envelope_by_key,
        changed_rows_by_key=changed_rows_by_key,
        manual_presence_review_by_key=manual_presence_review_by_key,
    )

    boundary_blocking_reasons: list[str] = []
    presence_blocking_reasons: list[str] = []
    advisory_reasons: list[str] = []
    if not baseline_peak_candidate_rows:
        boundary_blocking_reasons.append("missing_baseline_peak_candidates_tsv")
    if any(float(row["delta_ratio"]) < 0 for row in changed_rows):
        boundary_blocking_reasons.append("selected_area_decrease_review_required")
    if selected_chrom_review_only:
        missing_manual_reviews = [
            row
            for row in selected_chrom_review_only
            if _row_key(row) not in manual_presence_review_by_key
        ]
        if manual_presence_review_rows and missing_manual_reviews:
            presence_blocking_reasons.append(
                "manual_presence_review_missing_rows"
            )
        elif not manual_presence_review_rows:
            presence_blocking_reasons.append(
                "selected_chrom_review_only_rows_require_presence_review"
            )
        if _manual_presence_review_verdict_count(
            manual_presence_review_rows,
            {"blocked", "false_pick"},
        ):
            presence_blocking_reasons.append("manual_presence_review_blocked_rows")
        if _manual_presence_review_verdict_count(
            manual_presence_review_rows,
            {"expected_peak_change"},
        ):
            presence_blocking_reasons.append(
                "manual_presence_review_expected_peak_change_rows"
            )
        if _manual_presence_review_verdict_count(
            manual_presence_review_rows,
            {"inconclusive", "needs_followup"},
        ):
            presence_blocking_reasons.append(
                "manual_presence_review_inconclusive_rows"
            )
    if selected_envelope_externalized:
        advisory_reasons.append(
            "selected_envelope_gate_stale_for_segment_candidates"
        )
    if selected_chrom_rows and not changed_rows:
        advisory_reasons.append("segment_candidates_selected_without_area_delta")
    if not selected_chrom_rows:
        boundary_blocking_reasons.append("no_selected_chrom_peak_segment_rows")

    blocking_reasons = [
        *boundary_blocking_reasons,
        *presence_blocking_reasons,
    ]

    manifest: dict[str, Any] = {
        "gate_version": GATE_VERSION,
        "gate_decision": "defer" if blocking_reasons else "promote",
        "boundary_gate_decision": (
            "defer" if boundary_blocking_reasons else "promote"
        ),
        "presence_gate_decision": (
            "defer" if presence_blocking_reasons else "promote"
        ),
        "decision_reasons": [*blocking_reasons, *advisory_reasons],
        "blocking_reasons": blocking_reasons,
        "boundary_blocking_reasons": boundary_blocking_reasons,
        "presence_blocking_reasons": presence_blocking_reasons,
        "advisory_reasons": advisory_reasons,
        "row_count": len(peak_candidate_rows),
        "selected_count": len(selected_rows),
        "chrom_candidate_count": len(chrom_rows),
        "selected_chrom_count": len(selected_chrom_rows),
        "selected_nonchrom_count": len(selected_rows) - len(selected_chrom_rows),
        "selected_chrom_review_only_count": len(selected_chrom_review_only),
        "review_row_count": len(review_rows),
        "review_rows_by_reason": _counter_dict(
            row.get("review_reason", "") for row in review_rows
        ),
        "manual_presence_review_row_count": len(manual_presence_review_rows),
        "manual_presence_review_missing_count": (
            sum(
                1
                for row in selected_chrom_review_only
                if _row_key(row) not in manual_presence_review_by_key
            )
            if manual_presence_review_rows
            else len(selected_chrom_review_only)
        ),
        "manual_presence_review_by_verdict": _counter_dict(
            row.get("manual_presence_verdict", "")
            for row in manual_presence_review_rows
        ),
        "selected_chrom_by_role": _counter_dict(
            row.get("role", "") for row in selected_chrom_rows
        ),
        "selected_chrom_by_confidence": _counter_dict(
            row.get("confidence", "") for row in selected_chrom_rows
        ),
        "selected_chrom_by_sources": _counter_dict(
            row.get("proposal_sources", "") for row in selected_chrom_rows
        ),
        "selected_area_changed_count": len(changed_rows),
        "selected_area_increased_count": sum(
            1 for row in changed_rows if float(row["delta_ratio"]) > 0
        ),
        "selected_area_decreased_count": sum(
            1 for row in changed_rows if float(row["delta_ratio"]) < 0
        ),
        "max_selected_area_increase_ratio": _max_delta(changed_rows),
        "max_selected_area_decrease_ratio": _min_delta(changed_rows),
        "selected_envelope_row_count": len(selected_envelope_rows),
        "selected_envelope_externalize_count": len(selected_envelope_externalized),
        "selected_envelope_boundary_classes": _counter_dict(
            row.get("boundary_change_class", "") for row in selected_envelope_rows
        ),
    }
    return manifest, changed_rows, review_rows


def write_gate_outputs(
    manifest: dict[str, Any],
    changed_rows: Sequence[dict[str, str]],
    review_rows: Sequence[dict[str, str]],
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "chrom_peak_segment_gate_manifest.json"
    changed_rows_path = output_dir / "chrom_peak_segment_changed_rows.tsv"
    review_rows_path = output_dir / "chrom_peak_segment_review_rows.tsv"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_tsv(changed_rows_path, changed_rows, _CHANGED_ROW_FIELDS)
    _write_tsv(review_rows_path, review_rows, _REVIEW_ROW_FIELDS)
    return manifest_path, changed_rows_path, review_rows_path


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    rows = _read_tsv(args.peak_candidates_tsv)
    baseline_rows = (
        _read_tsv(args.baseline_peak_candidates_tsv)
        if args.baseline_peak_candidates_tsv is not None
        else []
    )
    selected_envelope_rows = (
        _read_tsv(args.selected_envelope_diagnostics_tsv)
        if args.selected_envelope_diagnostics_tsv is not None
        else []
    )
    manual_presence_review_rows = (
        _read_tsv(args.manual_presence_review_tsv)
        if args.manual_presence_review_tsv is not None
        else []
    )
    manifest, changed_rows, review_rows = build_gate_report(
        rows,
        baseline_peak_candidate_rows=baseline_rows,
        selected_envelope_rows=selected_envelope_rows,
        manual_presence_review_rows=manual_presence_review_rows,
    )
    manifest_path, changed_rows_path, review_rows_path = write_gate_outputs(
        manifest,
        changed_rows,
        review_rows,
        args.output_dir,
    )
    print(f"Gate manifest: {manifest_path}")
    print(f"Changed rows TSV: {changed_rows_path}")
    print(f"Review rows TSV: {review_rows_path}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--baseline-peak-candidates-tsv", type=Path)
    parser.add_argument("--selected-envelope-diagnostics-tsv", type=Path)
    parser.add_argument("--manual-presence-review-tsv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def _selected_area_changes(
    selected_rows: Sequence[dict[str, str]],
    baseline_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    baseline_map = {
        _row_key(row): row
        for row in baseline_rows
        if _is_selected(row) and _row_key(row)
    }
    changes: list[dict[str, str]] = []
    for row in selected_rows:
        key = _row_key(row)
        if not key or key not in baseline_map:
            continue
        baseline = baseline_map[key]
        old_area = _float(baseline.get("area_raw_counts_seconds", ""))
        new_area = _float(row.get("area_raw_counts_seconds", ""))
        if old_area <= 0:
            continue
        delta_ratio = (new_area - old_area) / old_area
        if abs(delta_ratio) <= 1e-9:
            continue
        changes.append(
            {
                "sample_name": row.get("sample_name", ""),
                "target_label": row.get("target_label", ""),
                "role": row.get("role", ""),
                "old_proposal_sources": baseline.get("proposal_sources", ""),
                "new_proposal_sources": row.get("proposal_sources", ""),
                "old_area_raw_counts_seconds": _format_float(old_area),
                "new_area_raw_counts_seconds": _format_float(new_area),
                "delta_ratio": _format_float(delta_ratio),
                "old_rt_left_min": baseline.get("rt_left_min", ""),
                "old_rt_right_min": baseline.get("rt_right_min", ""),
                "new_rt_left_min": row.get("rt_left_min", ""),
                "new_rt_right_min": row.get("rt_right_min", ""),
                "new_confidence": row.get("confidence", ""),
            }
        )
    return changes


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _selected_chrom_review_rows(
    selected_chrom_review_only: Sequence[dict[str, str]],
    *,
    selected_envelope_by_key: dict[tuple[str, str, str] | None, dict[str, str]],
    changed_rows_by_key: dict[tuple[str, str, str] | None, dict[str, str]],
    manual_presence_review_by_key: dict[
        tuple[str, str, str] | None,
        dict[str, str],
    ],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in selected_chrom_review_only:
        key = _row_key(row)
        selected_envelope = selected_envelope_by_key.get(key, {})
        changed = changed_rows_by_key.get(key, {})
        manual_review = manual_presence_review_by_key.get(key, {})
        rows.append(
            {
                "sample_name": row.get("sample_name", ""),
                "target_label": row.get("target_label", ""),
                "role": row.get("role", ""),
                "review_reason": "selected_chrom_review_only",
                "manual_presence_verdict": manual_review.get(
                    "manual_presence_verdict",
                    "",
                ),
                "manual_review_basis": manual_review.get("manual_review_basis", ""),
                "manual_product_action": manual_review.get(
                    "manual_product_action",
                    "",
                ),
                "manual_review_note": manual_review.get("manual_review_note", ""),
                "proposal_sources": row.get("proposal_sources", ""),
                "confidence": row.get("confidence", ""),
                "reason": row.get("reason", ""),
                "concern_labels": row.get("concern_labels", ""),
                "cap_labels": row.get("cap_labels", ""),
                "rt_left_min": row.get("rt_left_min", ""),
                "rt_apex_min": row.get("rt_apex_min", ""),
                "rt_right_min": row.get("rt_right_min", ""),
                "area_raw_counts_seconds": row.get("area_raw_counts_seconds", ""),
                "delta_ratio": changed.get("delta_ratio", ""),
                "selected_envelope_decision": selected_envelope.get(
                    "row_boundary_decision",
                    "",
                ),
                "selected_envelope_boundary_class": selected_envelope.get(
                    "boundary_change_class",
                    "",
                ),
                "selected_envelope_stop_reason": selected_envelope.get(
                    "boundary_stop_reason",
                    "",
                ),
            }
        )
    return rows


def _write_tsv(
    path: Path,
    rows: Sequence[dict[str, str]],
    fieldnames: Sequence[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _row_key(row: dict[str, str]) -> tuple[str, str, str] | None:
    values = (
        row.get(KEY_FIELDS[0], ""),
        row.get(KEY_FIELDS[1], ""),
        row.get(KEY_FIELDS[2], ""),
    )
    if not all(values):
        return None
    return values


def _is_selected(row: dict[str, str]) -> bool:
    return row.get("selected", "").upper() == "TRUE"


def _has_chrom_source(row: dict[str, str]) -> bool:
    return CHROM_SOURCE in _split_labels(row.get("proposal_sources", ""))


def _is_review_only(row: dict[str, str]) -> bool:
    confidence = row.get("confidence", "").upper()
    reason = row.get("reason", "").lower()
    return confidence == "VERY_LOW" or "review only" in reason


def _split_labels(value: str) -> set[str]:
    return {
        label.strip()
        for label in value.split(";")
        if label.strip()
    }


def _counter_dict(values: Sequence[str] | Any) -> dict[str, int]:
    return dict(sorted(Counter(value for value in values if value).items()))


def _manual_presence_review_verdict_count(
    rows: Sequence[dict[str, str]],
    verdicts: set[str],
) -> int:
    return sum(
        1
        for row in rows
        if row.get("manual_presence_verdict", "").strip() in verdicts
    )


def _float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_float(value: float) -> str:
    return f"{value:.6g}"


def _max_delta(rows: Sequence[dict[str, str]]) -> float | None:
    deltas = [float(row["delta_ratio"]) for row in rows]
    positive = [value for value in deltas if value > 0]
    return max(positive) if positive else None


def _min_delta(rows: Sequence[dict[str, str]]) -> float | None:
    deltas = [float(row["delta_ratio"]) for row in rows]
    negative = [value for value in deltas if value < 0]
    return min(negative) if negative else None


if __name__ == "__main__":
    raise SystemExit(main())
