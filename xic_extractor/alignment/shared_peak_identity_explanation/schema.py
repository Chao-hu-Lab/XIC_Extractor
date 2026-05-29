from __future__ import annotations

from collections.abc import Mapping, Sequence

ORACLE_SCHEMA_VERSION = "shared_peak_identity_manual_oracle_v1"
EVIDENCE_SCHEMA_VERSION = "shared_peak_identity_evidence_v1"
EXPLANATION_SCHEMA_VERSION = "shared_peak_identity_explanation_v1"
RUN_FACTS_SCHEMA_VERSION = "shared_peak_identity_run_facts_v1"
BLAST_RADIUS_MANIFEST_SCHEMA_VERSION = (
    "shared_peak_identity_blast_radius_manifest_v1"
)
BLAST_RADIUS_SUMMARY_SCHEMA_VERSION = "shared_peak_identity_blast_radius_summary_v1"

ORACLE_COLUMNS = (
    "oracle_schema_version",
    "oracle_row_id",
    "feature_family_id",
    "sample_id",
    "manual_label",
    "manual_label_source",
    "manual_confidence",
    "manual_scope",
    "manual_scope_rule_id",
    "manual_reason_tags",
    "reviewed_eic",
    "reviewed_ms2_pattern",
    "reviewed_nl_or_product_pattern",
    "reviewed_intensity_opportunity",
    "dda_opportunity_basis",
    "related_family_id",
    "manual_review_note",
    "manual_review_source",
    "manual_reviewed_at",
)

EVIDENCE_VECTOR_COLUMNS = (
    "evidence_schema_version",
    "evidence_record_id",
    "oracle_row_id",
    "feature_family_id",
    "sample_id",
    "evidence_source",
    "source_role",
    "source_artifact",
    "source_artifact_sha256",
    "source_row_id",
    "machine_current_label",
    "machine_reason",
    "machine_blockers",
    "candidate_apex_rt",
    "family_reference_rt",
    "seed_delta_sec",
    "family_consensus_delta_sec",
    "matrix_local_delta_sec",
    "rt_context_status",
    "shape_status",
    "apex_clarity_status",
    "single_peak_region_status",
    "peak_completeness_status",
    "boundary_reference_status",
    "seed_rescued_boundary_overlap",
    "rescued_pairwise_boundary_overlap_min",
    "family_consensus_boundary_overlap",
    "pattern_similarity_status",
    "matched_product_count",
    "matched_neutral_loss_count",
    "pattern_conflict_status",
    "delta_mass_context",
    "intensity_status",
    "dda_opportunity_status",
    "fragmentation_observation_status",
    "scan_availability_status",
    "metric_availability_status",
)

EXPLANATION_COLUMNS = (
    "explanation_schema_version",
    "oracle_row_id",
    "feature_family_id",
    "sample_id",
    "manual_label",
    "manual_label_source",
    "manual_confidence",
    "manual_scope",
    "manual_reason_tags",
    "machine_current_label",
    "machine_reason",
    "machine_match_status",
    "matched_source_row_ids",
    "machine_source_role",
    "machine_blockers",
    "evidence_gap_class",
    "secondary_gap_tags",
    "explanation_status",
    "smallest_missing_fact",
    "recommended_next_action",
    "source_roles_seen",
    "source_artifacts",
)

RUN_FACTS_COLUMNS = (
    "run_facts_schema_version",
    "slice",
    "seed_rows_total",
    "seed_rows_explained",
    "seed_rows_unexplained",
    "seed_rows_inconclusive",
    "vocabulary_special_casing_detected",
    "blast_radius_assessed",
    "blast_radius_stale_artifact_count",
    "max_overfit_risk",
    "durable_oracle_path",
    "durable_oracle_sha256",
)

BLAST_RADIUS_MANIFEST_COLUMNS = (
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

BLAST_RADIUS_SUMMARY_COLUMNS = (
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

MANUAL_REASON_TAGS = frozenset(
    {
        "rt_close",
        "rt_too_far",
        "rt_drift_possible",
        "single_plausible_peak",
        "shape_complete",
        "shape_normal",
        "shape_bad",
        "pattern_similar",
        "pattern_partial",
        "pattern_mismatch",
        "low_intensity",
        "dda_stochastic_missing",
        "boundary_consistent",
        "boundary_ambiguous",
        "delta_mass_related",
        "scope_derived_unmentioned_fail",
        "human_unjudgeable",
    }
)

EVIDENCE_GAP_CLASSES = frozenset(
    {
        "machine_agrees_with_manual",
        "machine_too_conservative_low_opportunity",
        "machine_too_conservative_shape_or_pattern_unmodeled",
        "machine_too_permissive_rt_pattern_conflict",
        "machine_too_permissive_scope_rule_conflict",
        "boundary_reference_ambiguous",
        "rt_drift_policy_gap",
        "human_unjudgeable_shape_bad",
        "delta_mass_related_context_only",
        "unexplained_machine_manual_gap",
    }
)

ALLOWED_BY_FIELD: dict[str, frozenset[str]] = {
    "manual_label": frozenset(
        {"pass", "suspect", "fail", "human_unjudgeable", "not_applicable"}
    ),
    "manual_label_source": frozenset(
        {
            "direct_eic_ms2_review",
            "direct_eic_only_review",
            "scope_rule_unmentioned_fail",
            "family_all_reviewed_rule",
            "derived_from_related_family_context",
        }
    ),
    "manual_confidence": frozenset(
        {"high", "medium", "low", "unjudgeable", "not_applicable"}
    ),
    "manual_scope": frozenset(
        {
            "reviewed_cell",
            "reviewed_family_all_cells",
            "reviewed_family_named_cells_only",
            "scope_derived_unmentioned_fail",
            "family_level_context",
        }
    ),
    "evidence_source": frozenset(
        {
            "manual_oracle",
            "alignment_review",
            "alignment_cells",
            "candidate_gate_sidecar",
            "tier2_trace_sidecar",
            "identity_coherence_sidecar",
            "targeted_benchmark_context",
            "blast_radius_manifest",
        }
    ),
    "source_role": frozenset(
        {
            "manual_oracle",
            "selected_peak",
            "rescued_cell",
            "candidate_gate_family_context",
            "tier2_raw_reread",
            "identity_coherence_diagnostic",
            "targeted_context",
            "blast_radius_context",
        }
    ),
    "machine_source_role": frozenset(
        {
            "selected_peak",
            "rescued_cell",
            "candidate_gate_family_context",
            "tier2_raw_reread",
            "identity_coherence_diagnostic",
            "targeted_context",
            "blast_radius_context",
            "not_available",
            "not_applicable",
        }
    ),
    "machine_match_status": frozenset(
        {
            "no_match",
            "single_match",
            "ambiguous_multiple_matches",
            "missing_required_key",
            "not_applicable",
        }
    ),
    "rt_context_status": frozenset(
        {
            "supportive",
            "conflicting",
            "drift_possible",
            "ambiguous",
            "not_assessed",
            "unavailable",
        }
    ),
    "shape_status": frozenset(
        {
            "complete",
            "acceptable",
            "distorted",
            "low_intensity_but_coherent",
            "noisy_unjudgeable",
            "not_assessed",
            "unavailable",
            "ambiguous",
        }
    ),
    "apex_clarity_status": frozenset(
        {"clear", "weak", "ambiguous", "not_assessed", "unavailable"}
    ),
    "single_peak_region_status": frozenset(
        {
            "single_plausible_peak",
            "multiple_plausible_peaks",
            "flat_or_noisy_region",
            "not_assessed",
            "unavailable",
        }
    ),
    "peak_completeness_status": frozenset(
        {
            "complete",
            "clipped",
            "partial",
            "not_assessed",
            "unavailable",
            "ambiguous",
        }
    ),
    "boundary_reference_status": frozenset(
        {
            "seed_consistent",
            "rescued_pairwise_consistent",
            "family_consensus_consistent",
            "reference_disagreement",
            "not_assessed",
            "unavailable",
        }
    ),
    "pattern_similarity_status": frozenset(
        {
            "similar",
            "partial_similar",
            "mismatch",
            "not_observed",
            "not_assessed",
            "unavailable",
            "ambiguous",
        }
    ),
    "pattern_conflict_status": frozenset(
        {
            "none",
            "rt_pattern_conflict",
            "pattern_only_conflict",
            "not_assessed",
            "unavailable",
        }
    ),
    "delta_mass_context": frozenset(
        {"none", "related_family_context_only", "not_assessed", "unavailable"}
    ),
    "intensity_status": frozenset(
        {
            "sufficient",
            "low_but_visible",
            "too_low_to_assess",
            "not_assessed",
            "unavailable",
        }
    ),
    "dda_opportunity_status": frozenset(
        {
            "observed",
            "low_intensity_stochastic_not_observed",
            "expected_but_missing",
            "not_assessed",
            "not_applicable",
            "unavailable",
        }
    ),
    "fragmentation_observation_status": frozenset(
        {"observed", "not_observed", "conflicting", "not_assessed", "unavailable"}
    ),
    "scan_availability_status": frozenset(
        {"sufficient", "low", "not_assessed", "unavailable"}
    ),
    "metric_availability_status": frozenset(
        {
            "complete",
            "partial",
            "schema_missing",
            "artifact_missing",
            "stale_hash_mismatch",
            "not_assessed",
        }
    ),
    "slice": frozenset({"slice0", "slice1"}),
    "blast_radius_assessed": frozenset(
        {
            "present_current",
            "8raw_not_assessed",
            "85raw_not_assessed",
            "stale_hash_mismatch",
            "manifest_missing",
            "not_run_slice0",
            "not_assessed",
        }
    ),
    "artifact_status": frozenset(
        {
            "present_current",
            "present_hash_unpinned",
            "present_stale_hash_mismatch",
            "present_missing_required_fields",
            "missing",
            "schema_unsupported",
            "not_assessed",
            "unavailable",
        }
    ),
    "scope": frozenset(
        {
            "seed",
            "non_seed_same_family",
            "all_available_8raw",
            "all_available_85raw",
            "overall",
        }
    ),
    "artifact_role": frozenset(
        {
            "manual_oracle_fixture",
            "alignment_review",
            "alignment_cells",
            "tier2_trace_sidecar",
            "identity_diagnostic",
            "targeted_context",
            "blast_radius_context",
        }
    ),
    "freshness_basis": frozenset(
        {
            "slice0_evidence_vector",
            "expected_blast_radius_manifest",
            "not_available",
        }
    ),
    "max_overfit_risk": frozenset(
        {"none", "low", "medium", "high", "unassessed"}
    ),
    "overfit_risk": frozenset({"none", "low", "medium", "high", "unassessed"}),
    "evidence_gap_class": EVIDENCE_GAP_CLASSES,
    "explanation_status": frozenset(
        {"explained", "partially_explained", "unexplained", "inconclusive"}
    ),
    "recommended_next_action": frozenset(
        {
            "no_action",
            "inspect_manual_eic",
            "inspect_ms2_pattern",
            "add_shape_metric",
            "add_pattern_metric",
            "add_opportunity_metric",
            "check_boundary_reference",
            "check_blast_radius",
            "flag_for_v2_gate_review",
        }
    ),
}


def split_semicolon(value: str) -> tuple[str, ...]:
    return tuple(part for part in str(value or "").split(";") if part)


def validate_token(value: str, field: str) -> None:
    allowed = ALLOWED_BY_FIELD.get(field)
    if allowed is None:
        return
    if value not in allowed:
        raise ValueError(f"{field}: unsupported token {value!r}")


def validate_semicolon_tokens(
    value: str,
    *,
    field: str,
    allowed_tokens: set[str] | frozenset[str],
) -> None:
    for token in split_semicolon(value):
        if token.strip() != token or any(char.isspace() for char in token):
            raise ValueError(f"{field}: invalid whitespace in token {token!r}")
        if token not in allowed_tokens:
            raise ValueError(f"{field}: unsupported token {token!r}")


def validate_source_row_ids(value: str, valid_source_row_ids: set[str]) -> None:
    for source_row_id in split_semicolon(value):
        if source_row_id.strip() != source_row_id or any(
            char.isspace() for char in source_row_id
        ):
            raise ValueError(f"matched_source_row_ids: invalid id {source_row_id!r}")
        if source_row_id not in valid_source_row_ids:
            raise ValueError(
                f"matched_source_row_ids: unknown source row id {source_row_id!r}"
            )


def validate_row_tokens(row: Mapping[str, str]) -> None:
    for field in ALLOWED_BY_FIELD:
        if field in row and row[field] != "":
            validate_token(row[field], field)
    if "manual_reason_tags" in row:
        validate_semicolon_tokens(
            row["manual_reason_tags"],
            field="manual_reason_tags",
            allowed_tokens=MANUAL_REASON_TAGS,
        )
    if "secondary_gap_tags" in row:
        validate_semicolon_tokens(
            row["secondary_gap_tags"],
            field="secondary_gap_tags",
            allowed_tokens=MANUAL_REASON_TAGS,
        )


def require_columns(row: Mapping[str, str], columns: Sequence[str], label: str) -> None:
    missing = [column for column in columns if column not in row]
    if missing:
        raise ValueError(f"{label}: missing required columns: {', '.join(missing)}")
