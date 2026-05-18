"""Classify targeted/untargeted area mismatch by integration uncertainty."""

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


RAW_AREA_RATIO_MIN = 0.80
RAW_AREA_RATIO_MAX = 1.25
HIGH_UNCERTAINTY_FRACTION = 0.20
LOW_BASELINE_FRACTION = 0.30
BOUNDARY_DELTA_CONCERN_MIN = 0.10

ROW_FIELDS = (
    "sample",
    "target_label",
    "role",
    "targeted_candidate_id",
    "untargeted_family_id",
    "target_mz",
    "untargeted_family_mz",
    "targeted_area",
    "untargeted_area",
    "raw_area_ratio",
    "targeted_baseline_area",
    "untargeted_baseline_area",
    "baseline_area_ratio",
    "targeted_uncertainty_fraction",
    "untargeted_uncertainty_fraction",
    "targeted_baseline_fraction",
    "untargeted_baseline_fraction",
    "boundary_delta_start_min",
    "boundary_delta_end_min",
    "boundary_alternative_area_ratio",
    "targeted_region_verdict",
    "untargeted_region_verdict",
    "targeted_local_mixture_verdict",
    "untargeted_local_mixture_verdict",
    "evidence_spine_mismatch_reason",
    "integration_bucket",
    "integration_reason",
)

SUMMARY_FIELDS = (
    "rows_checked",
    "bucket_counts",
    "missing_alignment_match_count",
    "integration_context_incomplete_count",
    "unexplained_area_mismatch_count",
)


@dataclass(frozen=True)
class AreaIntegrationUncertaintyOutputs:
    summary_tsv: Path
    rows_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class EvidenceRow:
    sample: str
    target_label: str
    role: str
    targeted_candidate_id: str
    untargeted_family_id: str
    target_mz: float | None
    untargeted_family_mz: float | None
    targeted_area: float | None
    untargeted_area: float | None
    raw_area_ratio: float | None
    boundary_delta_start_min: float | None
    boundary_delta_end_min: float | None
    targeted_region_verdict: str
    untargeted_region_verdict: str
    targeted_local_mixture_verdict: str
    untargeted_local_mixture_verdict: str
    mismatch_reason: str


@dataclass(frozen=True)
class TargetedAudit:
    sample: str
    target_label: str
    candidate_id: str
    area: float | None
    baseline_area: float | None
    area_uncertainty: float | None
    uncertainty_fraction: float | None
    baseline_fraction: float | None


@dataclass(frozen=True)
class AlignmentIntegrationAudit:
    family_id: str
    sample: str
    area: float | None
    baseline_area: float | None
    area_uncertainty: float | None
    uncertainty_fraction: float | None
    baseline_fraction: float | None


@dataclass(frozen=True)
class AreaIntegrationRow:
    sample: str
    target_label: str
    role: str
    targeted_candidate_id: str
    untargeted_family_id: str
    target_mz: float | None
    untargeted_family_mz: float | None
    targeted_area: float | None
    untargeted_area: float | None
    raw_area_ratio: float | None
    targeted_baseline_area: float | None
    untargeted_baseline_area: float | None
    baseline_area_ratio: float | None
    targeted_uncertainty_fraction: float | None
    untargeted_uncertainty_fraction: float | None
    targeted_baseline_fraction: float | None
    untargeted_baseline_fraction: float | None
    boundary_delta_start_min: float | None
    boundary_delta_end_min: float | None
    boundary_alternative_area_ratio: float | None
    targeted_region_verdict: str
    untargeted_region_verdict: str
    targeted_local_mixture_verdict: str
    untargeted_local_mixture_verdict: str
    evidence_spine_mismatch_reason: str
    integration_bucket: str
    integration_reason: str


@dataclass(frozen=True)
class AreaIntegrationSummary:
    rows_checked: int
    bucket_counts: str
    missing_alignment_match_count: int
    integration_context_incomplete_count: int
    unexplained_area_mismatch_count: int


@dataclass(frozen=True)
class AreaIntegrationUncertaintyResult:
    summary: AreaIntegrationSummary
    rows: tuple[AreaIntegrationRow, ...]


def run_area_integration_uncertainty_audit(
    *,
    evidence_spine_rows_tsv: Path,
    targeted_peak_candidates_tsv: Path,
    targeted_boundaries_tsv: Path,
    alignment_integration_audit_tsv: Path,
    output_dir: Path,
) -> tuple[AreaIntegrationUncertaintyOutputs, AreaIntegrationUncertaintyResult]:
    evidence_rows = _read_evidence_rows(evidence_spine_rows_tsv)
    targeted_audits = _read_targeted_audits(targeted_peak_candidates_tsv)
    boundary_alternatives = _read_boundary_alternatives(targeted_boundaries_tsv)
    alignment_audits = _read_alignment_integration_audits(
        alignment_integration_audit_tsv
    )
    rows = tuple(
        _build_row(
            evidence,
            targeted_audits=targeted_audits,
            boundary_alternatives=boundary_alternatives,
            alignment_audits=alignment_audits,
        )
        for evidence in evidence_rows
    )
    result = AreaIntegrationUncertaintyResult(
        summary=_summarize(rows),
        rows=rows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = AreaIntegrationUncertaintyOutputs(
        summary_tsv=output_dir / "area_integration_uncertainty_summary.tsv",
        rows_tsv=output_dir / "area_integration_uncertainty_rows.tsv",
        json_path=output_dir / "area_integration_uncertainty.json",
        markdown_path=output_dir / "area_integration_uncertainty.md",
    )
    _write_outputs(outputs, result)
    return outputs, result


def _read_evidence_rows(path: Path) -> tuple[EvidenceRow, ...]:
    rows = _read_required_tsv(
        path,
        (
            "sample",
            "target_label",
            "role",
            "targeted_candidate_id",
            "untargeted_family_id",
            "target_mz",
            "untargeted_family_mz",
            "targeted_area",
            "untargeted_area",
            "area_ratio_untargeted_to_targeted",
            "boundary_delta_start_min",
            "boundary_delta_end_min",
            "targeted_region_verdict",
            "untargeted_region_verdict",
            "targeted_local_mixture_verdict",
            "untargeted_local_mixture_verdict",
            "mismatch_reason",
        ),
    )
    return tuple(
        EvidenceRow(
            sample=row["sample"],
            target_label=row["target_label"],
            role=row["role"],
            targeted_candidate_id=row["targeted_candidate_id"],
            untargeted_family_id=row["untargeted_family_id"],
            target_mz=_optional_float(row["target_mz"]),
            untargeted_family_mz=_optional_float(row["untargeted_family_mz"]),
            targeted_area=_optional_float(row["targeted_area"]),
            untargeted_area=_optional_float(row["untargeted_area"]),
            raw_area_ratio=_optional_float(row["area_ratio_untargeted_to_targeted"]),
            boundary_delta_start_min=_optional_float(
                row["boundary_delta_start_min"]
            ),
            boundary_delta_end_min=_optional_float(row["boundary_delta_end_min"]),
            targeted_region_verdict=row["targeted_region_verdict"],
            untargeted_region_verdict=row["untargeted_region_verdict"],
            targeted_local_mixture_verdict=row["targeted_local_mixture_verdict"],
            untargeted_local_mixture_verdict=row[
                "untargeted_local_mixture_verdict"
            ],
            mismatch_reason=row["mismatch_reason"],
        )
        for row in rows
    )


def _read_targeted_audits(path: Path) -> dict[tuple[str, str, str], TargetedAudit]:
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "candidate_id",
            "selected",
            "area_raw_counts_seconds",
            "area_baseline_corrected",
            "area_uncertainty",
        ),
    )
    audits: dict[tuple[str, str, str], TargetedAudit] = {}
    for row in rows:
        if _bool_value(row["selected"]) is not True:
            continue
        area = _optional_float(row["area_raw_counts_seconds"])
        baseline_area = _optional_float(row["area_baseline_corrected"])
        uncertainty = _optional_float(row["area_uncertainty"])
        key = (row["sample_name"], row["target_label"], row["candidate_id"])
        audits[key] = TargetedAudit(
            sample=row["sample_name"],
            target_label=row["target_label"],
            candidate_id=row["candidate_id"],
            area=area,
            baseline_area=baseline_area,
            area_uncertainty=uncertainty,
            uncertainty_fraction=_ratio(uncertainty, area),
            baseline_fraction=_ratio(baseline_area, area),
        )
    return audits


def _read_boundary_alternatives(path: Path) -> dict[tuple[str, str, str], float | None]:
    rows = _read_required_tsv(
        path,
        (
            "sample_name",
            "target_label",
            "candidate_id",
            "selected_candidate",
            "boundary_audit_top",
            "area_ratio_vs_candidate_interval",
            "is_candidate_interval",
        ),
    )
    values: dict[tuple[str, str, str], float | None] = {}
    for row in rows:
        if _bool_value(row["selected_candidate"]) is not True:
            continue
        if _bool_value(row["boundary_audit_top"]) is not True:
            continue
        key = (row["sample_name"], row["target_label"], row["candidate_id"])
        values.setdefault(key, _optional_float(row["area_ratio_vs_candidate_interval"]))
    return values


def _read_alignment_integration_audits(
    path: Path,
) -> dict[tuple[str, str], AlignmentIntegrationAudit]:
    rows = _read_required_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "area",
            "area_baseline_corrected",
            "area_uncertainty",
            "uncertainty_fraction",
            "baseline_fraction",
        ),
    )
    audits: dict[tuple[str, str], AlignmentIntegrationAudit] = {}
    for row in rows:
        key = (row["feature_family_id"], row["sample_stem"])
        audits[key] = AlignmentIntegrationAudit(
            family_id=row["feature_family_id"],
            sample=row["sample_stem"],
            area=_optional_float(row["area"]),
            baseline_area=_optional_float(row["area_baseline_corrected"]),
            area_uncertainty=_optional_float(row["area_uncertainty"]),
            uncertainty_fraction=_optional_float(row["uncertainty_fraction"]),
            baseline_fraction=_optional_float(row["baseline_fraction"]),
        )
    return audits


def _build_row(
    evidence: EvidenceRow,
    *,
    targeted_audits: Mapping[tuple[str, str, str], TargetedAudit],
    boundary_alternatives: Mapping[tuple[str, str, str], float | None],
    alignment_audits: Mapping[tuple[str, str], AlignmentIntegrationAudit],
) -> AreaIntegrationRow:
    targeted = targeted_audits.get(
        (evidence.sample, evidence.target_label, evidence.targeted_candidate_id)
    )
    alignment = (
        None
        if not evidence.untargeted_family_id
        else alignment_audits.get((evidence.untargeted_family_id, evidence.sample))
    )
    boundary_alternative_ratio = boundary_alternatives.get(
        (evidence.sample, evidence.target_label, evidence.targeted_candidate_id)
    )
    baseline_ratio = _ratio(
        None if alignment is None else alignment.baseline_area,
        None if targeted is None else targeted.baseline_area,
    )
    bucket, reason = _classify(
        evidence,
        targeted=targeted,
        alignment=alignment,
        baseline_ratio=baseline_ratio,
        boundary_alternative_ratio=boundary_alternative_ratio,
    )
    return AreaIntegrationRow(
        sample=evidence.sample,
        target_label=evidence.target_label,
        role=evidence.role,
        targeted_candidate_id=evidence.targeted_candidate_id,
        untargeted_family_id=evidence.untargeted_family_id,
        target_mz=evidence.target_mz,
        untargeted_family_mz=evidence.untargeted_family_mz,
        targeted_area=evidence.targeted_area,
        untargeted_area=evidence.untargeted_area,
        raw_area_ratio=evidence.raw_area_ratio,
        targeted_baseline_area=None if targeted is None else targeted.baseline_area,
        untargeted_baseline_area=None if alignment is None else alignment.baseline_area,
        baseline_area_ratio=baseline_ratio,
        targeted_uncertainty_fraction=(
            None if targeted is None else targeted.uncertainty_fraction
        ),
        untargeted_uncertainty_fraction=(
            None if alignment is None else alignment.uncertainty_fraction
        ),
        targeted_baseline_fraction=(
            None if targeted is None else targeted.baseline_fraction
        ),
        untargeted_baseline_fraction=(
            None if alignment is None else alignment.baseline_fraction
        ),
        boundary_delta_start_min=evidence.boundary_delta_start_min,
        boundary_delta_end_min=evidence.boundary_delta_end_min,
        boundary_alternative_area_ratio=boundary_alternative_ratio,
        targeted_region_verdict=evidence.targeted_region_verdict,
        untargeted_region_verdict=evidence.untargeted_region_verdict,
        targeted_local_mixture_verdict=evidence.targeted_local_mixture_verdict,
        untargeted_local_mixture_verdict=evidence.untargeted_local_mixture_verdict,
        evidence_spine_mismatch_reason=evidence.mismatch_reason,
        integration_bucket=bucket,
        integration_reason=reason,
    )


def _classify(
    evidence: EvidenceRow,
    *,
    targeted: TargetedAudit | None,
    alignment: AlignmentIntegrationAudit | None,
    baseline_ratio: float | None,
    boundary_alternative_ratio: float | None,
) -> tuple[str, str]:
    if not evidence.untargeted_family_id:
        return "missing_alignment_match", "No matched untargeted family."
    if (
        targeted is None
        or alignment is None
        or evidence.raw_area_ratio is None
        or targeted.baseline_area is None
        or alignment.baseline_area is None
    ):
        return "integration_context_incomplete", "Required integration fields missing."

    raw_consistent = _ratio_in_window(evidence.raw_area_ratio)
    label_mismatch = _label_mismatch(evidence)
    if raw_consistent and not label_mismatch and not _has_high_uncertainty(
        targeted,
        alignment,
    ):
        return (
            "area_consistent_low_uncertainty",
            "Raw area ratio is consistent and uncertainty is low.",
        )
    if raw_consistent and label_mismatch:
        return (
            "label_only_mismatch",
            "RT/area are consistent but diagnostic region labels differ.",
        )
    if not raw_consistent and baseline_ratio is not None and _ratio_in_window(
        baseline_ratio
    ):
        return (
            "baseline_explains_raw_mismatch",
            "Baseline-corrected area ratio falls inside the consistency window.",
        )
    if _boundary_sensitive(evidence, boundary_alternative_ratio):
        return (
            "boundary_sensitive",
            "Boundary delta or selected top-boundary area ratio is outside limits.",
        )
    if _has_high_uncertainty(targeted, alignment):
        return (
            "high_uncertainty",
            "Area uncertainty or baseline fraction is outside limits.",
        )
    return (
        "unexplained_area_mismatch",
        "Area mismatch remains after available integration audit checks.",
    )


def _label_mismatch(evidence: EvidenceRow) -> bool:
    return _nonempty_diff(
        evidence.targeted_region_verdict,
        evidence.untargeted_region_verdict,
    ) or _nonempty_diff(
        evidence.targeted_local_mixture_verdict,
        evidence.untargeted_local_mixture_verdict,
    )


def _nonempty_diff(left: str, right: str) -> bool:
    return bool(left and right and left != right)


def _ratio_in_window(value: float) -> bool:
    return RAW_AREA_RATIO_MIN <= value <= RAW_AREA_RATIO_MAX


def _boundary_sensitive(
    evidence: EvidenceRow,
    boundary_alternative_ratio: float | None,
) -> bool:
    if _abs_gt(evidence.boundary_delta_start_min, BOUNDARY_DELTA_CONCERN_MIN):
        return True
    if _abs_gt(evidence.boundary_delta_end_min, BOUNDARY_DELTA_CONCERN_MIN):
        return True
    return boundary_alternative_ratio is not None and not _ratio_in_window(
        boundary_alternative_ratio
    )


def _has_high_uncertainty(
    targeted: TargetedAudit,
    alignment: AlignmentIntegrationAudit,
) -> bool:
    return (
        _gt(targeted.uncertainty_fraction, HIGH_UNCERTAINTY_FRACTION)
        or _gt(alignment.uncertainty_fraction, HIGH_UNCERTAINTY_FRACTION)
        or _lt(targeted.baseline_fraction, LOW_BASELINE_FRACTION)
        or _lt(alignment.baseline_fraction, LOW_BASELINE_FRACTION)
    )


def _summarize(rows: Sequence[AreaIntegrationRow]) -> AreaIntegrationSummary:
    counter = Counter(row.integration_bucket for row in rows)
    return AreaIntegrationSummary(
        rows_checked=len(rows),
        bucket_counts=_format_counter(counter),
        missing_alignment_match_count=counter["missing_alignment_match"],
        integration_context_incomplete_count=counter[
            "integration_context_incomplete"
        ],
        unexplained_area_mismatch_count=counter["unexplained_area_mismatch"],
    )


def _write_outputs(
    outputs: AreaIntegrationUncertaintyOutputs,
    result: AreaIntegrationUncertaintyResult,
) -> None:
    _write_tsv(outputs.summary_tsv, SUMMARY_FIELDS, (asdict(result.summary),))
    _write_tsv(outputs.rows_tsv, ROW_FIELDS, tuple(asdict(row) for row in result.rows))
    with outputs.json_path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(result), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    _write_markdown(outputs.markdown_path, result)


def _write_markdown(
    path: Path,
    result: AreaIntegrationUncertaintyResult,
) -> None:
    lines = [
        "# Area Integration Uncertainty Audit",
        "",
        f"- Rows checked: {result.summary.rows_checked}",
        f"- Bucket counts: {result.summary.bucket_counts}",
        "",
        "## Review Rows",
        "",
    ]
    for row in result.rows[:25]:
        lines.append(
            "- "
            f"{row.sample} / {row.target_label}: {row.integration_bucket} "
            f"(family={row.untargeted_family_id or 'NA'}, "
            f"raw_ratio={_fmt(row.raw_area_ratio)}, "
            f"baseline_ratio={_fmt(row.baseline_area_ratio)})"
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
        description="Classify targeted/untargeted area mismatch by integration audit.",
    )
    parser.add_argument("--evidence-spine-rows-tsv", type=Path, required=True)
    parser.add_argument("--targeted-peak-candidates-tsv", type=Path, required=True)
    parser.add_argument("--targeted-boundaries-tsv", type=Path, required=True)
    parser.add_argument("--alignment-integration-audit-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs, _result = run_area_integration_uncertainty_audit(
            evidence_spine_rows_tsv=args.evidence_spine_rows_tsv,
            targeted_peak_candidates_tsv=args.targeted_peak_candidates_tsv,
            targeted_boundaries_tsv=args.targeted_boundaries_tsv,
            alignment_integration_audit_tsv=args.alignment_integration_audit_tsv,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Summary TSV: {outputs.summary_tsv}")
    print(f"Rows TSV: {outputs.rows_tsv}")
    print(f"Uncertainty JSON: {outputs.json_path}")
    print(f"Uncertainty report: {outputs.markdown_path}")
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


def _bool_value(value: object) -> bool | None:
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _gt(value: float | None, threshold: float) -> bool:
    return value is not None and value > threshold


def _lt(value: float | None, threshold: float) -> bool:
    return value is not None and value < threshold


def _abs_gt(value: float | None, threshold: float) -> bool:
    return value is not None and abs(value) > threshold


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

