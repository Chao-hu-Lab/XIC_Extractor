import math
from collections.abc import Iterable
from pathlib import Path

from xic_extractor.discovery.models import (
    DiscoverySeed,
    DiscoverySeedGroup,
    DiscoverySettings,
)


def group_discovery_seeds(
    seeds: Iterable[DiscoverySeed],
    *,
    settings: DiscoverySettings,
) -> tuple[DiscoverySeedGroup, ...]:
    sorted_seeds = sorted(seeds, key=_seed_sort_key)
    if not sorted_seeds:
        return ()

    active_groups: list[list[DiscoverySeed]] = []

    for seed in sorted_seeds:
        matching_group = _matching_active_group(
            seed, active_groups, settings=settings
        )
        if matching_group is None:
            active_groups.append([seed])
        else:
            matching_group.append(seed)

    return tuple(_build_group(group) for group in active_groups)


def _matching_active_group(
    seed: DiscoverySeed,
    active_groups: list[list[DiscoverySeed]],
    *,
    settings: DiscoverySettings,
) -> list[DiscoverySeed] | None:
    for group in active_groups:
        if _can_join_group(seed, group, settings=settings):
            return group
    return None


def _can_join_group(
    seed: DiscoverySeed,
    current: list[DiscoverySeed],
    *,
    settings: DiscoverySettings,
) -> bool:
    first = current[0]
    previous = current[-1]
    return (
        seed.raw_file == first.raw_file
        and seed.sample_stem == first.sample_stem
        and seed.neutral_loss_tag == first.neutral_loss_tag
        and seed.rt - previous.rt <= settings.seed_rt_gap_min
        and all(
            _within_ppm(
                seed.precursor_mz,
                existing.precursor_mz,
                settings.precursor_mz_tolerance_ppm,
            )
            and _within_ppm(
                seed.product_mz,
                existing.product_mz,
                settings.product_mz_tolerance_ppm,
            )
            and _within_ppm(
                seed.observed_neutral_loss_da,
                existing.observed_neutral_loss_da,
                settings.nl_tolerance_ppm,
            )
            for existing in current
        )
    )


def _build_group(seeds: list[DiscoverySeed]) -> DiscoverySeedGroup:
    best_seed = _best_seed(seeds)
    return DiscoverySeedGroup(
        raw_file=best_seed.raw_file,
        sample_stem=best_seed.sample_stem,
        seeds=tuple(sorted(seeds, key=_seed_sort_key)),
        neutral_loss_tag=best_seed.neutral_loss_tag,
        configured_neutral_loss_da=best_seed.configured_neutral_loss_da,
        precursor_mz=best_seed.precursor_mz,
        product_mz=best_seed.product_mz,
        observed_neutral_loss_da=best_seed.observed_neutral_loss_da,
        neutral_loss_mass_error_ppm=best_seed.observed_loss_error_ppm,
        rt_seed_min=min(seed.rt for seed in seeds),
        rt_seed_max=max(seed.rt for seed in seeds),
    )


def _best_seed(seeds: Iterable[DiscoverySeed]) -> DiscoverySeed:
    return min(
        seeds,
        key=lambda seed: (
            -seed.product_intensity,
            abs(seed.observed_loss_error_ppm),
            seed.rt,
            seed.scan_number,
        ),
    )


def _within_ppm(a: float, b: float, tolerance_ppm: float) -> bool:
    if (
        not math.isfinite(a)
        or not math.isfinite(b)
        or not math.isfinite(tolerance_ppm)
        or a <= 0
        or b <= 0
        or tolerance_ppm < 0
    ):
        return False
    return abs(a - b) / abs(b) * 1_000_000.0 <= tolerance_ppm


def _seed_sort_key(
    seed: DiscoverySeed,
) -> tuple[str, str, str, float, int, float, float]:
    return (
        _path_sort_key(seed.raw_file),
        seed.sample_stem,
        seed.neutral_loss_tag,
        seed.rt,
        seed.scan_number,
        seed.precursor_mz,
        seed.product_mz,
    )


def _path_sort_key(path: Path) -> str:
    return str(path)
