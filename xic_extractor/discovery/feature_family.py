from dataclasses import replace

from xic_extractor.discovery.evidence_score import score_discovery_evidence
from xic_extractor.discovery.models import DiscoveryCandidate, DiscoverySettings

_APEX_RT_EPSILON_MIN = 1e-6


def assign_feature_families(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    settings: DiscoverySettings | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    family_assigned = _assign_strict_families(candidates)
    return _score_all_evidence(family_assigned, settings=settings)


def _assign_strict_families(
    candidates: tuple[DiscoveryCandidate, ...],
) -> tuple[DiscoveryCandidate, ...]:
    families: list[list[DiscoveryCandidate]] = []
    for candidate in candidates:
        family_index = _matching_family_index(candidate, families)
        if family_index is None:
            families.append([candidate])
        else:
            families[family_index].append(candidate)

    family_ids = _family_ids(families)
    assigned_by_candidate_id: dict[str, DiscoveryCandidate] = {}
    for family, family_id in zip(families, family_ids, strict=True):
        family_size = len(family)
        for candidate in family:
            assigned_by_candidate_id[candidate.candidate_id] = replace(
                candidate,
                feature_family_id=family_id,
                feature_family_size=family_size,
            )

    return tuple(
        assigned_by_candidate_id[candidate.candidate_id]
        for candidate in candidates
    )


def _score_all_evidence(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    settings: DiscoverySettings | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    scored: list[DiscoveryCandidate] = []
    for candidate in candidates:
        discovery_evidence = score_discovery_evidence(candidate, settings=settings)
        scored.append(
            replace(
                candidate,
                evidence_score=discovery_evidence.score,
                evidence_tier=discovery_evidence.tier,
                ms2_support=discovery_evidence.ms2_support,
                ms1_support=discovery_evidence.ms1_support,
                rt_alignment=discovery_evidence.rt_alignment,
            )
        )
    return tuple(scored)


def _matching_family_index(
    candidate: DiscoveryCandidate,
    families: list[list[DiscoveryCandidate]],
) -> int | None:
    for index, family in enumerate(families):
        if any(_same_feature_family(candidate, existing) for existing in family):
            return index
    return None


def _same_feature_family(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> bool:
    return (
        first.raw_file == second.raw_file
        and first.sample_stem == second.sample_stem
        and first.neutral_loss_tag == second.neutral_loss_tag
        and first.ms1_peak_found
        and second.ms1_peak_found
        and _peak_bounds_present(first)
        and _peak_bounds_present(second)
        and _apex_matches(first, second)
        and _peak_intervals_overlap(first, second)
    )


def _family_ids(families: list[list[DiscoveryCandidate]]) -> list[str]:
    sorted_families = sorted(families, key=_family_sort_key)
    family_id_by_key: dict[tuple[str, ...], str] = {}
    for index, family in enumerate(sorted_families, start=1):
        family_id_by_key[_family_identity_key(family)] = (
            f"{family[0].sample_stem}@F{index:04d}"
        )
    return [family_id_by_key[_family_identity_key(family)] for family in families]


def _family_sort_key(
    family: list[DiscoveryCandidate],
) -> tuple[str, float, float, str]:
    earliest = min(family, key=_candidate_sort_key)
    return _candidate_sort_key(earliest)


def _candidate_sort_key(candidate: DiscoveryCandidate) -> tuple[str, float, float, str]:
    apex = (
        candidate.ms1_apex_rt
        if candidate.ms1_apex_rt is not None
        else candidate.best_seed_rt
    )
    return (candidate.sample_stem, apex, candidate.best_seed_rt, candidate.candidate_id)


def _family_identity_key(family: list[DiscoveryCandidate]) -> tuple[str, ...]:
    return tuple(sorted(candidate.candidate_id for candidate in family))


def _peak_bounds_present(candidate: DiscoveryCandidate) -> bool:
    return (
        candidate.ms1_apex_rt is not None
        and candidate.ms1_peak_rt_start is not None
        and candidate.ms1_peak_rt_end is not None
        and candidate.ms1_peak_rt_start <= candidate.ms1_peak_rt_end
    )


def _apex_matches(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> bool:
    if first.ms1_apex_rt is None or second.ms1_apex_rt is None:
        return False
    return abs(first.ms1_apex_rt - second.ms1_apex_rt) <= _APEX_RT_EPSILON_MIN


def _peak_intervals_overlap(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> bool:
    first_start = first.ms1_peak_rt_start
    first_end = first.ms1_peak_rt_end
    second_start = second.ms1_peak_rt_start
    second_end = second.ms1_peak_rt_end
    if (
        first_start is None
        or first_end is None
        or second_start is None
        or second_end is None
    ):
        return False
    return max(first_start, second_start) <= min(first_end, second_end)
