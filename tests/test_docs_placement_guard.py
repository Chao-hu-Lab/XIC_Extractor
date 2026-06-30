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
                "Doc kind: plan",
                "Doc lifecycle: active",
                "Repo owner: docs/superpowers/handoffs/current/example.md",
                "Doc exit rule: replace with branch closeout after implementation.",
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


def test_new_lifecycle_managed_doc_requires_kind_lifecycle_and_exit_rule(
    tmp_path: Path,
) -> None:
    path = "docs/superpowers/plans/2026-07-01-example-contract.md"
    _write(
        tmp_path,
        path,
        "# Example Contract\n\nPublic behavior contract draft.\n",
    )

    problems = _problems(tmp_path, "A", path)

    assert any("missing Doc kind" in problem for problem in problems)
    assert any("missing Doc lifecycle" in problem for problem in problems)


def test_new_lifecycle_managed_plan_with_metadata_passes(tmp_path: Path) -> None:
    path = "docs/superpowers/plans/2026-07-01-example-contract.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Example Contract",
                "",
                "Doc placement: formal_repo_doc",
                "Doc kind: plan",
                "Doc lifecycle: active",
                "Repo owner: docs/product/example.md",
                "Doc exit rule: promote accepted behavior to docs/product/example.md.",
                "",
                "Public behavior contract draft.",
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


def test_user_guide_passes_without_marker(tmp_path: Path) -> None:
    path = "docs/user/targeted-extraction.md"
    _write(tmp_path, path, "# Targeted Extraction\n\nPublic user guide.\n")

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_user_guide_with_private_history_signal_fails(tmp_path: Path) -> None:
    path = "docs/user/branch-notes.md"
    _write(
        tmp_path,
        path,
        "# Branch notes\n\nImplementation diary and command transcript details.\n",
    )

    problems = _problems(tmp_path, "A", path)

    assert any("private-history signals" in problem for problem in problems)


def test_user_guide_with_non_user_placement_fails(tmp_path: Path) -> None:
    for placement in (
        "repo_active_stub",
        "branch_closeout_summary",
        "repo_stub_plus_obsidian",
        "repo_stub_plus_formal_doc",
        "ignored_artifact",
    ):
        path = f"docs/user/{placement}.md"
        _write(
            tmp_path,
            path,
            "\n".join(
                [
                    "# Misplaced user doc",
                    "",
                    f"Doc placement: {placement}",
                    "",
                    "Objective: preserve branch state.",
                ]
            ),
        )

        problems = _problems(tmp_path, "A", path)

        assert any("not valid in docs/user" in problem for problem in problems)


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


def test_transient_superpowers_specs_markdown_with_metadata_passes(
    tmp_path: Path,
) -> None:
    path = "docs/superpowers/specs/2026-07-01-example-contract.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Example contract",
                "",
                "Doc placement: formal_repo_doc",
                "Doc kind: spec",
                "Doc lifecycle: active",
                "Repo owner: docs/product/example.md",
                "Doc exit rule: promote accepted behavior to docs/product/example.md.",
                "",
                "This is a public contract.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_superpowers_specs_non_markdown_payload_fails(
    tmp_path: Path,
) -> None:
    path = "docs/superpowers/specs/example-schema.json"
    _write(tmp_path, path, "{}\n")

    problems = _problems(tmp_path, "A", path)

    assert any("Markdown-only" in problem for problem in problems)


def test_parse_name_status_keeps_specs_non_markdown_payloads() -> None:
    entries, ignored_deletions = parse_name_status(
        "A\tdocs/superpowers/specs/example-schema.json\n"
        "A\toutput/private.json\n"
    )

    assert ignored_deletions == 0
    assert [entry.path for entry in entries] == [
        "docs/superpowers/specs/example-schema.json"
    ]


def test_repo_support_doc_requires_owner_and_passes(tmp_path: Path) -> None:
    path = "docs/superpowers/file-management/docs-cleanup/example-support-note.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Example support note",
                "",
                "Doc placement: repo_support_doc",
                "Doc kind: validation_artifact",
                "Doc lifecycle: archived",
                "Repo owner: docs/product/backfill.md",
                "",
                "Compact validation note supporting the Backfill owner.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_repo_support_doc_without_owner_fails(tmp_path: Path) -> None:
    path = "docs/superpowers/file-management/docs-cleanup/example-support-note.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Example support note",
                "",
                "Doc placement: repo_support_doc",
                "Doc kind: validation_artifact",
                "Doc lifecycle: archived",
                "",
                "Compact validation note supporting the Backfill owner.",
            ]
        ),
    )

    problems = _problems(tmp_path, "A", path)

    assert any("requires a repo owner" in problem for problem in problems)


def test_repo_subcontract_doc_requires_owner_and_passes(tmp_path: Path) -> None:
    path = "docs/validation/example-subcontract.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Example subcontract",
                "",
                "Doc placement: repo_subcontract_doc",
                "Doc kind: spec",
                "Doc lifecycle: active",
                "Repo owner: docs/product/backfill.md",
                "Doc exit rule: retire after the canonical owner absorbs it.",
                "",
                "Bounded Backfill contract.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_repo_subcontract_doc_without_owner_fails(tmp_path: Path) -> None:
    path = "docs/validation/example-subcontract.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Example subcontract",
                "",
                "Doc placement: repo_subcontract_doc",
                "Doc kind: spec",
                "Doc lifecycle: active",
                "Doc exit rule: retire after the canonical owner absorbs it.",
                "",
                "Bounded Backfill contract.",
            ]
        ),
    )

    problems = _problems(tmp_path, "A", path)

    assert any("requires a repo owner" in problem for problem in problems)


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


def test_new_tracked_note_lane_fails_even_with_repo_stub_metadata(
    tmp_path: Path,
) -> None:
    path = "docs/superpowers/notes/2026-07-01-private-review-note.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Private review note",
                "",
                "Doc placement: repo_stub_plus_obsidian",
                "Doc kind: note",
                "Doc lifecycle: archived",
                "Repo owner: docs/product/review-roundtrip.md",
                "",
                "This file is a sanitized public stub.",
            ]
        ),
    )

    problems = _problems(tmp_path, "A", path)

    assert any("retired docs lane" in problem for problem in problems)


def test_new_tracked_deepresearch_lane_fails(tmp_path: Path) -> None:
    path = "docs/deepresearch/2026-07-01-literature-note.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Literature note",
                "",
                "Doc placement: repo_stub_plus_obsidian",
                "Doc kind: note",
                "Doc lifecycle: archived",
                "Repo owner: docs/product/untargeted-method.md",
                "",
                "Stable claims should be absorbed into the product owner.",
            ]
        ),
    )

    problems = _problems(tmp_path, "A", path)

    assert any("retired docs lane" in problem for problem in problems)


def test_sanitized_stub_plus_obsidian_passes(tmp_path: Path) -> None:
    path = "docs/superpowers/plans/2026-07-01-private-review-note.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Private review note",
                "",
                "Doc placement: repo_stub_plus_obsidian",
                "Doc kind: note",
                "Doc lifecycle: archived",
                "Repo owner: docs/product/review-roundtrip.md",
                "",
                "This file is a sanitized public stub.",
            ]
        ),
    )

    result = check_doc_placement(tmp_path, [StagedMarkdown("A", path)])

    assert result.problems == ()


def test_non_allowlisted_docs_root_markdown_fails(tmp_path: Path) -> None:
    path = "docs/2026-07-01-branch-report.md"
    _write(
        tmp_path,
        path,
        "\n".join(
            [
                "# Branch report",
                "",
                "Doc placement: repo_support_doc",
                "Doc kind: report",
                "Doc lifecycle: archived",
                "Repo owner: docs/product/productization.md",
                "Doc exit rule: retire after summary is absorbed.",
            ]
        ),
    )

    problems = _problems(tmp_path, "A", path)

    assert any("docs root only allows" in problem for problem in problems)


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
                "Doc kind: plan",
                "Doc lifecycle: active",
                "Repo owner: docs/superpowers/handoffs/current/example.md",
                "Doc exit rule: replace with branch closeout after implementation.",
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
