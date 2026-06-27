from __future__ import annotations

import subprocess
from pathlib import Path

from tools.diagnostics.docs_placement_guard import (
    StagedMarkdown,
    check_doc_placement,
    parse_name_status,
    staged_markdown,
)


def _write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _problems(root: Path, status: str, path: str) -> list[str]:
    result = check_doc_placement(root, [StagedMarkdown(status, path)])
    return [problem.reason for problem in result.problems]


def test_high_risk_dated_implementation_plan_without_marker_fails(
    tmp_path: Path,
) -> None:
    path = "docs/superpowers/plans/2026-07-01-example-implementation-plan.md"
    _write(
        tmp_path,
        path,
        "# Example plan\n\nImplementation diary and command log details.\n",
    )

    problems = _problems(tmp_path, "A", path)

    assert any("lacks placement marker" in problem for problem in problems)


def test_repo_active_stub_with_required_fields_passes(tmp_path: Path) -> None:
    path = "docs/superpowers/plans/2026-07-01-active-work-stub.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Active work stub",
                "",
                "Doc placement: repo_active_stub",
                "Repo owner: docs/superpowers/handoffs/current/example.md",
                "",
                "Objective: keep the next action recoverable.",
                "Scope: docs workflow only.",
                "Constraints: no destructive cleanup.",
                "Next 1-3 actions:",
                "1. Run the checker.",
                "Verification: focused pytest.",
                "Stop rule: stop if the repo stub is not self-sufficient.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_product_formal_source_of_truth_passes_without_marker(tmp_path: Path) -> None:
    path = "docs/product/backfill.md"
    _write(tmp_path, path, "# Backfill\n\nFormal public source of truth.\n")

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_canonical_doc_can_document_marker_schema_without_false_positive(
    tmp_path: Path,
) -> None:
    path = "docs/agent/obsidian-handoff-contract.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Contract",
                "",
                "```markdown",
                "Doc placement: <formal_repo_doc | repo_active_stub>",
                "Repo owner: <path-or-topic>",
                "```",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("M", path)])

    assert result.problems == ()


def test_superpowers_spec_with_formal_marker_passes(tmp_path: Path) -> None:
    path = "docs/superpowers/specs/2026-07-01-example-contract.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Example contract",
                "",
                "Doc placement: formal_repo_doc",
                "Repo owner: docs/product/example.md",
                "",
                "This is a public contract.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_branch_closeout_summary_with_pr_body_seed_passes(tmp_path: Path) -> None:
    path = (
        "docs/superpowers/closeouts/"
        "2026-07-01_codex-example_branch-closeout-summary.md"
    )
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Branch closeout",
                "",
                "## Problem",
                "",
                "## Solution",
                "",
                "## Verification",
                "",
                "## Residual Risk",
                "",
                "## PR Body Seed",
                "",
                "Problem: example.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_file_management_cleanup_evidence_passes_without_marker(tmp_path: Path) -> None:
    path = (
        "docs/superpowers/file-management/docs-cleanup/"
        "2026-07-01_codex-docs-cleanup_git-rm-candidate-manifest.md"
    )
    _write(
        tmp_path,
        path,
        "# Candidate manifest\n\nPublic cleanup evidence for approved review.\n",
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_handoff_archive_cleanup_evidence_without_marker_fails(tmp_path: Path) -> None:
    path = (
        "docs/superpowers/handoffs/archive/"
        "2026-07-01_codex-docs-cleanup_git-rm-candidate-manifest.md"
    )
    _write(
        tmp_path,
        path,
        "# Candidate manifest\n\nPublic cleanup evidence in the wrong lane.\n",
    )

    problems = _problems(tmp_path, "A", path)

    assert any("do not belong under handoffs" in problem for problem in problems)


def test_handoff_archive_private_diary_without_marker_fails(tmp_path: Path) -> None:
    path = (
        "docs/superpowers/handoffs/archive/"
        "2026-07-01_codex-example_branch-diary.md"
    )
    _write(
        tmp_path,
        path,
        "# Branch diary\n\nImplementation diary and command transcript.\n",
    )

    problems = _problems(tmp_path, "A", path)

    assert any("lacks placement marker" in problem for problem in problems)


def test_force_added_local_handoff_without_marker_fails(tmp_path: Path) -> None:
    path = "docs/superpowers/handoffs/current/ACTIVE.local.md"
    _write(
        tmp_path,
        path,
        "# Active local handoff\n\nImplementation diary and next actions.\n",
    )

    problems = _problems(tmp_path, "A", path)

    assert any("lacks placement marker" in problem for problem in problems)


def test_branch_named_productization_active_stub_is_not_misplaced_record(
    tmp_path: Path,
) -> None:
    path = "docs/superpowers/handoffs/current/codex-productization.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Productization handoff",
                "",
                "Doc placement: repo_active_stub",
                "Repo owner: docs/superpowers/handoffs/current/codex-productization.md",
                "",
                "Objective: keep productization work recoverable.",
                "Scope: active branch state only.",
                "Constraints: no public status authority.",
                "Next 1-3 actions:",
                "1. Re-run the guard.",
                "Verification: hook fixture.",
                "Stop rule: stop if the stub cannot name the next action.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_productization_status_handoff_remains_canonical(tmp_path: Path) -> None:
    path = (
        "docs/superpowers/productization/status/"
        "cc-framework-improvements-productization.md"
    )
    _write(tmp_path, path, "# Productization status anchor\n")

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_branch_closeout_summary_still_requires_pr_body_seed(tmp_path: Path) -> None:
    path = (
        "docs/superpowers/closeouts/"
        "2026-07-01_codex-example_branch-closeout-summary.md"
    )
    _write(tmp_path, path, "# Branch closeout\n\n## Verification\n")

    problems = _problems(tmp_path, "A", path)

    assert any("missing PR Body Seed" in problem for problem in problems)


def test_private_obsidian_note_staged_under_repo_docs_fails(tmp_path: Path) -> None:
    path = "docs/superpowers/notes/2026-07-01-private-review-note.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Private review note",
                "",
                "Doc placement: private_obsidian_note",
                "",
                "Review rationale and branch sequencing.",
            ]
        ),
    )

    problems = _problems(tmp_path, "A", path)

    assert any("not a repo-trackable placement" in problem for problem in problems)


def test_sanitized_stub_plus_obsidian_passes(tmp_path: Path) -> None:
    path = "docs/superpowers/notes/2026-07-01-private-review-note.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Private review note",
                "",
                "Doc placement: repo_stub_plus_obsidian",
                "Repo owner: docs/product/review-roundtrip.md",
                "",
                "This file is a sanitized public stub.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_deletions_are_ignored_by_placement_guard() -> None:
    entries, ignored_deletions = parse_name_status(
        "D\tdocs/superpowers/plans/2026-04-07-old-plan.md\n"
    )

    result = check_doc_placement(
        Path("."),
        entries,
        ignored_deletions=ignored_deletions,
    )

    assert result.checked_count == 0
    assert result.ignored_deletions == 1
    assert result.problems == ()


def test_cli_reads_staged_blob_not_worktree_after_divergence(tmp_path: Path) -> None:
    path = "docs/superpowers/plans/2026-07-01-example-implementation-plan.md"
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    _write(
        tmp_path,
        path,
        "# Example plan\n\nImplementation diary and command log details.\n",
    )
    subprocess.run(["git", "add", path], cwd=tmp_path, check=True, capture_output=True)
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Active work stub",
                "",
                "Doc placement: repo_active_stub",
                "Repo owner: docs/superpowers/handoffs/current/example.md",
                "",
                "Objective: keep the next action recoverable.",
                "Scope: docs workflow only.",
                "Constraints: no destructive cleanup.",
                "Next 1-3 actions:",
                "1. Run the checker.",
                "Verification: focused pytest.",
                "Stop rule: stop if the repo stub is not self-sufficient.",
            ]
        ),
    )

    entries, ignored_deletions = staged_markdown(tmp_path)
    result = check_doc_placement(
        tmp_path,
        entries,
        ignored_deletions=ignored_deletions,
    )

    assert any(
        "lacks placement marker" in problem.reason
        for problem in result.problems
    )
