from collections.abc import Callable
from dataclasses import replace

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.peak_detection.models import PeakCandidate, PeakCandidatesResult

PREFERRED_RT_RECOVERY_PROMINENCE_FRACTION: float = 0.2
PREFERRED_RT_RECOVERY_MIN_PROMINENCE_RATIO: float = 0.01
PREFERRED_RT_RECOVERY_MAX_DELTA_MIN: float = 0.35
RECOVERY_CANDIDATE_MIN_INTENSITY_RATIO: float = 0.03
LOCAL_RECOVERY_RELATIVE_HEIGHT_FRACTION: float = 0.25
LOCAL_RECOVERY_MIN_RELATIVE_HEIGHT: float = 0.01
LOCAL_RECOVERY_ABSOLUTE_HEIGHT_FRACTION: float = 0.5
LOCAL_RECOVERY_MIN_ABSOLUTE_HEIGHT: float = 5.0
LOCAL_RECOVERY_TOP_EDGE_RATIO: float = 1.05
LOCAL_RECOVERY_DURATION_MAX_MULTIPLIER: float = 1.5


def preferred_rt_recovery(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    preferred_rt: float | None,
    strict_preferred_rt: bool,
    current_candidate: PeakCandidate | None,
    candidate_finder: Callable[..., PeakCandidatesResult],
) -> tuple[PeakCandidate | None, PeakCandidatesResult | None]:
    if preferred_rt is None or strict_preferred_rt:
        return None, None
    if (
        current_candidate is not None
        and abs(current_candidate.selection_apex_rt - preferred_rt)
        <= PREFERRED_RT_RECOVERY_MAX_DELTA_MIN
    ):
        return None, None

    resolver_mode = getattr(config, "resolver_mode", "legacy_savgol")
    if resolver_mode == "local_minimum":
        relaxed_config = relaxed_local_minimum_recovery_config(config)
        if relaxed_config == config:
            return None, None
        relaxed_result = candidate_finder(
            rt,
            intensity,
            relaxed_config,
        )
    else:
        relaxed_ratio = max(
            PREFERRED_RT_RECOVERY_MIN_PROMINENCE_RATIO,
            config.peak_min_prominence_ratio
            * PREFERRED_RT_RECOVERY_PROMINENCE_FRACTION,
        )
        if relaxed_ratio >= config.peak_min_prominence_ratio:
            return None, None
        relaxed_result = candidate_finder(
            rt,
            intensity,
            config,
            peak_min_prominence_ratio=relaxed_ratio,
        )
    if relaxed_result.status != "OK":
        return None, None

    candidate = select_preferred_recovery_candidate(
        relaxed_result.candidates,
        preferred_rt=preferred_rt,
    )
    if candidate is None:
        return None, None
    return candidate, relaxed_result


def relaxed_local_minimum_recovery_config(
    config: ExtractionConfig,
) -> ExtractionConfig:
    return replace(
        config,
        resolver_min_relative_height=max(
            LOCAL_RECOVERY_MIN_RELATIVE_HEIGHT,
            config.resolver_min_relative_height
            * LOCAL_RECOVERY_RELATIVE_HEIGHT_FRACTION,
        ),
        resolver_min_absolute_height=max(
            LOCAL_RECOVERY_MIN_ABSOLUTE_HEIGHT,
            config.resolver_min_absolute_height
            * LOCAL_RECOVERY_ABSOLUTE_HEIGHT_FRACTION,
        ),
        resolver_min_ratio_top_edge=min(
            config.resolver_min_ratio_top_edge,
            LOCAL_RECOVERY_TOP_EDGE_RATIO,
        ),
        resolver_peak_duration_max=max(
            config.resolver_peak_duration_max,
            config.resolver_peak_duration_max
            * LOCAL_RECOVERY_DURATION_MAX_MULTIPLIER,
        ),
    )


def select_preferred_recovery_candidate(
    candidates: tuple[PeakCandidate, ...],
    *,
    preferred_rt: float,
) -> PeakCandidate | None:
    nearest_candidate = min(
        candidates,
        key=lambda candidate: abs(candidate.selection_apex_rt - preferred_rt),
    )
    delta = abs(nearest_candidate.selection_apex_rt - preferred_rt)
    if delta > PREFERRED_RT_RECOVERY_MAX_DELTA_MIN:
        return None

    strongest_candidate = max(
        candidates, key=lambda candidate: candidate.selection_apex_intensity
    )
    if (
        nearest_candidate.selection_apex_intensity
        < strongest_candidate.selection_apex_intensity
        * RECOVERY_CANDIDATE_MIN_INTENSITY_RATIO
    ):
        return None
    return nearest_candidate
