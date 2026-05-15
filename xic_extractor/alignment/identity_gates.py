from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

EXTREME_BACKFILL_REASON = "extreme_backfill_dependency"
WEAK_SEED_BACKFILL_REASON = "weak_seed_backfill_dependency"

SeedQualityStatus = Literal["unavailable", "adequate", "weak"]

_EXTREME_BACKFILL_MIN_RESCUE_FRACTION = 0.70
_EXTREME_BACKFILL_MAX_DETECTED_SUPPORT = 2
_WEAK_SEED_BACKFILL_MIN_RESCUE_FRACTION = 0.60
_WEAK_SEED_BACKFILL_MAX_DETECTED_SUPPORT = 3
_WEAK_SEED_MIN_EVIDENCE_SCORE = 60
_WEAK_SEED_MIN_EVENT_COUNT = 2
_WEAK_SEED_MAX_ABS_NL_PPM = 10.0


@dataclass(frozen=True)
class DetectedSeedRef:
    sample_stem: str
    source_candidate_id: str


@dataclass(frozen=True)
class SeedQualitySummary:
    available: bool
    min_evidence_score: float | None = None
    min_seed_event_count: float | None = None
    max_abs_nl_ppm: float | None = None
    min_scan_support_score: float | None = None
    missing_detected_candidate_count: int = 0

    @property
    def weak(self) -> bool:
        return self.available and (
            self.missing_detected_candidate_count > 0
            or (
                self.min_evidence_score is not None
                and self.min_evidence_score < _WEAK_SEED_MIN_EVIDENCE_SCORE
            )
            or (
                self.min_seed_event_count is not None
                and self.min_seed_event_count < _WEAK_SEED_MIN_EVENT_COUNT
            )
            or (
                self.max_abs_nl_ppm is not None
                and self.max_abs_nl_ppm > _WEAK_SEED_MAX_ABS_NL_PPM
            )
        )

    @property
    def status(self) -> SeedQualityStatus:
        if not self.available:
            return "unavailable"
        return "weak" if self.weak else "adequate"


SeedCandidateLookup = (
    Mapping[str, Any]
    | Mapping[tuple[str, str], Any]
    | Callable[[DetectedSeedRef], Any | None]
)


def classify_single_dr_backfill_dependency(
    *,
    neutral_loss_tag: str,
    q_detected: int,
    q_rescue: int,
    cell_count: int,
    seed_quality: SeedQualitySummary | None,
) -> str | None:
    if not is_dr_neutral_loss_tag(neutral_loss_tag):
        return None
    if q_detected <= 0 or cell_count <= 0:
        return None

    rescue_fraction = q_rescue / cell_count
    if (
        q_detected <= _EXTREME_BACKFILL_MAX_DETECTED_SUPPORT
        and rescue_fraction >= _EXTREME_BACKFILL_MIN_RESCUE_FRACTION
    ):
        return EXTREME_BACKFILL_REASON
    if (
        q_detected <= _WEAK_SEED_BACKFILL_MAX_DETECTED_SUPPORT
        and rescue_fraction >= _WEAK_SEED_BACKFILL_MIN_RESCUE_FRACTION
        and seed_quality is not None
        and seed_quality.weak
    ):
        return WEAK_SEED_BACKFILL_REASON
    return None


def summarize_detected_seed_quality(
    detected_seeds: Sequence[DetectedSeedRef],
    candidate_lookup: SeedCandidateLookup | None,
    *,
    enrichment_available: bool,
) -> SeedQualitySummary:
    if not enrichment_available:
        return SeedQualitySummary(available=False)
    if candidate_lookup is None:
        return SeedQualitySummary(available=False)

    candidates: list[Any] = []
    missing_count = 0
    for seed in detected_seeds:
        candidate = lookup_seed_candidate(seed, candidate_lookup)
        if candidate is None:
            missing_count += 1
            continue
        candidates.append(candidate)

    return SeedQualitySummary(
        available=True,
        min_evidence_score=_min_metric(candidates, "evidence_score"),
        min_seed_event_count=_min_metric(candidates, "seed_event_count"),
        max_abs_nl_ppm=_max_abs_metric(
            candidates,
            "neutral_loss_mass_error_ppm",
        ),
        min_scan_support_score=_min_metric(candidates, "ms1_scan_support_score"),
        missing_detected_candidate_count=missing_count,
    )


def lookup_seed_candidate(
    seed: DetectedSeedRef,
    candidate_lookup: SeedCandidateLookup,
) -> Any | None:
    if callable(candidate_lookup):
        return candidate_lookup(seed)
    for key in candidate_lookup_keys(seed.source_candidate_id):
        tuple_key = (seed.sample_stem, key)
        if tuple_key in candidate_lookup:
            return candidate_lookup[tuple_key]  # type: ignore[index]
        fallback_tuple_key = ("", key)
        if fallback_tuple_key in candidate_lookup:
            return candidate_lookup[fallback_tuple_key]  # type: ignore[index]
        if key in candidate_lookup:
            return candidate_lookup[key]  # type: ignore[index]
    return None


def candidate_lookup_keys(source_candidate_id: str) -> tuple[str, ...]:
    source = source_candidate_id.strip()
    if not source:
        return ()
    if "#" not in source:
        return (source,)
    head, tail = source.split("#", 1)
    return (source, head, tail)


def is_dr_neutral_loss_tag(tag: str) -> bool:
    return tag == "dR" or tag.endswith("_dR")


def _min_metric(candidates: Sequence[Any], key: str) -> float | None:
    values = tuple(
        value
        for candidate in candidates
        for value in (_number_field(candidate, key),)
        if value is not None
    )
    return min(values) if values else None


def _max_abs_metric(candidates: Sequence[Any], key: str) -> float | None:
    values = tuple(
        abs(value)
        for candidate in candidates
        for value in (_number_field(candidate, key),)
        if value is not None
    )
    return max(values) if values else None


def _number_field(item: Any, key: str) -> float | None:
    value = item.get(key) if isinstance(item, Mapping) else getattr(item, key, None)
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
