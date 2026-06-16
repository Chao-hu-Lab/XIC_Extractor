"""Build matrix-only activation inputs from standard-peak shadow projection."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.alignment.promotion_policy import (
    STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
)
from xic_extractor.alignment.shared_peak_identity_explanation import (
    activation_contract,
)
from xic_extractor.alignment.shared_peak_identity_explanation.schema import (
    ACTIVATION_DECISION_COLUMNS,
    ACTIVATION_DECISION_SCHEMA_VERSION,
    ACTIVATION_VALUE_INPUT_COLUMNS,
)
from xic_extractor.diagnostics.diagnostic_io import (
    format_diagnostic_value,
    split_semicolon_labels,
    text_value,
    write_tsv,
)
from xic_extractor.diagnostics.shadow_production_projection import (
    canonical_shadow_projection_sha256,
)
from xic_extractor.tabular_io import read_tsv_with_header

SCHEMA_VERSION = "standard_peak_shadow_activation_inputs_v1"
SEED_GUARD_SCHEMA_VERSION = "standard_peak_seed_guard_decision_v1"

SUMMARY_COLUMNS = (
    "schema_version",
    "source_run_id",
    "activation_decision_scope",
    "must_not_regress_basis",
    "source_shadow_projection_sha256",
    "source_shadow_projection_row_count",
    "selected_activation_row_count",
    "skipped_current_written_count",
    "skipped_non_accept_count",
    "skipped_non_standard_reason_count",
    "skipped_missing_value_count",
    "seed_guard_candidate_count",
    "seed_guard_blocked_count",
    "standard_peak_gate_status",
    "standard_peak_gate_failure_reasons",
    "activation_acceptance_status",
    "activation_acceptance_hard_fail_reasons",
    "activation_acceptance_max_allowed_product_affecting_rows",
    "activation_decisions_tsv",
    "activation_values_tsv",
    "activation_acceptance_tsv",
    "seed_guard_decisions_tsv",
    "next_action",
)

SEED_GUARD_DECISION_COLUMNS = (
    "schema_version",
    "source_run_id",
    "candidate_set_sha256",
    "candidate_source_row_count",
    "evaluated_row_count",
    "omitted_candidate_count",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_scope",
    "pre_backfill_matrix_path",
    "pre_backfill_matrix_sha256",
    "pre_backfill_review_path",
    "pre_backfill_review_sha256",
    "total_N",
    "detected_count",
    "seed_floor",
    "seed_guard_status",
    "cohort_size_band",
    "cohort_scale_automatic_backfill",
    "per_cell_review_allowed",
    "write_authority_status",
    "product_authority_scope",
    "allowed_contract_rule_ids",
    "per_cell_authority_reason",
    "expected_write_effect",
    "expected_no_write_cell_count",
    "expected_no_write_cell_keys",
    "actual_written_cell_count",
    "actual_written_cell_keys",
    "actual_cohort_scale_written_cell_count",
    "actual_cohort_scale_written_cell_keys",
    "actual_per_cell_written_cell_count",
    "actual_per_cell_written_cell_keys",
    "activation_value_delta_path",
    "activation_value_delta_sha256",
    "decision_reason",
    "blocking_reason",
    "raw_sample_match_status",
)

HELDOUT_ORACLE_RESULTS_SCHEMA_VERSION = (
    "standard_peak_seed_guard_heldout_oracle_results_v1"
)
HELDOUT_ORACLE_MANIFEST_SCHEMA_VERSION = (
    "standard_peak_seed_guard_heldout_oracle_manifest_v1"
)
HELDOUT_ORACLE_MAX_BOUNDARY_DELTA_MIN = 0.1
HELDOUT_ORACLE_MAX_AREA_RELATIVE_ERROR = 0.1
HELDOUT_ORACLE_FLOAT_ABS_TOLERANCE = 1e-12
HELDOUT_ORACLE_MANIFEST_REQUIRED_COLUMNS = (
    "schema_version",
    "oracle_case_id",
    "source_run_id",
    "mask_strategy",
    "masked_sample",
    "heldout_original_cell_status",
    "feature_family_id",
    "peak_hypothesis_id",
    "target_shape_class",
    "oracle_source",
    "oracle_start_rt",
    "oracle_end_rt",
    "oracle_area",
    "baseline_model_set",
    "baseline_epsilon",
    "baseline_residual_threshold",
    "acceptable_boundary_delta_min",
    "acceptable_area_relative_error",
    "expected_seed_guard_status",
    "expected_integration_pathology",
    "expected_matrix_write_allowed",
)
HELDOUT_ORACLE_ALLOWED_ORIGINAL_CELL_STATUS = (
    "detected",
    "detected_seed",
    "quantifiable_detected",
    "accepted_detected",
)
HELDOUT_ORACLE_OBSERVED_REQUIRED_COLUMNS = (
    "oracle_case_id",
    "observed_start_rt",
    "observed_end_rt",
    "observed_area",
    "observed_result_source",
    "observed_boundary_source",
    "observed_area_source",
    "observed_independence_basis",
)
HELDOUT_ORACLE_OBSERVED_ALLOWED_INDEPENDENCE_BASIS = (
    "product_writer_observed_result",
    "masked_rerun_observed_result",
    "independent_boundary_reintegration_result",
)
HELDOUT_ORACLE_RESULTS_COLUMNS = (
    "schema_version",
    "oracle_case_id",
    "source_run_id",
    "feature_family_id",
    "peak_hypothesis_id",
    "masked_sample",
    "observed_start_rt",
    "observed_end_rt",
    "observed_area",
    "observed_result_source",
    "observed_boundary_source",
    "observed_area_source",
    "observed_independence_basis",
    "boundary_error_min",
    "area_relative_error",
    "oracle_case_status",
    "inconclusive_reason",
    "included_in_product_acceptance",
    "result_source_artifact_path",
    "result_source_artifact_sha256",
)


@dataclass(frozen=True)
class StandardPeakActivationInputIndex:
    decisions: tuple[dict[str, str], ...]
    values: tuple[dict[str, str], ...]
    seed_guard_decisions: tuple[dict[str, str], ...]
    acceptance: dict[str, str]
    summary: dict[str, str]


@dataclass(frozen=True)
class StandardPeakActivationInputOutputs:
    decisions_tsv: Path
    values_tsv: Path
    acceptance_tsv: Path
    seed_guard_decisions_tsv: Path
    summary_tsv: Path
    summary_json: Path


@dataclass(frozen=True)
class StandardPeakSeedGuardContext:
    pre_backfill_matrix_path: Path
    pre_backfill_matrix_sha256: str
    pre_backfill_review_path: Path
    pre_backfill_review_sha256: str
    total_n: int
    detected_count_by_family: Mapping[str, int]


def load_seed_guard_context(
    *,
    pre_backfill_matrix_tsv: Path,
    pre_backfill_review_tsv: Path,
) -> StandardPeakSeedGuardContext:
    matrix_header, _matrix_rows = read_tsv_with_header(
        pre_backfill_matrix_tsv,
        required_columns=("Mz", "RT"),
        encoding="utf-8-sig",
    )
    sample_columns = tuple(
        column for column in matrix_header if column not in {"Mz", "RT"}
    )
    _review_header, review_rows = read_tsv_with_header(
        pre_backfill_review_tsv,
        required_columns=("feature_family_id",),
        encoding="utf-8-sig",
    )
    detected_count_by_family: dict[str, int] = {}
    for row in review_rows:
        family_id = text_value(row.get("feature_family_id"))
        if not family_id:
            continue
        detected_count = _optional_non_negative_int(
            row.get("quantifiable_detected_count"),
        )
        if detected_count is None:
            detected_count = _optional_non_negative_int(row.get("detected_count"))
        if detected_count is not None:
            detected_count_by_family[family_id] = detected_count
    return StandardPeakSeedGuardContext(
        pre_backfill_matrix_path=pre_backfill_matrix_tsv,
        pre_backfill_matrix_sha256=sha256_file(pre_backfill_matrix_tsv),
        pre_backfill_review_path=pre_backfill_review_tsv,
        pre_backfill_review_sha256=sha256_file(pre_backfill_review_tsv),
        total_n=len(sample_columns),
        detected_count_by_family=detected_count_by_family,
    )


def build_standard_peak_activation_inputs(
    shadow_projection_rows: Iterable[Mapping[str, str]],
    *,
    source_shadow_projection_sha256: str,
    source_run_id: str = "",
    required_same_peak_reason: str = STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
    seed_guard_context: StandardPeakSeedGuardContext | None = None,
) -> StandardPeakActivationInputIndex:
    rows = tuple(dict(row) for row in shadow_projection_rows)
    candidate_rows: list[dict[str, str]] = []
    decisions: list[dict[str, str]] = []
    values: list[dict[str, str]] = []
    seed_guard_decisions: list[dict[str, str]] = []
    counters: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        selection_reason = _selection_reject_reason(
            row,
            required_same_peak_reason=required_same_peak_reason,
        )
        if selection_reason:
            counters[selection_reason] += 1
            continue
        candidate_rows.append(row)

    candidate_set_sha256 = (
        canonical_shadow_projection_sha256(candidate_rows) if candidate_rows else ""
    )
    candidate_count = len(candidate_rows)
    for row in candidate_rows:
        if seed_guard_context is not None:
            seed_guard_decision = _seed_guard_decision_row(
                row,
                context=seed_guard_context,
                source_run_id=source_run_id,
                candidate_set_sha256=candidate_set_sha256,
                candidate_count=candidate_count,
            )
            seed_guard_decisions.append(seed_guard_decision)
            if _seed_guard_blocks(seed_guard_decision):
                counters["seed_guard_blocked"] += 1
                continue
        key = (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_stem")),
        )
        if key in seen:
            raise ValueError(
                "standard peak activation rows must be unique by "
                f"peak_hypothesis_id/sample_stem: {key[0]}/{key[1]}",
            )
        seen.add(key)
        decisions.append(_activation_decision_row(row))
        values.append(
            _activation_value_row(
                row,
                source_shadow_projection_sha256=source_shadow_projection_sha256,
            ),
        )

    decisions_tuple = tuple(
        sorted(decisions, key=lambda row: (row["feature_family_id"], row["sample_id"]))
    )
    values_tuple = tuple(
        sorted(values, key=lambda row: (row["feature_family_id"], row["sample_stem"]))
    )
    gate_status, gate_failures = _standard_peak_gate_status(
        decisions_tuple,
        values_tuple,
    )
    activation_decision_scope, must_not_regress_basis = _activation_contract_scope(
        decisions_tuple,
    )
    acceptance = activation_contract.summarize_activation_acceptance(
        decisions_tuple,
        blast_radius_current=True,
        activation_decision_scope=activation_decision_scope,
        must_not_regress_status=gate_status,
        must_not_regress_basis=must_not_regress_basis,
        must_not_regress_failure_reasons=gate_failures,
        thresholds=activation_contract.ActivationAcceptanceThresholds(
            max_product_affecting_fraction=1.0,
            max_product_affecting_rows=max(len(decisions_tuple), 1),
        ),
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "activation_decision_scope": activation_decision_scope,
        "must_not_regress_basis": must_not_regress_basis,
        "source_shadow_projection_sha256": source_shadow_projection_sha256,
        "source_shadow_projection_row_count": str(len(rows)),
        "selected_activation_row_count": str(len(decisions_tuple)),
        "skipped_current_written_count": str(counters["current_written"]),
        "skipped_non_accept_count": str(counters["non_accept"]),
        "skipped_non_standard_reason_count": str(counters["non_standard_reason"]),
        "skipped_missing_value_count": str(counters["missing_value"]),
        "seed_guard_candidate_count": str(len(seed_guard_decisions)),
        "seed_guard_blocked_count": str(counters["seed_guard_blocked"]),
        "standard_peak_gate_status": gate_status,
        "standard_peak_gate_failure_reasons": ";".join(gate_failures),
        "activation_acceptance_status": acceptance["acceptance_status"],
        "activation_acceptance_hard_fail_reasons": acceptance["hard_fail_reasons"],
        "activation_acceptance_max_allowed_product_affecting_rows": acceptance[
            "max_allowed_product_affecting_rows"
        ],
        "activation_decisions_tsv": "",
        "activation_values_tsv": "",
        "activation_acceptance_tsv": "",
        "seed_guard_decisions_tsv": "",
        "next_action": _next_action(decisions_tuple, acceptance),
    }
    return StandardPeakActivationInputIndex(
        decisions=decisions_tuple,
        values=values_tuple,
        seed_guard_decisions=tuple(
            sorted(
                seed_guard_decisions,
                key=lambda row: (
                    row["feature_family_id"],
                    row["peak_hypothesis_id"],
                    row["sample_scope"],
                ),
            )
        ),
        acceptance=acceptance,
        summary=summary,
    )


def write_standard_peak_activation_input_outputs(
    output_dir: Path,
    index: StandardPeakActivationInputIndex,
) -> StandardPeakActivationInputOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions_path = output_dir / "standard_peak_activation_decisions.tsv"
    values_path = output_dir / "standard_peak_activation_values.tsv"
    acceptance_path = output_dir / "standard_peak_activation_acceptance.tsv"
    seed_guard_path = output_dir / "seed_guard_decisions.tsv"
    summary_path = output_dir / "standard_peak_activation_inputs.tsv"
    summary_json_path = output_dir / "standard_peak_activation_inputs_summary.json"
    write_tsv(
        decisions_path,
        index.decisions,
        ACTIVATION_DECISION_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        values_path,
        index.values,
        ACTIVATION_VALUE_INPUT_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_tsv(
        acceptance_path,
        (index.acceptance,),
        tuple(index.acceptance.keys()),
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    write_seed_guard_decisions(seed_guard_path, index.seed_guard_decisions)
    summary = dict(index.summary)
    summary.update(
        {
            "activation_decisions_tsv": str(decisions_path),
            "activation_values_tsv": str(values_path),
            "activation_acceptance_tsv": str(acceptance_path),
            "seed_guard_decisions_tsv": str(seed_guard_path),
        },
    )
    write_tsv(
        summary_path,
        (summary,),
        SUMMARY_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary_json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return StandardPeakActivationInputOutputs(
        decisions_tsv=decisions_path,
        values_tsv=values_path,
        acceptance_tsv=acceptance_path,
        seed_guard_decisions_tsv=seed_guard_path,
        summary_tsv=summary_path,
        summary_json=summary_json_path,
    )


def write_seed_guard_decisions(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    write_tsv(
        path,
        rows,
        SEED_GUARD_DECISION_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )


def build_heldout_oracle_results(
    manifest_rows: Sequence[Mapping[str, str]],
    observed_rows: Sequence[Mapping[str, str]],
    *,
    result_source_artifact_path: Path,
) -> tuple[dict[str, str], ...]:
    _validate_heldout_oracle_manifest_rows(manifest_rows)
    manifest_by_case = {
        text_value(row.get("oracle_case_id")): row for row in manifest_rows
    }
    observed_by_case: dict[str, Mapping[str, str]] = {}
    for row in observed_rows:
        oracle_case_id = text_value(row.get("oracle_case_id"))
        if not oracle_case_id:
            raise ValueError("observed oracle_case_id is required")
        if oracle_case_id in observed_by_case:
            raise ValueError(f"duplicate observed oracle_case_id: {oracle_case_id}")
        if oracle_case_id not in manifest_by_case:
            raise ValueError(
                f"observed oracle_case_id not in manifest: {oracle_case_id}",
            )
        _validate_heldout_oracle_observed_row(
            row,
            manifest_row=manifest_by_case[oracle_case_id],
        )
        observed_by_case[oracle_case_id] = row
    if not result_source_artifact_path.is_file():
        raise ValueError(
            "heldout oracle result source artifact is required: "
            f"{result_source_artifact_path}",
        )
    source_sha256 = sha256_file(result_source_artifact_path)
    results: list[dict[str, str]] = []
    for manifest in manifest_rows:
        oracle_case_id = text_value(manifest.get("oracle_case_id"))
        observed = observed_by_case.get(oracle_case_id)
        results.append(
            _heldout_oracle_result_row(
                manifest,
                observed,
                result_source_artifact_path=result_source_artifact_path,
                result_source_artifact_sha256=source_sha256,
            )
        )
    return tuple(results)


def _validate_heldout_oracle_manifest_rows(
    manifest_rows: Sequence[Mapping[str, str]],
) -> None:
    for row in manifest_rows:
        missing_columns = tuple(
            column for column in HELDOUT_ORACLE_MANIFEST_REQUIRED_COLUMNS
            if column not in row
        )
        if missing_columns:
            oracle_case_id = text_value(row.get("oracle_case_id"))
            raise ValueError(
                "heldout oracle manifest missing required columns"
                f" for {oracle_case_id}: {','.join(missing_columns)}",
            )
        schema_version = text_value(row.get("schema_version"))
        if schema_version != HELDOUT_ORACLE_MANIFEST_SCHEMA_VERSION:
            oracle_case_id = text_value(row.get("oracle_case_id"))
            raise ValueError(
                "unsupported heldout oracle manifest schema_version"
                f" for {oracle_case_id}: {schema_version}",
            )
        _validate_heldout_oracle_original_cell_status(row)
        _validate_heldout_oracle_tolerance(
            row,
            column="acceptable_boundary_delta_min",
            max_allowed=HELDOUT_ORACLE_MAX_BOUNDARY_DELTA_MIN,
        )
        _validate_heldout_oracle_tolerance(
            row,
            column="acceptable_area_relative_error",
            max_allowed=HELDOUT_ORACLE_MAX_AREA_RELATIVE_ERROR,
        )


def _validate_heldout_oracle_original_cell_status(
    row: Mapping[str, str],
) -> None:
    oracle_case_id = text_value(row.get("oracle_case_id"))
    status = text_value(row.get("heldout_original_cell_status")).lower()
    if status not in HELDOUT_ORACLE_ALLOWED_ORIGINAL_CELL_STATUS:
        raise ValueError(
            "heldout oracle manifest heldout_original_cell_status must be "
            "an originally detected quantifiable cell"
            f" for {oracle_case_id}: "
            f"{text_value(row.get('heldout_original_cell_status'))}",
        )


def _validate_heldout_oracle_observed_row(
    row: Mapping[str, str],
    *,
    manifest_row: Mapping[str, str],
) -> None:
    missing_columns = tuple(
        column for column in HELDOUT_ORACLE_OBSERVED_REQUIRED_COLUMNS
        if column not in row
    )
    oracle_case_id = text_value(row.get("oracle_case_id"))
    if missing_columns:
        raise ValueError(
            "heldout oracle observed result missing required columns"
            f" for {oracle_case_id}: {','.join(missing_columns)}",
        )
    missing_values = tuple(
        column for column in (
            "observed_result_source",
            "observed_boundary_source",
            "observed_area_source",
            "observed_independence_basis",
        )
        if not text_value(row.get(column))
    )
    if missing_values:
        raise ValueError(
            "heldout oracle observed result missing provenance values"
            f" for {oracle_case_id}: {','.join(missing_values)}",
        )
    independence_basis = text_value(row.get("observed_independence_basis"))
    if independence_basis not in HELDOUT_ORACLE_OBSERVED_ALLOWED_INDEPENDENCE_BASIS:
        raise ValueError(
            "unsupported heldout oracle observed_independence_basis"
            f" for {oracle_case_id}: {independence_basis}",
        )
    source_values = (
        text_value(row.get("observed_result_source")),
        text_value(row.get("observed_boundary_source")),
        text_value(row.get("observed_area_source")),
    )
    if any(_observed_source_looks_like_oracle_copy(value) for value in source_values):
        raise ValueError(
            "heldout oracle observed result source is not independent"
            f" for {oracle_case_id}: {independence_basis}",
        )
    oracle_source = text_value(manifest_row.get("oracle_source"))
    if any(
        _observed_source_matches_oracle_source(value, oracle_source)
        for value in source_values
    ):
        raise ValueError(
            "heldout oracle observed result source is not independent"
            f" for {oracle_case_id}: {independence_basis}",
        )


def write_heldout_oracle_results(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    write_tsv(
        path,
        rows,
        HELDOUT_ORACLE_RESULTS_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )


def seed_guard_decisions_with_actual_writes(
    rows: Sequence[Mapping[str, str]],
    *,
    activation_value_delta_rows: Sequence[Mapping[str, str]],
    activation_value_delta_tsv: Path | None,
) -> tuple[dict[str, str], ...]:
    written_keys = {
        _stable_cell_key(
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_id")),
        )
        for row in activation_value_delta_rows
        if text_value(row.get("matrix_value_effect")) == "written"
    }
    delta_path = (
        "" if activation_value_delta_tsv is None else str(activation_value_delta_tsv)
    )
    delta_sha = (
        ""
        if activation_value_delta_tsv is None
        else sha256_file(activation_value_delta_tsv)
    )
    finalized: list[dict[str, str]] = []
    for row in rows:
        out = dict(row)
        key = _stable_cell_key(
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_scope")),
        )
        actual_keys = tuple(sorted({key} & written_keys))
        cohort_keys = (
            actual_keys
            if text_value(row.get("cohort_scale_automatic_backfill")) == "TRUE"
            else ()
        )
        per_cell_keys = tuple(key for key in actual_keys if key not in cohort_keys)
        out.update(
            {
                "actual_written_cell_count": str(len(actual_keys)),
                "actual_written_cell_keys": ";".join(actual_keys),
                "actual_cohort_scale_written_cell_count": str(len(cohort_keys)),
                "actual_cohort_scale_written_cell_keys": ";".join(cohort_keys),
                "actual_per_cell_written_cell_count": str(len(per_cell_keys)),
                "actual_per_cell_written_cell_keys": ";".join(per_cell_keys),
                "activation_value_delta_path": delta_path,
                "activation_value_delta_sha256": delta_sha,
            }
        )
        if (
            actual_keys
            and text_value(row.get("seed_guard_status")) == "blocked_low_seed_support"
        ):
            out["write_authority_status"] = "blocked_unattributed_write"
            out["blocking_reason"] = "blocked_seed_guard_row_was_written"
        finalized.append(out)
    return tuple(finalized)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _standard_peak_gate_status(
    decisions: Sequence[Mapping[str, str]],
    values: Sequence[Mapping[str, str]],
) -> tuple[str, tuple[str, ...]]:
    failures: list[str] = []
    if len(decisions) != len(values):
        failures.append("decision_value_row_count_mismatch")
    value_keys = {
        (
            text_value(row.get("peak_hypothesis_id")),
            text_value(row.get("sample_stem")),
        )
        for row in values
    }
    for decision in decisions:
        family_id = text_value(decision.get("feature_family_id"))
        sample_id = text_value(decision.get("sample_id"))
        peak_hypothesis_id = text_value(decision.get("peak_hypothesis_id"))
        key_label = f"{family_id}/{sample_id}"
        if not peak_hypothesis_id:
            failures.append(f"{key_label}:missing_peak_hypothesis_id")
        if decision.get("activation_status") != "auto_activate":
            failures.append(f"{key_label}:not_auto_activate")
        if decision.get("activation_unit_scope") != "peak_hypothesis":
            failures.append(f"{key_label}:not_peak_hypothesis_scope")
        if decision.get("contract_rule_id") != (
            "machine_observed_sufficient_positive_identity"
        ):
            failures.append(f"{key_label}:unexpected_contract_rule")
        if (
            STANDARD_PEAK_GATE_MS1_SUPPORT_REASON
            not in text_value(decision.get("source_evidence_tokens"))
        ):
            failures.append(f"{key_label}:missing_standard_peak_reason")
        if (peak_hypothesis_id, sample_id) not in value_keys:
            failures.append(f"{key_label}:missing_activation_value")
    for value in values:
        key_label = (
            f"{text_value(value.get('feature_family_id'))}/"
            f"{text_value(value.get('sample_stem'))}"
        )
        if not text_value(value.get("projected_matrix_value")):
            failures.append(f"{key_label}:blank_projected_matrix_value")
        if text_value(value.get("projected_matrix_value_source")) != (
            "standard_peak_shadow_projection"
        ):
            failures.append(f"{key_label}:unexpected_value_source")
        if text_value(value.get("source_artifact_schema_version")) != (
            "shadow_production_projection_v1"
        ):
            failures.append(f"{key_label}:unexpected_source_schema")
        artifact_sha = text_value(value.get("source_artifact_sha256"))
        if not _is_lowercase_sha256(artifact_sha):
            failures.append(f"{key_label}:invalid_source_artifact_sha256")
        row_sha = text_value(value.get("source_row_sha256"))
        if not _is_lowercase_sha256(row_sha):
            failures.append(f"{key_label}:invalid_source_row_sha256")
    return ("pass", ()) if not failures else ("fail", tuple(failures))


def _activation_contract_scope(
    decisions: Sequence[Mapping[str, str]],
) -> tuple[str, str]:
    source_tokens = tuple(
        text_value(decision.get("source_evidence_tokens")) for decision in decisions
    )
    if any("machine_standard_peak_gate_authorized" in token for token in source_tokens):
        return (
            "machine_gate_standard_peak_rows",
            "machine_shift_aware_standard_peak_gate",
        )
    return ("manual_oracle_seed_rows", "manual_status_flag")


def _is_lowercase_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _next_action(
    decisions: Sequence[Mapping[str, str]],
    acceptance: Mapping[str, str],
) -> str:
    if not decisions:
        return "no_standard_peak_activation_rows"
    if acceptance.get("acceptance_status") == "pass":
        return "apply_matrix_only_activation"
    return "review_standard_peak_activation_gate_failures"


def _seed_guard_decision_row(
    row: Mapping[str, str],
    *,
    context: StandardPeakSeedGuardContext,
    source_run_id: str,
    candidate_set_sha256: str,
    candidate_count: int,
) -> dict[str, str]:
    feature_family_id = text_value(row.get("feature_family_id"))
    peak_hypothesis_id = text_value(row.get("peak_hypothesis_id"))
    sample_scope = text_value(row.get("sample_stem"))
    total_n = context.total_n
    detected_count = context.detected_count_by_family.get(feature_family_id)
    band = _cohort_size_band(total_n)
    seed_floor = _seed_floor(total_n)
    stable_key = _stable_cell_key(peak_hypothesis_id, sample_scope)
    expected_no_write_keys: tuple[str, ...]
    if total_n <= 0 or detected_count is None:
        seed_guard_status = "inconclusive_source_mismatch"
        cohort_scale = False
        per_cell_allowed = False
        write_authority_status = "no_write"
        product_authority_scope = ""
        allowed_contract_rule_ids = ""
        per_cell_authority_reason = ""
        expected_write_effect = "no_write"
        expected_no_write_keys = (stable_key,)
        decision_reason = "seed_guard_source_missing"
        blocking_reason = "seed_guard_source_missing"
    elif total_n < 20:
        seed_guard_status = "not_applicable_small_cohort"
        cohort_scale = False
        per_cell_allowed = True
        write_authority_status = "per_cell_product_authorized"
        product_authority_scope = "feature_family_sample"
        allowed_contract_rule_ids = "machine_observed_sufficient_positive_identity"
        per_cell_authority_reason = "standard_peak_existing_per_cell_gate"
        expected_write_effect = "per_cell_write_allowed"
        expected_no_write_keys = ()
        decision_reason = "small_cohort_seed_guard_not_applicable"
        blocking_reason = ""
    elif detected_count < seed_floor:
        seed_guard_status = "blocked_low_seed_support"
        cohort_scale = False
        per_cell_allowed = False
        write_authority_status = "no_write"
        product_authority_scope = ""
        allowed_contract_rule_ids = ""
        per_cell_authority_reason = ""
        expected_write_effect = "no_write"
        expected_no_write_keys = (stable_key,)
        decision_reason = "detected_count_below_seed_floor"
        blocking_reason = "low_seed_support"
    elif total_n < 80:
        seed_guard_status = "eligible_per_cell_only"
        cohort_scale = False
        per_cell_allowed = True
        write_authority_status = "per_cell_product_authorized"
        product_authority_scope = "feature_family_sample"
        allowed_contract_rule_ids = "machine_observed_sufficient_positive_identity"
        per_cell_authority_reason = "medium_cohort_per_cell_only"
        expected_write_effect = "per_cell_write_allowed"
        expected_no_write_keys = ()
        decision_reason = "medium_cohort_seed_floor_met"
        blocking_reason = ""
    else:
        seed_guard_status = "eligible_continue_existing_gates"
        cohort_scale = True
        per_cell_allowed = True
        write_authority_status = "cohort_scale_standard_backfill"
        product_authority_scope = "feature_family"
        allowed_contract_rule_ids = "machine_observed_sufficient_positive_identity"
        per_cell_authority_reason = ""
        expected_write_effect = "continue_existing_gates"
        expected_no_write_keys = ()
        decision_reason = "large_cohort_seed_floor_met"
        blocking_reason = ""
    return {
        "schema_version": SEED_GUARD_SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "candidate_set_sha256": candidate_set_sha256,
        "candidate_source_row_count": str(candidate_count),
        "evaluated_row_count": str(candidate_count),
        "omitted_candidate_count": "0",
        "feature_family_id": feature_family_id,
        "peak_hypothesis_id": peak_hypothesis_id,
        "sample_scope": sample_scope,
        "pre_backfill_matrix_path": str(context.pre_backfill_matrix_path),
        "pre_backfill_matrix_sha256": context.pre_backfill_matrix_sha256,
        "pre_backfill_review_path": str(context.pre_backfill_review_path),
        "pre_backfill_review_sha256": context.pre_backfill_review_sha256,
        "total_N": str(total_n),
        "detected_count": "" if detected_count is None else str(detected_count),
        "seed_floor": "" if total_n < 20 or seed_floor <= 0 else str(seed_floor),
        "seed_guard_status": seed_guard_status,
        "cohort_size_band": band,
        "cohort_scale_automatic_backfill": _bool_text(cohort_scale),
        "per_cell_review_allowed": _bool_text(per_cell_allowed),
        "write_authority_status": write_authority_status,
        "product_authority_scope": product_authority_scope,
        "allowed_contract_rule_ids": allowed_contract_rule_ids,
        "per_cell_authority_reason": per_cell_authority_reason,
        "expected_write_effect": expected_write_effect,
        "expected_no_write_cell_count": str(len(expected_no_write_keys)),
        "expected_no_write_cell_keys": ";".join(expected_no_write_keys),
        "actual_written_cell_count": "0",
        "actual_written_cell_keys": "",
        "actual_cohort_scale_written_cell_count": "0",
        "actual_cohort_scale_written_cell_keys": "",
        "actual_per_cell_written_cell_count": "0",
        "actual_per_cell_written_cell_keys": "",
        "activation_value_delta_path": "",
        "activation_value_delta_sha256": "",
        "decision_reason": decision_reason,
        "blocking_reason": blocking_reason,
        "raw_sample_match_status": "not_checked_no_raw",
    }


def _seed_guard_blocks(row: Mapping[str, str]) -> bool:
    return text_value(row.get("seed_guard_status")) in {
        "blocked_low_seed_support",
        "inconclusive_source_mismatch",
    }


def _validate_heldout_oracle_tolerance(
    row: Mapping[str, str],
    *,
    column: str,
    max_allowed: float,
) -> None:
    value = _optional_float(row.get(column))
    oracle_case_id = text_value(row.get("oracle_case_id"))
    if value is None or value <= 0:
        raise ValueError(
            f"invalid heldout oracle {column} for {oracle_case_id}: "
            f"{text_value(row.get(column))}",
        )
    if value > max_allowed + 1e-12:
        raise ValueError(
            f"heldout oracle {column} for {oracle_case_id} exceeds accepted "
            f"maximum {max_allowed:g}: {value:g}",
        )


def _cohort_size_band(total_n: int) -> str:
    if total_n < 20:
        return "small_lt20"
    if total_n < 80:
        return "medium_20_to_79"
    return "large_ge80"


def _seed_floor(total_n: int) -> int:
    if total_n < 20:
        return 0
    if total_n < 80:
        return max(2, math.floor(total_n * 0.05))
    return max(4, math.floor(total_n * 0.05))


def _optional_non_negative_int(value: object) -> int | None:
    text = text_value(value)
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _stable_cell_key(peak_hypothesis_id: str, sample_stem: str) -> str:
    return f"{peak_hypothesis_id}/{sample_stem}"


def _bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _heldout_oracle_result_row(
    manifest: Mapping[str, str],
    observed: Mapping[str, str] | None,
    *,
    result_source_artifact_path: Path,
    result_source_artifact_sha256: str,
) -> dict[str, str]:
    oracle_area = _optional_float(manifest.get("oracle_area"))
    oracle_start = _optional_float(manifest.get("oracle_start_rt"))
    oracle_end = _optional_float(manifest.get("oracle_end_rt"))
    boundary_tolerance = _optional_float(manifest.get("acceptable_boundary_delta_min"))
    area_tolerance = _optional_float(manifest.get("acceptable_area_relative_error"))
    observed_start = (
        _optional_float(observed.get("observed_start_rt")) if observed else None
    )
    observed_end = (
        _optional_float(observed.get("observed_end_rt")) if observed else None
    )
    observed_area = _optional_float(observed.get("observed_area")) if observed else None
    status = "pass"
    inconclusive_reason = ""
    boundary_error: float | None = None
    area_relative_error: float | None = None
    if observed is None:
        status = "inconclusive_review_only"
        inconclusive_reason = "missing_observed_result"
    elif (
        oracle_start is None
        or oracle_end is None
        or observed_start is None
        or observed_end is None
        or boundary_tolerance is None
    ):
        status = "inconclusive_review_only"
        inconclusive_reason = "invalid_boundary_inputs"
    else:
        boundary_error = abs(observed_start - oracle_start) + abs(
            observed_end - oracle_end
        )
        if _exceeds_heldout_oracle_tolerance(boundary_error, boundary_tolerance):
            status = "fail_boundary"
    if status == "pass":
        if (
            oracle_area is None
            or oracle_area <= 0
            or observed_area is None
            or area_tolerance is None
        ):
            status = "inconclusive_review_only"
            inconclusive_reason = "invalid_oracle_area"
        else:
            area_relative_error = abs(observed_area - oracle_area) / abs(oracle_area)
            if _exceeds_heldout_oracle_tolerance(
                area_relative_error,
                area_tolerance,
            ):
                status = "fail_area"
    included = (
        status == "pass"
        and text_value(manifest.get("expected_matrix_write_allowed")).upper() == "TRUE"
    )
    return {
        "schema_version": HELDOUT_ORACLE_RESULTS_SCHEMA_VERSION,
        "oracle_case_id": text_value(manifest.get("oracle_case_id")),
        "source_run_id": text_value(manifest.get("source_run_id")),
        "feature_family_id": text_value(manifest.get("feature_family_id")),
        "peak_hypothesis_id": text_value(manifest.get("peak_hypothesis_id")),
        "masked_sample": text_value(manifest.get("masked_sample")),
        "observed_start_rt": _float_text(observed_start),
        "observed_end_rt": _float_text(observed_end),
        "observed_area": _float_text(observed_area),
        "observed_result_source": (
            text_value(observed.get("observed_result_source")) if observed else ""
        ),
        "observed_boundary_source": (
            text_value(observed.get("observed_boundary_source")) if observed else ""
        ),
        "observed_area_source": (
            text_value(observed.get("observed_area_source")) if observed else ""
        ),
        "observed_independence_basis": (
            text_value(observed.get("observed_independence_basis")) if observed else ""
        ),
        "boundary_error_min": _float_text(boundary_error),
        "area_relative_error": _float_text(area_relative_error),
        "oracle_case_status": status,
        "inconclusive_reason": inconclusive_reason,
        "included_in_product_acceptance": _bool_text(included),
        "result_source_artifact_path": str(result_source_artifact_path),
        "result_source_artifact_sha256": result_source_artifact_sha256,
    }


def _optional_float(value: object) -> float | None:
    text = text_value(value)
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _exceeds_heldout_oracle_tolerance(value: float, tolerance: float) -> bool:
    return value > tolerance + HELDOUT_ORACLE_FLOAT_ABS_TOLERANCE


def _observed_source_looks_like_oracle_copy(value: str) -> bool:
    normalized = _canonical_heldout_oracle_source_label(value)
    return any(
        token in normalized
        for token in (
            "oracle_source",
            "oracle_row",
            "manual_oracle",
            "manual_review",
            "manual_verdict",
            "review_queue",
        )
    )


def _observed_source_matches_oracle_source(value: str, oracle_source: str) -> bool:
    observed = _canonical_heldout_oracle_source_label(value)
    expected_oracle = _canonical_heldout_oracle_source_label(oracle_source)
    return bool(observed and expected_oracle and observed == expected_oracle)


def _canonical_heldout_oracle_source_label(value: str) -> str:
    return "_".join(
        part
        for part in "".join(
            char if char.isalnum() else "_" for char in value.lower()
        ).split("_")
        if part
    )


def _float_text(value: float | None) -> str:
    return "" if value is None else f"{value:.6g}"


def _selection_reject_reason(
    row: Mapping[str, str],
    *,
    required_same_peak_reason: str,
) -> str:
    if required_same_peak_reason and required_same_peak_reason not in text_value(
        row.get("product_authority_chain"),
    ):
        return "non_standard_reason"
    if text_value(row.get("current_matrix_written")) == "TRUE":
        return "current_written"
    if text_value(row.get("shadow_decision")) != "accept":
        return "non_accept"
    if text_value(row.get("projected_matrix_written")) != "TRUE":
        return "missing_value"
    if not text_value(row.get("projected_matrix_value")):
        return "missing_value"
    if not text_value(row.get("peak_hypothesis_id")) or not text_value(
        row.get("sample_stem"),
    ):
        return "missing_value"
    return ""


def _activation_decision_row(row: Mapping[str, str]) -> dict[str, str]:
    family_id = text_value(row.get("feature_family_id"))
    sample_id = text_value(row.get("sample_stem"))
    peak_hypothesis_id = text_value(row.get("peak_hypothesis_id"))
    source_provenance = _source_provenance_detail(row)
    return {
        "activation_schema_version": ACTIVATION_DECISION_SCHEMA_VERSION,
        "feature_family_id": family_id,
        "candidate_container_id": peak_hypothesis_id,
        "sample_id": sample_id,
        "peak_hypothesis_id": peak_hypothesis_id,
        "activation_unit_scope": "peak_hypothesis",
        "machine_current_label": text_value(row.get("current_production_status"))
        or text_value(row.get("current_raw_status")),
        "evidence_support_status": "product_authorized_standard_peak_ms1",
        "activation_status": "auto_activate",
        "activation_action": "activate_pass",
        "product_label_candidate": "pass",
        "product_effect": "accept_label_or_rescue",
        "activation_confidence": "high",
        "hard_product_block": "FALSE",
        "contract_rule_id": "machine_observed_sufficient_positive_identity",
        "activation_reason": (
            "standard_peak_shift_aware_ms1_same_peak_product_authorized"
        ),
        "required_review_reason": "",
        "source_evidence_tokens": source_provenance,
        "diagnostic_only": "FALSE",
    }


def _activation_value_row(
    row: Mapping[str, str],
    *,
    source_shadow_projection_sha256: str,
) -> dict[str, str]:
    return {
        "peak_hypothesis_id": text_value(row.get("peak_hypothesis_id")),
        "feature_family_id": text_value(row.get("feature_family_id")),
        "sample_stem": text_value(row.get("sample_stem")),
        "projected_matrix_value": text_value(row.get("projected_matrix_value")),
        "projected_matrix_value_source": "standard_peak_shadow_projection",
        "current_raw_status": text_value(row.get("current_raw_status")),
        "current_production_status": text_value(row.get("current_production_status")),
        "source_artifact_schema_version": text_value(row.get("schema_version")),
        "source_artifact_sha256": source_shadow_projection_sha256,
        "source_row_sha256": text_value(row.get("shadow_projection_row_sha256")),
        "source_provenance_detail": _source_provenance_detail(row),
    }


def _source_provenance_detail(row: Mapping[str, str]) -> str:
    warnings = tuple(
        f"audit_warning:{warning}"
        for warning in split_semicolon_labels(row.get("shadow_warnings"))
    )
    return " | ".join(
        dict.fromkeys(
            part
            for part in (text_value(row.get("product_authority_chain")), *warnings)
            if part
        ),
    )
