from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.diagnostics.asls_truth_validation_manifests import (
    B1_RELEVANCE_FIXTURE_CLASSES,
    B2_STRESS_FIXTURE_CLASSES,
    REQUIRED_BLANK_HARD_CASE_STRATA,
    REQUIRED_FIXTURE_CLASSES,
    load_fixture_lock,
    load_fixture_manifest,
    load_tier_a_manifest,
)

FIXTURE_DIR = Path("docs/superpowers/fixtures")
TIER_A_MANIFEST = FIXTURE_DIR / "asls_truth_tier_a_expected_manifest.json"
FIXTURE_MANIFEST = FIXTURE_DIR / "asls_truth_validation_fixture_manifest.json"
FIXTURE_LOCK = FIXTURE_DIR / "asls_truth_validation_fixture_lock.json"


def test_tier_a_manifest_has_locked_selected_family_coverage() -> None:
    manifest = load_tier_a_manifest(TIER_A_MANIFEST)

    assert manifest.manifest_version == "asls_truth_tier_a_manifest_v1"
    assert manifest.expected_family_count == 6
    assert manifest.expected_row_count == 48
    assert len(manifest.families) == 6
    assert {row.old_p2_status for row in manifest.families} == {"PASS", "FAIL"}
    assert all(row.expected_row_count == 8 for row in manifest.families)
    assert all(row.expected_sample_count == 8 for row in manifest.families)
    assert manifest.generated_by_git_sha
    assert manifest.current_code_compatibility_status
    assert manifest.p2b_85raw_acceptance_refs
    assert manifest.source_inputs
    assert manifest.generated_by_command
    assert manifest.environment_profile
    assert manifest.expected_dataset_label
    assert manifest.raw_subset == "8RAW selected ISTD audit rows"
    assert manifest.branch_family == "codex/peak-pipeline-modernization"
    assert manifest.p2b_semantic_version
    assert _artifact_hash(manifest.artifact_hashes, "rows")
    assert _artifact_hash(manifest.artifact_hashes, "summary")
    assert _artifact_hash(manifest.artifact_hashes, "json")
    assert _artifact_hash(manifest.artifact_hashes, "report")


def test_tier_a_manifest_rejects_missing_expected_family(tmp_path: Path) -> None:
    data = _load_json(TIER_A_MANIFEST)
    data["expected_families"] = data["expected_families"][:-1]
    path = tmp_path / "tier_a_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="missing Tier A expected families"):
        load_tier_a_manifest(path)


def test_tier_a_manifest_rejects_missing_required_metadata(tmp_path: Path) -> None:
    data = _load_json(TIER_A_MANIFEST)
    del data["generated_by_command"]
    path = tmp_path / "tier_a_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="generated_by_command"):
        load_tier_a_manifest(path)


def test_tier_a_manifest_rejects_empty_p2b_85raw_refs(tmp_path: Path) -> None:
    data = _load_json(TIER_A_MANIFEST)
    data["p2b_85raw_acceptance_refs"] = []
    path = tmp_path / "tier_a_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="p2b_85raw_acceptance_refs"):
        load_tier_a_manifest(path)


def test_tier_a_manifest_rejects_stale_source_hash(tmp_path: Path) -> None:
    data = _load_json(TIER_A_MANIFEST)
    source_inputs = data["source_inputs"]
    assert isinstance(source_inputs, dict)
    p2_rows = source_inputs["p2_gate_rows_tsv"]
    assert isinstance(p2_rows, dict)
    p2_rows["sha256"] = "0" * 64
    path = tmp_path / "tier_a_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="sha256 mismatch"):
        load_tier_a_manifest(path)


def test_tier_a_manifest_rejects_stale_artifact_hash(tmp_path: Path) -> None:
    data = _load_json(TIER_A_MANIFEST)
    artifact_hashes = data["artifact_hashes"]
    assert isinstance(artifact_hashes, dict)
    rows = artifact_hashes["rows"]
    assert isinstance(rows, dict)
    rows["sha256"] = "0" * 64
    path = tmp_path / "tier_a_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="sha256 mismatch"):
        load_tier_a_manifest(path)


def test_tier_a_manifest_rejects_stale_acceptance_ref_hash(tmp_path: Path) -> None:
    data = _load_json(TIER_A_MANIFEST)
    refs = data["p2b_85raw_acceptance_refs"]
    assert isinstance(refs, list)
    ref = refs[0]
    assert isinstance(ref, dict)
    ref["sha256"] = "0" * 64
    path = tmp_path / "tier_a_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="sha256 mismatch"):
        load_tier_a_manifest(path)


def test_tier_a_manifest_resolves_repo_relative_refs_from_other_cwd(
    tmp_path: Path,
) -> None:
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        manifest = load_tier_a_manifest(original_cwd / TIER_A_MANIFEST)
    finally:
        os.chdir(original_cwd)

    assert manifest.expected_family_count == 6


def test_tier_a_manifest_rejects_extra_expected_family(tmp_path: Path) -> None:
    data = _load_json(TIER_A_MANIFEST)
    extra = dict(data["expected_families"][0])
    extra["target_label"] = "extra"
    extra["feature_family_id"] = "FAM_EXTRA"
    data["expected_families"].append(extra)
    data["expected_family_count"] = 7
    data["expected_row_count"] = 56
    path = tmp_path / "tier_a_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected Tier A expected families"):
        load_tier_a_manifest(path)


def test_fixture_manifest_has_required_classes_and_lock_hash() -> None:
    manifest = load_fixture_manifest(FIXTURE_MANIFEST)

    assert manifest.fixture_version == "synthetic_truth_fixture_v2"
    assert manifest.minimum_calibration_replicates_per_class >= 10
    assert manifest.minimum_heldout_replicates_per_class >= 25
    assert manifest.fixture_classes == REQUIRED_FIXTURE_CLASSES
    assert manifest.b1_fixture_classes == B1_RELEVANCE_FIXTURE_CLASSES
    assert manifest.b2_fixture_classes == B2_STRESS_FIXTURE_CLASSES
    assert "flat_peak_control" in manifest.fixture_classes
    assert manifest.tolerance_profile == "asls_truth_tolerance_v2"
    assert manifest.legacy_fixture_status == "CURRENT"
    assert manifest.fixture_scope_status == "PASS"
    assert manifest.gate_layer_by_class["flat_peak_control"] == "B1_RELEVANCE"
    assert manifest.gate_layer_by_class["blank_noise_control"] == "B2_STRESS"
    assert manifest.fixture_lock_hash
    assert "edge" in manifest.required_hard_case_strata_by_class["tailing_peak"]
    assert (
        manifest.required_hard_case_strata_by_class["blank_noise_control"]
        == REQUIRED_BLANK_HARD_CASE_STRATA
    )


def test_fixture_manifest_rejects_lock_hash_mismatch(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    data["fixture_lock_hash"] = "wrong"
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="fixture_lock_hash"):
        load_fixture_manifest(path)


def test_fixture_manifest_rejects_missing_tolerance_rationale(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    del data["fixture_classes"][0]["tolerance_rationale"]
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="missing tolerance_rationale"):
        load_fixture_manifest(path)


def test_fixture_manifest_rejects_missing_parameter_grid_key(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    del data["fixture_classes"][0]["parameter_grid"]["scan_spacing_min"]
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="parameter_grid.scan_spacing_min"):
        load_fixture_manifest(path)


def test_fixture_manifest_rejects_missing_hard_case_strata(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    data["fixture_classes"][0]["required_hard_case_strata"] = []
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="hard-case strata"):
        load_fixture_manifest(path)


def test_fixture_manifest_rejects_stale_split_policy(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    data["fixture_classes"][0]["split_policy"] = (
        "10 calibration plus 20 heldout_gate rows locked in "
        "asls_truth_validation_fixture_lock.json"
    )
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="25 heldout"):
        load_fixture_manifest(path)


def test_fixture_manifest_rejects_blank_hard_case_codrift(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    for row in data["fixture_classes"]:
        if row["fixture_class"] == "blank_noise_control":
            row["required_hard_case_strata"] = ["blank"]
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="blank safety strata"):
        load_fixture_manifest(path)


def test_fixture_manifest_rejects_extra_fixture_class(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    extra = dict(data["fixture_classes"][0])
    extra["fixture_class"] = "extra_fixture_class"
    data["fixture_classes"].append(extra)
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected fixture classes"):
        load_fixture_manifest(path)


def test_fixture_manifest_rejects_duplicate_fixture_class(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_MANIFEST)
    data["fixture_classes"].append(dict(data["fixture_classes"][0]))
    path = tmp_path / "fixture_manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate fixture classes"):
        load_fixture_manifest(path)


def test_fixture_lock_has_per_row_locked_calibration_and_heldout_records() -> None:
    lock = load_fixture_lock(FIXTURE_LOCK)

    assert lock.lock_version == "asls_truth_fixture_lock_v2"
    assert lock.review_freeze_status == "reviewed_frozen_2026-05-27"
    assert lock.whole_lock_hash
    assert len(lock.records) >= len(REQUIRED_FIXTURE_CLASSES) * 30
    for class_name in REQUIRED_FIXTURE_CLASSES:
        calibration = [
            row
            for row in lock.records
            if row.fixture_class == class_name and row.split == "calibration"
        ]
        heldout = [
            row
            for row in lock.records
            if row.fixture_class == class_name and row.split == "heldout_gate"
        ]
        assert len(calibration) >= 10
        assert len(heldout) >= 25
    assert all(row.generator_input_hash for row in lock.records)
    assert all(row.gate_layer for row in lock.records)
    assert all(row.production_like_bounds_status for row in lock.records)
    assert all(row.decision_scope for row in lock.records)
    assert all(row.integration_point_count > 0 for row in lock.records)


def test_fixture_lock_rejects_duplicate_fixture_id(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_LOCK)
    data["records"][1]["fixture_id"] = data["records"][0]["fixture_id"]
    row = dict(data["records"][1])
    row.pop("generator_input_hash")
    data["records"][1]["generator_input_hash"] = _canonical_digest(row)
    data["whole_lock_hash"] = _canonical_digest({"records": data["records"]})
    path = tmp_path / "fixture_lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate fixture_id"):
        load_fixture_lock(path)


def test_fixture_lock_rejects_whole_lock_hash_drift(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_LOCK)
    data["records"][0]["replicate_id"] = 999
    path = tmp_path / "fixture_lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="whole_lock_hash"):
        load_fixture_lock(path)


def test_fixture_lock_rejects_row_hash_drift(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_LOCK)
    data["whole_lock_hash"] = "bad-but-present"
    data["records"][0]["generator_input_hash"] = "bad-row-hash"
    data["whole_lock_hash"] = _canonical_digest({"records": data["records"]})
    path = tmp_path / "fixture_lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="generator_input_hash"):
        load_fixture_lock(path)


def test_fixture_lock_rejects_missing_sn_strata(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_LOCK)
    target_class = "flat_peak_control"
    for record in data["records"]:
        if (
            record["fixture_class"] == target_class
            and record["split"] == "heldout_gate"
            and record["sn_stratum"] == "high"
        ):
            record["sn_stratum"] = "medium"
            row = dict(record)
            row.pop("generator_input_hash")
            record["generator_input_hash"] = _canonical_digest(row)
    data["whole_lock_hash"] = _canonical_digest({"records": data["records"]})
    path = tmp_path / "fixture_lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="S/N strata"):
        load_fixture_lock(path)


def test_fixture_lock_rejects_missing_peak_width_strata(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_LOCK)
    target_class = "flat_peak_control"
    for record in data["records"]:
        if (
            record["fixture_class"] == target_class
            and record["split"] == "heldout_gate"
            and record["peak_width_stratum"] == "wide"
        ):
            record["peak_width_stratum"] = "typical"
            row = dict(record)
            row.pop("generator_input_hash")
            record["generator_input_hash"] = _canonical_digest(row)
    data["whole_lock_hash"] = _canonical_digest({"records": data["records"]})
    path = tmp_path / "fixture_lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="peak-width strata"):
        load_fixture_lock(path)


def test_fixture_lock_rejects_sparse_sn_width_cross_coverage(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_LOCK)
    target_class = "flat_peak_control"
    changed = 0
    for record in data["records"]:
        if (
            record["fixture_class"] == target_class
            and record["split"] == "heldout_gate"
            and record["sn_stratum"] == "high"
            and record["peak_width_stratum"] == "wide"
            and changed < 3
        ):
            record["peak_width_stratum"] = "typical"
            row = dict(record)
            row.pop("generator_input_hash")
            record["generator_input_hash"] = _canonical_digest(row)
            changed += 1
    data["whole_lock_hash"] = _canonical_digest({"records": data["records"]})
    path = tmp_path / "fixture_lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="S/N x peak-width"):
        load_fixture_lock(path)


def test_fixture_lock_rejects_sparse_hard_case_stratum(tmp_path: Path) -> None:
    data = _load_json(FIXTURE_LOCK)
    target_class = "tailing_peak"
    changed = 0
    for record in data["records"]:
        if (
            record["fixture_class"] == target_class
            and record["split"] == "heldout_gate"
            and record["hard_case_stratum"] == "edge"
            and changed < 2
        ):
            record["hard_case_stratum"] = "strong"
            row = dict(record)
            row.pop("generator_input_hash")
            record["generator_input_hash"] = _canonical_digest(row)
            changed += 1
    data["whole_lock_hash"] = _canonical_digest({"records": data["records"]})
    path = tmp_path / "fixture_lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="fewer than 5 heldout rows"):
        load_fixture_manifest(_manifest_with_lock(tmp_path, path))


def test_fixture_manifest_rejects_missing_hard_case_stratum_in_lock(
    tmp_path: Path,
) -> None:
    data = _load_json(FIXTURE_LOCK)
    target_class = "tailing_peak"
    for record in data["records"]:
        if (
            record["fixture_class"] == target_class
            and record["split"] == "heldout_gate"
            and record["hard_case_stratum"] == "edge"
        ):
            record["hard_case_stratum"] = "strong"
            row = dict(record)
            row.pop("generator_input_hash")
            record["generator_input_hash"] = _canonical_digest(row)
    data["whole_lock_hash"] = _canonical_digest({"records": data["records"]})
    lock_path = tmp_path / "fixture_lock.json"
    lock_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="fewer than 5 heldout rows"):
        load_fixture_manifest(_manifest_with_lock(tmp_path, lock_path))


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def _canonical_digest(value: object) -> str:
    import hashlib

    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _manifest_with_lock(tmp_path: Path, lock_path: Path) -> Path:
    manifest = _load_json(FIXTURE_MANIFEST)
    lock_data = _load_json(lock_path)
    manifest["fixture_lock_path"] = str(lock_path)
    manifest["fixture_lock_hash"] = lock_data["whole_lock_hash"]
    manifest_path = tmp_path / "fixture_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _artifact_hash(artifact_hashes: object, key: str) -> str:
    assert isinstance(artifact_hashes, dict)
    artifact = artifact_hashes[key]
    assert isinstance(artifact, dict)
    value = artifact["sha256"]
    assert isinstance(value, str)
    return value
