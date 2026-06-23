from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from tools.diagnostics import standard_peak_policy_observed_oracle as cli
from xic_extractor.alignment.matrix_handoff import integration_from_peak_trace
from xic_extractor.diagnostics.standard_peak_heldout_trace_oracle import (
    _trace_reintegration_config,
)
from xic_extractor.signal_processing import find_peak_and_area


def test_policy_observed_oracle_cli_writes_pass_packet(tmp_path: Path) -> None:
    policy_tsv, source_audit_tsv = _write_policy_oracle_fixture(tmp_path)
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--backfill-policy-tsv",
                str(policy_tsv),
                "--activation-scope-audit-tsv",
                str(source_audit_tsv),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-policy-observed-oracle",
            ],
        )
        == 0
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["candidate_policy_row_count"] == "1"
    assert summary["oracle_case_status_pass_count"] == "1"
    assert summary["included_in_product_acceptance_count"] == "1"
    assert summary["observed_reintegration_mode"] == "full_trace"

    rows = _read_tsv(output_dir / "standard_peak_policy_observed_oracle.tsv")
    assert rows[0]["oracle_case_status"] == "pass"
    assert rows[0]["included_in_product_acceptance"] == "TRUE"
    assert rows[0]["observed_independence_basis"] == (
        "independent_boundary_reintegration_result"
    )
    assert rows[0]["policy_decision"] == "detected_flagged"


def test_policy_observed_oracle_fails_closed_without_matched_trace(
    tmp_path: Path,
) -> None:
    policy_tsv, source_audit_tsv = _write_policy_oracle_fixture(
        tmp_path,
        trace_match_status="missing_overlay_path",
    )
    output_dir = tmp_path / "oracle"

    assert (
        cli.main(
            [
                "--backfill-policy-tsv",
                str(policy_tsv),
                "--activation-scope-audit-tsv",
                str(source_audit_tsv),
                "--output-dir",
                str(output_dir),
                "--source-run-id",
                "unit-policy-observed-oracle-missing-trace",
            ],
        )
        == 1
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "fail"
    assert summary["oracle_case_status_inconclusive_count"] == "1"
    rows = _read_tsv(output_dir / "standard_peak_policy_observed_oracle.tsv")
    assert rows[0]["oracle_case_status"] == "inconclusive_review_only"
    assert rows[0]["inconclusive_reason"] == "trace_match_status:missing_overlay_path"
    assert rows[0]["included_in_product_acceptance"] == "FALSE"


def _write_policy_oracle_fixture(
    tmp_path: Path,
    *,
    trace_match_status: str = "matched",
) -> tuple[Path, Path]:
    trace_path = tmp_path / "FAM_STD_trace_data.json"
    rt = np.linspace(0.5, 1.5, 81)
    intensity = 1_000.0 + 5_000_000.0 * np.exp(-((rt - 1.0) ** 2) / (2 * 0.08**2))
    trace_path.write_text(
        json.dumps(
            {
                "family_id": "FAM_STD",
                "family_center_rt": 1.0,
                "traces": [
                    {
                        "sample_stem": "S1",
                        "status": "rescued",
                        "cell_area": 0,
                        "cell_height": float(max(intensity)),
                        "cell_apex_rt": 1.0,
                        "cell_start_rt": 0,
                        "cell_end_rt": 0,
                        "apex_aligned_shape_similarity": 0.96,
                        "local_window_to_global_max_ratio": 1.0,
                        "rt": [float(value) for value in rt],
                        "intensity": [float(value) for value in intensity],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    config = _trace_reintegration_config()
    result = find_peak_and_area(rt, intensity, config)
    assert result.peak is not None
    integration = integration_from_peak_trace(
        result.peak,
        rt,
        intensity,
        boundary_sources=("local_minimum",),
        integration_method="raw_trapezoid",
        baseline_integration_method="asls",
    )
    assert integration is not None
    source_area = integration.area_ms1_morphology or result.peak.area
    source_sha = "b" * 64

    policy_tsv = tmp_path / "standard_peak_backfill_policy.tsv"
    _write_tsv(
        policy_tsv,
        [
            {
                "schema_version": "standard_peak_backfill_policy_v2",
                "source_run_id": "unit-policy",
                "feature_family_id": "FAM_STD",
                "peak_hypothesis_id": "FAM_STD",
                "sample_id": "S1",
                "matrix_value_effect": "written",
                "matrix_value_source_row_sha256": source_sha,
                "backfill_policy_decision": "detected_flagged",
                "backfill_policy_evidence_class": "",
                "backfill_policy_authority_status": "review_only",
                "backfill_policy_reason": (
                    "boundary_stable_candidate_needs_masked_or_product_writer_oracle"
                ),
                "backfill_policy_decision_basis": (
                    "candidate_signal_without_writer_oracle"
                ),
                "backfill_policy_next_evidence": (
                    "masked_or_product_writer_oracle_required"
                ),
                "backfill_policy_candidate_evidence_class": "reintegration_stable",
                "ready_evidence_classes": "",
                "stability_status": "eligible",
                "backfill_policy_blockers": "missing_writer_approved_oracle",
            },
        ],
    )
    source_audit_tsv = tmp_path / "activation_scope_audit.tsv"
    _write_tsv(
        source_audit_tsv,
        [
            {
                "schema_version": "standard_peak_activation_scope_audit_v1",
                "source_run_id": "unit-source",
                "feature_family_id": "FAM_STD",
                "peak_hypothesis_id": "FAM_STD",
                "sample_id": "S1",
                "matrix_value_effect": "written",
                "source_cell_status": "rescued",
                "activated_matrix_value": str(source_area),
                "matrix_value_source_row_sha256": source_sha,
                "trace_data_path": str(trace_path),
                "trace_match_status": trace_match_status,
                "trace_status": "rescued",
                "cell_area": str(source_area),
                "cell_height": str(max(intensity)),
                "cell_start_rt": str(result.peak.peak_start),
                "cell_end_rt": str(result.peak.peak_end),
                "cell_apex_rt": str(result.peak.rt),
            },
        ],
    )
    return policy_tsv, source_audit_tsv


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
