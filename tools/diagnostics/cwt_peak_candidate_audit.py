from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

_CWT_SOURCE = "centwave_cwt"
_DEFAULT_NEAR_RT_WINDOW_MIN = 0.08

_REQUIRED_COLUMNS = (
    "sample_name",
    "target_label",
    "resolver_mode",
    "candidate_id",
    "proposal_sources",
    "rt_apex_min",
    "selected",
    "confidence",
    "raw_score",
    "reason",
)

_SUMMARY_COLUMNS = (
    "candidate_row_count",
    "candidate_group_count",
    "cwt_row_count",
    "cwt_only_row_count",
    "selected_cwt_agreed_group_count",
    "selected_cwt_nearby_group_count",
    "selected_cwt_disagreed_group_count",
    "selected_without_cwt_group_count",
)

_GROUP_COLUMNS = (
    "group_id",
    "sample_name",
    "target_label",
    "resolver_mode",
    "cwt_agreement_class",
    "candidate_count",
    "cwt_row_count",
    "cwt_only_row_count",
    "selected_candidate_id",
    "selected_rt_apex_min",
    "selected_proposal_sources",
    "nearest_cwt_candidate_id",
    "nearest_cwt_rt_apex_min",
    "nearest_cwt_delta_min",
    "selected_confidence",
    "selected_raw_score",
    "selected_reason",
)

_CWT_ONLY_COLUMNS = (
    "group_id",
    "sample_name",
    "target_label",
    "resolver_mode",
    "candidate_id",
    "rt_apex_min",
    "confidence",
    "raw_score",
    "reason",
)


@dataclass(frozen=True)
class CwtCandidateRow:
    sample_name: str
    target_label: str
    resolver_mode: str
    candidate_id: str
    proposal_sources: str
    rt_apex_min: float
    selected: bool
    confidence: str
    raw_score: str
    reason: str

    @property
    def group_id(self) -> str:
        return "|".join((self.sample_name, self.target_label, self.resolver_mode))

    @property
    def source_set(self) -> frozenset[str]:
        return frozenset(
            source.strip()
            for source in self.proposal_sources.split(";")
            if source.strip()
        )

    @property
    def has_cwt(self) -> bool:
        return _CWT_SOURCE in self.source_set

    @property
    def cwt_only(self) -> bool:
        return self.source_set == frozenset({_CWT_SOURCE})


@dataclass(frozen=True)
class CwtGroupAuditRow:
    group_id: str
    sample_name: str
    target_label: str
    resolver_mode: str
    cwt_agreement_class: str
    candidate_count: int
    cwt_row_count: int
    cwt_only_row_count: int
    selected_candidate_id: str
    selected_rt_apex_min: float | None
    selected_proposal_sources: str
    nearest_cwt_candidate_id: str
    nearest_cwt_rt_apex_min: float | None
    nearest_cwt_delta_min: float | None
    selected_confidence: str
    selected_raw_score: str
    selected_reason: str


@dataclass(frozen=True)
class CwtOnlyAuditRow:
    group_id: str
    sample_name: str
    target_label: str
    resolver_mode: str
    candidate_id: str
    rt_apex_min: float
    confidence: str
    raw_score: str
    reason: str


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = _read_peak_candidates(args.peak_candidates_tsv)
        groups = _audit_groups(rows, near_rt_window_min=args.near_rt_window_min)
        cwt_only_rows = _cwt_only_rows(rows)
        payload = {
            "summary": _summary(rows, groups, cwt_only_rows),
            "groups": [asdict(row) for row in groups],
            "cwt_only_rows": [asdict(row) for row in cwt_only_rows],
        }
        _write_outputs(args.output_dir, payload, groups, cwt_only_rows)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"CWT audit JSON: {args.output_dir / 'cwt_peak_candidate_audit.json'}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit CWT peak candidate agreement from peak_candidates.tsv.",
    )
    parser.add_argument("--peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--near-rt-window-min",
        type=float,
        default=_DEFAULT_NEAR_RT_WINDOW_MIN,
        help=(
            "Classify selected candidates as selected_cwt_nearby when the "
            "nearest CWT proposal is within this RT window."
        ),
    )
    return parser.parse_args(argv)


def _read_peak_candidates(path: Path) -> tuple[CwtCandidateRow, ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in _REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return tuple(
            _row_from_dict(path, index, row)
            for index, row in enumerate(reader, 2)
        )


def _row_from_dict(
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> CwtCandidateRow:
    return CwtCandidateRow(
        sample_name=row["sample_name"],
        target_label=row["target_label"],
        resolver_mode=row["resolver_mode"],
        candidate_id=row["candidate_id"],
        proposal_sources=row["proposal_sources"],
        rt_apex_min=_float_value(path, row_number, "rt_apex_min", row["rt_apex_min"]),
        selected=row["selected"].strip().upper() == "TRUE",
        confidence=row["confidence"],
        raw_score=row["raw_score"],
        reason=row["reason"],
    )


def _audit_groups(
    rows: tuple[CwtCandidateRow, ...],
    *,
    near_rt_window_min: float,
) -> tuple[CwtGroupAuditRow, ...]:
    grouped: dict[str, list[CwtCandidateRow]] = {}
    for row in rows:
        grouped.setdefault(row.group_id, []).append(row)
    return tuple(
        _audit_group(group_rows, near_rt_window_min=near_rt_window_min)
        for _, group_rows in sorted(grouped.items(), key=lambda item: item[0])
    )


def _audit_group(
    rows: list[CwtCandidateRow],
    *,
    near_rt_window_min: float,
) -> CwtGroupAuditRow:
    first = rows[0]
    selected = next((row for row in rows if row.selected), None)
    cwt_rows = [row for row in rows if row.has_cwt]
    cwt_only_count = sum(row.cwt_only for row in rows)
    nearest = _nearest_cwt(selected, cwt_rows)
    nearest_delta = (
        abs(selected.rt_apex_min - nearest.rt_apex_min)
        if selected is not None and nearest is not None
        else None
    )
    return CwtGroupAuditRow(
        group_id=first.group_id,
        sample_name=first.sample_name,
        target_label=first.target_label,
        resolver_mode=first.resolver_mode,
        cwt_agreement_class=_agreement_class(
            selected,
            cwt_rows,
            nearest_delta_min=nearest_delta,
            near_rt_window_min=near_rt_window_min,
        ),
        candidate_count=len(rows),
        cwt_row_count=len(cwt_rows),
        cwt_only_row_count=cwt_only_count,
        selected_candidate_id=selected.candidate_id if selected else "",
        selected_rt_apex_min=selected.rt_apex_min if selected else None,
        selected_proposal_sources=selected.proposal_sources if selected else "",
        nearest_cwt_candidate_id=nearest.candidate_id if nearest else "",
        nearest_cwt_rt_apex_min=nearest.rt_apex_min if nearest else None,
        nearest_cwt_delta_min=nearest_delta,
        selected_confidence=selected.confidence if selected else "",
        selected_raw_score=selected.raw_score if selected else "",
        selected_reason=selected.reason if selected else "",
    )


def _agreement_class(
    selected: CwtCandidateRow | None,
    cwt_rows: list[CwtCandidateRow],
    *,
    nearest_delta_min: float | None,
    near_rt_window_min: float,
) -> str:
    if selected is None:
        return "no_selected_candidate"
    if selected.has_cwt:
        return "selected_cwt_agreed"
    if cwt_rows:
        if nearest_delta_min is not None and nearest_delta_min <= near_rt_window_min:
            return "selected_cwt_nearby"
        return "selected_cwt_disagreed"
    return "selected_without_cwt"


def _nearest_cwt(
    selected: CwtCandidateRow | None,
    cwt_rows: list[CwtCandidateRow],
) -> CwtCandidateRow | None:
    if selected is None or not cwt_rows:
        return None
    return min(cwt_rows, key=lambda row: abs(selected.rt_apex_min - row.rt_apex_min))


def _cwt_only_rows(rows: tuple[CwtCandidateRow, ...]) -> tuple[CwtOnlyAuditRow, ...]:
    return tuple(
        CwtOnlyAuditRow(
            group_id=row.group_id,
            sample_name=row.sample_name,
            target_label=row.target_label,
            resolver_mode=row.resolver_mode,
            candidate_id=row.candidate_id,
            rt_apex_min=row.rt_apex_min,
            confidence=row.confidence,
            raw_score=row.raw_score,
            reason=row.reason,
        )
        for row in rows
        if row.cwt_only
    )


def _summary(
    rows: tuple[CwtCandidateRow, ...],
    groups: tuple[CwtGroupAuditRow, ...],
    cwt_only_rows: tuple[CwtOnlyAuditRow, ...],
) -> dict[str, int]:
    return {
        "candidate_row_count": len(rows),
        "candidate_group_count": len(groups),
        "cwt_row_count": sum(row.has_cwt for row in rows),
        "cwt_only_row_count": len(cwt_only_rows),
        "selected_cwt_agreed_group_count": _group_class_count(
            groups, "selected_cwt_agreed"
        ),
        "selected_cwt_nearby_group_count": _group_class_count(
            groups, "selected_cwt_nearby"
        ),
        "selected_cwt_disagreed_group_count": _group_class_count(
            groups, "selected_cwt_disagreed"
        ),
        "selected_without_cwt_group_count": _group_class_count(
            groups, "selected_without_cwt"
        ),
    }


def _group_class_count(
    groups: tuple[CwtGroupAuditRow, ...],
    cwt_agreement_class: str,
) -> int:
    return sum(row.cwt_agreement_class == cwt_agreement_class for row in groups)


def _write_outputs(
    output_dir: Path,
    payload: dict[str, object],
    groups: tuple[CwtGroupAuditRow, ...],
    cwt_only_rows: tuple[CwtOnlyAuditRow, ...],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_summary(output_dir / "cwt_peak_candidate_audit_summary.tsv", payload)
    _write_groups(output_dir / "cwt_peak_candidate_groups.tsv", groups)
    _write_cwt_only(output_dir / "cwt_peak_candidate_cwt_only.tsv", cwt_only_rows)
    (output_dir / "cwt_peak_candidate_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "cwt_peak_candidate_audit.md").write_text(
        _markdown(payload),
        encoding="utf-8",
    )


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise TypeError("summary payload must be a dictionary")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_SUMMARY_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerow(summary)


def _write_groups(path: Path, rows: tuple[CwtGroupAuditRow, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_GROUP_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(_format_group_row(row) for row in rows)


def _write_cwt_only(path: Path, rows: tuple[CwtOnlyAuditRow, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CWT_ONLY_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(_format_cwt_only_row(row) for row in rows)


def _format_group_row(row: CwtGroupAuditRow) -> dict[str, str]:
    return {
        "group_id": row.group_id,
        "sample_name": row.sample_name,
        "target_label": row.target_label,
        "resolver_mode": row.resolver_mode,
        "cwt_agreement_class": row.cwt_agreement_class,
        "candidate_count": str(row.candidate_count),
        "cwt_row_count": str(row.cwt_row_count),
        "cwt_only_row_count": str(row.cwt_only_row_count),
        "selected_candidate_id": row.selected_candidate_id,
        "selected_rt_apex_min": _format_optional_float(row.selected_rt_apex_min),
        "selected_proposal_sources": row.selected_proposal_sources,
        "nearest_cwt_candidate_id": row.nearest_cwt_candidate_id,
        "nearest_cwt_rt_apex_min": _format_optional_float(row.nearest_cwt_rt_apex_min),
        "nearest_cwt_delta_min": _format_optional_float(row.nearest_cwt_delta_min),
        "selected_confidence": row.selected_confidence,
        "selected_raw_score": row.selected_raw_score,
        "selected_reason": row.selected_reason,
    }


def _format_cwt_only_row(row: CwtOnlyAuditRow) -> dict[str, str]:
    return {
        "group_id": row.group_id,
        "sample_name": row.sample_name,
        "target_label": row.target_label,
        "resolver_mode": row.resolver_mode,
        "candidate_id": row.candidate_id,
        "rt_apex_min": _format_optional_float(row.rt_apex_min),
        "confidence": row.confidence,
        "raw_score": row.raw_score,
        "reason": row.reason,
    }


def _markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    if not isinstance(summary, dict):
        raise TypeError("summary payload must be a dictionary")
    return "\n".join(
        [
            "# CWT Peak Candidate Audit",
            "",
            f"- candidate_row_count: {summary['candidate_row_count']}",
            f"- candidate_group_count: {summary['candidate_group_count']}",
            f"- cwt_row_count: {summary['cwt_row_count']}",
            f"- cwt_only_row_count: {summary['cwt_only_row_count']}",
            "- selected_cwt_agreed_group_count: "
            f"{summary['selected_cwt_agreed_group_count']}",
            "- selected_cwt_nearby_group_count: "
            f"{summary['selected_cwt_nearby_group_count']}",
            "- selected_cwt_disagreed_group_count: "
            f"{summary['selected_cwt_disagreed_group_count']}",
            "- selected_without_cwt_group_count: "
            f"{summary['selected_without_cwt_group_count']}",
            "",
        ]
    )


def _float_value(path: Path, row_number: int, column: str, value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        message = f"{path}: row {row_number} invalid {column}: {value!r}"
        raise ValueError(message) from exc


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.5f}"


if __name__ == "__main__":
    raise SystemExit(main())
