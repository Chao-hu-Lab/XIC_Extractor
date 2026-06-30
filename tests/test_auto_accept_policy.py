from __future__ import annotations

from pathlib import Path

from tools.diagnostics.auto_accept_policy import (
    AutoAcceptDecision,
    decide_auto_accept,
    extract_page_metadata,
    parse_auto_accept_config,
)


def test_parse_config_extracts_classes_and_threshold(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.write_text(
        'OBSIDIAN_VAULT_PATH="C:\\Vaults\\Research Vault"\n'
        "WIKI_STAGED_WRITES=true\n"
        "WIKI_AUTO_ACCEPT_CLASSES=development-history,command-narratives,branch-diaries\n"
        "WIKI_AUTO_ACCEPT_MIN_CONFIDENCE=0.8\n",
        encoding="utf-8",
    )
    classes, threshold = parse_auto_accept_config(config)
    assert classes == {"development-history", "command-narratives", "branch-diaries"}
    assert threshold == 0.8


def test_parse_config_defaults_when_missing(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.write_text(
        'OBSIDIAN_VAULT_PATH="C:\\Vaults\\Research Vault"\n'
        "WIKI_STAGED_WRITES=true\n",
        encoding="utf-8",
    )
    classes, threshold = parse_auto_accept_config(config)
    assert classes == set()
    assert threshold == 1.0


def test_matching_class_and_confidence_auto_accepts() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.85,
        staging_subdir="ready",
        auto_accept_classes={"development-history", "command-narratives"},
        min_confidence=0.8,
    )
    assert decision.action == "auto_accept"


def test_low_confidence_requires_manual() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.5,
        staging_subdir="ready",
        auto_accept_classes={"development-history"},
        min_confidence=0.8,
    )
    assert decision.action == "manual_review"
    assert "confidence" in decision.reason


def test_needs_merge_subdir_always_manual() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.95,
        staging_subdir="needs-merge",
        auto_accept_classes={"development-history"},
        min_confidence=0.8,
    )
    assert decision.action == "always_manual"
    assert "needs-merge" in decision.reason


def test_unrecognized_class_requires_manual() -> None:
    decision = decide_auto_accept(
        doc_class="research",
        base_confidence=0.9,
        staging_subdir="ready",
        auto_accept_classes={"development-history"},
        min_confidence=0.8,
    )
    assert decision.action == "manual_review"
    assert "class" in decision.reason


def test_empty_config_never_auto_accepts() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.99,
        staging_subdir="ready",
        auto_accept_classes=set(),
        min_confidence=1.0,
    )
    assert decision.action == "manual_review"


def test_extract_metadata_from_frontmatter() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: test",
        "lifecycle: draft",
        "tier: supporting",
        "tags: visibility/internal",
        "base_confidence: 0.85",
        "doc_class: development-history",
        "---",
        "",
        "Content.",
    ])
    doc_class, confidence = extract_page_metadata(text)
    assert doc_class == "development-history"
    assert confidence == 0.85


def test_extract_metadata_defaults() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: test",
        "---",
        "",
        "Content.",
    ])
    doc_class, confidence = extract_page_metadata(text)
    assert doc_class == ""
    assert confidence == 0.0


def test_needs_split_always_manual() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.99,
        staging_subdir="needs-split",
        auto_accept_classes={"development-history"},
        min_confidence=0.5,
    )
    assert decision.action == "always_manual"


def test_needs_review_always_manual() -> None:
    decision = decide_auto_accept(
        doc_class="command-narratives",
        base_confidence=1.0,
        staging_subdir="needs-review",
        auto_accept_classes={"command-narratives"},
        min_confidence=0.5,
    )
    assert decision.action == "always_manual"
