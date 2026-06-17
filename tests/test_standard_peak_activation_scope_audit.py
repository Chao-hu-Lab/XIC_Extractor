from __future__ import annotations

import json
from pathlib import Path

from pytest import CaptureFixture

from xic_extractor.diagnostics.standard_peak_activation_scope_audit import (
    audit_activation_scope,
    build_narrow_expected_diff_acceptance,
)
from xic_extractor.tabular_io import read_tsv_required, write_tsv


def test_activation_scope_audit_classifies_high_signal_clean_rows(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "family_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="SampleA",
        family_center_rt=5.0,
        cell_height=2_500_000.0,
        cell_start_rt=4.8,
        cell_end_rt=5.2,
        cell_apex_rt=5.03,
        shape_similarity=0.96,
        local_global_ratio=0.99,
        rt_values=[
            4.75,
            4.80,
            4.84,
            4.88,
            4.92,
            4.96,
            5.00,
            5.04,
            5.08,
            5.12,
            5.16,
            5.20,
        ],
    )
    low_height_overlay = tmp_path / "low_height_overlay.png"
    _write_trace_json(
        low_height_overlay.with_name(f"{low_height_overlay.stem}_trace_data.json"),
        sample_stem="SampleB",
        family_center_rt=7.0,
        cell_height=100_000.0,
        cell_start_rt=6.8,
        cell_end_rt=7.2,
        cell_apex_rt=7.02,
        shape_similarity=0.97,
        local_global_ratio=1.0,
        rt_values=[
            6.80,
            6.84,
            6.88,
            6.92,
            6.96,
            7.00,
            7.04,
            7.08,
            7.12,
            7.16,
            7.20,
        ],
    )

    rows, summary = audit_activation_scope(
        activation_value_delta_rows=[
            _delta_row("FAM_A", "SampleA", "hash-a"),
            _delta_row("FAM_B", "SampleB", "hash-b"),
            _delta_row("FAM_C", "SampleC", "hash-c"),
            _delta_row("FAM_D", "SampleD", "hash-d"),
        ],
        shadow_projection_rows=[
            _projection_row("FAM_A", "SampleA", "hash-a", str(overlay)),
            _projection_row("FAM_B", "SampleB", "hash-b", str(low_height_overlay)),
            _projection_row("FAM_C", "SampleC", "hash-c", ""),
        ],
        activation_value_delta_tsv=tmp_path / "activation_value_delta.tsv",
        shadow_projection_cells_tsv=tmp_path / "shadow_projection_cells.tsv",
        source_run_id="unit",
    )

    by_family = {row["feature_family_id"]: row for row in rows}
    assert by_family["FAM_A"]["high_signal_clean_status"] == "eligible"
    assert by_family["FAM_A"]["low_scan_clean_status"] == "ineligible"
    assert by_family["FAM_A"]["low_height_clean_status"] == "ineligible"
    assert by_family["FAM_A"]["integration_scan_count"] == "11"
    assert by_family["FAM_A"]["high_signal_clean_blockers"] == ""
    assert by_family["FAM_B"]["high_signal_clean_status"] == "ineligible"
    assert "height_lt_2000000" in by_family["FAM_B"]["high_signal_clean_blockers"]
    assert "height_lt_2000000" in by_family["FAM_B"]["low_scan_clean_blockers"]
    assert by_family["FAM_B"]["low_height_clean_status"] == "eligible"
    assert by_family["FAM_B"]["low_height_clean_blockers"] == ""
    assert by_family["FAM_C"]["trace_match_status"] == "missing_overlay_path"
    assert by_family["FAM_C"]["high_signal_clean_status"] == "missing_evidence"
    assert by_family["FAM_D"]["projection_match_status"] == "missing_projection_row"
    assert by_family["FAM_D"]["high_signal_clean_status"] == "missing_evidence"
    assert summary["activation_value_delta_row_count"] == "4"
    assert summary["written_activation_row_count"] == "4"
    assert summary["projection_matched_written_count"] == "3"
    assert summary["high_signal_clean_eligible_written_count"] == "1"
    assert summary["low_scan_clean_eligible_written_count"] == "0"
    assert summary["low_height_clean_eligible_written_count"] == "1"
    assert summary["high_signal_clean_missing_evidence_written_count"] == "2"
    assert summary["broad_activation_scope_status"] == "not_ready"


def test_activation_scope_audit_joins_by_source_row_sha_not_family_sample(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "sha_only_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="DeltaSample",
        family_center_rt=5.0,
        cell_height=2_500_000.0,
        cell_start_rt=4.8,
        cell_end_rt=5.2,
        cell_apex_rt=5.03,
        shape_similarity=0.96,
        local_global_ratio=0.99,
        rt_values=_dense_rt_values(4.75, 5.20),
    )

    rows, summary = audit_activation_scope(
        activation_value_delta_rows=[
            _delta_row("DELTA_FAMILY", "DeltaSample", "shared-row-sha"),
        ],
        shadow_projection_rows=[
            _projection_row(
                "PROJECTION_FAMILY",
                "ProjectionSample",
                "shared-row-sha",
                str(overlay),
            ),
        ],
        activation_value_delta_tsv=tmp_path / "activation_value_delta.tsv",
        shadow_projection_cells_tsv=tmp_path / "shadow_projection_cells.tsv",
        source_run_id="unit",
    )

    assert rows[0]["projection_match_status"] == "matched"
    assert rows[0]["projection_feature_family_id"] == "PROJECTION_FAMILY"
    assert rows[0]["projection_sample_stem"] == "ProjectionSample"
    assert rows[0]["trace_match_status"] == "matched"
    assert rows[0]["high_signal_clean_status"] == "eligible"
    assert summary["projection_matched_written_count"] == "1"


def test_activation_scope_audit_reports_each_high_signal_threshold_blocker(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "threshold_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="ignored",
        family_center_rt=10.0,
        cell_height=1.0,
        cell_start_rt=0.0,
        cell_end_rt=0.1,
        cell_apex_rt=0.0,
        shape_similarity=1.0,
        local_global_ratio=1.0,
        rt_values=[0.0],
        trace_rows=[
            _trace_json_row(
                sample_stem="ThresholdSample",
                trace_status="context",
                cell_height=1_999_999.0,
                cell_start_rt=9.0,
                cell_end_rt=9.2,
                cell_apex_rt=10.3,
                shape_similarity=0.94,
                local_global_ratio=0.94,
                rt_values=[9.0, 9.1, 9.2],
            )
        ],
    )

    rows, _summary = audit_activation_scope(
        activation_value_delta_rows=[
            _delta_row("FAM_THRESHOLD", "ThresholdSample", "threshold-sha"),
        ],
        shadow_projection_rows=[
            _projection_row(
                "FAM_THRESHOLD",
                "ThresholdSample",
                "threshold-sha",
                str(overlay),
            ),
        ],
        activation_value_delta_tsv=tmp_path / "activation_value_delta.tsv",
        shadow_projection_cells_tsv=tmp_path / "shadow_projection_cells.tsv",
        source_run_id="unit",
    )

    blockers = set(rows[0]["high_signal_clean_blockers"].split(";"))
    assert rows[0]["high_signal_clean_status"] == "ineligible"
    assert blockers == {
        "unsupported_trace_status",
        "shape_lt_0.95",
        "local_global_ratio_lt_0.95",
        "height_lt_2000000",
        "width_outside_0.30_0.65",
        "apex_delta_gt_0.15",
        "scan_count_lt_10",
    }


def test_activation_scope_audit_classifies_low_scan_clean_rows(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "low_scan_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="LowScanSample",
        family_center_rt=5.0,
        cell_height=2_500_000.0,
        cell_start_rt=4.8,
        cell_end_rt=5.2,
        cell_apex_rt=5.03,
        shape_similarity=0.97,
        local_global_ratio=0.99,
        rt_values=[
            4.80,
            4.85,
            4.90,
            4.95,
            5.00,
            5.05,
            5.10,
            5.15,
            5.20,
        ],
    )

    rows, summary = audit_activation_scope(
        activation_value_delta_rows=[
            _delta_row("FAM_LOW_SCAN", "LowScanSample", "low-scan-sha"),
        ],
        shadow_projection_rows=[
            _projection_row(
                "FAM_LOW_SCAN",
                "LowScanSample",
                "low-scan-sha",
                str(overlay),
            ),
        ],
        activation_value_delta_tsv=tmp_path / "activation_value_delta.tsv",
        shadow_projection_cells_tsv=tmp_path / "shadow_projection_cells.tsv",
        source_run_id="unit",
    )

    assert rows[0]["high_signal_clean_status"] == "ineligible"
    assert rows[0]["high_signal_clean_blockers"] == "scan_count_lt_10"
    assert rows[0]["low_scan_clean_status"] == "eligible"
    assert rows[0]["low_scan_clean_blockers"] == ""
    assert summary["high_signal_clean_eligible_written_count"] == "0"
    assert summary["low_scan_clean_eligible_written_count"] == "1"
    assert summary["low_scan_clean_activation_scope_status"] == (
        "ready_if_product_scope_is_limited_to_low_scan_clean_rows"
    )


def test_activation_scope_audit_classifies_low_height_clean_rows(
    tmp_path: Path,
) -> None:
    overlay = tmp_path / "low_height_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="LowHeightSample",
        family_center_rt=5.0,
        cell_height=500_000.0,
        cell_start_rt=4.8,
        cell_end_rt=5.2,
        cell_apex_rt=5.03,
        shape_similarity=0.97,
        local_global_ratio=0.99,
        rt_values=_dense_rt_values(4.75, 5.20),
    )

    rows, summary = audit_activation_scope(
        activation_value_delta_rows=[
            _delta_row("FAM_LOW_HEIGHT", "LowHeightSample", "low-height-sha"),
        ],
        shadow_projection_rows=[
            _projection_row(
                "FAM_LOW_HEIGHT",
                "LowHeightSample",
                "low-height-sha",
                str(overlay),
            ),
        ],
        activation_value_delta_tsv=tmp_path / "activation_value_delta.tsv",
        shadow_projection_cells_tsv=tmp_path / "shadow_projection_cells.tsv",
        source_run_id="unit",
    )

    assert rows[0]["high_signal_clean_status"] == "ineligible"
    assert rows[0]["high_signal_clean_blockers"] == "height_lt_2000000"
    assert rows[0]["low_height_clean_status"] == "eligible"
    assert rows[0]["low_height_clean_blockers"] == ""
    assert summary["high_signal_clean_eligible_written_count"] == "0"
    assert summary["low_height_clean_eligible_written_count"] == "1"
    assert summary["low_height_clean_activation_scope_status"] == (
        "candidate_only_pending_low_height_heldout_oracle"
    )


def test_narrow_expected_diff_acceptance_fails_on_noneligible_delta(
    tmp_path: Path,
) -> None:
    eligible = _delta_row("FAM_ELIGIBLE", "SampleA", "eligible-sha")
    noneligible = _delta_row("FAM_BAD", "SampleB", "bad-sha")
    acceptance = build_narrow_expected_diff_acceptance(
        audit_rows=[
            _audit_row(
                "FAM_ELIGIBLE",
                "SampleA",
                "eligible-sha",
                high_signal_clean_status="eligible",
            ),
            _audit_row(
                "FAM_BAD",
                "SampleB",
                "bad-sha",
                high_signal_clean_status="ineligible",
            ),
        ],
        eligible_activation_value_delta_rows=[eligible, noneligible],
        activation_value_delta_rows=[eligible, noneligible],
        activation_value_delta_tsv=tmp_path / "activation_value_delta.tsv",
        activation_scope_audit_tsv=tmp_path / "audit.tsv",
        eligible_activation_value_delta_tsv=tmp_path / "eligible.tsv",
        source_run_id="unit",
    )

    assert acceptance["acceptance_status"] == "fail"
    assert acceptance["non_eligible_delta_row_count"] == "1"
    assert "eligible_delta_contains_noneligible_rows" in acceptance["blocking_reasons"]


def test_activation_scope_audit_cli_writes_summary_and_eligible_delta(
    tmp_path: Path,
) -> None:
    from tools.diagnostics import standard_peak_activation_scope_audit as cli

    overlay = tmp_path / "family_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="SampleA",
        family_center_rt=5.0,
        cell_height=2_500_000.0,
        cell_start_rt=4.8,
        cell_end_rt=5.2,
        cell_apex_rt=5.03,
        shape_similarity=0.96,
        local_global_ratio=0.99,
        rt_values=[
            4.75,
            4.80,
            4.84,
            4.88,
            4.92,
            4.96,
            5.00,
            5.04,
            5.08,
            5.12,
            5.16,
            5.20,
        ],
    )
    delta_tsv = tmp_path / "activation_value_delta.tsv"
    shadow_tsv = tmp_path / "shadow_projection_cells.tsv"
    output_dir = tmp_path / "audit"
    write_tsv(
        delta_tsv,
        [_delta_row("FAM_A", "SampleA", "hash-a")],
        _DELTA_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        shadow_tsv,
        [_projection_row("FAM_A", "SampleA", "hash-a", str(overlay))],
        _SHADOW_COLUMNS,
        lineterminator="\n",
    )

    assert cli.main(
        [
            "--activation-value-delta-tsv",
            str(delta_tsv),
            "--shadow-projection-cells-tsv",
            str(shadow_tsv),
            "--output-dir",
            str(output_dir),
            "--source-run-id",
            "unit-cli",
        ],
    ) == 0

    summary = json.loads(
        (output_dir / "activation_high_signal_clean_scope_summary.json").read_text(
            encoding="utf-8",
        )
    )
    acceptance = json.loads(
        (output_dir / "narrow_activation_expected_diff_acceptance.json").read_text(
            encoding="utf-8",
        )
    )
    eligible_delta = read_tsv_required(
        output_dir / "eligible_activation_value_delta.tsv",
        _DELTA_COLUMNS,
    )
    assert summary["high_signal_clean_eligible_written_count"] == "1"
    assert summary["source_run_id"] == "unit-cli"
    assert acceptance["acceptance_status"] == "pass"
    assert acceptance["expected_scope"] == "high_signal_clean_eligible_activation_rows"
    assert acceptance["product_surface_changed"] == "FALSE"
    assert len(eligible_delta) == 1
    assert eligible_delta[0]["feature_family_id"] == "FAM_A"


def test_activation_scope_audit_cli_writes_low_scan_expected_diff(
    tmp_path: Path,
) -> None:
    from tools.diagnostics import standard_peak_activation_scope_audit as cli

    overlay = tmp_path / "low_scan_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="LowScanSample",
        family_center_rt=5.0,
        cell_height=2_500_000.0,
        cell_start_rt=4.8,
        cell_end_rt=5.2,
        cell_apex_rt=5.03,
        shape_similarity=0.97,
        local_global_ratio=0.99,
        rt_values=[
            4.80,
            4.85,
            4.90,
            4.95,
            5.00,
            5.05,
            5.10,
            5.15,
            5.20,
        ],
    )
    delta_tsv = tmp_path / "activation_value_delta.tsv"
    shadow_tsv = tmp_path / "shadow_projection_cells.tsv"
    output_dir = tmp_path / "audit"
    write_tsv(
        delta_tsv,
        [_delta_row("FAM_LOW_SCAN", "LowScanSample", "low-scan-sha")],
        _DELTA_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        shadow_tsv,
        [
            _projection_row(
                "FAM_LOW_SCAN",
                "LowScanSample",
                "low-scan-sha",
                str(overlay),
            ),
        ],
        _SHADOW_COLUMNS,
        lineterminator="\n",
    )

    assert cli.main(
        [
            "--activation-value-delta-tsv",
            str(delta_tsv),
            "--shadow-projection-cells-tsv",
            str(shadow_tsv),
            "--output-dir",
            str(output_dir),
            "--source-run-id",
            "unit-low-scan-cli",
        ],
    ) == 0

    summary = json.loads(
        (output_dir / "activation_high_signal_clean_scope_summary.json").read_text(
            encoding="utf-8",
        )
    )
    acceptance = json.loads(
        (
            output_dir / "low_scan_clean_activation_expected_diff_acceptance.json"
        ).read_text(encoding="utf-8")
    )
    low_scan_delta = read_tsv_required(
        output_dir / "low_scan_clean_activation_value_delta.tsv",
        _DELTA_COLUMNS,
    )
    assert summary["low_scan_clean_eligible_written_count"] == "1"
    assert acceptance["acceptance_status"] == "pass"
    assert acceptance["expected_scope"] == "low_scan_clean_eligible_activation_rows"
    assert len(low_scan_delta) == 1
    assert low_scan_delta[0]["feature_family_id"] == "FAM_LOW_SCAN"


def test_activation_scope_audit_cli_writes_low_height_expected_diff(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    from tools.diagnostics import standard_peak_activation_scope_audit as cli

    overlay = tmp_path / "low_height_overlay.png"
    _write_trace_json(
        overlay.with_name(f"{overlay.stem}_trace_data.json"),
        sample_stem="LowHeightSample",
        family_center_rt=5.0,
        cell_height=500_000.0,
        cell_start_rt=4.8,
        cell_end_rt=5.2,
        cell_apex_rt=5.03,
        shape_similarity=0.97,
        local_global_ratio=0.99,
        rt_values=_dense_rt_values(4.75, 5.20),
    )
    delta_tsv = tmp_path / "activation_value_delta.tsv"
    shadow_tsv = tmp_path / "shadow_projection_cells.tsv"
    output_dir = tmp_path / "audit"
    write_tsv(
        delta_tsv,
        [_delta_row("FAM_LOW_HEIGHT", "LowHeightSample", "low-height-sha")],
        _DELTA_COLUMNS,
        lineterminator="\n",
    )
    write_tsv(
        shadow_tsv,
        [
            _projection_row(
                "FAM_LOW_HEIGHT",
                "LowHeightSample",
                "low-height-sha",
                str(overlay),
            ),
        ],
        _SHADOW_COLUMNS,
        lineterminator="\n",
    )

    assert cli.main(
        [
            "--activation-value-delta-tsv",
            str(delta_tsv),
            "--shadow-projection-cells-tsv",
            str(shadow_tsv),
            "--output-dir",
            str(output_dir),
            "--source-run-id",
            "unit-low-height-cli",
        ],
    ) == 0
    out = capsys.readouterr().out
    assert (
        "Low-height clean diagnostic/candidate-only expected-diff acceptance JSON"
        in out
    )

    summary = json.loads(
        (output_dir / "activation_high_signal_clean_scope_summary.json").read_text(
            encoding="utf-8",
        )
    )
    acceptance = json.loads(
        (
            output_dir / "low_height_clean_activation_expected_diff_acceptance.json"
        ).read_text(encoding="utf-8")
    )
    low_height_delta = read_tsv_required(
        output_dir / "low_height_clean_activation_value_delta.tsv",
        _DELTA_COLUMNS,
    )
    assert summary["low_height_clean_eligible_written_count"] == "1"
    assert summary["low_height_clean_activation_scope_status"] == (
        "candidate_only_pending_low_height_heldout_oracle"
    )
    assert acceptance["acceptance_status"] == "pass"
    assert acceptance["expected_scope"] == "low_height_clean_eligible_activation_rows"
    assert acceptance["product_surface_changed"] == "FALSE"
    assert acceptance["next_action"] == (
        "product_decision_required_before_writing_low_height_clean_activation_output"
    )
    assert len(low_height_delta) == 1
    assert low_height_delta[0]["feature_family_id"] == "FAM_LOW_HEIGHT"


_DELTA_COLUMNS = (
    "activation_value_delta_schema_version",
    "feature_family_id",
    "candidate_container_id",
    "sample_id",
    "peak_hypothesis_id",
    "activation_unit_scope",
    "activation_status",
    "product_effect",
    "contract_rule_id",
    "original_matrix_value",
    "activated_matrix_value",
    "matrix_value_kind",
    "matrix_value_source",
    "matrix_value_source_field",
    "matrix_value_source_detail",
    "matrix_value_source_artifact_schema_version",
    "matrix_value_source_artifact_sha256",
    "matrix_value_source_row_sha256",
    "source_cell_status",
    "source_cell_area",
    "matrix_value_effect",
    "value_changed",
    "activation_reason",
)

_SHADOW_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "feature_family_id",
    "sample_stem",
    "local_global_ratio",
    "cell_status",
    "gap_fill_state",
    "projected_matrix_value",
    "shadow_projection_row_sha256",
    "overlay_png_path",
)


def _delta_row(family_id: str, sample_id: str, row_sha: str) -> dict[str, str]:
    return {
        "activation_value_delta_schema_version": (
            "shared_peak_identity_activation_value_delta_v3"
        ),
        "feature_family_id": family_id,
        "candidate_container_id": family_id,
        "sample_id": sample_id,
        "peak_hypothesis_id": family_id,
        "activation_unit_scope": "peak_hypothesis",
        "activation_status": "auto_activate",
        "product_effect": "accept_label_or_rescue",
        "contract_rule_id": "machine_observed_sufficient_positive_identity",
        "original_matrix_value": "",
        "activated_matrix_value": "100",
        "matrix_value_kind": "backfill_activation",
        "matrix_value_source": "activation_values_tsv",
        "matrix_value_source_field": "projected_matrix_value",
        "matrix_value_source_detail": "standard_peak_shadow_projection",
        "matrix_value_source_artifact_schema_version": (
            "shadow_production_projection_v1"
        ),
        "matrix_value_source_artifact_sha256": "0" * 64,
        "matrix_value_source_row_sha256": row_sha,
        "source_cell_status": "rescued",
        "source_cell_area": "100",
        "matrix_value_effect": "written",
        "value_changed": "TRUE",
        "activation_reason": (
            "standard_peak_shift_aware_ms1_same_peak_product_authorized"
        ),
    }


def _projection_row(
    family_id: str,
    sample_id: str,
    row_sha: str,
    overlay_png_path: str,
) -> dict[str, str]:
    return {
        "schema_version": "shadow_production_projection_v1",
        "peak_hypothesis_id": family_id,
        "feature_family_id": family_id,
        "sample_stem": sample_id,
        "local_global_ratio": "0.99",
        "cell_status": "rescued",
        "gap_fill_state": "not_filled",
        "projected_matrix_value": "100",
        "shadow_projection_row_sha256": row_sha,
        "overlay_png_path": overlay_png_path,
    }


def _audit_row(
    family_id: str,
    sample_id: str,
    row_sha: str,
    *,
    high_signal_clean_status: str,
) -> dict[str, str]:
    return {
        "schema_version": "standard_peak_activation_scope_audit_v1",
        "source_run_id": "unit",
        "feature_family_id": family_id,
        "peak_hypothesis_id": family_id,
        "sample_id": sample_id,
        "matrix_value_effect": "written",
        "source_cell_status": "rescued",
        "activated_matrix_value": "100",
        "matrix_value_source_row_sha256": row_sha,
        "projection_match_status": "matched",
        "trace_match_status": "matched",
        "high_signal_clean_status": high_signal_clean_status,
        "high_signal_clean_blockers": ""
        if high_signal_clean_status == "eligible"
        else "height_lt_2000000",
        "low_scan_clean_status": "missing_evidence",
        "low_scan_clean_blockers": "not_tested",
        "low_height_clean_status": "missing_evidence",
        "low_height_clean_blockers": "not_tested",
    }


def _write_trace_json(
    path: Path,
    *,
    sample_stem: str,
    family_center_rt: float,
    cell_height: float,
    cell_start_rt: float,
    cell_end_rt: float,
    cell_apex_rt: float,
    shape_similarity: float,
    local_global_ratio: float,
    rt_values: list[float],
    trace_status: str = "rescued",
    trace_rows: list[dict[str, object]] | None = None,
) -> None:
    rows = trace_rows or [
        _trace_json_row(
            sample_stem=sample_stem,
            trace_status=trace_status,
            cell_height=cell_height,
            cell_start_rt=cell_start_rt,
            cell_end_rt=cell_end_rt,
            cell_apex_rt=cell_apex_rt,
            shape_similarity=shape_similarity,
            local_global_ratio=local_global_ratio,
            rt_values=rt_values,
        )
    ]
    path.write_text(
        json.dumps(
            {
                "family_id": "FAM_TEST",
                "family_center_rt": family_center_rt,
                "traces": rows,
            },
        ),
        encoding="utf-8",
    )


def _trace_json_row(
    *,
    sample_stem: str,
    trace_status: str,
    cell_height: float,
    cell_start_rt: float,
    cell_end_rt: float,
    cell_apex_rt: float,
    shape_similarity: float,
    local_global_ratio: float,
    rt_values: list[float],
) -> dict[str, object]:
    return {
        "sample_stem": sample_stem,
        "status": trace_status,
        "cell_area": 100.0,
        "cell_height": cell_height,
        "cell_apex_rt": cell_apex_rt,
        "cell_start_rt": cell_start_rt,
        "cell_end_rt": cell_end_rt,
        "local_window_to_global_max_ratio": local_global_ratio,
        "apex_aligned_shape_similarity": shape_similarity,
        "rt": rt_values,
        "intensity": [0.0 for _ in rt_values],
    }


def _dense_rt_values(start: float, end: float) -> list[float]:
    return [
        start,
        start + 0.05,
        start + 0.09,
        start + 0.13,
        start + 0.17,
        start + 0.21,
        start + 0.25,
        start + 0.29,
        start + 0.33,
        start + 0.37,
        end,
    ]
