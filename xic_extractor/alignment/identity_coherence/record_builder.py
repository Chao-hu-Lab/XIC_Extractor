from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.identity_coherence.models import (
    CellCandidateEvidence,
    IdentityCoherenceConfig,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)
from xic_extractor.alignment.identity_coherence.output import (
    IdentityCoherenceOutputRecord,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_seed_candidate_evidence,
)
from xic_extractor.alignment.identity_coherence.row_evaluator import (
    evaluate_identity_coherence_row,
)
from xic_extractor.alignment.identity_coherence.schema import SeedGateClass
from xic_extractor.alignment.identity_coherence.source_mapping import (
    IdentityCoherenceSeedSource,
    candidate_is_non_seed_pool_member,
)
from xic_extractor.alignment.identity_coherence.trace_retrieval import (
    trace_request_for_candidate,
)
from xic_extractor.discovery.models import DiscoveryCandidate


@dataclass(frozen=True)
class IdentityCoherenceSeedTracePlan:
    source_index: int
    source: IdentityCoherenceSeedSource
    candidate_pool: tuple[DiscoveryCandidate, ...]
    trace_requests: tuple[IdentityCoherenceTraceRequest, ...]


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


def build_identity_coherence_output_record(
    source: IdentityCoherenceSeedSource,
    *,
    candidate_pool: tuple[DiscoveryCandidate, ...],
    trace_results: tuple[IdentityCoherenceTraceResult, ...],
    assignment_by_candidate_id: Mapping[str, str],
    sample_order: tuple[str, ...],
    config: IdentityCoherenceConfig,
) -> IdentityCoherenceOutputRecord:
    if source.seed_gate.seed_gate_class != SeedGateClass.COHERENT_SEED:
        row = evaluate_identity_coherence_row(
            source.seed_gate,
            source.seed_evidence,
            None,
            (),
            config,
            identity_family_id=source.identity_family_id,
            assessed_sample_count=len(sample_order),
        )
        return IdentityCoherenceOutputRecord(source.seed_gate, row)

    expected_trace_count = len(candidate_pool) + 1
    if len(trace_results) != expected_trace_count:
        raise ValueError("trace result count does not match seed source plan")
    trace_by_candidate_id = {
        result.request.candidate_id: result for result in trace_results
    }
    seed_trace_result = trace_by_candidate_id[source.seed_candidate.candidate_id]
    seed_cell = build_cell_candidate_evidence(
        source.seed_candidate,
        owner_assignment_status=source.owner_assignment_status,
        trace_result=seed_trace_result,
    )
    non_seed_cells: list[CellCandidateEvidence] = []
    for candidate in candidate_pool:
        trace_result = trace_by_candidate_id[candidate.candidate_id]
        non_seed_cells.append(
            build_cell_candidate_evidence(
                candidate,
                owner_assignment_status=assignment_by_candidate_id.get(
                    candidate.candidate_id,
                    "unresolved",
                ),
                trace_result=trace_result,
            )
        )
    row = evaluate_identity_coherence_row(
        source.seed_gate,
        source.seed_evidence,
        seed_cell,
        tuple(non_seed_cells),
        config,
        identity_family_id=source.identity_family_id,
        assessed_sample_count=len(sample_order),
    )
    return IdentityCoherenceOutputRecord(source.seed_gate, row)


def candidate_pool_for_seed_source(
    source: IdentityCoherenceSeedSource,
    candidates: Sequence[DiscoveryCandidate],
    *,
    alignment_config: AlignmentConfig,
) -> tuple[DiscoveryCandidate, ...]:
    return tuple(
        candidate
        for candidate in candidates
        if candidate_is_non_seed_pool_member(
            source.request,
            candidate,
            seed_candidate=source.seed_candidate,
            config=alignment_config,
        )
    )


def trace_requests_for_seed_source(
    source: IdentityCoherenceSeedSource,
    candidate_pool: tuple[DiscoveryCandidate, ...],
    *,
    alignment_config: AlignmentConfig,
) -> tuple[IdentityCoherenceTraceRequest, ...]:
    return (
        trace_request_for_candidate(
            source=source,
            candidate=source.seed_candidate,
            ppm_tolerance=alignment_config.preferred_ppm,
        ),
        *(
            trace_request_for_candidate(
                source=source,
                candidate=candidate,
                ppm_tolerance=alignment_config.preferred_ppm,
            )
            for candidate in candidate_pool
        ),
    )
