from __future__ import annotations

import csv
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .models import (
    CellEvidenceResult,
    IdentityDecisionSummary,
    SeedGateResult,
)
from .row_evaluator import IdentityCoherenceRowResult
from .schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)
from .tags import format_fragment_tags


@dataclass(frozen=True)
class IdentityCoherenceOutputRecord:
    seed_gate: SeedGateResult
    row_result: IdentityCoherenceRowResult


@dataclass(frozen=True)
class IdentityCoherenceOutputContext:
    command: str
    mode: str
    input_source: str
    input_hashes: tuple[tuple[str, str], ...] = ()
    control_manifest_path: str = "not_provided"
    raw_xic_request_count: int | None = None
    xic_point_count: int | None = None
    projected_85raw_identity_request_count: int | None = None
    max_projected_85raw_identity_xic_requests: int | None = None
    max_infrastructure_blocked_fraction: float = 0.05
    firewall_fixture_status: str = "not_assessed"
    spawn_payload_smoke_status: str = "not_assessed"

    def __post_init__(self) -> None:
        blocked_fraction = _validate_nonnegative_float(
            self.max_infrastructure_blocked_fraction,
            "max_infrastructure_blocked_fraction",
        )
        if blocked_fraction > 1.0:
            raise ValueError("max_infrastructure_blocked_fraction must be <= 1")
        object.__setattr__(
            self,
            "max_infrastructure_blocked_fraction",
            blocked_fraction,
        )
        for field_name in (
            "raw_xic_request_count",
            "xic_point_count",
            "projected_85raw_identity_request_count",
            "max_projected_85raw_identity_xic_requests",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_optional_nonnegative_int(
                    getattr(self, field_name),
                    field_name,
                ),
            )


@dataclass(frozen=True)
class IdentityCoherenceOutputPaths:
    requests_tsv: Path
    decisions_tsv: Path
    cell_evidence_tsv: Path
    controls_tsv: Path
    summary_md: Path


def project_request_row(seed_gate: SeedGateResult) -> dict[str, str]:
    request = seed_gate.resolved_request
    _validate_frozen_request_status(request)
    identity = request.identity
    match = seed_gate.candidate_match
    values = {
        "request_id": request.request_id,
        "decision_id": request.decision_id,
        "seed_candidate_id": request.seed_candidate_id,
        "seed_sample": request.seed_sample,
        "fragment_observation_mode": identity.fragment_observation_mode,
        "precursor_mz": identity.precursor_mz,
        "product_mz": identity.product_mz,
        "fragment_tags": format_fragment_tags(identity.fragment_tags),
        "fragment_tag_match_policy": identity.fragment_tag_match_policy,
        "fragment_profile_id": identity.fragment_profile_id,
        "fragment_profile_hash": identity.fragment_profile_hash,
        "precursor_tolerance_ppm": identity.precursor_tolerance_ppm,
        "product_tolerance_ppm": identity.product_tolerance_ppm,
        "cid_observed_loss_da": identity.mode_constraint.cid_observed_loss_da,
        "cid_observed_loss_tolerance_ppm": (
            identity.mode_constraint.cid_observed_loss_tolerance_ppm
        ),
        "request_identity_completeness_status": (
            request.request_identity_completeness_status
        ),
        "request_candidate_identity_status": (
            request.request_candidate_identity_status
        ),
        "precursor_error_ppm": match.precursor_error_ppm,
        "product_error_ppm": match.product_error_ppm,
        "cid_observed_loss_error_ppm": match.cid_observed_loss_error_ppm,
        "cid_observed_loss_error_da": match.cid_observed_loss_error_da,
        "request_builder_flags": request.request_builder_flags,
    }
    return _project_columns(IDENTITY_COHERENCE_REQUEST_COLUMNS, values)


def project_decision_row(summary: IdentityDecisionSummary) -> dict[str, str]:
    _validate_decision_summary(summary)
    values = {
        "decision_id": summary.decision_id,
        "identity_family_id": summary.identity_family_id,
        "seed_candidate_id": summary.seed_candidate_id,
        "seed_sample": summary.seed_sample,
        "seed_gate_class": summary.seed_gate_class,
        "decision": summary.decision,
        "decision_reason": summary.decision_reason,
        "request_identity_completeness_status": (
            summary.request_identity_completeness_status
        ),
        "request_candidate_identity_status": (
            summary.request_candidate_identity_status
        ),
        "total_coherent_sample_count": summary.total_coherent_sample_count,
        "non_seed_coherent_sample_count": summary.non_seed_coherent_sample_count,
        "tier12_non_seed_identity_sample_count": (
            summary.tier12_non_seed_identity_sample_count
        ),
        "tier1_fragment_confirmed_sample_count": (
            summary.tier1_fragment_confirmed_sample_count
        ),
        "tier2_shape_supported_sample_count": (
            summary.tier2_shape_supported_sample_count
        ),
        "tier2_seed_shape_fallback_sample_count": (
            summary.tier2_seed_shape_fallback_sample_count
        ),
        "tier3_width_only_sample_count": summary.tier3_width_only_sample_count,
        "min_total_coherent_samples": summary.min_total_coherent_samples,
        "min_non_seed_coherent_samples": summary.min_non_seed_coherent_samples,
        "min_non_seed_tier12_identity_samples": (
            summary.min_non_seed_tier12_identity_samples
        ),
        "weak_basis_reason": summary.weak_basis_reason,
        "shape_reference_basis": summary.shape_reference_basis,
        "shape_reference_candidate_id": summary.shape_reference_candidate_id,
        "prototype_width_sec": summary.prototype_width_sec,
        "center_rt_sec": summary.center.center_rt_sec,
        "center_rt_source": summary.center_rt_source,
        "coherent_fraction": summary.coherent_fraction,
        "infrastructure_blocked_sample_count": (
            summary.infrastructure_blocked_sample_count
        ),
        "data_quality_reject_sample_count": (
            summary.data_quality_reject_sample_count
        ),
        "forbidden_evidence_used": summary.forbidden_evidence_used,
    }
    return _project_columns(IDENTITY_COHERENCE_DECISION_COLUMNS, values)


def project_cell_evidence_row(cell: CellEvidenceResult) -> dict[str, str]:
    values = {
        "decision_id": cell.decision_id,
        "identity_family_id": cell.identity_family_id,
        "sample_id": cell.sample_id,
        "candidate_id": cell.candidate_id,
        "cell_assessment_status": cell.cell_assessment_status,
        "cell_identity_tier": cell.cell_identity_tier,
        "cell_identity_basis": cell.cell_identity_basis,
        "fragment_observation_mode": cell.fragment_observation_mode,
        "fragment_match_status": cell.fragment_match_status,
        "fragment_tags_supported": format_fragment_tags(
            cell.fragment_tags_supported,
        ),
        "rt_delta_center_sec": cell.rt_delta_center_sec,
        "rt_gate_status": cell.rt_gate_status,
        "shape_status": cell.shape_status,
        "shape_similarity_cosine": cell.shape_similarity_cosine,
        "shape_reference_basis": cell.shape_reference_basis,
        "shape_reference_candidate_id": cell.shape_reference_candidate_id,
        "shape_fallback_used": cell.shape_fallback_used,
        "shape_audit_status": cell.shape_audit_status,
        "width_status": cell.width_status,
        "width_ratio_to_prototype": cell.width_ratio_to_prototype,
        "baseline_audit_status": cell.baseline_audit_status,
        "area_height_status": cell.area_height_status,
        "non_rt_identity_result": cell.non_rt_identity_result,
        "coherent_count_contribution": cell.coherent_count_contribution,
        "tier12_count_contribution": cell.tier12_count_contribution,
        "blocked_reason": cell.blocked_reason,
        "data_quality_reason": cell.data_quality_reason,
        "forbidden_evidence_seen": cell.forbidden_evidence_seen,
    }
    return _project_columns(IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS, values)


def project_control_row(row: Mapping[str, object]) -> dict[str, str]:
    return _project_columns(IDENTITY_COHERENCE_CONTROL_COLUMNS, row)


def write_identity_coherence_requests_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(_validate_output_record(record) for record in records)
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_REQUEST_COLUMNS,
        [project_request_row(record.seed_gate) for record in validated],
    )


def write_identity_coherence_decisions_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(_validate_output_record(record) for record in records)
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_DECISION_COLUMNS,
        [project_decision_row(record.row_result.decision) for record in validated],
    )


def write_identity_coherence_cell_evidence_tsv(
    path: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
) -> Path:
    validated = tuple(_validate_output_record(record) for record in records)
    rows: list[dict[str, str]] = []
    for record in validated:
        rows.extend(
            project_cell_evidence_row(cell)
            for cell in record.row_result.cells
        )
    return _write_tsv(path, IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS, rows)


def write_identity_coherence_controls_tsv(
    path: Path,
    rows: Sequence[Mapping[str, object]],
) -> Path:
    return _write_tsv(
        path,
        IDENTITY_COHERENCE_CONTROL_COLUMNS,
        [project_control_row(row) for row in rows],
    )


def write_identity_coherence_outputs(
    output_dir: Path,
    records: Sequence[IdentityCoherenceOutputRecord],
    *,
    context: IdentityCoherenceOutputContext,
    control_rows: Sequence[Mapping[str, object]] = (),
) -> IdentityCoherenceOutputPaths:
    validated = tuple(_validate_output_record(record) for record in records)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = IdentityCoherenceOutputPaths(
        requests_tsv=output_dir / "untargeted_identity_coherence_requests.tsv",
        decisions_tsv=output_dir / "untargeted_identity_coherence_decisions.tsv",
        cell_evidence_tsv=(
            output_dir / "untargeted_identity_coherence_cell_evidence.tsv"
        ),
        controls_tsv=output_dir / "untargeted_identity_coherence_controls.tsv",
        summary_md=output_dir / "untargeted_identity_coherence_summary.md",
    )
    write_identity_coherence_requests_tsv(paths.requests_tsv, validated)
    write_identity_coherence_decisions_tsv(paths.decisions_tsv, validated)
    write_identity_coherence_cell_evidence_tsv(paths.cell_evidence_tsv, validated)
    write_identity_coherence_controls_tsv(paths.controls_tsv, control_rows)
    paths.summary_md.write_text(
        render_identity_coherence_summary(
            validated,
            context=context,
            control_rows=control_rows,
        ),
        encoding="utf-8",
    )
    return paths


def render_identity_coherence_summary(
    records: Sequence[IdentityCoherenceOutputRecord],
    *,
    context: IdentityCoherenceOutputContext,
    control_rows: Sequence[Mapping[str, object]] = (),
) -> str:
    validated = tuple(_validate_output_record(record) for record in records)
    decision_rows = [record.row_result.decision for record in validated]
    cell_rows = [
        cell
        for record in validated
        for cell in record.row_result.cells
    ]
    request_rows = [record.seed_gate.resolved_request for record in validated]
    projected_85raw = (
        context.projected_85raw_identity_request_count
        if context.projected_85raw_identity_request_count is not None
        else "not_assessed"
    )
    raw_xic_requests = (
        context.raw_xic_request_count
        if context.raw_xic_request_count is not None
        else "not_assessed"
    )
    xic_points = (
        context.xic_point_count
        if context.xic_point_count is not None
        else "not_assessed"
    )
    forbidden_seen_count = sum(
        1 for row in decision_rows if row.forbidden_evidence_seen
    )
    tier1_count = _sum_decision_field(
        decision_rows,
        "tier1_fragment_confirmed_sample_count",
    )
    tier2_count = _sum_decision_field(
        decision_rows,
        "tier2_shape_supported_sample_count",
    )
    tier2_fallback_count = _sum_decision_field(
        decision_rows,
        "tier2_seed_shape_fallback_sample_count",
    )
    tier3_count = _sum_decision_field(
        decision_rows,
        "tier3_width_only_sample_count",
    )
    infrastructure_blocked_count = _sum_decision_field(
        decision_rows,
        "infrastructure_blocked_sample_count",
    )
    data_quality_reject_count = _sum_decision_field(
        decision_rows,
        "data_quality_reject_sample_count",
    )
    min_total = _first_threshold(decision_rows, "min_total_coherent_samples")
    min_non_seed = _first_threshold(
        decision_rows,
        "min_non_seed_coherent_samples",
    )
    min_tier12 = _first_threshold(
        decision_rows,
        "min_non_seed_tier12_identity_samples",
    )

    lines = [
        "# Untargeted Identity Coherence Summary",
        "",
        "This diagnostic is non-mutating. It reports identity-family evidence only; "
        "it may retrieve RAW/XIC traces for diagnostic identity evidence, but it "
        "does not mutate Backfill or final-matrix outputs and does not perform "
        "final-matrix filtering, background filtering, area correction, "
        "normalization, or statistics.",
        "",
        "## Run Context",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| command | `{context.command}` |",
        f"| mode | `{context.mode}` |",
        f"| input_source | `{context.input_source}` |",
        f"| input_row_count | {len(validated)} |",
        f"| control_manifest_path | `{context.control_manifest_path}` |",
        "",
        "## Input Hashes",
        "",
    ]
    lines.extend(_hash_lines(context.input_hashes))
    lines.extend(
        [
            "",
            "## Request Status Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(
                str(_enum_value(row.request_identity_completeness_status))
                for row in request_rows
            ),
            "request_identity_completeness_status",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                str(_enum_value(row.request_candidate_identity_status))
                for row in request_rows
            ),
            "request_candidate_identity_status",
        )
    )
    lines.extend(
        [
            "",
            "## Evidence Firewall",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            "| `promotion_used_forbidden_evidence` | `false` |",
            (
                "| `forbidden_evidence_seen_count` | "
                f"{forbidden_seen_count} |"
            ),
            "",
            "## Seed Gate Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(str(_enum_value(row.seed_gate_class)) for row in decision_rows),
            "seed_gate_class",
        )
    )
    lines.extend(
        [
            "",
            "## Decision Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(str(_enum_value(row.decision)) for row in decision_rows),
            "decision",
        )
    )
    lines.extend(
        [
            "",
            "## Tier Support Counts",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            f"| tier1_fragment_confirmed_sample_count | {tier1_count} |",
            f"| tier2_shape_supported_sample_count | {tier2_count} |",
            f"| tier2_seed_shape_fallback_sample_count | {tier2_fallback_count} |",
            f"| tier3_width_only_sample_count | {tier3_count} |",
            "",
            "## RT-Only Candidate Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(
                str(_enum_value(cell.cell_identity_tier))
                for cell in cell_rows
                if _enum_value(cell.cell_identity_tier) == "rt_only"
            ),
            "rt_only_cell_identity_tier",
        )
    )
    lines.extend(
        [
            "",
            "## Shape And Width Review",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(
                str(_enum_value(cell.shape_reference_basis))
                for cell in cell_rows
            ),
            "shape_reference_basis",
        )
    )
    lines.extend(
        _counter_table(
            Counter(str(_enum_value(cell.width_status)) for cell in cell_rows),
            "width_status",
        )
    )
    lines.extend(
        [
            "",
            "## Per-Sample Evidence Coverage",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            f"| assessed_non_seed_cell_count | {len(cell_rows)} |",
            (
                "| missing_shape_basis_count | "
                f"{_cell_status_count(cell_rows, 'shape_status', 'not_assessed')} |"
            ),
            (
                "| missing_width_basis_count | "
                f"{_cell_status_count(cell_rows, 'width_status', 'not_assessed')} |"
            ),
            "",
            "## Infrastructure And Data Quality",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            f"| infrastructure_blocked_sample_count | {infrastructure_blocked_count} |",
            f"| data_quality_reject_sample_count | {data_quality_reject_count} |",
            "",
            "## Threshold Count And Fraction Summaries",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| min_total_coherent_samples | {min_total} |",
            f"| min_non_seed_coherent_samples | {min_non_seed} |",
            f"| min_non_seed_tier12_identity_samples | {min_tier12} |",
            "",
            "## Weak Basis Counts",
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(str(_enum_value(row.weak_basis_reason)) for row in decision_rows),
            "weak_basis_reason",
        )
    )
    positive_rows = [
        row
        for row in control_rows
        if _format_tsv_value(row.get("control_type")) == "positive_targeted_istd"
    ]
    positive_pass_count = sum(
        1 for row in positive_rows if _control_pass_is_true(row.get("control_pass"))
    )
    positive_fraction = (
        "not_assessed"
        if not positive_rows
        else f"{positive_pass_count / len(positive_rows):.12g}"
    )
    decoy_rows = [
        row
        for row in control_rows
        if _format_tsv_value(row.get("control_type")) == "identity_decoy"
    ]
    decoy_correctly_rejected_count = sum(
        1 for row in decoy_rows if _control_pass_is_true(row.get("control_pass"))
    )
    decoy_correctly_rejected_value: int | str = (
        "not_assessed"
        if not decoy_rows
        else decoy_correctly_rejected_count
    )
    lines.extend(
        [
            "",
            "## Identity Controls",
            "",
            (
                "Control fields validate identity diagnostic behavior only; they "
                "do not promote identities or filter the final matrix."
            ),
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("control_type")) for row in control_rows
            ),
            "control_type",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("control_status"))
                for row in control_rows
            ),
            "control_status",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("control_pass")) for row in control_rows
            ),
            "control_pass",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("positive_control_mapping_status"))
                for row in control_rows
            ),
            "positive_control_mapping_status",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("decoy_generation_method"))
                for row in decoy_rows
            ),
            "decoy_generation_method",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("control_failure_reason"))
                for row in control_rows
                if _format_tsv_value(row.get("control_failure_reason"))
            ),
            "control_failure_reason",
        )
    )
    lines.extend(
        [
            "| Metric | Value |",
            "| --- | ---: |",
            f"| positive_control_pass_fraction | {positive_fraction} |",
            (
                "| decoy_correctly_rejected_count | "
                f"{decoy_correctly_rejected_value} |"
            ),
            "",
            "",
            "## Engineering Go / No-Go",
            "",
        ]
    )
    lines.extend(
        _engineering_go_no_go_rows(
            decision_rows,
            context=context,
            assessed_sample_total=_total_assessed_sample_count(decision_rows),
        )
    )
    lines.extend(
        [
            "## Cost Counters",
            "",
            "| Counter | Value |",
            "| --- | ---: |",
            f"| raw_xic_request_count | {raw_xic_requests} |",
            f"| xic_point_count | {xic_points} |",
            f"| projected_85raw_identity_request_count | {projected_85raw} |",
            "",
            "## Writer Contract Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
            "| forbidden_evidence_used | enforced: writer raises before emission |",
            "| schema_projection | Proceed when TSV headers match schema constants |",
            (
                "| controls | evaluated rows are rendered; identity decisions "
                "remain immutable |"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _validate_frozen_request_status(request: object) -> None:
    completeness = _enum_value(request.request_identity_completeness_status)
    candidate_status = _enum_value(request.request_candidate_identity_status)
    if (
        completeness == RequestIdentityCompletenessStatus.COMPLETE.value
        and candidate_status == RequestCandidateIdentityStatus.NOT_ASSESSED.value
    ):
        raise ValueError("complete request cannot be emitted as not_assessed")


def _validate_decision_summary(summary: IdentityDecisionSummary) -> None:
    if summary.forbidden_evidence_used:
        raise ValueError("forbidden_evidence_used cannot be emitted")


def _validate_output_record(
    record: IdentityCoherenceOutputRecord,
) -> IdentityCoherenceOutputRecord:
    request = record.seed_gate.resolved_request
    decision = record.row_result.decision
    if request.decision_id != decision.decision_id:
        raise ValueError("decision_id mismatch between request and decision")
    if request.seed_candidate_id != decision.seed_candidate_id:
        raise ValueError("seed_candidate_id mismatch between request and decision")
    if request.seed_sample != decision.seed_sample:
        raise ValueError("seed_sample mismatch between request and decision")
    if (
        request.request_identity_completeness_status
        != decision.request_identity_completeness_status
    ):
        raise ValueError(
            "request_identity_completeness_status mismatch between "
            "request and decision"
        )
    if (
        request.request_candidate_identity_status
        != decision.request_candidate_identity_status
    ):
        raise ValueError(
            "request_candidate_identity_status mismatch between "
            "request and decision"
        )
    _validate_decision_summary(decision)
    if not request.seed_sample:
        raise ValueError("writer requires resolved seed_sample")
    for cell in record.row_result.cells:
        if cell.decision_id != decision.decision_id:
            raise ValueError("decision_id mismatch between decision and cell")
        if cell.identity_family_id != decision.identity_family_id:
            raise ValueError(
                "identity_family_id mismatch between decision and cell"
            )
        if request.seed_sample and cell.sample_id == request.seed_sample:
            raise ValueError("seed sample cannot be emitted in cell_evidence.tsv")
    return record


def _write_tsv(
    path: Path,
    columns: tuple[str, ...],
    rows: Sequence[Mapping[str, str]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            dialect="excel-tab",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def _first_threshold(
    rows: list[IdentityDecisionSummary],
    field_name: str,
) -> object:
    if not rows:
        return "not_assessed"
    values = {getattr(row, field_name) for row in rows}
    if len(values) != 1:
        raise ValueError(f"mixed {field_name} values in summary rows")
    return getattr(rows[0], field_name)


def _sum_decision_field(
    rows: list[IdentityDecisionSummary],
    field_name: str,
) -> int:
    return sum(int(getattr(row, field_name)) for row in rows)


def _cell_status_count(
    rows: list[CellEvidenceResult],
    field_name: str,
    value: str,
) -> int:
    return sum(
        1 for row in rows
        if _enum_value(getattr(row, field_name)) == value
    )


def _counter_table(counter: Counter[str], label: str) -> list[str]:
    if not counter:
        return [
            f"| {label} | Count |",
            "| --- | ---: |",
            "| `none` | 0 |",
            "",
        ]
    return [
        f"| {label} | Count |",
        "| --- | ---: |",
        *[f"| `{key}` | {count} |" for key, count in sorted(counter.items())],
        "",
    ]


def _engineering_go_no_go_rows(
    decision_rows: Sequence[IdentityDecisionSummary],
    *,
    context: IdentityCoherenceOutputContext,
    assessed_sample_total: int,
) -> list[str]:
    blocked_count = _sum_decision_field(
        decision_rows,
        "infrastructure_blocked_sample_count",
    )
    blocked_fraction = (
        0.0 if assessed_sample_total <= 0 else blocked_count / assessed_sample_total
    )
    rows = [
        "| Check | Decision | Basis |",
        "| --- | --- | --- |",
        (
            "| evidence_firewall | Proceed | "
            "`promotion_used_forbidden_evidence = false` |"
        ),
        _status_row(
            "firewall_fixture",
            context.firewall_fixture_status,
            pass_basis="firewall A/B fixture passed",
        ),
        _status_row(
            "spawn_payload_smoke",
            context.spawn_payload_smoke_status,
            pass_basis="spawn payload smoke passed",
        ),
    ]
    if assessed_sample_total <= 0:
        rows.append(
            "| infrastructure_blocked_fraction | Not assessed | "
            "`assessed_sample_total` not assessed |"
        )
    else:
        max_blocked_fraction = context.max_infrastructure_blocked_fraction
        blocked_basis = (
            f"`{blocked_count} / {assessed_sample_total} = "
            f"{blocked_fraction:.12g}`"
        )
        if blocked_fraction <= max_blocked_fraction:
            rows.append(
                "| infrastructure_blocked_fraction | Proceed | "
                f"{blocked_basis} <= `{max_blocked_fraction}` |"
            )
        else:
            rows.append(
                "| infrastructure_blocked_fraction | Pivot | "
                f"{blocked_basis} exceeds `{max_blocked_fraction}` |"
            )

    projected = context.projected_85raw_identity_request_count
    max_projected = context.max_projected_85raw_identity_xic_requests
    if projected is None:
        rows.append(
            "| projected_85raw_identity_xic_requests | No-Go for 85RAW | "
            "`projected_85raw_identity_request_count` not assessed |"
        )
    elif max_projected is None:
        rows.append(
            "| projected_85raw_identity_xic_requests | No-Go for 85RAW | "
            "`max_projected_85raw_identity_xic_requests` not provided |"
        )
    elif projected <= max_projected:
        rows.append(
            "| projected_85raw_identity_xic_requests | Proceed | "
            f"`{projected}` <= `{max_projected}` |"
        )
    else:
        rows.append(
            "| projected_85raw_identity_xic_requests | Pivot | "
            f"`{projected}` exceeds `{max_projected}` |"
        )
    rows.append("")
    return rows


def _status_row(name: str, status: str, *, pass_basis: str) -> str:
    normalized = "" if status is None else str(status).strip()
    if normalized == "pass":
        return f"| {name} | Proceed | {pass_basis} |"
    if normalized == "not_assessed" or not normalized:
        return f"| {name} | Not assessed | `{name}` not assessed |"
    return f"| {name} | Pivot | `{normalized}` |"


def _assessed_sample_count_for_decision(
    row: IdentityDecisionSummary,
) -> int:
    if row.coherent_fraction in {None, 0}:
        return 0
    return max(1, round(row.total_coherent_sample_count / row.coherent_fraction))


def _total_assessed_sample_count(
    decision_rows: Sequence[IdentityDecisionSummary],
) -> int:
    return sum(_assessed_sample_count_for_decision(row) for row in decision_rows)


def _validate_nonnegative_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be nonnegative")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return numeric


def _validate_optional_nonnegative_int(
    value: object,
    field_name: str,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _hash_lines(input_hashes: tuple[tuple[str, str], ...]) -> list[str]:
    if not input_hashes:
        return [
            "| Input | Hash |",
            "| --- | --- |",
            "| `not_provided` | `not_provided` |",
        ]
    return [
        "| Input | Hash |",
        "| --- | --- |",
        *[f"| `{name}` | `{digest}` |" for name, digest in input_hashes],
    ]


def _project_columns(
    columns: tuple[str, ...],
    values: Mapping[str, object],
) -> dict[str, str]:
    return {column: _format_tsv_value(values.get(column)) for column in columns}


def _format_tsv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.12g}"
    if isinstance(value, tuple):
        return ";".join(_format_tsv_value(item) for item in value)
    if isinstance(value, list):
        return ";".join(_format_tsv_value(item) for item in value)
    if isinstance(value, set):
        return ";".join(_format_tsv_value(item) for item in sorted(value))
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def _control_pass_is_true(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
