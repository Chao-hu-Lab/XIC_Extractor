from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    IdentityEvent,
    OwnerAssignment,
    SampleLocalMS1Owner,
)
from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area


class OwnershipXICSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...


@dataclass(frozen=True)
class ResolvedPeak:
    rt: float
    peak_start: float
    peak_end: float
    area: float
    intensity: float


PeakResolver = Callable[
    [Any, NDArray[np.float64], NDArray[np.float64], ExtractionConfig, float],
    ResolvedPeak | None,
]


@dataclass(frozen=True)
class OwnershipBuildResult:
    owners: tuple[SampleLocalMS1Owner, ...]
    assignments: tuple[OwnerAssignment, ...]
    ambiguous_records: tuple[AmbiguousOwnerRecord, ...]


@dataclass(frozen=True)
class _ResolvedCandidate:
    candidate: Any
    event: IdentityEvent
    apex_rt: float
    peak_start_rt: float
    peak_end_rt: float
    area: float
    height: float


@dataclass(frozen=True)
class _ResolutionOutcome:
    resolved: _ResolvedCandidate | None
    unresolved: OwnerAssignment | None


def build_sample_local_owners(
    candidates: Sequence[Any],
    *,
    raw_sources: Mapping[str, OwnershipXICSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    peak_resolver: PeakResolver | None = None,
) -> OwnershipBuildResult:
    active_peak_resolver = peak_resolver or _default_peak_resolver
    outcomes = tuple(
        _resolve_candidate(
            candidate,
            raw_sources,
            alignment_config,
            peak_config,
            active_peak_resolver,
        )
        for candidate in candidates
    )
    resolved = tuple(
        outcome.resolved for outcome in outcomes if outcome.resolved is not None
    )
    unresolved_assignments = tuple(
        outcome.unresolved for outcome in outcomes if outcome.unresolved is not None
    )
    owners: list[SampleLocalMS1Owner] = []
    assignments: list[OwnerAssignment] = []
    ambiguous_records: list[AmbiguousOwnerRecord] = []
    by_sample: dict[str, list[_ResolvedCandidate]] = defaultdict(list)
    for item in resolved:
        by_sample[item.event.sample_stem].append(item)
    for sample_stem in sorted(by_sample):
        sample_owners, sample_assignments, sample_ambiguous = _owners_for_sample(
            sample_stem,
            by_sample[sample_stem],
            alignment_config=alignment_config,
        )
        owners.extend(sample_owners)
        assignments.extend(sample_assignments)
        ambiguous_records.extend(sample_ambiguous)
    return OwnershipBuildResult(
        owners=tuple(owners),
        assignments=(*unresolved_assignments, *assignments),
        ambiguous_records=tuple(ambiguous_records),
    )


def _resolve_candidate(
    candidate: Any,
    raw_sources: Mapping[str, OwnershipXICSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    peak_resolver: PeakResolver,
) -> _ResolutionOutcome:
    sample_stem = str(candidate.sample_stem)
    source = raw_sources.get(sample_stem)
    if source is None:
        return _unresolved_outcome(candidate, "missing_raw_source")
    seed_rt = _candidate_seed_rt(candidate)
    rt_min = seed_rt - alignment_config.max_rt_sec / 60.0
    rt_max = seed_rt + alignment_config.max_rt_sec / 60.0
    rt, intensity = source.extract_xic(
        float(candidate.precursor_mz),
        rt_min,
        rt_max,
        alignment_config.preferred_ppm,
    )
    rt_array, intensity_array = _validated_trace_arrays(rt, intensity)
    peak = peak_resolver(candidate, rt_array, intensity_array, peak_config, seed_rt)
    if peak is None:
        return _unresolved_outcome(candidate, "peak_not_found")
    return _ResolutionOutcome(
        resolved=_ResolvedCandidate(
            candidate=candidate,
            event=_identity_event(candidate, seed_rt=seed_rt),
            apex_rt=peak.rt,
            peak_start_rt=peak.peak_start,
            peak_end_rt=peak.peak_end,
            area=peak.area,
            height=peak.intensity,
        ),
        unresolved=None,
    )


def _unresolved_outcome(candidate: Any, reason: str) -> _ResolutionOutcome:
    return _ResolutionOutcome(
        resolved=None,
        unresolved=OwnerAssignment(
            str(candidate.candidate_id),
            None,
            "unresolved",
            reason,
        ),
    )


def _default_peak_resolver(
    candidate: Any,
    rt_array: NDArray[np.float64],
    intensity_array: NDArray[np.float64],
    peak_config: ExtractionConfig,
    seed_rt: float,
) -> ResolvedPeak | None:
    result = find_peak_and_area(
        rt_array,
        intensity_array,
        peak_config,
        preferred_rt=seed_rt,
        strict_preferred_rt=True,
    )
    if result.status != "OK" or result.peak is None:
        return None
    peak = result.peak
    return ResolvedPeak(
        rt=peak.rt,
        peak_start=peak.peak_start,
        peak_end=peak.peak_end,
        area=peak.area,
        intensity=peak.intensity,
    )


def _owners_for_sample(
    sample_stem: str,
    resolved: list[_ResolvedCandidate],
    *,
    alignment_config: AlignmentConfig,
) -> tuple[
    list[SampleLocalMS1Owner],
    list[OwnerAssignment],
    list[AmbiguousOwnerRecord],
]:
    pending = sorted(resolved, key=_resolved_sort_key)
    groups = _candidate_components(pending, alignment_config)
    owners: list[SampleLocalMS1Owner] = []
    assignments: list[OwnerAssignment] = []
    ambiguous: list[AmbiguousOwnerRecord] = []
    for index, group in enumerate(groups, start=1):
        if _component_is_ambiguous(group, alignment_config):
            ambiguity_id = f"AMB-{sample_stem}-{len(ambiguous) + 1:06d}"
            candidate_ids = tuple(
                item.event.candidate_id
                for item in sorted(group, key=_resolved_sort_key)
            )
            ambiguous.append(
                AmbiguousOwnerRecord(
                    ambiguity_id=ambiguity_id,
                    sample_stem=sample_stem,
                    candidate_ids=candidate_ids,
                    reason="owner_multiplet_ambiguity",
                ),
            )
            assignments.extend(
                OwnerAssignment(
                    candidate_id,
                    None,
                    "ambiguous",
                    "owner_multiplet_ambiguity",
                )
                for candidate_id in candidate_ids
            )
            continue
        primary, supporting = _primary_and_supporting(group)
        owner_id = f"OWN-{sample_stem}-{index:06d}"
        owners.append(
            SampleLocalMS1Owner(
                owner_id=owner_id,
                sample_stem=sample_stem,
                raw_file=primary.event.raw_file,
                precursor_mz=primary.event.precursor_mz,
                owner_apex_rt=primary.apex_rt,
                owner_peak_start_rt=primary.peak_start_rt,
                owner_peak_end_rt=primary.peak_end_rt,
                owner_area=primary.area,
                owner_height=primary.height,
                primary_identity_event=primary.event,
                supporting_events=tuple(item.event for item in supporting),
                identity_conflict=_identity_conflict(group),
                assignment_reason="owner_exact_apex_match",
            ),
        )
        assignments.append(
            OwnerAssignment(
                primary.event.candidate_id,
                owner_id,
                "primary",
                "primary_identity_event",
            ),
        )
        assignments.extend(
            OwnerAssignment(
                item.event.candidate_id,
                owner_id,
                "supporting",
                _assignment_reason(primary, item, alignment_config),
            )
            for item in supporting
        )
    return owners, assignments, ambiguous


def _candidate_components(
    items: list[_ResolvedCandidate],
    config: AlignmentConfig,
) -> list[list[_ResolvedCandidate]]:
    remaining = set(range(len(items)))
    components: list[list[_ResolvedCandidate]] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component = {seed}
        while stack:
            current = stack.pop()
            for candidate_index in tuple(remaining):
                relation = _owner_relation(
                    items[current],
                    items[candidate_index],
                    config,
                )
                if relation is not None:
                    remaining.remove(candidate_index)
                    stack.append(candidate_index)
                    component.add(candidate_index)
        components.append([items[index] for index in sorted(component)])
    return components


def _same_owner(
    left: _ResolvedCandidate,
    right: _ResolvedCandidate,
    config: AlignmentConfig,
) -> bool:
    return _owner_relation(left, right, config) in {
        "owner_exact_apex_match",
        "owner_tail_assignment",
    }


def _owner_relation(
    left: _ResolvedCandidate,
    right: _ResolvedCandidate,
    config: AlignmentConfig,
) -> str | None:
    if _ppm(left.event.precursor_mz, right.event.precursor_mz) > config.max_ppm:
        return None
    apex_delta_sec = abs(left.apex_rt - right.apex_rt) * 60.0
    overlap = _window_overlap_fraction(left, right)
    if _has_window_overlap(left, right) and _looks_like_unresolved_doublet(
        left,
        right,
        config,
    ):
        return "owner_multiplet_ambiguity"
    if (
        apex_delta_sec <= config.owner_apex_close_sec
        and overlap >= config.owner_window_overlap_fraction
    ):
        return "owner_exact_apex_match"
    if _seed_on_peak_tail(left, right, config) or _seed_on_peak_tail(
        right,
        left,
        config,
    ):
        return "owner_tail_assignment"
    return None


def _looks_like_unresolved_doublet(
    left: _ResolvedCandidate,
    right: _ResolvedCandidate,
    config: AlignmentConfig,
) -> bool:
    apex_delta_sec = abs(left.apex_rt - right.apex_rt) * 60.0
    lower_height = min(left.height, right.height)
    higher_height = max(left.height, right.height)
    return (
        apex_delta_sec > config.owner_apex_close_sec
        and lower_height / max(higher_height, 1e-12)
        > config.owner_tail_max_secondary_ratio
    )


def _seed_on_peak_tail(
    owner: _ResolvedCandidate,
    event: _ResolvedCandidate,
    config: AlignmentConfig,
) -> bool:
    seed_delta_sec = abs(event.event.seed_rt - owner.apex_rt) * 60.0
    return (
        owner.peak_start_rt <= event.event.seed_rt <= owner.peak_end_rt
        and seed_delta_sec <= config.owner_tail_seed_guard_sec
    )


def _component_is_ambiguous(
    group: list[_ResolvedCandidate],
    config: AlignmentConfig,
) -> bool:
    for left_index, left in enumerate(group):
        for right in group[left_index + 1 :]:
            if _owner_relation(left, right, config) == "owner_multiplet_ambiguity":
                return True
    return False


def _assignment_reason(
    primary: _ResolvedCandidate,
    supporting: _ResolvedCandidate,
    config: AlignmentConfig,
) -> str:
    seed_delta_sec = abs(supporting.event.seed_rt - primary.apex_rt) * 60.0
    if (
        seed_delta_sec > config.owner_apex_close_sec
        and seed_delta_sec <= config.owner_tail_seed_guard_sec
    ):
        return "owner_tail_assignment"
    relation = _owner_relation(primary, supporting, config)
    if relation == "owner_tail_assignment":
        return relation
    return "owner_exact_apex_match"



def _primary_and_supporting(
    group: list[_ResolvedCandidate],
) -> tuple[_ResolvedCandidate, list[_ResolvedCandidate]]:
    ordered = sorted(group, key=_resolved_sort_key)
    return ordered[0], ordered[1:]


def _resolved_sort_key(item: _ResolvedCandidate) -> tuple[object, ...]:
    return (
        -item.event.evidence_score,
        -item.event.seed_event_count,
        -item.area,
        abs(item.event.seed_rt - item.apex_rt),
        item.event.candidate_id,
    )


def _identity_conflict(group: list[_ResolvedCandidate]) -> bool:
    tags = {item.event.neutral_loss_tag for item in group}
    return len(tags) > 1


def _identity_event(candidate: Any, *, seed_rt: float) -> IdentityEvent:
    return IdentityEvent(
        candidate_id=str(candidate.candidate_id),
        sample_stem=str(candidate.sample_stem),
        raw_file=str(candidate.raw_file),
        neutral_loss_tag=str(candidate.neutral_loss_tag),
        precursor_mz=float(candidate.precursor_mz),
        product_mz=float(candidate.product_mz),
        observed_neutral_loss_da=float(candidate.observed_neutral_loss_da),
        seed_rt=seed_rt,
        evidence_score=int(getattr(candidate, "evidence_score", 0)),
        seed_event_count=int(getattr(candidate, "seed_event_count", 0)),
    )


def _candidate_seed_rt(candidate: Any) -> float:
    for field in ("best_seed_rt", "ms1_apex_rt"):
        value = getattr(candidate, field, None)
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        ):
            return float(value)
    raise ValueError("ownership candidate requires finite best_seed_rt or ms1_apex_rt")


def _window_overlap_fraction(
    left: _ResolvedCandidate,
    right: _ResolvedCandidate,
) -> float:
    intersection = min(left.peak_end_rt, right.peak_end_rt) - max(
        left.peak_start_rt,
        right.peak_start_rt,
    )
    if intersection <= 0:
        return 0.0
    left_width = left.peak_end_rt - left.peak_start_rt
    right_width = right.peak_end_rt - right.peak_start_rt
    denominator = min(left_width, right_width)
    if denominator <= 0:
        return 0.0
    return intersection / denominator


def _has_window_overlap(left: _ResolvedCandidate, right: _ResolvedCandidate) -> bool:
    return min(left.peak_end_rt, right.peak_end_rt) > max(
        left.peak_start_rt,
        right.peak_start_rt,
    )


def _validated_trace_arrays(
    rt: object,
    intensity: object,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    rt_array = np.asarray(rt, dtype=float)
    intensity_array = np.asarray(intensity, dtype=float)
    if (
        rt_array.ndim != 1
        or intensity_array.ndim != 1
        or rt_array.shape != intensity_array.shape
        or not np.all(np.isfinite(rt_array))
        or not np.all(np.isfinite(intensity_array))
    ):
        raise ValueError("ownership trace arrays must be finite one-dimensional pairs")
    return rt_array, intensity_array


def _ppm(left: float, right: float) -> float:
    denominator = max(abs(left), 1e-12)
    return abs(left - right) / denominator * 1_000_000.0
