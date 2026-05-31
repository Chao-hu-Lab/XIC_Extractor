import csv
from pathlib import Path

import pytest
from openpyxl import Workbook

from tools.diagnostics.apply_shared_peak_identity_activation import main
from xic_extractor.alignment.shared_peak_identity_explanation import (
    product_activation,
)


def test_activation_application_blanks_wrong_peak_and_writes_auto_activation(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")

    outputs = product_activation.apply_activation_to_alignment_outputs(
        activation_decisions_tsv=fixture["decisions"],
        activation_acceptance_tsv=fixture["acceptance"],
        alignment_matrix_tsv=fixture["matrix"],
        alignment_review_tsv=fixture["review"],
        alignment_cells_tsv=fixture["cells"],
        output_dir=tmp_path / "out",
    )

    matrix_rows = {
        row["feature_family_id"]: row for row in _read_tsv(outputs.matrix_tsv)
    }
    assert matrix_rows["FAM_BLOCK"]["S1"] == "100"
    assert matrix_rows["FAM_BLOCK"]["S2"] == ""
    assert matrix_rows["FAM_ADD"]["S2"] == "300"
    assert matrix_rows["FAM_KEEP"]["S2"] == "777"
    assert matrix_rows["FAM_SPLIT"]["S1"] == "111"
    assert matrix_rows["FAM_SPLIT"]["S2"] == "222"

    review_rows = {
        row["feature_family_id"]: row for row in _read_tsv(outputs.review_tsv)
    }
    assert review_rows["FAM_BLOCK"]["include_in_primary_matrix"] == "TRUE"
    assert review_rows["FAM_BLOCK"]["accepted_cell_count"] == "1"
    assert review_rows["FAM_BLOCK"]["accepted_rescue_count"] == "0"
    assert review_rows["FAM_BLOCK"]["activation_blocked_cell_count"] == "1"
    assert review_rows["FAM_BLOCK"]["activation_rules"] == "wrong_peak_conflict"
    assert review_rows["FAM_ADD"]["include_in_primary_matrix"] == "TRUE"
    assert review_rows["FAM_ADD"]["identity_decision"] == "provisional_discovery"
    assert review_rows["FAM_ADD"]["identity_reason"] == (
        "activation_peak_hypothesis_candidate"
    )
    assert review_rows["FAM_ADD"]["activation_written_cell_count"] == "1"

    cell_rows = {
        (row["feature_family_id"], row["sample_stem"]): row
        for row in _read_tsv(outputs.cells_tsv)
    }
    blocked = cell_rows[("FAM_BLOCK", "S2")]
    assert blocked["activation_status"] == "auto_block"
    assert blocked["activation_matrix_value_effect"] == "blanked"
    activated = cell_rows[("FAM_ADD", "S2")]
    assert activated["activation_status"] == "auto_activate"
    assert activated["activation_peak_hypothesis_id"] == "FAM_ADD::mode_1"
    assert activated["activation_unit_scope"] == "peak_hypothesis"
    assert activated["activation_matrix_value_effect"] == "written"
    kept = cell_rows[("FAM_KEEP", "S2")]
    assert kept["activation_status"] == "auto_activate"
    assert kept["activation_matrix_value_effect"] == "unchanged"
    split_blue = cell_rows[("FAM_SPLIT", "S1")]
    assert split_blue["activation_peak_hypothesis_id"] == "FAM_SPLIT::blue"
    split_green = cell_rows[("FAM_SPLIT", "S2")]
    assert split_green["activation_peak_hypothesis_id"] == "FAM_SPLIT::green"

    summary = _read_tsv(outputs.summary_tsv)[0]
    assert summary["application_status"] == "applied"
    assert summary["activation_output_mode"] == "activated-copy"
    assert summary["matrix_row_identity"] == "feature_family_id"
    assert summary["canonical_row_identity_ready"] == "FALSE"
    assert summary["canonical_row_identity_blockers"] == "formal_output_not_requested"
    assert summary["canonical_row_identity_scope"] == "legacy_feature_family_row"
    assert summary["family_projection_semantics"] == "not_applicable"
    assert summary["legacy_rt_row_context_authority"] == "not_applicable"
    assert summary["all_family_split_science_ready"] == "FALSE"
    assert summary["matrix_cells_blanked"] == "1"
    assert summary["matrix_cells_written"] == "1"
    assert summary["families_added_to_matrix"] == "1"

    delta_rows = {
        (row["feature_family_id"], row["sample_id"]): row
        for row in _read_tsv(outputs.value_delta_tsv)
    }
    blocked_delta = delta_rows[("FAM_BLOCK", "S2")]
    assert blocked_delta["original_matrix_value"] == "200"
    assert blocked_delta["activated_matrix_value"] == ""
    assert blocked_delta["source_cell_area"] == "200"
    assert blocked_delta["matrix_value_effect"] == "blanked"
    assert blocked_delta["value_changed"] == "TRUE"
    written_delta = delta_rows[("FAM_ADD", "S2")]
    assert written_delta["original_matrix_value"] == ""
    assert written_delta["activated_matrix_value"] == "300"
    assert written_delta["candidate_container_id"] == "FAM_ADD"
    assert written_delta["peak_hypothesis_id"] == "FAM_ADD::mode_1"
    assert written_delta["activation_unit_scope"] == "peak_hypothesis"
    assert written_delta["matrix_value_effect"] == "written"
    assert written_delta["value_changed"] == "TRUE"
    kept_delta = delta_rows[("FAM_KEEP", "S2")]
    assert kept_delta["original_matrix_value"] == "777"
    assert kept_delta["activated_matrix_value"] == "777"
    assert kept_delta["source_cell_area"] == "999"
    assert kept_delta["matrix_value_effect"] == "unchanged"
    assert kept_delta["value_changed"] == "FALSE"


def test_activation_application_requires_passing_acceptance(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="fail")

    with pytest.raises(ValueError, match="activation acceptance must pass"):
        product_activation.apply_activation_to_alignment_outputs(
            activation_decisions_tsv=fixture["decisions"],
            activation_acceptance_tsv=fixture["acceptance"],
            alignment_matrix_tsv=fixture["matrix"],
            alignment_review_tsv=fixture["review"],
            alignment_cells_tsv=fixture["cells"],
            output_dir=tmp_path / "out",
        )


def test_activation_application_rejects_auto_activate_without_peak_hypothesis(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")
    _write_tsv(
        fixture["decisions"],
        (
            "feature_family_id",
            "sample_id",
            "activation_status",
            "activation_action",
            "product_label_candidate",
            "product_effect",
            "contract_rule_id",
            "peak_hypothesis_id",
            "activation_unit_scope",
            "activation_reason",
        ),
        [
            {
                "feature_family_id": "FAM_ADD",
                "sample_id": "S2",
                "activation_status": "auto_activate",
                "activation_action": "activate_pass",
                "product_label_candidate": "pass",
                "product_effect": "accept_label_or_rescue",
                "contract_rule_id": (
                    "machine_observed_sufficient_positive_identity"
                ),
                "activation_reason": "missing product unit",
            }
        ],
    )

    with pytest.raises(ValueError, match="auto_activate decisions require"):
        product_activation.apply_activation_to_alignment_outputs(
            activation_decisions_tsv=fixture["decisions"],
            activation_acceptance_tsv=fixture["acceptance"],
            alignment_matrix_tsv=fixture["matrix"],
            alignment_review_tsv=fixture["review"],
            alignment_cells_tsv=fixture["cells"],
            output_dir=tmp_path / "out",
        )


def test_activation_application_formal_mode_writes_product_contract_names(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")

    outputs = product_activation.apply_activation_to_alignment_outputs(
        activation_decisions_tsv=fixture["decisions"],
        activation_acceptance_tsv=fixture["acceptance"],
        alignment_matrix_tsv=fixture["matrix"],
        alignment_review_tsv=fixture["review"],
        alignment_cells_tsv=fixture["cells"],
        output_dir=tmp_path / "formal",
        output_mode="formal",
    )

    assert outputs.matrix_tsv == tmp_path / "formal" / "alignment_matrix.tsv"
    assert outputs.review_tsv == tmp_path / "formal" / "alignment_review.tsv"
    assert outputs.cells_tsv == tmp_path / "formal" / "alignment_cells.tsv"
    assert not (tmp_path / "formal" / "alignment_matrix_activated.tsv").exists()
    assert _header(outputs.matrix_tsv)[:8] == (
        "peak_hypothesis_id",
        "feature_family_id",
        "candidate_container_id",
        "row_identity_basis",
        "legacy_rt_row_context_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
    )
    assert _header(outputs.review_tsv) == _header(fixture["review"])
    assert _header(outputs.cells_tsv) == _header(fixture["cells"])
    matrix_rows = {
        row["peak_hypothesis_id"]: row for row in _read_tsv(outputs.matrix_tsv)
    }
    assert matrix_rows["FAM_ADD::mode_1"]["S2"] == "300"
    assert matrix_rows["FAM_KEEP::mode_1"]["S2"] == "777"
    assert matrix_rows["FAM_SPLIT::blue"]["S1"] == "111"
    assert matrix_rows["FAM_SPLIT::blue"]["S2"] == ""
    assert matrix_rows["FAM_SPLIT::green"]["S1"] == ""
    assert matrix_rows["FAM_SPLIT::green"]["S2"] == "222"
    assert matrix_rows["FAM_BLOCK::family_projection"][
        "row_identity_basis"
    ] == "family_projection_no_split_evidence"
    summary = _read_tsv(outputs.summary_tsv)[0]
    assert summary["activation_output_mode"] == "formal"
    assert summary["matrix_row_identity"] == "peak_hypothesis_id"
    assert summary["canonical_row_identity_ready"] == "FALSE"
    assert summary["canonical_row_identity_blockers"] == "family_projection_present"
    assert summary["canonical_row_identity_scope"] == (
        "partial_peak_hypothesis_with_family_projections"
    )
    assert summary["family_projection_semantics"] == "projection_not_split_proof"
    assert summary["legacy_rt_row_context_authority"] == "not_applicable"
    assert summary["all_family_split_science_ready"] == "FALSE"


def test_activation_application_formal_mode_uses_legacy_rt_row_oracle(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")
    oracle = tmp_path / "legacy_mzmine_oracle.xlsx"
    _write_legacy_rt_row_oracle(oracle, rows=((100.1, 7.1),))

    outputs = product_activation.apply_activation_to_alignment_outputs(
        activation_decisions_tsv=fixture["decisions"],
        activation_acceptance_tsv=fixture["acceptance"],
        alignment_matrix_tsv=fixture["matrix"],
        alignment_review_tsv=fixture["review"],
        alignment_cells_tsv=fixture["cells"],
        output_dir=tmp_path / "formal",
        output_mode="formal",
        legacy_rt_row_oracle_xlsx=oracle,
    )

    matrix_rows = {
        row["peak_hypothesis_id"]: row for row in _read_tsv(outputs.matrix_tsv)
    }
    row = matrix_rows["FAM_BLOCK::family_projection"]
    assert row["feature_family_id"] == "FAM_BLOCK"
    assert row["row_identity_basis"] == "family_projection_no_split_evidence"
    assert row["legacy_rt_row_context_id"] == (
        "mzmine_rtrow_2_mz100.1000_rt7.10min"
    )
    assert row["S1"] == "100"
    assert row["S2"] == ""

    summary = _read_tsv(outputs.summary_tsv)[0]
    assert summary["legacy_rt_row_context_rows"] == "1"
    assert summary["family_projection_rows"] == "1"
    assert summary["legacy_rt_row_context_authority"] == (
        "context_only_not_identity_authority"
    )


def test_activation_application_formal_mode_can_require_peak_hypothesis_identity(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")

    with pytest.raises(ValueError, match="family_projection_present"):
        product_activation.apply_activation_to_alignment_outputs(
            activation_decisions_tsv=fixture["decisions"],
            activation_acceptance_tsv=fixture["acceptance"],
            alignment_matrix_tsv=fixture["matrix"],
            alignment_review_tsv=fixture["review"],
            alignment_cells_tsv=fixture["cells"],
            output_dir=tmp_path / "formal",
            output_mode="formal",
            require_complete_peak_hypothesis_identity=True,
        )


def test_activation_application_formal_mode_keeps_max_area_for_value_conflict(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")
    decisions = _read_tsv(fixture["decisions"])
    for row in decisions:
        if row["feature_family_id"] == "FAM_ADD":
            row["peak_hypothesis_id"] = "FAM_KEEP::mode_1"
    _write_tsv(fixture["decisions"], tuple(decisions[0]), decisions)

    outputs = product_activation.apply_activation_to_alignment_outputs(
        activation_decisions_tsv=fixture["decisions"],
        activation_acceptance_tsv=fixture["acceptance"],
        alignment_matrix_tsv=fixture["matrix"],
        alignment_review_tsv=fixture["review"],
        alignment_cells_tsv=fixture["cells"],
        output_dir=tmp_path / "formal",
        output_mode="formal",
    )

    matrix_rows = {
        row["peak_hypothesis_id"]: row for row in _read_tsv(outputs.matrix_tsv)
    }
    assert matrix_rows["FAM_KEEP::mode_1"]["feature_family_id"] == (
        "FAM_ADD;FAM_KEEP"
    )
    assert matrix_rows["FAM_KEEP::mode_1"]["S2"] == "777"
    summary = _read_tsv(outputs.summary_tsv)[0]
    assert summary["matrix_value_conflict_cells"] == "1"
    assert summary["matrix_value_conflict_policy"] == "max_area_pending_baseline"


def test_activation_application_formal_mode_refuses_source_overwrite(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")

    with pytest.raises(ValueError, match="overwrite source alignment artifacts"):
        product_activation.apply_activation_to_alignment_outputs(
            activation_decisions_tsv=fixture["decisions"],
            activation_acceptance_tsv=fixture["acceptance"],
            alignment_matrix_tsv=fixture["matrix"],
            alignment_review_tsv=fixture["review"],
            alignment_cells_tsv=fixture["cells"],
            output_dir=tmp_path,
            output_mode="formal",
        )


def test_activation_application_cli_writes_product_copies(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")

    assert (
        main(
            [
                "--activation-decisions-tsv",
                str(fixture["decisions"]),
                "--activation-acceptance-tsv",
                str(fixture["acceptance"]),
                "--alignment-matrix-tsv",
                str(fixture["matrix"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    assert (tmp_path / "out" / "alignment_matrix_activated.tsv").exists()
    assert (tmp_path / "out" / "activation_application_summary.tsv").exists()
    assert (tmp_path / "out" / "activation_value_delta.tsv").exists()


def test_activation_application_cli_formal_mode_writes_product_contract_names(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")

    assert (
        main(
            [
                "--activation-decisions-tsv",
                str(fixture["decisions"]),
                "--activation-acceptance-tsv",
                str(fixture["acceptance"]),
                "--alignment-matrix-tsv",
                str(fixture["matrix"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "formal"),
                "--output-mode",
                "formal",
            ]
        )
        == 0
    )
    assert (tmp_path / "formal" / "alignment_matrix.tsv").exists()
    assert (tmp_path / "formal" / "alignment_review.tsv").exists()
    assert (tmp_path / "formal" / "alignment_cells.tsv").exists()
    assert (tmp_path / "formal" / "activation_value_delta.tsv").exists()


def test_activation_application_cli_formal_mode_rejects_legacy_context_as_complete(
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, acceptance_status="pass")
    oracle = tmp_path / "legacy_mzmine_oracle.xlsx"
    _write_legacy_rt_row_oracle(oracle, rows=((100.1, 7.1),))

    assert (
        main(
            [
                "--activation-decisions-tsv",
                str(fixture["decisions"]),
                "--activation-acceptance-tsv",
                str(fixture["acceptance"]),
                "--alignment-matrix-tsv",
                str(fixture["matrix"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "formal"),
                "--output-mode",
                "formal",
                "--require-complete-peak-hypothesis-identity",
                "--legacy-rt-row-oracle-xlsx",
                str(oracle),
            ]
        )
        == 2
    )


def _write_fixture(tmp_path: Path, *, acceptance_status: str) -> dict[str, Path]:
    decisions = tmp_path / "activation_decisions.tsv"
    acceptance = tmp_path / "activation_acceptance.tsv"
    matrix = tmp_path / "alignment_matrix.tsv"
    review = tmp_path / "alignment_review.tsv"
    cells = tmp_path / "alignment_cells.tsv"
    _write_tsv(
        decisions,
        (
            "feature_family_id",
            "sample_id",
            "activation_status",
            "activation_action",
            "product_label_candidate",
            "product_effect",
            "contract_rule_id",
            "peak_hypothesis_id",
            "activation_unit_scope",
            "activation_reason",
        ),
        [
            {
                "feature_family_id": "FAM_BLOCK",
                "sample_id": "S2",
                "activation_status": "auto_block",
                "activation_action": "block_rescue",
                "product_label_candidate": "fail",
                "product_effect": "block_rescue_cell",
                "contract_rule_id": "wrong_peak_conflict",
                "activation_reason": "wrong peak",
            },
            {
                "feature_family_id": "FAM_ADD",
                "sample_id": "S2",
                "activation_status": "auto_activate",
                "activation_action": "activate_pass",
                "product_label_candidate": "pass",
                "product_effect": "accept_label_or_rescue",
                "contract_rule_id": (
                    "machine_observed_sufficient_positive_identity"
                ),
                "peak_hypothesis_id": "FAM_ADD::mode_1",
                "activation_unit_scope": "peak_hypothesis",
                "activation_reason": "machine observed",
            },
            {
                "feature_family_id": "FAM_KEEP",
                "sample_id": "S2",
                "activation_status": "auto_activate",
                "activation_action": "activate_pass",
                "product_label_candidate": "pass",
                "product_effect": "accept_label_or_rescue",
                "contract_rule_id": (
                    "machine_observed_sufficient_positive_identity"
                ),
                "peak_hypothesis_id": "FAM_KEEP::mode_1",
                "activation_unit_scope": "peak_hypothesis",
                "activation_reason": "already accepted",
            },
            {
                "feature_family_id": "FAM_SPLIT",
                "sample_id": "S1",
                "activation_status": "auto_activate",
                "activation_action": "activate_pass",
                "product_label_candidate": "pass",
                "product_effect": "accept_label_or_rescue",
                "contract_rule_id": (
                    "machine_observed_sufficient_positive_identity"
                ),
                "peak_hypothesis_id": "FAM_SPLIT::blue",
                "activation_unit_scope": "peak_hypothesis",
                "activation_reason": "mode split blue",
            },
            {
                "feature_family_id": "FAM_SPLIT",
                "sample_id": "S2",
                "activation_status": "auto_activate",
                "activation_action": "activate_pass",
                "product_label_candidate": "pass",
                "product_effect": "accept_label_or_rescue",
                "contract_rule_id": (
                    "machine_observed_sufficient_positive_identity"
                ),
                "peak_hypothesis_id": "FAM_SPLIT::green",
                "activation_unit_scope": "peak_hypothesis",
                "activation_reason": "mode split green",
            },
        ],
    )
    _write_tsv(
        acceptance,
        ("acceptance_status", "blast_radius_current", "decision_rows_total"),
        [
            {
                "acceptance_status": acceptance_status,
                "blast_radius_current": "TRUE",
                "decision_rows_total": "5",
            }
        ],
    )
    _write_tsv(
        matrix,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "S1",
            "S2",
        ),
        [
            {
                "feature_family_id": "FAM_BLOCK",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "100.1",
                "family_center_rt": "7.1",
                "S1": "100",
                "S2": "200",
            },
            {
                "feature_family_id": "FAM_KEEP",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "300.3",
                "family_center_rt": "9.3",
                "S1": "",
                "S2": "777",
            },
            {
                "feature_family_id": "FAM_SPLIT",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "400.4",
                "family_center_rt": "10.4",
                "S1": "111",
                "S2": "222",
            }
        ],
    )
    _write_tsv(
        review,
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "identity_decision",
            "identity_confidence",
            "identity_reason",
            "accepted_cell_count",
            "accepted_rescue_count",
            "include_in_primary_matrix",
        ),
        [
            {
                "feature_family_id": "FAM_BLOCK",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "100.1",
                "family_center_rt": "7.1",
                "identity_decision": "production_family",
                "identity_confidence": "high",
                "identity_reason": "owner_complete_link",
                "accepted_cell_count": "2",
                "accepted_rescue_count": "1",
                "include_in_primary_matrix": "TRUE",
            },
            {
                "feature_family_id": "FAM_ADD",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "200.2",
                "family_center_rt": "8.2",
                "identity_decision": "provisional_discovery",
                "identity_confidence": "review",
                "identity_reason": "insufficient_detected_identity_support",
                "accepted_cell_count": "0",
                "accepted_rescue_count": "0",
                "include_in_primary_matrix": "FALSE",
            },
            {
                "feature_family_id": "FAM_KEEP",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "300.3",
                "family_center_rt": "9.3",
                "identity_decision": "production_family",
                "identity_confidence": "high",
                "identity_reason": "owner_complete_link",
                "accepted_cell_count": "1",
                "accepted_rescue_count": "1",
                "include_in_primary_matrix": "TRUE",
            },
            {
                "feature_family_id": "FAM_SPLIT",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "400.4",
                "family_center_rt": "10.4",
                "identity_decision": "production_family",
                "identity_confidence": "high",
                "identity_reason": "owner_complete_link",
                "accepted_cell_count": "2",
                "accepted_rescue_count": "0",
                "include_in_primary_matrix": "TRUE",
            },
        ],
    )
    _write_tsv(
        cells,
        ("feature_family_id", "sample_stem", "status", "area"),
        [
            {
                "feature_family_id": "FAM_BLOCK",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
            },
            {
                "feature_family_id": "FAM_BLOCK",
                "sample_stem": "S2",
                "status": "rescued",
                "area": "200",
            },
            {
                "feature_family_id": "FAM_ADD",
                "sample_stem": "S2",
                "status": "rescued",
                "area": "300",
            },
            {
                "feature_family_id": "FAM_KEEP",
                "sample_stem": "S2",
                "status": "rescued",
                "area": "999",
            },
            {
                "feature_family_id": "FAM_SPLIT",
                "sample_stem": "S1",
                "status": "detected",
                "area": "111",
            },
            {
                "feature_family_id": "FAM_SPLIT",
                "sample_stem": "S2",
                "status": "detected",
                "area": "222",
            },
        ],
    )
    return {
        "decisions": decisions,
        "acceptance": acceptance,
        "matrix": matrix,
        "review": review,
        "cells": cells,
    }


def _write_tsv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _header(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return tuple(next(csv.reader(handle, delimiter="\t")))


def _write_legacy_rt_row_oracle(
    path: Path,
    *,
    rows: tuple[tuple[float, float], ...],
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(("Mz", "RT"))
    for mz, rt in rows:
        sheet.append((mz, rt))
    workbook.save(path)
