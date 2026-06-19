from pathlib import Path

from xic_extractor.artifact_retention import (
    git_visible_paths,
    index_inventory_by_path,
    missing_inventory_paths,
    normalize_repo_path,
    present_existing_paths,
    read_policy_decisions,
    retained_file_metadata,
)


def test_read_policy_decisions_reports_missing_required_decisions(
    tmp_path: Path,
) -> None:
    policy = tmp_path / "RETENTION.md"
    policy.write_text(
        "\n".join(
            [
                "| Decision | Meaning |",
                "| --- | --- |",
                "| `keep_contract` | keep |",
                "",
            ],
        ),
        encoding="utf-8",
    )
    problems: list[str] = []

    decisions = read_policy_decisions(
        policy,
        required_decisions={"keep_contract", "externalize"},
        problems=problems,
        missing_message="missing decisions: ",
    )

    assert decisions == {"keep_contract"}
    assert problems == ["missing decisions: externalize"]


def test_index_inventory_normalizes_duplicates_and_rejects_self_row() -> None:
    problems: list[str] = []

    indexed = index_inventory_by_path(
        [
            {"path": "docs\\superpowers\\fixtures\\contract.tsv"},
            {"path": "docs/superpowers/fixtures/contract.tsv"},
            {"path": "docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv"},
            {"path": ""},
        ],
        problems=problems,
        self_index_path="docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv",
        self_index_message="self row rejected",
    )

    assert tuple(indexed) == ("docs/superpowers/fixtures/contract.tsv",)
    assert (
        "duplicate inventory rows: docs/superpowers/fixtures/contract.tsv" in problems
    )
    assert "self row rejected" in problems
    assert "inventory row 5: path is required" in problems


def test_present_existing_paths_and_missing_inventory_share_normalized_paths(
    tmp_path: Path,
) -> None:
    existing = "docs/superpowers/validation/contract.tsv"
    excluded = "docs/superpowers/validation/ARTIFACT_INVENTORY.tsv"
    (tmp_path / existing).parent.mkdir(parents=True)
    (tmp_path / existing).write_text("id\nA\n", encoding="utf-8")
    (tmp_path / excluded).write_text("path\n", encoding="utf-8")

    present = present_existing_paths(
        [existing.replace("/", "\\"), excluded],
        repo_root=tmp_path,
        exclude_paths={excluded},
    )

    assert present == {existing}
    assert missing_inventory_paths(present, {}) == [existing]


def test_retained_file_metadata_reports_size_line_count_and_sha(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fixture.tsv"
    path.write_bytes(b"a\n1")

    metadata = retained_file_metadata(path)

    assert metadata.size_bytes == 3
    assert metadata.line_count == 2
    assert len(metadata.sha256) == 64
    assert metadata.sha256 == metadata.sha256.upper()


def test_git_visible_paths_returns_tracked_untracked_and_deleted(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test User")
    surface = tmp_path / "docs/superpowers/validation"
    surface.mkdir(parents=True)
    tracked = surface / "tracked.tsv"
    deleted = surface / "deleted.tsv"
    untracked = surface / "untracked.tsv"
    tracked.write_text("a\n", encoding="utf-8")
    deleted.write_text("b\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    deleted.unlink()
    untracked.write_text("c\n", encoding="utf-8")
    problems: list[str] = []

    candidates, deleted_paths = git_visible_paths(
        repo_root=tmp_path,
        surface_dir=surface,
        problems=problems,
        include_deleted=True,
    )

    assert problems == []
    assert "docs/superpowers/validation/tracked.tsv" in candidates
    assert "docs/superpowers/validation/untracked.tsv" in candidates
    assert "docs/superpowers/validation/deleted.tsv" not in candidates
    assert deleted_paths == ("docs/superpowers/validation/deleted.tsv",)


def test_normalize_repo_path_handles_windows_separators() -> None:
    assert normalize_repo_path(" docs\\superpowers\\fixtures\\x.tsv ") == (
        "docs/superpowers/fixtures/x.tsv"
    )


def _git(cwd: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
