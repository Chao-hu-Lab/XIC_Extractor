from xic_extractor.peak_detection.models import PeakCandidate

ANCHOR_SELECTION_MIN_INTENSITY_RATIO: float = 0.2


def select_candidate(
    candidates: tuple[PeakCandidate, ...],
    *,
    preferred_rt: float | None,
    strict_preferred_rt: bool,
) -> PeakCandidate:
    strongest_candidate = max(
        candidates, key=lambda candidate: candidate.selection_apex_intensity
    )
    if preferred_rt is None or len(candidates) == 1:
        return strongest_candidate

    nearest_candidate = min(
        candidates,
        key=lambda candidate: abs(candidate.selection_apex_rt - preferred_rt),
    )
    if strict_preferred_rt:
        return nearest_candidate
    if (
        nearest_candidate.selection_apex_intensity
        >= strongest_candidate.selection_apex_intensity
        * ANCHOR_SELECTION_MIN_INTENSITY_RATIO
    ):
        return nearest_candidate
    return strongest_candidate


def selection_rt_for_scored_candidates(
    candidates: tuple[PeakCandidate, ...],
    *,
    preferred_rt: float | None,
    strict_preferred_rt: bool,
) -> float | None:
    if preferred_rt is None or not candidates:
        return None
    if strict_preferred_rt:
        return preferred_rt

    nearest_candidate = min(
        candidates,
        key=lambda candidate: abs(candidate.selection_apex_rt - preferred_rt),
    )
    strongest_candidate = max(
        candidates, key=lambda candidate: candidate.selection_apex_intensity
    )
    if (
        nearest_candidate.selection_apex_intensity
        >= strongest_candidate.selection_apex_intensity
        * ANCHOR_SELECTION_MIN_INTENSITY_RATIO
    ):
        return preferred_rt
    return None
