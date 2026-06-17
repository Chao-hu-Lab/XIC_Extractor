"""Orchestrate standard-peak backfill activation and synced gallery output."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    product_activation,
)
from xic_extractor.alignment.shared_peak_identity_explanation.schema import (
    ACTIVATION_APPLICATION_SUMMARY_COLUMNS,
    ACTIVATION_VALUE_DELTA_COLUMNS,
)
from xic_extractor.diagnostics import backfill_reconciliation_gallery
from xic_extractor.diagnostics.diagnostic_io import (
    file_sha256,
    format_diagnostic_value,
    optional_float,
    read_tsv_required,
    text_value,
    write_tsv,
)
from xic_extractor.diagnostics.shadow_production_projection import (
    canonical_shadow_projection_sha256,
)
from xic_extractor.diagnostics.standard_peak_shadow_activation_inputs import (
    StandardPeakActivationInputOutputs,
    build_standard_peak_activation_inputs,
    load_seed_guard_context,
    seed_guard_decisions_with_actual_writes,
    write_seed_guard_decisions,
    write_standard_peak_activation_input_outputs,
)
from xic_extractor.tabular_io import (
    identity_family_keys,
    positive_int,
    read_tsv_with_header,
)

SCHEMA_VERSION = "standard_peak_backfill_productization_v1"
BACKFILL_POLICY_SCHEMA_VERSION = "standard_peak_backfill_policy_v2"
BACKFILL_POLICY_DECISION_COLUMN = "backfill_policy_decision"
BACKFILL_POLICY_WRITE_READY = "write_ready"
BACKFILL_POLICY_ALLOWED_DECISIONS = frozenset(
    {"write_ready", "detected_flagged", "blocked"},
)
NARROW_PRODUCT_WRITER_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION = (
    "standard_peak_narrow_product_writer_expected_diff_acceptance_v1"
)

SHADOW_PROJECTION_REQUIRED_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "feature_family_id",
    "sample_stem",
    "current_raw_status",
    "current_production_status",
    "current_matrix_written",
    "shadow_decision",
    "projected_matrix_written",
    "projected_matrix_value",
    "product_authority_chain",
    "shadow_projection_row_sha256",
)

SUMMARY_COLUMNS = (
    "schema_version",
    "source_run_id",
    "status",
    "source_shadow_projection_tsv",
    "activation_scope_contract",
    "activation_scope_filter_status",
    "activation_scope_audit_tsv",
    "activation_scope_audit_sha256",
    "reintegration_stability_audit_tsv",
    "reintegration_stability_audit_sha256",
    "activation_scope_filter_selected_shadow_row_count",
    "activation_scope_filter_excluded_shadow_row_count",
    "activation_scope_filter_eligible_audit_row_count",
    "standard_peak_activation_inputs_dir",
    "activated_matrix_dir",
    "reconciliation_gallery_dir",
    "selected_activation_row_count",
    "skipped_current_written_count",
    "skipped_non_accept_count",
    "skipped_non_standard_reason_count",
    "skipped_missing_value_count",
    "activation_acceptance_status",
    "activation_acceptance_hard_fail_reasons",
    "activation_application_status",
    "activation_output_mode",
    "matrix_cells_written",
    "matrix_cells_blanked",
    "activation_value_delta_written_count",
    "activation_value_delta_row_count",
    "standard_peak_activation_decisions_tsv",
    "standard_peak_activation_values_tsv",
    "standard_peak_activation_acceptance_tsv",
    "activated_alignment_matrix_tsv",
    "activation_application_summary_tsv",
    "activation_value_delta_tsv",
    "narrow_product_writer_expected_diff_acceptance_status",
    "narrow_product_writer_expected_diff_acceptance_tsv",
    "narrow_product_writer_expected_diff_acceptance_json",
    "reconciliation_gallery_html",
    "matrix_contract_changed",
    "product_behavior_changed",
    "next_action",
)

ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_id",
    "matrix_value_effect",
    "matrix_value_source_row_sha256",
    "high_signal_clean_status",
)
ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION = "standard_peak_activation_scope_audit_v1"
REINTEGRATION_STABILITY_AUDIT_SCHEMA_VERSION = (
    "standard_peak_reintegration_stability_audit_v1"
)
REINTEGRATION_STABILITY_AUDIT_REQUIRED_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "sample_id",
    "matrix_value_effect",
    "matrix_value_source_row_sha256",
    "stability_status",
)
BACKFILL_POLICY_REQUIRED_COLUMNS = (
    "schema_version",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_id",
    "matrix_value_effect",
    "matrix_value_source_row_sha256",
    BACKFILL_POLICY_DECISION_COLUMN,
    "backfill_policy_evidence_class",
    "backfill_policy_authority_status",
    "backfill_policy_reason",
    "backfill_policy_decision_basis",
    "backfill_policy_next_evidence",
)
BACKFILL_POLICY_OUTPUT_COLUMNS = (
    "schema_version",
    "source_run_id",
    "feature_family_id",
    "peak_hypothesis_id",
    "sample_id",
    "matrix_value_effect",
    "matrix_value_source_row_sha256",
    BACKFILL_POLICY_DECISION_COLUMN,
    "backfill_policy_evidence_class",
    "backfill_policy_authority_status",
    "backfill_policy_reason",
    "backfill_policy_decision_basis",
    "backfill_policy_next_evidence",
    "backfill_policy_candidate_evidence_class",
    "ready_evidence_classes",
    "stability_status",
    "backfill_policy_blockers",
)
BACKFILL_POLICY_SOURCE_AUDIT_REQUIRED_COLUMNS = (
    *ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS,
    "low_scan_clean_status",
    "low_height_clean_status",
    "low_height_low_scan_clean_status",
    "cell_height",
    "trace_match_status",
)
LOW_HEIGHT_REINTEGRATION_STABLE_STATUS_COLUMN = (
    "low_height_reintegration_stable_status"
)
MIN_LOW_HEIGHT_REINTEGRATION_STABLE_HEIGHT = 2_000_000.0

NARROW_PRODUCT_WRITER_EXPECTED_DIFF_ACCEPTANCE_COLUMNS = (
    "schema_version",
    "source_run_id",
    "acceptance_status",
    "readiness_tier",
    "expected_scope",
    "activation_scope_audit_tsv",
    "activation_scope_audit_sha256",
    "reintegration_stability_audit_tsv",
    "reintegration_stability_audit_sha256",
    "product_activation_value_delta_tsv",
    "product_activation_value_delta_sha256",
    "activation_application_status",
    "matrix_cells_written",
    "eligible_audit_row_count",
    "product_delta_row_count",
    "product_written_delta_row_count",
    "duplicate_delta_key_count",
    "missing_delta_row_count",
    "unexpected_delta_row_count",
    "non_eligible_delta_row_count",
    "not_written_delta_row_count",
    "unchanged_delta_row_count",
    "blank_activated_value_count",
    "blocking_reasons",
    "product_surface_changed",
    "next_action",
)


@dataclass(frozen=True)
class StandardPeakBackfillProductizationOutputs:
    summary_tsv: Path
    summary_json: Path
    status: str
    activation_inputs: StandardPeakActivationInputOutputs
    activated_matrix_tsv: Path | None = None
    activation_application_summary_tsv: Path | None = None
    activation_value_delta_tsv: Path | None = None
    narrow_product_writer_expected_diff_acceptance_tsv: Path | None = None
    narrow_product_writer_expected_diff_acceptance_json: Path | None = None
    reconciliation_gallery_html: Path | None = None


@dataclass(frozen=True)
class _ActivationScopeRequest:
    audit_tsv: Path | None
    contract: str
    status_column: str
    label: str
    no_rows_blocker: str
    ready_next_action: str
    eligible_value: str = "eligible"
    required_columns: tuple[str, ...] | None = None
    schema_version: str = ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION
    reintegration_stability_audit_tsv: Path | None = None


def run_standard_peak_backfill_productization(
    *,
    shadow_projection_cells_tsv: Path,
    alignment_matrix_tsv: Path,
    alignment_matrix_identity_tsv: Path,
    alignment_review_tsv: Path,
    output_dir: Path,
    source_run_id: str = "",
    write_gallery: bool = False,
    alignment_cells_tsv: Path | None = None,
    backfill_seed_audit_tsv: Path | None = None,
    overlay_batch_summary_tsvs: Sequence[Path] = (),
    shift_aware_standard_peak_gate_tsvs: Sequence[Path] = (),
    retained_backfill_gate_tsv: Path | None = None,
    gallery_output_dir: Path | None = None,
    high_signal_clean_activation_scope_audit_tsv: Path | None = None,
    low_scan_clean_activation_scope_audit_tsv: Path | None = None,
    low_height_clean_activation_scope_audit_tsv: Path | None = None,
    low_height_low_scan_clean_activation_scope_audit_tsv: Path | None = None,
    low_height_reintegration_stable_activation_scope_audit_tsv: Path | None = None,
    reintegration_stability_audit_tsv: Path | None = None,
    backfill_policy_source_audit_tsv: Path | None = None,
) -> StandardPeakBackfillProductizationOutputs:
    """Apply standard-peak projection accepts and optionally render synced gallery."""

    output_dir.mkdir(parents=True, exist_ok=True)
    activation_inputs_dir = output_dir / "standard_peak_activation_inputs"
    activated_matrix_dir = output_dir / "activated_matrix"
    gallery_dir = gallery_output_dir or output_dir / "reconciliation_gallery"

    shadow_rows = read_tsv_required(
        shadow_projection_cells_tsv,
        SHADOW_PROJECTION_REQUIRED_COLUMNS,
    )
    _validate_shadow_current_matrix_claims(
        shadow_rows,
        alignment_matrix_tsv=alignment_matrix_tsv,
        alignment_matrix_identity_tsv=alignment_matrix_identity_tsv,
    )
    generated_policy_tsv: Path | None = None
    if backfill_policy_source_audit_tsv is not None:
        generated_policy_tsv = _write_backfill_policy_from_source_audit(
            source_audit_tsv=backfill_policy_source_audit_tsv,
            reintegration_stability_audit_tsv=reintegration_stability_audit_tsv,
            output_dir=output_dir,
            source_run_id=source_run_id,
        )
    activation_scope = _activation_scope_request(
        high_signal_clean_activation_scope_audit_tsv=(
            high_signal_clean_activation_scope_audit_tsv
        ),
        low_scan_clean_activation_scope_audit_tsv=(
            low_scan_clean_activation_scope_audit_tsv
        ),
        low_height_clean_activation_scope_audit_tsv=(
            low_height_clean_activation_scope_audit_tsv
        ),
        low_height_low_scan_clean_activation_scope_audit_tsv=(
            low_height_low_scan_clean_activation_scope_audit_tsv
        ),
        low_height_reintegration_stable_activation_scope_audit_tsv=(
            low_height_reintegration_stable_activation_scope_audit_tsv
        ),
        reintegration_stability_audit_tsv=reintegration_stability_audit_tsv,
        activation_policy_tsv=generated_policy_tsv,
    )
    (
        activation_shadow_rows,
        activation_scope_filter,
        activation_scope_audit_rows,
    ) = _filter_shadow_rows_to_activation_scope(
        shadow_rows,
        activation_scope_audit_tsv=activation_scope.audit_tsv,
        reintegration_stability_audit_tsv=(
            activation_scope.reintegration_stability_audit_tsv
        ),
        activation_scope_contract=activation_scope.contract,
        scope_status_column=activation_scope.status_column,
        scope_label=activation_scope.label,
        scope_eligible_value=activation_scope.eligible_value,
        scope_required_columns=activation_scope.required_columns,
        expected_schema_version=activation_scope.schema_version,
    )
    activation_index = build_standard_peak_activation_inputs(
        activation_shadow_rows,
        source_shadow_projection_sha256=canonical_shadow_projection_sha256(
            activation_shadow_rows,
        ),
        source_run_id=source_run_id,
        seed_guard_context=load_seed_guard_context(
            pre_backfill_matrix_tsv=alignment_matrix_tsv,
            pre_backfill_review_tsv=alignment_review_tsv,
        ),
    )
    activation_outputs = write_standard_peak_activation_input_outputs(
        activation_inputs_dir,
        activation_index,
    )
    selected_count = _int_value(
        activation_index.summary.get("selected_activation_row_count"),
    )
    acceptance_status = text_value(
        activation_index.summary.get("activation_acceptance_status"),
    )
    hard_fail_reasons = text_value(
        activation_index.summary.get("activation_acceptance_hard_fail_reasons"),
    )

    apply_outputs: product_activation.MatrixActivationApplicationOutputs | None = None
    application_summary: dict[str, str] = {}
    delta_rows: tuple[dict[str, str], ...] = ()
    narrow_writer_acceptance: dict[str, str] = {}
    narrow_writer_acceptance_tsv: Path | None = None
    narrow_writer_acceptance_json: Path | None = None
    status = "pass"
    next_action = "no_new_standard_peak_activation_rows"
    if acceptance_status != "pass":
        status = "fail"
        next_action = "review_standard_peak_activation_gate_failures"
    elif selected_count > 0:
        apply_outputs = product_activation.apply_activation_to_alignment_matrix_outputs(
            activation_decisions_tsv=activation_outputs.decisions_tsv,
            activation_acceptance_tsv=activation_outputs.acceptance_tsv,
            activation_values_tsv=activation_outputs.values_tsv,
            alignment_matrix_tsv=alignment_matrix_tsv,
            alignment_matrix_identity_tsv=alignment_matrix_identity_tsv,
            alignment_review_tsv=alignment_review_tsv,
            output_dir=activated_matrix_dir,
        )
        application_summary = _single_row(
            read_tsv_required(
                apply_outputs.summary_tsv,
                ACTIVATION_APPLICATION_SUMMARY_COLUMNS,
            ),
        )
        delta_rows = read_tsv_required(
            apply_outputs.value_delta_tsv,
            ACTIVATION_VALUE_DELTA_COLUMNS,
        )
        if activation_index.seed_guard_decisions:
            finalized_seed_guard_decisions = seed_guard_decisions_with_actual_writes(
                activation_index.seed_guard_decisions,
                activation_value_delta_rows=delta_rows,
                activation_value_delta_tsv=apply_outputs.value_delta_tsv,
            )
            write_seed_guard_decisions(
                activation_outputs.seed_guard_decisions_tsv,
                finalized_seed_guard_decisions,
            )
            attribution_failures = _seed_guard_write_attribution_failures(
                finalized_seed_guard_decisions,
            )
            if attribution_failures:
                status = "fail"
                next_action = "review_seed_guard_write_attribution_failure"
                hard_fail_reasons = _append_failure_reasons(
                    hard_fail_reasons,
                    attribution_failures,
                )
        if text_value(application_summary.get("application_status")) != "applied":
            status = "fail"
            next_action = "review_activation_application_failure"
        elif status == "pass":
            next_action = "review_activation_application_summary"
        if activation_scope_audit_rows:
            narrow_writer_acceptance_tsv = (
                output_dir / "narrow_product_writer_expected_diff_acceptance.tsv"
            )
            narrow_writer_acceptance_json = (
                output_dir / "narrow_product_writer_expected_diff_acceptance.json"
            )
            narrow_writer_acceptance = (
                _narrow_product_writer_expected_diff_acceptance_row(
                    activation_scope_audit_rows=activation_scope_audit_rows,
                    product_activation_value_delta_rows=delta_rows,
                    activation_scope_audit_tsv=activation_scope.audit_tsv,
                    reintegration_stability_audit_tsv=(
                        activation_scope.reintegration_stability_audit_tsv
                    ),
                    product_activation_value_delta_tsv=apply_outputs.value_delta_tsv,
                    application_summary=application_summary,
                    source_run_id=source_run_id,
                    scope_status_column=activation_scope.status_column,
                    scope_eligible_value=activation_scope.eligible_value,
                    expected_scope=activation_scope.contract,
                    no_rows_blocker=activation_scope.no_rows_blocker,
                    ready_next_action=activation_scope.ready_next_action,
                )
            )
            write_tsv(
                narrow_writer_acceptance_tsv,
                (narrow_writer_acceptance,),
                NARROW_PRODUCT_WRITER_EXPECTED_DIFF_ACCEPTANCE_COLUMNS,
                formatter=format_diagnostic_value,
                lineterminator="\n",
            )
            narrow_writer_acceptance_json.write_text(
                json.dumps(narrow_writer_acceptance, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            if narrow_writer_acceptance["acceptance_status"] != "pass":
                status = "fail"
                next_action = "review_narrow_product_writer_expected_diff_failures"
                hard_fail_reasons = _append_failure_reasons(
                    hard_fail_reasons,
                    (narrow_writer_acceptance["blocking_reasons"],),
                )
            elif status == "pass":
                next_action = activation_scope.ready_next_action
    elif activation_scope_audit_rows:
        status = "fail"
        next_action = "review_narrow_activation_scope_no_product_rows"
        hard_fail_reasons = _append_failure_reasons(
            hard_fail_reasons,
            ("narrow_activation_scope_selected_no_product_rows",),
        )

    gallery_outputs: backfill_reconciliation_gallery.ReconciliationOutputs | None = None
    if write_gallery:
        if alignment_cells_tsv is None:
            raise ValueError("--write-gallery requires --alignment-cells-tsv")
        gallery_outputs = backfill_reconciliation_gallery.run_reconciliation_gallery(
            alignment_review_tsv=alignment_review_tsv,
            alignment_cells_tsv=alignment_cells_tsv,
            output_dir=gallery_dir,
            alignment_matrix_tsv=alignment_matrix_tsv,
            backfill_seed_audit_tsv=backfill_seed_audit_tsv,
            overlay_batch_summary_tsvs=tuple(overlay_batch_summary_tsvs),
            shift_aware_standard_peak_gate_tsvs=tuple(
                shift_aware_standard_peak_gate_tsvs,
            ),
            retained_backfill_gate_tsv=retained_backfill_gate_tsv,
            shadow_projection_cells_tsv=shadow_projection_cells_tsv,
            activation_application_summary_tsv=(
                apply_outputs.summary_tsv if apply_outputs is not None else None
            ),
            activation_value_delta_tsv=(
                apply_outputs.value_delta_tsv if apply_outputs is not None else None
            ),
            source_run_id=source_run_id,
        )
        if status == "pass":
            next_action = "review_activation_synced_gallery"

    summary = _summary_row(
        source_run_id=source_run_id,
        status=status,
        shadow_projection_cells_tsv=shadow_projection_cells_tsv,
        activation_inputs_dir=activation_inputs_dir,
        activated_matrix_dir=activated_matrix_dir if apply_outputs else None,
        gallery_dir=gallery_dir if gallery_outputs else None,
        activation_summary=activation_index.summary,
        activation_scope_filter=activation_scope_filter,
        application_summary=application_summary,
        delta_rows=delta_rows,
        activation_outputs=activation_outputs,
        apply_outputs=apply_outputs,
        narrow_writer_acceptance=narrow_writer_acceptance,
        narrow_writer_acceptance_tsv=narrow_writer_acceptance_tsv,
        narrow_writer_acceptance_json=narrow_writer_acceptance_json,
        gallery_outputs=gallery_outputs,
        hard_fail_reasons=hard_fail_reasons,
        next_action=next_action,
    )
    summary_tsv = output_dir / "standard_peak_backfill_productization_summary.tsv"
    summary_json = output_dir / "standard_peak_backfill_productization_summary.json"
    write_tsv(
        summary_tsv,
        (summary,),
        SUMMARY_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return StandardPeakBackfillProductizationOutputs(
        summary_tsv=summary_tsv,
        summary_json=summary_json,
        status=status,
        activation_inputs=activation_outputs,
        activated_matrix_tsv=apply_outputs.matrix_tsv if apply_outputs else None,
        activation_application_summary_tsv=(
            apply_outputs.summary_tsv if apply_outputs else None
        ),
        activation_value_delta_tsv=apply_outputs.value_delta_tsv
        if apply_outputs
        else None,
        narrow_product_writer_expected_diff_acceptance_tsv=(
            narrow_writer_acceptance_tsv
        ),
        narrow_product_writer_expected_diff_acceptance_json=(
            narrow_writer_acceptance_json
        ),
        reconciliation_gallery_html=gallery_outputs.gallery_html
        if gallery_outputs
        else None,
    )


def _summary_row(
    *,
    source_run_id: str,
    status: str,
    shadow_projection_cells_tsv: Path,
    activation_inputs_dir: Path,
    activated_matrix_dir: Path | None,
    gallery_dir: Path | None,
    activation_summary: Mapping[str, str],
    activation_scope_filter: Mapping[str, str],
    application_summary: Mapping[str, str],
    delta_rows: Sequence[Mapping[str, str]],
    activation_outputs: StandardPeakActivationInputOutputs,
    apply_outputs: product_activation.MatrixActivationApplicationOutputs | None,
    narrow_writer_acceptance: Mapping[str, str],
    narrow_writer_acceptance_tsv: Path | None,
    narrow_writer_acceptance_json: Path | None,
    gallery_outputs: backfill_reconciliation_gallery.ReconciliationOutputs | None,
    hard_fail_reasons: str,
    next_action: str,
) -> dict[str, str]:
    delta_effect_counts = Counter(
        text_value(row.get("matrix_value_effect")) for row in delta_rows
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "status": status,
        "source_shadow_projection_tsv": str(shadow_projection_cells_tsv),
        "activation_scope_contract": text_value(
            activation_scope_filter.get("activation_scope_contract"),
        ),
        "activation_scope_filter_status": text_value(
            activation_scope_filter.get("activation_scope_filter_status"),
        ),
        "activation_scope_audit_tsv": text_value(
            activation_scope_filter.get("activation_scope_audit_tsv"),
        ),
        "activation_scope_audit_sha256": text_value(
            activation_scope_filter.get("activation_scope_audit_sha256"),
        ),
        "reintegration_stability_audit_tsv": text_value(
            activation_scope_filter.get("reintegration_stability_audit_tsv"),
        ),
        "reintegration_stability_audit_sha256": text_value(
            activation_scope_filter.get("reintegration_stability_audit_sha256"),
        ),
        "activation_scope_filter_selected_shadow_row_count": text_value(
            activation_scope_filter.get(
                "activation_scope_filter_selected_shadow_row_count",
            ),
        ),
        "activation_scope_filter_excluded_shadow_row_count": text_value(
            activation_scope_filter.get(
                "activation_scope_filter_excluded_shadow_row_count",
            ),
        ),
        "activation_scope_filter_eligible_audit_row_count": text_value(
            activation_scope_filter.get(
                "activation_scope_filter_eligible_audit_row_count",
            ),
        ),
        "standard_peak_activation_inputs_dir": str(activation_inputs_dir),
        "activated_matrix_dir": _path_text(activated_matrix_dir),
        "reconciliation_gallery_dir": _path_text(gallery_dir),
        "selected_activation_row_count": text_value(
            activation_summary.get("selected_activation_row_count"),
        ),
        "skipped_current_written_count": text_value(
            activation_summary.get("skipped_current_written_count"),
        ),
        "skipped_non_accept_count": text_value(
            activation_summary.get("skipped_non_accept_count"),
        ),
        "skipped_non_standard_reason_count": text_value(
            activation_summary.get("skipped_non_standard_reason_count"),
        ),
        "skipped_missing_value_count": text_value(
            activation_summary.get("skipped_missing_value_count"),
        ),
        "activation_acceptance_status": text_value(
            activation_summary.get("activation_acceptance_status"),
        ),
        "activation_acceptance_hard_fail_reasons": hard_fail_reasons,
        "activation_application_status": text_value(
            application_summary.get("application_status"),
        ),
        "activation_output_mode": text_value(
            application_summary.get("activation_output_mode"),
        ),
        "matrix_cells_written": text_value(
            application_summary.get("matrix_cells_written"),
        ),
        "matrix_cells_blanked": text_value(
            application_summary.get("matrix_cells_blanked"),
        ),
        "activation_value_delta_written_count": str(delta_effect_counts["written"]),
        "activation_value_delta_row_count": str(len(delta_rows)),
        "standard_peak_activation_decisions_tsv": str(
            activation_outputs.decisions_tsv,
        ),
        "standard_peak_activation_values_tsv": str(activation_outputs.values_tsv),
        "standard_peak_activation_acceptance_tsv": str(
            activation_outputs.acceptance_tsv,
        ),
        "activated_alignment_matrix_tsv": _path_text(
            apply_outputs.matrix_tsv if apply_outputs else None,
        ),
        "activation_application_summary_tsv": _path_text(
            apply_outputs.summary_tsv if apply_outputs else None,
        ),
        "activation_value_delta_tsv": _path_text(
            apply_outputs.value_delta_tsv if apply_outputs else None,
        ),
        "narrow_product_writer_expected_diff_acceptance_status": text_value(
            narrow_writer_acceptance.get("acceptance_status"),
        ),
        "narrow_product_writer_expected_diff_acceptance_tsv": _path_text(
            narrow_writer_acceptance_tsv,
        ),
        "narrow_product_writer_expected_diff_acceptance_json": _path_text(
            narrow_writer_acceptance_json,
        ),
        "reconciliation_gallery_html": _path_text(
            gallery_outputs.gallery_html if gallery_outputs else None,
        ),
        "matrix_contract_changed": "FALSE",
        "product_behavior_changed": "TRUE"
        if delta_effect_counts["written"] > 0
        else "FALSE",
        "next_action": next_action,
    }


def _write_backfill_policy_from_source_audit(
    *,
    source_audit_tsv: Path,
    reintegration_stability_audit_tsv: Path | None,
    output_dir: Path,
    source_run_id: str,
) -> Path:
    source_rows = tuple(
        read_tsv_required(
            source_audit_tsv,
            BACKFILL_POLICY_SOURCE_AUDIT_REQUIRED_COLUMNS,
        ),
    )
    _validate_scope_schema(
        source_rows,
        source_audit_tsv,
        expected_schema_version=ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION,
    )
    stability_by_sha = _eligible_stability_by_sha(reintegration_stability_audit_tsv)
    policy_rows = tuple(
        _backfill_policy_row(
            row,
            source_run_id=source_run_id,
            stability_by_sha=stability_by_sha,
        )
        for row in source_rows
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    policy_tsv = output_dir / "standard_peak_backfill_policy.tsv"
    write_tsv(
        policy_tsv,
        policy_rows,
        BACKFILL_POLICY_OUTPUT_COLUMNS,
        formatter=format_diagnostic_value,
        lineterminator="\n",
    )
    policy_summary = _backfill_policy_summary_row(
        policy_rows,
        source_run_id=source_run_id,
        source_audit_tsv=source_audit_tsv,
        reintegration_stability_audit_tsv=reintegration_stability_audit_tsv,
        policy_tsv=policy_tsv,
    )
    (output_dir / "standard_peak_backfill_policy_summary.json").write_text(
        json.dumps(policy_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return policy_tsv


def _eligible_stability_by_sha(
    reintegration_stability_audit_tsv: Path | None,
) -> dict[str, Mapping[str, str]]:
    if reintegration_stability_audit_tsv is None:
        return {}
    rows = read_tsv_required(
        reintegration_stability_audit_tsv,
        REINTEGRATION_STABILITY_AUDIT_REQUIRED_COLUMNS,
    )
    _validate_stability_schema(rows, reintegration_stability_audit_tsv)
    eligible_rows = tuple(
        row
        for row in rows
        if text_value(row.get("stability_status")) == "eligible"
        and text_value(row.get("matrix_value_effect")) == "written"
    )
    eligible_shas = tuple(
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in eligible_rows
    )
    duplicates = _duplicates(eligible_shas)
    if duplicates:
        raise ValueError(
            "reintegration stability audit has duplicate eligible "
            "matrix_value_source_row_sha256 values: "
            f"{';'.join(duplicates[:10])}",
        )
    return {
        text_value(row.get("matrix_value_source_row_sha256")): row
        for row in eligible_rows
        if text_value(row.get("matrix_value_source_row_sha256"))
    }


def _backfill_policy_row(
    row: Mapping[str, str],
    *,
    source_run_id: str,
    stability_by_sha: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
    sha = text_value(row.get("matrix_value_source_row_sha256"))
    ready_evidence = list(_ready_evidence_classes(row))
    stability_row = stability_by_sha.get(sha)
    stability_status = (
        text_value(stability_row.get("stability_status")) if stability_row else ""
    )
    if _low_height_stability_ready(row, stability_row):
        ready_evidence.append("low_height_reintegration_stable")
    candidate_evidence = list(_candidate_evidence_classes(row, stability_row))

    if ready_evidence:
        decision = BACKFILL_POLICY_WRITE_READY
        authority = "writer_approved"
        reason = "production_ready_scope:" + ",".join(ready_evidence)
        decision_basis = "approved_writer_scope"
        next_evidence = "none_current_scope_writer_approved"
        blockers = ""
    elif stability_row is not None:
        decision = "detected_flagged"
        authority = "review_only"
        reason = "boundary_stable_candidate_needs_masked_or_product_writer_oracle"
        decision_basis = "candidate_signal_without_writer_oracle"
        next_evidence = "masked_or_product_writer_oracle_required"
        blockers = "missing_writer_approved_oracle"
    else:
        decision = "blocked"
        authority = "blocked"
        reason = _blocked_policy_reason(row)
        decision_basis = reason
        next_evidence = _blocked_policy_next_evidence(row)
        blockers = ";".join(_blocked_policy_blockers(row))

    return {
        "schema_version": BACKFILL_POLICY_SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "feature_family_id": text_value(row.get("feature_family_id")),
        "peak_hypothesis_id": text_value(row.get("peak_hypothesis_id")),
        "sample_id": text_value(row.get("sample_id")),
        "matrix_value_effect": text_value(row.get("matrix_value_effect")),
        "matrix_value_source_row_sha256": sha,
        BACKFILL_POLICY_DECISION_COLUMN: decision,
        "backfill_policy_evidence_class": ",".join(ready_evidence),
        "backfill_policy_authority_status": authority,
        "backfill_policy_reason": reason,
        "backfill_policy_decision_basis": decision_basis,
        "backfill_policy_next_evidence": next_evidence,
        "backfill_policy_candidate_evidence_class": ",".join(candidate_evidence),
        "ready_evidence_classes": ",".join(ready_evidence),
        "stability_status": stability_status,
        "backfill_policy_blockers": blockers,
    }


def _ready_evidence_classes(row: Mapping[str, str]) -> tuple[str, ...]:
    if text_value(row.get("matrix_value_effect")) != "written":
        return ()
    if text_value(row.get("trace_match_status")) != "matched":
        return ()
    evidence: list[str] = []
    for column, evidence_class in (
        ("high_signal_clean_status", "high_signal_clean"),
        ("low_scan_clean_status", "low_scan_clean"),
        ("low_height_clean_status", "low_height_clean"),
        ("low_height_low_scan_clean_status", "low_height_low_scan_clean"),
    ):
        if text_value(row.get(column)) == "eligible":
            evidence.append(evidence_class)
    return tuple(evidence)


def _candidate_evidence_classes(
    row: Mapping[str, str],
    stability_row: Mapping[str, str] | None,
) -> tuple[str, ...]:
    evidence: list[str] = []
    for column, evidence_class in (
        ("high_signal_clean_status", "high_signal_clean"),
        ("low_scan_clean_status", "low_scan_clean"),
        ("low_height_clean_status", "low_height_clean"),
        ("low_height_low_scan_clean_status", "low_height_low_scan_clean"),
    ):
        if text_value(row.get(column)) == "eligible":
            evidence.append(evidence_class)
    if stability_row is not None:
        evidence.append("reintegration_stable")
    return tuple(evidence)


def _low_height_stability_ready(
    row: Mapping[str, str],
    stability_row: Mapping[str, str] | None,
) -> bool:
    if stability_row is None:
        return False
    if text_value(row.get("matrix_value_effect")) != "written":
        return False
    if text_value(row.get("trace_match_status")) != "matched":
        return False
    if text_value(row.get("feature_family_id")) != text_value(
        stability_row.get("feature_family_id"),
    ):
        return False
    height = optional_float(row.get("cell_height"))
    return (
        height is not None
        and height >= 0.0
        and height < MIN_LOW_HEIGHT_REINTEGRATION_STABLE_HEIGHT
    )


def _blocked_policy_reason(row: Mapping[str, str]) -> str:
    if text_value(row.get("matrix_value_effect")) != "written":
        return "not_written_activation_row"
    if text_value(row.get("trace_match_status")) != "matched":
        return "missing_trace_evidence"
    return "no_writer_approved_evidence_class"


def _blocked_policy_next_evidence(row: Mapping[str, str]) -> str:
    if text_value(row.get("matrix_value_effect")) != "written":
        return "activation_candidate_write_required_before_policy"
    if text_value(row.get("trace_match_status")) != "matched":
        return "trace_overlay_or_reintegration_evidence_required"
    return "approved_evidence_class_or_passing_oracle_required"


def _blocked_policy_blockers(row: Mapping[str, str]) -> tuple[str, ...]:
    reason = _blocked_policy_reason(row)
    blockers: list[str] = [reason]
    if reason == "not_written_activation_row":
        blockers.append(
            "matrix_value_effect:"
            + (text_value(row.get("matrix_value_effect")) or "missing"),
        )
        return tuple(blockers)
    if reason == "missing_trace_evidence":
        blockers.extend(
            (
                "trace_match_status:"
                + (text_value(row.get("trace_match_status")) or "missing"),
                "approved_evidence_classes_require_matched_trace",
            ),
        )
        return tuple(blockers)
    for column in (
        "high_signal_clean_status",
        "low_scan_clean_status",
        "low_height_clean_status",
        "low_height_low_scan_clean_status",
    ):
        blockers.append(f"{column}:{text_value(row.get(column)) or 'missing'}")
    blockers.append("reintegration_stability_status:missing_or_ineligible")
    return tuple(blockers)


def _backfill_policy_summary_row(
    rows: Sequence[Mapping[str, str]],
    *,
    source_run_id: str,
    source_audit_tsv: Path,
    reintegration_stability_audit_tsv: Path | None,
    policy_tsv: Path,
) -> dict[str, str]:
    decision_counts = Counter(
        text_value(row.get(BACKFILL_POLICY_DECISION_COLUMN)) for row in rows
    )
    reason_counts = Counter(
        text_value(row.get("backfill_policy_reason")) for row in rows
    )
    next_evidence_counts = Counter(
        text_value(row.get("backfill_policy_next_evidence")) for row in rows
    )
    return {
        "schema_version": BACKFILL_POLICY_SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "source_activation_scope_audit_tsv": str(source_audit_tsv),
        "source_activation_scope_audit_sha256": file_sha256(source_audit_tsv),
        "reintegration_stability_audit_tsv": _path_text(
            reintegration_stability_audit_tsv,
        ),
        "reintegration_stability_audit_sha256": (
            ""
            if reintegration_stability_audit_tsv is None
            else file_sha256(reintegration_stability_audit_tsv)
        ),
        "backfill_policy_tsv": str(policy_tsv),
        "backfill_policy_sha256": file_sha256(policy_tsv),
        "policy_row_count": str(len(rows)),
        "write_ready_row_count": str(decision_counts[BACKFILL_POLICY_WRITE_READY]),
        "detected_flagged_row_count": str(decision_counts["detected_flagged"]),
        "blocked_row_count": str(decision_counts["blocked"]),
        "policy_reason_counts_json": _compact_json_counts(reason_counts),
        "policy_next_evidence_counts_json": _compact_json_counts(
            next_evidence_counts,
        ),
    }


def _activation_scope_request(
    *,
    high_signal_clean_activation_scope_audit_tsv: Path | None,
    low_scan_clean_activation_scope_audit_tsv: Path | None,
    low_height_clean_activation_scope_audit_tsv: Path | None,
    low_height_low_scan_clean_activation_scope_audit_tsv: Path | None,
    low_height_reintegration_stable_activation_scope_audit_tsv: Path | None,
    reintegration_stability_audit_tsv: Path | None,
    activation_policy_tsv: Path | None,
) -> _ActivationScopeRequest:
    requested = tuple(
        path
        for path in (
            activation_policy_tsv,
            high_signal_clean_activation_scope_audit_tsv,
            low_scan_clean_activation_scope_audit_tsv,
            low_height_clean_activation_scope_audit_tsv,
            low_height_low_scan_clean_activation_scope_audit_tsv,
            low_height_reintegration_stable_activation_scope_audit_tsv,
        )
        if path is not None
    )
    if len(requested) > 1:
        raise ValueError(
            "only one activation scope audit may be provided at a time",
        )
    if (
        reintegration_stability_audit_tsv is not None
        and low_height_reintegration_stable_activation_scope_audit_tsv is None
        and activation_policy_tsv is None
    ):
        raise ValueError(
            "--reintegration-stability-audit-tsv requires "
            "--low-height-reintegration-stable-activation-scope-audit-tsv",
        )
    if activation_policy_tsv is not None:
        return _ActivationScopeRequest(
            audit_tsv=activation_policy_tsv,
            contract="backfill_policy_write_ready_rows",
            status_column=BACKFILL_POLICY_DECISION_COLUMN,
            label="backfill-policy",
            no_rows_blocker="no_backfill_policy_write_ready_rows",
            ready_next_action="backfill_policy_writer_production_ready",
            eligible_value=BACKFILL_POLICY_WRITE_READY,
            required_columns=BACKFILL_POLICY_REQUIRED_COLUMNS,
            schema_version=BACKFILL_POLICY_SCHEMA_VERSION,
        )
    if high_signal_clean_activation_scope_audit_tsv is not None:
        return _ActivationScopeRequest(
            audit_tsv=high_signal_clean_activation_scope_audit_tsv,
            contract="high_signal_clean_eligible_activation_rows",
            status_column="high_signal_clean_status",
            label="high-signal-clean",
            no_rows_blocker="no_high_signal_clean_eligible_audit_rows",
            ready_next_action="narrow_high_signal_clean_backfill_production_ready",
        )
    if low_scan_clean_activation_scope_audit_tsv is not None:
        return _ActivationScopeRequest(
            audit_tsv=low_scan_clean_activation_scope_audit_tsv,
            contract="low_scan_clean_eligible_activation_rows",
            status_column="low_scan_clean_status",
            label="low-scan-clean",
            no_rows_blocker="no_low_scan_clean_eligible_audit_rows",
            ready_next_action="narrow_low_scan_clean_backfill_production_ready",
        )
    if low_height_clean_activation_scope_audit_tsv is not None:
        return _ActivationScopeRequest(
            audit_tsv=low_height_clean_activation_scope_audit_tsv,
            contract="low_height_clean_eligible_activation_rows",
            status_column="low_height_clean_status",
            label="low-height-clean",
            no_rows_blocker="no_low_height_clean_eligible_audit_rows",
            ready_next_action="narrow_low_height_clean_backfill_production_ready",
        )
    if low_height_low_scan_clean_activation_scope_audit_tsv is not None:
        return _ActivationScopeRequest(
            audit_tsv=low_height_low_scan_clean_activation_scope_audit_tsv,
            contract="low_height_low_scan_clean_eligible_activation_rows",
            status_column="low_height_low_scan_clean_status",
            label="low-height-low-scan-clean",
            no_rows_blocker="no_low_height_low_scan_clean_eligible_audit_rows",
            ready_next_action=(
                "narrow_low_height_low_scan_clean_backfill_production_ready"
            ),
        )
    if low_height_reintegration_stable_activation_scope_audit_tsv is not None:
        if reintegration_stability_audit_tsv is None:
            raise ValueError(
                "--low-height-reintegration-stable-activation-scope-audit-tsv "
                "requires --reintegration-stability-audit-tsv",
            )
        return _ActivationScopeRequest(
            audit_tsv=low_height_reintegration_stable_activation_scope_audit_tsv,
            contract="low_height_reintegration_stable_eligible_activation_rows",
            status_column=LOW_HEIGHT_REINTEGRATION_STABLE_STATUS_COLUMN,
            label="low-height-reintegration-stable",
            no_rows_blocker=(
                "no_low_height_reintegration_stable_eligible_audit_rows"
            ),
            ready_next_action=(
                "narrow_low_height_reintegration_stable_backfill_production_ready"
            ),
            reintegration_stability_audit_tsv=reintegration_stability_audit_tsv,
        )
    return _ActivationScopeRequest(
        audit_tsv=None,
        contract="unscoped_standard_peak_gate",
        status_column="",
        label="unscoped",
        no_rows_blocker="",
        ready_next_action="review_activation_application_summary",
    )


def _filter_shadow_rows_to_activation_scope(
    shadow_rows: Sequence[Mapping[str, str]],
    *,
    activation_scope_audit_tsv: Path | None,
    reintegration_stability_audit_tsv: Path | None,
    activation_scope_contract: str,
    scope_status_column: str,
    scope_label: str,
    scope_eligible_value: str = "eligible",
    scope_required_columns: tuple[str, ...] | None = None,
    expected_schema_version: str = ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION,
) -> tuple[tuple[Mapping[str, str], ...], dict[str, str], tuple[dict[str, str], ...]]:
    if activation_scope_audit_tsv is None:
        return (
            tuple(shadow_rows),
            {
                "activation_scope_contract": activation_scope_contract,
                "activation_scope_filter_status": "not_requested",
                "activation_scope_audit_tsv": "",
                "activation_scope_audit_sha256": "",
                "reintegration_stability_audit_tsv": "",
                "reintegration_stability_audit_sha256": "",
                "activation_scope_filter_selected_shadow_row_count": str(
                    len(shadow_rows),
                ),
                "activation_scope_filter_excluded_shadow_row_count": "0",
                "activation_scope_filter_eligible_audit_row_count": "",
            },
            (),
        )

    audit_rows = tuple(
        read_tsv_required(
            activation_scope_audit_tsv,
            scope_required_columns
            or _activation_scope_required_columns(
                scope_status_column,
                reintegration_stability_audit_tsv=reintegration_stability_audit_tsv,
            ),
        )
    )
    _validate_scope_schema(
        audit_rows,
        activation_scope_audit_tsv,
        expected_schema_version=expected_schema_version,
    )
    if expected_schema_version == BACKFILL_POLICY_SCHEMA_VERSION:
        _validate_backfill_policy_rows(audit_rows, activation_scope_audit_tsv)
    if reintegration_stability_audit_tsv is not None:
        audit_rows = _with_low_height_reintegration_stable_status(
            audit_rows,
            reintegration_stability_audit_tsv=reintegration_stability_audit_tsv,
            activation_scope_audit_tsv=activation_scope_audit_tsv,
        )
    eligible_audit_rows = tuple(
        row
        for row in audit_rows
        if text_value(row.get(scope_status_column)) == scope_eligible_value
        and text_value(row.get("matrix_value_effect")) == "written"
    )
    eligible_shas = tuple(
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in eligible_audit_rows
    )
    if not eligible_shas:
        raise ValueError(
            f"{scope_label} activation scope audit has no eligible written rows",
        )
    duplicate_audit_shas = _duplicates(eligible_shas)
    if duplicate_audit_shas:
        raise ValueError(
            f"{scope_label} activation scope audit has duplicate eligible "
            "matrix_value_source_row_sha256 values: "
            f"{';'.join(duplicate_audit_shas[:10])}",
        )

    shadow_by_sha: dict[str, list[Mapping[str, str]]] = {}
    for row in shadow_rows:
        row_sha = text_value(row.get("shadow_projection_row_sha256"))
        if row_sha:
            shadow_by_sha.setdefault(row_sha, []).append(row)
    duplicate_shadow_shas = tuple(
        sha for sha in eligible_shas if len(shadow_by_sha.get(sha, ())) > 1
    )
    if duplicate_shadow_shas:
        raise ValueError(
            "shadow projection contains duplicate shadow_projection_row_sha256 "
            f"values: {';'.join(duplicate_shadow_shas[:10])}",
        )
    missing_shadow_shas = tuple(
        sha for sha in eligible_shas if sha not in shadow_by_sha
    )
    if missing_shadow_shas:
        raise ValueError(
            f"{scope_label} activation scope audit references missing "
            "shadow_projection_row_sha256 values: "
            f"{';'.join(missing_shadow_shas[:10])}",
        )

    eligible_sha_set = set(eligible_shas)
    filtered_rows = tuple(
        row
        for row in shadow_rows
        if text_value(row.get("shadow_projection_row_sha256")) in eligible_sha_set
    )
    return (
        filtered_rows,
        {
            "activation_scope_contract": activation_scope_contract,
            "activation_scope_filter_status": "applied",
            "activation_scope_audit_tsv": str(activation_scope_audit_tsv),
            "activation_scope_audit_sha256": file_sha256(
                activation_scope_audit_tsv,
            ),
            "reintegration_stability_audit_tsv": _path_text(
                reintegration_stability_audit_tsv,
            ),
            "reintegration_stability_audit_sha256": (
                ""
                if reintegration_stability_audit_tsv is None
                else file_sha256(reintegration_stability_audit_tsv)
            ),
            "activation_scope_filter_selected_shadow_row_count": str(
                len(filtered_rows),
            ),
            "activation_scope_filter_excluded_shadow_row_count": str(
                len(shadow_rows) - len(filtered_rows),
            ),
            "activation_scope_filter_eligible_audit_row_count": str(
                len(eligible_audit_rows),
            ),
        },
        tuple(dict(row) for row in audit_rows),
    )


def _activation_scope_required_columns(
    scope_status_column: str,
    *,
    reintegration_stability_audit_tsv: Path | None,
) -> tuple[str, ...]:
    if reintegration_stability_audit_tsv is None:
        return (*ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS, scope_status_column)
    return (*ACTIVATION_SCOPE_AUDIT_REQUIRED_COLUMNS, "cell_height")


def _with_low_height_reintegration_stable_status(
    activation_rows: Sequence[Mapping[str, str]],
    *,
    reintegration_stability_audit_tsv: Path,
    activation_scope_audit_tsv: Path,
) -> tuple[dict[str, str], ...]:
    stability_rows = read_tsv_required(
        reintegration_stability_audit_tsv,
        REINTEGRATION_STABILITY_AUDIT_REQUIRED_COLUMNS,
    )
    _validate_stability_schema(stability_rows, reintegration_stability_audit_tsv)
    activation_shas = tuple(
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in activation_rows
        if text_value(row.get("matrix_value_source_row_sha256"))
    )
    duplicate_activation_shas = _duplicates(activation_shas)
    if duplicate_activation_shas:
        raise ValueError(
            "activation scope audit has duplicate matrix_value_source_row_sha256 "
            f"values: {';'.join(duplicate_activation_shas[:10])}",
        )
    activation_by_sha = {
        text_value(row.get("matrix_value_source_row_sha256")): row
        for row in activation_rows
        if text_value(row.get("matrix_value_source_row_sha256"))
    }
    eligible_stability_rows = tuple(
        row
        for row in stability_rows
        if text_value(row.get("stability_status")) == "eligible"
        and text_value(row.get("matrix_value_effect")) == "written"
    )
    eligible_stability_shas = tuple(
        text_value(row.get("matrix_value_source_row_sha256"))
        for row in eligible_stability_rows
    )
    duplicate_stability_shas = _duplicates(eligible_stability_shas)
    if duplicate_stability_shas:
        raise ValueError(
            "reintegration stability audit has duplicate eligible "
            "matrix_value_source_row_sha256 values: "
            f"{';'.join(duplicate_stability_shas[:10])}",
        )
    missing_activation_shas: list[str] = []
    family_mismatch_shas: list[str] = []
    eligible_low_height_shas: set[str] = set()
    for row in eligible_stability_rows:
        sha = text_value(row.get("matrix_value_source_row_sha256"))
        activation = activation_by_sha.get(sha)
        if activation is None:
            missing_activation_shas.append(sha)
            continue
        if text_value(activation.get("matrix_value_effect")) != "written":
            continue
        if text_value(row.get("feature_family_id")) != text_value(
            activation.get("feature_family_id"),
        ):
            family_mismatch_shas.append(sha)
            continue
        height = optional_float(activation.get("cell_height"))
        if (
            height is not None
            and height >= 0.0
            and height < MIN_LOW_HEIGHT_REINTEGRATION_STABLE_HEIGHT
        ):
            eligible_low_height_shas.add(sha)
    if missing_activation_shas:
        raise ValueError(
            "reintegration stability audit references activation rows missing "
            f"from {activation_scope_audit_tsv}: "
            f"{';'.join(missing_activation_shas[:10])}",
        )
    if family_mismatch_shas:
        raise ValueError(
            "reintegration stability audit family ids disagree with activation "
            "scope rows for shas: "
            f"{';'.join(family_mismatch_shas[:10])}",
        )
    return tuple(
        {
            **dict(row),
            LOW_HEIGHT_REINTEGRATION_STABLE_STATUS_COLUMN: (
                "eligible"
                if text_value(row.get("matrix_value_source_row_sha256"))
                in eligible_low_height_shas
                else "ineligible"
            ),
        }
        for row in activation_rows
    )


def _validate_activation_scope_schema(
    rows: Sequence[Mapping[str, str]],
    path: Path,
) -> None:
    _validate_scope_schema(
        rows,
        path,
        expected_schema_version=ACTIVATION_SCOPE_AUDIT_SCHEMA_VERSION,
    )


def _validate_scope_schema(
    rows: Sequence[Mapping[str, str]],
    path: Path,
    *,
    expected_schema_version: str,
) -> None:
    unexpected = sorted(
        {
            text_value(row.get("schema_version"))
            for row in rows
            if text_value(row.get("schema_version")) != expected_schema_version
        },
    )
    if unexpected:
        raise ValueError(
            f"{path}: expected schema_version {expected_schema_version}; "
            f"found {', '.join(unexpected)}",
        )


def _validate_backfill_policy_rows(
    rows: Sequence[Mapping[str, str]],
    path: Path,
) -> None:
    invalid_decisions = sorted(
        {
            text_value(row.get(BACKFILL_POLICY_DECISION_COLUMN))
            for row in rows
            if text_value(row.get(BACKFILL_POLICY_DECISION_COLUMN))
            not in BACKFILL_POLICY_ALLOWED_DECISIONS
        },
    )
    if invalid_decisions:
        raise ValueError(
            f"{path}: invalid backfill_policy_decision values: "
            f"{', '.join(invalid_decisions)}",
        )

    missing_explanation_rows = tuple(
        row
        for row in rows
        if not text_value(row.get("backfill_policy_reason"))
        or not text_value(row.get("backfill_policy_decision_basis"))
        or not text_value(row.get("backfill_policy_next_evidence"))
    )
    if missing_explanation_rows:
        bad_keys = tuple(
            "/".join(_audit_key(row)) for row in missing_explanation_rows
        )
        raise ValueError(
            f"{path}: backfill policy rows missing decision explanations: "
            f"{';'.join(bad_keys[:10])}",
        )

    invalid_write_ready_rows = tuple(
        row
        for row in rows
        if text_value(row.get(BACKFILL_POLICY_DECISION_COLUMN))
        == BACKFILL_POLICY_WRITE_READY
        and (
            text_value(row.get("matrix_value_effect")) != "written"
            or not text_value(row.get("backfill_policy_evidence_class"))
            or text_value(row.get("backfill_policy_authority_status"))
            != "writer_approved"
            or not text_value(row.get("backfill_policy_reason"))
        )
    )
    if invalid_write_ready_rows:
        bad_keys = tuple(
            "/".join(_audit_key(row)) for row in invalid_write_ready_rows
        )
        raise ValueError(
            f"{path}: invalid write_ready policy rows: "
            f"{';'.join(bad_keys[:10])}",
        )


def _validate_stability_schema(
    rows: Sequence[Mapping[str, str]],
    path: Path,
) -> None:
    unexpected = sorted(
        {
            text_value(row.get("schema_version"))
            for row in rows
            if text_value(row.get("schema_version"))
            != REINTEGRATION_STABILITY_AUDIT_SCHEMA_VERSION
        },
    )
    if unexpected:
        raise ValueError(
            f"{path}: expected schema_version "
            f"{REINTEGRATION_STABILITY_AUDIT_SCHEMA_VERSION}; "
            f"found {', '.join(unexpected)}",
        )


def _narrow_product_writer_expected_diff_acceptance_row(
    *,
    activation_scope_audit_rows: Sequence[Mapping[str, str]],
    product_activation_value_delta_rows: Sequence[Mapping[str, str]],
    activation_scope_audit_tsv: Path | None,
    reintegration_stability_audit_tsv: Path | None,
    product_activation_value_delta_tsv: Path,
    application_summary: Mapping[str, str],
    source_run_id: str,
    scope_status_column: str,
    scope_eligible_value: str,
    expected_scope: str,
    no_rows_blocker: str,
    ready_next_action: str,
) -> dict[str, str]:
    eligible_audit_keys = {
        _audit_key(row)
        for row in activation_scope_audit_rows
        if text_value(row.get(scope_status_column)) == scope_eligible_value
        and text_value(row.get("matrix_value_effect")) == "written"
    }
    all_audit_written_keys = {
        _audit_key(row)
        for row in activation_scope_audit_rows
        if text_value(row.get("matrix_value_effect")) == "written"
    }
    product_delta_keys = [
        _delta_key(row) for row in product_activation_value_delta_rows
    ]
    product_delta_key_set = set(product_delta_keys)
    product_written_delta_rows = tuple(
        row
        for row in product_activation_value_delta_rows
        if text_value(row.get("matrix_value_effect")) == "written"
    )
    duplicate_delta_key_count = len(product_delta_keys) - len(product_delta_key_set)
    missing_delta_keys = eligible_audit_keys - product_delta_key_set
    unexpected_delta_keys = product_delta_key_set - all_audit_written_keys
    non_eligible_delta_keys = product_delta_key_set - eligible_audit_keys
    not_written_delta_count = sum(
        1
        for row in product_activation_value_delta_rows
        if text_value(row.get("matrix_value_effect")) != "written"
    )
    unchanged_delta_count = sum(
        1
        for row in product_activation_value_delta_rows
        if text_value(row.get("value_changed")) != "TRUE"
    )
    blank_activated_value_count = sum(
        1
        for row in product_activation_value_delta_rows
        if not text_value(row.get("activated_matrix_value"))
    )
    matrix_cells_written = _int_value(application_summary.get("matrix_cells_written"))
    blockers = _narrow_product_writer_acceptance_blockers(
        eligible_audit_row_count=len(eligible_audit_keys),
        product_delta_row_count=len(product_activation_value_delta_rows),
        product_written_delta_row_count=len(product_written_delta_rows),
        duplicate_delta_key_count=duplicate_delta_key_count,
        missing_delta_count=len(missing_delta_keys),
        unexpected_delta_count=len(unexpected_delta_keys),
        non_eligible_delta_count=len(non_eligible_delta_keys),
        not_written_delta_count=not_written_delta_count,
        unchanged_delta_count=unchanged_delta_count,
        blank_activated_value_count=blank_activated_value_count,
        matrix_cells_written=matrix_cells_written,
        application_status=text_value(application_summary.get("application_status")),
        no_rows_blocker=no_rows_blocker,
    )
    acceptance_status = "pass" if not blockers else "fail"
    return {
        "schema_version": (
            NARROW_PRODUCT_WRITER_EXPECTED_DIFF_ACCEPTANCE_SCHEMA_VERSION
        ),
        "source_run_id": source_run_id,
        "acceptance_status": acceptance_status,
        "readiness_tier": "production_ready" if acceptance_status == "pass" else "",
        "expected_scope": expected_scope,
        "activation_scope_audit_tsv": _path_text(activation_scope_audit_tsv),
        "activation_scope_audit_sha256": (
            "" if activation_scope_audit_tsv is None else file_sha256(
                activation_scope_audit_tsv,
            )
        ),
        "reintegration_stability_audit_tsv": _path_text(
            reintegration_stability_audit_tsv,
        ),
        "reintegration_stability_audit_sha256": (
            ""
            if reintegration_stability_audit_tsv is None
            else file_sha256(reintegration_stability_audit_tsv)
        ),
        "product_activation_value_delta_tsv": str(product_activation_value_delta_tsv),
        "product_activation_value_delta_sha256": file_sha256(
            product_activation_value_delta_tsv,
        ),
        "activation_application_status": text_value(
            application_summary.get("application_status"),
        ),
        "matrix_cells_written": str(matrix_cells_written),
        "eligible_audit_row_count": str(len(eligible_audit_keys)),
        "product_delta_row_count": str(len(product_activation_value_delta_rows)),
        "product_written_delta_row_count": str(len(product_written_delta_rows)),
        "duplicate_delta_key_count": str(duplicate_delta_key_count),
        "missing_delta_row_count": str(len(missing_delta_keys)),
        "unexpected_delta_row_count": str(len(unexpected_delta_keys)),
        "non_eligible_delta_row_count": str(len(non_eligible_delta_keys)),
        "not_written_delta_row_count": str(not_written_delta_count),
        "unchanged_delta_row_count": str(unchanged_delta_count),
        "blank_activated_value_count": str(blank_activated_value_count),
        "blocking_reasons": ";".join(blockers),
        "product_surface_changed": "TRUE",
        "next_action": (
            f"claim_{ready_next_action}"
            if acceptance_status == "pass"
            else "review_narrow_product_writer_expected_diff_failures"
        ),
    }


def _narrow_product_writer_acceptance_blockers(
    *,
    eligible_audit_row_count: int,
    product_delta_row_count: int,
    product_written_delta_row_count: int,
    duplicate_delta_key_count: int,
    missing_delta_count: int,
    unexpected_delta_count: int,
    non_eligible_delta_count: int,
    not_written_delta_count: int,
    unchanged_delta_count: int,
    blank_activated_value_count: int,
    matrix_cells_written: int,
    application_status: str,
    no_rows_blocker: str = "no_high_signal_clean_eligible_audit_rows",
) -> tuple[str, ...]:
    blockers: list[str] = []
    if eligible_audit_row_count == 0:
        blockers.append(no_rows_blocker)
    if product_delta_row_count == 0:
        blockers.append("no_product_delta_rows")
    if product_written_delta_row_count != eligible_audit_row_count:
        blockers.append("product_written_delta_count_mismatch")
    if matrix_cells_written != eligible_audit_row_count:
        blockers.append("matrix_written_count_mismatch")
    if application_status != "applied":
        blockers.append("activation_application_not_applied")
    if duplicate_delta_key_count:
        blockers.append("duplicate_product_delta_keys")
    if missing_delta_count:
        blockers.append("eligible_audit_rows_missing_from_product_delta")
    if unexpected_delta_count:
        blockers.append("product_delta_rows_missing_from_scope_audit")
    if non_eligible_delta_count:
        blockers.append("product_delta_contains_noneligible_rows")
    if not_written_delta_count:
        blockers.append("product_delta_contains_non_written_rows")
    if unchanged_delta_count:
        blockers.append("product_delta_contains_unchanged_rows")
    if blank_activated_value_count:
        blockers.append("product_delta_contains_blank_activated_values")
    return tuple(blockers)


def _delta_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        text_value(row.get("peak_hypothesis_id")),
        text_value(row.get("sample_id")),
        text_value(row.get("matrix_value_source_row_sha256")),
    )


def _audit_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        text_value(row.get("peak_hypothesis_id")),
        text_value(row.get("sample_id")),
        text_value(row.get("matrix_value_source_row_sha256")),
    )


def _duplicates(values: Sequence[str]) -> tuple[str, ...]:
    counts = Counter(value for value in values if value)
    return tuple(value for value, count in counts.items() if count > 1)


def _compact_json_counts(counts: Counter[str]) -> str:
    return json.dumps(
        {key: counts[key] for key in sorted(counts) if key},
        separators=(",", ":"),
        sort_keys=True,
    )


def _seed_guard_write_attribution_failures(
    rows: Sequence[Mapping[str, str]],
) -> tuple[str, ...]:
    failures: list[str] = []
    for row in rows:
        if text_value(row.get("write_authority_status")) != (
            "blocked_unattributed_write"
        ):
            continue
        peak_hypothesis_id = text_value(row.get("peak_hypothesis_id"))
        sample_scope = text_value(row.get("sample_scope"))
        failures.append(f"blocked_unattributed_write:{peak_hypothesis_id}/{sample_scope}")
    return tuple(failures)


def _append_failure_reasons(
    existing: str,
    failures: Sequence[str],
) -> str:
    parts = [part for part in existing.split(";") if part]
    parts.extend(failures)
    return ";".join(parts)


def _validate_shadow_current_matrix_claims(
    shadow_rows: Sequence[Mapping[str, str]],
    *,
    alignment_matrix_tsv: Path,
    alignment_matrix_identity_tsv: Path,
) -> None:
    current_claims = tuple(
        row
        for row in shadow_rows
        if text_value(row.get("current_matrix_written")) == "TRUE"
    )
    if not current_claims:
        return
    matrix_values = _current_matrix_values_by_family_sample(
        alignment_matrix_tsv=alignment_matrix_tsv,
        alignment_matrix_identity_tsv=alignment_matrix_identity_tsv,
    )
    stale: list[str] = []
    for row in current_claims:
        family_id = text_value(row.get("feature_family_id"))
        peak_hypothesis_id = text_value(row.get("peak_hypothesis_id"))
        sample = text_value(row.get("sample_stem"))
        keys = tuple(
            dict.fromkeys(
                key for key in (peak_hypothesis_id, family_id) if key
            ),
        )
        actual = None
        for key in keys:
            matrix_key = (key, sample)
            if matrix_key in matrix_values:
                actual = matrix_values[matrix_key]
                break
        if actual is None or not text_value(actual):
            stale.append(f"{family_id}/{sample}")
    if stale:
        preview = ";".join(stale[:10])
        suffix = f";+{len(stale) - 10} more" if len(stale) > 10 else ""
        raise ValueError(
            "shadow_projection current_matrix_written claims do not match "
            "alignment_matrix.tsv values: "
            f"{preview}{suffix}",
        )


def _current_matrix_values_by_family_sample(
    *,
    alignment_matrix_tsv: Path,
    alignment_matrix_identity_tsv: Path,
) -> dict[tuple[str, str], str]:
    matrix_header, matrix_rows = read_tsv_with_header(alignment_matrix_tsv)
    identity_rows = read_tsv_required(
        alignment_matrix_identity_tsv,
        ("matrix_row_index", "peak_hypothesis_id"),
    )
    sample_columns = tuple(
        column for column in matrix_header if column not in {"Mz", "RT"}
    )
    values: dict[tuple[str, str], str] = {}
    for identity in identity_rows:
        row_index = positive_int(identity.get("matrix_row_index"))
        if row_index is None or row_index > len(matrix_rows):
            continue
        matrix_row = matrix_rows[row_index - 1]
        for row_key in identity_family_keys(identity):
            for sample in sample_columns:
                values[(row_key, sample)] = matrix_row.get(sample, "")
    return values


def _single_row(rows: Sequence[dict[str, str]]) -> dict[str, str]:
    if not rows:
        return {}
    return dict(rows[0])


def _int_value(value: object) -> int:
    try:
        return int(text_value(value) or "0")
    except ValueError:
        return 0


def _path_text(path: Path | None) -> str:
    return "" if path is None else str(path)
