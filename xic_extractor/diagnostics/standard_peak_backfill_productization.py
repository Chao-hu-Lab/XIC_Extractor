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
    format_diagnostic_value,
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
    write_standard_peak_activation_input_outputs,
)
from xic_extractor.tabular_io import (
    identity_family_keys,
    positive_int,
    read_tsv_with_header,
)

SCHEMA_VERSION = "standard_peak_backfill_productization_v0"

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
    "reconciliation_gallery_html",
    "matrix_contract_changed",
    "product_behavior_changed",
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
    reconciliation_gallery_html: Path | None = None


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
    activation_index = build_standard_peak_activation_inputs(
        shadow_rows,
        source_shadow_projection_sha256=canonical_shadow_projection_sha256(
            shadow_rows,
        ),
        source_run_id=source_run_id,
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
        if text_value(application_summary.get("application_status")) != "applied":
            status = "fail"
            next_action = "review_activation_application_failure"
        else:
            next_action = "review_activation_application_summary"

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
        application_summary=application_summary,
        delta_rows=delta_rows,
        activation_outputs=activation_outputs,
        apply_outputs=apply_outputs,
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
    application_summary: Mapping[str, str],
    delta_rows: Sequence[Mapping[str, str]],
    activation_outputs: StandardPeakActivationInputOutputs,
    apply_outputs: product_activation.MatrixActivationApplicationOutputs | None,
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
        "reconciliation_gallery_html": _path_text(
            gallery_outputs.gallery_html if gallery_outputs else None,
        ),
        "matrix_contract_changed": "FALSE",
        "product_behavior_changed": "TRUE"
        if delta_effect_counts["written"] > 0
        else "FALSE",
        "next_action": next_action,
    }


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
