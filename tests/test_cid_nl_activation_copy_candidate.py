from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.diagnostics import cid_nl_activation_copy_candidate as activation
from tools.diagnostics import cid_nl_feature_inclusion_gate as gate
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_builds_activation_copy_without_default_authority(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    payload = activation.build_activation_copy_candidate(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(paths["forbidden"],),
        alignment_matrix_tsv=paths["matrix"],
        alignment_matrix_identity_tsv=paths["identity"],
        output_dir=tmp_path / "out",
    )

    assert payload["activation_copy_status"] == "pass"
    assert payload["validation_label"] == "diagnostic_only_activated_copy_candidate"
    assert payload["candidate_contract_cell_count"] == 2
    assert payload["changed_matrix_cell_count"] == 2
    assert payload["candidate_transition_count"] == 1
    assert payload["product_writer_changed"] is False
    assert payload["default_quant_matrix_changed"] is False
    assert payload["workbook_gui_changed"] is False
    assert payload["candidate_rows_are_matrix_rows"] is False

    matrix_rows = read_tsv_required(
        tmp_path / "out" / "alignment_matrix_activated_copy.tsv",
        ("Mz", "RT", "S1", "S2"),
    )
    assert matrix_rows[0]["S1"] == "10"
    assert matrix_rows[0]["S2"] == "20"
    assert matrix_rows[1]["S1"] == "999"

    delta_rows = read_tsv_required(
        tmp_path / "out" / "cid_nl_activation_copy_value_delta.tsv",
        activation.VALUE_DELTA_COLUMNS,
    )
    assert len(delta_rows) == 2
    assert {row["original_matrix_value"] for row in delta_rows} == {""}
    assert {row["product_authority_effect"] for row in delta_rows} == {
        "diagnostic_only_no_authority_change",
    }

    summary = json.loads(
        (tmp_path / "out" / "cid_nl_activation_copy_candidate_summary.json")
        .read_text(encoding="utf-8")
    )
    assert "activated-copy validation artifact only" in (
        summary["authority_statement"]
    )


def test_activation_copy_blocks_existing_matrix_value_overwrite(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path, existing_value="111")

    with pytest.raises(ValueError, match="overwrite an existing matrix value"):
        activation.build_activation_copy_candidate(
            expected_diff_contract_tsvs=(paths["contract"],),
            forbidden_transition_tsvs=(paths["forbidden"],),
            alignment_matrix_tsv=paths["matrix"],
            alignment_matrix_identity_tsv=paths["identity"],
            output_dir=tmp_path / "out",
        )


def test_activation_copy_blocks_forbidden_transition(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, forbidden_transition="FAM_SRC->FAM_NEW")

    with pytest.raises(ValueError, match="forbidden review/hold/blocked"):
        activation.build_activation_copy_candidate(
            expected_diff_contract_tsvs=(paths["contract"],),
            forbidden_transition_tsvs=(paths["forbidden"],),
            alignment_matrix_tsv=paths["matrix"],
            alignment_matrix_identity_tsv=paths["identity"],
            output_dir=tmp_path / "out",
        )


def test_cli_require_pass_builds_activation_copy(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    exit_code = activation.main(
        [
            "--expected-diff-contract-tsv",
            str(paths["contract"]),
            "--forbidden-transition-tsv",
            str(paths["forbidden"]),
            "--alignment-matrix-tsv",
            str(paths["matrix"]),
            "--alignment-matrix-identity-tsv",
            str(paths["identity"]),
            "--output-dir",
            str(tmp_path / "out"),
            "--require-pass",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "out" / "alignment_matrix_activated_copy.tsv").exists()


def _write_inputs(
    tmp_path: Path,
    *,
    existing_value: str = "",
    forbidden_transition: str = "FAM_OTHER->FAM_BLOCKED",
) -> dict[str, Path]:
    matrix = tmp_path / "alignment_matrix.tsv"
    identity = tmp_path / "alignment_matrix_identity.tsv"
    contract = tmp_path / "expected_diff_contract.tsv"
    forbidden = tmp_path / "forbidden.tsv"
    write_tsv(
        matrix,
        [
            {"Mz": "300.1", "RT": "23.3", "S1": existing_value, "S2": ""},
            {"Mz": "301.2", "RT": "24.4", "S1": "999", "S2": ""},
        ],
        ("Mz", "RT", "S1", "S2"),
    )
    write_tsv(
        identity,
        [
            {"matrix_row_index": "1", "peak_hypothesis_id": "FAM_NEW"},
            {"matrix_row_index": "2", "peak_hypothesis_id": "FAM_KEEP"},
        ],
        ("matrix_row_index", "peak_hypothesis_id"),
    )
    write_tsv(
        contract,
        [
            _contract_row("S1", "10"),
            _contract_row("S2", "20"),
        ],
        gate.EXPECTED_DIFF_COLUMNS,
    )
    write_tsv(
        forbidden,
        [{"transition_key": forbidden_transition}],
        ("transition_key",),
    )
    return {
        "matrix": matrix,
        "identity": identity,
        "contract": contract,
        "forbidden": forbidden,
    }


def _contract_row(sample: str, value: str) -> dict[str, object]:
    return {
        "schema_version": gate.SCHEMA_VERSION,
        "expected_diff_contract_status": "expected_diff_design_candidate",
        "transition_key": "FAM_SRC->FAM_NEW",
        "sample_stem": sample,
        "source_peak_hypothesis_id": "FAM_SRC",
        "successor_peak_hypothesis_id": "FAM_NEW",
        "source_mz": "243.099",
        "source_rt": "23.66",
        "source_product_mz": "127.052",
        "source_neutral_loss_tag": "DNA_dR",
        "source_identity_decision": "audit_family",
        "successor_mz": "300.1605",
        "successor_rt": "23.35",
        "successor_product_mz": "184.113",
        "successor_neutral_loss_tag": "DNA_dR",
        "successor_identity_decision": "production_family",
        "candidate_quant_value": value,
        "legacy_successor_matrix_effect": "write_accepted_backfill",
        "legacy_successor_write_authority": "TRUE",
        "legacy_successor_matrix_write_allowed": "TRUE",
        "legacy_input_resolution_status": "write_ready_blank",
        "feature_inclusion_review_status": (
            "candidate_feature_inclusion_supported_by_current_overlay"
        ),
        "identity_authority_status": (
            "expected_diff_required_before_identity_authority"
        ),
        "authority_gate": "candidate_only_expected_diff_required_no_product_write",
        "product_authority_effect": "diagnostic_only_no_authority_change",
        "expected_product_effect": "candidate_cell_expected_diff_design_only",
        "guardrail_flag": "",
        "trace_data_json": "trace.json",
    }
