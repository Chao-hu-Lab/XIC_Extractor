"""Input validators for the P2c AsLS truth-validation gate."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.diagnostics.asls_truth_validation_manifests import (
    FixtureManifest,
    REQUIRED_TIER_A_FAMILIES,
    TierAFamily,
    load_tier_a_manifest,
)
from tools.diagnostics.asls_truth_validation_models import (
    DECISION_SCOPE_C1B,
    DECISION_SCOPE_RETIREMENT,
    INCONCLUSIVE_FIXTURE_GAP,
    INCONCLUSIVE_INVALID_INPUT,
    INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE,
    INCONCLUSIVE_REGENERATE_TIER_A,
    PRODUCTION_LIKE_IN_SCOPE,
    TIER_B2_STRESS,
    load_json_object,
)


PASS = "PASS"
FAIL = "FAIL"
VALID = "VALID"
NOT_PROVIDED = "NOT_PROVIDED"
NOT_SATISFIED = "NOT_SATISFIED"
NOT_APPLICABLE_WITH_EXCLUSION = "NOT_APPLICABLE_WITH_EXCLUSION"

_TIER_A_ROW_COLUMNS = (
    "target_label",
    "feature_family_id",
    "sample_stem",
    "status",
    "raw_area",
    "linear_area",
    "asls_area",
    "linear_raw_pct",
    "asls_raw_pct",
    "asls_vs_linear_pct",
    "linear_baseline_subtracted_pct",
    "asls_baseline_subtracted_pct",
    "linear_edge_delta_pct",
    "outside_background_pct",
    "peak_start_rt",
    "apex_rt",
    "peak_end_rt",
    "trace_point_count",
    "classification",
    "review_reason",
    "plot_path",
    "rt_identity_status",
    "boundary_status",
)
_TIER_A_SUMMARY_COLUMNS = (
    "target_label",
    "feature_family_id",
    "row_count",
    "dominant_classification",
    "classification_counts",
    "median_linear_baseline_subtracted_pct",
    "median_asls_baseline_subtracted_pct",
    "median_asls_vs_linear_pct",
    "max_asls_vs_linear_pct",
    "median_linear_edge_delta_pct",
    "median_outside_background_pct",
    "review_status",
    "plot_path",
)
_TIER_A_SUMMARY_NUMERIC_COLUMNS = (
    "row_count",
    "median_linear_baseline_subtracted_pct",
    "median_asls_baseline_subtracted_pct",
    "median_asls_vs_linear_pct",
    "max_asls_vs_linear_pct",
    "median_linear_edge_delta_pct",
    "median_outside_background_pct",
)
_PATTERN_TO_FIXTURES = {
    "linear_edge_over_subtraction_plausible": (
        "sloped_baseline_peak",
        "tailing_peak",
        "adjacent_shoulder",
        "flat_peak_control",
    ),
    "methods_similar": ("flat_peak_control",),
    "low_outside_background_with_baseline_disagreement": (
        "flat_peak_control",
    ),
}
_SUPPORTED_TIER_C_AXES = {
    "spike_in_recovery",
    "linearity",
    "blank_carryover",
    "blinded_manual_integration",
    "real_85raw_cohort",
}
_APPROVED_WAIVER_OWNERS = {"methodology_owner"}
_WAIVER_REQUIRED_FIELDS = (
    "methodology_owner",
    "approved",
    "review_date",
    "review_artifact_path",
    "review_artifact_sha256",
    "blank_carryover_disposition",
    "accepted_residual_risks",
    "output_scope",
    "expiry_or_revalidation_trigger",
    "waived_decision",
    "waived_tier_c_axes",
    "waiver_rationale",
    "branch_scope",
    "target_classes",
    "sample_classes",
    "supporting_evidence",
    "delete_only_after_c1a_c5_rollback_deprecation",
)
_WAIVER_NON_EMPTY_LIST_FIELDS = (
    "accepted_residual_risks",
    "output_scope",
    "target_classes",
    "sample_classes",
    "supporting_evidence",
    "waived_tier_c_axes",
)
_VALIDATION_STATUS_VALUES = {"LANDED_VALIDATED", "PLANNED", "NOT_LANDED"}
_ROLLBACK_STATUS_VALUES = {
    "DEPRECATED_BY_APPROVED_SCHEMA_NOTE",
    "PLANNED",
    "NOT_DEPRECATED",
}
_LINEAR_EDGE_COLUMNS = {
    "area_baseline_corrected_linear_edge",
    "baseline_score_linear_edge",
}
_POST_ROLLBACK_AUDIT_SCHEMA_REQUIRED_COLUMNS = {
    "feature_family_id",
    "sample_stem",
    "status",
    "area",
    "apex_rt",
    "peak_start_rt",
    "peak_end_rt",
    "area_baseline_corrected",
    "area_uncertainty",
    "baseline_type",
    "baseline_score",
    "integration_scan_count",
}


@dataclass(frozen=True)
class TierAValidationResult:
    status: str
    reasons: tuple[str, ...]
    family_count: int
    row_count: int
    expected_families: tuple[TierAFamily, ...]
    coverage_rows: tuple["CoverageRow", ...]


@dataclass(frozen=True)
class CoverageRow:
    observed_pattern: str
    target_label: str
    feature_family_id: str
    observed_row_count: int
    required_b1_fixture_classes: tuple[str, ...]
    covered_b1_fixture_classes: tuple[str, ...]
    b2_stress_fixture_classes: tuple[str, ...]
    coverage_status: str
    fixture_scope_status: str
    unmapped_reason: str = ""


@dataclass(frozen=True)
class TierCValidationResult:
    status: str
    nonblank_status: str
    blank_safety_status: str
    axis: str
    reasons: tuple[str, ...]
    stress_axis_disposition_statuses: tuple[str, ...] = ()
    nonblank_decision_scope: str = DECISION_SCOPE_C1B


@dataclass(frozen=True)
class WaiverValidationResult:
    status: str
    waiver_state: str
    nonblank_tier_c_status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RetirementPrerequisiteValidationResult:
    status: str
    satisfied: bool
    reasons: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_tier_a(
    *,
    rows_path: Path,
    summary_path: Path,
    json_path: Path,
    report_path: Path,
    manifest_path: Path,
    fixture_manifest: FixtureManifest,
    verify_artifact_hashes: bool = True,
    require_p2b_85raw_acceptance: bool = True,
) -> TierAValidationResult:
    try:
        manifest = load_tier_a_manifest(manifest_path)
    except ValueError as exc:
        message = str(exc)
        if (
            require_p2b_85raw_acceptance
            and "p2b_85raw_acceptance_refs" in message
        ):
            return _tier_a_result(INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE, (message,))
        return _tier_a_result(
            INCONCLUSIVE_REGENERATE_TIER_A,
            ("tier_a_manifest_freshness", message),
        )
    if require_p2b_85raw_acceptance and not manifest.p2b_85raw_acceptance_refs:
        return _tier_a_result(INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE, ())
    if (
        manifest.generated_by_git_sha != _current_git_sha(manifest_path)
        and manifest.current_code_compatibility_status
        != "accepted_current_worktree_artifact_hashes"
    ):
        return _tier_a_result(
            INCONCLUSIVE_REGENERATE_TIER_A,
            ("current_code_compatibility",),
            expected_families=manifest.families,
        )
    try:
        rows = _read_tsv_required(rows_path, _TIER_A_ROW_COLUMNS)
        summary_rows = _read_tsv_required(summary_path, _TIER_A_SUMMARY_COLUMNS)
        _json_payload = load_json_object(json_path)
        if not report_path.exists():
            raise OSError(f"report does not exist: {report_path}")
    except OSError as exc:
        return _tier_a_result(
            INCONCLUSIVE_INVALID_INPUT,
            ("unreadable_tier_a_artifact", str(exc)),
            expected_families=manifest.families,
        )
    except ValueError as exc:
        return _tier_a_result(
            INCONCLUSIVE_INVALID_INPUT,
            (str(exc),),
            expected_families=manifest.families,
        )
    if verify_artifact_hashes:
        mismatch = _artifact_hash_mismatch(
            {
                "rows": rows_path,
                "summary": summary_path,
                "json": json_path,
                "report": report_path,
            },
            manifest.artifact_hashes,
        )
        if mismatch:
            return _tier_a_result(
                INCONCLUSIVE_REGENERATE_TIER_A,
                ("artifact_hash_mismatch", mismatch),
                expected_families=manifest.families,
            )
    try:
        asls_raw_pct_values = [_required_float(row, "asls_raw_pct") for row in rows]
        _validate_summary_numeric_fields(summary_rows)
        coverage_rows = build_coverage_rows(summary_rows, fixture_manifest)
    except ValueError as exc:
        return _tier_a_result(
            INCONCLUSIVE_INVALID_INPUT,
            (str(exc),),
            expected_families=manifest.families,
        )
    reasons: list[str] = []
    family_keys = {
        (row["target_label"], row["feature_family_id"]) for row in summary_rows
    }
    missing = REQUIRED_TIER_A_FAMILIES - family_keys
    if missing:
        reasons.append("missing_expected_family")
    if len(rows) != 48:
        reasons.append("wrong_tier_a_row_count")
    if len(summary_rows) != 6:
        reasons.append("wrong_tier_a_family_count")
    old_statuses = {row.old_p2_status for row in manifest.families}
    if old_statuses != {"PASS", "FAIL"}:
        reasons.append("missing_old_p2_status_representation")
    if any(value > 100.0 for value in asls_raw_pct_values):
        reasons.append("asls_raw_pct_gt_100")
    if any(
        row.get("dominant_classification") == "asls_under_subtraction_plausible"
        for row in summary_rows
    ):
        reasons.append("asls_under_subtraction_dominant")
    if _missing_plot(summary_path, summary_rows):
        reasons.append("missing_required_plot_path")
    if any(row["rt_identity_status"] != "PASS" for row in rows):
        reasons.append("rt_identity_status_fail")
    if any(
        row["boundary_status"] not in {"PASS", "accepted", "reviewed"}
        for row in rows
    ):
        reasons.append("boundary_status_fail")
    if any(row.coverage_status == INCONCLUSIVE_FIXTURE_GAP for row in coverage_rows):
        reasons.append("fixture_coverage_gap")
    status = FAIL if reasons else PASS
    return TierAValidationResult(
        status=status,
        reasons=tuple(reasons),
        family_count=len(family_keys),
        row_count=len(rows),
        expected_families=manifest.families,
        coverage_rows=tuple(coverage_rows),
    )


def build_coverage_rows(
    tier_a_summary_rows: list[dict[str, str]],
    fixture_manifest: FixtureManifest,
) -> tuple[CoverageRow, ...]:
    b1_fixture_classes = set(fixture_manifest.b1_fixture_classes)
    b2_fixture_classes = tuple(fixture_manifest.b2_fixture_classes)
    rows: list[CoverageRow] = []
    for row in tier_a_summary_rows:
        pattern = row.get("dominant_classification", "")
        required = _PATTERN_TO_FIXTURES.get(pattern)
        if required is None:
            rows.append(
                CoverageRow(
                    observed_pattern=pattern,
                    target_label=row.get("target_label", ""),
                    feature_family_id=row.get("feature_family_id", ""),
                    observed_row_count=int(_required_float(row, "row_count")),
                    required_b1_fixture_classes=(),
                    covered_b1_fixture_classes=(),
                    b2_stress_fixture_classes=b2_fixture_classes,
                    coverage_status=INCONCLUSIVE_FIXTURE_GAP,
                    fixture_scope_status=fixture_manifest.fixture_scope_status,
                    unmapped_reason="unmapped_observed_pattern",
                )
            )
            continue
        covered = tuple(item for item in required if item in b1_fixture_classes)
        status = PASS if len(covered) == len(required) else INCONCLUSIVE_FIXTURE_GAP
        rows.append(
            CoverageRow(
                observed_pattern=pattern,
                target_label=row.get("target_label", ""),
                feature_family_id=row.get("feature_family_id", ""),
                observed_row_count=int(_required_float(row, "row_count")),
                required_b1_fixture_classes=tuple(required),
                covered_b1_fixture_classes=covered,
                b2_stress_fixture_classes=b2_fixture_classes,
                coverage_status=status,
                fixture_scope_status=fixture_manifest.fixture_scope_status,
            )
        )
    return tuple(rows)


def validate_tier_c(path: Path | None) -> TierCValidationResult:
    if path is None:
        return TierCValidationResult(NOT_PROVIDED, NOT_PROVIDED, NOT_PROVIDED, "", ())
    try:
        data = load_json_object(path)
        axis = _text(data, "tier_c_axis")
        if axis not in _SUPPORTED_TIER_C_AXES:
            raise ValueError(f"unsupported tier_c_axis {axis!r}")
        status = _text(data, "tier_c_status")
        if status not in {PASS, FAIL, NOT_PROVIDED, "MIXED"}:
            raise ValueError("tier_c_status must be PASS, FAIL, MIXED, or NOT_PROVIDED")
        if status == NOT_PROVIDED:
            return TierCValidationResult(NOT_PROVIDED, NOT_PROVIDED, NOT_PROVIDED, axis, ())
        _validate_tier_c_metadata(data, base_path=path)
        explicit_nonblank = str(data.get("tier_c_nonblank_status", "")).strip()
        explicit_blank = str(data.get("blank_safety_status", "")).strip()
        nonblank = explicit_nonblank or NOT_PROVIDED
        blank = explicit_blank or NOT_PROVIDED
        if nonblank not in {PASS, FAIL, NOT_PROVIDED}:
            raise ValueError("tier_c_nonblank_status must be PASS, FAIL, or NOT_PROVIDED")
        if blank not in {
            PASS,
            FAIL,
            NOT_PROVIDED,
            NOT_APPLICABLE_WITH_EXCLUSION,
        }:
            raise ValueError(
                "blank_safety_status must be PASS, FAIL, NOT_PROVIDED, "
                "or NOT_APPLICABLE_WITH_EXCLUSION"
            )
        stress_statuses = _validate_stress_axis_dispositions(data, base_path=path)
        nonblank_scope = str(data.get("nonblank_decision_scope", DECISION_SCOPE_C1B))
        if nonblank_scope not in {DECISION_SCOPE_C1B, DECISION_SCOPE_RETIREMENT}:
            raise ValueError("unsupported nonblank_decision_scope")
        if status == FAIL and nonblank == NOT_PROVIDED and blank == NOT_PROVIDED:
            nonblank = FAIL
        if axis == "spike_in_recovery":
            _require_min(data, "level_count", 3)
            _require_min(data, "replicates_per_level", 5)
            recovery = _number(data, "median_recovery_pct")
            if not 80.0 <= recovery <= 120.0:
                raise ValueError("median_recovery_pct out of range")
            if explicit_nonblank != FAIL:
                nonblank = PASS
        elif axis == "linearity":
            _require_min(data, "level_count", 5)
            _require_min(data, "replicates_per_level", 3)
            if _number(data, "slope") <= 0:
                raise ValueError("slope must be positive")
            if _number(data, "r2") < 0.98:
                raise ValueError("r2 must be >= 0.98")
            if explicit_nonblank != FAIL:
                nonblank = PASS
        elif axis == "blank_carryover":
            if explicit_blank != FAIL:
                blank = _validate_blank_safety(data, base_path=path)
        elif axis == "blinded_manual_integration":
            _require_min(data, "stratified_row_count", 30)
            if _number(data, "median_relative_difference_pct") > 10.0:
                raise ValueError("median_relative_difference_pct > 10")
            if _number(data, "unreviewed_above_25pct_count") > 0:
                raise ValueError("unreviewed_above_25pct_count > 0")
            if explicit_nonblank != FAIL:
                nonblank = PASS
        elif axis == "real_85raw_cohort":
            _require_min(data, "raw_file_count", 85)
            _require_min(data, "sample_count", 1)
            _require_min(data, "selected_istd_count", 1)
            _require_min(data, "high_risk_morphology_row_count", 1)
            _require_min(data, "blank_control_row_count", 1)
            if not data.get("covered_target_classes"):
                raise ValueError("covered_target_classes required")
            if _number(data, "unaccepted_rt_boundary_mismatch_count") > 0:
                raise ValueError("unaccepted_rt_boundary_mismatch_count > 0")
            if _number(data, "asls_raw_area_exceedance_count") > 0:
                raise ValueError("asls_raw_area_exceedance_count > 0")
            _text(data, "quantitative_truth_comparator_type")
            if _number(data, "max_unreviewed_relative_difference_pct") > 25.0:
                raise ValueError("max_unreviewed_relative_difference_pct > 25")
            if _number(data, "median_nonblank_drift_pct") > 10.0:
                raise ValueError("median_nonblank_drift_pct > 10")
            if explicit_nonblank != FAIL:
                nonblank = PASS
    except (OSError, ValueError) as exc:
        return TierCValidationResult(
            INCONCLUSIVE_INVALID_INPUT,
            NOT_PROVIDED,
            NOT_PROVIDED,
            "",
            (str(exc),),
        )
    aggregate_status = FAIL if FAIL in {nonblank, blank} else status
    return TierCValidationResult(
        aggregate_status,
        nonblank,
        blank,
        axis,
        (),
        stress_axis_disposition_statuses=stress_statuses,
        nonblank_decision_scope=nonblank_scope,
    )


def validate_waiver(path: Path | None) -> WaiverValidationResult:
    if path is None:
        return WaiverValidationResult(NOT_PROVIDED, NOT_PROVIDED, NOT_PROVIDED, ())
    try:
        data = load_json_object(path)
        for key in _WAIVER_REQUIRED_FIELDS:
            if key not in data:
                raise ValueError(f"missing waiver field {key}")
        if _text(data, "methodology_owner") not in _APPROVED_WAIVER_OWNERS:
            raise ValueError("unsupported methodology_owner")
        review_date = _parse_iso_date(_text(data, "review_date"), "review_date")
        expiry_date = _parse_iso_date(
            _text(data, "expiry_or_revalidation_trigger"),
            "expiry_or_revalidation_trigger",
        )
        if expiry_date <= review_date:
            raise ValueError("expiry_or_revalidation_trigger must be after review_date")
        if expiry_date < _current_date():
            raise ValueError("waiver has expired")
        for key in _WAIVER_NON_EMPTY_LIST_FIELDS:
            _require_non_empty_list(data, key)
        for key in (
            "blank_carryover_disposition",
            "waiver_rationale",
            "branch_scope",
        ):
            _text(data, key)
        if data["approved"] is not True:
            raise ValueError("waiver must be approved")
        _validate_hashed_ref_object(
            data,
            "review_artifact_path",
            "review_artifact_sha256",
            base_path=path,
        )
        waived_axes = set(_require_non_empty_list(data, "waived_tier_c_axes"))
        unsupported_axes = waived_axes - _SUPPORTED_TIER_C_AXES
        if unsupported_axes:
            raise ValueError(f"unsupported waived_tier_c_axes {sorted(unsupported_axes)!r}")
        for ref in _require_non_empty_list(data, "supporting_evidence"):
            _validate_ref(ref, base_path=path)
        if data["delete_only_after_c1a_c5_rollback_deprecation"] is not True:
            raise ValueError("missing deletion prerequisite statement")
        if data["waived_decision"] not in {"c1b-plan", "linear-edge-retirement"}:
            raise ValueError("unsupported waived_decision")
    except (OSError, TypeError, ValueError) as exc:
        return WaiverValidationResult(
            INCONCLUSIVE_INVALID_INPUT,
            INCONCLUSIVE_INVALID_INPUT,
            NOT_PROVIDED,
            (str(exc),),
        )
    return WaiverValidationResult(PASS, VALID, NOT_PROVIDED, ())


def validate_retirement_prerequisites(
    path: Path | None,
) -> RetirementPrerequisiteValidationResult:
    if path is None:
        return RetirementPrerequisiteValidationResult(NOT_PROVIDED, False, ())
    try:
        data = load_json_object(path)
        c1a_status = _text(data, "c1a_status")
        c5_status = _text(data, "c5_status")
        rollback_status = _text(data, "rollback_column_status")
        if c1a_status not in _VALIDATION_STATUS_VALUES:
            raise ValueError(f"unsupported c1a_status {c1a_status!r}")
        if c5_status not in _VALIDATION_STATUS_VALUES:
            raise ValueError(f"unsupported c5_status {c5_status!r}")
        if rollback_status not in _ROLLBACK_STATUS_VALUES:
            raise ValueError(f"unsupported rollback_column_status {rollback_status!r}")
        for key in (
            "c1a_validation_note",
            "c5_validation_note",
            "rollback_schema_deprecation_note",
        ):
            _validate_ref(data[key], base_path=path)
        schema_ref = data["post_rollback_audit_schema_artifact"]
        schema_path = _validate_ref(schema_ref, base_path=path)
        artifact_columns = _read_artifact_columns(schema_path)
        if _LINEAR_EDGE_COLUMNS & set(artifact_columns):
            raise ValueError("post rollback artifact still contains linear-edge columns")
        missing_required_columns = (
            _POST_ROLLBACK_AUDIT_SCHEMA_REQUIRED_COLUMNS - set(artifact_columns)
        )
        if missing_required_columns:
            raise ValueError("post rollback artifact is not an accepted audit schema")
        for key in (
            "affected_public_contracts_reviewed",
        ):
            _require_non_empty_list(data, key)
        _text(data, "reviewer_identity")
        _parse_iso_date(_text(data, "review_date"), "review_date")
        absent = set(_require_string_list(data, "post_rollback_absent_columns"))
        if not _LINEAR_EDGE_COLUMNS.issubset(absent):
            raise ValueError("post rollback schema does not prove linear-edge columns absent")
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return RetirementPrerequisiteValidationResult(
            INCONCLUSIVE_INVALID_INPUT,
            False,
            (str(exc),),
        )
    satisfied = (
        c1a_status == "LANDED_VALIDATED"
        and c5_status == "LANDED_VALIDATED"
        and rollback_status == "DEPRECATED_BY_APPROVED_SCHEMA_NOTE"
    )
    return RetirementPrerequisiteValidationResult(
        VALID if satisfied else NOT_SATISFIED,
        satisfied,
        (),
    )


def _tier_a_result(
    status: str,
    reasons: tuple[str, ...],
    *,
    expected_families: tuple[TierAFamily, ...] = (),
) -> TierAValidationResult:
    return TierAValidationResult(status, reasons, 0, 0, expected_families, ())


def _artifact_hash_mismatch(
    paths_by_key: dict[str, Path],
    artifact_hashes: Any,
) -> str:
    for key, path in paths_by_key.items():
        expected = artifact_hashes[key]["sha256"]
        if sha256_file(path) != expected:
            return key
    return ""


def _read_tsv_required(
    path: Path,
    columns: tuple[str, ...],
) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError("missing_required_column")
        missing = set(columns) - set(reader.fieldnames)
        if missing:
            raise ValueError("missing_required_column")
        unexpected = set(reader.fieldnames) - set(columns)
        if unexpected:
            raise ValueError("unexpected_column")
        if tuple(reader.fieldnames) != columns:
            raise ValueError("schema_order_mismatch")
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError("unexpected_column")
        if any(value is None for row in rows for value in row.values()):
            raise ValueError("missing_required_column")
        return rows


def _missing_plot(summary_path: Path, rows: list[dict[str, str]]) -> bool:
    base_dir = summary_path.parent
    return any(not (base_dir / row.get("plot_path", "")).exists() for row in rows)


def _current_git_sha(repo_hint: Path | None = None) -> str:
    repo_root = _find_repo_root(repo_hint) if repo_hint is not None else Path.cwd()
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    git_dir = repo_root / ".git"
    if git_dir.is_file():
        pointer = git_dir.read_text(encoding="utf-8").strip()
        if pointer.startswith("gitdir: "):
            raw_git_dir = Path(pointer[8:].strip())
            git_dir = raw_git_dir if raw_git_dir.is_absolute() else repo_root / raw_git_dir
            git_dir = git_dir.resolve()
    git_head = git_dir / "HEAD"
    if not git_head.exists():
        return ""
    head = git_head.read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref_name = head[5:]
        ref_candidates = [git_dir / ref_name]
        commondir_path = git_dir / "commondir"
        if commondir_path.exists():
            raw_commondir = Path(commondir_path.read_text(encoding="utf-8").strip())
            common_dir = (
                raw_commondir
                if raw_commondir.is_absolute()
                else (git_dir / raw_commondir).resolve()
            )
            ref_candidates.append(common_dir / ref_name)
        for ref_path in ref_candidates:
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()
    return head


def _find_repo_root(path: Path | None) -> Path:
    start = (path if path is not None else Path.cwd()).resolve()
    current = start.parent if start.is_file() else start
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def _validate_tier_c_metadata(data: dict[str, Any], *, base_path: Path) -> None:
    for key in ("thresholds_used", "output_scope", "target_classes"):
        _require_non_empty_list(data, key)
    _text(data, "reviewer_or_generator")
    exclusions = data.get("known_exclusions")
    if not isinstance(exclusions, list):
        raise ValueError("known_exclusions must be a list")
    for ref in _require_non_empty_list(data, "evidence_artifacts"):
        _validate_ref(ref, base_path=base_path)


def _validate_blank_safety(data: dict[str, Any], *, base_path: Path) -> str:
    exclusion = data.get("blank_exclusion_contract")
    if isinstance(exclusion, dict):
        _require_non_empty_list(exclusion, "affected_outputs")
        for ref in _require_non_empty_list(exclusion, "evidence_artifacts"):
            _validate_ref(ref, base_path=base_path)
        if exclusion.get("approved") is True:
            return NOT_APPLICABLE_WITH_EXCLUSION
    _require_min(data, "blank_control_row_count", 8)
    if _number(data, "blank_below_threshold_pct") < 95.0:
        raise ValueError("blank_below_threshold_pct must be >= 95")
    return PASS


def _validate_stress_axis_dispositions(
    data: dict[str, Any],
    *,
    base_path: Path,
) -> tuple[str, ...]:
    dispositions = data.get("stress_axis_dispositions", [])
    if not isinstance(dispositions, list):
        raise ValueError("stress_axis_dispositions must be a list")
    statuses: list[str] = []
    for disposition in dispositions:
        if not isinstance(disposition, dict):
            raise ValueError("stress_axis_dispositions entries must be objects")
        _text(disposition, "stress_axis")
        status = _text(disposition, "status")
        if status not in {PASS, FAIL, "NOT_REQUIRED", NOT_PROVIDED}:
            raise ValueError("unsupported stress_axis disposition status")
        scope = _text(disposition, "decision_scope")
        if scope not in {DECISION_SCOPE_C1B, DECISION_SCOPE_RETIREMENT}:
            raise ValueError("unsupported stress_axis decision_scope")
        if status == "NOT_REQUIRED":
            _text(disposition, "rationale")
        for ref in disposition.get("evidence_artifacts", []):
            _validate_ref(ref, base_path=base_path)
        statuses.append(f"{disposition['stress_axis']}={status}")
    return tuple(statuses)


def _validate_hashed_ref_object(
    data: dict[str, Any],
    path_key: str,
    sha_key: str,
    *,
    base_path: Path,
) -> Path:
    return _validate_ref(
        {"path": data[path_key], "sha256": data[sha_key]},
        base_path=base_path,
    )


def _validate_ref(ref: Any, *, base_path: Path) -> Path:
    if not isinstance(ref, dict):
        raise ValueError("hashed reference must be an object")
    path = _resolve_ref_path(str(ref.get("path", "")), base_path)
    expected = str(ref.get("sha256", ""))
    if not path.exists():
        raise ValueError(f"hashed reference path does not exist: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"hash mismatch for {path}")
    return path


def _resolve_ref_path(raw_path: str, base_path: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    repo_root = _find_repo_root(base_path)
    candidates = (
        repo_root / path,
        base_path.resolve().parent / path,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return repo_root / path


def _read_artifact_columns(path: Path) -> tuple[str, ...]:
    if path.suffix.lower() not in {".tsv", ".csv"}:
        raise ValueError("post rollback schema artifact must be TSV or CSV")
    with path.open(encoding="utf-8", newline="") as handle:
        header = handle.readline().strip()
    if not header:
        raise ValueError("post rollback artifact has no header")
    delimiter = "\t" if "\t" in header else ","
    columns = tuple(part.strip() for part in header.split(delimiter) if part.strip())
    if len(columns) < 2:
        raise ValueError("post rollback schema artifact must have tabular columns")
    return columns


def _require_non_empty_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{key} must be a non-empty list")
    return value


def _require_string_list(data: dict[str, Any], key: str) -> list[str]:
    value = _require_non_empty_list(data, key)
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{key} must be a list of non-empty strings")
    return value


def _parse_iso_date(value: str, key: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an ISO date") from exc


def _current_date() -> dt.date:
    return dt.date.today()


def _validate_summary_numeric_fields(rows: list[dict[str, str]]) -> None:
    for row in rows:
        for key in _TIER_A_SUMMARY_NUMERIC_COLUMNS:
            _required_float(row, key)


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _require_min(data: dict[str, Any], key: str, minimum: int) -> None:
    if _number(data, key) < minimum:
        raise ValueError(f"{key} must be >= {minimum}")


def _number(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _required_float(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_numeric_field") from exc


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
