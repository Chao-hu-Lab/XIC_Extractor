from __future__ import annotations

import csv
from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    mode_window_assignment_gate,
)


def test_mode_window_gate_accepts_typed_assignment_with_partial_projection() -> None:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=[
            _fixture_row(
                "FAM011810_blue_normal_candidate",
                "FAM011810",
                "NormalBC2312_DNA",
                "multi_peak_tag_bearing_core",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
                "activation_candidate_only",
                "partial_until_no_family_projection",
            ),
            _fixture_row(
                "FAM011810_green_tumor_wrong_peak",
                "FAM011810",
                "TumorBC2263_DNA",
                "multi_peak_non_tag_mode",
                "cross_mode_rescue_blocked",
                "block_cross_mode_rescue",
                "auto_block_wrong_peak",
                "partial_until_no_family_projection",
            ),
            _fixture_row(
                "FAM015168_tailing_confounded",
                "FAM015168",
                "Breast_Cancer_Tissue_pooled_QC5",
                "tailing_confounded",
                "tailing_review_only",
                "require_tailing_review",
                "review_required",
                "review_only",
            ),
            _fixture_row(
                "QC_nearest_conflict_not_standalone_veto",
                "__QC_POLICY__",
                "__qc_context__",
                "qc_local_vs_consensus",
                "not_applicable",
                "no_product_action",
                "context_conflict_gate",
                "not_applicable",
            ),
            _fixture_row(
                "ISTD_non_parallel_drift_review",
                "__ISTD_POLICY__",
                "__istd_context__",
                "istd_drift_non_parallel",
                "not_applicable",
                "no_product_action",
                "review_required",
                "not_applicable",
            ),
        ],
        selection_rows=[
            _selection_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
            ),
            _selection_row(
                "FAM011810",
                "TumorBC2263_DNA",
                "cross_mode_rescue_blocked",
                "block_cross_mode_rescue",
            ),
            _selection_row(
                "FAM015168",
                "Breast_Cancer_Tissue_pooled_QC5",
                "raw_mode_review_only",
                "require_raw_mode_review",
            ),
        ],
        activation_rows=[
            _activation_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "auto_activate",
                "",
                selected_mode_id="irt_blue_core",
            ),
            _activation_row(
                "FAM011810",
                "TumorBC2263_DNA",
                "auto_block",
                "wrong_peak_conflict",
                selected_mode_id="irt_green_core",
            ),
            _activation_row(
                "FAM015168",
                "Breast_Cancer_Tissue_pooled_QC5",
                "not_applicable",
                "context_or_not_evaluable",
            ),
        ],
        matrix_summary=_matrix_summary(
            ready="FALSE",
            blockers="matrix_construction_blocked",
            family_projection_rows="610",
        ),
        qc_reference_rows=[
            {
                "feature_family_id": "FAM011810",
                "sample_stem": "TumorBC2263_DNA",
                "qc_reference_policy": "qc_consensus_mixed_review",
                "qc_consensus_status": "mixed_conflict",
            }
        ],
        rt_drift_rows=[
            {
                "feature_family_id": "FAM002625",
                "sample_stem": "Breast_Cancer_Tissue_pooled_QC1",
                "matrix_rt_drift_status": "drift_supported",
                "drift_evidence_level": "sample_istd_aligned",
                "istd_phase_summary": "early:n=29|mid:n=30|late:n=26",
                "istd_trend_sample_count": "85",
            }
        ],
    )

    assert {row["gate_status"] for row in rows} == {"pass"}
    summary = mode_window_assignment_gate.build_gate_summary(rows)
    assert summary["mode_window_assignment_gate_status"] == "pass"
    assert summary["next_action"] == (
        "mode_window_assignment_contract_gate_passed_"
        "keep_product_activation_blocked_until_matrix_construction"
    )


def test_mode_window_gate_fails_when_review_only_raw_mode_auto_activates() -> None:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=[
            _fixture_row(
                "FAM002625_raw_single_mode_review_only",
                "FAM002625",
                "TumorBC2263_DNA",
                "raw_single_mode_with_tag",
                "raw_mode_review_only",
                "require_raw_mode_review",
                "activation_ineligible_until_typed_mode",
                "review_only",
            )
        ],
        selection_rows=[
            _selection_row(
                "FAM002625",
                "TumorBC2263_DNA",
                "raw_mode_review_only",
                "require_raw_mode_review",
            )
        ],
        activation_rows=[
            _activation_row("FAM002625", "TumorBC2263_DNA", "auto_activate", "")
        ],
        matrix_summary=_matrix_summary(
            ready="FALSE",
            blockers="raw_mode_review_only",
            family_projection_rows="0",
        ),
    )

    assert rows[0]["gate_status"] == "fail"
    assert "activation_ineligible_auto_activated" in rows[0]["failure_reason"]


def test_mode_window_gate_fails_activation_hypothesis_id_mismatch() -> None:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=[
            _fixture_row(
                "FAM011810_blue_normal_candidate",
                "FAM011810",
                "NormalBC2312_DNA",
                "multi_peak_tag_bearing_core",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
                "activation_candidate_only",
                "partial_until_no_family_projection",
            )
        ],
        selection_rows=[
            _selection_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
            )
        ],
        activation_rows=[
            _activation_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "auto_activate",
                "",
                selected_mode_id="irt_green_core",
            )
        ],
        matrix_summary=_matrix_summary(
            ready="FALSE",
            blockers="matrix_construction_blocked",
            family_projection_rows="610",
        ),
    )

    assert rows[0]["gate_status"] == "fail"
    assert (
        rows[0]["observed_activation_peak_hypothesis_id"]
        == "FAM011810::irt_green_core"
    )
    assert "activation_peak_hypothesis_id_mismatch" in rows[0]["failure_reason"]


def test_mode_window_gate_marks_required_activation_sidecar_missing() -> None:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=[
            _fixture_row(
                "FAM011810_blue_normal_candidate",
                "FAM011810",
                "NormalBC2312_DNA",
                "multi_peak_tag_bearing_core",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
                "activation_candidate_only",
                "partial_until_no_family_projection",
                required_evidence_oracle="manual_overlay_ms1_qc_rt_ms2",
            )
        ],
        selection_rows=[
            _selection_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
            )
        ],
        matrix_summary=_matrix_summary(
            ready="FALSE",
            blockers="matrix_construction_blocked",
            family_projection_rows="610",
        ),
        qc_reference_rows=[_qc_row("FAM011810", "NormalBC2312_DNA")],
        rt_drift_rows=[_rt_drift_row("FAM011810", "NormalBC2312_DNA")],
        ms1_pattern_rows=[_ms1_row("FAM011810", "NormalBC2312_DNA")],
        candidate_ms2_pattern_rows=[
            _candidate_ms2_row("FAM011810", "NormalBC2312_DNA")
        ],
    )

    assert rows[0]["gate_status"] == "not_assessed"
    assert "activation_decision_not_assessed" in rows[0]["failure_reason"]


def test_mode_window_gate_fails_when_peak_hypothesis_identity_is_missing() -> None:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=[
            _fixture_row(
                "FAM011810_blue_normal_candidate",
                "FAM011810",
                "NormalBC2312_DNA",
                "multi_peak_tag_bearing_core",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
                "activation_candidate_only",
                "partial_until_no_family_projection",
                required_evidence_oracle="manual_overlay_ms1_qc_rt_ms2",
            )
        ],
        selection_rows=[
            {
                "feature_family_id": "FAM011810",
                "sample_stem": "NormalBC2312_DNA",
                "peak_hypothesis_status": "product_candidate_core",
                "product_selection_action": "select_mode_peak_hypothesis",
            }
        ],
        matrix_summary=_matrix_summary(
            ready="FALSE",
            blockers="matrix_construction_blocked",
            family_projection_rows="610",
        ),
    )

    assert rows[0]["gate_status"] == "fail"
    assert "peak_hypothesis_id_missing" in rows[0]["failure_reason"]
    assert "selected_mode_id_missing" in rows[0]["failure_reason"]


def test_mode_window_gate_fails_when_required_ms1_oracle_is_missing() -> None:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=[
            _fixture_row(
                "FAM011810_blue_normal_candidate",
                "FAM011810",
                "NormalBC2312_DNA",
                "multi_peak_tag_bearing_core",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
                "activation_candidate_only",
                "partial_until_no_family_projection",
                required_evidence_oracle="manual_overlay_ms1_qc_rt_ms2",
            )
        ],
        selection_rows=[
            _selection_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
            )
        ],
        matrix_summary=_matrix_summary(
            ready="FALSE",
            blockers="matrix_construction_blocked",
            family_projection_rows="610",
        ),
    )

    assert rows[0]["gate_status"] == "fail"
    assert "ms1_oracle_not_assessed" in rows[0]["failure_reason"]


def test_mode_window_gate_fails_when_family_projection_claims_canonical_ready() -> None:
    rows = mode_window_assignment_gate.build_gate_rows(
        fixture_rows=[
            _fixture_row(
                "FAM011810_blue_normal_candidate",
                "FAM011810",
                "NormalBC2312_DNA",
                "multi_peak_tag_bearing_core",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
                "activation_candidate_only",
                "partial_until_no_family_projection",
            )
        ],
        selection_rows=[
            _selection_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
            )
        ],
        matrix_summary=_matrix_summary(
            ready="TRUE",
            blockers="none",
            family_projection_rows="610",
        ),
    )

    assert rows[0]["gate_status"] == "fail"
    assert (
        "family_projection_canonical_readiness_overclaim"
        in rows[0]["failure_reason"]
    )


def test_mode_window_gate_cli_writes_rows_and_summary(tmp_path: Path) -> None:
    from tools.diagnostics.evaluate_mode_window_assignment_contract import main

    fixture = tmp_path / "fixture.tsv"
    selection = tmp_path / "selection.tsv"
    activation = tmp_path / "activation.tsv"
    matrix_summary = tmp_path / "matrix_summary.tsv"
    output_dir = tmp_path / "gate"
    _write_tsv(
        fixture,
        [
            _fixture_row(
                "FAM011810_blue_normal_candidate",
                "FAM011810",
                "NormalBC2312_DNA",
                "multi_peak_tag_bearing_core",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
                "activation_candidate_only",
                "partial_until_no_family_projection",
            )
        ],
    )
    _write_tsv(
        selection,
        [
            _selection_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "product_candidate_core",
                "select_mode_peak_hypothesis",
            )
        ],
    )
    _write_tsv(
        activation,
        [
            _activation_row(
                "FAM011810",
                "NormalBC2312_DNA",
                "auto_activate",
                "",
                selected_mode_id="irt_blue_core",
            )
        ],
    )
    _write_tsv(
        matrix_summary,
        [
            _matrix_summary(
                ready="FALSE",
                blockers="matrix_construction_blocked",
                family_projection_rows="610",
            )
        ],
    )
    ms1 = tmp_path / "ms1.tsv"
    candidate_ms2 = tmp_path / "candidate_ms2.tsv"
    qc = tmp_path / "qc.tsv"
    rt_drift = tmp_path / "rt_drift.tsv"
    _write_tsv(ms1, [_ms1_row("FAM011810", "NormalBC2312_DNA")])
    _write_tsv(candidate_ms2, [_candidate_ms2_row("FAM011810", "NormalBC2312_DNA")])
    _write_tsv(qc, [_qc_row("FAM011810", "NormalBC2312_DNA")])
    _write_tsv(rt_drift, [_rt_drift_row("FAM011810", "NormalBC2312_DNA")])

    assert (
        main(
            [
                "--contract-fixture-tsv",
                str(fixture),
                "--peak-hypothesis-selection-tsv",
                str(selection),
                "--activation-decisions-tsv",
                str(activation),
                "--peak-hypothesis-matrix-summary-tsv",
                str(matrix_summary),
                "--ms1-pattern-coherence-tsv",
                str(ms1),
                "--candidate-ms2-pattern-evidence-tsv",
                str(candidate_ms2),
                "--qc-ms1-pattern-reference-tsv",
                str(qc),
                "--matrix-rt-drift-policy-tsv",
                str(rt_drift),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    summary = _read_tsv(
        output_dir / "shared_peak_identity_mode_window_assignment_summary.tsv"
    )[0]
    assert summary["mode_window_assignment_gate_status"] == "pass"


def test_mode_window_gate_cli_returns_one_on_gate_failure(tmp_path: Path) -> None:
    from tools.diagnostics.evaluate_mode_window_assignment_contract import main

    fixture = tmp_path / "fixture.tsv"
    selection = tmp_path / "selection.tsv"
    activation = tmp_path / "activation.tsv"
    matrix_summary = tmp_path / "matrix_summary.tsv"
    output_dir = tmp_path / "gate"
    _write_tsv(
        fixture,
        [
            _fixture_row(
                "FAM002625_raw_single_mode_review_only",
                "FAM002625",
                "TumorBC2263_DNA",
                "raw_single_mode_with_tag",
                "raw_mode_review_only",
                "require_raw_mode_review",
                "activation_ineligible_until_typed_mode",
                "review_only",
            )
        ],
    )
    _write_tsv(
        selection,
        [
            _selection_row(
                "FAM002625",
                "TumorBC2263_DNA",
                "raw_mode_review_only",
                "require_raw_mode_review",
                selected_mode_id="raw_mode_1",
            )
        ],
    )
    _write_tsv(
        activation,
        [
            _activation_row(
                "FAM002625",
                "TumorBC2263_DNA",
                "auto_activate",
                "",
                selected_mode_id="raw_mode_1",
            )
        ],
    )
    _write_tsv(
        matrix_summary,
        [
            _matrix_summary(
                ready="FALSE",
                blockers="raw_mode_review_only",
                family_projection_rows="0",
            )
        ],
    )

    assert (
        main(
            [
                "--contract-fixture-tsv",
                str(fixture),
                "--peak-hypothesis-selection-tsv",
                str(selection),
                "--activation-decisions-tsv",
                str(activation),
                "--peak-hypothesis-matrix-summary-tsv",
                str(matrix_summary),
                "--output-dir",
                str(output_dir),
                "--fail-on-gate-failure",
            ]
        )
        == 1
    )
    assert (
        output_dir / "shared_peak_identity_mode_window_assignment_summary.tsv"
    ).exists()


def test_mode_window_gate_cli_returns_one_on_inconclusive_gate(tmp_path: Path) -> None:
    from tools.diagnostics.evaluate_mode_window_assignment_contract import main

    fixture = tmp_path / "fixture.tsv"
    selection = tmp_path / "selection.tsv"
    matrix_summary = tmp_path / "matrix_summary.tsv"
    output_dir = tmp_path / "gate"
    _write_tsv(
        fixture,
        [
            _fixture_row(
                "QC_nearest_conflict_not_standalone_veto",
                "__QC_POLICY__",
                "__qc_context__",
                "qc_local_vs_consensus",
                "not_applicable",
                "no_product_action",
                "context_conflict_gate",
                "not_applicable",
            )
        ],
    )
    _write_tsv(selection, [_selection_row("__IGNORED__", "S1", "", "")])
    _write_tsv(
        matrix_summary,
        [
            _matrix_summary(
                ready="FALSE",
                blockers="matrix_construction_blocked",
                family_projection_rows="0",
            )
        ],
    )

    assert (
        main(
            [
                "--contract-fixture-tsv",
                str(fixture),
                "--peak-hypothesis-selection-tsv",
                str(selection),
                "--peak-hypothesis-matrix-summary-tsv",
                str(matrix_summary),
                "--output-dir",
                str(output_dir),
                "--fail-on-gate-failure",
            ]
        )
        == 1
    )
    summary = _read_tsv(
        output_dir / "shared_peak_identity_mode_window_assignment_summary.tsv"
    )[0]
    assert summary["mode_window_assignment_gate_status"] == "inconclusive"


def _fixture_row(
    sentinel_id: str,
    family_id: str,
    sample_id: str,
    case_type: str,
    expected_status: str,
    expected_action: str,
    expected_boundary: str,
    expected_effect: str,
    *,
    expected_peak_hypothesis_id: str | None = None,
    expected_product_unit_scope: str | None = None,
    expected_selected_mode_id: str | None = None,
    expected_activation_unit_scope: str | None = None,
    required_evidence_oracle: str | None = None,
) -> dict[str, str]:
    mode_id = expected_selected_mode_id or _default_mode_id(
        family_id,
        expected_status,
    )
    return {
        "contract_schema_version": mode_window_assignment_gate.CONTRACT_SCHEMA_VERSION,
        "sentinel_id": sentinel_id,
        "feature_family_id": family_id,
        "sample_id": sample_id,
        "sentinel_case_type": case_type,
        "expected_peak_hypothesis_id": (
            expected_peak_hypothesis_id
            if expected_peak_hypothesis_id is not None
            else _default_peak_hypothesis_id(family_id, mode_id)
        ),
        "expected_product_unit_scope": (
            expected_product_unit_scope
            or _default_product_unit_scope(expected_status)
        ),
        "expected_selected_mode_id": mode_id,
        "expected_peak_hypothesis_status": expected_status,
        "expected_product_selection_action": expected_action,
        "expected_activation_unit_scope": (
            expected_activation_unit_scope
            or _default_activation_unit_scope(expected_status)
        ),
        "expected_activation_boundary": expected_boundary,
        "expected_canonical_identity_effect": expected_effect,
        "required_evidence_oracle": required_evidence_oracle or "unit_test_oracle",
        "expectation_reason": "unit test",
    }


def _selection_row(
    family_id: str,
    sample_id: str,
    status: str,
    action: str,
    *,
    selected_mode_id: str | None = None,
    product_unit_scope: str | None = None,
    reason: str | None = None,
) -> dict[str, str]:
    mode_id = selected_mode_id or _default_mode_id(family_id, status)
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_id,
        "peak_hypothesis_id": _default_peak_hypothesis_id(family_id, mode_id),
        "peak_hypothesis_status": status,
        "product_unit_scope": product_unit_scope or _default_product_unit_scope(status),
        "selected_mode_id": mode_id,
        "product_selection_action": action,
        "product_selection_blocker": _default_product_selection_blocker(status),
        "reason": reason or _default_selection_reason(status),
    }


def _activation_row(
    family_id: str,
    sample_id: str,
    status: str,
    rule_id: str,
    *,
    selected_mode_id: str | None = None,
    activation_unit_scope: str | None = None,
) -> dict[str, str]:
    mode_id = selected_mode_id or _default_mode_id(family_id, "")
    return {
        "feature_family_id": family_id,
        "sample_id": sample_id,
        "peak_hypothesis_id": _default_peak_hypothesis_id(family_id, mode_id),
        "activation_unit_scope": (
            activation_unit_scope or _default_activation_unit_scope_for_status(status)
        ),
        "activation_status": status,
        "contract_rule_id": rule_id,
    }


def _matrix_summary(
    *,
    ready: str,
    blockers: str,
    family_projection_rows: str,
) -> dict[str, str]:
    return {
        "canonical_row_identity_ready": ready,
        "canonical_row_identity_blockers": blockers,
        "family_projection_rows": family_projection_rows,
    }


def _ms1_row(family_id: str, sample_id: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_id,
        "ms1_pattern_status": "supportive",
    }


def _candidate_ms2_row(family_id: str, sample_id: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_id,
        "candidate_ms2_pattern_status": "supportive",
        "candidate_ms2_evidence_level": "sample_boundary_aligned",
        "diagnostic_only": "TRUE",
    }


def _qc_row(family_id: str, sample_id: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_id,
        "qc_reference_policy": "qc_consensus_with_local_qc_overlay",
        "qc_consensus_status": "supportive",
    }


def _rt_drift_row(family_id: str, sample_id: str) -> dict[str, str]:
    return {
        "feature_family_id": family_id,
        "sample_stem": sample_id,
        "matrix_rt_drift_status": "drift_supported",
        "drift_evidence_level": "sample_istd_aligned",
    }


def _default_mode_id(family_id: str, status: str) -> str:
    if family_id.startswith("__"):
        return "not_applicable"
    if status == "product_candidate_core":
        return "irt_blue_core"
    if status == "cross_mode_rescue_blocked":
        return "irt_green_core"
    if family_id == "FAM015168":
        return "raw_mode_1_8.43min"
    if family_id == "FAM001473":
        return "raw_mode_1_19.27min"
    if family_id == "FAM005937":
        return "raw_mode_1_14.34min"
    return "raw_mode_1"


def _default_peak_hypothesis_id(family_id: str, mode_id: str) -> str:
    if family_id.startswith("__") or mode_id == "not_applicable":
        return "not_applicable"
    return f"{family_id}::{mode_id}"


def _default_product_unit_scope(status: str) -> str:
    if status == "product_candidate_core":
        return "mode_level"
    if status == "cross_mode_rescue_blocked":
        return "sample_cell"
    if status in {"raw_mode_review_only", "tailing_review_only"}:
        return "review_only"
    return "not_applicable"


def _default_activation_unit_scope(status: str) -> str:
    if status == "cross_mode_rescue_blocked":
        return "sample_cell"
    if status in {"product_candidate_core", "raw_mode_review_only"}:
        return "peak_hypothesis"
    return "not_applicable"


def _default_activation_unit_scope_for_status(status: str) -> str:
    if status == "auto_block":
        return "sample_cell"
    if status in {"auto_activate", "review_required"}:
        return "peak_hypothesis"
    return "not_applicable"


def _default_product_selection_blocker(status: str) -> str:
    if status == "raw_mode_review_only":
        return "raw_mode_review_only"
    if status == "cross_mode_rescue_blocked":
        return "cross_mode_rescue"
    return "none"


def _default_selection_reason(status: str) -> str:
    if status == "product_candidate_core":
        return "typed_mode_hypothesis_assignment_supported_by_mode_tag"
    if status == "cross_mode_rescue_blocked":
        return "selected_cell_belongs_to_non_core_rt_mode"
    if status == "raw_mode_review_only":
        return "raw_mode_requires_typed_irt_mode_hypothesis"
    return "unit_test_selection"


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = tuple(dict.fromkeys(field for row in rows for field in row))
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
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
