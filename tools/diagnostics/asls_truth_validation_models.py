"""Models and schema constants for the P2c AsLS truth-validation gate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GATE_C1B_PLAN = "GO_FOR_C1B_PLAN_SYNTHETIC_ONLY"
GATE_RETIREMENT = "GO_FOR_LINEAR_EDGE_RETIREMENT"
GATE_REQUIRES_TIER_C = "REQUIRES_TIER_C"
GATE_REQUIRES_RETIREMENT_PREREQS = "REQUIRES_RETIREMENT_PREREQS"
GATE_NO_GO = "NO_GO_KEEP_LINEAR_EDGE"

INCONCLUSIVE_INVALID_INPUT = "INCONCLUSIVE_INVALID_INPUT"
INCONCLUSIVE_REGENERATE_TIER_A = "INCONCLUSIVE_REGENERATE_TIER_A"
INCONCLUSIVE_FIXTURE_LOCK_CHANGED = "INCONCLUSIVE_FIXTURE_LOCK_CHANGED"
INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH = "INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH"
INCONCLUSIVE_FIXTURE_GAP = "INCONCLUSIVE_FIXTURE_GAP"
INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE = (
    "INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE"
)

BENCHMARK_STATUS_PASS = "PASS"
BENCHMARK_STATUS_FAIL = "FAIL"
BENCHMARK_STATUS_INCONCLUSIVE = "INCONCLUSIVE"
ROW_STATUS_PASS = "PASS"
ROW_STATUS_HARD_BLOCKER = "HARD_BLOCKER"
ROW_STATUS_CAUTION = "CAUTION"

TIER_B1_RELEVANCE = "B1_RELEVANCE"
TIER_B1_ADJACENT_STRESS = "B1_ADJACENT_STRESS"
TIER_B2_STRESS = "B2_STRESS"

PRODUCTION_LIKE_IN_SCOPE = "IN_SCOPE"
PRODUCTION_LIKE_ADJACENT_STRESS = "ADJACENT_STRESS"
PRODUCTION_LIKE_OUT_OF_SCOPE_STRESS = "OUT_OF_SCOPE_STRESS"

DECISION_SCOPE_C1B = "C1B_RELEVANCE"
DECISION_SCOPE_RETIREMENT = "RETIREMENT_ONLY"
DECISION_SCOPE_REPORTING = "REPORTING_ONLY"

BLOCKER_SCOPE_B1_C1B = "B1_C1B"
BLOCKER_SCOPE_B2_RETIREMENT = "B2_RETIREMENT"
BLOCKER_SCOPE_CAUTION = "CAUTION"
BLOCKER_SCOPE_REPORTING_ONLY = "REPORTING_ONLY"

LEGACY_FIXTURE_CURRENT = "CURRENT"
LEGACY_FIXTURE_V1_NON_AUTHORITATIVE = "LEGACY_V1_NON_AUTHORITATIVE"
LEGACY_FIXTURE_NOT_APPLICABLE = "NOT_APPLICABLE"

TIER_B1_ACCURACY_RETIREMENT_ELIGIBLE = "RETIREMENT_ELIGIBLE"
TIER_B1_ACCURACY_PLANNING_ONLY = "PLANNING_ONLY_REQUIRES_TIER_C"
TIER_B1_ACCURACY_FAIL = "FAIL"

TIER_B2_STATUS_STRESS_REQUIRES_TIER_C = "STRESS_REQUIRES_TIER_C"
TIER_B2_STATUS_NOT_RUN = "NOT_RUN"

SUMMARY_FIELDS = (
    "readiness_status",
    "benchmark_status",
    "synthetic_decision_status",
    "gate_decision",
    "fixture_version",
    "tolerance_profile",
    "legacy_fixture_status",
    "decision_target",
    "fixture_manifest_hash",
    "fixture_lock_hash",
    "tier_a_generated_by_git_sha",
    "tier_a_current_code_compatibility_status",
    "tier_a_rows_hash",
    "tier_a_summary_hash",
    "tier_a_json_hash",
    "tier_a_report_hash",
    "tier_a_manifest_hash",
    "tier_a_expected_family_count",
    "tier_a_observed_family_count",
    "tier_a_expected_row_count",
    "tier_a_observed_row_count",
    "tier_a_source_input_hashes",
    "p2b_85raw_acceptance_ref",
    "p2b_85raw_acceptance_hash",
    "asls_lam",
    "asls_p",
    "asls_n_iter",
    "generator_seed",
    "bounds_policy",
    "heldout_row_count",
    "tier_b1_status",
    "tier_b1_accuracy_scope",
    "tier_b2_status",
    "fixture_scope_status",
    "tier_b1_heldout_row_count",
    "b1_adjacent_stress_row_count",
    "tier_b2_heldout_row_count",
    "tier_b1_hard_blocker_count",
    "tier_b2_stress_blocker_count",
    "production_like_heldout_row_count",
    "stress_heldout_row_count",
    "hard_blocker_count",
    "max_asls_raw_area_exceedance_count",
    "max_negative_nonblank_area_count",
    "blank_false_positive_rate",
    "blank_not_quantifiable_rate",
    "blank_synthetic_scope",
    "coverage_status",
    "b1_coverage_status",
    "b2_stress_status",
    "unmapped_observed_pattern_count",
    "tier_c_axis",
    "tier_c_status",
    "tier_c_nonblank_status",
    "blank_safety_status",
    "stress_axis_disposition_statuses",
    "tier_c_evidence_ref",
    "tier_c_evidence_hash",
    "waiver_ref",
    "methodology_waiver_hash",
    "methodology_owner",
    "waiver_scope",
    "waiver_valid",
    "waiver_expiry_or_revalidation_trigger",
    "retirement_prereq_status",
    "c1a_status",
    "c5_status",
    "rollback_column_status",
    "retirement_prereq_manifest_hash",
    "worst_heldout_median_relative_error_pct",
    "worst_heldout_p95_relative_error_pct",
    "previous_failed_run_refs",
)

ROW_FIELDS = (
    "tier",
    "tier_b_layer",
    "split",
    "fixture_class",
    "fixture_id",
    "replicate_id",
    "stress_role",
    "production_like_bounds_status",
    "scan_density_stratum",
    "integration_point_count",
    "integration_width_min",
    "target_label",
    "feature_family_id",
    "raw_area",
    "true_area",
    "linear_edge_area",
    "asls_area",
    "linear_edge_abs_error",
    "asls_abs_error",
    "linear_edge_relative_error_pct",
    "asls_relative_error_pct",
    "asls_error_over_linear_error",
    "asls_exceeds_raw_area",
    "asls_negative_nonblank_area",
    "blank_false_positive",
    "blank_not_quantifiable",
    "asls_area_uncertainty",
    "asls_baseline_residual_mad",
    "asls_area_uncertainty_noise_source",
    "rt_identity_status",
    "boundary_status",
    "blocker_scope",
    "row_status",
    "failure_reasons",
)

COVERAGE_FIELDS = (
    "observed_pattern",
    "target_label",
    "feature_family_id",
    "observed_row_count",
    "required_b1_fixture_classes",
    "covered_b1_fixture_classes",
    "b2_stress_fixture_classes",
    "coverage_status",
    "fixture_scope_status",
    "unmapped_reason",
)


@dataclass(frozen=True)
class TruthValidationOutputs:
    rows_tsv: Path
    summary_tsv: Path
    coverage_tsv: Path
    json_path: Path
    fixture_manifest_json: Path
    fixture_lock_json: Path
    tier_a_manifest_json: Path
    p2b_85raw_acceptance_json: Path
    tier_c_evidence_json: Path
    methodology_waiver_json: Path
    retirement_prereq_json: Path
    markdown_path: Path
    plots_dir: Path

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> "TruthValidationOutputs":
        return cls(
            rows_tsv=output_dir / "asls_truth_validation_rows.tsv",
            summary_tsv=output_dir / "asls_truth_validation_summary.tsv",
            coverage_tsv=output_dir / "asls_truth_validation_coverage.tsv",
            json_path=output_dir / "asls_truth_validation.json",
            fixture_manifest_json=(
                output_dir / "asls_truth_validation_fixture_manifest.json"
            ),
            fixture_lock_json=output_dir / "asls_truth_validation_fixture_lock.json",
            tier_a_manifest_json=output_dir / "asls_truth_validation_tier_a_manifest.json",
            p2b_85raw_acceptance_json=(
                output_dir / "asls_truth_validation_p2b_85raw_acceptance_manifest.json"
            ),
            tier_c_evidence_json=(
                output_dir / "asls_truth_validation_tier_c_evidence.json"
            ),
            methodology_waiver_json=(
                output_dir / "asls_truth_validation_methodology_waiver.json"
            ),
            retirement_prereq_json=(
                output_dir / "asls_truth_validation_retirement_prerequisites.json"
            ),
            markdown_path=output_dir / "asls_truth_validation.md",
            plots_dir=output_dir / "plots",
        )


def load_json_object(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON document must be a JSON object")
    return value
