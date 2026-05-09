from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ReviewPriority = Literal["HIGH", "MEDIUM", "LOW"]

DISCOVERY_REVIEW_COLUMNS = (
    "review_priority",
    "candidate_id",
    "feature_family_id",
    "feature_family_size",
    "feature_superfamily_id",
    "feature_superfamily_size",
    "feature_superfamily_role",
    "feature_superfamily_confidence",
    "feature_superfamily_evidence",
    "precursor_mz",
    "product_mz",
    "observed_neutral_loss_da",
    "best_seed_rt",
    "seed_event_count",
    "ms1_peak_found",
    "ms1_apex_rt",
    "ms1_area",
    "ms2_product_max_intensity",
    "reason",
)

DISCOVERY_PROVENANCE_COLUMNS = (
    "raw_file",
    "sample_stem",
    "best_ms2_scan_id",
    "seed_scan_ids",
    "neutral_loss_tag",
    "configured_neutral_loss_da",
    "neutral_loss_mass_error_ppm",
    "rt_seed_min",
    "rt_seed_max",
    "ms1_search_rt_min",
    "ms1_search_rt_max",
    "ms1_seed_delta_min",
    "ms1_peak_rt_start",
    "ms1_peak_rt_end",
    "ms1_height",
    "ms1_trace_quality",
)

DISCOVERY_CANDIDATE_COLUMNS = DISCOVERY_REVIEW_COLUMNS + DISCOVERY_PROVENANCE_COLUMNS


@dataclass(frozen=True)
class NeutralLossProfile:
    tag: str
    neutral_loss_da: float


@dataclass(frozen=True)
class DiscoverySettings:
    neutral_loss_profile: NeutralLossProfile
    nl_tolerance_ppm: float = 20.0
    precursor_mz_tolerance_ppm: float = 20.0
    product_mz_tolerance_ppm: float = 20.0
    product_search_ppm: float = 50.0
    nl_min_intensity_ratio: float = 0.01
    seed_rt_gap_min: float = 0.20
    ms1_search_padding_min: float = 0.20
    rt_min: float = 0.0
    rt_max: float = 999.0
    resolver_mode: str = "local_minimum"


@dataclass(frozen=True)
class DiscoverySeed:
    raw_file: Path
    sample_stem: str
    scan_number: int
    rt: float
    precursor_mz: float
    product_mz: float
    product_intensity: float
    neutral_loss_tag: str
    configured_neutral_loss_da: float
    observed_neutral_loss_da: float
    observed_loss_error_ppm: float


@dataclass(frozen=True)
class DiscoverySeedGroup:
    raw_file: Path
    sample_stem: str
    seeds: tuple[DiscoverySeed, ...]
    neutral_loss_tag: str
    configured_neutral_loss_da: float
    precursor_mz: float
    product_mz: float
    observed_neutral_loss_da: float
    neutral_loss_mass_error_ppm: float
    rt_seed_min: float
    rt_seed_max: float


@dataclass(frozen=True)
class DiscoveryCandidate:
    review_priority: ReviewPriority
    candidate_id: str
    precursor_mz: float
    product_mz: float
    observed_neutral_loss_da: float
    best_seed_rt: float
    seed_event_count: int
    ms1_peak_found: bool
    ms1_apex_rt: float | None
    ms1_area: float | None
    ms2_product_max_intensity: float
    reason: str
    raw_file: Path
    sample_stem: str
    best_ms2_scan_id: int
    seed_scan_ids: tuple[int, ...]
    neutral_loss_tag: str
    configured_neutral_loss_da: float
    neutral_loss_mass_error_ppm: float
    rt_seed_min: float
    rt_seed_max: float
    ms1_search_rt_min: float
    ms1_search_rt_max: float
    ms1_seed_delta_min: float | None
    ms1_peak_rt_start: float | None
    ms1_peak_rt_end: float | None
    ms1_height: float | None
    ms1_trace_quality: str
    feature_family_id: str = ""
    feature_family_size: int = 1
    feature_superfamily_id: str = ""
    feature_superfamily_size: int = 1
    feature_superfamily_role: str = "representative"
    feature_superfamily_confidence: str = "LOW"
    feature_superfamily_evidence: str = "single_candidate"

    @classmethod
    def from_values(
        cls,
        *,
        raw_file: Path,
        sample_stem: str,
        precursor_mz: float,
        product_mz: float,
        observed_neutral_loss_da: float,
        best_seed: DiscoverySeed,
        seed_scan_ids: tuple[int, ...],
        neutral_loss_tag: str,
        configured_neutral_loss_da: float,
        neutral_loss_mass_error_ppm: float,
        rt_seed_min: float,
        rt_seed_max: float,
        ms1_search_rt_min: float,
        ms1_search_rt_max: float,
        ms1_seed_delta_min: float | None,
        ms1_peak_rt_start: float | None,
        ms1_peak_rt_end: float | None,
        ms1_height: float | None,
        ms1_trace_quality: str,
        seed_event_count: int,
        ms1_peak_found: bool,
        ms1_apex_rt: float | None,
        ms1_area: float | None,
        ms2_product_max_intensity: float,
        review_priority: ReviewPriority,
        reason: str,
    ) -> "DiscoveryCandidate":
        return cls(
            review_priority=review_priority,
            candidate_id=f"{sample_stem}#{best_seed.scan_number}",
            precursor_mz=precursor_mz,
            product_mz=product_mz,
            observed_neutral_loss_da=observed_neutral_loss_da,
            best_seed_rt=best_seed.rt,
            seed_event_count=seed_event_count,
            ms1_peak_found=ms1_peak_found,
            ms1_apex_rt=ms1_apex_rt,
            ms1_area=ms1_area,
            ms2_product_max_intensity=ms2_product_max_intensity,
            reason=reason,
            raw_file=raw_file,
            sample_stem=sample_stem,
            best_ms2_scan_id=best_seed.scan_number,
            seed_scan_ids=seed_scan_ids,
            neutral_loss_tag=neutral_loss_tag,
            configured_neutral_loss_da=configured_neutral_loss_da,
            neutral_loss_mass_error_ppm=neutral_loss_mass_error_ppm,
            rt_seed_min=rt_seed_min,
            rt_seed_max=rt_seed_max,
            ms1_search_rt_min=ms1_search_rt_min,
            ms1_search_rt_max=ms1_search_rt_max,
            ms1_seed_delta_min=ms1_seed_delta_min,
            ms1_peak_rt_start=ms1_peak_rt_start,
            ms1_peak_rt_end=ms1_peak_rt_end,
            ms1_height=ms1_height,
            ms1_trace_quality=ms1_trace_quality,
        )
