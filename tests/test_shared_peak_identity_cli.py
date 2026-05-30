from __future__ import annotations

import csv
import hashlib
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
        "batch_index": batch_index,
        "eight_raw": eight_raw,
        "eightyfive_raw": eightyfive_raw,
    }


def _write_oracle(path: Path) -> None:
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
            "manual_reason_tags": "shape_complete;pattern_similar",
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


def _write_cells(path: Path) -> None:
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
                "apex_rt": "1.0",
                "peak_start_rt": "0.9",
                "peak_end_rt": "1.1",
                "rt_delta_sec": "0.0",
                "trace_quality": "clean",
                "scan_support_score": "1.0",
                "source_candidate_id": "S1#100",
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
