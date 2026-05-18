from __future__ import annotations

from collections.abc import Callable

from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.signal_processing import PeakCandidate


def selected_candidate_ms2_evidence(
    candidate: PeakCandidate | None,
    candidate_ms2_cache: dict[PeakCandidate, CandidateMS2Evidence],
    candidate_ms2_builder: Callable[[PeakCandidate], CandidateMS2Evidence | None],
) -> CandidateMS2Evidence | None:
    if candidate is None:
        return None
    evidence = candidate_ms2_cache.get(candidate)
    if evidence is not None:
        return evidence
    if "region_first_safe_merge" not in candidate.merge_note.split(";"):
        return None
    return candidate_ms2_builder(candidate)
