from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from xic_extractor.evidence_semantics import (
    EvidenceSignalSet,
    classify_evidence_consistency,
)

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
    "support_labels",
    "concern_labels",
    "cap_labels",
    "reason",
    "rejection_reason",
    "ms2_present",
    "nl_match",
    "ms2_trace_strength",
)

_APEX_SHADOW_RT_WINDOW_MIN = 0.08

_SUMMARY_COLUMNS = (
    "candidate_row_count",
    "candidate_group_count",
    "selected_row_count",
    "rejected_row_count",
    "selected_review_only_count",
    "selected_nl_fail_count",
    "selected_no_ms2_count",
    "plausible_nl_dropout_selected_count",
    "apex_evidence_shadow_group_count",
    "high_score_rejected_challenger_group_count",
    "strict_nl_rejected_challenger_group_count",
    "cwt_supported_rejected_challenger_group_count",
)

_RISK_COLUMNS = (
    "group_id",
    "sample_name",
    "target_label",
    "resolver_mode",
    "risk_type",
    "selected_candidate_id",
    "selected_rt_apex_min",
    "selected_raw_score",
    "selected_confidence",
    "selected_support_labels",
    "selected_concern_labels",
    "challenger_candidate_id",
    "challenger_rt_apex_min",
    "challenger_raw_score",
    "challenger_confidence",
    "challenger_support_labels",
    "challenger_concern_labels",
    "reason",
)

_LABEL_COLUMNS = (
    "label_kind",
    "label",
    "selected_count",
    "rejected_count",
    "selected_rate",
    "selected_median_raw_score",
    "rejected_median_raw_score",
)


@dataclass(frozen=True)
class PeakCandidateScoreRow:
    sample_name: str
    target_label: str
    resolver_mode: str
    candidate_id: str
    proposal_sources: str
    rt_apex_min: float | None
    selected: bool
    confidence: str
    raw_score: float | None
    support_labels: tuple[str, ...]
    concern_labels: tuple[str, ...]
    cap_labels: tuple[str, ...]
    reason: str
    rejection_reason: str
    ms2_present: str
    nl_match: str
    ms2_trace_strength: str

    @property
    def group_id(self) -> str:
        return "|".join((self.sample_name, self.target_label, self.resolver_mode))

    @property
    def source_set(self) -> frozenset[str]:
        return frozenset(_split_labels(self.proposal_sources))

    @property
    def support_set(self) -> frozenset[str]:
        return frozenset(self.support_labels)

    @property
    def concern_set(self) -> frozenset[str]:
        return frozenset(self.concern_labels)


@dataclass(frozen=True)
class ScoreRiskRow:
    group_id: str
    sample_name: str
    target_label: str
    resolver_mode: str
    risk_type: str
    selected_candidate_id: str
    selected_rt_apex_min: float | None
    selected_raw_score: float | None
    selected_confidence: str
    selected_support_labels: str
    selected_concern_labels: str
    challenger_candidate_id: str
    challenger_rt_apex_min: float | None
    challenger_raw_score: float | None
    challenger_confidence: str
    challenger_support_labels: str
    challenger_concern_labels: str
    reason: str


@dataclass(frozen=True)
class ScoreLabelImpactRow:
    label_kind: str
    label: str
    selected_count: int
    rejected_count: int
    selected_rate: float | None
    selected_median_raw_score: float | None
    rejected_median_raw_score: float | None


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = _read_peak_candidates(args.peak_candidates_tsv)
        risk_rows = _risk_rows(rows)
        label_impact = _label_impact(rows)
        summary = _summary(rows, risk_rows)
        payload = {
            "summary": summary,
            "risk_rows": [asdict(row) for row in risk_rows],
            "label_impact": [asdict(row) for row in label_impact],
            "recommendations": _recommendations(summary, risk_rows),
        }
        _write_outputs(args.output_dir, payload, risk_rows, label_impact)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        "Peak candidate score calibration JSON: "
        f"{args.output_dir / 'peak_candidate_score_calibration.json'}"
    )
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit peak candidate scoring against newer evidence labels without "
            "changing production selection."
        )
    )
    parser.add_argument("--peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def _read_peak_candidates(path: Path) -> tuple[PeakCandidateScoreRow, ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in _REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return tuple(
            _row_from_dict(path, row_number, row)
            for row_number, row in enumerate(reader, 2)
        )


def _row_from_dict(
    path: Path,
    row_number: int,
    row: dict[str, str],
) -> PeakCandidateScoreRow:
    return PeakCandidateScoreRow(
        sample_name=row["sample_name"],
        target_label=row["target_label"],
        resolver_mode=row["resolver_mode"],
        candidate_id=row["candidate_id"],
        proposal_sources=row["proposal_sources"],
        rt_apex_min=_optional_float(
            path,
            row_number,
            "rt_apex_min",
            row["rt_apex_min"],
        ),
        selected=_bool_value(row["selected"]),
        confidence=row["confidence"],
        raw_score=_optional_float(path, row_number, "raw_score", row["raw_score"]),
        support_labels=tuple(_split_labels(row["support_labels"])),
        concern_labels=tuple(_split_labels(row["concern_labels"])),
        cap_labels=tuple(_split_labels(row["cap_labels"])),
        reason=row["reason"],
        rejection_reason=row["rejection_reason"],
        ms2_present=row["ms2_present"],
        nl_match=row["nl_match"],
        ms2_trace_strength=row["ms2_trace_strength"],
    )


def _risk_rows(rows: tuple[PeakCandidateScoreRow, ...]) -> tuple[ScoreRiskRow, ...]:
    grouped: dict[str, list[PeakCandidateScoreRow]] = {}
    for row in rows:
        grouped.setdefault(row.group_id, []).append(row)
    risks: list[ScoreRiskRow] = []
    for _, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
        risks.extend(_group_risks(group_rows))
    return tuple(risks)


def _group_risks(rows: list[PeakCandidateScoreRow]) -> list[ScoreRiskRow]:
    selected = next((row for row in rows if row.selected), None)
    rejected = [row for row in rows if not row.selected]
    if selected is None:
        return []

    risks: list[ScoreRiskRow] = []
    if _selected_review_only(selected):
        risks.append(
            _risk_row(
                selected,
                "selected_review_only",
                challenger=None,
                reason="Selected candidate is review-only or VERY_LOW confidence.",
            )
        )
    if _selected_nl_fail(selected):
        risks.append(
            _risk_row(
                selected,
                "selected_nl_fail",
                challenger=None,
                reason="Selected candidate carries NL failure evidence.",
            )
        )
        if _plausible_nl_dropout(selected):
            risks.append(
                _risk_row(
                    selected,
                    "plausible_nl_dropout_selected",
                    challenger=None,
                    reason=(
                        "Selected row has strong MS1/shape support but lacks "
                        "the expected NL; treat as possible NL dropout context."
                    ),
                )
            )
    if _selected_no_ms2(selected):
        risks.append(
            _risk_row(
                selected,
                "selected_no_ms2",
                challenger=None,
                reason="Selected candidate lacks MS2 evidence.",
            )
        )

    apex_shadow = _best_challenger(
        rejected,
        lambda row: _same_or_near_apex(selected, row) and _has_new_support(
            selected,
            row,
        ),
    )
    if apex_shadow is not None:
        risks.append(
            _risk_row(
                selected,
                "apex_evidence_shadow",
                challenger=apex_shadow,
                reason=(
                    "Rejected near-apex row carries support labels not mirrored "
                    "on the selected row; treat as provenance/boundary context."
                ),
            )
        )

    alternative_rejected = [
        row for row in rejected if not _same_or_near_apex(selected, row)
    ]
    high_score = _best_challenger(
        alternative_rejected,
        lambda row: _score_greater(row.raw_score, selected.raw_score),
    )
    if high_score is not None:
        risks.append(
            _risk_row(
                selected,
                "high_score_rejected_challenger",
                challenger=high_score,
                reason="Rejected challenger has a higher raw score than selected.",
            )
        )

    strict_nl = _best_challenger(
        alternative_rejected,
        lambda row: (
            "strict_nl_ok" in row.support_set
            and "strict_nl_ok" not in selected.support_set
        )
        or ("strict_nl_ok" in row.support_set and _selected_nl_fail(selected)),
    )
    if strict_nl is not None:
        risks.append(
            _risk_row(
                selected,
                "strict_nl_rejected_challenger",
                challenger=strict_nl,
                reason=(
                    "Rejected challenger has strict NL support while selected "
                    "does not."
                ),
            )
        )

    cwt_supported = _best_challenger(
        alternative_rejected,
        lambda row: "cwt_same_apex_support" in row.support_set,
    )
    if cwt_supported is not None:
        risks.append(
            _risk_row(
                selected,
                "cwt_supported_rejected_challenger",
                challenger=cwt_supported,
                reason="Rejected challenger has same-apex CWT support.",
            )
        )

    return risks


def _selected_review_only(row: PeakCandidateScoreRow) -> bool:
    reason = row.reason.lower()
    return row.confidence.strip().upper() == "VERY_LOW" or "review only" in reason


def _selected_nl_fail(row: PeakCandidateScoreRow) -> bool:
    return "nl_fail" in row.concern_set or _bool_value(row.nl_match) is False


def _selected_no_ms2(row: PeakCandidateScoreRow) -> bool:
    if "no_ms2" in row.concern_set:
        return True
    return (
        _bool_value(row.ms2_present) is False
        and "no_nl_required" not in row.support_set
    )


def _plausible_nl_dropout(row: PeakCandidateScoreRow) -> bool:
    return "plausible_nl_dropout" in classify_evidence_consistency(
        EvidenceSignalSet(
            support_labels=row.support_labels,
            concern_labels=(
                *row.concern_labels,
                *(() if _bool_value(row.nl_match) is not False else ("nl_fail",)),
            ),
            proposal_sources=tuple(row.source_set),
            ms2_present=_bool_value(row.ms2_present),
            nl_match=_bool_value(row.nl_match),
            raw_score=row.raw_score,
        )
    )


def _same_or_near_apex(
    left: PeakCandidateScoreRow,
    right: PeakCandidateScoreRow,
) -> bool:
    if left.rt_apex_min is None or right.rt_apex_min is None:
        return False
    return abs(left.rt_apex_min - right.rt_apex_min) <= _APEX_SHADOW_RT_WINDOW_MIN


def _has_new_support(
    selected: PeakCandidateScoreRow,
    challenger: PeakCandidateScoreRow,
) -> bool:
    return bool(challenger.support_set - selected.support_set) or _score_greater(
        challenger.raw_score,
        selected.raw_score,
    )


def _best_challenger(
    rows: Iterable[PeakCandidateScoreRow],
    predicate: Callable[[PeakCandidateScoreRow], bool],
) -> PeakCandidateScoreRow | None:
    matches = [row for row in rows if predicate(row)]
    if not matches:
        return None
    return max(matches, key=lambda row: _score_sort_value(row.raw_score))


def _score_greater(left: float | None, right: float | None) -> bool:
    return _score_sort_value(left) > _score_sort_value(right)


def _score_sort_value(value: float | None) -> float:
    if value is None:
        return float("-inf")
    return value


def _risk_row(
    selected: PeakCandidateScoreRow,
    risk_type: str,
    *,
    challenger: PeakCandidateScoreRow | None,
    reason: str,
) -> ScoreRiskRow:
    return ScoreRiskRow(
        group_id=selected.group_id,
        sample_name=selected.sample_name,
        target_label=selected.target_label,
        resolver_mode=selected.resolver_mode,
        risk_type=risk_type,
        selected_candidate_id=selected.candidate_id,
        selected_rt_apex_min=selected.rt_apex_min,
        selected_raw_score=selected.raw_score,
        selected_confidence=selected.confidence,
        selected_support_labels=";".join(selected.support_labels),
        selected_concern_labels=";".join(selected.concern_labels),
        challenger_candidate_id=challenger.candidate_id if challenger else "",
        challenger_rt_apex_min=challenger.rt_apex_min if challenger else None,
        challenger_raw_score=challenger.raw_score if challenger else None,
        challenger_confidence=challenger.confidence if challenger else "",
        challenger_support_labels=";".join(challenger.support_labels)
        if challenger
        else "",
        challenger_concern_labels=";".join(challenger.concern_labels)
        if challenger
        else "",
        reason=reason,
    )


def _label_impact(
    rows: tuple[PeakCandidateScoreRow, ...],
) -> tuple[ScoreLabelImpactRow, ...]:
    buckets: dict[tuple[str, str], list[PeakCandidateScoreRow]] = {}
    for row in rows:
        for label in row.support_labels:
            buckets.setdefault(("support", label), []).append(row)
        for label in row.concern_labels:
            buckets.setdefault(("concern", label), []).append(row)
        for label in row.cap_labels:
            buckets.setdefault(("cap", label), []).append(row)

    label_rows = tuple(
        _label_impact_row(kind, label, label_rows)
        for (kind, label), label_rows in buckets.items()
    )
    return tuple(
        sorted(
            label_rows,
            key=lambda row: (
                row.label_kind,
                -(row.selected_count + row.rejected_count),
                row.label,
            ),
        )
    )


def _label_impact_row(
    label_kind: str,
    label: str,
    rows: list[PeakCandidateScoreRow],
) -> ScoreLabelImpactRow:
    selected_scores = [row.raw_score for row in rows if row.selected]
    rejected_scores = [row.raw_score for row in rows if not row.selected]
    selected_count = len(selected_scores)
    rejected_count = len(rejected_scores)
    total = selected_count + rejected_count
    return ScoreLabelImpactRow(
        label_kind=label_kind,
        label=label,
        selected_count=selected_count,
        rejected_count=rejected_count,
        selected_rate=selected_count / total if total else None,
        selected_median_raw_score=_median_score(selected_scores),
        rejected_median_raw_score=_median_score(rejected_scores),
    )


def _summary(
    rows: tuple[PeakCandidateScoreRow, ...],
    risk_rows: tuple[ScoreRiskRow, ...],
) -> dict[str, int]:
    group_ids = {row.group_id for row in rows}
    risk_group_counts = _risk_group_counts(risk_rows)
    return {
        "candidate_row_count": len(rows),
        "candidate_group_count": len(group_ids),
        "selected_row_count": sum(row.selected for row in rows),
        "rejected_row_count": sum(not row.selected for row in rows),
        "selected_review_only_count": risk_group_counts["selected_review_only"],
        "selected_nl_fail_count": risk_group_counts["selected_nl_fail"],
        "selected_no_ms2_count": risk_group_counts["selected_no_ms2"],
        "plausible_nl_dropout_selected_count": risk_group_counts[
            "plausible_nl_dropout_selected"
        ],
        "apex_evidence_shadow_group_count": risk_group_counts[
            "apex_evidence_shadow"
        ],
        "high_score_rejected_challenger_group_count": risk_group_counts[
            "high_score_rejected_challenger"
        ],
        "strict_nl_rejected_challenger_group_count": risk_group_counts[
            "strict_nl_rejected_challenger"
        ],
        "cwt_supported_rejected_challenger_group_count": risk_group_counts[
            "cwt_supported_rejected_challenger"
        ],
    }


def _risk_group_counts(risk_rows: tuple[ScoreRiskRow, ...]) -> Counter[str]:
    risk_groups: dict[str, set[str]] = {}
    for row in risk_rows:
        risk_groups.setdefault(row.risk_type, set()).add(row.group_id)
    return Counter(
        {
            risk_type: len(group_ids)
            for risk_type, group_ids in risk_groups.items()
        }
    )


def _recommendations(
    summary: dict[str, int],
    risk_rows: tuple[ScoreRiskRow, ...],
) -> tuple[str, ...]:
    recommendations: list[str] = []
    if summary["apex_evidence_shadow_group_count"]:
        recommendations.append(
            "Resolve near-apex audit/provenance shadows before treating rejected "
            "CWT rows as true alternative peaks."
        )
    if summary["strict_nl_rejected_challenger_group_count"]:
        recommendations.append(
            "Rebalance NL evidence before changing generic raw-score thresholds."
        )
    if summary["cwt_supported_rejected_challenger_group_count"]:
        recommendations.append(
            "Treat CWT same-apex support as a bounded positive signal only when "
            "chemical evidence is present."
        )
    if summary["selected_review_only_count"] or summary["selected_nl_fail_count"]:
        recommendations.append(
            "Keep weak targeted evidence visible in review, but do not count it as "
            "a clean positive for benchmark denominators."
        )
    if summary["plausible_nl_dropout_selected_count"]:
        recommendations.append(
            "Review plausible NL-dropout rows separately before weakening the "
            "global NL-fail cap."
        )
    if not recommendations and not risk_rows:
        recommendations.append("No scoring conflicts detected in this input.")
    return tuple(recommendations)


def _write_outputs(
    output_dir: Path,
    payload: dict[str, object],
    risk_rows: tuple[ScoreRiskRow, ...],
    label_impact: tuple[ScoreLabelImpactRow, ...],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_summary(output_dir / "peak_candidate_score_calibration_summary.tsv", payload)
    _write_risk_rows(output_dir / "peak_candidate_score_risk_rows.tsv", risk_rows)
    _write_label_impact(
        output_dir / "peak_candidate_score_label_impact.tsv",
        label_impact,
    )
    (output_dir / "peak_candidate_score_calibration.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "peak_candidate_score_calibration.md").write_text(
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


def _write_risk_rows(path: Path, rows: tuple[ScoreRiskRow, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_RISK_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(_format_risk_row(row) for row in rows)


def _write_label_impact(path: Path, rows: tuple[ScoreLabelImpactRow, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_LABEL_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(_format_label_impact_row(row) for row in rows)


def _format_risk_row(row: ScoreRiskRow) -> dict[str, str]:
    return {
        "group_id": row.group_id,
        "sample_name": row.sample_name,
        "target_label": row.target_label,
        "resolver_mode": row.resolver_mode,
        "risk_type": row.risk_type,
        "selected_candidate_id": row.selected_candidate_id,
        "selected_rt_apex_min": _format_optional_float(row.selected_rt_apex_min),
        "selected_raw_score": _format_optional_float(row.selected_raw_score),
        "selected_confidence": row.selected_confidence,
        "selected_support_labels": row.selected_support_labels,
        "selected_concern_labels": row.selected_concern_labels,
        "challenger_candidate_id": row.challenger_candidate_id,
        "challenger_rt_apex_min": _format_optional_float(row.challenger_rt_apex_min),
        "challenger_raw_score": _format_optional_float(row.challenger_raw_score),
        "challenger_confidence": row.challenger_confidence,
        "challenger_support_labels": row.challenger_support_labels,
        "challenger_concern_labels": row.challenger_concern_labels,
        "reason": row.reason,
    }


def _format_label_impact_row(row: ScoreLabelImpactRow) -> dict[str, str]:
    return {
        "label_kind": row.label_kind,
        "label": row.label,
        "selected_count": str(row.selected_count),
        "rejected_count": str(row.rejected_count),
        "selected_rate": _format_optional_float(row.selected_rate),
        "selected_median_raw_score": _format_optional_float(
            row.selected_median_raw_score
        ),
        "rejected_median_raw_score": _format_optional_float(
            row.rejected_median_raw_score
        ),
    }


def _markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    recommendations = payload["recommendations"]
    if not isinstance(summary, dict):
        raise TypeError("summary payload must be a dictionary")
    if not isinstance(recommendations, list | tuple):
        raise TypeError("recommendations payload must be a sequence")
    lines = [
        "# Peak Candidate Score Calibration",
        "",
        "This diagnostic does not change production selection.",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {column}: {summary[column]}" for column in _SUMMARY_COLUMNS)
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {recommendation}" for recommendation in recommendations)
    lines.append("")
    return "\n".join(lines)


def _split_labels(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _bool_value(value: str) -> bool | None:
    normalized = value.strip().upper()
    if normalized in {"TRUE", "T", "YES", "Y", "1"}:
        return True
    if normalized in {"FALSE", "F", "NO", "N", "0"}:
        return False
    return None


def _optional_float(
    path: Path,
    row_number: int,
    column: str,
    value: str,
) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        message = f"{path}: row {row_number} invalid {column}: {value!r}"
        raise ValueError(message) from exc


def _median_score(values: Iterable[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return float(statistics.median(numeric))


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.5f}"


if __name__ == "__main__":
    raise SystemExit(main())
