"""Build matrix-only activation inputs from standard-peak shadow projection."""

from __future__ import annotations

import hashlib
import json
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

SCHEMA_VERSION = "standard_peak_shadow_activation_inputs_v1"

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
    "standard_peak_gate_status",
    "standard_peak_gate_failure_reasons",
    "activation_acceptance_status",
    "activation_acceptance_hard_fail_reasons",
    "activation_acceptance_max_allowed_product_affecting_rows",
    "activation_decisions_tsv",
    "activation_values_tsv",
    "activation_acceptance_tsv",
    "next_action",
)


@dataclass(frozen=True)
class StandardPeakActivationInputIndex:
    decisions: tuple[dict[str, str], ...]
    values: tuple[dict[str, str], ...]
    acceptance: dict[str, str]
    summary: dict[str, str]


@dataclass(frozen=True)
class StandardPeakActivationInputOutputs:
    decisions_tsv: Path
    values_tsv: Path
    acceptance_tsv: Path
    summary_tsv: Path
    summary_json: Path


def build_standard_peak_activation_inputs(
    shadow_projection_rows: Iterable[Mapping[str, str]],
    *,
    source_shadow_projection_sha256: str,
    source_run_id: str = "",
    required_same_peak_reason: str = STANDARD_PEAK_GATE_MS1_SUPPORT_REASON,
) -> StandardPeakActivationInputIndex:
    rows = tuple(dict(row) for row in shadow_projection_rows)
    decisions: list[dict[str, str]] = []
    values: list[dict[str, str]] = []
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
        "next_action": _next_action(decisions_tuple, acceptance),
    }
    return StandardPeakActivationInputIndex(
        decisions=decisions_tuple,
        values=values_tuple,
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
    summary = dict(index.summary)
    summary.update(
        {
            "activation_decisions_tsv": str(decisions_path),
            "activation_values_tsv": str(values_path),
            "activation_acceptance_tsv": str(acceptance_path),
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
        summary_tsv=summary_path,
        summary_json=summary_json_path,
    )


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
