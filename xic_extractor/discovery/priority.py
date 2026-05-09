from xic_extractor.discovery.models import DiscoverySettings, ReviewPriority


def assign_review_priority(
    *,
    seed_event_count: int,
    ms1_peak_found: bool,
    ms1_seed_delta_min: float | None,
    settings: DiscoverySettings,
) -> ReviewPriority:
    if (
        seed_event_count >= 2
        and ms1_peak_found
        and ms1_seed_delta_min is not None
        and ms1_seed_delta_min <= settings.ms1_search_padding_min
    ):
        return "HIGH"
    if ms1_peak_found:
        return "MEDIUM"
    return "LOW"


def build_candidate_reason(
    *,
    seed_event_count: int,
    ms1_peak_found: bool,
    ms1_seed_delta_min: float | None,
    settings: DiscoverySettings,
) -> str:
    if not ms1_peak_found:
        return "strict MS2 NL seed; MS1 peak missing"
    if (
        seed_event_count >= 2
        and ms1_seed_delta_min is not None
        and ms1_seed_delta_min <= settings.ms1_search_padding_min
    ):
        return "strong MS2 NL seed group; MS1 peak found near seed RT"
    if (
        seed_event_count >= 2
        and ms1_seed_delta_min is not None
        and ms1_seed_delta_min > settings.ms1_search_padding_min
    ):
        return "MS1 peak offset from seed RT"
    return "single MS2 NL seed; MS1 peak found"
