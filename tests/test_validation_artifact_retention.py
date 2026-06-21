from pathlib import Path

from scripts.check_validation_artifact_retention import (
    REQUIRED_INVENTORY_COLUMNS,
    check_validation_artifact_retention,
)


def test_current_validation_retention_inventory_accepts_worktree() -> None:
    result = check_validation_artifact_retention()

    assert result.problems == ()
    assert result.summary["externalized_count"] == 139
    assert result.summary["shrink_later_count"] == 0


def test_checker_rejects_missing_inventory_row(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    _write_text(root / "docs/superpowers/validation/contract.tsv", "a\n1\n")
    _write_inventory(inventory, [])

    result = _check(
        root,
        inventory,
        policy,
        candidate_paths=["docs/superpowers/validation/contract.tsv"],
    )

    assert any("missing inventory rows" in problem for problem in result.problems)


def test_checker_rejects_externalized_png_still_present(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/validation/rendered/plot.png"
    _write_bytes(root / path, b"png")
    _write_inventory(
        inventory,
        [
            _row(
                path,
                category="rendered_plot",
                decision="externalize",
                tracked_replacement="docs/superpowers/validation/rendered/README.md",
                externalized_local_path="local_validation_artifacts/rendered/plot.png",
            ),
        ],
    )

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert any(
        "externalize artifact is still present" in problem
        for problem in result.problems
    )


def test_checker_rejects_externalized_html_still_present(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/validation/rendered/index.html"
    _write_text(root / path, "<html></html>")
    _write_inventory(
        inventory,
        [
            _row(
                path,
                category="rendered_html",
                decision="externalize",
                tracked_replacement="docs/superpowers/validation/rendered/README.md",
                externalized_local_path="local_validation_artifacts/rendered/index.html",
            ),
        ],
    )

    result = _check(root, inventory, policy, candidate_paths=[path])

    assert any(
        "externalize artifact is still present" in problem
        for problem in result.problems
    )


def test_checker_accepts_contract_tsv_and_summary_markdown(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    contract = "docs/superpowers/validation/contract.tsv"
    summary = "docs/superpowers/validation/README.md"
    _write_text(root / contract, "id\tvalue\nA\t1\n")
    _write_text(root / summary, "# Summary\n")
    _write_inventory(
        inventory,
        [
            _row(contract, category="tabular_contract", decision="keep_contract"),
            _row(summary, category="summary_or_policy", decision="keep_summary"),
        ],
    )

    result = _check(root, inventory, policy, candidate_paths=[contract, summary])

    assert result.problems == ()


def test_checker_accepts_handwritten_human_guide_html(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    guide = "docs/superpowers/validation/evidence_overlay_interpretation_guide.html"
    _write_text(
        root / guide,
        "<!doctype html><html><body><main>How to read overlays</main></body></html>",
    )
    _write_inventory(
        inventory,
        [
            _row(
                guide,
                category="human_guide_html",
                decision="keep_summary",
                required_by="Gallery overlay interpretation guide",
            ),
        ],
    )

    result = _check(root, inventory, policy, candidate_paths=[guide])

    assert result.problems == ()


def test_checker_accepts_minimal_fixture_tsv(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    fixture = "docs/superpowers/validation/readiness/inputs/cell_provenance.tsv"
    _write_text(root / fixture, "id\tcell_status\nA\tdetected\nB\taccepted_backfill\n")
    _write_inventory(
        inventory,
        [
            _row(
                fixture,
                category="tabular_contract",
                decision="keep_minimal_fixture",
                generated_by="scripts/build_packet.py --write-readiness-fixture",
                required_by="scripts/check_readiness.py synthetic readiness contract",
            ),
        ],
    )

    result = _check(root, inventory, policy, candidate_paths=[fixture], strict=True)

    assert result.problems == ()
    assert result.summary["shrink_later_count"] == 0


def test_checker_warns_for_large_shrink_later_and_strict_fails(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    path = "docs/superpowers/validation/big.tsv"
    _write_text(root / path, "x" * 20)
    _write_inventory(
        inventory,
        [
            _row(
                path,
                category="full_result_tsv",
                decision="shrink_later",
                generated_by="scripts/build_big.py",
                required_by="current checker",
                tracked_replacement="docs/superpowers/validation/big_summary.json",
            ),
        ],
    )

    result = _check(
        root,
        inventory,
        policy,
        candidate_paths=[path],
        large_file_threshold_bytes=10,
    )
    strict_result = _check(
        root,
        inventory,
        policy,
        candidate_paths=[path],
        strict=True,
        large_file_threshold_bytes=10,
    )

    assert result.problems == ()
    assert any("shrink_later remains tracked" in warning for warning in result.warnings)
    assert any(
        "shrink_later remains tracked" in problem
        for problem in strict_result.problems
    )


def test_checker_rejects_stale_rendered_reference_without_mapping(
    tmp_path: Path,
) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    summary = "docs/superpowers/validation/summary.md"
    rendered = "docs/superpowers/validation/rendered/index.html"
    _write_text(root / summary, f"Open {rendered}\n")
    _write_inventory(
        inventory,
        [_row(summary, category="summary_or_policy", decision="keep_summary")],
    )

    result = _check(root, inventory, policy, candidate_paths=[summary])

    assert any("lacks inventory mapping" in problem for problem in result.problems)


def test_checker_accepts_stale_rendered_reference_with_externalized_mapping(
    tmp_path: Path,
) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    summary = "docs/superpowers/validation/summary.md"
    rendered = "docs/superpowers/validation/rendered/index.html"
    _write_text(root / summary, f"Open {rendered}\n")
    _write_inventory(
        inventory,
        [
            _row(summary, category="summary_or_policy", decision="keep_summary"),
            _row(
                rendered,
                category="rendered_html",
                decision="externalize",
                tracked_replacement="docs/superpowers/validation/rendered/index_summary.json",
                externalized_local_path="local_validation_artifacts/rendered/index.html",
            ),
        ],
    )

    result = _check(root, inventory, policy, candidate_paths=[summary])

    assert result.problems == ()


def test_checker_can_require_externalized_local_copy(tmp_path: Path) -> None:
    root, inventory, policy = _fixture_root(tmp_path)
    summary = "docs/superpowers/validation/summary.md"
    rendered = "docs/superpowers/validation/rendered/index.html"
    tracked_replacement = "docs/superpowers/validation/rendered/index_summary.json"
    externalized_local_path = "local_validation_artifacts/rendered/index.html"
    _write_text(root / summary, f"Open {rendered}\n")
    _write_inventory(
        inventory,
        [
            _row(summary, category="summary_or_policy", decision="keep_summary"),
            _row(
                rendered,
                category="rendered_html",
                decision="externalize",
                tracked_replacement=tracked_replacement,
                externalized_local_path=externalized_local_path,
            ),
        ],
    )

    missing = _check(
        root,
        inventory,
        policy,
        candidate_paths=[summary],
        require_externalized_local=True,
    )
    _write_text(root / externalized_local_path, "<html></html>")
    present = _check(
        root,
        inventory,
        policy,
        candidate_paths=[summary],
        require_externalized_local=True,
    )

    assert any(
        "externalized local replacement missing" in problem
        for problem in missing.problems
    )
    assert present.problems == ()


def _fixture_root(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path
    validation = root / "docs/superpowers/validation"
    validation.mkdir(parents=True)
    policy = validation / "RETENTION.md"
    inventory = validation / "ARTIFACT_INVENTORY.tsv"
    _write_text(
        policy,
        "\n".join(
            [
                "| Decision | Meaning |",
                "| --- | --- |",
                "| `keep_contract` | keep |",
                "| `keep_summary` | keep |",
                "| `keep_minimal_fixture` | keep |",
                "| `shrink_later` | keep temporarily |",
                "| `externalize` | move local |",
                "| `delete_generated` | remove |",
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
    deleted_paths: list[str] | None = None,
    strict: bool = False,
    require_externalized_local: bool = False,
    large_file_threshold_bytes: int = 500_000,
):
    return check_validation_artifact_retention(
        inventory_path=inventory,
        retention_policy_path=policy,
        validation_dir=root / "docs/superpowers/validation",
        repo_root=root,
        strict=strict,
        require_externalized_local=require_externalized_local,
        large_file_threshold_bytes=large_file_threshold_bytes,
        candidate_paths=candidate_paths,
        deleted_paths=deleted_paths or [],
    )


def _row(
    path: str,
    *,
    category: str,
    decision: str,
    generated_by: str = "",
    required_by: str = "",
    tracked_replacement: str = "",
    externalized_local_path: str = "",
) -> dict[str, str]:
    return {
        "path": path,
        "size_bytes": "",
        "line_count": "",
        "category": category,
        "retention_decision": decision,
        "keep_reason": "test reason",
        "generated_by": generated_by,
        "required_by": required_by,
        "tracked_replacement_or_summary": tracked_replacement,
        "externalized_local_path": externalized_local_path,
    }


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


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
