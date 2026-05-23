from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    IdentityCoherenceRequest,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
    SeedCandidateEvidence,
    SeedGateResult,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
    build_seed_candidate_evidence,
)
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate
from xic_extractor.alignment.ownership import OwnershipBuildResult
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner
from xic_extractor.alignment.process_backend import run_identity_trace_process
from xic_extractor.discovery.models import DiscoveryCandidate


@dataclass(frozen=True)
class IdentityCoherenceSeedSource:
    request_id: str
    decision_id: str
    identity_family_id: str
    request: IdentityCoherenceRequest
    seed_candidate: DiscoveryCandidate
    seed_evidence: SeedCandidateEvidence
    owner: SampleLocalMS1Owner
    owner_assignment_status: str
    seed_gate: SeedGateResult


class IdentityCoherenceRawSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> object:
        raise NotImplementedError


def build_identity_coherence_seed_sources(
    *,
    candidates: Sequence[DiscoveryCandidate],
    ownership: OwnershipBuildResult,
    alignment_config: AlignmentConfig,
    fragment_profile_id: str,
    fragment_profile_hash: str,
    config: IdentityCoherenceConfig | None = None,
) -> tuple[IdentityCoherenceSeedSource, ...]:
    identity_config = config or IdentityCoherenceConfig()
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    assignment_by_candidate_id = assignment_status_by_candidate_id(ownership)
    joined_sources: list[tuple[SampleLocalMS1Owner, DiscoveryCandidate]] = []
    for owner in sorted(ownership.owners, key=_owner_sort_key):
        seed_id = owner.primary_identity_event.candidate_id
        seed_candidate = candidates_by_id.get(seed_id)
        if seed_candidate is None:
            continue
        if seed_id not in assignment_by_candidate_id:
            continue
        joined_sources.append((owner, seed_candidate))

    sources: list[IdentityCoherenceSeedSource] = []
    for index, (owner, seed_candidate) in enumerate(joined_sources, start=1):
        seed_id = owner.primary_identity_event.candidate_id
        request_id = candidate_request_id(index)
        decision_id = candidate_decision_id(index)
        request = build_identity_coherence_request(
            seed_candidate,
            request_id=request_id,
            decision_id=decision_id,
            precursor_tolerance_ppm=alignment_config.preferred_ppm,
            product_tolerance_ppm=alignment_config.product_mz_tolerance_ppm,
            cid_observed_loss_tolerance_ppm=(
                alignment_config.observed_loss_tolerance_ppm
            ),
            fragment_profile_id=fragment_profile_id,
            fragment_profile_hash=fragment_profile_hash,
        )
        seed_evidence = build_seed_candidate_evidence(seed_candidate)
        owner_assignment_status = assignment_by_candidate_id[seed_id]
        seed_gate = evaluate_seed_gate(
            request,
            seed_evidence,
            owner,
            owner_assignment_status=owner_assignment_status,
            config=identity_config.seed_gate,
        )
        sources.append(
            IdentityCoherenceSeedSource(
                request_id=request_id,
                decision_id=decision_id,
                identity_family_id=candidate_identity_family_id(index),
                request=seed_gate.resolved_request,
                seed_candidate=seed_candidate,
                seed_evidence=seed_evidence,
                owner=owner,
                owner_assignment_status=owner_assignment_status,
                seed_gate=seed_gate,
            )
        )
    return tuple(sources)


def trace_request_for_candidate(
    *,
    source: IdentityCoherenceSeedSource,
    candidate: DiscoveryCandidate,
    ppm_tolerance: float,
) -> IdentityCoherenceTraceRequest:
    return IdentityCoherenceTraceRequest(
        decision_id=source.decision_id,
        request_id=source.request_id,
        sample_id=candidate.sample_stem,
        candidate_id=candidate.candidate_id,
        precursor_mz=candidate.precursor_mz,
        ppm_tolerance=ppm_tolerance,
        rt_min=float(candidate.ms1_peak_rt_start),
        rt_max=float(candidate.ms1_peak_rt_end),
    )


def retrieve_identity_coherence_trace(
    request: IdentityCoherenceTraceRequest,
    raw_sources: Mapping[str, IdentityCoherenceRawSource],
) -> IdentityCoherenceTraceResult:
    raw_source = raw_sources.get(request.sample_id)
    if raw_source is None:
        return IdentityCoherenceTraceResult(
            request=request,
            trace=None,
            status="blocked_infrastructure",
            blocked_reason="missing_raw_source",
        )

    start = perf_counter()
    try:
        raw_result = raw_source.extract_xic(
            request.precursor_mz,
            request.rt_min,
            request.rt_max,
            request.ppm_tolerance,
        )
    except Exception:
        return IdentityCoherenceTraceResult(
            request=request,
            trace=None,
            status="blocked_infrastructure",
            blocked_reason="raw_xic_extraction_error",
            raw_xic_request_count=1,
            elapsed_sec=perf_counter() - start,
        )

    try:
        rt_values, intensity_values = raw_result
        trace = CandidateTrace(
            rt_min=tuple(float(value) for value in rt_values),
            intensity=tuple(float(value) for value in intensity_values),
        )
    except (TypeError, ValueError):
        return IdentityCoherenceTraceResult(
            request=request,
            trace=None,
            status="data_quality_reject",
            blocked_reason="invalid_trace_payload",
            raw_xic_request_count=1,
            elapsed_sec=perf_counter() - start,
        )

    return IdentityCoherenceTraceResult(
        request=request,
        trace=trace,
        status="pass",
        raw_xic_request_count=1,
        raw_chromatogram_call_count=1,
        xic_point_count=len(trace.rt_min),
        elapsed_sec=perf_counter() - start,
    )


def retrieve_identity_coherence_traces(
    requests: Sequence[IdentityCoherenceTraceRequest],
    *,
    raw_sources: Mapping[str, IdentityCoherenceRawSource],
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    raw_workers: int,
    raw_xic_batch_size: int,
) -> tuple[IdentityCoherenceTraceResult, ...]:
    if raw_workers < 1:
        raise ValueError("raw_workers must be >= 1")
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    if raw_workers == 1:
        return tuple(
            retrieve_identity_coherence_trace(request, raw_sources)
            for request in requests
        )
    process_output = run_identity_trace_process(
        requests,
        raw_paths=raw_paths,
        dll_dir=dll_dir,
        max_workers=raw_workers,
        raw_xic_batch_size=raw_xic_batch_size,
    )
    return process_output.results


def build_cell_candidate_evidence(
    candidate: DiscoveryCandidate,
    *,
    owner_assignment_status: str,
    trace_result: IdentityCoherenceTraceResult | None,
) -> CellCandidateEvidence:
    blocked_reason = ""
    data_quality_reason = ""
    trace = None
    point_count = None
    if trace_result is not None:
        if trace_result.status == "pass":
            trace = trace_result.trace
            point_count = trace_result.xic_point_count
        elif trace_result.status == "blocked_infrastructure":
            blocked_reason = trace_result.blocked_reason
        elif trace_result.status == "data_quality_reject":
            data_quality_reason = trace_result.blocked_reason
    return CellCandidateEvidence(
        sample_id=candidate.sample_stem,
        candidate_evidence=build_seed_candidate_evidence(candidate),
        apex_rt=candidate.ms1_apex_rt,
        peak_start_rt=candidate.ms1_peak_rt_start,
        peak_end_rt=candidate.ms1_peak_rt_end,
        area=candidate.ms1_area,
        height=candidate.ms1_height,
        point_count=point_count,
        owner_assignment_status=owner_assignment_status,
        trace=trace,
        blocked_reason=blocked_reason,
        data_quality_reason=data_quality_reason,
    )


def assignment_status_by_candidate_id(
    ownership: OwnershipBuildResult,
) -> dict[str, str]:
    return {
        assignment.candidate_id: assignment.assignment_status
        for assignment in ownership.assignments
    }


def candidate_request_id(index: int) -> str:
    return f"ICR{index:06d}"


def candidate_decision_id(index: int) -> str:
    return f"ICD{index:06d}"


def candidate_identity_family_id(index: int) -> str:
    return f"ICF{index:06d}"


def candidate_is_non_seed_pool_member(
    request: IdentityCoherenceRequest,
    candidate: DiscoveryCandidate,
    *,
    seed_candidate: DiscoveryCandidate,
    config: AlignmentConfig,
) -> bool:
    if candidate.candidate_id == seed_candidate.candidate_id:
        return False
    if candidate.sample_stem == seed_candidate.sample_stem:
        return False
    if not _has_complete_candidate_morphology(candidate):
        return False
    precursor = request.identity.precursor_mz
    tolerance = request.identity.precursor_tolerance_ppm
    if precursor is None or tolerance is None:
        return False
    error = _ppm_error(candidate.precursor_mz, precursor)
    if error is None or abs(error) > tolerance:
        return False
    rt_delta_sec = abs(candidate.best_seed_rt - seed_candidate.best_seed_rt) * 60.0
    return rt_delta_sec <= config.identity_rt_candidate_window_sec


def _owner_sort_key(owner: SampleLocalMS1Owner) -> tuple[str, float, str]:
    return (
        owner.sample_stem,
        owner.owner_apex_rt,
        owner.primary_identity_event.candidate_id,
    )


def _has_complete_candidate_morphology(candidate: DiscoveryCandidate) -> bool:
    values = (
        candidate.ms1_apex_rt,
        candidate.ms1_peak_rt_start,
        candidate.ms1_peak_rt_end,
        candidate.ms1_area,
        candidate.ms1_height,
    )
    if any(not _finite_number(value) for value in values):
        return False
    return (
        float(candidate.ms1_peak_rt_start)
        < float(candidate.ms1_apex_rt)
        < float(candidate.ms1_peak_rt_end)
        and float(candidate.ms1_area) > 0.0
        and float(candidate.ms1_height) > 0.0
    )


def _ppm_error(observed: float, expected: float) -> float | None:
    if not _finite_number(observed) or not _finite_number(expected):
        return None
    if expected <= 0:
        return None
    return (observed - expected) / expected * 1_000_000.0


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(value)
    )
