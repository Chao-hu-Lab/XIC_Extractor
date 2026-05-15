"""Decision report for single-dR primary matrix gate candidates."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from xic_extractor.alignment.identity_gates import (
    EXTREME_BACKFILL_REASON,
    WEAK_SEED_BACKFILL_REASON,
    DetectedSeedRef,
    SeedQualitySummary,
    classify_single_dr_backfill_dependency,
    is_dr_neutral_loss_tag,
    lookup_seed_candidate,
    summarize_detected_seed_quality,
)

_REVIEW_REQUIRED_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "detected_count",
    "include_in_primary_matrix",
)
_CELLS_REQUIRED_COLUMNS = ("feature_family_id", "sample_stem", "status")

_SUMMARY_COLUMNS = ("metric", "value")
_FAMILY_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "risk_classification",
    "rt_context",
    "include_in_primary_matrix",
    "q_detected",
    "q_rescue",
    "sample_count",
    "rescue_fraction",
    "duplicate_assigned_count",
    "row_flags",
    "seed_quality_status",
    "min_evidence_score",
    "min_seed_event_count",
    "max_abs_nl_ppm",
    "min_scan_support_score",
    "missing_detected_candidate_count",
    "targeted_istd_labels",
    "targeted_istd_statuses",
    "family_center_mz",
    "family_center_rt",
    "family_product_mz",
    "family_observed_neutral_loss_da",
)
_DETECTED_CELL_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "status",
    "source_candidate_id",
    "area",
    "apex_rt",
    "seed_candidate_joined",
    "evidence_score",
    "seed_event_count",
    "neutral_loss_mass_error_ppm",
    "ms1_scan_support_score",
)
_GATE_CANDIDATE_COLUMNS = (
    "gate_candidate_id",
    "rule_description",
    "affected_primary_rows",
    "affected_istd_rows",
    "affected_known_target_rows",
    "affected_rows_by_reason",
    "false_positive_risk_reason",
    "recommended_action",
    "recommendation_reason",
)

_EXTREME_GATE_ID = "dr_extreme_backfill_dependency"
_WEAK_SEED_GATE_ID = "dr_weak_seed_backfill_dependency"
_DUPLICATE_GATE_ID = "dr_duplicate_rescue_pressure"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = build_decision_report(
            alignment_dir=args.alignment_dir,
            discovery_batch_index=args.discovery_batch_index,
            rt_normalization_families_tsv=args.rt_normalization_families_tsv,
            targeted_istd_benchmark_json=args.targeted_istd_benchmark_json,
        )
        write_outputs(args.output_dir, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"single-dR gate decision report: {args.output_dir}")
    return 0


def build_decision_report(
    *,
    alignment_dir: Path,
    discovery_batch_index: Path | None = None,
    rt_normalization_families_tsv: Path | None = None,
    targeted_istd_benchmark_json: Path | None = None,
) -> dict[str, Any]:
    review_rows = _read_tsv(
        alignment_dir / "alignment_review.tsv",
        required_columns=_REVIEW_REQUIRED_COLUMNS,
    )
    cell_rows = _read_tsv(
        alignment_dir / "alignment_cells.tsv",
        required_columns=_CELLS_REQUIRED_COLUMNS,
    )
    cells_by_family = _cells_by_family(cell_rows)
    sample_order = _sample_order(cell_rows)
    discovery = _load_discovery_candidates(discovery_batch_index)
    rt_context = _load_rt_context(rt_normalization_families_tsv)
    benchmark = _load_targeted_istd_context(targeted_istd_benchmark_json)

    families: list[dict[str, Any]] = []
    detected_cells: list[dict[str, Any]] = []
    for review_row in review_rows:
        if not _is_single_dr_primary(review_row):
            continue
        family_id = review_row["feature_family_id"]
        family_cells = cells_by_family.get(family_id, ())
        seed_quality = _seed_quality(
            family_cells,
            discovery=discovery,
        )
        family_rt_context = rt_context.get(family_id, "")
        family_istd = benchmark["families"].get(family_id, {})
        family = _classify_family(
            review_row,
            family_cells,
            sample_count=len(sample_order),
            seed_quality=seed_quality,
            rt_context=family_rt_context,
            targeted_istd=family_istd,
        )
        families.append(family)
        detected_cells.extend(
            _detected_cell_rows(family_cells, discovery=discovery),
        )

    families.sort(
        key=lambda row: (
            _risk_sort_key(str(row["risk_classification"])),
            -int(row["q_rescue"]),
            str(row["feature_family_id"]),
        ),
    )
    detected_cells.sort(
        key=lambda row: (
            str(row["feature_family_id"]),
            str(row["sample_stem"]),
        ),
    )
    gate_candidates = _gate_candidates(families)
    summary = _summary_rows(
        alignment_dir=alignment_dir,
        sample_count=len(sample_order),
        families=families,
        gate_candidates=gate_candidates,
    )
    return {
        "alignment_dir": str(alignment_dir),
        "sample_count": len(sample_order),
        "enrichment": {
            "discovery_batch_index": (
                str(discovery_batch_index)
                if discovery_batch_index is not None
                else "not_provided"
            ),
            "rt_normalization_families_tsv": (
                str(rt_normalization_families_tsv)
                if rt_normalization_families_tsv is not None
                else "not_provided"
            ),
            "targeted_istd_benchmark_json": (
                str(targeted_istd_benchmark_json)
                if targeted_istd_benchmark_json is not None
                else "not_provided"
            ),
            "discovery_status": discovery["status"],
            "rt_context_status": rt_context["status"],
            "targeted_istd_status": benchmark["status"],
        },
        "summary": summary,
        "families": families,
        "detected_cells": detected_cells,
        "gate_candidates": gate_candidates,
    }


def write_outputs(output_dir: Path, result: Mapping[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_tsv(
        output_dir / "single_dr_gate_decision_summary.tsv",
        result["summary"],
        fieldnames=_SUMMARY_COLUMNS,
    )
    _write_tsv(
        output_dir / "single_dr_gate_decision_families.tsv",
        result["families"],
        fieldnames=_FAMILY_COLUMNS,
    )
    _write_tsv(
        output_dir / "single_dr_gate_decision_detected_cells.tsv",
        result["detected_cells"],
        fieldnames=_DETECTED_CELL_COLUMNS,
    )
    _write_tsv(
        output_dir / "single_dr_gate_candidates.tsv",
        result["gate_candidates"],
        fieldnames=_GATE_CANDIDATE_COLUMNS,
    )
    (output_dir / "single_dr_gate_decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "single_dr_gate_decision.md").write_text(
        _markdown(result),
        encoding="utf-8",
    )


def _classify_family(
    review_row: Mapping[str, str],
    cells: tuple[dict[str, str], ...],
    *,
    sample_count: int,
    seed_quality: Mapping[str, Any],
    rt_context: str,
    targeted_istd: Mapping[str, Any],
) -> dict[str, Any]:
    q_detected = _int_value(
        review_row.get("quantifiable_detected_count", "")
        or review_row.get("detected_count", ""),
    )
    q_rescue = _int_value(
        review_row.get("quantifiable_rescue_count", "")
        or review_row.get("accepted_rescue_count", ""),
    )
    denominator = sample_count or len(cells) or 1
    rescue_fraction = q_rescue / denominator
    duplicate_count = _int_value(review_row.get("duplicate_assigned_count", ""))
    row_flags = review_row.get("row_flags", "")
    dependency = classify_single_dr_backfill_dependency(
        neutral_loss_tag=review_row.get("neutral_loss_tag", ""),
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=denominator,
        seed_quality=seed_quality,
    )

    if dependency == EXTREME_BACKFILL_REASON:
        classification = "risky_extreme_backfill"
    elif dependency == WEAK_SEED_BACKFILL_REASON:
        classification = "risky_weak_seed_backfill"
    elif _is_duplicate_rescue_watch(
        q_detected=q_detected,
        q_rescue=q_rescue,
        rescue_fraction=rescue_fraction,
        duplicate_count=duplicate_count,
        row_flags=row_flags,
    ):
        classification = "watch_duplicate_rescue"
    elif q_detected >= 5:
        classification = "strong"
    else:
        classification = "weak"

    labels = targeted_istd.get("target_labels", ())
    statuses = targeted_istd.get("statuses", ())
    return {
        "feature_family_id": review_row["feature_family_id"],
        "neutral_loss_tag": review_row.get("neutral_loss_tag", ""),
        "risk_classification": classification,
        "rt_context": rt_context or "",
        "include_in_primary_matrix": True,
        "q_detected": q_detected,
        "q_rescue": q_rescue,
        "sample_count": denominator,
        "rescue_fraction": f"{rescue_fraction:.4f}",
        "duplicate_assigned_count": duplicate_count,
        "row_flags": row_flags,
        "seed_quality_status": seed_quality.status,
        "min_evidence_score": _optional_metric(seed_quality.min_evidence_score),
        "min_seed_event_count": _optional_metric(seed_quality.min_seed_event_count),
        "max_abs_nl_ppm": _optional_metric(seed_quality.max_abs_nl_ppm),
        "min_scan_support_score": _optional_metric(
            seed_quality.min_scan_support_score,
        ),
        "missing_detected_candidate_count": (
            seed_quality.missing_detected_candidate_count
            if seed_quality.available
            else ""
        ),
        "targeted_istd_labels": ";".join(labels),
        "targeted_istd_statuses": ";".join(statuses),
        "family_center_mz": review_row.get("family_center_mz", ""),
        "family_center_rt": review_row.get("family_center_rt", ""),
        "family_product_mz": review_row.get("family_product_mz", ""),
        "family_observed_neutral_loss_da": review_row.get(
            "family_observed_neutral_loss_da",
            "",
        ),
    }


def _is_duplicate_rescue_watch(
    *,
    q_detected: int,
    q_rescue: int,
    rescue_fraction: float,
    duplicate_count: int,
    row_flags: str,
) -> bool:
    flags = set(_split_list(row_flags))
    duplicate_pressure = duplicate_count > 0 or "duplicate_claim_pressure" in flags
    rescue_heavy = rescue_fraction >= 0.50 or "rescue_heavy" in flags
    low_detected_support = q_detected <= 5
    return (
        duplicate_pressure
        and rescue_heavy
        and low_detected_support
        and q_rescue > 0
    )


def _seed_quality(
    cells: tuple[dict[str, str], ...],
    *,
    discovery: Mapping[str, Any],
) -> SeedQualitySummary:
    detected_cells = [cell for cell in cells if cell.get("status") == "detected"]
    if discovery["status"] == "not_provided":
        return summarize_detected_seed_quality(
            (),
            None,
            enrichment_available=False,
        )

    return summarize_detected_seed_quality(
        tuple(
            DetectedSeedRef(
                sample_stem=cell.get("sample_stem", ""),
                source_candidate_id=cell.get("source_candidate_id", ""),
            )
            for cell in detected_cells
        ),
        discovery["candidates"],
        enrichment_available=True,
    )


def _detected_cell_rows(
    cells: tuple[dict[str, str], ...],
    *,
    discovery: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in cells:
        if cell.get("status") != "detected":
            continue
        quality = (
            _lookup_candidate_quality(cell, discovery["candidates"])
            if discovery["status"] != "not_provided"
            else None
        )
        rows.append(
            {
                "feature_family_id": cell.get("feature_family_id", ""),
                "sample_stem": cell.get("sample_stem", ""),
                "status": cell.get("status", ""),
                "source_candidate_id": cell.get("source_candidate_id", ""),
                "area": cell.get("area", ""),
                "apex_rt": cell.get("apex_rt", ""),
                "seed_candidate_joined": quality is not None,
                "evidence_score": _quality_value(quality, "evidence_score"),
                "seed_event_count": _quality_value(quality, "seed_event_count"),
                "neutral_loss_mass_error_ppm": _quality_value(
                    quality,
                    "neutral_loss_mass_error_ppm",
                ),
                "ms1_scan_support_score": _quality_value(
                    quality,
                    "ms1_scan_support_score",
                ),
            },
        )
    return rows


def _gate_candidates(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _gate_candidate(
            gate_candidate_id=_EXTREME_GATE_ID,
            rule_description=(
                "single dR primary rows with q_detected <= 2 and "
                "rescue_fraction >= 0.70"
            ),
            families=[
                row
                for row in families
                if row["risk_classification"] == "risky_extreme_backfill"
            ],
            default_action="implement",
            false_positive_risk_reason=(
                "Most quantification comes from owner backfill while original "
                "neutral-loss detected support is at most two samples."
            ),
        ),
        _gate_candidate(
            gate_candidate_id=_WEAK_SEED_GATE_ID,
            rule_description=(
                "single dR primary rows with q_detected <= 3, "
                "rescue_fraction >= 0.60, and weak detected seed quality"
            ),
            families=[
                row
                for row in families
                if row["risk_classification"] == "risky_weak_seed_backfill"
            ],
            default_action="implement",
            false_positive_risk_reason=(
                "Backfill-heavy rows start from low-quality or unjoined "
                "detected seed evidence."
            ),
        ),
        _gate_candidate(
            gate_candidate_id=_DUPLICATE_GATE_ID,
            rule_description=(
                "single dR primary rows with duplicate pressure, rescue-heavy "
                "support, and low detected support"
            ),
            families=[
                row
                for row in families
                if row["risk_classification"] == "watch_duplicate_rescue"
            ],
            default_action="keep_warning",
            false_positive_risk_reason=(
                "Duplicate pressure plus rescue-heavy support can indicate a "
                "family still competing for row identity."
            ),
        ),
    ]


def _gate_candidate(
    *,
    gate_candidate_id: str,
    rule_description: str,
    families: list[dict[str, Any]],
    default_action: str,
    false_positive_risk_reason: str,
) -> dict[str, Any]:
    affected_istd_rows = sum(1 for row in families if row["targeted_istd_labels"])
    affected_known_target_rows = affected_istd_rows
    if not families:
        recommended_action = "reject"
        reason = "No current primary rows match this rule."
    elif affected_istd_rows:
        recommended_action = "keep_warning"
        reason = (
            "The rule affects targeted ISTD-selected families, so it must not "
            "be auto-implemented without manual review."
        )
    else:
        recommended_action = default_action
        reason = _recommendation_reason(default_action)
    return {
        "gate_candidate_id": gate_candidate_id,
        "rule_description": rule_description,
        "affected_primary_rows": len(families),
        "affected_istd_rows": affected_istd_rows,
        "affected_known_target_rows": affected_known_target_rows,
        "affected_rows_by_reason": _affected_rows_by_reason(families),
        "false_positive_risk_reason": false_positive_risk_reason,
        "recommended_action": recommended_action,
        "recommendation_reason": reason,
    }


def _recommendation_reason(default_action: str) -> str:
    if default_action == "implement":
        return (
            "No targeted ISTD-selected family is affected; the rule is narrow "
            "enough to move into the next production gate candidate set."
        )
    if default_action == "keep_warning":
        return (
            "The signal is a useful review warning but is not yet strict enough "
            "for automatic demotion."
        )
    return "The rule is not currently actionable."


def _affected_rows_by_reason(families: list[dict[str, Any]]) -> str:
    counts = Counter(str(row["risk_classification"]) for row in families)
    return ";".join(f"{key}={counts[key]}" for key in sorted(counts))


def _summary_rows(
    *,
    alignment_dir: Path,
    sample_count: int,
    families: list[dict[str, Any]],
    gate_candidates: list[dict[str, Any]],
) -> list[dict[str, str]]:
    class_counts = Counter(str(row["risk_classification"]) for row in families)
    action_counts = Counter(
        str(row["recommended_action"]) for row in gate_candidates
    )
    rows = [
        {"metric": "alignment_dir", "value": str(alignment_dir)},
        {"metric": "sample_count", "value": str(sample_count)},
        {"metric": "single_dr_primary_rows", "value": str(len(families))},
    ]
    for key in (
        "strong",
        "weak",
        "risky_extreme_backfill",
        "risky_weak_seed_backfill",
        "watch_duplicate_rescue",
    ):
        rows.append(
            {
                "metric": f"{key}_rows",
                "value": str(class_counts.get(key, 0)),
            },
        )
    for action in ("implement", "keep_warning", "reject"):
        rows.append(
            {
                "metric": f"gate_candidates_{action}",
                "value": str(action_counts.get(action, 0)),
            },
        )
    return rows


def _load_discovery_candidates(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "not_provided", "candidates": {}}
    rows, fieldnames = _read_delimited_rows(path)
    missing = [
        column
        for column in ("sample_stem", "candidate_csv")
        if column not in fieldnames
    ]
    if missing:
        raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
    candidates: dict[tuple[str, str], dict[str, float | str]] = {}
    for _, row in rows:
        sample = _machine_text(row.get("sample_stem", ""))
        candidate_csv = _machine_text(row.get("candidate_csv", ""))
        if not sample or not candidate_csv:
            continue
        candidate_path = _resolve_artifact_path(path.parent, candidate_csv)
        candidate_rows, candidate_fieldnames = _read_delimited_rows(candidate_path)
        if "candidate_id" not in candidate_fieldnames:
            raise ValueError(
                f"{candidate_path}: missing required columns: candidate_id"
            )
        for _, candidate_row in candidate_rows:
            candidate_id = _machine_text(candidate_row.get("candidate_id", ""))
            if not candidate_id:
                continue
            quality = {
                "sample_stem": _machine_text(
                    candidate_row.get("sample_stem", sample),
                )
                or sample,
                "candidate_id": candidate_id,
                "evidence_score": _float_or_none(
                    candidate_row.get("evidence_score", ""),
                ),
                "seed_event_count": _float_or_none(
                    candidate_row.get("seed_event_count", ""),
                ),
                "neutral_loss_mass_error_ppm": _float_or_none(
                    candidate_row.get("neutral_loss_mass_error_ppm", ""),
                ),
                "ms1_scan_support_score": _float_or_none(
                    candidate_row.get("ms1_scan_support_score", ""),
                ),
            }
            candidate_sample = str(quality["sample_stem"])
            candidates[(candidate_sample, candidate_id)] = quality
            candidates[("", candidate_id)] = quality
    return {"status": "provided", "candidates": candidates}


def _load_rt_context(path: Path | None) -> dict[str, str]:
    if path is None:
        return {"status": "not_provided"}
    rows = _read_tsv(path, required_columns=("feature_family_id",))
    contexts: dict[str, str] = {"status": "provided"}
    for row in rows:
        family_id = row.get("feature_family_id", "")
        if not family_id:
            continue
        text = ";".join(
            (
                row.get("rt_context", ""),
                row.get("normalized_rt_support", ""),
                row.get("irt_support", ""),
                row.get("rt_warping_effect", ""),
            ),
        ).lower()
        if "worsen" in text or "context_rt_worsened" in text:
            contexts[family_id] = "context_rt_worsened"
    return contexts


def _load_targeted_istd_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "not_provided", "families": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    summaries = payload.get("summaries", ())
    if not isinstance(summaries, Sequence) or isinstance(summaries, (str, bytes)):
        raise ValueError(f"{path}: summaries must be a list")
    by_family: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"target_labels": set(), "statuses": set()},
    )
    for item in summaries:
        if not isinstance(item, Mapping):
            continue
        target = str(item.get("target_label", ""))
        status = str(item.get("status", "UNKNOWN") or "UNKNOWN")
        family_ids = set(_string_list(item.get("primary_feature_ids", ())))
        selected = str(item.get("selected_feature_id", "") or "")
        if selected:
            family_ids.add(selected)
        for family_id in family_ids:
            by_family[family_id]["target_labels"].add(target)
            by_family[family_id]["statuses"].add(status)
    return {
        "status": "provided",
        "families": {
            family_id: {
                "target_labels": tuple(sorted(data["target_labels"])),
                "statuses": tuple(sorted(data["statuses"])),
            }
            for family_id, data in by_family.items()
        },
    }


def _lookup_candidate_quality(
    cell: Mapping[str, str],
    candidates: Mapping[tuple[str, str], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    return lookup_seed_candidate(
        DetectedSeedRef(
            sample_stem=cell.get("sample_stem", ""),
            source_candidate_id=cell.get("source_candidate_id", ""),
        ),
        candidates,
    )


def _is_single_dr_primary(row: Mapping[str, str]) -> bool:
    if not _is_true(row.get("include_in_primary_matrix", "")):
        return False
    return is_dr_neutral_loss_tag(row.get("neutral_loss_tag", ""))


def _cells_by_family(
    rows: tuple[dict[str, str], ...],
) -> dict[str, tuple[dict[str, str], ...]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["feature_family_id"]].append(row)
    return {feature_id: tuple(items) for feature_id, items in grouped.items()}


def _sample_order(rows: tuple[dict[str, str], ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        sample = row.get("sample_stem", "")
        if sample and sample not in seen:
            seen.add(sample)
            ordered.append(sample)
    return tuple(ordered)


def _read_tsv(
    path: Path,
    *,
    required_columns: tuple[str, ...],
) -> tuple[dict[str, str], ...]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = tuple(reader.fieldnames or ())
            missing = [
                column for column in required_columns if column not in fieldnames
            ]
            if missing:
                raise ValueError(
                    f"{path}: missing required columns: {', '.join(missing)}"
                )
            return tuple(dict(row) for row in reader)
    except OSError as exc:
        raise ValueError(f"{path}: could not read TSV: {exc}") from exc


def _read_delimited_rows(
    path: Path,
) -> tuple[list[tuple[int, dict[str, str]]], tuple[str, ...]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            return (
                [(index, dict(row)) for index, row in enumerate(reader, start=2)],
                tuple(reader.fieldnames or ()),
            )
    except OSError as exc:
        raise ValueError(f"{path}: could not read table: {exc}") from exc


def _write_tsv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    fieldnames: tuple[str, ...],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _markdown(result: Mapping[str, Any]) -> str:
    summary = {row["metric"]: row["value"] for row in result["summary"]}
    lines = [
        "# Single-dR Production Gate Decision Report",
        "",
        f"- alignment_dir: `{result['alignment_dir']}`",
        f"- sample_count: {result['sample_count']}",
        f"- single_dr_primary_rows: {summary.get('single_dr_primary_rows', '0')}",
        "",
        "## Gate Candidates",
        "",
        (
            "| Candidate | Affected primary rows | ISTD rows | "
            "Recommended action |"
        ),
        "|---|---:|---:|---|",
    ]
    for candidate in result["gate_candidates"]:
        lines.append(
            "| "
            f"{candidate['gate_candidate_id']} | "
            f"{candidate['affected_primary_rows']} | "
            f"{candidate['affected_istd_rows']} | "
            f"{candidate['recommended_action']} |"
        )
    lines.extend(
        [
            "",
            "## Top Families",
            "",
            "| Family | Class | q_detected | q_rescue | rescue_fraction | ISTD |",
            "|---|---|---:|---:|---:|---|",
        ],
    )
    for family in result["families"][:30]:
        lines.append(
            "| "
            f"{family['feature_family_id']} | "
            f"{family['risk_classification']} | "
            f"{family['q_detected']} | "
            f"{family['q_rescue']} | "
            f"{family['rescue_fraction']} | "
            f"{family['targeted_istd_labels']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _risk_sort_key(classification: str) -> int:
    order = {
        "risky_extreme_backfill": 0,
        "risky_weak_seed_backfill": 1,
        "watch_duplicate_rescue": 2,
        "weak": 3,
        "strong": 4,
    }
    return order.get(classification, 99)


def _quality_value(
    quality: Mapping[str, Any] | None,
    key: str,
) -> Any:
    if quality is None:
        return ""
    value = quality.get(key)
    return "" if value is None else value


def _optional_metric(value: float | None) -> float | str:
    return value if value is not None else ""


def _split_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part for part in _split_list(value) if part)
    if isinstance(value, Sequence):
        return tuple(str(part) for part in value if str(part))
    return ()


def _float_or_none(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _int_value(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def _resolve_artifact_path(parent: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else parent / path


def _machine_text(value: str) -> str:
    if len(value) >= 2 and value[0] == "'" and value[1] in ("=", "+", "-", "@"):
        return value[1:]
    return value


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a single-dR production gate decision report.",
    )
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--discovery-batch-index", type=Path)
    parser.add_argument("--rt-normalization-families-tsv", type=Path)
    parser.add_argument("--targeted-istd-benchmark-json", type=Path)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
