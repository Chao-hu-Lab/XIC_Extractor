from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from xic_extractor.neutral_loss import CandidateMS2Evidence
from xic_extractor.peak_detection.models import PeakCandidate, PeakCandidateScore

_SOFT_TRACE_QUALITY_FLAGS = {"low_trace_continuity", "poor_edge_recovery"}
_HARD_LOCAL_CONCERN_LABELS = {
    "hard_quality_flag",
    "low_scan_support",
    "rt_centrality_poor",
    "shape_poor",
}

EvidenceSource = Literal[
    "targeted_peak",
    "discovery_candidate",
    "alignment_cell",
]


@dataclass(frozen=True)
class CommonEvidence:
    source: EvidenceSource
    source_id: str = ""
    provenance: str = ""
    ms1_peak_found: bool | None = None
    ms1_apex_rt_min: float | None = None
    ms1_area: float | None = None
    ms1_height: float | None = None
    ms1_peak_rt_start: float | None = None
    ms1_peak_rt_end: float | None = None
    rt_delta_min: float | None = None
    trace_quality: str = ""
    scan_support_score: float | None = None
    neutral_loss_tag: str = ""
    configured_neutral_loss_da: float | None = None
    observed_neutral_loss_da: float | None = None
    neutral_loss_error_ppm: float | None = None
    seed_event_count: int | None = None
    ms2_present: bool | None = None
    nl_match: bool | None = None
    ms2_trace_strength: str = ""
    confidence: str = ""
    evidence_score: int | None = None
    review_priority: str = ""
    reason: str = ""


@dataclass(frozen=True)
class EvidenceSignalSet:
    support_labels: tuple[str, ...] = ()
    concern_labels: tuple[str, ...] = ()
    proposal_sources: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    ms2_present: bool | None = None
    nl_match: bool | None = None
    raw_score: float | None = None


def common_evidence_from_targeted_candidate(
    candidate: PeakCandidate,
    *,
    score: PeakCandidateScore | None = None,
    candidate_ms2_evidence: CandidateMS2Evidence | None = None,
    target_label: str = "",
) -> CommonEvidence:
    return CommonEvidence(
        source="targeted_peak",
        source_id=target_label,
        provenance="selected_or_candidate",
        ms1_peak_found=True,
        ms1_apex_rt_min=candidate.selection_apex_rt,
        ms1_area=candidate.peak.area,
        ms1_height=candidate.raw_apex_intensity,
        ms1_peak_rt_start=candidate.peak.peak_start,
        ms1_peak_rt_end=candidate.peak.peak_end,
        trace_quality=_targeted_trace_quality(candidate),
        scan_support_score=_scan_support_from_candidate(candidate),
        neutral_loss_error_ppm=(
            candidate_ms2_evidence.best_loss_ppm
            if candidate_ms2_evidence is not None
            else None
        ),
        ms2_present=(
            candidate_ms2_evidence.ms2_present
            if candidate_ms2_evidence is not None
            else None
        ),
        nl_match=(
            candidate_ms2_evidence.nl_match
            if candidate_ms2_evidence is not None
            else None
        ),
        ms2_trace_strength=(
            candidate_ms2_evidence.trace.strength
            if candidate_ms2_evidence is not None
            else ""
        ),
        confidence=score.confidence if score is not None else "",
        evidence_score=score.raw_score if score is not None else None,
        reason=score.reason if score is not None else "",
    )


def common_evidence_from_discovery_candidate(candidate: Any) -> CommonEvidence:
    seed_event_count = _optional_int(_field(candidate, "seed_event_count"))
    neutral_loss_error_ppm = _optional_float(
        _field(candidate, "neutral_loss_mass_error_ppm")
    )
    return CommonEvidence(
        source="discovery_candidate",
        source_id=_text_field(candidate, "candidate_id"),
        provenance="original_discovery_seed",
        ms1_peak_found=_optional_bool(_field(candidate, "ms1_peak_found")),
        ms1_apex_rt_min=_optional_float(_field(candidate, "ms1_apex_rt")),
        ms1_area=_optional_float(_field(candidate, "ms1_area")),
        ms1_height=_optional_float(_field(candidate, "ms1_height")),
        ms1_peak_rt_start=_optional_float(_field(candidate, "ms1_peak_rt_start")),
        ms1_peak_rt_end=_optional_float(_field(candidate, "ms1_peak_rt_end")),
        rt_delta_min=_optional_float(_field(candidate, "ms1_seed_delta_min")),
        trace_quality=_text_field(candidate, "ms1_trace_quality"),
        scan_support_score=_optional_float(_field(candidate, "ms1_scan_support_score")),
        neutral_loss_tag=_text_field(candidate, "neutral_loss_tag"),
        configured_neutral_loss_da=_optional_float(
            _field(candidate, "configured_neutral_loss_da")
        ),
        observed_neutral_loss_da=_optional_float(
            _field(candidate, "observed_neutral_loss_da")
        ),
        neutral_loss_error_ppm=neutral_loss_error_ppm,
        seed_event_count=seed_event_count,
        ms2_present=seed_event_count is not None and seed_event_count > 0,
        nl_match=neutral_loss_error_ppm is not None,
        evidence_score=_optional_int(_field(candidate, "evidence_score")),
        review_priority=_text_field(candidate, "review_priority"),
        reason=_text_field(candidate, "reason"),
    )


def common_evidence_from_aligned_cell(
    cell: Any,
    *,
    neutral_loss_tag: str = "",
    family_id: str = "",
) -> CommonEvidence:
    status = _text_field(cell, "status")
    sample_stem = _text_field(cell, "sample_stem")
    provenance = status or "unknown"
    source_id = f"{family_id}:{sample_stem}" if family_id else sample_stem
    return CommonEvidence(
        source="alignment_cell",
        source_id=source_id,
        provenance=provenance,
        ms1_peak_found=status in {"detected", "rescued"},
        ms1_apex_rt_min=_optional_float(_field(cell, "apex_rt")),
        ms1_area=_optional_float(_field(cell, "area")),
        ms1_height=_optional_float(_field(cell, "height")),
        ms1_peak_rt_start=_optional_float(_field(cell, "peak_start_rt")),
        ms1_peak_rt_end=_optional_float(_field(cell, "peak_end_rt")),
        rt_delta_min=_delta_sec_to_min(_optional_float(_field(cell, "rt_delta_sec"))),
        trace_quality=_text_field(cell, "trace_quality"),
        scan_support_score=_optional_float(_field(cell, "scan_support_score")),
        neutral_loss_tag=neutral_loss_tag,
        reason=_text_field(cell, "reason"),
    )


def canonical_support_labels(evidence: CommonEvidence) -> tuple[str, ...]:
    labels: list[str] = []
    if evidence.ms1_peak_found:
        labels.append("ms1_peak")
    if _positive(evidence.ms1_area):
        labels.append("positive_area")
    if evidence.ms2_present:
        labels.append("ms2_present")
    if evidence.nl_match:
        labels.append("nl_match")
    if evidence.seed_event_count is not None and evidence.seed_event_count >= 2:
        labels.append("multi_seed")
    if evidence.scan_support_score is not None:
        labels.append("scan_support")
    return tuple(labels)


def canonical_concern_labels(evidence: CommonEvidence) -> tuple[str, ...]:
    labels: list[str] = []
    if evidence.ms1_peak_found is False:
        labels.append("missing_ms1_peak")
    if evidence.ms1_peak_found and not _positive(evidence.ms1_area):
        labels.append("non_positive_area")
    if evidence.nl_match is False:
        labels.append("nl_fail")
    if evidence.trace_quality and evidence.trace_quality != "clean":
        labels.append("trace_quality_review")
    if evidence.provenance in {"rescued", "owner_backfill"}:
        labels.append("backfill_provenance")
    return tuple(labels)


def classify_evidence_consistency(signals: EvidenceSignalSet) -> tuple[str, ...]:
    support = _label_set(signals.support_labels)
    concerns = _label_set(signals.concern_labels)
    sources = _label_set(signals.proposal_sources)
    quality_flags = _label_set(signals.quality_flags)

    labels: list[str] = []
    has_shape_context = (
        "shape_clean" in support
        or "centwave_cwt" in sources
        or "cwt_same_apex_support" in support
    )
    hard_quality_flags = quality_flags - _SOFT_TRACE_QUALITY_FLAGS
    trace_context_ok = "trace_clean" in support or not hard_quality_flags
    ms1_coherent = (
        "local_sn_strong" in support
        and trace_context_ok
        and has_shape_context
    )
    hard_local_conflict = bool(hard_quality_flags) or bool(
        concerns & _HARD_LOCAL_CONCERN_LABELS
    )
    if hard_local_conflict:
        labels.append("hard_local_quality_conflict")
    elif ms1_coherent:
        labels.append("ms1_coherent")

    missing_ms2 = signals.ms2_present is False or "no_ms2" in concerns
    if missing_ms2:
        labels.append("missing_ms2")

    nl_failed = signals.nl_match is False or "nl_fail" in concerns
    score_not_negative = signals.raw_score is None or signals.raw_score >= 0
    if nl_failed:
        if (
            ms1_coherent
            and not hard_local_conflict
            and not missing_ms2
            and score_not_negative
        ):
            labels.append("plausible_nl_dropout")
        else:
            labels.append("hard_nl_conflict")

    return tuple(labels)


def _targeted_trace_quality(candidate: PeakCandidate) -> str:
    return "review" if candidate.quality_flags else "clean"


def _scan_support_from_candidate(candidate: PeakCandidate) -> float | None:
    if candidate.region_scan_count is None:
        return None
    return float(candidate.region_scan_count)


def _field(item: Any, key: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(key)
    return getattr(item, key, None)


def _text_field(item: Any, key: str) -> str:
    value = _field(item, key)
    if value is None:
        return ""
    return str(value)


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _delta_sec_to_min(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 60.0


def _positive(value: float | None) -> bool:
    return value is not None and value > 0.0


def _label_set(values: tuple[str, ...]) -> frozenset[str]:
    return frozenset(_normalize_label(value) for value in values if value)


def _normalize_label(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )
