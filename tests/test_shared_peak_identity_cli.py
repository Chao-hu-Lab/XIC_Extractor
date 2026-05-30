from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from tools.diagnostics.shared_peak_identity_explanation import main
from xic_extractor.alignment.shared_peak_identity_explanation.schema import (
    ORACLE_COLUMNS,
    ORACLE_SCHEMA_VERSION,
)


def test_cli_writes_slice0_outputs_and_no_blast_radius(tmp_path: Path) -> None:
    fixture = _write_cli_fixture(tmp_path)
    output_dir = tmp_path / "out"

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    expected = {
        "shared_peak_identity_manual_oracle.tsv",
        "shared_peak_identity_evidence_vectors.tsv",
        "shared_peak_identity_explanations.tsv",
        "shared_peak_identity_run_facts.tsv",
        "shared_peak_identity_explanation_report.md",
    }
    assert expected <= {path.name for path in output_dir.iterdir()}
    assert not (output_dir / "shared_peak_identity_blast_radius_manifest.tsv").exists()
    facts = _read_tsv(output_dir / "shared_peak_identity_run_facts.tsv")[0]
    assert facts["slice"] == "slice0"
    assert facts["blast_radius_assessed"] == "not_run_slice0"
    assert facts["max_overfit_risk"] == "unassessed"
    assert facts["seed_rows_explained"] == facts["seed_rows_total"]
    report = (output_dir / "shared_peak_identity_explanation_report.md").read_text(
        encoding="utf-8"
    )
    assert report.index("## Decision Summary") < report.index(
        "## Run-Level Readiness Facts"
    )
    assert "production readiness" in report


def test_cli_reports_missing_input(tmp_path: Path) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(tmp_path / "missing.tsv"),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 2
    )


def test_cli_requires_both_blast_radius_runs(tmp_path: Path) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path),
                "--enable-blast-radius",
                "--blast-radius-8raw-run",
                str(tmp_path / "8raw"),
            ]
        )
        == 2
    )


def test_cli_preflight_samples_without_slice1_outputs(
    tmp_path: Path,
    capsys,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-blast-radius",
                "--blast-radius-preflight-only",
                "--blast-radius-sample-row-limit",
                "1",
                "--blast-radius-8raw-run",
                str(fixture["eight_raw"]),
                "--blast-radius-85raw-run",
                str(fixture["eightyfive_raw"]),
            ]
        )
        == 0
    )

    stdout = capsys.readouterr().out
    assert "preflight_85raw_alignment_cells_row_count: 1" in stdout
    assert not (tmp_path / "out" / "shared_peak_identity_run_facts.tsv").exists()
    assert not (
        tmp_path / "out" / "shared_peak_identity_explanation_report.md"
    ).exists()
    assert not (
        tmp_path
        / "out"
        / "shared_peak_identity_blast_radius_manifest.tsv"
    ).exists()
    assert not (
        tmp_path
        / "out"
        / "shared_peak_identity_blast_radius_summary.tsv"
    ).exists()


def test_cli_rejects_unknown_optional_blast_radius_role(tmp_path: Path) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-blast-radius",
                "--blast-radius-8raw-run",
                str(fixture["eight_raw"]),
                "--blast-radius-85raw-run",
                str(fixture["eightyfive_raw"]),
                "--optional-blast-radius-artifact",
                f"unknown={tmp_path / 'artifact.tsv'}",
            ]
        )
        == 2
    )


def test_cli_slice1_writes_blast_radius_outputs(tmp_path: Path) -> None:
    fixture = _write_cli_fixture(tmp_path)
    expected_manifest = tmp_path / "expected_manifest.tsv"
    _write_expected_manifest(
        expected_manifest,
        {
            "8raw_alignment_review": fixture["eight_raw"] / "alignment_review.tsv",
            "8raw_alignment_cells": fixture["eight_raw"] / "alignment_cells.tsv",
            "85raw_alignment_review": fixture["eightyfive_raw"]
            / "alignment_review.tsv",
            "85raw_alignment_cells": fixture["eightyfive_raw"]
            / "alignment_cells.tsv",
        },
    )

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-blast-radius",
                "--blast-radius-8raw-run",
                str(fixture["eight_raw"]),
                "--blast-radius-85raw-run",
                str(fixture["eightyfive_raw"]),
                "--expected-blast-radius-manifest",
                str(expected_manifest),
                "--optional-blast-radius-artifact",
                f"candidate_gate_8raw={fixture['gate']}",
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    assert (output_dir / "shared_peak_identity_blast_radius_manifest.tsv").exists()
    assert (output_dir / "shared_peak_identity_blast_radius_summary.tsv").exists()
    facts = _read_tsv(output_dir / "shared_peak_identity_run_facts.tsv")[0]
    assert facts["slice"] == "slice1"
    assert facts["blast_radius_assessed"] == "present_current"
    assert facts["max_overfit_risk"] != "unassessed"
    manifest_rows = _read_tsv(
        output_dir / "shared_peak_identity_blast_radius_manifest.tsv"
    )
    assert {row["artifact_id"] for row in manifest_rows} >= {"candidate_gate_8raw"}
    summary_rows = _read_tsv(
        output_dir / "shared_peak_identity_blast_radius_summary.tsv"
    )
    compatible_by_scope = {
        row["scope"]: int(row["compatible_row_count"]) for row in summary_rows
    }
    assert "candidate_gate_8raw" not in compatible_by_scope
    report = (output_dir / "shared_peak_identity_explanation_report.md").read_text(
        encoding="utf-8"
    )
    assert "production_ready" not in report


def test_cli_writes_v2_shadow_alignment_as_exploratory_when_unpinned(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-blast-radius",
                "--blast-radius-8raw-run",
                str(fixture["eight_raw"]),
                "--blast-radius-85raw-run",
                str(fixture["eightyfive_raw"]),
                "--enable-shadow-label-alignment",
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    assert (output_dir / "shared_peak_identity_shadow_labels.tsv").exists()
    assert (
        output_dir / "shared_peak_identity_shadow_alignment_summary.tsv"
    ).exists()
    assert (
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    ).exists()
    readiness = _read_tsv(output_dir / "shared_peak_identity_v2_readiness.tsv")[0]
    assert readiness["v2_gate_status"] == "exploratory_only"
    assert readiness["machine_only_labeler_ready"] == "FALSE"
    assert readiness["machine_evidence_basis"] == "machine_proxy_or_manual_derived"
    assert "formal_shape_metric" in readiness["machine_evidence_blockers"]
    assert readiness["semantic_generalization_evidence"] == (
        "seed_only_manual_oracle_derived"
    )
    assert "blast_radius_not_current" in readiness["clear_answer"]
    report = (output_dir / "shared_peak_identity_v2_report.md").read_text(
        encoding="utf-8"
    )
    assert "exploratory_only" in report
    assert "production_ready" not in report
    assert "Machine Evidence Provenance" in report


def test_cli_writes_v2_machine_observed_support_with_optional_evidence(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--cwt-shape-evidence-tsv",
                str(fixture["cwt"]),
                "--tier2-trace-evidence-tsv",
                str(fixture["tier2_trace"]),
                "--candidate-ms2-pattern-evidence-tsv",
                str(fixture["candidate_ms2"]),
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    readiness = _read_tsv(output_dir / "shared_peak_identity_v2_readiness.tsv")[0]
    assert readiness["machine_evidence_basis"] == "machine_observed_sufficient"
    assert readiness["machine_observed_partial_rows"] == "0"
    assert readiness["machine_evidence_supported_rows"] == "1"
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert support["shape_basis_status"] == "machine_observed"
    assert support["opportunity_basis_status"] == "machine_observed"
    assert support["evidence_support_status"] == "machine_observed_sufficient"
    assert "formal_shape_metric" not in support["missing_machine_evidence"]
    assert "candidate_ms2_pattern_status=supportive" in support[
        "observed_machine_metrics"
    ]
    assert support["missing_machine_evidence"] == ""


def test_cli_accepts_ms1_pattern_and_matrix_rt_drift_sidecars(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--cwt-shape-evidence-tsv",
                str(fixture["cwt"]),
                "--ms1-pattern-coherence-evidence-tsv",
                str(fixture["ms1_pattern"]),
                "--matrix-rt-drift-policy-tsv",
                str(fixture["matrix_drift"]),
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert support["pattern_basis_status"] == "machine_observed"
    assert "formal_pattern_metric" not in support["missing_machine_evidence"]
    assert "ms1_pattern_status=supportive" in support["observed_machine_metrics"]
    assert "matrix_rt_drift_status=rt_close" in support["observed_machine_metrics"]


def test_cli_can_generate_ms1_pattern_coherence_evidence(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--cwt-shape-evidence-tsv",
                str(fixture["cwt"]),
                "--tier2-trace-evidence-tsv",
                str(fixture["tier2_trace"]),
                "--generate-ms1-pattern-coherence-evidence",
                "--generate-matrix-rt-drift-policy",
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    generated = (
        output_dir / "shared_peak_identity_ms1_pattern_coherence_evidence.tsv"
    )
    assert generated.exists()
    generated_rows = _read_tsv(generated)
    assert generated_rows[0]["ms1_pattern_status"] == "supportive"
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert "formal_pattern_metric" not in support["missing_machine_evidence"]
    assert "ms1_pattern_status=supportive" in support["observed_machine_metrics"]


def test_cli_can_generate_ms1_pattern_with_raw_overlay_shape_metrics(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--generate-ms1-pattern-coherence-evidence",
                "--ms1-pattern-coherence-overlay-trace-data-json",
                str(fixture["overlay_trace_data"]),
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    generated = (
        output_dir / "shared_peak_identity_ms1_pattern_coherence_evidence.tsv"
    )
    generated_rows = _read_tsv(generated)
    assert generated_rows[0]["ms1_pattern_evidence_level"] == "trace_constellation"
    assert generated_rows[0]["shape_correlation_score"] == "0.94"
    assert generated_rows[0]["shape_metric_source"] == (
        "family_ms1_overlay_raw_trace"
    )
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert "formal_shape_metric" not in support["missing_machine_evidence"]
    assert "formal_pattern_metric" not in support["missing_machine_evidence"]
    assert "ms1_shape_metric_source=family_ms1_overlay_raw_trace" in support[
        "observed_machine_metrics"
    ]
    assert support["evidence_support_status"] == "machine_observed_sufficient"


def test_cli_can_generate_candidate_ms2_pattern_evidence_from_batch_index(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--cwt-shape-evidence-tsv",
                str(fixture["cwt"]),
                "--tier2-trace-evidence-tsv",
                str(fixture["tier2_trace"]),
                "--candidate-ms2-pattern-batch-index",
                str(fixture["batch_index"]),
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    generated = output_dir / "shared_peak_identity_candidate_ms2_pattern_evidence.tsv"
    assert generated.exists()
    generated_rows = _read_tsv(generated)
    assert generated_rows[0]["candidate_ms2_pattern_status"] == "supportive"
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert "candidate_ms2_pattern_status=supportive" in support[
        "observed_machine_metrics"
    ]
    assert support["evidence_support_status"] == "machine_observed_sufficient"


def test_cli_can_generate_matrix_rt_drift_policy_from_existing_artifacts(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--cwt-shape-evidence-tsv",
                str(fixture["cwt"]),
                "--ms1-pattern-coherence-evidence-tsv",
                str(fixture["ms1_pattern"]),
                "--matrix-rt-drift-policy-owner-edge-tsv",
                str(fixture["owner_edge"]),
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    generated = output_dir / "shared_peak_identity_matrix_rt_drift_policy.tsv"
    assert generated.exists()
    generated_rows = _read_tsv(generated)
    assert generated_rows[0]["matrix_rt_drift_status"] == "rt_close"
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert "matrix_rt_drift_status=rt_close" in support["observed_machine_metrics"]


def test_cli_can_generate_matrix_rt_drift_policy_without_external_drift_artifacts(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--generate-matrix-rt-drift-policy",
            ]
        )
        == 0
    )

    generated = (
        tmp_path / "out" / "shared_peak_identity_matrix_rt_drift_policy.tsv"
    )
    assert generated.exists()
    assert _read_tsv(generated)[0]["matrix_rt_drift_status"] == "rt_close"


def test_cli_generated_matrix_rt_drift_policy_closes_rt_drift_blocker(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)
    _write_oracle(
        fixture["oracle"],
        manual_reason_tags="shape_complete;pattern_similar;rt_drift_possible",
    )
    _write_cells(fixture["cells"], apex_rt="8.0", rt_delta_sec="95.0")
    _write_owner_edge(
        fixture["owner_edge"],
        left_rt_min="8.0",
        rt_raw_delta_sec="93.0",
        rt_drift_corrected_delta_sec="4.0",
    )

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--cwt-shape-evidence-tsv",
                str(fixture["cwt"]),
                "--ms1-pattern-coherence-evidence-tsv",
                str(fixture["ms1_pattern"]),
                "--matrix-rt-drift-policy-owner-edge-tsv",
                str(fixture["owner_edge"]),
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    generated_rows = _read_tsv(
        output_dir / "shared_peak_identity_matrix_rt_drift_policy.tsv"
    )
    assert generated_rows[0]["matrix_rt_drift_status"] == "drift_supported"
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert "matrix_rt_drift_policy" not in support["missing_machine_evidence"]
    assert "matrix_rt_drift_status=drift_supported" in support[
        "observed_machine_metrics"
    ]


def test_cli_generated_matrix_rt_drift_policy_uses_anchor_local_trend(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)
    _write_oracle(
        fixture["oracle"],
        manual_reason_tags="shape_complete;pattern_similar;rt_drift_possible",
    )
    _write_cells(fixture["cells"], apex_rt="8.0", rt_delta_sec="95.0")
    targeted_summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    leave_one_out = tmp_path / "rt_normalization_leave_one_anchor_out.tsv"
    rt_trend = tmp_path / "d3_n6_meda_rt_by_injection_order.tsv"
    phase_summary = tmp_path / "d3_n6_meda_injection_phase_summary.tsv"
    _write_targeted_istd_summary(
        targeted_summary,
        targeted_positive_count="85",
        coverage_denominator_count="85",
        sample_rt_p95_abs_delta_min="0.12",
    )
    _write_rt_normalization_leave_one_anchor_out(
        leave_one_out,
        evaluated_count="85",
        p95_abs_error_min="0.05",
        status="PASS",
    )
    _write_istd_rt_trend(rt_trend)
    _write_istd_phase_summary(phase_summary)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--candidate-gate-tsv",
                str(fixture["gate"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--cwt-shape-evidence-tsv",
                str(fixture["cwt"]),
                "--ms1-pattern-coherence-evidence-tsv",
                str(fixture["ms1_pattern"]),
                "--matrix-rt-drift-policy-targeted-istd-summary-tsv",
                str(targeted_summary),
                "--matrix-rt-drift-policy-rt-normalization-leave-one-out-tsv",
                str(leave_one_out),
                "--matrix-rt-drift-policy-istd-rt-trend-tsv",
                str(rt_trend),
                "--matrix-rt-drift-policy-istd-phase-summary-tsv",
                str(phase_summary),
            ]
        )
        == 0
    )

    output_dir = tmp_path / "out"
    generated_rows = _read_tsv(
        output_dir / "shared_peak_identity_matrix_rt_drift_policy.tsv"
    )
    assert generated_rows[0]["matrix_rt_drift_status"] == "drift_supported"
    assert generated_rows[0]["drift_reference_source"] == (
        "targeted_istd_benchmark+rt_normalization_leave_one_anchor_out"
    )
    assert generated_rows[0]["istd_trend_injection_order_span"] == "1-91"
    assert str(rt_trend) in generated_rows[0]["drift_reference_artifacts"]
    assert str(phase_summary) in generated_rows[0]["drift_reference_artifacts"]
    support = _read_tsv(
        output_dir / "shared_peak_identity_machine_evidence_support.tsv"
    )[0]
    assert "matrix_rt_drift_policy" not in support["missing_machine_evidence"]
    assert "drift_evidence_level=sample_istd_aligned" in support[
        "observed_machine_metrics"
    ]
    assert "istd_trend_injection_order_span=1-91" in support[
        "observed_machine_metrics"
    ]


def test_cli_rejects_direct_and_generated_matrix_rt_drift_policy(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--matrix-rt-drift-policy-tsv",
                str(fixture["matrix_drift"]),
                "--matrix-rt-drift-policy-owner-edge-tsv",
                str(fixture["owner_edge"]),
            ]
        )
        == 2
    )


def test_cli_rejects_direct_and_generated_ms1_pattern_coherence(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--ms1-pattern-coherence-evidence-tsv",
                str(fixture["ms1_pattern"]),
                "--generate-ms1-pattern-coherence-evidence",
            ]
        )
        == 2
    )


def test_cli_rejects_candidate_ms2_raw_fallback_without_batch_index(
    tmp_path: Path,
) -> None:
    fixture = _write_cli_fixture(tmp_path)

    assert (
        main(
            [
                "--manual-oracle-tsv",
                str(fixture["oracle"]),
                "--alignment-review-tsv",
                str(fixture["review"]),
                "--alignment-cells-tsv",
                str(fixture["cells"]),
                "--output-dir",
                str(tmp_path / "out"),
                "--enable-shadow-label-alignment",
                "--candidate-ms2-pattern-raw-dll-dir",
                str(tmp_path),
            ]
        )
        == 2
    )


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_cli_fixture(tmp_path: Path) -> dict[str, Path]:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    oracle = inputs / "manual_oracle.tsv"
    review = inputs / "alignment_review.tsv"
    cells = inputs / "alignment_cells.tsv"
    gate = inputs / "candidate_gate.tsv"
    cwt = inputs / "cwt_shape.tsv"
    tier2_trace = inputs / "tier2_trace.tsv"
    candidate_ms2 = inputs / "candidate_ms2.tsv"
    ms1_pattern = inputs / "ms1_pattern.tsv"
    matrix_drift = inputs / "matrix_rt_drift.tsv"
    owner_edge = inputs / "owner_edge_evidence.tsv"
    overlay_trace_data = inputs / "fam001_overlay_trace_data.json"
    batch_index = inputs / "discovery_batch_index.csv"
    discovery_dir = inputs / "S1"
    discovery_dir.mkdir()
    discovery_candidates = discovery_dir / "discovery_candidates.csv"
    _write_oracle(oracle)
    _write_review(review)
    _write_cells(cells)
    _write_candidate_gate(gate)
    _write_cwt_shape(cwt)
    _write_tier2_trace(tier2_trace)
    _write_candidate_ms2(candidate_ms2)
    _write_ms1_pattern(ms1_pattern)
    _write_matrix_rt_drift(matrix_drift)
    _write_owner_edge(owner_edge)
    _write_overlay_trace_data(overlay_trace_data)
    _write_discovery_batch_index(batch_index, discovery_candidates)
    _write_discovery_candidates(discovery_candidates)
    eight_raw = _write_blast_radius_run(tmp_path / "8raw")
    eightyfive_raw = _write_blast_radius_run(tmp_path / "85raw")
    return {
        "oracle": oracle,
        "review": review,
        "cells": cells,
        "gate": gate,
        "cwt": cwt,
        "tier2_trace": tier2_trace,
        "candidate_ms2": candidate_ms2,
        "ms1_pattern": ms1_pattern,
        "matrix_drift": matrix_drift,
        "owner_edge": owner_edge,
        "overlay_trace_data": overlay_trace_data,
        "batch_index": batch_index,
        "eight_raw": eight_raw,
        "eightyfive_raw": eightyfive_raw,
    }


def _write_oracle(
    path: Path,
    *,
    manual_reason_tags: str = "shape_complete;pattern_similar",
) -> None:
    row = {column: "" for column in ORACLE_COLUMNS}
    row.update(
        {
            "oracle_schema_version": ORACLE_SCHEMA_VERSION,
            "oracle_row_id": "FAM001|S1",
            "feature_family_id": "FAM001",
            "sample_id": "S1",
            "manual_label": "pass",
            "manual_label_source": "direct_eic_ms2_review",
            "manual_confidence": "high",
            "manual_scope": "reviewed_cell",
            "manual_reason_tags": manual_reason_tags,
            "reviewed_eic": "TRUE",
            "reviewed_ms2_pattern": "TRUE",
            "reviewed_nl_or_product_pattern": "FALSE",
            "reviewed_intensity_opportunity": "TRUE",
            "dda_opportunity_basis": "observed",
            "manual_review_note": "tiny fixture",
            "manual_review_source": "unit_test",
            "manual_reviewed_at": "2026-05-29",
        }
    )
    _write_tsv(path, ORACLE_COLUMNS, [row])


def _write_review(path: Path) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "identity_decision",
            "identity_reason",
            "row_flags",
            "family_center_mz",
            "family_product_mz",
            "family_observed_neutral_loss_da",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "identity_decision": "review",
                "identity_reason": "context",
                "row_flags": "",
                "family_center_mz": "257.125",
                "family_product_mz": "141.077",
                "family_observed_neutral_loss_da": "116.047",
            }
        ],
    )


def _write_cells(
    path: Path,
    *,
    apex_rt: str = "1.0",
    rt_delta_sec: str = "0.0",
) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "status",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "rt_delta_sec",
            "trace_quality",
            "scan_support_score",
            "source_candidate_id",
            "reason",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "selected",
                "apex_rt": apex_rt,
                "peak_start_rt": "0.9",
                "peak_end_rt": "1.1",
                "rt_delta_sec": rt_delta_sec,
                "trace_quality": "clean",
                "scan_support_score": "1.0",
                "source_candidate_id": "S1#100",
                "reason": "supported",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "selected",
                "apex_rt": "1.01",
                "peak_start_rt": "0.91",
                "peak_end_rt": "1.11",
                "rt_delta_sec": "0.6",
                "trace_quality": "clean",
                "scan_support_score": "1.0",
                "source_candidate_id": "S2#100",
                "reason": "supported",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S3",
                "status": "selected",
                "apex_rt": "0.99",
                "peak_start_rt": "0.89",
                "peak_end_rt": "1.09",
                "rt_delta_sec": "-0.6",
                "trace_quality": "clean",
                "scan_support_score": "1.0",
                "source_candidate_id": "S3#100",
                "reason": "supported",
            }
        ],
    )


def _write_candidate_gate(path: Path) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "candidate_gate_status",
            "recommended_action",
            "challenge_blockers",
            "dependent_context",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "candidate_gate_status": "detected",
                "recommended_action": "no_action",
                "challenge_blockers": "",
                "dependent_context": "unit_test",
            }
        ],
    )


def _write_cwt_shape(path: Path) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "cwt_status",
            "cwt_nearest_apex_rt",
            "cwt_apex_delta_sec",
            "cwt_boundary_width_sec",
            "cwt_prominence",
            "cwt_region_scan_count",
            "cwt_quality_flags",
            "cwt_shape_status",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "cwt_status": "OK",
                "cwt_nearest_apex_rt": "1.0",
                "cwt_apex_delta_sec": "0.0",
                "cwt_boundary_width_sec": "6.0",
                "cwt_prominence": "1000",
                "cwt_region_scan_count": "5",
                "cwt_quality_flags": "",
                "cwt_shape_status": "cwt_near_expected",
            }
        ],
    )


def _write_tier2_trace(path: Path) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "raw_trace_reread_status",
            "scan_support_score",
            "trace_scan_count",
            "scan_availability_score",
            "trace_signal_to_noise_proxy",
            "trace_apex_prominence_score",
            "challenge_blockers",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "raw_trace_reread_status": "pass",
                "scan_support_score": "1",
                "trace_scan_count": "5",
                "scan_availability_score": "1",
                "trace_signal_to_noise_proxy": "3.0",
                "trace_apex_prominence_score": "0.5",
                "challenge_blockers": "",
            }
        ],
    )


def _write_candidate_ms2(path: Path) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "candidate_ms2_pattern_status",
            "candidate_ms2_evidence_level",
            "candidate_ms2_similarity_score",
            "matched_product_count",
            "matched_neutral_loss_count",
            "apex_ms2_delta_sec",
            "ms2_alignment_source",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "candidate_ms2_pattern_status": "supportive",
                "candidate_ms2_evidence_level": "sample_candidate_aligned",
                "candidate_ms2_similarity_score": "0.91",
                "matched_product_count": "3",
                "matched_neutral_loss_count": "1",
                "apex_ms2_delta_sec": "3.0",
                "ms2_alignment_source": "unit_test_sidecar",
            }
        ],
    )


def _write_ms1_pattern(path: Path) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "ms1_pattern_status",
            "ms1_pattern_evidence_level",
            "apex_coherence_sec",
            "boundary_overlap_score",
            "shape_correlation_score",
            "relative_pattern_stability_score",
            "local_interference_score",
            "constellation_peak_count",
            "reference_peak_count",
            "drift_compatible_status",
            "reason",
            "diagnostic_only",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "ms1_pattern_status": "supportive",
                "ms1_pattern_evidence_level": "sample_constellation",
                "apex_coherence_sec": "2.5",
                "boundary_overlap_score": "0.85",
                "shape_correlation_score": "0.92",
                "relative_pattern_stability_score": "0.75",
                "local_interference_score": "0.04",
                "constellation_peak_count": "3",
                "reference_peak_count": "3",
                "drift_compatible_status": "compatible",
                "reason": "unit_test_ms1_constellation",
                "diagnostic_only": "TRUE",
            }
        ],
    )


def _write_matrix_rt_drift(path: Path) -> None:
    _write_tsv(
        path,
        (
            "feature_family_id",
            "sample_stem",
            "matrix_rt_drift_status",
            "drift_evidence_level",
            "raw_rt_delta_sec",
            "drift_corrected_delta_sec",
            "matrix_shift_sec",
            "drift_reference_count",
            "drift_reference_source",
            "drift_compatible_status",
            "reason",
            "diagnostic_only",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "matrix_rt_drift_status": "rt_close",
                "drift_evidence_level": "sample_istd_aligned",
                "raw_rt_delta_sec": "0.0",
                "drift_corrected_delta_sec": "0.0",
                "matrix_shift_sec": "0.0",
                "drift_reference_count": "3",
                "drift_reference_source": "sample_istd_trend",
                "drift_compatible_status": "compatible",
                "reason": "unit_test_rt_close",
                "diagnostic_only": "TRUE",
            }
        ],
    )


def _write_overlay_trace_data(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "rt_min": 0.5,
                "rt_max": 1.5,
                "evidence_summary": {
                    "family_verdict": "ms1_shape_supports_family_backfill"
                },
                "traces": [
                    {
                        "sample_stem": "S1",
                        "status": "rescued",
                        "cell_apex_rt": 1.0,
                        "apex_aligned_shape_similarity": 0.94,
                        "local_window_to_global_max_ratio": 0.98,
                        "local_window_apex_delta_min": 0.01,
                        "global_trace_apex_delta_min": 0.02,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_owner_edge(
    path: Path,
    *,
    left_rt_min: str = "1.0",
    rt_raw_delta_sec: str = "6.0",
    rt_drift_corrected_delta_sec: str = "1.0",
) -> None:
    _write_tsv(
        path,
        (
            "left_sample_stem",
            "right_sample_stem",
            "left_precursor_mz",
            "right_precursor_mz",
            "left_rt_min",
            "right_rt_min",
            "decision",
            "rt_raw_delta_sec",
            "rt_drift_corrected_delta_sec",
            "drift_prior_source",
            "reason",
        ),
        [
            {
                "left_sample_stem": "S1",
                "right_sample_stem": "QC5",
                "left_precursor_mz": "257.125",
                "right_precursor_mz": "257.126",
                "left_rt_min": left_rt_min,
                "right_rt_min": "1.1",
                "decision": "strong_edge",
                "rt_raw_delta_sec": rt_raw_delta_sec,
                "rt_drift_corrected_delta_sec": rt_drift_corrected_delta_sec,
                "drift_prior_source": "targeted_istd_trend",
                "reason": "unit_test_edge",
            }
        ],
    )


def _write_targeted_istd_summary(
    path: Path,
    *,
    targeted_positive_count: str,
    coverage_denominator_count: str,
    sample_rt_p95_abs_delta_min: str,
) -> None:
    _write_tsv(
        path,
        (
            "target_label",
            "role",
            "active_tag",
            "targeted_positive_count",
            "coverage_denominator_count",
            "primary_match_count",
            "selected_feature_id",
            "sample_rt_p95_abs_delta_min",
        ),
        [
            {
                "target_label": "d3-N6-medA",
                "role": "ISTD",
                "active_tag": "TRUE",
                "targeted_positive_count": targeted_positive_count,
                "coverage_denominator_count": coverage_denominator_count,
                "primary_match_count": "1",
                "selected_feature_id": "FAM001",
                "sample_rt_p95_abs_delta_min": sample_rt_p95_abs_delta_min,
            }
        ],
    )


def _write_rt_normalization_leave_one_anchor_out(
    path: Path,
    *,
    evaluated_count: str,
    p95_abs_error_min: str,
    status: str,
) -> None:
    _write_tsv(
        path,
        (
            "target_label",
            "evaluated_count",
            "p95_abs_error_min",
            "status",
        ),
        [
            {
                "target_label": "d3-N6-medA",
                "evaluated_count": evaluated_count,
                "p95_abs_error_min": p95_abs_error_min,
                "status": status,
            }
        ],
    )


def _write_istd_rt_trend(path: Path) -> None:
    _write_tsv(
        path,
        (
            "target_label",
            "sample_stem",
            "injection_order",
            "injection_phase",
            "observed_rt_min",
        ),
        [
            {
                "target_label": "d3-N6-medA",
                "sample_stem": "QC1",
                "injection_order": "1",
                "injection_phase": "early",
                "observed_rt_min": "24.1827",
            },
            {
                "target_label": "d3-N6-medA",
                "sample_stem": "NormalBC2312_DNA",
                "injection_order": "52",
                "injection_phase": "mid",
                "observed_rt_min": "25.7525",
            },
            {
                "target_label": "d3-N6-medA",
                "sample_stem": "TumorBC2264_DNA",
                "injection_order": "91",
                "injection_phase": "late",
                "observed_rt_min": "26.3365",
            },
        ],
    )


def _write_istd_phase_summary(path: Path) -> None:
    _write_tsv(
        path,
        (
            "target_label",
            "injection_phase",
            "sample_count",
            "injection_order_min",
            "injection_order_max",
            "observed_rt_min_min",
            "observed_rt_median_min",
            "observed_rt_max_min",
            "observed_rt_iqr_min",
        ),
        [
            {
                "target_label": "d3-N6-medA",
                "injection_phase": "early",
                "sample_count": "1",
                "injection_order_min": "1",
                "injection_order_max": "31",
                "observed_rt_min_min": "24.1827",
                "observed_rt_median_min": "24.6903",
                "observed_rt_max_min": "25.9377",
                "observed_rt_iqr_min": "0.6349",
            },
            {
                "target_label": "d3-N6-medA",
                "injection_phase": "overall",
                "sample_count": "3",
                "injection_order_min": "1",
                "injection_order_max": "91",
                "observed_rt_min_min": "24.1827",
                "observed_rt_median_min": "25.7525",
                "observed_rt_max_min": "26.3365",
                "observed_rt_iqr_min": "1.1149",
            },
        ],
    )


def _write_discovery_batch_index(path: Path, candidate_csv: Path) -> None:
    _write_csv(
        path,
        ("sample_stem", "raw_file", "candidate_csv"),
        [
            {
                "sample_stem": "S1",
                "raw_file": "S1.raw",
                "candidate_csv": str(candidate_csv),
            }
        ],
    )


def _write_discovery_candidates(path: Path) -> None:
    _write_csv(
        path,
        (
            "review_priority",
            "evidence_tier",
            "evidence_score",
            "ms2_support",
            "ms1_support",
            "rt_alignment",
            "family_context",
            "candidate_id",
            "feature_family_id",
            "feature_family_size",
            "feature_superfamily_id",
            "feature_superfamily_size",
            "feature_superfamily_role",
            "feature_superfamily_confidence",
            "feature_superfamily_evidence",
            "precursor_mz",
            "product_mz",
            "observed_neutral_loss_da",
            "best_seed_rt",
            "seed_event_count",
            "ms1_peak_found",
            "ms1_apex_rt",
            "ms1_area",
            "ms2_product_max_intensity",
            "reason",
            "raw_file",
            "sample_stem",
            "best_ms2_scan_id",
            "seed_scan_ids",
            "neutral_loss_tag",
            "configured_neutral_loss_da",
            "neutral_loss_mass_error_ppm",
            "rt_seed_min",
            "rt_seed_max",
            "ms1_search_rt_min",
            "ms1_search_rt_max",
            "ms1_seed_delta_min",
            "ms1_peak_rt_start",
            "ms1_peak_rt_end",
            "ms1_height",
            "ms1_trace_quality",
            "ms1_scan_support_score",
            "selected_tag_count",
            "matched_tag_count",
            "matched_tag_names",
            "primary_tag_name",
            "tag_combine_mode",
            "tag_intersection_status",
            "tag_evidence_json",
        ),
        [
            {
                "review_priority": "MEDIUM",
                "evidence_tier": "C",
                "evidence_score": "48",
                "ms2_support": "moderate",
                "ms1_support": "weak",
                "rt_alignment": "aligned",
                "family_context": "singleton",
                "candidate_id": "S1#100",
                "feature_family_id": "S1@F001",
                "feature_family_size": "1",
                "feature_superfamily_id": "S1@SF001",
                "feature_superfamily_size": "1",
                "feature_superfamily_role": "representative",
                "feature_superfamily_confidence": "high",
                "feature_superfamily_evidence": "singleton",
                "precursor_mz": "257.125",
                "product_mz": "141.077",
                "observed_neutral_loss_da": "116.047",
                "best_seed_rt": "1.0",
                "seed_event_count": "1",
                "ms1_peak_found": "TRUE",
                "ms1_apex_rt": "1.0",
                "ms1_area": "1000",
                "ms2_product_max_intensity": "5000",
                "reason": "single MS2 NL seed; MS1 peak found",
                "raw_file": "S1.raw",
                "sample_stem": "S1",
                "best_ms2_scan_id": "100",
                "seed_scan_ids": "100",
                "neutral_loss_tag": "DNA_dR",
                "configured_neutral_loss_da": "116.047",
                "neutral_loss_mass_error_ppm": "0.5",
                "rt_seed_min": "1.0",
                "rt_seed_max": "1.0",
                "ms1_search_rt_min": "0.5",
                "ms1_search_rt_max": "1.5",
                "ms1_seed_delta_min": "0.0",
                "ms1_peak_rt_start": "0.9",
                "ms1_peak_rt_end": "1.1",
                "ms1_height": "100",
                "ms1_trace_quality": "clean",
                "ms1_scan_support_score": "1",
                "selected_tag_count": "1",
                "matched_tag_count": "1",
                "matched_tag_names": "DNA_dR",
                "primary_tag_name": "DNA_dR",
                "tag_combine_mode": "any",
                "tag_intersection_status": "single_tag",
                "tag_evidence_json": "{}",
            }
        ],
    )


def _write_blast_radius_run(run_dir: Path) -> Path:
    run_dir.mkdir()
    _write_review(run_dir / "alignment_review.tsv")
    _write_tsv(
        run_dir / "alignment_cells.tsv",
        (
            "feature_family_id",
            "sample_stem",
            "status",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "rt_delta_sec",
            "trace_quality",
            "scan_support_score",
            "reason",
        ),
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "selected",
                "apex_rt": "1.0",
                "peak_start_rt": "0.9",
                "peak_end_rt": "1.1",
                "rt_delta_sec": "0.0",
                "trace_quality": "clean",
                "scan_support_score": "1.0",
                "reason": "supported",
            },
            {
                "feature_family_id": "FAM002",
                "sample_stem": "S2",
                "status": "missing",
                "apex_rt": "",
                "peak_start_rt": "",
                "peak_end_rt": "",
                "rt_delta_sec": "",
                "trace_quality": "low",
                "scan_support_score": "0.0",
                "reason": "no local MS1 owner",
            },
        ],
    )
    return run_dir


def _write_expected_manifest(path: Path, artifacts: dict[str, Path]) -> None:
    rows = []
    for artifact_id, artifact_path in artifacts.items():
        rows.append(
            {
                "artifact_id": artifact_id,
                "artifact_role": "alignment_cells"
                if artifact_id.endswith("_cells")
                else "alignment_review",
                "expected_artifact_sha256": hashlib.sha256(
                    artifact_path.read_bytes()
                )
                .hexdigest()
                .upper(),
            }
        )
    _write_tsv(
        path,
        ("artifact_id", "artifact_role", "expected_artifact_sha256"),
        rows,
    )


def _write_tsv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    _write_delimited(path, fieldnames, rows, delimiter="\t")


def _write_csv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
) -> None:
    _write_delimited(path, fieldnames, rows, delimiter=",")


def _write_delimited(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, str]],
    *,
    delimiter: str,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
