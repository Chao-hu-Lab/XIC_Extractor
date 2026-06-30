from __future__ import annotations

from tools.diagnostics.validate_vault_page import validate_vault_page


def test_valid_page_passes() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page for validation",
        "lifecycle: draft",
        "tier: supporting",
        "tags: visibility/internal",
        "base_confidence: 0.8",
        "---",
        "",
        "# Test Page",
        "",
        "Content here.",
    ])
    errors = validate_vault_page(text)
    assert errors == []


def test_missing_summary_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "lifecycle: draft",
        "tier: supporting",
        "tags: visibility/internal",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("summary" in e for e in errors)


def test_invalid_lifecycle_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page",
        "lifecycle: active",
        "tier: supporting",
        "tags: visibility/internal",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("lifecycle" in e for e in errors)


def test_missing_visibility_tag_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page",
        "lifecycle: draft",
        "tier: supporting",
        "tags: ml architecture",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("visibility" in e for e in errors)


def test_missing_tier_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page",
        "lifecycle: draft",
        "tags: visibility/internal",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("tier" in e for e in errors)


def test_missing_frontmatter_fails() -> None:
    errors = validate_vault_page("# No frontmatter\n\nJust text.\n")
    assert any("frontmatter" in e for e in errors)


def test_invalid_tier_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page",
        "lifecycle: draft",
        "tier: critical",
        "tags: visibility/internal",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("tier" in e for e in errors)


def test_multiple_errors_reported() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert len(errors) >= 3
