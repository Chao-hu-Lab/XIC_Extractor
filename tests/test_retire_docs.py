from __future__ import annotations

from pathlib import Path

from tools.diagnostics.retire_docs import (
    VAULT_ARCHIVE_DIR,
    find_retire_candidates,
    retire_files,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _completed_spec(owner: str = "docs/product/backfill.md") -> str:
    return "\n".join(
        [
            "# Backfill spec",
            "",
            "Doc placement: formal_repo_doc",
            "Doc kind: spec",
            "Doc lifecycle: implemented",
            f"Repo owner: {owner}",
            "Doc exit rule: retire after product owner absorption.",
            "",
            "Durable conclusion already lives in the product owner.",
        ]
    )


def test_completed_unreferenced_spec_auto_retires_after_vault_copy(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    spec = repo / "docs/superpowers/specs/2026-07-01-backfill-spec.md"
    _write(spec, _completed_spec())

    result = retire_files([spec], repo, vault, execute=True)

    assert result.retired == ["docs/superpowers/specs/2026-07-01-backfill-spec.md"]
    assert not spec.exists()
    assert (
        vault
        / VAULT_ARCHIVE_DIR
        / "2026-07-01-backfill-spec.md"
    ).exists()


def test_active_spec_is_kept_even_when_swept(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    spec = repo / "docs/superpowers/specs/2026-07-01-active-spec.md"
    _write(
        spec,
        _completed_spec().replace(
            "Doc lifecycle: implemented",
            "Doc lifecycle: active",
        ),
    )

    result = retire_files([spec], repo, vault, execute=True)

    assert result.retired == []
    assert result.kept == [
        ("docs/superpowers/specs/2026-07-01-active-spec.md", "active lifecycle")
    ]
    assert spec.exists()


def test_missing_lifecycle_metadata_is_not_auto_retired(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    note = repo / "docs/superpowers/plans/2026-07-01-unmarked-plan.md"
    _write(note, "# Plan\n\nHistorical implementation note.\n")

    result = retire_files([note], repo, vault, execute=True)

    assert result.retired == []
    assert result.kept == [
        (
            "docs/superpowers/plans/2026-07-01-unmarked-plan.md",
            (
                "missing or invalid lifecycle metadata; run product-absorption "
                "review before retirement"
            ),
        )
    ]
    assert note.exists()


def test_referrer_bound_spec_is_kept_without_stub_option(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    spec = repo / "docs/superpowers/specs/2026-07-01-backfill-spec.md"
    rel = "docs/superpowers/specs/2026-07-01-backfill-spec.md"
    _write(spec, _completed_spec())
    _write(repo / "docs/product/backfill.md", f"# Backfill\n\nSee `{rel}`.\n")

    result = retire_files([spec], repo, vault, execute=True)

    assert result.retired == []
    assert result.referrer_bound == [(rel, ("docs/product/backfill.md",))]
    assert spec.exists()


def test_referrer_bound_spec_can_be_replaced_with_short_stub(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    spec = repo / "docs/superpowers/specs/2026-07-01-backfill-spec.md"
    rel = "docs/superpowers/specs/2026-07-01-backfill-spec.md"
    _write(spec, _completed_spec())
    _write(repo / "docs/product/backfill.md", f"# Backfill\n\nSee `{rel}`.\n")

    result = retire_files([spec], repo, vault, execute=True, stub_bound=True)

    assert result.retired == []
    assert result.stubbed == [(rel, "docs/product/backfill.md")]
    text = spec.read_text(encoding="utf-8")
    assert "# Retired Document Stub" in text
    assert "Current repo authority: `docs/product/backfill.md`" in text
    assert "source_repo_path:docs/superpowers/specs/2026-07-01-backfill-spec.md" in text


def test_sweep_finds_markdown_transient_candidates_only(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    spec = repo / "docs/superpowers/specs/2026-07-01-backfill-spec.md"
    schema = repo / "docs/superpowers/specs/not-a-spec.json"
    readme = repo / "docs/superpowers/specs/README.md"
    _write(spec, _completed_spec())
    _write(schema, "{}\n")
    _write(readme, "# Specs\n")

    result = find_retire_candidates(repo)

    assert result == [spec]
