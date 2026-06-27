from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.diagnostics.docs_management_audit import run_audit

CURRENT_HANDOFF = (
    "docs/superpowers/handoffs/current/"
    "codex-docs-cleanup-official-docs-and-handoff.md"
)
CLOSEOUT_SUMMARY = (
    "docs/superpowers/closeouts/"
    "2026-06-26_codex-docs-cleanup_branch-closeout-summary.md"
)
RETENTION_INVENTORY = "docs/superpowers/handoffs/RETENTION.tsv"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _clean_repo(root: Path) -> None:
    _write(
        root / CURRENT_HANDOFF,
        "# Current handoff\n\nStatus: committed.\n",
    )
    _write(
        root / CLOSEOUT_SUMMARY,
        "# Closeout\n\nStatus: committed.\n\n## PR Body Seed\n\nProblem: x.\n",
    )
    _write(
        root / RETENTION_INVENTORY,
        "\n".join(
            [
                "path\tretention_decision\trepo_owner\tnext_review_event\trationale",
                (
                    f"{CURRENT_HANDOFF}\tactive_current\tPR #1\t"
                    "pr_merge_or_close\tActive branch stub."
                ),
            ]
        )
        + "\n",
    )


def _clean_vault(vault: Path) -> None:
    _write(
        vault / "index.md",
        "\n".join(
            [
                "---",
                "title: Index",
                "tags: [visibility/internal]",
                "lifecycle: draft",
                "tier: supporting",
                "---",
                "",
                "# Index",
            ]
        ),
    )
    manifest = {
        "version": 1,
        "last_updated": "2026-06-26T00:00:00Z",
        "sources": {},
        "projects": {},
        "stats": {
            "total_sources_ingested": 0,
            "total_pages": 1,
            "total_projects": 0,
        },
    }
    (vault / ".manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def _run_audit(root: Path, vault: Path | None = None):
    return run_audit(
        root,
        vault,
        allow_filesystem_handoff_fallback=True,
    )


def test_stale_handoff_state_is_a_blocker(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_vault(vault)
    _write(
        root / CURRENT_HANDOFF,
        "Status: batches are staged; no commit has been made.\n",
    )
    _write(
        root / RETENTION_INVENTORY,
        "\n".join(
            [
                "path\tretention_decision\trepo_owner\tnext_review_event\trationale",
                (
                    f"{CURRENT_HANDOFF}\tactive_current\tPR #1\t"
                    "pr_merge_or_close\tActive branch stub."
                ),
            ]
        )
        + "\n",
    )

    result = _run_audit(root, vault)

    assert any("stale branch-state phrase" in msg.message for msg in result.blockers)


def test_manifest_stats_mismatch_is_a_blocker(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_repo(root)
    _clean_vault(vault)
    manifest_path = vault / ".manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["stats"]["total_pages"] = 99
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = _run_audit(root, vault)

    assert any("stats.total_pages" in msg.message for msg in result.blockers)


def test_local_machine_path_is_reported_as_warning(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_repo(root)
    _clean_vault(vault)
    _write(
        root / "docs/agent-parameter-settings.md",
        "RAW root: C:\\Xcalibur\n",
    )

    result = _run_audit(root, vault)

    assert result.blockers == ()
    assert any(
        msg.severity == "warning" and "local/private path exposure" in msg.message
        for msg in result.messages
    )


def test_handoff_retention_blocker_is_reported_by_docs_management_audit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_vault(vault)
    _write(
        root / CURRENT_HANDOFF,
        "# Current handoff\n\nStatus: active.\n",
    )
    _write(
        root / RETENTION_INVENTORY,
        "path\tretention_decision\trepo_owner\tnext_review_event\trationale\n",
    )

    result = _run_audit(root, vault)

    assert "handoff_retention" in result.summary["repo"]
    assert result.summary["repo"]["handoff_retention"]["handoff_files"] == 1
    assert any(
        msg.path == CURRENT_HANDOFF
        and msg.message.startswith("handoff retention:")
        and "no retention inventory row" in msg.message
        for msg in result.blockers
    )


def test_ignored_local_handoff_is_not_a_docs_management_problem(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    _clean_vault(vault)
    _write(
        root / ".gitignore",
        "docs/superpowers/handoffs/current/*\n",
    )
    _write(
        root / "docs/superpowers/handoffs/current/ACTIVE.local.md",
        "# Local handoff\n\nStatus: active.\n",
    )
    _write(
        root / RETENTION_INVENTORY,
        "path\tretention_decision\trepo_owner\tnext_review_event\trationale\n",
    )
    subprocess.run(
        ["git", "add", ".gitignore", RETENTION_INVENTORY],
        cwd=root,
        check=True,
        capture_output=True,
    )

    result = _run_audit(root, vault)

    assert result.blockers == ()
    assert not [msg for msg in result.messages if msg.severity == "warning"]
    assert result.summary["repo"]["handoff_retention"]["handoff_files"] == 0


def test_env_example_local_machine_path_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_repo(root)
    _clean_vault(vault)
    _write(root / ".env.example", "XIC_RAW_ROOT=C:\\Xcalibur\\data\n")

    result = _run_audit(root, vault)

    assert result.blockers == ()
    top_hits = result.summary["repo"]["top_local_path_files"]
    assert any(item["path"] == ".env.example" for item in top_hits)


def test_xic_local_env_configures_vault_when_env_var_is_unset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    _clean_repo(root)
    _clean_vault(vault)
    _write(root / ".env.xic-local", f"OBSIDIAN_VAULT_PATH={vault}\n")

    result = _run_audit(root)

    assert result.blockers == ()
    assert result.summary["vault"]["vault_configured"] is True
    assert result.summary["vault"]["vault_path"] == str(vault)


def test_wikilink_heading_anchor_is_not_reported_broken(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_repo(root)
    _clean_vault(vault)
    _write(
        vault / "Target.md",
        "\n".join(
            [
                "---",
                "tags: [visibility/internal]",
                "lifecycle: draft",
                "tier: supporting",
                "---",
                "# Heading",
            ]
        ),
    )
    _write(
        vault / "index.md",
        "\n".join(
            [
                "---",
                "tags: [visibility/internal]",
                "lifecycle: draft",
                "tier: supporting",
                "---",
                "[[Target#Heading]]",
            ]
        ),
    )
    manifest = json.loads((vault / ".manifest.json").read_text(encoding="utf-8"))
    manifest["stats"]["total_pages"] = 2
    (vault / ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = _run_audit(root, vault)

    assert result.summary["vault"]["link_health"]["broken_wikilinks"] == 0


def test_multiline_frontmatter_tags_count_as_visibility(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_repo(root)
    _write(
        vault / "index.md",
        "\n".join(
            [
                "---",
                "tags:",
                "  - visibility/internal",
                "lifecycle: draft",
                "tier: supporting",
                "---",
                "# Index",
            ]
        ),
    )
    manifest = {
        "version": 1,
        "sources": {},
        "projects": {},
        "stats": {
            "total_sources_ingested": 0,
            "total_pages": 1,
            "total_projects": 0,
        },
    }
    (vault / ".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = _run_audit(root, vault)

    assert result.summary["vault"]["frontmatter"]["missing_visibility"] == 0


def test_clean_repo_and_vault_have_no_blockers(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    vault = tmp_path / "vault"
    _clean_repo(root)
    _clean_vault(vault)

    result = _run_audit(root, vault)

    assert result.blockers == ()
