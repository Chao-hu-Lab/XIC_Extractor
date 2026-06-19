from pathlib import Path

from scripts.check_superpowers_fixture_retention import (
    REQUIRED_INVENTORY_COLUMNS,
    check_superpowers_fixture_retention,
)
from xic_extractor.tabular_io import file_sha256, read_tsv_with_header


def test_current_superpowers_fixture_inventory_accepts_worktree() -> None:
    result = check_superpowers_fixture_retention()

    assert result.problems == ()
    assert result.summary["present_fixture_files"] == result.summary["inventory_rows"]
    assert result.summary["needs_human_review_count"] == 1


def test_checker_rejects_missing_inventory_row(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/contract.tsv"
    _write_text(root / path, "a\n1\n")
    _write_inventory(inventory, [])

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert any("missing inventory rows" in problem for problem in result.problems)


def test_checker_rejects_invalid_retention_decision(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/contract.tsv"
    _write_text(root / path, "a\n1\n")
    _write_inventory(
        inventory,
        [_row(root, path, category="contract_fixture", decision="keep_forever")],
    )

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert any("invalid retention_decision" in problem for problem in result.problems)


def test_checker_rejects_sha256_mismatch(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/contract.tsv"
    _write_text(root / path, "a\n1\n")
    row = _row(root, path, category="contract_fixture", decision="keep_contract")
    row["sha256"] = "0" * 64
    _write_inventory(inventory, [row])

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert any("sha256" in problem for problem in result.problems)


def test_checker_rejects_missing_keep_summary_file(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/README.md"
    _write_text(root / path, "# Fixture summary\n")
    row = _row(root, path, category="retention_summary", decision="keep_summary")
    (root / path).unlink()
    _write_inventory(inventory, [row])

    result = _check(root, inventory, policy, candidate_paths=[])

    assert any(
        "inventory says keep_summary but file is absent" in problem
        for problem in result.problems
    )


def test_checker_warns_for_needs_human_review_without_strict(
    tmp_path: Path,
) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/manual_oracle.tsv"
    _write_text(root / path, "a\n1\n")
    row = _row(
        root,
        path,
        category="manual_oracle",
        decision="needs_human_review",
    )
    _write_inventory(inventory, [row])

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert result.problems == ()
    assert any(
        "needs_human_review remains unresolved" in warning
        for warning in result.warnings
    )


def test_checker_strict_rejects_needs_human_review(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/manual_oracle.tsv"
    _write_text(root / path, "a\n1\n")
    row = _row(
        root,
        path,
        category="manual_oracle",
        decision="needs_human_review",
    )
    _write_inventory(inventory, [row])

    result = _check(root, inventory, policy, candidate_paths=[path], strict=True)

    assert any(
        "needs_human_review remains unresolved" in problem
        for problem in result.problems
    )


def test_checker_requires_ledger_reference_for_ledger_snapshot(
    tmp_path: Path,
) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/snapshot.tsv"
    _write_text(root / path, "a\n1\n")
    row = _row(
        root,
        path,
        category="diagnostic_ledger_snapshot",
        decision="keep_ledger_snapshot",
    )
    row["referenced_by"] = ""
    _write_inventory(inventory, [row])

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert any(
        "needs ledger or packet README reference" in problem
        for problem in result.problems
    )


def test_checker_requires_active_fixture_reference(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/contract.tsv"
    _write_text(root / path, "a\n1\n")
    row = _row(root, path, category="contract_fixture", decision="keep_contract")
    row["referenced_by"] = ""
    _write_inventory(inventory, [row])

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert any(
        "active root fixture needs referenced_by" in problem
        for problem in result.problems
    )


def test_checker_rejects_large_generated_dump_without_policy_reason(
    tmp_path: Path,
) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/fixtures/generated_dump.tsv"
    _write_text(root / path, "x" * 20)
    row = _row(
        root,
        path,
        category="full_result_tsv",
        decision="keep_summary",
    )
    row["keep_reason"] = ""
    row["referenced_by"] = ""
    _write_inventory(inventory, [row])

    result = _check(
        root,
        inventory,
        policy,
        candidate_paths=[path],
        large_file_threshold_bytes=10,
    )

    assert any(
        "large generated-like fixture needs policy reason" in problem
        for problem in result.problems
    )


def test_active_fixture_paths_are_present_and_classified() -> None:
    active_paths = {
        "docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv",
        "docs/superpowers/fixtures/shared_peak_identity_mode_window_assignment_contract_v0.tsv",
        "docs/superpowers/fixtures/shared_peak_identity_activation_must_not_regress_v1.tsv",
        "docs/superpowers/fixtures/target_pair_chrom_morphology_area_ratio_manual_oracle_v1.tsv",
        "docs/superpowers/fixtures/targeted_nl_fail_own_max_gate_expected_diff_v0.tsv",
        "docs/superpowers/fixtures/alignment_cell_integration_audit_current_asls_schema.tsv",
    }
    inventory = _read_current_inventory()

    for path in active_paths:
        assert Path(path).exists()
        assert inventory[path]["retention_decision"] in {
            "keep_contract",
            "keep_manual_oracle",
            "keep_manifest",
        }


def _fixture_root(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path
    fixtures = root / "docs/superpowers/fixtures"
    fixtures.mkdir(parents=True)
    policy = fixtures / "RETENTION.md"
    inventory = fixtures / "ARTIFACT_INVENTORY.tsv"
    _write_text(
        policy,
        "\n".join(
            [
                "| Decision | Meaning |",
                "| --- | --- |",
                "| `keep_contract` | keep |",
                "| `keep_manual_oracle` | keep |",
                "| `keep_manifest` | keep |",
                "| `keep_ledger_snapshot` | keep |",
                "| `keep_summary` | keep |",
                "| `needs_human_review` | keep temporarily |",
                "| `archive_later` | keep temporarily |",
                "| `externalize` | move local |",
                "| `remove_generated` | remove |",
                "",
            ],
        ),
    )
    return root, inventory, policy


def _check(
    root: Path,
    inventory: Path,
    policy: Path,
    *,
    candidate_paths: list[str],
    strict: bool = False,
    large_file_threshold_bytes: int = 100_000,
):
    return check_superpowers_fixture_retention(
        inventory_path=inventory,
        retention_policy_path=policy,
        fixtures_dir=root / "docs/superpowers/fixtures",
        repo_root=root,
        strict=strict,
        large_file_threshold_bytes=large_file_threshold_bytes,
        candidate_paths=candidate_paths,
    )


def _row(
    root: Path,
    path: str,
    *,
    category: str,
    decision: str,
) -> dict[str, str]:
    file_path = root / path
    data = file_path.read_bytes()
    line_count = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
    return {
        "path": path,
        "size_bytes": str(file_path.stat().st_size),
        "line_count": str(line_count),
        "sha256": file_sha256(file_path),
        "category": category,
        "retention_decision": decision,
        "authority_scope": "test_scope",
        "referenced_by": "docs/diagnostic-ledger.md",
        "keep_reason": "test reason",
        "next_action": "",
    }


def _read_current_inventory() -> dict[str, dict[str, str]]:
    header, rows = read_tsv_with_header(
        Path("docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv"),
        required_columns=REQUIRED_INVENTORY_COLUMNS,
    )
    assert header == REQUIRED_INVENTORY_COLUMNS
    return {row["path"]: row for row in rows}


def _write_inventory(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\t".join(REQUIRED_INVENTORY_COLUMNS) + "\n")
        for row in rows:
            handle.write(
                "\t".join(row.get(column, "") for column in REQUIRED_INVENTORY_COLUMNS)
                + "\n",
            )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
