from __future__ import annotations

import pytest

from xic_extractor.alignment.shared_peak_identity_explanation.schema import (
    ALLOWED_BY_FIELD,
    BLAST_RADIUS_MANIFEST_COLUMNS,
    BLAST_RADIUS_MANIFEST_SCHEMA_VERSION,
    BLAST_RADIUS_SUMMARY_COLUMNS,
    BLAST_RADIUS_SUMMARY_SCHEMA_VERSION,
    MANUAL_REASON_TAGS,
    validate_semicolon_tokens,
    validate_source_row_ids,
    validate_token,
)


def test_schema_allows_slice0_sentinel_tokens() -> None:
    validate_token("not_applicable", "manual_label")
    validate_token("not_applicable", "machine_current_label")
    validate_token("not_applicable", "machine_match_status")
    validate_token("slice0", "slice")
    validate_token("not_run_slice0", "blast_radius_assessed")
    validate_token("unassessed", "max_overfit_risk")


def test_semicolon_tokens_reject_unknown_or_whitespace() -> None:
    validate_semicolon_tokens(
        "rt_close;shape_complete",
        field="manual_reason_tags",
        allowed_tokens=MANUAL_REASON_TAGS,
    )
    with pytest.raises(ValueError):
        validate_semicolon_tokens(
            "rt_close;bad token",
            field="manual_reason_tags",
            allowed_tokens=MANUAL_REASON_TAGS,
        )
    with pytest.raises(ValueError):
        validate_semicolon_tokens(
            "rt_close;unknown",
            field="manual_reason_tags",
            allowed_tokens=MANUAL_REASON_TAGS,
        )


def test_matched_source_row_ids_are_dynamic_traceable_ids() -> None:
    validate_source_row_ids(
        "alignment_cells.tsv:1;alignment_review.tsv:2",
        {"alignment_cells.tsv:1", "alignment_review.tsv:2"},
    )
    with pytest.raises(ValueError):
        validate_source_row_ids("alignment_cells.tsv:999", {"alignment_cells.tsv:1"})
    assert "matched_source_row_ids" not in ALLOWED_BY_FIELD


def test_slice1_blast_radius_schema_constants_match_contract() -> None:
    assert (
        BLAST_RADIUS_MANIFEST_SCHEMA_VERSION
        == "shared_peak_identity_blast_radius_manifest_v1"
    )
    assert BLAST_RADIUS_MANIFEST_COLUMNS == (
        "manifest_schema_version",
        "artifact_id",
        "artifact_role",
        "artifact_path",
        "artifact_sha256",
        "expected_artifact_sha256",
        "freshness_basis",
        "artifact_schema_version",
        "artifact_status",
        "row_count",
        "sample_count",
        "family_count",
        "available_required_fields",
        "missing_required_fields",
        "generated_from_existing_artifact",
        "notes",
    )
    assert (
        BLAST_RADIUS_SUMMARY_SCHEMA_VERSION
        == "shared_peak_identity_blast_radius_summary_v1"
    )
    assert BLAST_RADIUS_SUMMARY_COLUMNS == (
        "summary_schema_version",
        "scope",
        "artifact_id",
        "evidence_gap_class",
        "seed_count",
        "context_row_count",
        "non_seed_same_family_count",
        "assessed_row_count",
        "all_available_row_count",
        "compatible_row_count",
        "unavailable_field_count",
        "contradictory_count",
        "ambiguous_machine_match_count",
        "compatible_fraction",
        "contradictory_fraction",
        "ambiguous_fraction",
        "unavailable_fraction",
        "overfit_risk",
        "example_oracle_row_ids",
        "example_feature_family_ids",
    )


def test_slice1_tokens_are_allowed() -> None:
    for token in {
        "present_current",
        "present_hash_unpinned",
        "present_stale_hash_mismatch",
        "present_missing_required_fields",
        "missing",
        "schema_unsupported",
        "not_assessed",
        "unavailable",
    }:
        validate_token(token, "artifact_status")

    for token in {
        "seed",
        "non_seed_same_family",
        "all_available_8raw",
        "all_available_85raw",
        "overall",
    }:
        validate_token(token, "scope")

    for token in {
        "manual_oracle_fixture",
        "alignment_review",
        "alignment_cells",
        "tier2_trace_sidecar",
        "identity_diagnostic",
        "targeted_context",
        "blast_radius_context",
    }:
        validate_token(token, "artifact_role")

    for token in {
        "slice0_evidence_vector",
        "expected_blast_radius_manifest",
        "not_available",
    }:
        validate_token(token, "freshness_basis")

    for token in {"none", "low", "medium", "high", "unassessed"}:
        validate_token(token, "overfit_risk")

    validate_token("slice1", "slice")
    validate_token("present_current", "blast_radius_assessed")


def test_slice1_schema_rejects_noncanonical_review_drift_tokens() -> None:
    for field, token in (
        ("freshness_basis", "slice0_evidence_vectors"),
        ("freshness_basis", "expected_manifest"),
        ("freshness_basis", "missing_expected_hash"),
        ("freshness_basis", "not_applicable"),
        ("artifact_role", "slice0_explanations"),
        ("artifact_role", "slice0_evidence_vectors"),
        ("artifact_role", "candidate_gate_8raw"),
        ("artifact_role", "tier2_coherence_8raw"),
    ):
        with pytest.raises(ValueError):
            validate_token(token, field)
