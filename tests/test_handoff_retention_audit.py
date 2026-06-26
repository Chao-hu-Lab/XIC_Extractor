from __future__ import annotations

from pathlib import Path

from tools.diagnostics.handoff_retention_audit import run_handoff_retention_audit

HEADER = "path\tretention_decision\trepo_owner\tnext_review_event\trationale"
CURRENT = "docs/superpowers/handoffs/current/codex-example.md"
ARCHIVE = "docs/superpowers/handoffs/archive/2026-07-01_codex-example.md"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _inventory(root: Path, *rows: str) -> None:
    _write(
        root / "docs/superpowers/handoffs/RETENTION.tsv",
        "\n".join((HEADER, *rows)) + "\n",
    )


def test_missing_retention_row_is_blocker(tmp_path: Path) -> None:
    _write(tmp_path / CURRENT, "# Current\n\nBranch: `codex/example`\n")
    _inventory(tmp_path)

    result = run_handoff_retention_audit(tmp_path)

    assert any("no retention inventory row" in msg.message for msg in result.blockers)


def test_complete_inventory_passes_and_reports_candidates(tmp_path: Path) -> None:
    _write(tmp_path / CURRENT, "# Current\n\nBranch: `codex/example`\n")
    _write(tmp_path / ARCHIVE, "# Archive\n\nCompleted review narrative.\n")
    _inventory(
        tmp_path,
        (
            f"{CURRENT}\tactive_current\tPR #1\tpr_merge_or_close\t"
            "Active branch handoff."
        ),
        (
            f"{ARCHIVE}\tmove_to_obsidian_after_pr\tdocs/agent/example.md\t"
            "pr_merge_or_close\tReview details belong in Obsidian after PR."
        ),
    )

    result = run_handoff_retention_audit(tmp_path)

    assert result.blockers == ()
    assert result.summary["move_to_obsidian_after_pr"] == [ARCHIVE]


def test_current_handoff_with_archive_decision_is_blocker(tmp_path: Path) -> None:
    _write(tmp_path / CURRENT, "# Current\n\nBranch: `codex/example`\n")
    _inventory(
        tmp_path,
        (
            f"{CURRENT}\tkeep_repo_public_evidence\tdocs/agent/example.md\t"
            "manual_review\tWrong decision for current."
        ),
    )

    result = run_handoff_retention_audit(tmp_path)

    assert any(
        "current handoff must be active_current" in msg.message
        for msg in result.blockers
    )


def test_long_current_handoff_is_warning_not_blocker(tmp_path: Path) -> None:
    _write(
        tmp_path / CURRENT,
        "# Current\n" + "\n".join(f"line {index}" for index in range(205)),
    )
    _inventory(
        tmp_path,
        (
            f"{CURRENT}\tactive_current\tPR #1\tpr_merge_or_close\t"
            "Active branch handoff."
        ),
    )

    result = run_handoff_retention_audit(tmp_path)

    assert result.blockers == ()
    assert any("target is <=" in msg.message for msg in result.messages)
