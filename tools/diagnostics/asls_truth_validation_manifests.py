"""Manifest validators for the P2c AsLS truth-validation gate."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.diagnostics.asls_truth_validation_models import (
    DECISION_SCOPE_C1B,
    DECISION_SCOPE_REPORTING,
    DECISION_SCOPE_RETIREMENT,
    LEGACY_FIXTURE_CURRENT,
    LEGACY_FIXTURE_V1_NON_AUTHORITATIVE,
    PRODUCTION_LIKE_ADJACENT_STRESS,
    PRODUCTION_LIKE_IN_SCOPE,
    PRODUCTION_LIKE_OUT_OF_SCOPE_STRESS,
    TIER_B1_ADJACENT_STRESS,
    TIER_B1_RELEVANCE,
    TIER_B2_STRESS,
    load_json_object,
)

REQUIRED_FIXTURE_CLASSES = (
    "flat_peak_control",
    "sloped_baseline_peak",
    "hump_baseline_peak",
    "tailing_peak",
    "adjacent_shoulder",
    "coeluting_interference",
    "local_baseline_dip",
    "heteroscedastic_noise_peak",
    "low_sn_peak",
    "saturated_or_clipped_apex",
    "blank_noise_control",
)
B1_RELEVANCE_FIXTURE_CLASSES = (
    "flat_peak_control",
    "sloped_baseline_peak",
    "tailing_peak",
    "adjacent_shoulder",
)
B2_STRESS_FIXTURE_CLASSES = tuple(
    class_name
    for class_name in REQUIRED_FIXTURE_CLASSES
    if class_name not in B1_RELEVANCE_FIXTURE_CLASSES
)
MIN_CALIBRATION_REPLICATES_PER_CLASS = 10
MIN_HELDOUT_REPLICATES_PER_CLASS = 25
REQUIRED_NONBLANK_SN_WIDTH_COMBINATIONS = 9
REQUIRED_BLANK_HARD_CASE_STRATA = (
    "low_noise_blank",
    "high_noise_blank",
    "sloped_blank",
    "hump_blank",
    "carryover_like_blank",
)

REQUIRED_TIER_A_FAMILIES = {
    ("15N5-8-oxodG", "FAM000538"),
    ("d3-5-hmdC", "FAM000153"),
    ("d3-5-medC", "FAM000031"),
    ("d3-N6-medA", "FAM000242"),
    ("d3-dG-C8-MeIQx", "FAM001878"),
    ("d4-N6-2HE-dA", "FAM000807"),
}

_REQUIRED_TIER_A_ARTIFACT_KEYS = (
    "rows",
    "summary",
    "json",
    "report",
)
_REQUIRED_FIXTURE_CLASS_KEYS = (
    "default_gate_layer",
    "truth_target_type",
    "stress_role",
    "allowed_decision_targets",
    "production_like_bounds_policy",
    "promotion_requires_review_evidence",
    "true_baseline_function",
    "true_peak_function",
    "parameter_grid",
    "split_policy",
    "required_hard_case_strata",
    "expected_linear_edge_failure_mode",
    "tolerance_rationale",
)
_VALID_GATE_LAYERS = {TIER_B1_RELEVANCE, TIER_B1_ADJACENT_STRESS, TIER_B2_STRESS}
_VALID_DECISION_SCOPES = {
    DECISION_SCOPE_C1B,
    DECISION_SCOPE_RETIREMENT,
    DECISION_SCOPE_REPORTING,
}
_VALID_PRODUCTION_BOUNDS_STATUSES = {
    PRODUCTION_LIKE_IN_SCOPE,
    PRODUCTION_LIKE_ADJACENT_STRESS,
    PRODUCTION_LIKE_OUT_OF_SCOPE_STRESS,
}
_VALID_TRUTH_TARGET_TYPES = {
    "baseline_corrected_peak_area",
    "accepted_boundary_signal",
    "blank_zero_area",
    "stress_not_truth",
}
_REQUIRED_PARAMETER_GRID_KEYS = (
    "scan_spacing_min",
    "peak_height",
    "peak_sigma_min",
    "baseline_slope_pct_peak_height_per_min",
    "hump_amplitude_pct_peak_height",
    "tail_factor_sigma",
    "shoulder_offset_sigma",
    "shoulder_height_fraction",
    "coeluting_interference_height_fraction",
    "local_dip_depth_fraction",
    "clip_fraction",
)
_REQUIRED_LOCK_RECORD_KEYS = (
    "fixture_id",
    "fixture_class",
    "split",
    "replicate_id",
    "sn_stratum",
    "peak_width_stratum",
    "hard_case_stratum",
    "parameters",
    "true_area_formula_version",
    "bounds_policy",
    "expected_bound_indices",
    "gate_layer",
    "stress_role",
    "production_like_bounds_status",
    "scan_density_stratum",
    "integration_point_count",
    "integration_width_min",
    "tier_a_width_quantile_band",
    "decision_scope",
    "truth_target_type",
    "required_for_b1_coverage",
    "fixture_scope_reason",
    "generator_input_hash",
)


@dataclass(frozen=True)
class TierAFamily:
    target_label: str
    feature_family_id: str
    old_p2_status: str
    expected_row_count: int
    expected_sample_count: int
    required_plot_path: str


@dataclass(frozen=True)
class TierAManifest:
    manifest_version: str
    generated_by_command: str
    environment_profile: str
    expected_dataset_label: str
    raw_subset: str
    branch_family: str
    p2b_semantic_version: str
    expected_family_count: int
    expected_row_count: int
    generated_by_git_sha: str
    current_code_compatibility_status: str
    source_inputs: Mapping[str, Mapping[str, Any]]
    families: tuple[TierAFamily, ...]
    artifact_hashes: Mapping[str, Mapping[str, Any]]
    p2b_85raw_acceptance_refs: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class FixtureManifest:
    fixture_version: str
    tolerance_profile: str
    asls_lam: float
    asls_p: float
    asls_n_iter: int
    generator_seed: int
    fixture_classes: tuple[str, ...]
    b1_fixture_classes: tuple[str, ...]
    b2_fixture_classes: tuple[str, ...]
    minimum_calibration_replicates_per_class: int
    minimum_heldout_replicates_per_class: int
    fixture_lock_path: str
    fixture_lock_hash: str
    required_hard_case_strata_by_class: Mapping[str, tuple[str, ...]]
    gate_layer_by_class: Mapping[str, str]
    truth_target_type_by_class: Mapping[str, str]
    stress_role_by_class: Mapping[str, str]
    allowed_decision_targets_by_class: Mapping[str, tuple[str, ...]]
    legacy_fixture_status: str
    fixture_scope_status: str


@dataclass(frozen=True)
class FixtureLockRecord:
    fixture_id: str
    fixture_class: str
    split: str
    replicate_id: int
    sn_stratum: str
    peak_width_stratum: str
    hard_case_stratum: str
    parameters: Mapping[str, Any]
    true_area_formula_version: str
    bounds_policy: str
    expected_bound_indices: tuple[int, int]
    gate_layer: str
    stress_role: str
    production_like_bounds_status: str
    scan_density_stratum: str
    integration_point_count: int
    integration_width_min: float
    tier_a_width_quantile_band: str
    decision_scope: str
    truth_target_type: str
    required_for_b1_coverage: bool
    fixture_scope_reason: str
    generator_input_hash: str


@dataclass(frozen=True)
class FixtureLock:
    lock_version: str
    whole_lock_hash: str
    review_freeze_status: str
    records: tuple[FixtureLockRecord, ...]


def load_tier_a_manifest(path: Path) -> TierAManifest:
    data = load_json_object(path)
    generated_by_command = _require_text(data, "generated_by_command", path)
    environment_profile = _require_text(data, "environment_profile", path)
    expected_dataset_label = _require_text(data, "expected_dataset_label", path)
    raw_subset = _require_text(data, "raw_subset", path)
    branch_family = _require_text(data, "branch_family", path)
    p2b_semantic_version = _require_text(data, "p2b_semantic_version", path)
    raw_source_inputs = _require_mapping(data, "source_inputs", path)
    if not raw_source_inputs:
        raise ValueError(f"{path}: source_inputs must not be empty")
    source_inputs = {
        key: _validate_hashed_ref(value, path, label=f"source_inputs.{key}")
        for key, value in raw_source_inputs.items()
    }
    expected_family_count = _require_positive_int(data, "expected_family_count", path)
    expected_row_count = _require_positive_int(data, "expected_row_count", path)
    generated_by_git_sha = _require_text(data, "generated_by_git_sha", path)
    current_code_status = _require_text(
        data, "current_code_compatibility_status", path
    )
    raw_artifacts = _require_mapping(data, "artifact_hashes", path)
    artifacts: dict[str, Mapping[str, Any]] = {}
    for key in _REQUIRED_TIER_A_ARTIFACT_KEYS:
        artifacts[key] = _validate_hashed_ref(
            _require_mapping(raw_artifacts, key, path),
            path,
            label=f"artifact_hashes.{key}",
        )
    families_data = _require_sequence(data, "expected_families", path)
    families = tuple(_parse_tier_a_family(row, path) for row in families_data)
    family_keys = {(row.target_label, row.feature_family_id) for row in families}
    missing = sorted(REQUIRED_TIER_A_FAMILIES - family_keys)
    if missing:
        raise ValueError(f"{path}: missing Tier A expected families: {missing}")
    extra = sorted(family_keys - REQUIRED_TIER_A_FAMILIES)
    if extra:
        raise ValueError(f"{path}: unexpected Tier A expected families: {extra}")
    if expected_family_count != len(REQUIRED_TIER_A_FAMILIES):
        raise ValueError(f"{path}: expected_family_count must be 6")
    if expected_row_count != 48:
        raise ValueError(f"{path}: expected_row_count must be 48")
    if len(families) != expected_family_count:
        raise ValueError(f"{path}: expected_family_count does not match families")
    if sum(row.expected_row_count for row in families) != expected_row_count:
        raise ValueError(f"{path}: expected_row_count does not match families")
    raw_refs = data.get("p2b_85raw_acceptance_refs", ())
    if not isinstance(raw_refs, list | tuple):
        raise ValueError(f"{path}: p2b_85raw_acceptance_refs must be a list")
    p2b_refs = tuple(_validate_acceptance_ref(row, path) for row in raw_refs)
    if not p2b_refs:
        raise ValueError(f"{path}: p2b_85raw_acceptance_refs must not be empty")
    return TierAManifest(
        manifest_version=_require_text(data, "manifest_version", path),
        generated_by_command=generated_by_command,
        environment_profile=environment_profile,
        expected_dataset_label=expected_dataset_label,
        raw_subset=raw_subset,
        branch_family=branch_family,
        p2b_semantic_version=p2b_semantic_version,
        expected_family_count=expected_family_count,
        expected_row_count=expected_row_count,
        generated_by_git_sha=generated_by_git_sha,
        current_code_compatibility_status=current_code_status,
        source_inputs=source_inputs,
        families=families,
        artifact_hashes=artifacts,
        p2b_85raw_acceptance_refs=p2b_refs,
    )


def load_fixture_manifest(path: Path) -> FixtureManifest:
    data = load_json_object(path)
    fixture_version = _require_text(data, "fixture_version", path)
    tolerance_profile = _require_text(data, "tolerance_profile", path)
    is_legacy = (
        fixture_version != "synthetic_truth_fixture_v2"
        or tolerance_profile != "asls_truth_tolerance_v2"
    )
    classes = _require_sequence(data, "fixture_classes", path)
    class_names: list[str] = []
    hard_case_strata_by_class: dict[str, tuple[str, ...]] = {}
    gate_layer_by_class: dict[str, str] = {}
    truth_target_type_by_class: dict[str, str] = {}
    stress_role_by_class: dict[str, str] = {}
    allowed_targets_by_class: dict[str, tuple[str, ...]] = {}
    for row in classes:
        if not isinstance(row, Mapping):
            raise ValueError(f"{path}: fixture_classes entries must be objects")
        class_name = _require_text(row, "fixture_class", path)
        class_names.append(class_name)
        required_keys = (
            tuple(
                key
                for key in _REQUIRED_FIXTURE_CLASS_KEYS
                if key
                not in {
                    "default_gate_layer",
                    "truth_target_type",
                    "stress_role",
                    "allowed_decision_targets",
                    "production_like_bounds_policy",
                    "promotion_requires_review_evidence",
                }
            )
            if is_legacy
            else _REQUIRED_FIXTURE_CLASS_KEYS
        )
        for key in required_keys:
            if key not in row:
                raise ValueError(f"{path}: {class_name} missing {key}")
        gate_layer = _optional_class_gate_layer(class_name, row, is_legacy, path)
        truth_target = _optional_truth_target_type(class_name, row, is_legacy, path)
        stress_role = _optional_stress_role(class_name, row, is_legacy, path)
        allowed_targets = _optional_allowed_targets(class_name, row, is_legacy, path)
        gate_layer_by_class[class_name] = gate_layer
        truth_target_type_by_class[class_name] = truth_target
        stress_role_by_class[class_name] = stress_role
        allowed_targets_by_class[class_name] = allowed_targets
        if not is_legacy:
            _require_text(row, "production_like_bounds_policy", path)
            if not isinstance(row.get("promotion_requires_review_evidence"), bool):
                raise ValueError(
                    f"{path}: {class_name} promotion_requires_review_evidence "
                    "must be a boolean"
                )
        expected_split_policy = (
            "10 calibration plus 25 heldout_gate rows locked in "
            "asls_truth_validation_fixture_lock.json"
        )
        split_policy = _require_text(row, "split_policy", path)
        if split_policy != expected_split_policy:
            raise ValueError(
                f"{path}: {class_name} split_policy must state 25 heldout rows"
            )
        parameter_grid = _require_mapping(row, "parameter_grid", path)
        for key in _REQUIRED_PARAMETER_GRID_KEYS:
            if key not in parameter_grid:
                raise ValueError(f"{path}: {class_name} missing parameter_grid.{key}")
        hard_case_strata = _require_sequence(row, "required_hard_case_strata", path)
        if not hard_case_strata:
            raise ValueError(f"{path}: {class_name} missing hard-case strata")
        hard_case_tuple = tuple(str(value) for value in hard_case_strata)
        if (
            class_name == "blank_noise_control"
            and hard_case_tuple != REQUIRED_BLANK_HARD_CASE_STRATA
        ):
            raise ValueError(
                f"{path}: blank_noise_control hard-case strata must match "
                "required blank safety strata"
            )
        hard_case_strata_by_class[class_name] = hard_case_tuple
    duplicate_classes = [
        item for item, count in Counter(class_names).items() if count > 1
    ]
    if duplicate_classes:
        raise ValueError(f"{path}: duplicate fixture classes: {duplicate_classes}")
    expected_classes = set(REQUIRED_FIXTURE_CLASSES)
    actual_classes = set(class_names)
    missing = sorted(expected_classes - actual_classes)
    if missing:
        raise ValueError(f"{path}: missing required fixture classes: {missing}")
    extra = sorted(actual_classes - expected_classes)
    if extra:
        raise ValueError(f"{path}: unexpected fixture classes: {extra}")
    min_cal = _require_positive_int(
        data, "minimum_calibration_replicates_per_class", path
    )
    min_heldout = _require_positive_int(
        data, "minimum_heldout_replicates_per_class", path
    )
    if min_cal < MIN_CALIBRATION_REPLICATES_PER_CLASS:
        raise ValueError(f"{path}: minimum_calibration_replicates_per_class < 10")
    if min_heldout < MIN_HELDOUT_REPLICATES_PER_CLASS:
        raise ValueError(f"{path}: minimum_heldout_replicates_per_class < 25")
    fixture_lock_path = _require_text(data, "fixture_lock_path", path)
    fixture_lock_hash = _require_text(data, "fixture_lock_hash", path)
    lock_path = _resolve_manifest_ref(path, fixture_lock_path)
    if not lock_path.exists():
        raise ValueError(
            f"{path}: fixture_lock_path does not exist: {fixture_lock_path}"
        )
    lock = load_fixture_lock(lock_path)
    if lock.whole_lock_hash != fixture_lock_hash:
        raise ValueError(f"{path}: fixture_lock_hash does not match fixture lock")
    validate_fixture_lock_coverage(
        lock,
        required_hard_case_strata_by_class=hard_case_strata_by_class,
        path=lock_path,
    )
    return FixtureManifest(
        fixture_version=fixture_version,
        tolerance_profile=tolerance_profile,
        asls_lam=_require_float(
            _require_mapping(data, "asls_params", path), "lam", path
        ),
        asls_p=_require_float(_require_mapping(data, "asls_params", path), "p", path),
        asls_n_iter=_require_positive_int(
            _require_mapping(data, "asls_params", path), "n_iter", path
        ),
        generator_seed=_require_positive_int(data, "generator_seed", path),
        fixture_classes=tuple(class_names),
        b1_fixture_classes=tuple(
            class_name
            for class_name in class_names
            if gate_layer_by_class[class_name] == TIER_B1_RELEVANCE
        ),
        b2_fixture_classes=tuple(
            class_name
            for class_name in class_names
            if gate_layer_by_class[class_name] == TIER_B2_STRESS
        ),
        minimum_calibration_replicates_per_class=min_cal,
        minimum_heldout_replicates_per_class=min_heldout,
        fixture_lock_path=fixture_lock_path,
        fixture_lock_hash=fixture_lock_hash,
        required_hard_case_strata_by_class=hard_case_strata_by_class,
        gate_layer_by_class=gate_layer_by_class,
        truth_target_type_by_class=truth_target_type_by_class,
        stress_role_by_class=stress_role_by_class,
        allowed_decision_targets_by_class=allowed_targets_by_class,
        legacy_fixture_status=(
            LEGACY_FIXTURE_V1_NON_AUTHORITATIVE if is_legacy else LEGACY_FIXTURE_CURRENT
        ),
        fixture_scope_status=(
            "INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH" if is_legacy else "PASS"
        ),
    )


def load_fixture_lock(path: Path) -> FixtureLock:
    data = load_json_object(path)
    raw_records = _require_sequence(data, "records", path)
    expected_whole_hash = _require_text(data, "whole_lock_hash", path)
    actual_whole_hash = _canonical_digest({"records": raw_records})
    if expected_whole_hash != actual_whole_hash:
        raise ValueError(f"{path}: whole_lock_hash does not match records")
    lock_version = _require_text(data, "lock_version", path)
    is_legacy = lock_version != "asls_truth_fixture_lock_v2"
    records = tuple(
        _parse_fixture_lock_record(row, path, legacy=is_legacy) for row in raw_records
    )
    if not records:
        raise ValueError(f"{path}: records must not be empty")
    ids = [row.fixture_id for row in records]
    duplicates = [item for item, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"{path}: duplicate fixture_id values: {duplicates}")
    validate_fixture_lock_coverage(
        FixtureLock(
            lock_version=lock_version,
            whole_lock_hash=expected_whole_hash,
            review_freeze_status=str(data.get("review_freeze_status", "")),
            records=records,
        ),
        required_hard_case_strata_by_class=None,
        path=path,
    )
    return FixtureLock(
        lock_version=lock_version,
        whole_lock_hash=expected_whole_hash,
        review_freeze_status=str(data.get("review_freeze_status", "")),
        records=records,
    )


def validate_fixture_lock_coverage(
    lock: FixtureLock,
    *,
    required_hard_case_strata_by_class: Mapping[str, tuple[str, ...]] | None,
    path: Path,
) -> None:
    records = lock.records
    counts = Counter((row.fixture_class, row.split) for row in records)
    for class_name in REQUIRED_FIXTURE_CLASSES:
        class_heldout = [
            row
            for row in records
            if row.fixture_class == class_name and row.split == "heldout_gate"
        ]
        if counts[(class_name, "calibration")] < MIN_CALIBRATION_REPLICATES_PER_CLASS:
            raise ValueError(f"{path}: {class_name} has too few calibration rows")
        if counts[(class_name, "heldout_gate")] < MIN_HELDOUT_REPLICATES_PER_CLASS:
            raise ValueError(f"{path}: {class_name} has too few heldout rows")
        if class_name != "blank_noise_control":
            sn_strata = {row.sn_stratum for row in class_heldout}
            if not {"low", "medium", "high"}.issubset(sn_strata):
                raise ValueError(f"{path}: {class_name} missing heldout S/N strata")
            width_strata = {row.peak_width_stratum for row in class_heldout}
            if not {"narrow", "typical", "wide"}.issubset(width_strata):
                raise ValueError(
                    f"{path}: {class_name} missing heldout peak-width strata"
                )
            sn_width_combinations = {
                (row.sn_stratum, row.peak_width_stratum) for row in class_heldout
            }
            if len(sn_width_combinations) < REQUIRED_NONBLANK_SN_WIDTH_COMBINATIONS:
                raise ValueError(
                    f"{path}: {class_name} missing heldout S/N x peak-width coverage"
                )
        hard_counts = Counter(row.hard_case_stratum for row in class_heldout)
        expected_hard_cases = (
            required_hard_case_strata_by_class.get(class_name, ())
            if required_hard_case_strata_by_class is not None
            else tuple(hard_counts)
        )
        for hard_case in expected_hard_cases:
            if hard_case and hard_counts[hard_case] < 5:
                raise ValueError(
                    f"{path}: {class_name} hard-case stratum {hard_case!r} "
                    "has fewer than 5 heldout rows"
                )


def _parse_tier_a_family(row: Any, path: Path) -> TierAFamily:
    if not isinstance(row, Mapping):
        raise ValueError(f"{path}: expected_families entries must be objects")
    return TierAFamily(
        target_label=_require_text(row, "target_label", path),
        feature_family_id=_require_text(row, "feature_family_id", path),
        old_p2_status=_require_text(row, "old_p2_status", path),
        expected_row_count=_require_positive_int(row, "expected_row_count", path),
        expected_sample_count=_require_positive_int(row, "expected_sample_count", path),
        required_plot_path=_require_text(row, "required_plot_path", path),
    )


def _parse_fixture_lock_record(
    row: Any,
    path: Path,
    *,
    legacy: bool,
) -> FixtureLockRecord:
    if not isinstance(row, Mapping):
        raise ValueError(f"{path}: records entries must be objects")
    required_keys = (
        tuple(
            key
            for key in _REQUIRED_LOCK_RECORD_KEYS
            if key
            not in {
                "gate_layer",
                "stress_role",
                "production_like_bounds_status",
                "scan_density_stratum",
                "integration_point_count",
                "integration_width_min",
                "tier_a_width_quantile_band",
                "decision_scope",
                "truth_target_type",
                "required_for_b1_coverage",
                "fixture_scope_reason",
            }
        )
        if legacy
        else _REQUIRED_LOCK_RECORD_KEYS
    )
    for key in required_keys:
        if key not in row:
            raise ValueError(f"{path}: fixture lock record missing {key}")
    row_without_hash = dict(row)
    expected_row_hash = _require_text(row_without_hash, "generator_input_hash", path)
    row_without_hash.pop("generator_input_hash")
    if expected_row_hash != _canonical_digest(row_without_hash):
        raise ValueError(f"{path}: generator_input_hash does not match fixture row")
    bounds = _require_sequence(row, "expected_bound_indices", path)
    if len(bounds) != 2:
        raise ValueError(f"{path}: expected_bound_indices must have 2 values")
    fixture_class = _require_fixture_class(row, path)
    left = int(bounds[0])
    right = int(bounds[1])
    gate_layer = _optional_record_gate_layer(fixture_class, row, legacy, path)
    production_status = _optional_production_bounds_status(row, legacy, path)
    decision_scope = _optional_decision_scope(fixture_class, row, legacy, path)
    truth_target_type = _optional_record_truth_target_type(
        fixture_class, row, legacy, path
    )
    integration_point_count = int(
        row.get("integration_point_count", max(0, right - left + 1))
    )
    integration_width_min = float(
        row.get(
            "integration_width_min",
            max(0, right - left)
            * float(
                _require_mapping(row, "parameters", path).get(
                    "scan_spacing_min", 0.0
                )
            ),
        )
    )
    return FixtureLockRecord(
        fixture_id=_require_text(row, "fixture_id", path),
        fixture_class=fixture_class,
        split=_require_split(row, path),
        replicate_id=_require_positive_int(row, "replicate_id", path),
        sn_stratum=_require_text(row, "sn_stratum", path),
        peak_width_stratum=_require_text(row, "peak_width_stratum", path),
        hard_case_stratum=_require_text(row, "hard_case_stratum", path),
        parameters=_require_mapping(row, "parameters", path),
        true_area_formula_version=_require_text(
            row, "true_area_formula_version", path
        ),
        bounds_policy=_require_text(row, "bounds_policy", path),
        expected_bound_indices=(left, right),
        gate_layer=gate_layer,
        stress_role=str(row.get("stress_role", _default_stress_role(fixture_class))),
        production_like_bounds_status=production_status,
        scan_density_stratum=str(row.get("scan_density_stratum", "legacy_unknown")),
        integration_point_count=integration_point_count,
        integration_width_min=integration_width_min,
        tier_a_width_quantile_band=str(
            row.get("tier_a_width_quantile_band", "legacy_unknown")
        ),
        decision_scope=decision_scope,
        truth_target_type=truth_target_type,
        required_for_b1_coverage=bool(
            row.get("required_for_b1_coverage", gate_layer == TIER_B1_RELEVANCE)
        ),
        fixture_scope_reason=str(
            row.get(
                "fixture_scope_reason",
                "legacy_v1_default" if legacy else "fixture_scope_not_recorded",
            )
        ),
        generator_input_hash=_require_text(row, "generator_input_hash", path),
    )


def _optional_class_gate_layer(
    class_name: str,
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> str:
    value = (
        _default_gate_layer(class_name)
        if legacy
        else _require_text(row, "default_gate_layer", path)
    )
    if value not in _VALID_GATE_LAYERS:
        raise ValueError(
            f"{path}: {class_name} unsupported default_gate_layer {value!r}"
        )
    return value


def _optional_truth_target_type(
    class_name: str,
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> str:
    value = (
        _default_truth_target_type(class_name)
        if legacy
        else _require_text(row, "truth_target_type", path)
    )
    if value not in _VALID_TRUTH_TARGET_TYPES:
        raise ValueError(
            f"{path}: {class_name} unsupported truth_target_type {value!r}"
        )
    return value


def _optional_stress_role(
    class_name: str,
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> str:
    value = (
        _default_stress_role(class_name)
        if legacy
        else _require_text(row, "stress_role", path)
    )
    return value


def _optional_allowed_targets(
    class_name: str,
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> tuple[str, ...]:
    if legacy:
        if _default_gate_layer(class_name) == TIER_B1_RELEVANCE:
            return ("c1b-plan",)
        return ("linear-edge-retirement",)
    values = _require_sequence(row, "allowed_decision_targets", path)
    targets = tuple(str(value) for value in values)
    if not targets:
        raise ValueError(
            f"{path}: {class_name} allowed_decision_targets must not be empty"
        )
    return targets


def _optional_record_gate_layer(
    class_name: str,
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> str:
    value = (
        _default_gate_layer(class_name)
        if legacy
        else _require_text(row, "gate_layer", path)
    )
    if value not in _VALID_GATE_LAYERS:
        raise ValueError(f"{path}: unsupported gate_layer {value!r}")
    return value


def _optional_production_bounds_status(
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> str:
    value = (
        PRODUCTION_LIKE_OUT_OF_SCOPE_STRESS
        if legacy
        else _require_text(row, "production_like_bounds_status", path)
    )
    if value not in _VALID_PRODUCTION_BOUNDS_STATUSES:
        raise ValueError(f"{path}: unsupported production_like_bounds_status {value!r}")
    return value


def _optional_decision_scope(
    class_name: str,
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> str:
    value = (
        DECISION_SCOPE_C1B
        if legacy and _default_gate_layer(class_name) == TIER_B1_RELEVANCE
        else DECISION_SCOPE_RETIREMENT
        if legacy
        else _require_text(row, "decision_scope", path)
    )
    if value not in _VALID_DECISION_SCOPES:
        raise ValueError(f"{path}: unsupported decision_scope {value!r}")
    return value


def _optional_record_truth_target_type(
    class_name: str,
    row: Mapping[str, Any],
    legacy: bool,
    path: Path,
) -> str:
    value = (
        _default_truth_target_type(class_name)
        if legacy
        else _require_text(row, "truth_target_type", path)
    )
    if value not in _VALID_TRUTH_TARGET_TYPES:
        raise ValueError(f"{path}: unsupported truth_target_type {value!r}")
    return value


def _default_gate_layer(class_name: str) -> str:
    if class_name in B1_RELEVANCE_FIXTURE_CLASSES:
        return TIER_B1_RELEVANCE
    return TIER_B2_STRESS


def _default_truth_target_type(class_name: str) -> str:
    if class_name == "blank_noise_control":
        return "blank_zero_area"
    if class_name == "coeluting_interference":
        return "stress_not_truth"
    if class_name == "adjacent_shoulder":
        return "accepted_boundary_signal"
    return "baseline_corrected_peak_area"


def _default_stress_role(class_name: str) -> str:
    if class_name in B1_RELEVANCE_FIXTURE_CLASSES:
        return "b1_relevance"
    return {
        "blank_noise_control": "blank_carryover_safety",
        "coeluting_interference": "peak_purity_deconvolution_stress",
        "local_baseline_dip": "local_baseline_distortion_stress",
        "heteroscedastic_noise_peak": "noise_model_stress",
        "low_sn_peak": "low_sn_stress",
        "saturated_or_clipped_apex": "clipping_stress",
        "hump_baseline_peak": "hump_morphology_review",
    }.get(class_name, "stress")


def _validate_acceptance_ref(row: Any, path: Path) -> Mapping[str, Any]:
    if not isinstance(row, Mapping):
        raise ValueError(f"{path}: p2b_85raw_acceptance_refs entries must be objects")
    _require_text(row, "artifact", path)
    return _validate_hashed_ref(row, path, label="p2b_85raw_acceptance_refs")


def _validate_hashed_ref(
    row: Any,
    manifest_path: Path,
    *,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(row, Mapping):
        raise ValueError(f"{manifest_path}: {label} must be an object")
    ref = _require_text(row, "path", manifest_path)
    expected_sha = _require_text(row, "sha256", manifest_path)
    ref_path = _resolve_manifest_ref(manifest_path, ref)
    if not ref_path.exists():
        raise ValueError(f"{manifest_path}: {label} path does not exist: {ref}")
    actual_sha = _sha256_file(ref_path)
    if actual_sha != expected_sha:
        raise ValueError(
            f"{manifest_path}: {label} sha256 mismatch for {ref}: "
            f"expected {expected_sha}, got {actual_sha}"
        )
    return row


def _require_fixture_class(data: Mapping[str, Any], path: Path) -> str:
    value = _require_text(data, "fixture_class", path)
    if value not in REQUIRED_FIXTURE_CLASSES:
        raise ValueError(f"{path}: unsupported fixture_class {value!r}")
    return value


def _require_split(data: Mapping[str, Any], path: Path) -> str:
    value = _require_text(data, "split", path)
    if value not in {"calibration", "heldout_gate"}:
        raise ValueError(f"{path}: unsupported split {value!r}")
    return value


def _require_mapping(
    data: Mapping[str, Any], key: str, path: Path
) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: {key} must be an object")
    return value


def _require_sequence(data: Mapping[str, Any], key: str, path: Path) -> Sequence[Any]:
    value = data.get(key)
    if not isinstance(value, list | tuple):
        raise ValueError(f"{path}: {key} must be a list")
    return value


def _require_text(data: Mapping[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def _require_positive_int(data: Mapping[str, Any], key: str, path: Path) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{path}: {key} must be a positive integer")
    return value


def _require_float(data: Mapping[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{path}: {key} must be a number")
    return float(value)


def _resolve_manifest_ref(manifest_path: Path, ref: str) -> Path:
    candidate = Path(ref)
    if candidate.is_absolute():
        return candidate
    repo_relative = _repo_root_for(manifest_path) / candidate
    if repo_relative.exists():
        return repo_relative
    return manifest_path.parent / candidate


def _canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_root_for(path: Path) -> Path:
    current = path.resolve().parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "AGENTS.md").exists():
            return candidate
    return Path.cwd()
