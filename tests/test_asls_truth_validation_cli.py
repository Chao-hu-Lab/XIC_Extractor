from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.diagnostics.asls_truth_validation import (
    SyntheticBenchmarkResult,
    main,
)
from tools.diagnostics.asls_truth_validation_inputs import sha256_file
from tools.diagnostics.asls_truth_validation_models import (
    GATE_C1B_PLAN,
    GATE_NO_GO,
    GATE_REQUIRES_TIER_C,
    INCONCLUSIVE_INVALID_INPUT,
    INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE,
    INCONCLUSIVE_REGENERATE_TIER_A,
    TruthValidationOutputs,
)


FIXTURE_DIR = Path("docs/superpowers/fixtures")
TIER_A_MANIFEST = FIXTURE_DIR / "asls_truth_tier_a_expected_manifest.json"
FIXTURE_MANIFEST = FIXTURE_DIR / "asls_truth_validation_fixture_manifest.json"
FIXTURE_LOCK = FIXTURE_DIR / "asls_truth_validation_fixture_lock.json"
ROWS = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit_rows.tsv"
)
SUMMARY = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit_summary.tsv"
)
JSON_REPORT = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit.json"
)
MARKDOWN_REPORT = Path(
    "output/phase1_p2_baseline_truth_audit_all_statuses/"
    "baseline_truth_audit.md"
)


def test_cli_writes_outputs_for_c1b_planning_target(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "out"
    _patch_synthetic_pass(monkeypatch)

    exit_code = main([*_base_args(output_dir), "--decision-target", "c1b-plan"])

    assert exit_code == 3
    outputs = TruthValidationOutputs.from_output_dir(output_dir)
    for path in (
        outputs.rows_tsv,
        outputs.summary_tsv,
        outputs.coverage_tsv,
        outputs.json_path,
        outputs.fixture_manifest_json,
        outputs.fixture_lock_json,
        outputs.tier_a_manifest_json,
        outputs.markdown_path,
    ):
        assert path.exists(), path
    assert _summary(output_dir)["gate_decision"] == GATE_C1B_PLAN
    assert _summary(output_dir)["readiness_status"] == "diagnostic_only"
    payload = _json_payload(output_dir)
    assert payload["schema_version"] == "asls_truth_validation_v2"
    assert payload["provenance"]["command_line"][:2] == [
        "tools.diagnostics.asls_truth_validation",
        "--tier-a-rows",
    ]
    assert payload["provenance"]["code_git_sha"]
    assert payload["inputs"]["fixture_manifest"]["hash"]
    assert payload["inputs"]["fixture_lock"]["object"]["lock_version"]
    assert payload["inputs"]["tier_a"]["artifact_refs"]["rows"] == str(ROWS)
    assert not outputs.tier_c_evidence_json.exists()
    assert not outputs.methodology_waiver_json.exists()
    assert not outputs.retirement_prereq_json.exists()
    assert not outputs.p2b_85raw_acceptance_json.exists()


def test_cli_runs_real_synthetic_benchmark_without_header_only_rows(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "real_synthetic"

    exit_code = main([*_base_args(output_dir), "--decision-target", "c1b-plan"])

    assert exit_code in {1, 3}
    rows = _rows(output_dir)
    assert len(rows) > 0
    assert int(_summary(output_dir)["heldout_row_count"]) > 0
    assert _json_payload(output_dir)["rows"]
    if exit_code == 1:
        assert _summary(output_dir)["gate_decision"] == GATE_NO_GO
        assert _summary(output_dir)["benchmark_status"] == "FAIL"


def test_cli_retirement_target_requires_tier_c_without_optional_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "retirement"
    _patch_synthetic_pass(monkeypatch)

    exit_code = main(
        [*_base_args(output_dir), "--decision-target", "linear-edge-retirement"]
    )

    assert exit_code == 3
    assert _summary(output_dir)["gate_decision"] == GATE_REQUIRES_TIER_C


def test_cli_copies_optional_evidence_when_supplied(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "optional"
    _patch_synthetic_pass(monkeypatch)
    p2b_manifest = _write_json(tmp_path / "p2b_acceptance.json", {"status": "accepted"})
    tier_c = _write_tier_c(tmp_path / "tier_c.json")
    waiver = _write_waiver(tmp_path / "waiver.json")
    prereq = _write_prereq(tmp_path / "prereq.json", tmp_path / "schema.tsv")

    exit_code = main(
        [
            *_base_args(output_dir),
            "--decision-target",
            "c1b-plan",
            "--p2b-85raw-acceptance-manifest",
            str(p2b_manifest),
            "--tier-c-evidence",
            str(tier_c),
            "--methodology-waiver",
            str(waiver),
            "--retirement-prereq-manifest",
            str(prereq),
        ]
    )

    assert exit_code == 3
    outputs = TruthValidationOutputs.from_output_dir(output_dir)
    assert outputs.p2b_85raw_acceptance_json.read_text(encoding="utf-8")
    assert outputs.tier_c_evidence_json.read_text(encoding="utf-8")
    assert outputs.methodology_waiver_json.read_text(encoding="utf-8")
    assert outputs.retirement_prereq_json.read_text(encoding="utf-8")
    summary = _summary(output_dir)
    assert summary["tier_c_axis"] == "spike_in_recovery"
    assert summary["methodology_owner"] == "methodology_owner"
    assert summary["waiver_scope"] == "alignment_matrix.tsv"
    assert summary["waiver_expiry_or_revalidation_trigger"] == "2026-12-31"
    assert summary["c1a_status"] == "PLANNED"
    assert summary["c5_status"] == "LANDED_VALIDATED"
    assert (
        summary["rollback_column_status"]
        == "DEPRECATED_BY_APPROVED_SCHEMA_NOTE"
    )
    payload = _json_payload(output_dir)
    assert payload["inputs"]["p2b_85raw_acceptance"]["hash"]
    assert payload["inputs"]["tier_c_evidence"]["object"]["tier_c_axis"] == "spike_in_recovery"
    assert payload["inputs"]["methodology_waiver"]["object"]["methodology_owner"] == "methodology_owner"
    assert payload["inputs"]["retirement_prerequisites"]["object"]["c5_status"] == "LANDED_VALIDATED"


def test_cli_invalid_waiver_exits_invalid_input(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "invalid_waiver"
    _patch_synthetic_pass(monkeypatch)
    waiver = _write_json(tmp_path / "waiver.json", {"approved": True})

    exit_code = main(
        [
            *_base_args(output_dir),
            "--decision-target",
            "linear-edge-retirement",
            "--methodology-waiver",
            str(waiver),
        ]
    )

    assert exit_code == 2
    assert _summary(output_dir)["gate_decision"] == INCONCLUSIVE_INVALID_INPUT


def test_cli_invalid_tier_a_path_exits_two(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "invalid_tier_a"
    _patch_synthetic_pass(monkeypatch)
    args = _base_args(output_dir)
    args[args.index("--tier-a-rows") + 1] = str(tmp_path / "missing.tsv")

    exit_code = main([*args, "--decision-target", "c1b-plan"])

    assert exit_code == 2


def test_cli_stale_tier_a_hash_exits_two(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "stale_hash"
    _patch_synthetic_pass(monkeypatch)
    stale_manifest = _write_stale_tier_a_manifest(tmp_path / "stale_manifest.json")

    args = _base_args(output_dir)
    args[args.index("--tier-a-manifest") + 1] = str(stale_manifest)
    exit_code = main([*args, "--decision-target", "c1b-plan"])

    assert exit_code == 2
    assert _summary(output_dir)["gate_decision"] == INCONCLUSIVE_REGENERATE_TIER_A


def test_cli_schema_incompatible_tier_a_exits_two(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "bad_schema"
    _patch_synthetic_pass(monkeypatch)
    bad_rows = tmp_path / "bad_rows.tsv"
    _write_tsv_artifact(bad_rows, ["target_label", "feature_family_id"])

    args = _base_args(output_dir)
    args[args.index("--tier-a-rows") + 1] = str(bad_rows)
    exit_code = main([*args, "--decision-target", "c1b-plan"])

    assert exit_code == 2
    assert _summary(output_dir)["gate_decision"] == INCONCLUSIVE_INVALID_INPUT


def test_cli_missing_p2b_85raw_acceptance_exits_two(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "missing_p2b"
    _patch_synthetic_pass(monkeypatch)
    missing_p2b_manifest = _write_tier_a_without_p2b_refs(
        tmp_path / "missing_p2b_manifest.json"
    )

    args = _base_args(output_dir)
    args[args.index("--tier-a-manifest") + 1] = str(missing_p2b_manifest)
    exit_code = main([*args, "--decision-target", "linear-edge-retirement"])

    assert exit_code == 2
    assert _summary(output_dir)["gate_decision"] == INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE


def test_cli_missing_fixture_manifest_writes_audit_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "missing_fixture_manifest"
    _patch_synthetic_pass(monkeypatch)
    args = _base_args(output_dir)
    args[args.index("--fixture-manifest") + 1] = str(tmp_path / "missing.json")

    exit_code = main([*args, "--decision-target", "c1b-plan"])

    assert exit_code == 2
    assert _summary(output_dir)["gate_decision"] == INCONCLUSIVE_INVALID_INPUT
    assert _json_payload(output_dir)["provenance"]["error"]
    assert TruthValidationOutputs.from_output_dir(output_dir).rows_tsv.exists()


def test_cli_fixture_lock_hash_drift_writes_inconclusive_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "lock_drift"
    _patch_synthetic_pass(monkeypatch)
    stale_manifest = _write_fixture_manifest_with_stale_lock_hash(
        tmp_path / "stale_fixture_manifest.json"
    )
    args = _base_args(output_dir)
    args[args.index("--fixture-manifest") + 1] = str(stale_manifest)

    exit_code = main([*args, "--decision-target", "c1b-plan"])

    assert exit_code == 2
    summary = _summary(output_dir)
    assert summary["gate_decision"] == "INCONCLUSIVE_FIXTURE_LOCK_CHANGED"
    assert summary["benchmark_status"] == "INCONCLUSIVE"


def test_cli_records_malformed_optional_json_load_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "malformed_optional"
    _patch_synthetic_pass(monkeypatch)
    waiver = tmp_path / "waiver.json"
    waiver.write_text("[]", encoding="utf-8")

    exit_code = main(
        [
            *_base_args(output_dir),
            "--decision-target",
            "linear-edge-retirement",
            "--methodology-waiver",
            str(waiver),
        ]
    )

    assert exit_code == 2
    payload = _json_payload(output_dir)
    waiver_input = payload["inputs"]["methodology_waiver"]
    assert waiver_input["hash"]
    assert waiver_input["object"] == {}
    assert waiver_input["load_error"]


def _base_args(output_dir: Path) -> list[str]:
    return [
        "--tier-a-rows",
        str(ROWS),
        "--tier-a-summary",
        str(SUMMARY),
        "--tier-a-json",
        str(JSON_REPORT),
        "--tier-a-report",
        str(MARKDOWN_REPORT),
        "--tier-a-manifest",
        str(TIER_A_MANIFEST),
        "--fixture-manifest",
        str(FIXTURE_MANIFEST),
        "--fixture-lock",
        str(FIXTURE_LOCK),
        "--output-dir",
        str(output_dir),
    ]


def _patch_synthetic_pass(monkeypatch) -> None:
    from tools.diagnostics import asls_truth_validation as cli

    monkeypatch.setattr(
        cli,
        "_run_synthetic_benchmark",
        lambda *_args, **_kwargs: SyntheticBenchmarkResult(
            synthetic_decision_status="PASS",
            tier_b1_status="PASS",
            tier_b1_accuracy_scope="RETIREMENT_ELIGIBLE",
            tier_b2_status="PASS",
            fixture_scope_status="PASS",
            legacy_fixture_status="CURRENT",
            rows=(),
            b1_hard_blockers=(),
            b1_cautions=(),
            b2_retirement_blockers=(),
            heldout_row_count=25,
            tier_b1_heldout_row_count=25,
            b1_adjacent_stress_row_count=0,
            tier_b2_heldout_row_count=0,
            production_like_heldout_row_count=25,
            stress_heldout_row_count=0,
            blank_false_positive_rate=0.0,
            blank_not_quantifiable_rate=0.0,
            worst_heldout_median_relative_error_pct=None,
            worst_heldout_p95_relative_error_pct=None,
        ),
    )


def _summary(output_dir: Path) -> dict[str, str]:
    summary_path = TruthValidationOutputs.from_output_dir(output_dir).summary_tsv
    with summary_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 1
    return rows[0]


def _rows(output_dir: Path) -> list[dict[str, str]]:
    rows_path = TruthValidationOutputs.from_output_dir(output_dir).rows_tsv
    with rows_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _json_payload(output_dir: Path) -> dict[str, object]:
    path = TruthValidationOutputs.from_output_dir(output_dir).json_path
    return json.loads(path.read_text(encoding="utf-8"))


def _write_tier_c(path: Path) -> Path:
    return _write_json(
        path,
        {
            "tier_c_axis": "spike_in_recovery",
            "tier_c_status": "PASS",
            "level_count": 3,
            "replicates_per_level": 5,
            "median_recovery_pct": 105.0,
            "evidence_artifacts": [_hashed_ref(MARKDOWN_REPORT)],
            "thresholds_used": ["test"],
            "reviewer_or_generator": "pytest",
            "output_scope": ["alignment_matrix.tsv"],
            "target_classes": ["ISTD"],
            "known_exclusions": [],
        },
    )


def _write_waiver(path: Path) -> Path:
    return _write_json(
        path,
        {
            "methodology_owner": "methodology_owner",
            "approved": True,
            "review_date": "2026-05-27",
            "review_artifact_path": str(MARKDOWN_REPORT),
            "review_artifact_sha256": sha256_file(MARKDOWN_REPORT),
            "blank_carryover_disposition": "accepted_residual_risk",
            "accepted_residual_risks": ["Tier C unavailable"],
            "output_scope": ["alignment_matrix.tsv"],
            "expiry_or_revalidation_trigger": "2026-12-31",
            "waived_decision": "c1b-plan",
            "waived_tier_c_axes": ["spike_in_recovery"],
            "waiver_rationale": "No spike-in series exists for this dataset.",
            "branch_scope": "codex/peak-pipeline-modernization",
            "target_classes": ["ISTD"],
            "sample_classes": ["tissue"],
            "supporting_evidence": [_hashed_ref(MARKDOWN_REPORT)],
            "delete_only_after_c1a_c5_rollback_deprecation": True,
        },
    )


def _write_prereq(path: Path, schema_path: Path) -> Path:
    _write_tsv_artifact(
        schema_path,
        [
            "feature_family_id",
            "sample_stem",
            "status",
            "area",
            "apex_rt",
            "peak_start_rt",
            "peak_end_rt",
            "area_baseline_corrected",
            "area_uncertainty",
            "baseline_type",
            "baseline_score",
            "integration_scan_count",
        ],
    )
    return _write_json(
        path,
        {
            "c1a_status": "PLANNED",
            "c5_status": "LANDED_VALIDATED",
            "rollback_column_status": "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
            "c1a_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "c5_validation_note": _hashed_ref(MARKDOWN_REPORT),
            "rollback_schema_deprecation_note": _hashed_ref(MARKDOWN_REPORT),
            "post_rollback_audit_schema_artifact": _hashed_ref(schema_path),
            "post_rollback_absent_columns": [
                "area_baseline_corrected_linear_edge",
                "baseline_score_linear_edge",
            ],
            "affected_public_contracts_reviewed": ["alignment_cell_integration_audit.tsv"],
            "reviewer_identity": "reviewer",
            "review_date": "2026-05-27",
        },
    )


def _write_json(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_stale_tier_a_manifest(path: Path) -> Path:
    data = json.loads(TIER_A_MANIFEST.read_text(encoding="utf-8"))
    data["artifact_hashes"]["rows"]["sha256"] = "0" * 64
    return _write_json(path, data)


def _write_tier_a_without_p2b_refs(path: Path) -> Path:
    data = json.loads(TIER_A_MANIFEST.read_text(encoding="utf-8"))
    data["p2b_85raw_acceptance_refs"] = []
    return _write_json(path, data)


def _write_fixture_manifest_with_stale_lock_hash(path: Path) -> Path:
    data = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    data["fixture_lock_hash"] = "0" * 64
    return _write_json(path, data)


def _hashed_ref(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": sha256_file(path)}


def _write_tsv_artifact(path: Path, columns: list[str]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(columns)
        writer.writerow(["dummy" for _ in columns])
    return path
