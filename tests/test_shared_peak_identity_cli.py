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
    _write_oracle(oracle)
    _write_review(review)
    _write_cells(cells)
    _write_candidate_gate(gate)
    eight_raw = _write_blast_radius_run(tmp_path / "8raw")
    eightyfive_raw = _write_blast_radius_run(tmp_path / "85raw")
    return {
        "oracle": oracle,
        "review": review,
        "cells": cells,
        "gate": gate,
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
            "manual_reason_tags": "shape_complete",
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
        ("feature_family_id", "identity_decision", "identity_reason", "row_flags"),
        [
            {
                "feature_family_id": "FAM001",
                "identity_decision": "review",
                "identity_reason": "context",
                "row_flags": "",
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
