from __future__ import annotations

from enum import StrEnum


class RequestIdentityCompletenessStatus(StrEnum):
    COMPLETE = "complete"
    MISSING_FRAGMENT_OBSERVATION_MODE = "missing_fragment_observation_mode"
    MISSING_PRECURSOR_MZ = "missing_precursor_mz"
    MISSING_PRODUCT_MZ = "missing_product_mz"
    MISSING_FRAGMENT_TAGS = "missing_fragment_tags"
    MISSING_TOLERANCE = "missing_tolerance"
    MISSING_MODE_SPECIFIC_CONSTRAINT = "missing_mode_specific_constraint"


class RequestCandidateIdentityStatus(StrEnum):
    NOT_ASSESSED = "not_assessed"
    MATCH = "match"
    MISSING_DISCOVERY_CANDIDATE_JOIN = "missing_discovery_candidate_join"
    MISSING_DIAGNOSTIC_FRAGMENT_EVIDENCE = "missing_diagnostic_fragment_evidence"
    REQUEST_CANDIDATE_IDENTITY_MISMATCH = "request_candidate_identity_mismatch"
    UNSUPPORTED_FRAGMENT_OBSERVATION_MODE = "unsupported_fragment_observation_mode"


class FragmentObservationMode(StrEnum):
    CID_NEUTRAL_LOSS = "cid_neutral_loss"


class FragmentTagMatchPolicy(StrEnum):
    ALL_REQUEST_TAGS_SUPPORTED = "all_request_tags_supported"


IDENTITY_COHERENCE_REQUEST_COLUMNS: tuple[str, ...] = (
    "request_id",
    "decision_id",
    "seed_candidate_id",
    "seed_sample",
    "fragment_observation_mode",
    "precursor_mz",
    "product_mz",
    "fragment_tags",
    "fragment_tag_match_policy",
    "fragment_profile_id",
    "fragment_profile_hash",
    "precursor_tolerance_ppm",
    "product_tolerance_ppm",
    "cid_observed_loss_da",
    "cid_observed_loss_tolerance_ppm",
    "request_identity_completeness_status",
    "request_candidate_identity_status",
    "precursor_error_ppm",
    "product_error_ppm",
    "cid_observed_loss_error_ppm",
    "cid_observed_loss_error_da",
    "request_builder_flags",
)

IDENTITY_COHERENCE_DECISION_COLUMNS: tuple[str, ...] = (
    "decision_id",
    "identity_family_id",
    "seed_candidate_id",
    "seed_sample",
    "seed_gate_class",
    "decision",
    "decision_reason",
    "request_identity_completeness_status",
    "request_candidate_identity_status",
    "total_coherent_sample_count",
    "non_seed_coherent_sample_count",
    "tier12_non_seed_identity_sample_count",
    "tier1_fragment_confirmed_sample_count",
    "tier2_shape_supported_sample_count",
    "tier2_seed_shape_fallback_sample_count",
    "tier3_width_only_sample_count",
    "min_total_coherent_samples",
    "min_non_seed_coherent_samples",
    "min_non_seed_tier12_identity_samples",
    "weak_basis_reason",
    "shape_reference_basis",
    "shape_reference_candidate_id",
    "prototype_width_sec",
    "center_rt_sec",
    "center_rt_source",
    "coherent_fraction",
    "infrastructure_blocked_sample_count",
    "data_quality_reject_sample_count",
    "forbidden_evidence_used",
)

IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS: tuple[str, ...] = (
    "decision_id",
    "identity_family_id",
    "sample_id",
    "candidate_id",
    "cell_assessment_status",
    "cell_identity_tier",
    "cell_identity_basis",
    "fragment_observation_mode",
    "fragment_match_status",
    "fragment_tags_supported",
    "rt_delta_center_sec",
    "rt_gate_status",
    "shape_status",
    "shape_similarity_cosine",
    "shape_reference_basis",
    "shape_reference_candidate_id",
    "shape_fallback_used",
    "shape_audit_status",
    "width_status",
    "width_ratio_to_prototype",
    "baseline_audit_status",
    "area_height_status",
    "non_rt_identity_result",
    "coherent_count_contribution",
    "tier12_count_contribution",
    "blocked_reason",
    "data_quality_reason",
    "forbidden_evidence_seen",
)

IDENTITY_COHERENCE_CONTROL_COLUMNS: tuple[str, ...] = (
    "control_id",
    "control_type",
    "control_name",
    "decision_id",
    "identity_family_id",
    "seed_candidate_id",
    "control_status",
    "control_expected_behavior",
    "control_observed_behavior",
    "control_pass",
    "control_failure_reason",
    "fragment_observation_mode",
    "decoy_generation_method",
    "decoy_source_request_id",
    "decoy_shift_value",
    "decoy_identity_constraint_changed",
    "positive_control_mapping_status",
    "positive_control_target_name",
    "positive_control_target_mz",
    "positive_control_target_rt_sec",
    "positive_control_mapping_error_ppm",
    "positive_control_mapping_delta_rt_sec",
    "control_notes",
)
