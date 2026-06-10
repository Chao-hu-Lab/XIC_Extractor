from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics import standard_peak_backfill_productization as cli
from xic_extractor.alignment.tsv_writer import (
    ALIGNMENT_CELLS_COLUMNS,
    ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS,
    ALIGNMENT_REVIEW_COLUMNS,
)
from xic_extractor.diagnostics.shadow_production_projection import (
    SHADOW_PRODUCTION_PROJECTION_COLUMNS,
)


def test_standard_peak_productization_applies_matrix_and_synced_gallery(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path)
    output_dir = tmp_path / "out"

    assert (
        cli.main(
            [
                "--shadow-projection-cells-tsv",
                str(fixture["shadow"]),
                "--alignment-matrix-tsv",
                str(fixture["matrix"]),
                "--alignment-matrix-identity-tsv",
                str(fixture["identity"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-standard-peak-productization",
                "--write-gallery",
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--backfill-seed-audit-tsv",
                str(fixture["seeds"]),
                "--shift-aware-standard-peak-gate-tsv",
                str(fixture["gate"]),
            ],
        )
        == 0
    )

    summary = json.loads(
        (
            output_dir / "standard_peak_backfill_productization_summary.json"
        ).read_text(encoding="utf-8"),
    )
    assert summary["status"] == "pass"
    assert summary["selected_activation_row_count"] == "1"
    assert summary["skipped_non_standard_reason_count"] == "1"
    assert summary["activation_application_status"] == "applied"
    assert summary["matrix_cells_written"] == "1"
    assert summary["activation_value_delta_written_count"] == "1"
    assert summary["product_behavior_changed"] == "TRUE"

    matrix_rows = _read_tsv(output_dir / "activated_matrix" / "alignment_matrix.tsv")
    identity_rows = _read_tsv(
        output_dir / "activated_matrix" / "alignment_matrix_identity.tsv",
    )
    matrix_index_by_hypothesis = {
        row["peak_hypothesis_id"]: int(row["matrix_row_index"]) - 1
        for row in identity_rows
    }
    assert matrix_rows[matrix_index_by_hypothesis["FAM_STD"]]["S2"] == "100"
    assert matrix_rows[matrix_index_by_hypothesis["FAM_NON"]]["S2"] == ""

    delta = _read_tsv(output_dir / "activated_matrix" / "activation_value_delta.tsv")
    assert len(delta) == 1
    assert delta[0]["feature_family_id"] == "FAM_STD"
    assert delta[0]["matrix_value_effect"] == "written"

    gallery_groups = _read_tsv(
        output_dir
        / "reconciliation_gallery"
        / "backfill_evidence_reconciliation_groups.tsv",
    )
    by_family = {row["feature_family_id"]: row for row in gallery_groups}
    assert by_family["FAM_STD"]["product_behavior_state"] == (
        "product_primary_backfilled"
    )
    assert by_family["FAM_STD"]["top_product_reason"] == (
        "activation_value_delta_written"
    )
    assert by_family["FAM_NON"]["product_behavior_state"] == (
        "product_rescued_context_only"
    )
    assert by_family["FAM_NON"]["reconciliation_class"] == (
        "product_rejects_and_evidence_blocks"
    )


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    matrix = tmp_path / "alignment_matrix.tsv"
    identity = tmp_path / "alignment_matrix_identity.tsv"
    review = tmp_path / "alignment_review.tsv"
    cells = tmp_path / "alignment_backfill_cell_evidence.tsv"
    seeds = tmp_path / "alignment_owner_backfill_seed_audit.tsv"
    gate = tmp_path / "shift_aware_standard_peak_gate_calibration.tsv"
    shadow = tmp_path / "shadow_production_projection_cells.tsv"

    _write_tsv(
        matrix,
        [
            {"Mz": "300.3", "RT": "9.3", "S1": "10", "S2": ""},
            {"Mz": "301.3", "RT": "9.4", "S1": "20", "S2": ""},
        ],
        ("Mz", "RT", "S1", "S2"),
    )
    _write_tsv(
        identity,
        [
            _identity_row("1", "300.3", "9.3", "FAM_STD"),
            _identity_row("2", "301.3", "9.4", "FAM_NON"),
        ],
        (
            "matrix_row_index",
            "Mz",
            "RT",
            "peak_hypothesis_id",
            "row_identity_basis",
            "source_feature_family_ids",
        ),
    )
    _write_tsv(
        review,
        [
            _review_row("FAM_STD", "300.3", "9.3"),
            _review_row("FAM_NON", "301.3", "9.4"),
        ],
        ALIGNMENT_REVIEW_COLUMNS,
    )
    _write_tsv(
        cells,
        [
            _cell_row("FAM_STD", "S1", "detected"),
            _cell_row("FAM_STD", "S2", "rescued"),
            _cell_row("FAM_NON", "S1", "detected"),
            _cell_row("FAM_NON", "S2", "rescued"),
        ],
        ALIGNMENT_CELLS_COLUMNS,
    )
    _write_tsv(
        seeds,
        [_seed_row("FAM_STD", "S2"), _seed_row("FAM_NON", "S2")],
        ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS,
    )
    _write_tsv(
        gate,
        [_gate_row("FAM_STD", supported=True), _gate_row("FAM_NON", supported=False)],
        (
            "feature_family_id",
            "standard_peak_gate_call",
            "standard_peak_gate_reasons",
            "standard_peak_gate_blockers",
            "calibration_outcome",
            "min_shape_r_after_best_shift",
            "max_abs_shift_sec",
        ),
    )
    _write_tsv(
        shadow,
        [
            _shadow_row("FAM_STD", "S2", "100", standard=True),
            _shadow_row("FAM_NON", "S2", "200", standard=False),
        ],
        SHADOW_PRODUCTION_PROJECTION_COLUMNS,
    )
    return {
        "matrix": matrix,
        "identity": identity,
        "review": review,
        "cells": cells,
        "seeds": seeds,
        "gate": gate,
        "shadow": shadow,
    }


def _identity_row(
    index: str,
    mz: str,
    rt: str,
    family: str,
) -> dict[str, str]:
    return {
        "matrix_row_index": index,
        "Mz": mz,
        "RT": rt,
        "peak_hypothesis_id": family,
        "row_identity_basis": "no_split_peak_hypothesis",
        "source_feature_family_ids": family,
    }


def _review_row(family: str, mz: str, rt: str) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_REVIEW_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "family_center_mz": mz,
            "family_center_rt": rt,
            "detected_count": "1",
            "accepted_cell_count": "2",
            "accepted_rescue_count": "1",
            "quantifiable_detected_count": "1",
            "quantifiable_rescue_count": "1",
            "identity_decision": "provisional_discovery",
            "identity_confidence": "review_only",
            "primary_evidence": "owner_backfill_context",
            "identity_reason": "owner_backfill_context",
            "include_in_primary_matrix": "FALSE",
            "row_flags": "single_detected_seed;provisional_retention_candidate",
            "reason": "fixture",
        },
    )
    return row


def _cell_row(family: str, sample: str, status: str) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_CELLS_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "sample_stem": sample,
            "status": status,
            "area": "1000.0",
            "primary_matrix_area": "1000.0" if status == "detected" else "",
            "primary_matrix_area_source": "detected" if status == "detected" else "",
            "apex_rt": "10.0000",
            "peak_start_rt": "9.9000",
            "peak_end_rt": "10.1000",
            "rt_delta_sec": "0",
            "trace_quality": "ok",
            "scan_support_score": "0.9",
            "gap_fill_state": "owner_backfill" if status == "rescued" else "observed",
            "gap_fill_reason": "owner_backfill" if status == "rescued" else "",
            "reason": "fixture",
        },
    )
    return row


def _seed_row(family: str, sample: str) -> dict[str, str]:
    row = _blank_row(ALIGNMENT_OWNER_BACKFILL_SEED_AUDIT_COLUMNS)
    row.update(
        {
            "feature_family_id": family,
            "group_hypothesis_id": f"{family}::group",
            "public_family_id": family,
            "group_construction_role": "single_detected_seed",
            "group_delivery_role": "review",
            "group_membership_source": "owner_family",
            "sample_stem": sample,
            "status": "rescued",
            "area": "1000.0",
            "apex_rt": "10.0000",
            "family_center_mz": "300.3",
            "family_center_rt": "10.0000",
            "backfill_seed_mz": "300.3",
            "backfill_seed_rt": "10.0000",
            "backfill_request_rt_min": "9.0000",
            "backfill_request_rt_max": "11.0000",
            "backfill_request_ppm": "20",
            "reason": "fixture",
        },
    )
    return row


def _gate_row(family: str, *, supported: bool) -> dict[str, str]:
    return {
        "feature_family_id": family,
        "standard_peak_gate_call": "standard_peak_gate_supported"
        if supported
        else "standard_peak_gate_blocked",
        "standard_peak_gate_reasons": "shift_aware_same_pattern_supported",
        "standard_peak_gate_blockers": ""
        if supported
        else "family_overlay_gaussian_smoothed_peak_not_standard",
        "calibration_outcome": "true_positive" if supported else "true_negative",
        "min_shape_r_after_best_shift": "0.99",
        "max_abs_shift_sec": "1.0",
    }


def _shadow_row(
    family: str,
    sample: str,
    value: str,
    *,
    standard: bool,
) -> dict[str, str]:
    row = _blank_row(SHADOW_PRODUCTION_PROJECTION_COLUMNS)
    reason = (
        "MS1:product_authorized:supportive:trace_constellation:"
        "feature_family_sample:manual_standard_peak_gate_authorized | "
        "same_peak_reason:shift_aware_standard_peak_gate_supported"
        if standard
        else "MS1:product_authorized:supportive:trace_constellation:"
        "feature_family_sample:other"
    )
    row.update(
        {
            "schema_version": "shadow_production_projection_v1",
            "peak_hypothesis_id": family,
            "feature_family_id": family,
            "seed_group_id": (
                f"seed::{family}::mz=300.3::rt=10.0000::"
                "window=9.0000-11.0000::ppm=20"
            ),
            "sample_stem": sample,
            "current_raw_status": "rescued",
            "current_production_status": "review_rescue",
            "current_matrix_written": "FALSE",
            "shadow_decision": "accept",
            "shadow_reasons": (
                "same_peak_reason:shift_aware_standard_peak_gate_supported"
                if standard
                else "same_peak_reason:other"
            ),
            "projected_matrix_written": "TRUE",
            "projected_matrix_value": value,
            "product_authority_chain": reason,
            "shadow_projection_row_sha256": "b" * 64,
            "evidence_gate_status": "visual_support",
            "support_components": "seed_request_provenance",
            "hard_blockers": "",
            "overlay_verdict": "ms1_shape_supports_family_backfill"
            if standard
            else "review_required_neighboring_ms1_interference",
        },
    )
    return row


def _blank_row(columns: tuple[str, ...]) -> dict[str, str]:
    return {column: "" for column in columns}


def _write_tsv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: tuple[str, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
