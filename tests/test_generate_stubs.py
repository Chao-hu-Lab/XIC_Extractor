from __future__ import annotations

from tools.diagnostics.generate_stubs import (
    extract_doc_kind,
    generate_stub_content,
    generate_stubs,
    infer_repo_owner,
    main,
    parse_blocker_tsv,
)


def test_parse_blocker_tsv_extracts_fields(tmp_path: object) -> None:
    tsv = tmp_path / "blockers.tsv"  # type: ignore[union-attr]
    tsv.write_text(
        '"target_source_path"\t"target_note"\t"target_doc_class"\t"target_line_count"'
        '\t"reference_type"\t"referrer_path"\t"referrer_kind"\t"referrer_line"'
        '\t"referrer_text"\t"suggested_resolution"\t"evidence_terms"\t"strong_risk_terms"\n'
        '"docs/notes/example.md"\t"Example Note.md"\t"development-history"\t"100"'
        '\t"name_title"\t"docs/agent/contract.md"\t"agent_runtime_doc"\t"42"'
        '\t"some text"\t"keep_target_or_leave_stub_first"\t"85RAW"\t""\n',
        encoding="utf-8",
    )
    rows = parse_blocker_tsv(tsv)
    assert len(rows) == 1
    assert rows[0].target_source_path == "docs/notes/example.md"
    assert rows[0].target_note == "Example Note.md"
    assert rows[0].target_doc_class == "development-history"
    assert rows[0].suggested_resolution == "keep_target_or_leave_stub_first"


def test_generate_stub_content_produces_valid_stub() -> None:
    content = generate_stub_content(
        target_source_path="docs/notes/example.md",
        target_note="Example Note.md",
        doc_kind="note",
        repo_owner="docs/product/discovery.md",
    )
    assert "Doc placement: repo_stub_plus_obsidian" in content
    assert "Doc kind: note" in content
    assert "Doc lifecycle: retired" in content
    assert "Repo owner: docs/product/discovery.md" in content
    assert "Doc exit rule:" in content
    assert "[[Example Note.md]]" in content
    non_marker_lines = [
        line
        for line in content.strip().splitlines()
        if line.strip()
        and not line.startswith("Doc ")
        and not line.startswith("Repo owner:")
    ]
    assert len(non_marker_lines) <= 5


def test_extract_doc_kind_from_existing_content() -> None:
    text = "# Plan\n\nDoc kind: plan\nDoc lifecycle: active\n"
    assert extract_doc_kind(text) == "plan"


def test_extract_doc_kind_defaults_to_note() -> None:
    assert extract_doc_kind("# No metadata here\n") == "note"


def test_infer_repo_owner_from_existing_content() -> None:
    text = "Repo owner: docs/product/discovery.md\n"
    assert infer_repo_owner(text, "docs/notes/x.md") == "docs/product/discovery.md"


def test_infer_repo_owner_falls_back_to_self() -> None:
    assert infer_repo_owner("# No owner\n", "docs/notes/x.md") == "docs/notes/x.md"


def test_generate_stubs_dry_run_does_not_write(tmp_path: object) -> None:
    repo_root = tmp_path / "repo"  # type: ignore[union-attr]
    repo_root.mkdir()
    target = repo_root / "docs" / "notes"
    target.mkdir(parents=True)
    (target / "example.md").write_text(
        "# Example\n\nDoc kind: note\nDoc lifecycle: active\n"
        "Repo owner: docs/product/discovery.md\n",
        encoding="utf-8",
    )
    tsv = tmp_path / "blockers.tsv"  # type: ignore[union-attr]
    tsv.write_text(
        '"target_source_path"\t"target_note"\t"target_doc_class"\t"target_line_count"'
        '\t"reference_type"\t"referrer_path"\t"referrer_kind"\t"referrer_line"'
        '\t"referrer_text"\t"suggested_resolution"\t"evidence_terms"\t"strong_risk_terms"\n'
        '"docs/notes/example.md"\t"Example Note.md"\t"development-history"\t"50"'
        '\t"name_title"\t"docs/agent/c.md"\t"agent_runtime_doc"\t"1"'
        '\t"ref"\t"keep_target_or_leave_stub_first"\t""\t""\n',
        encoding="utf-8",
    )
    result = generate_stubs(tsv, repo_root, dry_run=True)
    assert len(result.planned) == 1
    assert result.planned[0].target_source_path == "docs/notes/example.md"
    original = (target / "example.md").read_text(encoding="utf-8")
    assert "repo_stub_plus_obsidian" not in original


def test_generate_stubs_execute_writes_stub(tmp_path: object) -> None:
    repo_root = tmp_path / "repo"  # type: ignore[union-attr]
    repo_root.mkdir()
    target = repo_root / "docs" / "notes"
    target.mkdir(parents=True)
    (target / "example.md").write_text(
        "# Example\n\nDoc kind: note\nDoc lifecycle: active\n"
        "Repo owner: docs/product/discovery.md\n",
        encoding="utf-8",
    )
    tsv = tmp_path / "blockers.tsv"  # type: ignore[union-attr]
    tsv.write_text(
        '"target_source_path"\t"target_note"\t"target_doc_class"\t"target_line_count"'
        '\t"reference_type"\t"referrer_path"\t"referrer_kind"\t"referrer_line"'
        '\t"referrer_text"\t"suggested_resolution"\t"evidence_terms"\t"strong_risk_terms"\n'
        '"docs/notes/example.md"\t"Example Note.md"\t"development-history"\t"50"'
        '\t"name_title"\t"docs/agent/c.md"\t"agent_runtime_doc"\t"1"'
        '\t"ref"\t"keep_target_or_leave_stub_first"\t""\t""\n',
        encoding="utf-8",
    )
    result = generate_stubs(tsv, repo_root, dry_run=False)
    assert len(result.written) == 1
    stub_text = (target / "example.md").read_text(encoding="utf-8")
    assert "Doc placement: repo_stub_plus_obsidian" in stub_text
    assert "Doc kind: note" in stub_text
    assert "[[Example Note.md]]" in stub_text


def test_generate_stubs_cli_fails_when_required_stub_errors(
    tmp_path: object,
    capsys: object,
) -> None:
    repo_root = tmp_path / "repo"  # type: ignore[union-attr]
    repo_root.mkdir()
    tsv = tmp_path / "blockers.tsv"  # type: ignore[union-attr]
    tsv.write_text(
        '"target_source_path"\t"target_note"\t"target_doc_class"\t"target_line_count"'
        '\t"reference_type"\t"referrer_path"\t"referrer_kind"\t"referrer_line"'
        '\t"referrer_text"\t"suggested_resolution"\t"evidence_terms"\t"strong_risk_terms"\n'
        '"docs/notes/missing.md"\t"Missing Note.md"\t"development-history"\t"50"'
        '\t"name_title"\t"docs/agent/c.md"\t"agent_runtime_doc"\t"1"'
        '\t"ref"\t"keep_target_or_leave_stub_first"\t""\t""\n',
        encoding="utf-8",
    )

    exit_code = main([str(tsv), "--repo-root", str(repo_root), "--execute"])

    assert exit_code == 1
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "ERROR: docs/notes/missing.md (target file does not exist)" in captured.out
