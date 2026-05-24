from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast

from xic_extractor.alignment.identity_coherence.models import (
    CandidateTrace,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)
from xic_extractor.alignment.identity_coherence_source_mapping import (
    IdentityCoherenceSeedSource,
)
from xic_extractor.alignment.process_backend import run_identity_trace_process
from xic_extractor.discovery.models import DiscoveryCandidate


class IdentityCoherenceRawSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[object, object]:
        raise NotImplementedError


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
        rt_min=float(cast(float, candidate.ms1_peak_rt_start)),
        rt_max=float(cast(float, candidate.ms1_peak_rt_end)),
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
            rt_min=tuple(float(value) for value in cast(Iterable[float], rt_values)),
            intensity=tuple(
                float(value) for value in cast(Iterable[float], intensity_values)
            ),
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
