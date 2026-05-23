from __future__ import annotations

from .models import (
    CandidateTrace,
    IdentityCoherenceTraceRequest,
    IdentityCoherenceTraceResult,
)


def identity_coherence_trace_payload_smoke_worker(
    request: IdentityCoherenceTraceRequest,
) -> IdentityCoherenceTraceResult:
    """Round-trip a payload without RAW IO using a zero-intensity sentinel trace."""

    trace = CandidateTrace(
        rt_min=(request.rt_min, request.rt_max),
        intensity=(0.0, 0.0),
    )
    return IdentityCoherenceTraceResult(
        request=request,
        trace=trace,
        status="pass",
        raw_xic_request_count=0,
        raw_chromatogram_call_count=0,
        xic_point_count=len(trace.rt_min),
        elapsed_sec=0.0,
    )
