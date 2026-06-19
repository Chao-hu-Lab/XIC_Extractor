import csv
import json
from pathlib import Path

from scripts.check_productization_state import (
    DEFAULT_AUTHORITY_MANIFEST,
    DEFAULT_CONTROL_PLANE,
    DEFAULT_HANDOFF,
    DEFAULT_SCHEMA,
    DEFAULT_STATUS_INDEX,
    check_productization_state,
)


def test_productization_state_index_accepts_current_artifacts() -> None:
    assert check_productization_state() == []


def test_status_schema_matches_index_header() -> None:
    schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    header, rows = _read_tsv(DEFAULT_STATUS_INDEX)

    assert header == schema["required_status_index_columns"]
    assert {row["lane_id"] for row in rows} == set(schema["required_lane_ids"])
    assert len(rows) == len(schema["required_lane_ids"])


def test_only_current_backfill_scope_has_writer_authority() -> None:
    _, rows = _read_tsv(DEFAULT_STATUS_INDEX)
    authority_rows = [row for row in rows if row["write_authority"] == "TRUE"]

    assert [row["lane_id"] for row in authority_rows] == [
        "backfill_current_write_ready_scope"
    ]
    authority = authority_rows[0]
    assert authority["product_authority_scope"] == "backfill_policy_write_ready_rows"
    assert authority["row_count"] == "511"
    assert authority["may_touch_matrix"] == "TRUE"


def test_peak_choice_lockbox_status_points_to_shadow_automation_design() -> None:
    _, rows = _read_tsv(DEFAULT_STATUS_INDEX)
    row = next(
        item for item in rows if item["lane_id"] == "peak_choice_truth_lockbox_v1"
    )

    assert (
        row["current_artifact"]
        == "docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json"
    )
    assert row["public_surface"] == "lockbox_shadow_automation_experiment_v1"
    assert row["product_effect"] == "shadow_only_contract_adapter_manifest"
    assert row["row_count"] == "72"
    assert "shadow_scoring_contract_adapter_v1_ready" in row["notes"]
    assert "53 owner-clean Gaussian15 cases as non-authoritative accept challenges" in (
        row["notes"]
    )
    assert "6 manual negative controls as reject hard stops" in row["notes"]
    assert row["write_authority"] == "FALSE"


def test_control_plane_lockbox_shadow_adapter_route_is_current() -> None:
    text = DEFAULT_CONTROL_PLANE.read_text(encoding="utf-8")
    section = _section(
        text,
        "### 2026-06-19 - lockbox_shadow_automation_experiment_v1",
        "### 2026-06-18 - productization_status_index_v1",
    )

    assert "shadow_scoring_contract_adapter_v1_ready" in section
    assert "define_production_acceptance_manifest_v1" in section
    assert "ProductionAcceptanceManifest v1" in section
    assert "implement the shadow-only scoring experiment" not in section
    assert "No ProductWriter, matrix, workbook" in section
    assert "Phase 2 `ProductionAcceptanceManifest v1`, expected-diff" not in section
    assert "define `ProductionAcceptanceManifest v1` in a separate goal" not in section
    assert "Phase 3 QuantMatrixVersion Activation" in section


def test_control_plane_production_acceptance_manifest_contract_is_current() -> None:
    text = DEFAULT_CONTROL_PLANE.read_text(encoding="utf-8")
    section = _section(
        text,
        "### 2026-06-19 - ProductionAcceptanceManifest v1 schema/checker",
        "### 2026-06-19 - lockbox_shadow_automation_experiment_v1",
    )

    assert "production_acceptance_manifest_schema.v1.json" in section
    assert "scripts/check_production_acceptance_manifest.py" in section
    assert "peak_hypothesis_id + sample_stem" in section
    assert "feature_family_id is context/provenance only" in section
    assert "No ProductWriter, matrix, workbook" in section
    assert "Phase 3 QuantMatrixVersion Activation" in section


def test_control_plane_quant_matrix_version_activation_is_current() -> None:
    text = DEFAULT_CONTROL_PLANE.read_text(encoding="utf-8")
    section = _section(
        text,
        "### 2026-06-19 - QuantMatrixVersion Activation v1",
        "### 2026-06-19 - ProductionAcceptanceManifest v1 schema/checker",
    )

    assert "quant_matrix_version_schema.v1.json" in section
    assert "scripts/build_quant_matrix_version.py" in section
    assert "quant_matrix.tsv" in section
    assert "cell_provenance.tsv" in section
    assert "row_summary.tsv" in section
    assert "expected-diff" in section
    assert "detected-only view is reconstructable" in section
    assert "No ProductWriter default extraction" in section
    assert "Phase 4 Gallery/Report Alignment" in section


def test_control_plane_quant_matrix_review_report_is_current() -> None:
    text = DEFAULT_CONTROL_PLANE.read_text(encoding="utf-8")
    section = _section(
        text,
        "### 2026-06-19 - QuantMatrixVersion Review Report v1",
        "### 2026-06-19 - QuantMatrixVersion Activation v1",
    )

    assert "quant_matrix_review_report_schema.v1.json" in section
    assert "scripts/build_quant_matrix_version_report.py" in section
    assert "quant_matrix_review_rows.tsv" in section
    assert "quant_matrix_review_summary.json" in section
    assert "quant_matrix_review_report.html" in section
    assert "review-only report adapter" in section
    assert "No ProductWriter default extraction" in section
    assert "QuantMatrix Promotion Readiness v1" in section


def test_control_plane_quant_matrix_promotion_readiness_is_current() -> None:
    text = DEFAULT_CONTROL_PLANE.read_text(encoding="utf-8")
    section = _section(
        text,
        "### 2026-06-19 - QuantMatrix Promotion Readiness v1",
        "### 2026-06-19 - QuantMatrixVersion Review Report v1",
    )

    assert "quant_matrix_promotion_readiness_schema.v1.json" in section
    assert "scripts/check_quant_matrix_promotion_readiness.py" in section
    assert "quant_matrix_promotion_readiness_summary.json" in section
    assert "quant_matrix_promotion_readiness_checks.tsv" in section
    assert "contract-ready/science-inconclusive" in section
    assert "focused tests prove the gate behavior only" in section
    assert "artifact-bound passing large-cohort" in section
    assert "No ProductWriter default extraction" in section
    assert "broad Backfill authority changed" in section
    assert "Do not run RAW/85RAW unless" in section
    assert "an active goal names that tier" in section


def test_control_plane_quant_matrix_validation_packet_is_current() -> None:
    text = DEFAULT_CONTROL_PLANE.read_text(encoding="utf-8")
    section = _section(
        text,
        "### 2026-06-19 - QuantMatrix Promotion Validation Packet v1",
        "### 2026-06-19 - QuantMatrix Promotion Readiness v1",
    )

    assert "quant_matrix_validation_evidence_schema.v1.json" in section
    assert "scripts/build_quant_matrix_promotion_validation_packet.py" in section
    assert "quant_matrix_validation_evidence_v1.json" in section
    assert "quant_matrix_validation_evidence_rows.tsv" in section
    assert "readiness_integration_fixture" in section
    assert "large-cohort evidence is `pass`" in section
    assert "heldout-oracle evidence is `pass`" in section
    assert "downstream-impact evidence is `missing`" in section
    assert "`production_ready=false`" in section
    assert "`may_promote_default_quant_matrix=false`" in section
    assert "No ProductWriter default extraction" in section
    assert "Do not treat this packet as `production_ready`" in section


def test_control_plane_current_summary_routes_to_promotion_packet_v2() -> None:
    text = DEFAULT_CONTROL_PLANE.read_text(encoding="utf-8")
    summary = _section(
        text,
        "Lockbox Shadow Scoring Contract Adapter v1 turns",
        "Missing-Overlay Evidence Recovery v1",
    )

    assert "Phase 2" in summary
    assert "`ProductionAcceptanceManifest v1` is now defined" in summary
    assert "Phase 3" in summary
    assert "Phase 3 `QuantMatrixVersion Activation`" in summary
    assert "is now implemented as an explicit manifest-driven activation" in summary
    assert "Phase 4" in summary
    assert "`Gallery/Report Alignment` is now implemented" in summary
    assert "Phase 5" in summary
    assert "`Validation/Promotion Readiness` is now" in summary
    assert "contract correctness" in summary
    assert "scientific confidence" in summary
    assert "`QuantMatrix Promotion Validation Packet v1`" in summary
    assert "`contract_ready_science_inconclusive`" in summary
    assert "`may_promote_default_quant_matrix=false`" in summary
    assert "Phase 6" in summary
    assert "tier/status strings" in summary
    assert "Phase 7" in summary
    assert "current real\n511-cell `QuantMatrixVersion` bundle" in summary
    assert "Phase 8" in summary
    assert "`QuantMatrix Promotion Packet v2`" in summary
    assert "`production_ready_candidate_packet`" in summary
    assert "`production_ready=true`" in summary
    assert "`may_promote_default_quant_matrix=true`" in summary
    assert "candidate promotion\npacket only" in summary
    assert "ProductWriter default extraction" in summary
    assert "default matrix authority" in summary
    assert "later expected-diff activation gate" in summary
    assert "Phase 9" in summary
    assert "default activation dry-run expected-diff gate" in summary
    assert "511 expected, 511 written, and 0\nunused expected-diff rows" in summary
    assert "writes no default matrix files" in summary
    assert "changes no\nProductWriter/default behavior" in summary
    assert "large-cohort" in summary
    assert "heldout-oracle evidence" in summary
    assert "`Validation/Promotion Readiness`" in summary
    assert "`QuantMatrixVersion Activation`" in summary
    assert "Next checkpoint is Phase 2" not in summary
    assert "Next checkpoint is Phase 3" not in summary
    assert "Next checkpoint is Phase 4" not in summary
    assert "Next checkpoint is Phase 5" not in summary


def test_specs_readme_lists_quant_matrix_version_schema() -> None:
    text = (Path(__file__).parents[1] / "docs/superpowers/specs/README.md").read_text(
        encoding="utf-8",
    )

    assert "quant_matrix_version_schema.v1.json" in text
    assert "cell_provenance" in text
    assert "row_summary" in text
    assert "expected-diff" in text


def test_specs_readme_lists_quant_matrix_review_report_schema() -> None:
    text = (Path(__file__).parents[1] / "docs/superpowers/specs/README.md").read_text(
        encoding="utf-8",
    )

    assert "quant_matrix_review_report_schema.v1.json" in text
    assert "review rows" in text
    assert "summary JSON" in text
    assert "HTML report" in text
    assert "does not grant ProductWriter or matrix authority" in text


def test_specs_readme_lists_quant_matrix_promotion_readiness_schema() -> None:
    text = (Path(__file__).parents[1] / "docs/superpowers/specs/README.md").read_text(
        encoding="utf-8",
    )

    assert "quant_matrix_promotion_readiness_schema.v1.json" in text
    assert "readiness summary JSON" in text
    assert "checks" in text
    assert "contract correctness from scientific confidence" in text
    assert "focused tests and 8RAW smoke evidence cannot claim" in text
    assert "artifact-bound large-cohort" in text


def test_specs_readme_lists_quant_matrix_validation_evidence_schema() -> None:
    text = (Path(__file__).parents[1] / "docs/superpowers/specs/README.md").read_text(
        encoding="utf-8",
    )

    assert "quant_matrix_validation_evidence_schema.v1.json" in text
    assert "artifact-bound" in text
    assert "source artifact paths/hashes" in text
    assert "`write_authority=false`" in text


def test_specs_readme_lists_quant_matrix_promotion_packet_v2_schema() -> None:
    text = (Path(__file__).parents[1] / "docs/superpowers/specs/README.md").read_text(
        encoding="utf-8",
    )

    assert "quant_matrix_promotion_packet_v2_schema.v1.json" in text
    assert "`production_ready_candidate_packet`" in text
    assert "large-cohort" in text
    assert "heldout-oracle" in text
    assert "real downstream-impact smoke" in text
    assert "default matrix authority unchanged" in text


def test_specs_readme_lists_quant_matrix_default_activation_dry_run_schema() -> None:
    text = (Path(__file__).parents[1] / "docs/superpowers/specs/README.md").read_text(
        encoding="utf-8",
    )

    assert "quant_matrix_default_activation_dry_run_schema.v1.json" in text
    assert "temporary directory" in text
    assert "expected-diff summary hashes" in text
    assert "comparison/summary artifacts" in text
    assert "ProductWriter defaults and default matrix outputs remain unchanged" in text


def test_checker_rejects_parked_broad_backfill_authority(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "broad_backfill_autowrite",
        {
            "write_authority": "TRUE",
            "product_authority_scope": "backfill_policy_write_ready_rows",
            "may_touch_matrix": "TRUE",
        },
    )

    problems = _check_with_index(mutated)

    assert any("parked lane grants authority" in problem for problem in problems)
    assert any(
        "broad_backfill_autowrite must stay parked" in problem
        for problem in problems
    )


def test_checker_rejects_review_truth_or_recovery_authority(tmp_path: Path) -> None:
    for lane_id in (
        "review_packet_workflow_v1",
        "peak_choice_truth_lockbox_v1",
        "missing_overlay_evidence_recovery_v1",
    ):
        mutated = _mutated_index(
            tmp_path,
            lane_id,
            {
                "write_authority": "TRUE",
                "product_authority_scope": "backfill_policy_write_ready_rows",
                "may_touch_matrix": "TRUE",
            },
        )

        problems = _check_with_index(mutated)

        assert any("lane grants authority" in problem for problem in problems)


def test_checker_rejects_non_writer_scope_without_write_flag(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "review_packet_workflow_v1",
        {"product_authority_scope": "backfill_policy_write_ready_rows"},
    )

    problems = _check_with_index(mutated)

    assert any("non-writer row has authority scope" in problem for problem in problems)


def test_checker_rejects_non_writer_product_output_changes(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "peak_choice_truth_lockbox_v1",
        {
            "may_change_workbook": "TRUE",
            "may_change_selected_peak": "TRUE",
            "may_change_selected_area": "TRUE",
            "may_change_counted_detection": "TRUE",
        },
    )

    problems = _check_with_index(mutated)

    assert any(
        "non-writer row changes product output" in problem
        for problem in problems
    )


def test_checker_rejects_blank_doc_anchors(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "mechanical_adjudication_contract_v1",
        {"handoff_anchor": "", "control_plane_anchor": ""},
    )

    problems = _check_with_index(mutated)

    assert any("handoff anchor is required" in problem for problem in problems)
    assert any("control-plane anchor is required" in problem for problem in problems)


def test_checker_rejects_artifact_hash_drift(tmp_path: Path) -> None:
    mutated = _mutated_index(
        tmp_path,
        "mechanical_adjudication_contract_v1",
        {"artifact_sha256": "0" * 64},
    )

    problems = _check_with_index(mutated)

    assert any("artifact_sha256 mismatch" in problem for problem in problems)


def _check_with_index(path: Path) -> list[str]:
    return check_productization_state(
        schema_path=DEFAULT_SCHEMA,
        status_index_path=path,
        authority_manifest_path=DEFAULT_AUTHORITY_MANIFEST,
        handoff_path=DEFAULT_HANDOFF,
        control_plane_path=DEFAULT_CONTROL_PLANE,
    )


def _mutated_index(
    tmp_path: Path,
    lane_id: str,
    updates: dict[str, str],
) -> Path:
    header, rows = _read_tsv(DEFAULT_STATUS_INDEX)
    for row in rows:
        if row["lane_id"] == lane_id:
            row.update(updates)
            break
    else:
        raise AssertionError(f"lane not found: {lane_id}")
    output = tmp_path / f"{lane_id}.tsv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    return output


def _read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def _section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]
