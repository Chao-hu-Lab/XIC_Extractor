from __future__ import annotations

from pathlib import Path

from tests.test_cid_nl_activation_copy_candidate import _write_inputs
from tools.diagnostics import cid_nl_activation_copy_acceptance as acceptance
from tools.diagnostics import cid_nl_activation_copy_candidate as activation
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_accepts_activation_copy_matching_contract(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    activation.build_activation_copy_candidate(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(paths["forbidden"],),
        alignment_matrix_tsv=paths["matrix"],
        alignment_matrix_identity_tsv=paths["identity"],
        output_dir=tmp_path / "copy",
    )

    payload = acceptance.build_activation_copy_acceptance(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(paths["forbidden"],),
        input_alignment_matrix_tsv=paths["matrix"],
        activated_matrix_tsv=tmp_path / "copy" / "alignment_matrix_activated_copy.tsv",
        alignment_matrix_identity_tsv=paths["identity"],
        value_delta_tsv=tmp_path / "copy" / "cid_nl_activation_copy_value_delta.tsv",
        output_dir=tmp_path / "acceptance",
    )

    assert payload["acceptance_status"] == "pass"
    assert payload["production_ready"] is False
    assert payload["contract_cell_count"] == 2
    assert payload["value_delta_cell_count"] == 2
    assert payload["matrix_changed_cell_count"] == 2
    assert payload["forbidden_overlap_count"] == 0
    assert payload["default_quant_matrix_changed"] is False
    diff_rows = read_tsv_required(
        tmp_path / "acceptance" / "cid_nl_activation_copy_matrix_diff.tsv",
        acceptance.MATRIX_DIFF_COLUMNS,
    )
    assert len(diff_rows) == 2
    assert {row["input_value"] for row in diff_rows} == {""}


def test_rejects_forbidden_contract_overlap(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, forbidden_transition="FAM_SRC->FAM_NEW")
    activation.build_activation_copy_candidate(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(),
        alignment_matrix_tsv=paths["matrix"],
        alignment_matrix_identity_tsv=paths["identity"],
        output_dir=tmp_path / "copy",
    )

    payload = acceptance.build_activation_copy_acceptance(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(paths["forbidden"],),
        input_alignment_matrix_tsv=paths["matrix"],
        activated_matrix_tsv=tmp_path / "copy" / "alignment_matrix_activated_copy.tsv",
        alignment_matrix_identity_tsv=paths["identity"],
        value_delta_tsv=tmp_path / "copy" / "cid_nl_activation_copy_value_delta.tsv",
        output_dir=tmp_path / "acceptance",
    )

    assert payload["acceptance_status"] == "fail"
    assert payload["forbidden_overlap_count"] == 1
    assert "forbidden_transition_overlap" in payload["hard_fail_reasons"]


def test_rejects_unexpected_matrix_change(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    activation.build_activation_copy_candidate(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(paths["forbidden"],),
        alignment_matrix_tsv=paths["matrix"],
        alignment_matrix_identity_tsv=paths["identity"],
        output_dir=tmp_path / "copy",
    )
    rows = read_tsv_required(
        tmp_path / "copy" / "alignment_matrix_activated_copy.tsv",
        ("Mz", "RT", "S1", "S2"),
    )
    rows[1]["S2"] = "777"
    write_tsv(
        tmp_path / "copy" / "alignment_matrix_activated_copy.tsv",
        rows,
        ("Mz", "RT", "S1", "S2"),
    )

    payload = acceptance.build_activation_copy_acceptance(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(paths["forbidden"],),
        input_alignment_matrix_tsv=paths["matrix"],
        activated_matrix_tsv=tmp_path / "copy" / "alignment_matrix_activated_copy.tsv",
        alignment_matrix_identity_tsv=paths["identity"],
        value_delta_tsv=tmp_path / "copy" / "cid_nl_activation_copy_value_delta.tsv",
        output_dir=tmp_path / "acceptance",
    )

    assert payload["acceptance_status"] == "fail"
    assert "unexpected_matrix_change" in payload["hard_fail_reasons"]


def test_cli_require_pass_builds_acceptance(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    activation.build_activation_copy_candidate(
        expected_diff_contract_tsvs=(paths["contract"],),
        forbidden_transition_tsvs=(paths["forbidden"],),
        alignment_matrix_tsv=paths["matrix"],
        alignment_matrix_identity_tsv=paths["identity"],
        output_dir=tmp_path / "copy",
    )

    exit_code = acceptance.main(
        [
            "--expected-diff-contract-tsv",
            str(paths["contract"]),
            "--forbidden-transition-tsv",
            str(paths["forbidden"]),
            "--input-alignment-matrix-tsv",
            str(paths["matrix"]),
            "--activated-matrix-tsv",
            str(tmp_path / "copy" / "alignment_matrix_activated_copy.tsv"),
            "--alignment-matrix-identity-tsv",
            str(paths["identity"]),
            "--value-delta-tsv",
            str(tmp_path / "copy" / "cid_nl_activation_copy_value_delta.tsv"),
            "--output-dir",
            str(tmp_path / "acceptance"),
            "--require-pass",
        ]
    )

    assert exit_code == 0
