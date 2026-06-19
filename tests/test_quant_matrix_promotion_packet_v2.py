import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.build_quant_matrix_promotion_packet_v2 as packet_v2_module
from scripts.build_quant_matrix_promotion_packet_v2 import (
    PROMOTION_PACKET_V2_SUMMARY_SCHEMA,
    build_quant_matrix_promotion_packet_v2,
    validate_quant_matrix_promotion_packet_v2,
)
from scripts.build_quant_matrix_real_bundle import build_quant_matrix_real_bundle
from tests.test_quant_matrix_real_bundle import _write_source_run_fixture
from xic_extractor.tabular_io import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "docs/superpowers/specs/quant_matrix_promotion_packet_v2_schema.v1.json"
)


def test_promotion_packet_v2_schema_matches_builder_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["schema_version"] == "quant_matrix_promotion_packet_v2_schema_v1"
    assert (
        schema["promotion_packet_v2_summary_schema"]
        == PROMOTION_PACKET_V2_SUMMARY_SCHEMA
    )
    assert schema["binding_rules"]["real_bundle_must_validate"] is True
    assert schema["binding_rules"]["validation_packet_must_validate"] is True
    assert schema["binding_rules"][
        "readiness_must_be_production_ready_candidate_packet"
    ]
    assert schema["authority_rules"]["read_only"] is True
    assert schema["authority_rules"]["write_authority"] is False
    assert schema["authority_rules"]["scorer_ran"] is False
    assert schema["authority_rules"]["raw_or_85raw_ran"] is False
    assert schema["authority_rules"]["product_writer_changed"] is False
    assert schema["authority_rules"]["default_quant_matrix_changed"] is False


def test_promotion_packet_v2_builds_real_bundle_ready_candidate(
    tmp_path: Path,
) -> None:
    fixture = _write_source_run_fixture(tmp_path)
    real_bundle = build_quant_matrix_real_bundle(
        source_run_dir=fixture["source_run"],
        output_dir=fixture["output_dir"],
        repo_root=tmp_path,
        downstream_scope="synthetic_current_authority_replay",
    )
    sources = _write_science_sources(tmp_path)

    outputs = build_quant_matrix_promotion_packet_v2(
        output_dir=tmp_path / "packet_v2",
        source_root=tmp_path,
        real_bundle_summary_json=real_bundle["summary_json"],
        large_cohort_artifact=sources["large"],
        heldout_oracle_artifact=sources["oracle"],
        cohort_id="synthetic_85raw",
        oracle_packet_id="synthetic_oracle",
        expected_source_run_id="synthetic-current-511-authority-replay",
        expected_downstream_scope="synthetic_current_authority_replay",
        expected_accepted_backfill_count=1,
    )

    assert (
        validate_quant_matrix_promotion_packet_v2(
            summary_json=outputs["summary_json"],
            source_root=tmp_path,
            expected_source_run_id="synthetic-current-511-authority-replay",
            expected_downstream_scope="synthetic_current_authority_replay",
            expected_accepted_backfill_count=1,
        )
        == []
    )
    summary = json.loads(outputs["summary_json"].read_text(encoding="utf-8"))
    assert summary["readiness_label"] == "production_ready_candidate_packet"
    assert summary["production_ready"] is True
    assert summary["may_promote_default_quant_matrix"] is True
    assert summary["write_authority"] is False
    assert summary["default_quant_matrix_changed"] is False
    assert summary["raw_or_85raw_ran"] is False
    assert summary["validation_tiers"] == {
        "85raw_large_cohort": "pass",
        "heldout_oracle": "pass",
        "downstream_impact_smoke": "pass",
    }
    assert summary["missing_science_evidence"] == []

    evidence = json.loads(
        outputs["validation_evidence_json"].read_text(encoding="utf-8")
    )
    downstream_row = next(
        row for row in evidence["evidence"] if row["tier"] == "downstream_impact_smoke"
    )
    copied_downstream = outputs["validation_evidence_json"].parent / downstream_row[
        "artifact_path"
    ]
    copied_downstream_payload = json.loads(
        copied_downstream.read_text(encoding="utf-8"),
    )
    copied_downstream_rows = (
        copied_downstream.parent / copied_downstream_payload["row_metrics_tsv"]
    )
    assert copied_downstream_rows.is_file()
    assert not (copied_downstream.parent / "downstream_impact_inputs").exists()
    input_artifacts = copied_downstream_payload["input_artifacts"]
    for field in ("cell_provenance_tsv", "quant_matrix_tsv", "row_summary_tsv"):
        assert input_artifacts[field].startswith("bundle/quant_matrix_version/")
        assert (tmp_path / input_artifacts[field]).is_file()
    assert (
        summary["artifacts"]["real_bundle_readiness_summary_json"]["sha256"]
        == file_sha256(outputs["real_bundle_readiness_summary_json"])
    )


def test_promotion_packet_v2_builds_externalized_real_bundle_cell_provenance(
    tmp_path: Path,
) -> None:
    fixture = _write_source_run_fixture(tmp_path)
    real_bundle = build_quant_matrix_real_bundle(
        source_run_dir=fixture["source_run"],
        output_dir=fixture["output_dir"],
        repo_root=tmp_path,
        downstream_scope="synthetic_current_authority_replay",
    )
    real_bundle["cell_provenance"].unlink()
    sources = _write_science_sources(tmp_path)

    outputs = build_quant_matrix_promotion_packet_v2(
        output_dir=tmp_path / "packet_v2",
        source_root=tmp_path,
        real_bundle_summary_json=real_bundle["summary_json"],
        large_cohort_artifact=sources["large"],
        heldout_oracle_artifact=sources["oracle"],
        cohort_id="synthetic_85raw",
        oracle_packet_id="synthetic_oracle",
        expected_source_run_id="synthetic-current-511-authority-replay",
        expected_downstream_scope="synthetic_current_authority_replay",
        expected_accepted_backfill_count=1,
    )

    assert (
        validate_quant_matrix_promotion_packet_v2(
            summary_json=outputs["summary_json"],
            source_root=tmp_path,
            expected_source_run_id="synthetic-current-511-authority-replay",
            expected_downstream_scope="synthetic_current_authority_replay",
            expected_accepted_backfill_count=1,
        )
        == []
    )
    evidence = json.loads(
        outputs["validation_evidence_json"].read_text(encoding="utf-8")
    )
    downstream_row = next(
        row for row in evidence["evidence"] if row["tier"] == "downstream_impact_smoke"
    )
    copied_downstream = outputs["validation_evidence_json"].parent / downstream_row[
        "artifact_path"
    ]
    copied_downstream_payload = json.loads(
        copied_downstream.read_text(encoding="utf-8"),
    )
    input_artifacts = copied_downstream_payload["input_artifacts"]
    contract = json.loads(
        real_bundle["cell_provenance_summary_json"].read_text(encoding="utf-8"),
    )
    assert (
        input_artifacts["cell_provenance_tsv"]
        == "bundle/quant_matrix_version/cell_provenance.tsv"
    )
    assert not (tmp_path / input_artifacts["cell_provenance_tsv"]).exists()
    assert input_artifacts["cell_provenance_sha256"] == contract["source_sha256"]

    readiness = json.loads(
        outputs["real_bundle_readiness_summary_json"].read_text(encoding="utf-8"),
    )
    readiness_inputs = readiness["input_artifacts"]
    readiness_input_text = "\n".join(str(value) for value in readiness_inputs.values())
    assert "activation_rerun" not in readiness_input_text
    assert "validation_evidence/" not in readiness_input_text
    assert not Path(readiness_inputs["cell_provenance_tsv"]).is_absolute()
    assert not Path(readiness_inputs["validation_evidence_json"]).is_absolute()
    assert readiness_inputs["cell_provenance_tsv"].endswith(
        "bundle/quant_matrix_version/cell_provenance.tsv",
    )
    assert readiness_inputs["validation_evidence_json"].endswith(
        "quant_matrix_validation_evidence_v1.json",
    )


def test_promotion_packet_v2_build_rejects_externalized_provenance_replay_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fixture = _write_source_run_fixture(tmp_path)
    real_bundle = build_quant_matrix_real_bundle(
        source_run_dir=fixture["source_run"],
        output_dir=fixture["output_dir"],
        repo_root=tmp_path,
        downstream_scope="synthetic_current_authority_replay",
    )
    real_bundle["cell_provenance"].unlink()
    sources = _write_science_sources(tmp_path)
    original_run_activation = packet_v2_module.run_activation

    def drifted_run_activation(*args, **kwargs):
        outputs = dict(original_run_activation(*args, **kwargs))
        with outputs["cell_provenance"].open("a", encoding="utf-8") as handle:
            handle.write("# drift\n")
        return outputs

    monkeypatch.setattr(packet_v2_module, "run_activation", drifted_run_activation)

    with pytest.raises(
        ValueError,
        match="promotion packet v2 cell_provenance materialization failed",
    ):
        build_quant_matrix_promotion_packet_v2(
            output_dir=tmp_path / "packet_v2",
            source_root=tmp_path,
            real_bundle_summary_json=real_bundle["summary_json"],
            large_cohort_artifact=sources["large"],
            heldout_oracle_artifact=sources["oracle"],
            cohort_id="synthetic_85raw",
            oracle_packet_id="synthetic_oracle",
            expected_source_run_id="synthetic-current-511-authority-replay",
            expected_downstream_scope="synthetic_current_authority_replay",
            expected_accepted_backfill_count=1,
        )


def test_promotion_packet_v2_rejects_stale_real_bundle_readiness(
    tmp_path: Path,
) -> None:
    outputs = _build_synthetic_packet_v2(tmp_path)
    readiness_summary = outputs["real_bundle_readiness_summary_json"]
    payload = json.loads(readiness_summary.read_text(encoding="utf-8"))
    payload["production_ready"] = False
    readiness_summary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    problems = validate_quant_matrix_promotion_packet_v2(
        summary_json=outputs["summary_json"],
        source_root=tmp_path,
        expected_source_run_id="synthetic-current-511-authority-replay",
        expected_downstream_scope="synthetic_current_authority_replay",
        expected_accepted_backfill_count=1,
    )

    assert any("readiness production_ready must be true" in p for p in problems)
    assert any("readiness summary is stale" in p for p in problems)


def test_promotion_packet_v2_check_accepts_externalized_real_bundle_cell_provenance(
    tmp_path: Path,
) -> None:
    fixture = _write_source_run_fixture(tmp_path)
    real_bundle = build_quant_matrix_real_bundle(
        source_run_dir=fixture["source_run"],
        output_dir=fixture["output_dir"],
        repo_root=tmp_path,
        downstream_scope="synthetic_current_authority_replay",
    )
    sources = _write_science_sources(tmp_path)
    outputs = build_quant_matrix_promotion_packet_v2(
        output_dir=tmp_path / "packet_v2",
        source_root=tmp_path,
        real_bundle_summary_json=real_bundle["summary_json"],
        large_cohort_artifact=sources["large"],
        heldout_oracle_artifact=sources["oracle"],
        cohort_id="synthetic_85raw",
        oracle_packet_id="synthetic_oracle",
        expected_source_run_id="synthetic-current-511-authority-replay",
        expected_downstream_scope="synthetic_current_authority_replay",
        expected_accepted_backfill_count=1,
    )
    real_bundle["cell_provenance"].unlink()

    assert (
        validate_quant_matrix_promotion_packet_v2(
            summary_json=outputs["summary_json"],
            source_root=tmp_path,
            expected_source_run_id="synthetic-current-511-authority-replay",
            expected_downstream_scope="synthetic_current_authority_replay",
            expected_accepted_backfill_count=1,
        )
        == []
    )


def test_promotion_packet_v2_rejects_externalized_provenance_readiness_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fixture = _write_source_run_fixture(tmp_path)
    real_bundle = build_quant_matrix_real_bundle(
        source_run_dir=fixture["source_run"],
        output_dir=fixture["output_dir"],
        repo_root=tmp_path,
        downstream_scope="synthetic_current_authority_replay",
    )
    sources = _write_science_sources(tmp_path)
    outputs = build_quant_matrix_promotion_packet_v2(
        output_dir=tmp_path / "packet_v2",
        source_root=tmp_path,
        real_bundle_summary_json=real_bundle["summary_json"],
        large_cohort_artifact=sources["large"],
        heldout_oracle_artifact=sources["oracle"],
        cohort_id="synthetic_85raw",
        oracle_packet_id="synthetic_oracle",
        expected_source_run_id="synthetic-current-511-authority-replay",
        expected_downstream_scope="synthetic_current_authority_replay",
        expected_accepted_backfill_count=1,
    )
    real_bundle["cell_provenance"].unlink()
    original_evaluate = packet_v2_module.evaluate_quant_matrix_promotion_readiness

    def drifted_evaluate(*args, **kwargs):
        result = dict(original_evaluate(*args, **kwargs))
        summary = json.loads(result["summary_json"].read_text(encoding="utf-8"))
        summary["production_ready"] = False
        result["summary_json"].write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result

    monkeypatch.setattr(
        packet_v2_module,
        "evaluate_quant_matrix_promotion_readiness",
        drifted_evaluate,
    )

    problems = validate_quant_matrix_promotion_packet_v2(
        summary_json=outputs["summary_json"],
        source_root=tmp_path,
        expected_source_run_id="synthetic-current-511-authority-replay",
        expected_downstream_scope="synthetic_current_authority_replay",
        expected_accepted_backfill_count=1,
    )

    assert any("readiness summary is stale" in problem for problem in problems)


def test_promotion_packet_v2_default_check_rejects_non_current_511_bundle(
    tmp_path: Path,
) -> None:
    outputs = _build_synthetic_packet_v2(tmp_path)

    problems = validate_quant_matrix_promotion_packet_v2(
        summary_json=outputs["summary_json"],
        source_root=tmp_path,
    )

    assert any("source_run_id mismatch" in problem for problem in problems)
    assert any("downstream_scope mismatch" in problem for problem in problems)
    assert any("accepted_backfill_count mismatch" in problem for problem in problems)


def test_promotion_packet_v2_script_check_only_round_trip(tmp_path: Path) -> None:
    fixture = _write_source_run_fixture(tmp_path)
    real_bundle = build_quant_matrix_real_bundle(
        source_run_dir=fixture["source_run"],
        output_dir=fixture["output_dir"],
        repo_root=tmp_path,
        downstream_scope="synthetic_current_authority_replay",
    )
    sources = _write_science_sources(tmp_path)
    output_dir = tmp_path / "packet_v2"

    build = subprocess.run(
        [
            sys.executable,
            "scripts/build_quant_matrix_promotion_packet_v2.py",
            "--output-dir",
            str(output_dir),
            "--source-root",
            str(tmp_path),
            "--real-bundle-summary-json",
            str(real_bundle["summary_json"]),
            "--large-cohort-artifact",
            str(sources["large"]),
            "--heldout-oracle-artifact",
            str(sources["oracle"]),
            "--cohort-id",
            "synthetic_85raw",
            "--oracle-packet-id",
            "synthetic_oracle",
            "--expected-source-run-id",
            "synthetic-current-511-authority-replay",
            "--expected-downstream-scope",
            "synthetic_current_authority_replay",
            "--expected-accepted-backfill-count",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    check = subprocess.run(
        [
            sys.executable,
            "scripts/build_quant_matrix_promotion_packet_v2.py",
            "--output-dir",
            str(output_dir),
            "--source-root",
            str(tmp_path),
            "--check-only",
            "--expected-source-run-id",
            "synthetic-current-511-authority-replay",
            "--expected-downstream-scope",
            "synthetic_current_authority_replay",
            "--expected-accepted-backfill-count",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert check.returncode == 0, check.stderr
    assert "promotion_packet_v2_status: pass" in check.stdout


def _build_synthetic_packet_v2(tmp_path: Path) -> dict[str, Path]:
    fixture = _write_source_run_fixture(tmp_path)
    real_bundle = build_quant_matrix_real_bundle(
        source_run_dir=fixture["source_run"],
        output_dir=fixture["output_dir"],
        repo_root=tmp_path,
        downstream_scope="synthetic_current_authority_replay",
    )
    sources = _write_science_sources(tmp_path)
    return dict(
        build_quant_matrix_promotion_packet_v2(
            output_dir=tmp_path / "packet_v2",
            source_root=tmp_path,
            real_bundle_summary_json=real_bundle["summary_json"],
            large_cohort_artifact=sources["large"],
            heldout_oracle_artifact=sources["oracle"],
            cohort_id="synthetic_85raw",
            oracle_packet_id="synthetic_oracle",
            expected_source_run_id="synthetic-current-511-authority-replay",
            expected_downstream_scope="synthetic_current_authority_replay",
            expected_accepted_backfill_count=1,
        )
    )


def _write_science_sources(root: Path) -> dict[str, Path]:
    source_dir = root / "science_sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    large = source_dir / "large_cohort_summary.json"
    oracle = source_dir / "heldout_oracle_summary.json"
    large.write_text('{"large_cohort": true}\n', encoding="utf-8")
    oracle.write_text('{"heldout_oracle": true}\n', encoding="utf-8")
    return {"large": large, "oracle": oracle}
