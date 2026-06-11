from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from xic_extractor.tabular_io import (
    read_tsv_required,
    text_value,
    write_tsv,
)

CONTRACT_SCHEMA_VERSION = "shared_peak_identity_mode_window_assignment_contract_v0"
GATE_ROW_SCHEMA_VERSION = "shared_peak_identity_mode_window_assignment_gate_v0"
GATE_SUMMARY_SCHEMA_VERSION = "shared_peak_identity_mode_window_assignment_summary_v0"

CONTRACT_FIXTURE_COLUMNS = (
    "contract_schema_version",
    "sentinel_id",
    "feature_family_id",
    "sample_id",
    "sentinel_case_type",
    "expected_peak_hypothesis_id",
    "expected_product_unit_scope",
    "expected_selected_mode_id",
    "expected_peak_hypothesis_status",
    "expected_product_selection_action",
    "expected_activation_unit_scope",
    "expected_activation_boundary",
    "expected_canonical_identity_effect",
    "required_evidence_oracle",
    "expectation_reason",
)

GATE_ROW_COLUMNS = (
    "mode_window_assignment_gate_schema_version",
    "sentinel_id",
    "feature_family_id",
    "sample_id",
    "sentinel_case_type",
    "expected_peak_hypothesis_id",
    "observed_peak_hypothesis_id",
    "expected_product_unit_scope",
    "observed_product_unit_scope",
    "expected_selected_mode_id",
    "observed_selected_mode_id",
    "expected_peak_hypothesis_status",
    "observed_peak_hypothesis_status",
    "expected_product_selection_action",
    "observed_product_selection_action",
    "observed_activation_peak_hypothesis_id",
    "expected_activation_unit_scope",
    "observed_activation_unit_scope",
    "expected_activation_boundary",
    "observed_activation_status",
    "observed_contract_rule_id",
    "expected_canonical_identity_effect",
    "observed_canonical_row_identity_ready",
    "observed_canonical_row_identity_blockers",
    "required_evidence_oracle",
    "gate_status",
    "failure_reason",
    "diagnostic_only",
)

GATE_SUMMARY_COLUMNS = (
    "mode_window_assignment_summary_schema_version",
    "scope",
    "fixture_rows",
    "pass_count",
    "fail_count",
    "not_assessed_count",
    "mode_window_assignment_gate_status",
    "dominant_failures",
    "canonical_row_identity_ready",
    "canonical_row_identity_blockers",
    "next_action",
    "diagnostic_only",
)

_SELECTION_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "peak_hypothesis_id",
    "peak_hypothesis_status",
    "product_unit_scope",
    "selected_mode_id",
    "product_selection_action",
    "product_selection_blocker",
    "reason",
)
_ACTIVATION_COLUMNS = (
    "feature_family_id",
    "sample_id",
    "peak_hypothesis_id",
    "activation_unit_scope",
    "activation_status",
    "contract_rule_id",
)
_MATRIX_SUMMARY_COLUMNS = (
    "canonical_row_identity_ready",
    "canonical_row_identity_blockers",
    "family_projection_rows",
)
_QC_REFERENCE_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "qc_reference_policy",
    "qc_consensus_status",
)
_RT_DRIFT_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "matrix_rt_drift_status",
    "drift_evidence_level",
)
_MS1_PATTERN_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "ms1_pattern_status",
)
_CANDIDATE_MS2_PATTERN_COLUMNS = (
    "feature_family_id",
    "sample_stem",
    "candidate_ms2_pattern_status",
    "candidate_ms2_evidence_level",
)


def load_contract_fixture(path: Path) -> tuple[dict[str, str], ...]:
    rows = read_tsv_required(path, CONTRACT_FIXTURE_COLUMNS)
    if not rows:
        raise ValueError("mode-window assignment contract fixture has no rows")
    for row in rows:
        schema = row.get("contract_schema_version")
        if schema != CONTRACT_SCHEMA_VERSION:
            raise ValueError(
                "unsupported mode-window assignment contract schema version: "
                f"{schema!r}"
            )
    return rows


def load_peak_hypothesis_selection(path: Path) -> tuple[dict[str, str], ...]:
    return read_tsv_required(path, _SELECTION_COLUMNS)


def load_activation_decisions(path: Path | None) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(path, _ACTIVATION_COLUMNS)


def load_matrix_summary(path: Path | None) -> Mapping[str, str]:
    if path is None:
        return {}
    rows = read_tsv_required(path, _MATRIX_SUMMARY_COLUMNS)
    if len(rows) != 1:
        raise ValueError("peak_hypothesis_matrix_summary.tsv must contain one row")
    return rows[0]


def load_qc_reference_rows(path: Path | None) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(path, _QC_REFERENCE_COLUMNS)


def load_rt_drift_rows(path: Path | None) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(path, _RT_DRIFT_COLUMNS)


def load_ms1_pattern_rows(path: Path | None) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(path, _MS1_PATTERN_COLUMNS)


def load_candidate_ms2_pattern_rows(path: Path | None) -> tuple[dict[str, str], ...]:
    if path is None:
        return ()
    return read_tsv_required(path, _CANDIDATE_MS2_PATTERN_COLUMNS)


def build_gate_rows(
    *,
    fixture_rows: Sequence[Mapping[str, str]],
    selection_rows: Sequence[Mapping[str, str]],
    activation_rows: Sequence[Mapping[str, str]] = (),
    matrix_summary: Mapping[str, str] | None = None,
    qc_reference_rows: Sequence[Mapping[str, str]] = (),
    rt_drift_rows: Sequence[Mapping[str, str]] = (),
    ms1_pattern_rows: Sequence[Mapping[str, str]] = (),
    candidate_ms2_pattern_rows: Sequence[Mapping[str, str]] = (),
) -> tuple[dict[str, str], ...]:
    selection_by_key = _rows_by_key(selection_rows, sample_field="sample_stem")
    activation_by_key = _rows_by_key(activation_rows, sample_field="sample_id")
    qc_by_key = _rows_by_key(qc_reference_rows, sample_field="sample_stem")
    rt_drift_by_key = _rows_by_key(rt_drift_rows, sample_field="sample_stem")
    ms1_by_key = _rows_by_key(ms1_pattern_rows, sample_field="sample_stem")
    candidate_ms2_by_key = _rows_by_key(
        candidate_ms2_pattern_rows,
        sample_field="sample_stem",
    )
    summary = matrix_summary or {}
    return tuple(
        _evaluate_fixture_row(
            fixture=row,
            selection=selection_by_key.get(
                (row["feature_family_id"], row["sample_id"])
            ),
            activation=activation_by_key.get(
                (row["feature_family_id"], row["sample_id"])
            ),
            matrix_summary=summary,
            qc_reference_rows=qc_reference_rows,
            rt_drift_rows=rt_drift_rows,
            qc_reference=qc_by_key.get((row["feature_family_id"], row["sample_id"])),
            rt_drift=rt_drift_by_key.get((row["feature_family_id"], row["sample_id"])),
            ms1_pattern=ms1_by_key.get((row["feature_family_id"], row["sample_id"])),
            candidate_ms2_pattern=candidate_ms2_by_key.get(
                (row["feature_family_id"], row["sample_id"])
            ),
        )
        for row in fixture_rows
    )


def build_gate_summary(rows: Sequence[Mapping[str, str]]) -> dict[str, str]:
    counts = Counter(row.get("gate_status", "") for row in rows)
    failures = Counter(
        reason
        for row in rows
        for reason in _split_reasons(row.get("failure_reason", ""))
    )
    gate_status = "pass"
    next_action = "mode_window_assignment_contract_gate_passed"
    if counts["fail"]:
        gate_status = "fail"
        next_action = "fix_mode_window_assignment_contract_failures"
    elif counts["not_assessed"]:
        gate_status = "inconclusive"
        next_action = "provide_missing_policy_or_activation_artifacts"
    canonical_ready = _first_non_empty(rows, "observed_canonical_row_identity_ready")
    canonical_blockers = _first_non_empty(
        rows,
        "observed_canonical_row_identity_blockers",
    )
    if gate_status == "pass" and (
        canonical_ready == "FALSE" or canonical_blockers not in {"", "none"}
    ):
        next_action = (
            "mode_window_assignment_contract_gate_passed_"
            "keep_product_activation_blocked_until_matrix_construction"
        )
    return {
        "mode_window_assignment_summary_schema_version": GATE_SUMMARY_SCHEMA_VERSION,
        "scope": "sentinel_mode_window_assignment_contract_v0",
        "fixture_rows": str(len(rows)),
        "pass_count": str(counts["pass"]),
        "fail_count": str(counts["fail"]),
        "not_assessed_count": str(counts["not_assessed"]),
        "mode_window_assignment_gate_status": gate_status,
        "dominant_failures": ";".join(
            reason for reason, _count in failures.most_common(5)
        ),
        "canonical_row_identity_ready": canonical_ready,
        "canonical_row_identity_blockers": canonical_blockers,
        "next_action": next_action,
        "diagnostic_only": "TRUE",
    }


def write_gate_outputs(
    *,
    output_dir: Path,
    rows: Sequence[Mapping[str, str]],
    summary: Mapping[str, str],
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "shared_peak_identity_mode_window_assignment_gate.tsv"
    summary_path = (
        output_dir / "shared_peak_identity_mode_window_assignment_summary.tsv"
    )
    write_tsv(rows_path, rows, GATE_ROW_COLUMNS, lineterminator="\n")
    write_tsv(summary_path, [summary], GATE_SUMMARY_COLUMNS, lineterminator="\n")
    return rows_path, summary_path


def _evaluate_fixture_row(
    *,
    fixture: Mapping[str, str],
    selection: Mapping[str, str] | None,
    activation: Mapping[str, str] | None,
    matrix_summary: Mapping[str, str],
    qc_reference_rows: Sequence[Mapping[str, str]],
    rt_drift_rows: Sequence[Mapping[str, str]],
    qc_reference: Mapping[str, str] | None,
    rt_drift: Mapping[str, str] | None,
    ms1_pattern: Mapping[str, str] | None,
    candidate_ms2_pattern: Mapping[str, str] | None,
) -> dict[str, str]:
    failures: list[str] = []
    sentinel_type = fixture["sentinel_case_type"]
    expected_status = fixture["expected_peak_hypothesis_status"]
    expected_action = fixture["expected_product_selection_action"]
    observed_status = text_value((selection or {}).get("peak_hypothesis_status"))
    observed_action = text_value((selection or {}).get("product_selection_action"))
    observed_hypothesis_id = text_value((selection or {}).get("peak_hypothesis_id"))
    observed_unit_scope = text_value((selection or {}).get("product_unit_scope"))
    observed_mode_id = text_value((selection or {}).get("selected_mode_id"))
    if fixture["feature_family_id"].startswith("__"):
        failures.extend(
            _policy_failures(
                sentinel_type=sentinel_type,
                qc_reference_rows=qc_reference_rows,
                rt_drift_rows=rt_drift_rows,
            )
        )
        observed_status = "not_applicable"
        observed_action = "no_product_action"
    else:
        if selection is None:
            failures.append("missing_peak_hypothesis_selection")
        else:
            failures.extend(_selection_identity_failures(fixture, selection))
            if not _status_matches(
                expected_status=expected_status,
                observed_status=observed_status,
                sentinel_type=sentinel_type,
            ):
                failures.append("peak_hypothesis_status_mismatch")
            if not _action_matches(
                expected_action=expected_action,
                observed_action=observed_action,
                sentinel_type=sentinel_type,
            ):
                failures.append("product_selection_action_mismatch")
            failures.extend(
                _required_oracle_failures(
                    fixture=fixture,
                    qc_reference=qc_reference,
                    rt_drift=rt_drift,
                    ms1_pattern=ms1_pattern,
                    candidate_ms2_pattern=candidate_ms2_pattern,
                )
            )

    failures.extend(
        _activation_boundary_failures(
            fixture["expected_peak_hypothesis_id"],
            fixture["expected_activation_boundary"],
            fixture["expected_activation_unit_scope"],
            activation,
        )
    )
    failures.extend(
        _canonical_identity_failures(
            fixture["expected_canonical_identity_effect"],
            matrix_summary,
        )
    )
    status = "pass" if not failures else "fail"
    if any(reason.endswith("_not_assessed") for reason in failures):
        status = "not_assessed" if len(failures) == 1 else "fail"
    return {
        "mode_window_assignment_gate_schema_version": GATE_ROW_SCHEMA_VERSION,
        "sentinel_id": fixture["sentinel_id"],
        "feature_family_id": fixture["feature_family_id"],
        "sample_id": fixture["sample_id"],
        "sentinel_case_type": sentinel_type,
        "expected_peak_hypothesis_id": fixture["expected_peak_hypothesis_id"],
        "observed_peak_hypothesis_id": observed_hypothesis_id,
        "expected_product_unit_scope": fixture["expected_product_unit_scope"],
        "observed_product_unit_scope": observed_unit_scope,
        "expected_selected_mode_id": fixture["expected_selected_mode_id"],
        "observed_selected_mode_id": observed_mode_id,
        "expected_peak_hypothesis_status": expected_status,
        "observed_peak_hypothesis_status": observed_status,
        "expected_product_selection_action": expected_action,
        "observed_product_selection_action": observed_action,
        "observed_activation_peak_hypothesis_id": text_value(
            (activation or {}).get("peak_hypothesis_id")
        )
        or "not_assessed",
        "expected_activation_unit_scope": fixture["expected_activation_unit_scope"],
        "observed_activation_unit_scope": text_value(
            (activation or {}).get("activation_unit_scope")
        )
        or "not_assessed",
        "expected_activation_boundary": fixture["expected_activation_boundary"],
        "observed_activation_status": text_value(
            (activation or {}).get("activation_status")
        )
        or "not_assessed",
        "observed_contract_rule_id": text_value(
            (activation or {}).get("contract_rule_id")
        ),
        "expected_canonical_identity_effect": fixture[
            "expected_canonical_identity_effect"
        ],
        "observed_canonical_row_identity_ready": text_value(
            matrix_summary.get("canonical_row_identity_ready")
        )
        or "not_assessed",
        "observed_canonical_row_identity_blockers": text_value(
            matrix_summary.get("canonical_row_identity_blockers")
        ),
        "required_evidence_oracle": fixture["required_evidence_oracle"],
        "gate_status": status,
        "failure_reason": ";".join(failures),
        "diagnostic_only": "TRUE",
    }


def _policy_failures(
    *,
    sentinel_type: str,
    qc_reference_rows: Sequence[Mapping[str, str]],
    rt_drift_rows: Sequence[Mapping[str, str]],
) -> tuple[str, ...]:
    if sentinel_type == "qc_local_vs_consensus":
        if not qc_reference_rows:
            return ("qc_reference_policy_not_assessed",)
        has_consensus_policy = any(
            "qc_consensus" in row.get("qc_reference_policy", "")
            and text_value(row.get("qc_consensus_status"))
            for row in qc_reference_rows
        )
        return () if has_consensus_policy else ("qc_consensus_policy_missing",)
    if sentinel_type == "istd_drift_non_parallel":
        if not rt_drift_rows:
            return ("istd_rt_drift_policy_not_assessed",)
        has_trend_context = any(
            text_value(row.get("istd_phase_summary"))
            or text_value(row.get("istd_trend_sample_count"))
            or row.get("drift_evidence_level") == "sample_istd_aligned"
            for row in rt_drift_rows
        )
        return () if has_trend_context else ("istd_trend_context_missing",)
    return ()


def _activation_boundary_failures(
    expected_peak_hypothesis_id: str,
    expected_boundary: str,
    expected_unit_scope: str,
    activation: Mapping[str, str] | None,
) -> tuple[str, ...]:
    if activation is None:
        if (
            expected_boundary in {"auto_block_wrong_peak"}
            or expected_unit_scope not in {"", "not_applicable"}
        ):
            return ("activation_decision_not_assessed",)
        return ()
    failures: list[str] = []
    status = activation.get("activation_status", "")
    rule = activation.get("contract_rule_id", "")
    activation_hypothesis_id = text_value(activation.get("peak_hypothesis_id"))
    unit_scope = text_value(activation.get("activation_unit_scope"))
    if expected_peak_hypothesis_id not in {"", "not_applicable"}:
        if not activation_hypothesis_id:
            failures.append("activation_peak_hypothesis_id_missing")
        elif activation_hypothesis_id != expected_peak_hypothesis_id:
            failures.append("activation_peak_hypothesis_id_mismatch")
    if expected_unit_scope not in {"", "not_applicable"}:
        if unit_scope != expected_unit_scope:
            failures.append("activation_unit_scope_mismatch")
    if expected_boundary == "auto_block_wrong_peak":
        if status != "auto_block" or rule != "wrong_peak_conflict":
            failures.append("activation_wrong_peak_block_mismatch")
    elif expected_boundary.startswith("activation_ineligible"):
        if status == "auto_activate":
            failures.append("activation_ineligible_auto_activated")
        if status == "auto_block":
            failures.append("activation_ineligible_auto_blocked")
    elif expected_boundary == "review_required":
        if status == "auto_activate":
            failures.append("review_required_auto_activated")
    elif expected_boundary == "context_conflict_gate":
        if status in {"auto_activate", "auto_block"}:
            failures.append("context_policy_changed_product")
    elif expected_boundary == "activation_candidate_only":
        if status == "auto_block":
            failures.append("activation_candidate_auto_blocked")
    return tuple(failures)


def _selection_identity_failures(
    fixture: Mapping[str, str],
    selection: Mapping[str, str],
) -> tuple[str, ...]:
    failures: list[str] = []
    expected_hypothesis_id = fixture["expected_peak_hypothesis_id"]
    observed_hypothesis_id = text_value(selection.get("peak_hypothesis_id"))
    expected_unit_scope = fixture["expected_product_unit_scope"]
    observed_unit_scope = text_value(selection.get("product_unit_scope"))
    expected_mode_id = fixture["expected_selected_mode_id"]
    observed_mode_id = text_value(selection.get("selected_mode_id"))
    if expected_hypothesis_id not in {"", "not_applicable"}:
        if not observed_hypothesis_id:
            failures.append("peak_hypothesis_id_missing")
        elif observed_hypothesis_id != expected_hypothesis_id:
            failures.append("peak_hypothesis_id_mismatch")
    if expected_unit_scope not in {"", "not_applicable"}:
        if observed_unit_scope != expected_unit_scope:
            failures.append("product_unit_scope_mismatch")
    if expected_mode_id not in {"", "not_applicable"}:
        if not observed_mode_id:
            failures.append("selected_mode_id_missing")
        elif observed_mode_id != expected_mode_id:
            failures.append("selected_mode_id_mismatch")
    if observed_hypothesis_id and observed_mode_id:
        expected_joined_id = f"{fixture['feature_family_id']}::{observed_mode_id}"
        if observed_hypothesis_id != expected_joined_id:
            failures.append("peak_hypothesis_id_not_mode_scoped")
    failures.extend(_selection_authority_failures(fixture, selection))
    return tuple(failures)


def _selection_authority_failures(
    fixture: Mapping[str, str],
    selection: Mapping[str, str],
) -> tuple[str, ...]:
    status = fixture["expected_peak_hypothesis_status"]
    reason = text_value(selection.get("reason"))
    mode_id = text_value(selection.get("selected_mode_id"))
    if status == "product_candidate_core":
        if not reason.startswith("typed_mode_hypothesis_assignment_"):
            return ("typed_mode_authority_missing",)
        if not mode_id.startswith("irt_"):
            return ("typed_mode_id_missing",)
    if status == "cross_mode_rescue_blocked":
        if reason != "selected_cell_belongs_to_non_core_rt_mode":
            return ("cross_mode_block_reason_mismatch",)
        if not mode_id.startswith("irt_"):
            return ("typed_mode_id_missing",)
    if status == "raw_mode_review_only":
        if reason != "raw_mode_requires_typed_irt_mode_hypothesis":
            return ("raw_mode_review_reason_mismatch",)
    return ()


def _required_oracle_failures(
    *,
    fixture: Mapping[str, str],
    qc_reference: Mapping[str, str] | None,
    rt_drift: Mapping[str, str] | None,
    ms1_pattern: Mapping[str, str] | None,
    candidate_ms2_pattern: Mapping[str, str] | None,
) -> tuple[str, ...]:
    oracle = fixture["required_evidence_oracle"]
    failures: list[str] = []
    if "ms1" in oracle or "shape" in oracle:
        if ms1_pattern is None:
            failures.append("ms1_oracle_not_assessed")
        elif text_value(ms1_pattern.get("ms1_pattern_status")) == "not_available":
            failures.append("ms1_oracle_not_available")
    if "qc" in oracle:
        if qc_reference is None:
            failures.append("qc_oracle_not_assessed")
        elif not text_value(qc_reference.get("qc_reference_policy")):
            failures.append("qc_oracle_not_available")
    if "rt" in oracle:
        if rt_drift is None:
            failures.append("rt_drift_oracle_not_assessed")
        elif not text_value(rt_drift.get("matrix_rt_drift_status")):
            failures.append("rt_drift_oracle_not_available")
    if "ms2" in oracle or "tag" in oracle:
        if candidate_ms2_pattern is None:
            failures.append("candidate_ms2_oracle_not_assessed")
        elif not text_value(
            candidate_ms2_pattern.get("candidate_ms2_pattern_status")
        ):
            failures.append("candidate_ms2_oracle_not_available")
    return tuple(failures)


def _canonical_identity_failures(
    expected_effect: str,
    matrix_summary: Mapping[str, str],
) -> tuple[str, ...]:
    if not matrix_summary:
        return ("canonical_identity_not_assessed",)
    ready = matrix_summary.get("canonical_row_identity_ready", "")
    blockers = matrix_summary.get("canonical_row_identity_blockers", "")
    family_projection_rows = _int_or_none(matrix_summary.get("family_projection_rows"))
    if expected_effect == "partial_until_no_family_projection":
        if family_projection_rows and (
            ready != "FALSE" or blockers in {"", "none"}
        ):
            return ("family_projection_canonical_readiness_overclaim",)
    elif expected_effect == "review_only" and ready == "TRUE":
        return ("review_only_canonical_identity_overclaim",)
    return ()


def _status_matches(
    *,
    expected_status: str,
    observed_status: str,
    sentinel_type: str,
) -> bool:
    if expected_status == observed_status:
        return True
    if sentinel_type == "tailing_confounded":
        return observed_status in {"tailing_review_only", "raw_mode_review_only"}
    return False


def _action_matches(
    *,
    expected_action: str,
    observed_action: str,
    sentinel_type: str,
) -> bool:
    if expected_action == observed_action:
        return True
    if sentinel_type == "tailing_confounded":
        return observed_action in {"require_tailing_review", "require_raw_mode_review"}
    return False


def _rows_by_key(
    rows: Sequence[Mapping[str, str]],
    *,
    sample_field: str,
) -> dict[tuple[str, str], Mapping[str, str]]:
    return {
        (row.get("feature_family_id", ""), row.get(sample_field, "")): row
        for row in rows
    }


def _split_reasons(value: object) -> tuple[str, ...]:
    return tuple(part for part in text_value(value).split(";") if part)


def _first_non_empty(rows: Sequence[Mapping[str, str]], field: str) -> str:
    for row in rows:
        value = text_value(row.get(field))
        if value and value != "not_assessed":
            return value
    return ""


def _int_or_none(value: object) -> int | None:
    try:
        return int(text_value(value))
    except ValueError:
        return None
