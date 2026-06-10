import csv
import json
from pathlib import Path

from tools.diagnostics import standard_peak_shadow_activation_inputs as cli
from xic_extractor.diagnostics.standard_peak_shadow_activation_inputs import (
    build_standard_peak_activation_inputs,
)


def test_build_standard_peak_activation_inputs_selects_new_standard_accepts() -> None:
    index = build_standard_peak_activation_inputs(
        [
            _shadow_row("FAM_STD", "S1", "100", standard=True),
            _shadow_row(
                "FAM_ALREADY",
                "S1",
                "200",
                standard=True,
                current_written="TRUE",
            ),
            _shadow_row("FAM_OTHER", "S1", "300", standard=False),
            _shadow_row("FAM_CTX", "S1", "400", standard=True, decision="context"),
        ],
        source_shadow_projection_sha256="a" * 64,
        source_run_id="unit-test",
    )

    assert len(index.decisions) == 1
    decision = index.decisions[0]
    assert decision["feature_family_id"] == "FAM_STD"
    assert decision["sample_id"] == "S1"
    assert decision["activation_status"] == "auto_activate"
    assert decision["activation_unit_scope"] == "peak_hypothesis"
    assert decision["diagnostic_only"] == "FALSE"
    value = index.values[0]
    assert value["projected_matrix_value"] == "100"
    assert value["source_artifact_sha256"] == "a" * 64
    assert value["source_row_sha256"] == "b" * 64
    assert index.summary["selected_activation_row_count"] == "1"
    assert index.summary["skipped_current_written_count"] == "1"
    assert index.summary["skipped_non_standard_reason_count"] == "1"
    assert index.summary["skipped_non_accept_count"] == "1"
    assert index.summary["standard_peak_gate_status"] == "pass"
    assert index.summary["activation_acceptance_status"] == "pass"
    assert index.summary["activation_acceptance_hard_fail_reasons"] == ""
    assert index.summary["activation_decision_scope"] == "manual_oracle_seed_rows"
    assert index.summary["must_not_regress_basis"] == "manual_status_flag"
    assert index.summary["next_action"] == "apply_matrix_only_activation"
    assert index.acceptance["activation_decision_scope"] == "manual_oracle_seed_rows"
    assert index.acceptance["must_not_regress_basis"] == "manual_status_flag"


def test_build_standard_peak_activation_inputs_labels_machine_gate_scope() -> None:
    index = build_standard_peak_activation_inputs(
        [_shadow_row("FAM_STD", "S1", "100", standard=True, machine=True)],
        source_shadow_projection_sha256="a" * 64,
        source_run_id="machine-gate-unit-test",
    )

    assert index.summary["selected_activation_row_count"] == "1"
    assert index.summary["activation_decision_scope"] == (
        "machine_gate_standard_peak_rows"
    )
    assert index.summary["must_not_regress_basis"] == (
        "machine_shift_aware_standard_peak_gate"
    )
    assert index.acceptance["activation_decision_scope"] == (
        "machine_gate_standard_peak_rows"
    )
    assert index.acceptance["must_not_regress_basis"] == (
        "machine_shift_aware_standard_peak_gate"
    )


def test_build_standard_peak_activation_inputs_rejects_malformed_row_hash() -> None:
    malformed = _shadow_row("FAM_STD", "S1", "100", standard=True)
    malformed["shadow_projection_row_sha256"] = "g" * 64

    index = build_standard_peak_activation_inputs(
        [malformed],
        source_shadow_projection_sha256="a" * 64,
        source_run_id="unit-test",
    )

    assert index.summary["standard_peak_gate_status"] == "fail"
    assert "FAM_STD/S1:invalid_source_row_sha256" in index.summary[
        "standard_peak_gate_failure_reasons"
    ]
    assert index.summary["activation_acceptance_status"] == "fail"
    assert index.summary["next_action"] == (
        "review_standard_peak_activation_gate_failures"
    )


def test_standard_peak_shadow_activation_inputs_cli_writes_activation_inputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "shadow.tsv"
    _write_tsv(
        source,
        [_shadow_row("FAM_STD", "S1", "100", standard=True)],
        (
            "schema_version",
            "peak_hypothesis_id",
            "feature_family_id",
            "sample_stem",
            "current_raw_status",
            "current_production_status",
            "current_matrix_written",
            "shadow_decision",
            "projected_matrix_written",
            "projected_matrix_value",
            "product_authority_chain",
            "shadow_projection_row_sha256",
        ),
    )

    assert (
        cli.main(
            [
                "--shadow-projection-cells-tsv",
                str(source),
                "--output-dir",
                str(tmp_path / "out"),
                "--source-run-id",
                "unit-test",
            ],
        )
        == 0
    )

    out = tmp_path / "out"
    decisions = _read_tsv(out / "standard_peak_activation_decisions.tsv")
    values = _read_tsv(out / "standard_peak_activation_values.tsv")
    acceptance = _read_tsv(out / "standard_peak_activation_acceptance.tsv")
    summary = json.loads(
        (out / "standard_peak_activation_inputs_summary.json").read_text(
            encoding="utf-8",
        ),
    )
    assert decisions[0]["activation_status"] == "auto_activate"
    assert values[0]["projected_matrix_value_source"] == (
        "standard_peak_shadow_projection"
    )
    assert len(values[0]["source_artifact_sha256"]) == 64
    assert acceptance[0]["decision_rows_total"] == "1"
    assert acceptance[0]["acceptance_status"] == "pass"
    assert acceptance[0]["hard_fail_reasons"] == ""
    assert acceptance[0]["must_not_regress_status"] == "pass"
    assert summary["selected_activation_row_count"] == "1"
    assert summary["standard_peak_gate_status"] == "pass"
    assert summary["activation_acceptance_status"] == "pass"
    assert summary["activation_acceptance_max_allowed_product_affecting_rows"] == "1"
    assert summary["next_action"] == "apply_matrix_only_activation"
    assert summary["source_run_id"] == "unit-test"


def test_standard_peak_shadow_activation_inputs_cli_can_apply_matrix_only(
    tmp_path: Path,
) -> None:
    source = tmp_path / "shadow.tsv"
    fixture = _write_matrix_only_fixture(tmp_path)
    _write_tsv(
        source,
        [_shadow_row("FAM_STD", "S2", "100", standard=True)],
        (
            "schema_version",
            "peak_hypothesis_id",
            "feature_family_id",
            "sample_stem",
            "current_raw_status",
            "current_production_status",
            "current_matrix_written",
            "shadow_decision",
            "projected_matrix_written",
            "projected_matrix_value",
            "product_authority_chain",
            "shadow_projection_row_sha256",
        ),
    )

    assert (
        cli.main(
            [
                "--shadow-projection-cells-tsv",
                str(source),
                "--output-dir",
                str(tmp_path / "out"),
                "--source-run-id",
                "unit-test",
                "--apply-matrix-only",
                "--alignment-matrix-tsv",
                str(fixture["matrix"]),
                "--alignment-matrix-identity-tsv",
                str(fixture["identity"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
            ],
        )
        == 0
    )

    activated_dir = tmp_path / "out" / "activated_matrix"
    matrix_rows = _read_tsv(activated_dir / "alignment_matrix.tsv")
    identity_rows = _read_tsv(activated_dir / "alignment_matrix_identity.tsv")
    delta = _read_tsv(activated_dir / "activation_value_delta.tsv")
    row_index = next(
        index
        for index, row in enumerate(identity_rows)
        if row["peak_hypothesis_id"] == "FAM_STD"
    )
    assert matrix_rows[row_index]["S2"] == "100"
    assert delta[0]["matrix_value_effect"] == "written"
    assert delta[0]["matrix_value_source"] == "activation_values_tsv"


def _shadow_row(
    family: str,
    sample: str,
    value: str,
    *,
    standard: bool,
    decision: str = "accept",
    current_written: str = "FALSE",
    machine: bool = False,
) -> dict[str, str]:
    authority_token = (
        "machine_standard_peak_gate_authorized"
        if machine
        else "manual_standard_peak_gate_authorized"
    )
    reason = (
        "MS1:product_authorized:supportive:trace_constellation:"
        f"feature_family_sample:{authority_token} | "
        "same_peak_reason:shift_aware_standard_peak_gate_supported"
        if standard
        else "MS1:product_authorized:supportive:trace_constellation:"
        "feature_family_sample:other"
    )
    return {
        "schema_version": "shadow_production_projection_v1",
        "peak_hypothesis_id": family,
        "feature_family_id": family,
        "sample_stem": sample,
        "current_raw_status": "rescued",
        "current_production_status": "review_rescue",
        "current_matrix_written": current_written,
        "shadow_decision": decision,
        "projected_matrix_written": "TRUE",
        "projected_matrix_value": value,
        "product_authority_chain": reason,
        "shadow_projection_row_sha256": "b" * 64,
    }


def _write_matrix_only_fixture(tmp_path: Path) -> dict[str, Path]:
    matrix = tmp_path / "alignment_matrix.tsv"
    identity = tmp_path / "alignment_matrix_identity.tsv"
    review = tmp_path / "alignment_review.tsv"
    _write_tsv(
        matrix,
        [
            {
                "Mz": "300.3",
                "RT": "9.3",
                "S1": "10",
                "S2": "",
            },
        ],
        ("Mz", "RT", "S1", "S2"),
    )
    _write_tsv(
        identity,
        [
            {
                "matrix_row_index": "1",
                "Mz": "300.3",
                "RT": "9.3",
                "peak_hypothesis_id": "FAM_STD",
                "row_identity_basis": "no_split_peak_hypothesis",
                "source_feature_family_ids": "FAM_STD",
            },
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
            {
                "feature_family_id": "FAM_STD",
                "neutral_loss_tag": "DNA_dR",
                "family_center_mz": "300.3",
                "family_center_rt": "9.3",
                "include_in_primary_matrix": "TRUE",
            },
        ],
        (
            "feature_family_id",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "include_in_primary_matrix",
        ),
    )
    return {"matrix": matrix, "identity": identity, "review": review}


def _write_tsv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: tuple[str, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
