from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import numpy as np

from xic_extractor.discovery.models import DiscoverySeed, DiscoverySettings
from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent


class MS2ScanSource(Protocol):
    def iter_ms2_scans(self, rt_min: float, rt_max: float) -> Iterator[Ms2ScanEvent]:
        """Yield MS2 scan events within the requested retention-time window."""


def collect_strict_nl_seeds(
    raw: MS2ScanSource,
    *,
    raw_file: Path,
    settings: DiscoverySettings,
) -> tuple[DiscoverySeed, ...]:
    seeds: list[DiscoverySeed] = []
    for event in raw.iter_ms2_scans(settings.rt_min, settings.rt_max):
        if event.parse_error is not None or event.scan is None:
            continue

        seed = _seed_from_scan(event.scan, raw_file=raw_file, settings=settings)
        if seed is not None:
            seeds.append(seed)

    return tuple(seeds)


def _seed_from_scan(
    scan: Ms2Scan,
    *,
    raw_file: Path,
    settings: DiscoverySettings,
) -> DiscoverySeed | None:
    neutral_loss_da = settings.neutral_loss_profile.neutral_loss_da
    expected_product = scan.precursor_mz - neutral_loss_da
    if expected_product <= 0.0 or scan.base_peak <= 0.0 or neutral_loss_da <= 0.0:
        return None

    masses = np.asarray(scan.masses, dtype=float)
    intensities = np.asarray(scan.intensities, dtype=float)
    if (
        masses.ndim != 1
        or intensities.ndim != 1
        or masses.size == 0
        or masses.size != intensities.size
    ):
        return None

    intensity_floor = scan.base_peak * settings.nl_min_intensity_ratio
    effective_product_search_ppm = max(
        settings.product_search_ppm,
        settings.nl_tolerance_ppm * neutral_loss_da / expected_product,
    )
    product_window_ppm = (
        np.abs(masses - expected_product) / expected_product * 1_000_000.0
    )
    search_mask = (
        (product_window_ppm <= effective_product_search_ppm)
        & (intensities >= intensity_floor)
        & np.isfinite(masses)
        & np.isfinite(intensities)
    )
    if not search_mask.any():
        return None

    candidates: list[DiscoverySeed] = []
    for index in np.flatnonzero(search_mask):
        product_mz = float(masses[int(index)])
        product_intensity = float(intensities[int(index)])
        observed_loss_da = scan.precursor_mz - product_mz
        observed_loss_error_ppm = (
            abs(observed_loss_da - neutral_loss_da) / neutral_loss_da * 1_000_000.0
        )
        if observed_loss_error_ppm > settings.nl_tolerance_ppm + 1e-9:
            continue

        candidates.append(
            DiscoverySeed(
                raw_file=raw_file,
                sample_stem=raw_file.stem,
                scan_number=scan.scan_number,
                rt=scan.rt,
                precursor_mz=scan.precursor_mz,
                product_mz=product_mz,
                product_intensity=product_intensity,
                neutral_loss_tag=settings.neutral_loss_profile.tag,
                configured_neutral_loss_da=neutral_loss_da,
                observed_neutral_loss_da=observed_loss_da,
                observed_loss_error_ppm=observed_loss_error_ppm,
            )
        )

    if not candidates:
        return None
    return min(
        candidates,
        key=lambda seed: (seed.observed_loss_error_ppm, -seed.product_intensity),
    )
