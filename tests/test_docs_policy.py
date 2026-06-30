from __future__ import annotations

from tools.diagnostics.docs_policy import classify_doc, classify_doc_path


def test_docs_policy_marks_validation_as_route_retained_contract_surface() -> None:
    classification = classify_doc(
        "docs/superpowers/validation/current-packet.md",
        "# Validation packet\n\nDoc kind: validation_artifact\n",
    )

    assert classification.is_docs_routing_scan_target
    assert classification.is_validation_or_fixture
    assert not classification.is_high_risk_repo_doc
    assert classification.doc_kind == "validation_artifact"
    assert classification.doc_kind_source == "declared"


def test_docs_policy_marks_legacy_plan_as_high_risk_lifecycle_doc() -> None:
    classification = classify_doc_path(
        "docs/superpowers/plans/2026-07-01-example-plan.md"
    )

    assert classification.is_repo_doc
    assert classification.is_high_risk_repo_doc
    assert classification.is_lifecycle_managed
    assert classification.is_legacy_history
    assert classification.inferred_kind == "plan"


def test_docs_policy_uses_metadata_before_path_kind_inference() -> None:
    classification = classify_doc(
        "docs/superpowers/plans/2026-07-01-generated-cleanup-table.md",
        "\n".join(
            [
                "# Cleanup table",
                "",
                "Doc placement: repo_support_doc",
                "Doc kind: manifest",
                "Doc lifecycle: archived",
                "Repo owner: docs/project-layout.md",
                "Doc exit rule: keep while cleanup referrers need this manifest.",
            ]
        ),
    )

    assert classification.doc_kind == "manifest"
    assert classification.doc_kind_source == "declared"
    assert classification.path_classification.inferred_kind == "plan"
    assert classification.doc_lifecycle == "archived"
    assert classification.lifecycle_status == "declared"


def test_docs_policy_falls_back_to_path_kind_without_metadata() -> None:
    classification = classify_doc(
        "docs/superpowers/goals/2026-07-01-open-question.md",
        "# Open question\n\nNeeds a route decision.\n",
    )

    assert classification.doc_kind == "goal"
    assert classification.doc_kind_source == "inferred"
    assert classification.doc_lifecycle == "unknown"
    assert classification.lifecycle_status == "missing_lifecycle"


def test_docs_policy_reads_non_repo_placement_from_metadata() -> None:
    classification = classify_doc(
        "docs/superpowers/notes/private-review-note.md",
        "\n".join(
            [
                "# Private note",
                "",
                "Doc placement: private_obsidian_note",
                "Doc kind: note",
                "Doc lifecycle: archived",
                "Doc exit rule: source-copy to Obsidian and keep no repo body.",
            ]
        ),
    )

    assert classification.placement == "private_obsidian_note"
    assert classification.doc_kind == "note"
    assert classification.lifecycle_status == "declared"


def test_docs_policy_keeps_root_authority_docs_canonical_not_high_risk() -> None:
    classification = classify_doc(
        "docs/diagnostic-ledger.md",
        "\n".join(
            [
                "# Diagnostic Ledger",
                "",
                "Doc placement: formal_repo_doc",
                "Doc kind: report",
                "Doc lifecycle: active",
                "Repo owner: docs/diagnostic-ledger.md",
                (
                    "Doc exit rule: keep active while expensive RAW rerun "
                    "memory is needed."
                ),
            ]
        ),
    )

    assert classification.is_repo_doc
    assert classification.is_canonical_owner
    assert classification.is_canonical_owner_source == "path"
    assert not classification.is_high_risk_repo_doc
    assert classification.doc_kind == "report"
    assert classification.doc_kind_source == "declared"
    assert classification.repo_owner == "docs/diagnostic-ledger.md"


def test_formal_repo_doc_placement_upgrades_canonical_owner() -> None:
    classification = classify_doc(
        "docs/superpowers/notes/some-important-note.md",
        "\n".join(
            [
                "# Important note",
                "",
                "Doc placement: formal_repo_doc",
                "Doc kind: note",
                "Doc lifecycle: active",
                "Repo owner: docs/superpowers/notes/some-important-note.md",
                "Doc exit rule: keep while referenced.",
            ]
        ),
    )

    assert classification.is_canonical_owner
    assert classification.is_canonical_owner_source == "metadata_override"
    assert not classification.is_high_risk_repo_doc
    assert classification.is_high_risk_source == "metadata_cleared"


def test_any_placement_clears_high_risk() -> None:
    classification = classify_doc(
        "docs/superpowers/notes/private-review.md",
        "\n".join(
            [
                "# Private review",
                "",
                "Doc placement: repo_stub_plus_obsidian",
                "Doc kind: note",
                "Doc lifecycle: archived",
                "Repo owner: docs/superpowers/notes/private-review.md",
                "Doc exit rule: source-copy to Obsidian.",
            ]
        ),
    )

    assert not classification.is_high_risk_repo_doc
    assert classification.is_high_risk_source == "metadata_cleared"
    assert not classification.is_canonical_owner


def test_no_placement_keeps_high_risk() -> None:
    classification = classify_doc(
        "docs/superpowers/notes/unclassified-note.md",
        "# Unclassified note\n\nNo metadata markers.\n",
    )

    assert classification.is_high_risk_repo_doc
    assert classification.is_high_risk_source == "path"
    assert not classification.is_canonical_owner
    assert classification.is_canonical_owner_source == "path"


def test_canonical_path_stays_canonical_without_metadata() -> None:
    classification = classify_doc(
        "docs/product/user-guide.md",
        "# User guide\n\nNo placement metadata.\n",
    )

    assert classification.is_canonical_owner
    assert classification.is_canonical_owner_source == "path"
    assert not classification.is_high_risk_repo_doc
    assert classification.is_high_risk_source == "path"


def test_lifecycle_managed_not_overridden_by_metadata() -> None:
    classification = classify_doc(
        "docs/superpowers/plans/2026-07-01-example-plan.md",
        "\n".join(
            [
                "# Example plan",
                "",
                "Doc placement: formal_repo_doc",
                "Doc kind: plan",
                "Doc lifecycle: active",
                "Repo owner: docs/superpowers/plans/2026-07-01-example-plan.md",
                "Doc exit rule: keep while plan is active.",
            ]
        ),
    )

    assert classification.is_lifecycle_managed
