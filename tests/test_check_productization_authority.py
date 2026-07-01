from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from scripts.check_productization_authority import (
    DEFAULT_INDEX,
    DEFAULT_MANIFEST,
    DEFAULT_SCHEMA,
    check_productization_authority,
    main,
)
from scripts.check_productization_state import artifact_sha256

BACKFILL_EXTERNALIZED_SUMMARY = (
    "docs/superpowers/validation/"
    "backfill_generated_policy_externalized_artifacts_v1/"
    "backfill_generated_policy_externalized_artifacts_summary.json"
)


def test_productization_authority_checker_accepts_repo_artifacts() -> None:
    assert main([]) == 0


def test_productization_authority_checker_rejects_forbidden_scope(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / DEFAULT_MANIFEST.name
    schema = tmp_path / DEFAULT_SCHEMA.name
    index = tmp_path / DEFAULT_INDEX.name
    shutil.copyfile(DEFAULT_MANIFEST, manifest)
    shutil.copyfile(DEFAULT_SCHEMA, schema)
    shutil.copyfile(DEFAULT_INDEX, index)

    _mutate_first_non_write_row_to_forbidden_scope(index)

    problems = check_productization_authority(
        manifest_path=manifest,
        schema_path=schema,
        index_path=index,
        repo_root=tmp_path,
    )

    assert any("unregistered authority scope" in problem for problem in problems)
    assert any("forbidden authority scopes present" in problem for problem in problems)


def test_productization_authority_checker_rejects_stale_cid_nl_hash(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / DEFAULT_MANIFEST.name
    schema = tmp_path / DEFAULT_SCHEMA.name
    index = tmp_path / DEFAULT_INDEX.name
    shutil.copyfile(DEFAULT_MANIFEST, manifest)
    shutil.copyfile(DEFAULT_SCHEMA, schema)
    shutil.copyfile(DEFAULT_INDEX, index)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["current_authority"]["cid_nl_default_activation"][
        "artifact_sha256"
    ] = "STALE"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    problems = check_productization_authority(
        manifest_path=manifest,
        schema_path=schema,
        index_path=index,
    )

    assert any(
        "CID-NL artifact hash does not match manifest" in problem
        for problem in problems
    )


def test_productization_authority_checker_rejects_stale_clean_target_hash(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / DEFAULT_MANIFEST.name
    schema = tmp_path / DEFAULT_SCHEMA.name
    index = tmp_path / DEFAULT_INDEX.name
    shutil.copyfile(DEFAULT_MANIFEST, manifest)
    shutil.copyfile(DEFAULT_SCHEMA, schema)
    shutil.copyfile(DEFAULT_INDEX, index)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["current_authority"][
        "backfill_expansion_clean_target_selective_activation"
    ]["artifact_sha256"] = "STALE"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    problems = check_productization_authority(
        manifest_path=manifest,
        schema_path=schema,
        index_path=index,
    )

    assert any(
        "Backfill clean-target artifact hash does not match manifest" in problem
        for problem in problems
    )


def test_productization_authority_checker_requires_compact_artifact(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / DEFAULT_MANIFEST.name
    schema = tmp_path / DEFAULT_SCHEMA.name
    index = tmp_path / DEFAULT_INDEX.name
    shutil.copyfile(DEFAULT_MANIFEST, manifest)
    shutil.copyfile(DEFAULT_SCHEMA, schema)
    shutil.copyfile(DEFAULT_INDEX, index)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["current_authority"]["backfill"][
        "artifact"
    ] = "docs/superpowers/validation/missing_backfill_summary.json"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    problems = check_productization_authority(
        manifest_path=manifest,
        schema_path=schema,
        index_path=index,
    )

    assert any(
        "policy compact artifact is missing: "
        "docs/superpowers/validation/missing_backfill_summary.json" in problem
        for problem in problems
    )


def test_productization_authority_checker_rejects_stale_backfill_acceptance_hash(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / DEFAULT_MANIFEST.name
    schema = tmp_path / DEFAULT_SCHEMA.name
    index = tmp_path / DEFAULT_INDEX.name
    shutil.copyfile(DEFAULT_MANIFEST, manifest)
    shutil.copyfile(DEFAULT_SCHEMA, schema)
    shutil.copyfile(DEFAULT_INDEX, index)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["current_authority"]["backfill"][
        "acceptance_artifact_sha256"
    ] = "STALE_ACCEPTANCE_SHA"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    problems = check_productization_authority(
        manifest_path=manifest,
        schema_path=schema,
        index_path=index,
    )

    assert any(
        "compact summary acceptance sha256 does not match manifest" in problem
        for problem in problems
    )


def test_productization_authority_checker_validates_compact_summary_contents(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / DEFAULT_MANIFEST.name
    schema = tmp_path / DEFAULT_SCHEMA.name
    index = tmp_path / DEFAULT_INDEX.name
    summary = tmp_path / BACKFILL_EXTERNALIZED_SUMMARY
    shutil.copyfile(DEFAULT_MANIFEST, manifest)
    shutil.copyfile(DEFAULT_SCHEMA, schema)
    shutil.copyfile(DEFAULT_INDEX, index)
    summary.parent.mkdir(parents=True)
    shutil.copyfile(
        DEFAULT_MANIFEST.parent.parent
        / "validation/backfill_generated_policy_externalized_artifacts_v1/"
        / "backfill_generated_policy_externalized_artifacts_summary.json",
        summary,
    )

    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    policy = summary_payload["externalized_artifacts"]["standard_peak_backfill_policy"]
    quality = summary_payload["externalized_artifacts"][
        "standard_peak_backfill_policy_quality_explanations"
    ]
    acceptance = summary_payload["externalized_artifacts"][
        "narrow_product_writer_expected_diff_acceptance"
    ]
    policy["path"] = "output/stale_policy.tsv"
    policy["sha256"] = "STALE_POLICY_SHA"
    policy["data_rows"] = 1
    policy["write_authority"] = False
    policy["product_authority_scope"] = "wrong_scope"
    policy["policy_decision_counts"]["write_ready"] = 0
    quality["sha256"] = "STALE_QUALITY_SHA"
    quality["write_authority"] = True
    quality["may_grant_write_authority"] = True
    acceptance["path"] = "output/stale_acceptance.json"
    acceptance["acceptance_status"] = "fail"
    acceptance["activation_application_status"] = "not_applied"
    acceptance["expected_scope"] = "wrong_scope"
    acceptance["eligible_audit_row_count"] = 1
    acceptance["matrix_cells_written"] = 1
    acceptance["activation_scope_audit_tsv"] = "output/wrong_policy.tsv"
    acceptance["activation_scope_audit_sha256"] = "STALE_ACCEPTANCE_POLICY_SHA"
    summary.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    compact_relative = summary.relative_to(tmp_path).as_posix()
    manifest_payload["current_authority"]["backfill"]["artifact"] = compact_relative
    manifest_payload["current_authority"]["backfill"][
        "artifact_sha256"
    ] = artifact_sha256(summary)
    manifest_payload["explanation_only_sources"][0]["artifact"] = compact_relative
    manifest_payload["explanation_only_sources"][0][
        "artifact_sha256"
    ] = artifact_sha256(summary)
    manifest.write_text(
        json.dumps(manifest_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    problems = check_productization_authority(
        manifest_path=manifest,
        schema_path=schema,
        index_path=index,
        repo_root=tmp_path,
    )

    assert any(
        "compact summary policy path does not match manifest" in problem
        for problem in problems
    )
    assert any(
        "compact summary policy sha256 does not match manifest" in problem
        for problem in problems
    )
    assert any(
        "compact summary policy data_rows does not match manifest" in problem
        for problem in problems
    )
    assert any(
        "compact summary policy write_authority does not match manifest" in problem
        for problem in problems
    )
    assert any(
        "compact summary policy product_authority_scope does not match manifest"
        in problem
        for problem in problems
    )
    assert any(
        "compact summary policy decision count write_ready does not match index"
        in problem
        for problem in problems
    )
    assert any(
        "compact summary quality sha256 does not match manifest" in problem
        for problem in problems
    )
    assert any(
        "compact summary quality write_authority does not match manifest" in problem
        for problem in problems
    )
    assert any(
        "compact summary quality may_grant_write_authority does not match manifest"
        in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance path does not match manifest" in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance status must be pass" in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance application status must be applied" in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance expected_scope does not match manifest"
        in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance eligible_audit_row_count does not match manifest"
        in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance matrix_cells_written does not match manifest"
        in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance activation_scope_audit_tsv does not match policy"
        in problem
        for problem in problems
    )
    assert any(
        "compact summary acceptance activation_scope_audit_sha256 does not match policy"
        in problem
        for problem in problems
    )


def _mutate_first_non_write_row_to_forbidden_scope(index: Path) -> None:
    with index.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = tuple(reader.fieldnames or ())
        rows = list(reader)
    for row in rows:
        if row["write_authority"] == "FALSE":
            row["write_authority"] = "TRUE"
            row["may_touch_matrix"] = "TRUE"
            row["explanation_only"] = "FALSE"
            row["product_authority_scope"] = "all_stability"
            break
    else:
        raise AssertionError("fixture index has no non-write rows")
    with index.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
