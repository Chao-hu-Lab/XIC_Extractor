"""Build the Peak-Choice Truth Lockbox v1 artifacts.

This is a read-only truth-acquisition helper. It samples existing adjudication,
review, oracle, and manual-negative artifacts into a lockbox for independent
human labels. It does not modify ProductWriter, matrices, workbooks, selected
peaks, areas, or counted detections.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.check_productization_state import artifact_sha256
from tools.diagnostics.docs_policy import MECHANICAL_ADJUDICATION_INDEX_REL

ROOT = Path(__file__).resolve().parents[1]

INDEX_PATH = ROOT / MECHANICAL_ADJUDICATION_INDEX_REL
REVIEW_QUEUE_PATH = ROOT / "docs/superpowers/validation/review_queue_v1.tsv"
SOURCE_AUDIT_PATH = (
    ROOT
    / "output/productization_realdata_seed_guard_85raw_20260617"
    / "low_height_low_scan_clean_activation_scope_audit"
    / "activation_high_signal_clean_scope_audit.tsv"
)
MANUAL_NEGATIVE_PATH = (
    ROOT
    / "docs/superpowers/fixtures/"
    / "target_pair_chrom_morphology_area_ratio_manual_oracle_v1.tsv"
)
FAILED_ORACLE_PATHS = [
    ROOT
    / "output/productization_realdata_seed_guard_85raw_20260617"
    / "heldout_trace_reintegration_oracle_all_stability_family"
    / "heldout_oracle_results.tsv",
    ROOT
    / "output/productization_realdata_seed_guard_85raw_20260617"
    / "heldout_trace_reintegration_oracle_apex_delta_clean_probe"
    / "heldout_oracle_results.tsv",
    ROOT
    / "output/productization_realdata_seed_guard_85raw_20260617"
    / "heldout_trace_reintegration_oracle_low_height_bounded_probe_pad005"
    / "heldout_oracle_results.tsv",
    ROOT
    / "output/productization_realdata_seed_guard_85raw_20260617"
    / "heldout_trace_reintegration_oracle_shape_margin_clean_probe"
    / "heldout_oracle_results.tsv",
    ROOT
    / "output/productization_realdata_seed_guard_85raw_20260617"
    / "heldout_trace_reintegration_oracle_width_clean_probe"
    / "heldout_oracle_results.tsv",
]

DEFAULT_OUTPUT_DIR = ROOT / "docs/superpowers/validation"

MANIFEST_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "lockbox_split_id",
    "split_basis",
    "source_stratum",
    "candidate_universe",
    "row_id",
    "family_id",
    "sample_id",
    "analyte",
    "mechanical_decision",
    "evidence_grade",
    "source_write_authority",
    "review_packet_id",
    "candidate_value_if_any",
    "candidate_area",
    "candidate_height",
    "candidate_apex_rt_min",
    "candidate_start_rt_min",
    "candidate_end_rt_min",
    "trace_data_path",
    "overlay_png_path",
    "known_blockers",
    "risk_tags",
    "label_task",
    "required_reviewer_count",
    "truth_label_status",
    "allowed_truth_labels",
    "peak_choice_label_required",
    "area_label_required",
    "source_artifacts",
    "source_hashes",
    "may_touch_matrix",
    "may_grant_product_authority",
    "notes",
]

LABEL_LOG_HEADER = [
    "schema_version",
    "lockbox_case_id",
    "reviewer_id",
    "reviewed_at_utc",
    "peak_choice_label",
    "area_label",
    "area_error_direction",
    "reviewer_confidence",
    "evidence_viewed",
    "round_trip_oracle_used",
    "reviewer_notes",
    "decision_hash",
]

SCHEMA_VERSION = "peak_choice_truth_lockbox_v1"
UNLABELED = "unlabeled"
NO_AUTHORITY = "FALSE"


def build_lockbox(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_rows = _read_tsv(INDEX_PATH)
    review_rows = _read_tsv(REVIEW_QUEUE_PATH)
    audit_by_sha = {
        row["matrix_value_source_row_sha256"]: row
        for row in _read_tsv(SOURCE_AUDIT_PATH)
    }
    index_by_family_sample = {
        (row["family_id"], row["sample_id"]): row for row in index_rows
    }
    source_hashes = {
        "mechanical_adjudication_index": artifact_sha256(INDEX_PATH),
        "review_queue": artifact_sha256(REVIEW_QUEUE_PATH),
        "source_audit": _sha256(SOURCE_AUDIT_PATH),
        "manual_negative_fixture": _sha256(MANUAL_NEGATIVE_PATH),
    }
    rows: list[dict[str, str]] = []
    used_rows: set[str] = set()

    rows.extend(
        _sample_index_rows(
            index_rows,
            audit_by_sha,
            source_hashes,
            source_stratum="approved_write_ready_control",
            count=18,
            predicate=lambda row: row["decision"] == "write_ready",
            used_rows=used_rows,
        )
    )
    rows.extend(
        _sample_review_rows(
            review_rows,
            source_hashes,
            source_stratum="unresolved_high_signal_dirty",
            count=6,
            predicate=lambda row: "height_gte_2000000" in row["known_blockers"],
            used_rows=used_rows,
        )
    )
    rows.extend(
        _sample_review_rows(
            review_rows,
            source_hashes,
            source_stratum="unresolved_low_height",
            count=6,
            predicate=lambda row: "height_lt_2000000" in row["known_blockers"],
            used_rows=used_rows,
        )
    )
    rows.extend(
        _sample_review_rows(
            review_rows,
            source_hashes,
            source_stratum="unresolved_apex_delta",
            count=6,
            predicate=lambda row: "apex_delta_gt_0.15" in row["known_blockers"],
            used_rows=used_rows,
        )
    )
    rows.extend(
        _sample_review_rows(
            review_rows,
            source_hashes,
            source_stratum="unresolved_shape_width_scan",
            count=6,
            predicate=_has_shape_width_scan_risk,
            used_rows=used_rows,
        )
    )
    rows.extend(
        _sample_index_rows(
            index_rows,
            audit_by_sha,
            source_hashes,
            source_stratum="missing_overlay_evidence_gap",
            count=12,
            predicate=lambda row: row["evidence_grade"] == "D",
            used_rows=used_rows,
        )
    )
    rows.extend(
        _sample_failed_oracle_rows(
            source_hashes,
            index_by_family_sample,
            count=12,
            used_rows=used_rows,
        )
    )
    rows.extend(_manual_negative_rows(source_hashes, count=6))

    if len(rows) != 72:
        raise ValueError(f"expected 72 lockbox rows, built {len(rows)}")
    rows = sorted(rows, key=lambda row: row["lockbox_case_id"])

    manifest_path = output_dir / "lockbox_sampling_manifest_v1.tsv"
    label_log_path = output_dir / "reviewer_label_log_v1.tsv"
    summary_path = output_dir / "inter_reviewer_agreement_summary_v1.json"
    _write_tsv(manifest_path, MANIFEST_HEADER, rows)
    _write_tsv(label_log_path, LABEL_LOG_HEADER, [])

    summary = _build_summary(rows, manifest_path, label_log_path)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "manifest_path": manifest_path,
        "label_log_path": label_log_path,
        "summary_path": summary_path,
        "case_count": len(rows),
        "strata": dict(Counter(row["source_stratum"] for row in rows)),
    }


def _sample_index_rows(
    index_rows: list[dict[str, str]],
    audit_by_sha: dict[str, dict[str, str]],
    source_hashes: dict[str, str],
    *,
    source_stratum: str,
    count: int,
    predicate: Any,
    used_rows: set[str],
) -> list[dict[str, str]]:
    candidates = [row for row in index_rows if predicate(row)]
    selected = _select(candidates, count, source_stratum, used_rows)
    return [
        _lockbox_row_from_index(row, audit_by_sha, source_hashes, source_stratum)
        for row in selected
    ]


def _sample_review_rows(
    review_rows: list[dict[str, str]],
    source_hashes: dict[str, str],
    *,
    source_stratum: str,
    count: int,
    predicate: Any,
    used_rows: set[str],
) -> list[dict[str, str]]:
    candidates = [row for row in review_rows if predicate(row)]
    selected = _select(candidates, count, source_stratum, used_rows)
    return [
        _lockbox_row_from_review(row, source_hashes, source_stratum)
        for row in selected
    ]


def _sample_failed_oracle_rows(
    source_hashes: dict[str, str],
    index_by_family_sample: dict[tuple[str, str], dict[str, str]],
    *,
    count: int,
    used_rows: set[str],
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for path in FAILED_ORACLE_PATHS:
        for row in _read_tsv(path):
            if row["oracle_case_status"] == "pass":
                continue
            row = dict(row)
            row["_source_path"] = _relative(path)
            row["_source_hash"] = _sha256(path)
            candidates.append(row)
    selected = _select(candidates, count, "failed_oracle_negative", used_rows)
    return [
        _lockbox_row_from_failed_oracle(row, index_by_family_sample, source_hashes)
        for row in selected
    ]


def _manual_negative_rows(
    source_hashes: dict[str, str],
    *,
    count: int,
) -> list[dict[str, str]]:
    rows = [
        row
        for row in _read_tsv(MANUAL_NEGATIVE_PATH)
        if row["manual_verdict"] in {"wrong_peak", "no_peak"}
    ]
    selected = sorted(
        rows,
        key=lambda row: _stable_digest(
            "manual_negative",
            row["sample_name"],
            row["target_label"],
            row["manual_verdict"],
        ),
    )[:count]
    if len(selected) != count:
        raise ValueError("not enough manual negative rows")
    return [
        _base_lockbox_row(
            source_stratum="manual_wrong_peak_or_no_peak",
            candidate_universe="targeted_manual_negative_fixture",
            row_id="",
            family_id=f"TARGET::{row['target_label']}",
            sample_id=row["sample_name"],
            analyte=row["target_label"],
            mechanical_decision="known_manual_negative",
            evidence_grade="negative_fixture",
            source_write_authority="FALSE",
            review_packet_id="",
            candidate_value_if_any="",
            candidate_area="",
            candidate_height="",
            candidate_apex_rt_min="",
            candidate_start_rt_min="",
            candidate_end_rt_min="",
            trace_data_path="",
            overlay_png_path="",
            known_blockers=row["manual_product_action"],
            risk_tags=row["manual_verdict"],
            label_task="negative_control_confirm_peak_absence_or_wrong_peak",
            area_label_required="FALSE",
            source_artifacts=_relative(MANUAL_NEGATIVE_PATH),
            source_hashes=(
                "manual_negative_fixture="
                + source_hashes["manual_negative_fixture"]
            ),
            notes=row["manual_review_note"],
        )
        for row in selected
    ]


def _lockbox_row_from_index(
    row: dict[str, str],
    audit_by_sha: dict[str, dict[str, str]],
    source_hashes: dict[str, str],
    source_stratum: str,
) -> dict[str, str]:
    audit = audit_by_sha.get(row["source_matrix_value_source_row_sha256"], {})
    label_task = (
        "positive_control_reconfirm_peak_choice_and_area"
        if row["decision"] == "write_ready"
        else "recover_evidence_before_truth_label"
    )
    requires_area = "FALSE" if row["evidence_grade"] == "D" else "TRUE"
    return _base_lockbox_row(
        source_stratum=source_stratum,
        candidate_universe="backfill_candidate_audit_universe_4613",
        row_id=row["row_id"],
        family_id=row["family_id"],
        sample_id=row["sample_id"],
        analyte=row["analyte"],
        mechanical_decision=row["decision"],
        evidence_grade=row["evidence_grade"],
        source_write_authority=row["write_authority"],
        review_packet_id="",
        candidate_value_if_any=row["candidate_value_if_any"],
        candidate_area=audit.get("cell_area", ""),
        candidate_height=audit.get("cell_height", ""),
        candidate_apex_rt_min=audit.get("cell_apex_rt", ""),
        candidate_start_rt_min=audit.get("cell_start_rt", ""),
        candidate_end_rt_min=audit.get("cell_end_rt", ""),
        trace_data_path=audit.get("trace_data_path", ""),
        overlay_png_path=audit.get("projection_overlay_png_path", ""),
        known_blockers=row["blockers"],
        risk_tags=_risk_tags(row["blockers"]),
        label_task=label_task,
        area_label_required=requires_area,
        source_artifacts=(
            f"{_relative(INDEX_PATH)};{_relative(SOURCE_AUDIT_PATH)}"
        ),
        source_hashes=(
            "mechanical_adjudication_index="
            + source_hashes["mechanical_adjudication_index"]
            + ";source_audit="
            + source_hashes["source_audit"]
        ),
        notes=row["next_required_evidence"],
    )


def _lockbox_row_from_review(
    row: dict[str, str],
    source_hashes: dict[str, str],
    source_stratum: str,
) -> dict[str, str]:
    return _base_lockbox_row(
        source_stratum=source_stratum,
        candidate_universe="backfill_review_queue_3015",
        row_id=row["row_id"],
        family_id=row["family_id"],
        sample_id=row["sample_id"],
        analyte=row["analyte"],
        mechanical_decision=row["source_mechanical_decision"],
        evidence_grade=row["source_evidence_grade"],
        source_write_authority="FALSE",
        review_packet_id=row["review_packet_id"],
        candidate_value_if_any=row["candidate_value_if_any"],
        candidate_area=row["candidate_area"],
        candidate_height=row["candidate_height"],
        candidate_apex_rt_min=row["candidate_apex_rt_min"],
        candidate_start_rt_min=row["candidate_start_rt_min"],
        candidate_end_rt_min=row["candidate_end_rt_min"],
        trace_data_path=row["trace_data_path"],
        overlay_png_path=row["overlay_png_path"],
        known_blockers=row["known_blockers"],
        risk_tags=_risk_tags(row["known_blockers"]),
        label_task="independent_peak_choice_and_area_truth_label",
        area_label_required="TRUE",
        source_artifacts=f"{_relative(REVIEW_QUEUE_PATH)};{_relative(INDEX_PATH)}",
        source_hashes=(
            "review_queue="
            + source_hashes["review_queue"]
            + ";mechanical_adjudication_index="
            + source_hashes["mechanical_adjudication_index"]
        ),
        notes=row["why_machine_cannot_auto_write"],
    )


def _lockbox_row_from_failed_oracle(
    row: dict[str, str],
    index_by_family_sample: dict[tuple[str, str], dict[str, str]],
    source_hashes: dict[str, str],
) -> dict[str, str]:
    matched = index_by_family_sample.get(
        (row["feature_family_id"], row["masked_sample"])
    )
    row_id = matched["row_id"] if matched else ""
    source_write_authority = matched["write_authority"] if matched else "FALSE"
    return _base_lockbox_row(
        source_stratum="failed_oracle_negative",
        candidate_universe="failed_heldout_oracle_cases",
        row_id=row_id,
        family_id=row["feature_family_id"],
        sample_id=row["masked_sample"],
        analyte="not_applicable_untargeted_backfill",
        mechanical_decision=matched["decision"] if matched else "oracle_negative_only",
        evidence_grade=matched["evidence_grade"] if matched else "failed_oracle",
        source_write_authority=source_write_authority,
        review_packet_id="",
        candidate_value_if_any="",
        candidate_area=row["observed_area"],
        candidate_height="",
        candidate_apex_rt_min="",
        candidate_start_rt_min=row["observed_start_rt"],
        candidate_end_rt_min=row["observed_end_rt"],
        trace_data_path="",
        overlay_png_path="",
        known_blockers=row["oracle_case_status"],
        risk_tags=f"failed_oracle:{row['oracle_case_status']}",
        label_task="negative_control_relabel_or_explain_oracle_failure",
        area_label_required="TRUE",
        source_artifacts=row["_source_path"],
        source_hashes="oracle_results=" + row["_source_hash"],
        notes=(
            f"{row['source_run_id']};boundary_error_min="
            f"{row['boundary_error_min']};area_relative_error="
            f"{row['area_relative_error']};round_trip_oracle_not_truth"
        ),
    )


def _base_lockbox_row(**values: str) -> dict[str, str]:
    family_id = values["family_id"]
    case_id = _case_id(
        values["source_stratum"],
        family_id,
        values["sample_id"],
        values["row_id"],
        values["analyte"],
    )
    row = {
        "schema_version": SCHEMA_VERSION,
        "lockbox_case_id": case_id,
        "lockbox_split_id": "family_" + _stable_digest("split", family_id)[:16],
        "split_basis": "family_id",
        "required_reviewer_count": "2",
        "truth_label_status": UNLABELED,
        "allowed_truth_labels": (
            "correct_peak;wrong_peak;no_peak;unresolved;"
            "area_acceptable;area_error;boundary_error"
            ";not_assessed;unavailable"
        ),
        "peak_choice_label_required": "TRUE",
        "area_label_required": "TRUE",
        "may_touch_matrix": NO_AUTHORITY,
        "may_grant_product_authority": NO_AUTHORITY,
    }
    row.update(values)
    return {column: row.get(column, "") for column in MANIFEST_HEADER}


def _select(
    rows: list[dict[str, str]],
    count: int,
    source_stratum: str,
    used_rows: set[str],
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    used_families: set[str] = set()
    for row in sorted(rows, key=lambda item: _row_sort_key(source_stratum, item)):
        row_key = (
            row.get("row_id")
            or row.get("oracle_case_id")
            or repr(sorted(row.items()))
        )
        family = row.get("family_id") or row.get("feature_family_id", "")
        if row_key in used_rows or family in used_families:
            continue
        selected.append(row)
        used_rows.add(row_key)
        used_families.add(family)
        if len(selected) == count:
            return selected
    raise ValueError(f"not enough rows for {source_stratum}: {len(selected)}/{count}")


def _row_sort_key(source_stratum: str, row: dict[str, str]) -> str:
    return _stable_digest(
        source_stratum,
        row.get("family_id", row.get("feature_family_id", "")),
        row.get("sample_id", row.get("masked_sample", "")),
        row.get("row_id", row.get("oracle_case_id", "")),
    )


def _has_shape_width_scan_risk(row: dict[str, str]) -> bool:
    blockers = row["known_blockers"]
    return any(
        token in blockers
        for token in (
            "shape_lt_0.95",
            "width_outside_0.30_0.65",
            "scan_count_lt_7",
            "scan_count_lt_10",
        )
    )


def _risk_tags(blockers: str) -> str:
    tokens = blockers.split(";") if blockers else []
    tags = []
    for token in tokens:
        if token.startswith("height_"):
            tags.append("height")
        elif token.startswith("scan_count_"):
            tags.append("scan_count")
        elif token.startswith("apex_delta_"):
            tags.append("apex_delta")
        elif token.startswith("shape_"):
            tags.append("shape")
        elif token.startswith("width_"):
            tags.append("width")
        elif token == "missing_overlay_path":
            tags.append("missing_overlay")
    return ";".join(dict.fromkeys(tags))


def _build_summary(
    rows: list[dict[str, str]],
    manifest_path: Path,
    label_log_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "peak_choice_truth_lockbox_agreement_summary_v1",
        "status": "no_labels_collected",
        "lockbox_manifest": _relative(manifest_path),
        "lockbox_manifest_sha256": artifact_sha256(manifest_path),
        "reviewer_label_log": _relative(label_log_path),
        "reviewer_label_log_sha256": artifact_sha256(label_log_path),
        "case_count": len(rows),
        "labels_collected": 0,
        "required_reviewer_count_per_case": 2,
        "source_strata_counts": dict(Counter(row["source_stratum"] for row in rows)),
        "split_basis": "family_id",
        "round_trip_oracle_truth_policy": "forbidden_as_peak_choice_or_area_truth",
        "agreement_metrics": {
            "peak_choice_percent_agreement": None,
            "area_label_percent_agreement": None,
            "cohen_kappa_peak_choice": None,
            "cohen_kappa_area_label": None,
        },
        "authority": {
            "may_touch_matrix": False,
            "may_grant_product_authority": False,
            "product_writer_consumption": (
                "forbidden_without_later_authority_expected_diff_goal"
            ),
        },
        "next_action": (
            "collect_two_independent_labels_per_case_then_recompute_agreement"
        ),
    }


def _case_id(*parts: str) -> str:
    return "LOCKBOXV1_" + _stable_digest(*parts)[:24]


def _stable_digest(*parts: str) -> str:
    payload = "\x1f".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(
    path: Path,
    header: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for lockbox_sampling_manifest_v1.tsv and label artifacts.",
    )
    args = parser.parse_args(argv)
    result = build_lockbox(args.output_dir)
    print(
        "Peak-choice truth lockbox built: "
        f"{result['case_count']} cases -> {result['manifest_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
