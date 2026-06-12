from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.identity_coherence_validation.bundle import (
    read_tsv_dict_rows,
)
from xic_extractor.alignment.identity_coherence_validation.models import (
    CONTROL_MANIFEST_COLUMNS,
    DiagnosticBundle,
)
from xic_extractor.tabular_io import write_tsv


def write_decoy_manifest_proposal(
    serial_bundle: DiagnosticBundle,
    proposal_path: Path,
    *,
    max_decoys: int = 3,
) -> int:
    if max_decoys < 0:
        raise ValueError("max_decoys must be nonnegative")
    request_rows = read_tsv_dict_rows(serial_bundle.requests_tsv)
    decision_rows = read_tsv_dict_rows(serial_bundle.decisions_tsv)
    request_by_decision, ambiguous_decision_ids = _unique_requests_by_decision(
        request_rows
    )
    proposal_rows: list[dict[str, str]] = []
    for decision in decision_rows:
        if len(proposal_rows) >= max_decoys:
            break
        decision_id = decision.get("decision_id", "")
        if decision_id in ambiguous_decision_ids:
            continue
        if decision.get("seed_gate_class") != "coherent_seed":
            continue
        request = request_by_decision.get(decision_id)
        if request is None:
            continue
        if request.get("seed_candidate_id") != decision.get("seed_candidate_id"):
            continue
        if request.get("seed_sample") != decision.get("seed_sample"):
            continue
        if not _proposal_request_has_required_values(request):
            continue
        proposal_rows.append(
            _decoy_manifest_row(
                index=len(proposal_rows) + 1,
                request=request,
                decision=decision,
            )
        )
    _write_manifest_rows(proposal_path, proposal_rows)
    return len(proposal_rows)


def _unique_requests_by_decision(
    request_rows: tuple[dict[str, str], ...],
) -> tuple[dict[str, dict[str, str]], set[str]]:
    request_by_decision: dict[str, dict[str, str]] = {}
    ambiguous: set[str] = set()
    for row in request_rows:
        decision_id = row.get("decision_id", "")
        if not decision_id:
            continue
        if decision_id in request_by_decision:
            ambiguous.add(decision_id)
            request_by_decision.pop(decision_id, None)
            continue
        if decision_id not in ambiguous:
            request_by_decision[decision_id] = row
    return request_by_decision, ambiguous


def _proposal_request_has_required_values(request: dict[str, str]) -> bool:
    required = (
        "fragment_observation_mode",
        "precursor_tolerance_ppm",
        "product_tolerance_ppm",
        "cid_observed_loss_tolerance_ppm",
    )
    return all(request.get(field, "").strip() for field in required)


def _decoy_manifest_row(
    *,
    index: int,
    request: dict[str, str],
    decision: dict[str, str],
) -> dict[str, str]:
    request_id = request.get("request_id", "")
    return {
        "control_id": f"IDC-{index:03d}",
        "control_type": "identity_decoy",
        "control_name": f"Auto-proposed rt_shift decoy for {request_id}",
        "expected_mapping_status": "not_applicable",
        "control_expected_behavior": "decoy_rejected_before_promotion",
        "fragment_observation_mode": request.get("fragment_observation_mode", ""),
        "precursor_tolerance_ppm": request.get("precursor_tolerance_ppm", ""),
        "product_tolerance_ppm": request.get("product_tolerance_ppm", ""),
        "cid_observed_loss_tolerance_ppm": request.get(
            "cid_observed_loss_tolerance_ppm", ""
        ),
        "rt_tolerance_sec": "60.0",
        "required_failure_reason_when_missed": "seed_rt_outside_owner_peak",
        "decision_id": decision.get("decision_id", ""),
        "identity_family_id": decision.get("identity_family_id", ""),
        "seed_candidate_id": decision.get("seed_candidate_id", ""),
        "decoy_generation_method": "rt_shift",
        "decoy_source_request_id": request_id,
        "decoy_fragment_tags": "",
        "positive_control_target_name": "",
        "positive_control_target_mz": "",
        "positive_control_target_rt_sec": "",
        "positive_control_mapping_error_ppm": "",
        "positive_control_mapping_delta_rt_sec": "",
        "control_notes": (
            "auto-proposed identity decoy; review and rename to .reviewed.tsv "
            "before using as validation input"
        ),
    }


def _write_manifest_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(
        path,
        rows,
        CONTROL_MANIFEST_COLUMNS,
        formatter=_format_tsv_value,
    )


def _format_tsv_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
