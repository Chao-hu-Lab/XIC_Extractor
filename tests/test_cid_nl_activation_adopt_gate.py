from __future__ import annotations

from pathlib import Path

from tools.diagnostics import cid_nl_activation_adopt_gate as adopt
from tools.diagnostics import cid_nl_activation_copy_acceptance as acceptance
from tools.diagnostics import cid_nl_activation_copy_candidate as activation
from tools.diagnostics import cid_nl_feature_inclusion_gate as feature_gate
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_builds_adopt_ready_gate_without_default_authority(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    payload = adopt.build_activation_adopt_gate(
        expected_diff_contract_tsvs=(
            paths["primary_contract"],
            paths["agent_contract"],
            paths["manual_contract"],
        ),
        forbidden_transition_tsvs=(
            paths["user_review"],
            paths["agent_hold"],
            paths["manual_hold"],
            paths["blocked"],
        ),
        feature_gate_summary_tsv=paths["feature_summary"],
        activation_copy_summary_tsv=paths["copy_summary"],
        acceptance_summary_tsv=paths["acceptance_summary"],
        value_delta_tsv=paths["value_delta"],
        output_dir=tmp_path / "adopt",
    )

    assert payload["adopt_gate_status"] == "adopt_ready"
    assert payload["validation_label"] == "production_candidate_activation_adopt_gate"
    assert payload["contract_cell_count"] == 95
    assert payload["candidate_transition_count"] == 20
    assert payload["primary_expected_diff_cell_count"] == 73
    assert payload["agent_resolved_expected_diff_cell_count"] == 9
    assert payload["manual_resolved_expected_diff_cell_count"] == 13
    assert payload["activation_bundle_adopt_ready"] is True
    assert payload["production_ready"] is False
    assert payload["product_writer_changed"] is False
    assert payload["default_quant_matrix_changed"] is False

    manifest = read_tsv_required(
        tmp_path / "adopt" / "cid_nl_activation_adopt_manifest.tsv",
        adopt.MANIFEST_COLUMNS,
    )
    assert len(manifest) == 20
    assert _source_transition_counts(manifest) == {
        "primary_supported": 14,
        "agent_resolved": 2,
        "manual_resolved": 4,
    }


def test_adopt_gate_holds_on_forbidden_overlap(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, forbidden_transition="FAM_P_SRC_00->FAM_P_NEW_00")

    payload = adopt.build_activation_adopt_gate(
        expected_diff_contract_tsvs=(
            paths["primary_contract"],
            paths["agent_contract"],
            paths["manual_contract"],
        ),
        forbidden_transition_tsvs=(
            paths["user_review"],
            paths["agent_hold"],
            paths["manual_hold"],
            paths["blocked"],
        ),
        feature_gate_summary_tsv=paths["feature_summary"],
        activation_copy_summary_tsv=paths["copy_summary"],
        acceptance_summary_tsv=paths["acceptance_summary"],
        value_delta_tsv=paths["value_delta"],
        output_dir=tmp_path / "adopt",
    )

    assert payload["adopt_gate_status"] == "hold"
    assert payload["activation_bundle_adopt_ready"] is False
    assert "forbidden_transition_overlap" in payload["hard_fail_reasons"]
    assert payload["production_ready"] is False


def test_adopt_gate_holds_on_wrong_bundle_shape(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, primary_cell_count=72)

    payload = adopt.build_activation_adopt_gate(
        expected_diff_contract_tsvs=(
            paths["primary_contract"],
            paths["agent_contract"],
            paths["manual_contract"],
        ),
        forbidden_transition_tsvs=(
            paths["user_review"],
            paths["agent_hold"],
            paths["manual_hold"],
            paths["blocked"],
        ),
        feature_gate_summary_tsv=paths["feature_summary"],
        activation_copy_summary_tsv=paths["copy_summary"],
        acceptance_summary_tsv=paths["acceptance_summary"],
        value_delta_tsv=paths["value_delta"],
        output_dir=tmp_path / "adopt",
    )

    assert payload["adopt_gate_status"] == "hold"
    assert payload["activation_bundle_adopt_ready"] is False
    assert "adopt_contract_cell_count_drift" in payload["hard_fail_reasons"]
    assert "primary_expected_diff_count_drift" in payload["hard_fail_reasons"]


def test_adopt_gate_reports_authority_flags_on_hold(tmp_path: Path) -> None:
    paths = _write_inputs(
        tmp_path,
        copy_summary_overrides={"product_writer_changed": "TRUE"},
    )

    payload = adopt.build_activation_adopt_gate(
        expected_diff_contract_tsvs=(
            paths["primary_contract"],
            paths["agent_contract"],
            paths["manual_contract"],
        ),
        forbidden_transition_tsvs=(
            paths["user_review"],
            paths["agent_hold"],
            paths["manual_hold"],
            paths["blocked"],
        ),
        feature_gate_summary_tsv=paths["feature_summary"],
        activation_copy_summary_tsv=paths["copy_summary"],
        acceptance_summary_tsv=paths["acceptance_summary"],
        value_delta_tsv=paths["value_delta"],
        output_dir=tmp_path / "adopt",
    )

    assert payload["adopt_gate_status"] == "hold"
    assert payload["product_writer_changed"] is True
    assert "product_writer_changed_before_adopt_gate" in payload["hard_fail_reasons"]


def test_cli_require_pass_builds_adopt_gate(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    exit_code = adopt.main(
        [
            "--expected-diff-contract-tsv",
            str(paths["primary_contract"]),
            "--expected-diff-contract-tsv",
            str(paths["agent_contract"]),
            "--expected-diff-contract-tsv",
            str(paths["manual_contract"]),
            "--forbidden-transition-tsv",
            str(paths["user_review"]),
            "--forbidden-transition-tsv",
            str(paths["agent_hold"]),
            "--forbidden-transition-tsv",
            str(paths["manual_hold"]),
            "--forbidden-transition-tsv",
            str(paths["blocked"]),
            "--feature-gate-summary-tsv",
            str(paths["feature_summary"]),
            "--activation-copy-summary-tsv",
            str(paths["copy_summary"]),
            "--acceptance-summary-tsv",
            str(paths["acceptance_summary"]),
            "--value-delta-tsv",
            str(paths["value_delta"]),
            "--output-dir",
            str(tmp_path / "adopt"),
            "--require-pass",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "adopt" / "cid_nl_activation_adopt_gate_summary.tsv").exists()


def _write_inputs(
    tmp_path: Path,
    *,
    forbidden_transition: str = "FAM_BLOCKED->FAM_OTHER",
    primary_cell_count: int = adopt.EXPECTED_PRIMARY_EXPECTED_DIFF_CELL_COUNT,
    copy_summary_overrides: dict[str, object] | None = None,
) -> dict[str, Path]:
    primary = tmp_path / "cid_nl_supported_candidate_expected_diff_contract.tsv"
    agent = tmp_path / "cid_nl_agent_resolved_expected_diff_contract.tsv"
    manual = tmp_path / "cid_nl_manual_resolved_expected_diff_contract.tsv"
    value_delta = tmp_path / "value_delta.tsv"
    feature_summary = tmp_path / "feature_summary.tsv"
    copy_summary = tmp_path / "copy_summary.tsv"
    acceptance_summary = tmp_path / "acceptance_summary.tsv"
    user_review = tmp_path / "user_review.tsv"
    agent_hold = tmp_path / "agent_hold.tsv"
    manual_hold = tmp_path / "manual_hold.tsv"
    blocked = tmp_path / "blocked.tsv"

    primary_rows = _split_rows("P", 14, primary_cell_count, 0)
    agent_rows = _split_rows(
        "A",
        2,
        adopt.EXPECTED_AGENT_RESOLVED_EXPECTED_DIFF_CELL_COUNT,
        len(primary_rows),
    )
    manual_rows = _split_rows(
        "M",
        4,
        adopt.EXPECTED_MANUAL_RESOLVED_EXPECTED_DIFF_CELL_COUNT,
        len(primary_rows) + len(agent_rows),
    )
    contract_rows = [*primary_rows, *agent_rows, *manual_rows]
    write_tsv(primary, primary_rows, feature_gate.EXPECTED_DIFF_COLUMNS)
    write_tsv(agent, agent_rows, feature_gate.EXPECTED_DIFF_COLUMNS)
    write_tsv(manual, manual_rows, feature_gate.EXPECTED_DIFF_COLUMNS)
    write_tsv(
        value_delta,
        [_delta_row(row) for row in contract_rows],
        activation.VALUE_DELTA_COLUMNS,
    )
    write_tsv(
        feature_summary,
        [_feature_summary_row()],
        adopt.FEATURE_GATE_SUMMARY_COLUMNS,
    )
    write_tsv(
        copy_summary,
        [_copy_summary_row(len(contract_rows), 20, copy_summary_overrides)],
        adopt.ACTIVATION_COPY_SUMMARY_COLUMNS,
    )
    write_tsv(
        acceptance_summary,
        [_acceptance_summary_row(len(contract_rows), 20)],
        adopt.ACCEPTANCE_SUMMARY_COLUMNS,
    )
    for path, key in (
        (user_review, ""),
        (agent_hold, ""),
        (manual_hold, ""),
        (blocked, forbidden_transition),
    ):
        rows = [{"transition_key": key}] if key else []
        write_tsv(path, rows, acceptance.FORBIDDEN_TRANSITION_COLUMNS)
    return {
        "primary_contract": primary,
        "agent_contract": agent,
        "manual_contract": manual,
        "value_delta": value_delta,
        "feature_summary": feature_summary,
        "copy_summary": copy_summary,
        "acceptance_summary": acceptance_summary,
        "user_review": user_review,
        "agent_hold": agent_hold,
        "manual_hold": manual_hold,
        "blocked": blocked,
    }


def _split_rows(
    prefix: str,
    transition_count: int,
    cell_count: int,
    start_index: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    base, extra = divmod(cell_count, transition_count)
    for transition_index in range(transition_count):
        per_transition = base + (1 if transition_index < extra else 0)
        source = f"FAM_{prefix}_SRC_{transition_index:02d}"
        successor = f"FAM_{prefix}_NEW_{transition_index:02d}"
        for sample_index in range(per_transition):
            row_index = start_index + len(rows)
            rows.append(
                _contract_row(
                    source,
                    successor,
                    f"{prefix}{transition_index:02d}_{sample_index:02d}",
                    row_index,
                )
            )
    return rows


def _source_transition_counts(
    manifest: list[dict[str, str]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in manifest:
        source = row["contract_source"]
        counts[source] = counts.get(source, 0) + 1
    return counts


def _contract_row(
    source: str,
    successor: str,
    sample: str,
    index: int,
) -> dict[str, object]:
    return {
        "schema_version": feature_gate.SCHEMA_VERSION,
        "expected_diff_contract_status": "expected_diff_design_candidate",
        "transition_key": f"{source}->{successor}",
        "sample_stem": sample,
        "source_peak_hypothesis_id": source,
        "successor_peak_hypothesis_id": successor,
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
        "candidate_quant_value": str(1000 + index),
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


def _delta_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": activation.SCHEMA_VERSION,
        "transition_key": row["transition_key"],
        "sample_stem": row["sample_stem"],
        "source_peak_hypothesis_id": row["source_peak_hypothesis_id"],
        "successor_peak_hypothesis_id": row["successor_peak_hypothesis_id"],
        "matrix_row_index": "1",
        "source_mz": row["source_mz"],
        "source_rt": row["source_rt"],
        "successor_mz": row["successor_mz"],
        "successor_rt": row["successor_rt"],
        "successor_product_mz": row["successor_product_mz"],
        "successor_neutral_loss_tag": row["successor_neutral_loss_tag"],
        "original_matrix_value": "",
        "activated_copy_value": row["candidate_quant_value"],
        "candidate_quant_value": row["candidate_quant_value"],
        "value_changed": "TRUE",
        "authority_gate": row["authority_gate"],
        "product_authority_effect": "diagnostic_only_no_authority_change",
        "expected_product_effect": row["expected_product_effect"],
    }


def _feature_summary_row() -> dict[str, object]:
    return {
        "overall_status": "pass",
        "validation_label": "diagnostic_only",
        "candidate_cell_count": "147",
        "expected_diff_cell_count": "73",
        "agent_resolved_expected_diff_contract_cell_count": "9",
        "manual_resolved_expected_diff_contract_cell_count": "13",
        "agent_resolved_hold_cell_count": "24",
        "manual_resolved_hold_cell_count": "0",
        "user_review_cell_count": "0",
        "blocked_candidate_cell_count": "28",
        "existing_successor_context_cell_count": "337",
        "omitted_no_target_cell_count": "27",
        "product_writer_changed": "FALSE",
        "default_quant_matrix_changed": "FALSE",
        "candidate_rows_are_matrix_rows": "FALSE",
    }


def _copy_summary_row(
    contract_cell_count: int,
    transition_count: int,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "activation_copy_status": "pass",
        "validation_label": "diagnostic_only_activated_copy_candidate",
        "candidate_contract_cell_count": str(contract_cell_count),
        "changed_matrix_cell_count": str(contract_cell_count),
        "candidate_transition_count": str(transition_count),
        "product_writer_changed": "FALSE",
        "default_quant_matrix_changed": "FALSE",
        "workbook_gui_changed": "FALSE",
        "candidate_rows_are_matrix_rows": "FALSE",
    }
    if overrides:
        row.update(overrides)
    return row


def _acceptance_summary_row(
    contract_cell_count: int,
    transition_count: int,
) -> dict[str, object]:
    return {
        "acceptance_status": "pass",
        "validation_label": "diagnostic_only_activated_copy_acceptance",
        "contract_cell_count": str(contract_cell_count),
        "value_delta_cell_count": str(contract_cell_count),
        "matrix_changed_cell_count": str(contract_cell_count),
        "candidate_transition_count": str(transition_count),
        "forbidden_overlap_count": "0",
        "unexpected_matrix_change_count": "0",
        "missing_matrix_change_count": "0",
        "product_writer_changed": "FALSE",
        "default_quant_matrix_changed": "FALSE",
        "workbook_gui_changed": "FALSE",
        "candidate_rows_are_matrix_rows": "FALSE",
        "production_ready": "FALSE",
        "hard_fail_reasons": "",
        "next_action": "promote_requires_explicit_adopt_gate",
    }
