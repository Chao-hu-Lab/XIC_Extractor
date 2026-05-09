from dataclasses import replace

from xic_extractor.discovery.models import DiscoveryCandidate

_APEX_RT_EPSILON_MIN = 1e-6
_SUPERFAMILY_APEX_DELTA_MIN = 0.12
_SUPERFAMILY_OVERLAP_RATIO_MIN = 0.50
_PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def assign_feature_families(
    candidates: tuple[DiscoveryCandidate, ...],
) -> tuple[DiscoveryCandidate, ...]:
    family_assigned = _assign_strict_families(candidates)
    return _assign_superfamilies(family_assigned)


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


def _assign_superfamilies(
    candidates: tuple[DiscoveryCandidate, ...],
) -> tuple[DiscoveryCandidate, ...]:
    superfamilies: list[list[DiscoveryCandidate]] = []
    for candidate in candidates:
        family_index = _matching_superfamily_index(candidate, superfamilies)
        if family_index is None:
            superfamilies.append([candidate])
        else:
            superfamilies[family_index].append(candidate)

    superfamily_ids = _superfamily_ids(superfamilies)
    assigned_by_candidate_id: dict[str, DiscoveryCandidate] = {}
    for superfamily, superfamily_id in zip(
        superfamilies, superfamily_ids, strict=True
    ):
        representative = _representative(superfamily)
        superfamily_size = len(superfamily)
        confidence = "HIGH" if superfamily_size > 1 else "LOW"
        evidence = (
            "peak_boundary_overlap;apex_close"
            if superfamily_size > 1
            else "single_candidate"
        )
        for candidate in superfamily:
            assigned_by_candidate_id[candidate.candidate_id] = replace(
                candidate,
                feature_superfamily_id=superfamily_id,
                feature_superfamily_size=superfamily_size,
                feature_superfamily_role=(
                    "representative"
                    if candidate.candidate_id == representative.candidate_id
                    else "member"
                ),
                feature_superfamily_confidence=confidence,
                feature_superfamily_evidence=evidence,
            )

    return tuple(
        assigned_by_candidate_id[candidate.candidate_id]
        for candidate in candidates
    )


def _matching_family_index(
    candidate: DiscoveryCandidate,
    families: list[list[DiscoveryCandidate]],
) -> int | None:
    for index, family in enumerate(families):
        if any(_same_feature_family(candidate, existing) for existing in family):
            return index
    return None


def _matching_superfamily_index(
    candidate: DiscoveryCandidate,
    superfamilies: list[list[DiscoveryCandidate]],
) -> int | None:
    for index, superfamily in enumerate(superfamilies):
        if all(
            _same_feature_superfamily(candidate, existing)
            for existing in superfamily
        ):
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


def _same_feature_superfamily(
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
        and _apex_delta(first, second) <= _SUPERFAMILY_APEX_DELTA_MIN
        and _peak_overlap_ratio(first, second) >= _SUPERFAMILY_OVERLAP_RATIO_MIN
    )


def _family_ids(families: list[list[DiscoveryCandidate]]) -> list[str]:
    sorted_families = sorted(families, key=_family_sort_key)
    family_id_by_key: dict[tuple[str, ...], str] = {}
    for index, family in enumerate(sorted_families, start=1):
        family_id_by_key[_family_identity_key(family)] = (
            f"{family[0].sample_stem}@F{index:04d}"
        )
    return [family_id_by_key[_family_identity_key(family)] for family in families]


def _superfamily_ids(superfamilies: list[list[DiscoveryCandidate]]) -> list[str]:
    sorted_superfamilies = sorted(superfamilies, key=_family_sort_key)
    superfamily_id_by_key: dict[tuple[str, ...], str] = {}
    for index, superfamily in enumerate(sorted_superfamilies, start=1):
        superfamily_id_by_key[_family_identity_key(superfamily)] = (
            f"{superfamily[0].sample_stem}@SF{index:04d}"
        )
    return [
        superfamily_id_by_key[_family_identity_key(superfamily)]
        for superfamily in superfamilies
    ]


def _family_sort_key(
    family: list[DiscoveryCandidate],
) -> tuple[str, float, float, str]:
    earliest = min(family, key=lambda candidate: candidate.best_seed_rt)
    apex = (
        earliest.ms1_apex_rt
        if earliest.ms1_apex_rt is not None
        else earliest.best_seed_rt
    )
    return (earliest.sample_stem, apex, earliest.best_seed_rt, earliest.candidate_id)


def _family_identity_key(family: list[DiscoveryCandidate]) -> tuple[str, ...]:
    return tuple(sorted(candidate.candidate_id for candidate in family))


def _representative(
    candidates: list[DiscoveryCandidate],
) -> DiscoveryCandidate:
    return min(
        candidates,
        key=lambda candidate: (
            _PRIORITY_RANK.get(candidate.review_priority, len(_PRIORITY_RANK)),
            -candidate.seed_event_count,
            -candidate.ms2_product_max_intensity,
            -(candidate.ms1_area or 0.0),
            abs(candidate.neutral_loss_mass_error_ppm),
            candidate.best_seed_rt,
            candidate.candidate_id,
        ),
    )


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


def _apex_delta(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> float:
    if first.ms1_apex_rt is None or second.ms1_apex_rt is None:
        return float("inf")
    return abs(first.ms1_apex_rt - second.ms1_apex_rt)


def _peak_overlap_ratio(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> float:
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
        return 0.0
    overlap = max(0.0, min(first_end, second_end) - max(first_start, second_start))
    min_width = min(first_end - first_start, second_end - second_start)
    if min_width <= 0.0:
        return 0.0
    return overlap / min_width


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
