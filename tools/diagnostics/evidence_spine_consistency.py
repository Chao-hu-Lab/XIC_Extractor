"""Audit targeted and untargeted shared evidence semantics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


DEFAULT_FOCUS_LABELS = (
    "15N5-8-oxodG",
    "d3-N6-medA",
    "5-medC",
    "5-hmdC",
)

ROW_FIELDS = (
    "sample",
    "target_label",
    "role",
    "targeted_candidate_id",
    "untargeted_family_id",
    "target_mz",
    "untargeted_family_mz",
    "mz_delta_ppm",
    "trace_scan_count",
    "rt_window_min",
    "targeted_selected_rt",
    "untargeted_selected_rt",
    "rt_delta_min",
    "targeted_boundary_start",
    "targeted_boundary_end",
    "untargeted_boundary_start",
    "untargeted_boundary_end",
    "boundary_delta_start_min",
    "boundary_delta_end_min",
    "targeted_area",
    "untargeted_area",
    "area_ratio_untargeted_to_targeted",
    "baseline_corrected_area_available",
    "targeted_region_verdict",
    "untargeted_region_verdict",
    "targeted_local_mixture_verdict",
    "untargeted_local_mixture_verdict",
    "mismatch_reason",
)

SUMMARY_FIELDS = (
    "rows_checked",
    "matched_rows",
    "consistent_rows",
    "mismatch_rows",
    "missing_alignment_rows",
    "focused_target_labels",
    "included_istd_rows",
    "mismatch_reason_counts",
)


@dataclass(frozen=True)
class EvidenceSpineConsistencyOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class TargetedCandidate:
    sample: str
    target_label: str
    role: str
    candidate_id: str
    rt: float | None
    left: float | None
    right: float | None
    area: float | None
    baseline_area: float | None
    scan_count: int | None


@dataclass(frozen=True)
class TargetedShadow:
    shadow_verdict: str
    local_mixture_diagnostic: str


@dataclass(frozen=True)
class AlignmentCell:
    sample: str
    family_id: str
    status: str
    mz: float | None
    rt: float | None
    area: float | None
    left: float | None
    right: float | None
    region_verdict: str
    local_mixture_diagnostic: str


@dataclass(frozen=True)
class ConsistencyRow:
    sample: str
    target_label: str
    role: str
    targeted_candidate_id: str
    untargeted_family_id: str
    target_mz: float | None
    untargeted_family_mz: float | None
    mz_delta_ppm: float | None
    trace_scan_count: int | None
    rt_window_min: str
    targeted_selected_rt: float | None
    untargeted_selected_rt: float | None
    rt_delta_min: float | None
    targeted_boundary_start: float | None
    targeted_boundary_end: float | None
    untargeted_boundary_start: float | None
    untargeted_boundary_end: float | None
    boundary_delta_start_min: float | None
    boundary_delta_end_min: float | None
    targeted_area: float | None
    untargeted_area: float | None
    area_ratio_untargeted_to_targeted: float | None
    baseline_corrected_area_available: bool
    targeted_region_verdict: str
    untargeted_region_verdict: str
    targeted_local_mixture_verdict: str
    untargeted_local_mixture_verdict: str
    mismatch_reason: str


@dataclass(frozen=True)
class ConsistencySummary:
    rows_checked: int
    matched_rows: int
    consistent_rows: int
    mismatch_rows: int
    missing_alignment_rows: int
    focused_target_labels: str
    included_istd_rows: int
    mismatch_reason_counts: str


@dataclass(frozen=True)
class EvidenceSpineConsistencyResult:
    summary: ConsistencySummary
    rows: tuple[ConsistencyRow, ...]


def run_evidence_spine_consistency(
    *,
    targeted_dir: Path,
    alignment_dir: Path,
    output_dir: Path,
    target_labels: Sequence[str] = DEFAULT_FOCUS_LABELS,
    include_istd: bool = True,
    match_ppm: float = 20.0,
    match_rt_min: float = 0.75,
) -> tuple[EvidenceSpineConsistencyOutputs, EvidenceSpineConsistencyResult]:
    targeted = _read_targeted_candidates(targeted_dir / "peak_candidates.tsv")
    target_mz = _read_target_mz(targeted_dir / "peak_candidate_boundaries.tsv")
    shadows = _read_targeted_shadows(
        targeted_dir / "peak_region_selection_shadow_summary.tsv"
    )
    cells = _read_alignment_cells(alignment_dir / "alignment_cells.tsv")
    rows = _build_rows(
        targeted,
        target_mz=target_mz,
        shadows=shadows,
        alignment_cells=cells,
        target_labels=tuple(target_labels),
        include_istd=include_istd,
        match_ppm=match_ppm,
        match_rt_min=match_rt_min,
    )
    result = EvidenceSpineConsistencyResult(
        summary=_summarize(rows, target_labels=tuple(target_labels)),
        rows=tuple(rows),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = EvidenceSpineConsistencyOutputs(
        summary_tsv=output_dir / "evidence_spine_consistency_summary.tsv",
        rows_tsv=output_dir / "evidence_spine_consistency_rows.tsv",
        json_path=output_dir / "evidence_spine_consistency.json",
        markdown_path=output_dir / "evidence_spine_consistency.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def _read_targeted_candidates(path: Path) -> tuple[TargetedCandidate, ...]:
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "role",
            "candidate_id",
            "selected",
            "rt_apex_min",
            "rt_left_min",
            "rt_right_min",
            "area_raw_counts_seconds",
            "area_baseline_corrected",
            "region_scan_count",
        ),
    )
    return tuple(
        TargetedCandidate(
            sample=row["sample_name"],
            target_label=row["target_label"],
            role=row["role"],
            candidate_id=row["candidate_id"],
            rt=_optional_float(row["rt_apex_min"]),
            left=_optional_float(row["rt_left_min"]),
            right=_optional_float(row["rt_right_min"]),
            area=_optional_float(row["area_raw_counts_seconds"]),
            baseline_area=_optional_float(row["area_baseline_corrected"]),
            scan_count=_optional_int(row["region_scan_count"]),
        )
        for row in rows
        if _bool_value(row["selected"]) is True
    )


def _read_target_mz(path: Path) -> dict[tuple[str, str, str], float]:
    if not path.exists():
        return {}
    rows = _read_required_tsv(
        path,
        ("sample_name", "target_label", "candidate_id", "target_mz"),
    )
    values: dict[tuple[str, str, str], float] = {}
    for row in rows:
        value = _optional_float(row["target_mz"])
        if value is None:
            continue
        key = (row["sample_name"], row["target_label"], row["candidate_id"])
        values.setdefault(key, value)
    return values


def _read_targeted_shadows(path: Path) -> dict[tuple[str, str], TargetedShadow]:
    if not path.exists():
        return {}
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "shadow_verdict",
            "local_mixture_diagnostic",
        ),
    )
    return {
        (row["sample_name"], row["target_label"]): TargetedShadow(
            shadow_verdict=row["shadow_verdict"],
            local_mixture_diagnostic=row["local_mixture_diagnostic"],
        )
        for row in rows
    }


def _read_alignment_cells(path: Path) -> tuple[AlignmentCell, ...]:
    rows = _read_required_tsv(
        path,
        (
            "sample_stem",
            "feature_family_id",
            "status",
            "area",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "family_center_mz",
            "region_shadow_verdict",
            "region_local_mixture_diagnostic",
        ),
    )
    return tuple(
        AlignmentCell(
            sample=row["sample_stem"],
            family_id=row["feature_family_id"],
            status=row["status"],
            mz=_optional_float(row["family_center_mz"]),
            rt=_optional_float(row["apex_rt"]),
            area=_optional_float(row["area"]),
            left=_optional_float(row["peak_start_rt"]),
            right=_optional_float(row["peak_end_rt"]),
            region_verdict=row["region_shadow_verdict"],
            local_mixture_diagnostic=row["region_local_mixture_diagnostic"],
        )
        for row in rows
    )


def _build_rows(
    targeted: tuple[TargetedCandidate, ...],
    *,
    target_mz: Mapping[tuple[str, str, str], float],
    shadows: Mapping[tuple[str, str], TargetedShadow],
    alignment_cells: tuple[AlignmentCell, ...],
    target_labels: tuple[str, ...],
    include_istd: bool,
    match_ppm: float,
    match_rt_min: float,
) -> list[ConsistencyRow]:
    focus = set(target_labels)
    cells_by_sample: dict[str, list[AlignmentCell]] = {}
    for cell in alignment_cells:
        if cell.status not in {"detected", "rescued"}:
            continue
        cells_by_sample.setdefault(cell.sample, []).append(cell)

    rows: list[ConsistencyRow] = []
    for candidate in targeted:
        if candidate.target_label not in focus and not (
            include_istd and candidate.role == "ISTD"
        ):
            continue
        mz = target_mz.get(
            (candidate.sample, candidate.target_label, candidate.candidate_id)
        )
        shadow = shadows.get((candidate.sample, candidate.target_label))
        match = _best_alignment_match(
            candidate,
            target_mz=mz,
            cells=cells_by_sample.get(candidate.sample, ()),
            match_ppm=match_ppm,
            match_rt_min=match_rt_min,
        )
        rows.append(_consistency_row(candidate, mz=mz, shadow=shadow, match=match))
    return rows


def _best_alignment_match(
    candidate: TargetedCandidate,
    *,
    target_mz: float | None,
    cells: Sequence[AlignmentCell],
    match_ppm: float,
    match_rt_min: float,
) -> AlignmentCell | None:
    if target_mz is None or candidate.rt is None:
        return None
    candidates: list[tuple[float, AlignmentCell]] = []
    for cell in cells:
        if cell.mz is None or cell.rt is None:
            continue
        ppm = _ppm(cell.mz, target_mz)
        rt_delta = abs(cell.rt - candidate.rt)
        if ppm <= match_ppm and rt_delta <= match_rt_min:
            candidates.append((ppm + rt_delta, cell))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def _consistency_row(
    candidate: TargetedCandidate,
    *,
    mz: float | None,
    shadow: TargetedShadow | None,
    match: AlignmentCell | None,
) -> ConsistencyRow:
    targeted_region_verdict = "" if shadow is None else shadow.shadow_verdict
    targeted_mixture = "" if shadow is None else shadow.local_mixture_diagnostic
    reasons = _mismatch_reasons(candidate, mz=mz, shadow=shadow, match=match)
    return ConsistencyRow(
        sample=candidate.sample,
        target_label=candidate.target_label,
        role=candidate.role,
        targeted_candidate_id=candidate.candidate_id,
        untargeted_family_id="" if match is None else match.family_id,
        target_mz=mz,
        untargeted_family_mz=None if match is None else match.mz,
        mz_delta_ppm=(
            None
            if match is None or mz is None or match.mz is None
            else _ppm(match.mz, mz)
        ),
        trace_scan_count=candidate.scan_count,
        rt_window_min=_format_rt_window(candidate.left, candidate.right),
        targeted_selected_rt=candidate.rt,
        untargeted_selected_rt=None if match is None else match.rt,
        rt_delta_min=None
        if match is None or candidate.rt is None or match.rt is None
        else match.rt - candidate.rt,
        targeted_boundary_start=candidate.left,
        targeted_boundary_end=candidate.right,
        untargeted_boundary_start=None if match is None else match.left,
        untargeted_boundary_end=None if match is None else match.right,
        boundary_delta_start_min=None
        if match is None or candidate.left is None or match.left is None
        else match.left - candidate.left,
        boundary_delta_end_min=None
        if match is None or candidate.right is None or match.right is None
        else match.right - candidate.right,
        targeted_area=candidate.area,
        untargeted_area=None if match is None else match.area,
        area_ratio_untargeted_to_targeted=_ratio(
            None if match is None else match.area,
            candidate.area,
        ),
        baseline_corrected_area_available=candidate.baseline_area is not None,
        targeted_region_verdict=targeted_region_verdict,
        untargeted_region_verdict="" if match is None else match.region_verdict,
        targeted_local_mixture_verdict=targeted_mixture,
        untargeted_local_mixture_verdict=""
        if match is None
        else match.local_mixture_diagnostic,
        mismatch_reason=";".join(reasons),
    )


def _mismatch_reasons(
    candidate: TargetedCandidate,
    *,
    mz: float | None,
    shadow: TargetedShadow | None,
    match: AlignmentCell | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if mz is None:
        reasons.append("target_mz_unavailable")
    if match is None:
        reasons.append("no_alignment_mz_rt_match")
        return tuple(reasons)
    if candidate.left is not None and match.left is not None:
        if abs(match.left - candidate.left) > 0.10:
            reasons.append("boundary_start_delta_gt_0.10")
    if candidate.right is not None and match.right is not None:
        if abs(match.right - candidate.right) > 0.10:
            reasons.append("boundary_end_delta_gt_0.10")
    area_ratio = _ratio(match.area, candidate.area)
    if area_ratio is not None and (area_ratio < 0.5 or area_ratio > 2.0):
        reasons.append("area_ratio_outside_2x")
    if shadow is not None and shadow.shadow_verdict and match.region_verdict:
        if shadow.shadow_verdict != match.region_verdict:
            reasons.append("region_verdict_mismatch")
    if (
        shadow is not None
        and shadow.local_mixture_diagnostic
        and match.local_mixture_diagnostic
        and shadow.local_mixture_diagnostic != match.local_mixture_diagnostic
    ):
        reasons.append("local_mixture_mismatch")
    if not reasons:
        reasons.append("consistent")
    return tuple(reasons)


def _summarize(
    rows: Sequence[ConsistencyRow],
    *,
    target_labels: tuple[str, ...],
) -> ConsistencySummary:
    reason_counter: Counter[str] = Counter()
    matched = 0
    consistent = 0
    missing = 0
    istd_rows = 0
    for row in rows:
        if row.untargeted_family_id:
            matched += 1
        else:
            missing += 1
        if row.mismatch_reason == "consistent":
            consistent += 1
        if row.role == "ISTD":
            istd_rows += 1
        for reason in row.mismatch_reason.split(";"):
            reason_counter[reason] += 1
    return ConsistencySummary(
        rows_checked=len(rows),
        matched_rows=matched,
        consistent_rows=consistent,
        mismatch_rows=len(rows) - consistent,
        missing_alignment_rows=missing,
        focused_target_labels=";".join(target_labels),
        included_istd_rows=istd_rows,
        mismatch_reason_counts=_format_counter(reason_counter),
    )


def _write_outputs(
    outputs: EvidenceSpineConsistencyOutputs,
    result: EvidenceSpineConsistencyResult,
) -> None:
    _write_tsv(outputs.summary_tsv, SUMMARY_FIELDS, (asdict(result.summary),))
    _write_tsv(outputs.rows_tsv, ROW_FIELDS, tuple(asdict(row) for row in result.rows))
    with outputs.json_path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(result), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    _write_markdown(outputs.markdown_path, result)


def _write_markdown(
    path: Path,
    result: EvidenceSpineConsistencyResult,
) -> None:
    lines = [
        "# Evidence Spine Consistency",
        "",
        f"- Rows checked: {result.summary.rows_checked}",
        f"- Matched rows: {result.summary.matched_rows}",
        f"- Consistent rows: {result.summary.consistent_rows}",
        f"- Missing alignment rows: {result.summary.missing_alignment_rows}",
        f"- Mismatch reasons: {result.summary.mismatch_reason_counts}",
        "",
        "## Review Rows",
        "",
    ]
    for row in result.rows[:20]:
        lines.append(
            "- "
            f"{row.sample} / {row.target_label}: {row.mismatch_reason} "
            f"(family={row.untargeted_family_id or 'NA'}, "
            f"target_rt={_fmt(row.targeted_selected_rt)}, "
            f"align_rt={_fmt(row.untargeted_selected_rt)})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tsv(
    path: Path,
    fields: Sequence[str],
    rows: Sequence[Mapping[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=tuple(fields),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field)) for field in fields})


def _read_required_tsv(
    path: Path,
    required: Sequence[str],
) -> tuple[dict[str, str], ...]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required if column not in fieldnames]
        if missing:
            raise ValueError(
                f"{path}: missing required columns: {', '.join(missing)}"
            )
        return tuple(dict(row) for row in reader)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare targeted candidate and untargeted alignment evidence.",
    )
    parser.add_argument("--targeted-dir", type=Path, required=True)
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--target-label",
        action="append",
        default=[],
        help="Target label to include. Defaults to key high-value targets.",
    )
    parser.add_argument(
        "--exclude-istd",
        action="store_true",
        help="Do not automatically include all selected ISTD candidates.",
    )
    parser.add_argument("--match-ppm", type=float, default=20.0)
    parser.add_argument("--match-rt-min", type=float, default=0.75)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    labels = tuple(args.target_label) or DEFAULT_FOCUS_LABELS
    try:
        outputs, _result = run_evidence_spine_consistency(
            targeted_dir=args.targeted_dir,
            alignment_dir=args.alignment_dir,
            output_dir=args.output_dir,
            target_labels=labels,
            include_istd=not args.exclude_istd,
            match_ppm=args.match_ppm,
            match_rt_min=args.match_rt_min,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Consistency JSON: {outputs.json_path}")
    print(f"Consistency report: {outputs.markdown_path}")
    return 0


def _optional_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_int(value: object) -> int | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _bool_value(value: object) -> bool | None:
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _ppm(observed: float, expected: float) -> float:
    if expected == 0:
        return math.inf
    return abs(observed - expected) / expected * 1_000_000.0


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _format_rt_window(left: float | None, right: float | None) -> str:
    if left is None or right is None:
        return ""
    return f"{left:.6g}-{right:.6g}"


def _format_counter(counter: Counter[str]) -> str:
    return ";".join(f"{key}:{counter[key]}" for key in sorted(counter))


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.10g}"
    return str(value)


def _fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4g}"


if __name__ == "__main__":
    raise SystemExit(main())
