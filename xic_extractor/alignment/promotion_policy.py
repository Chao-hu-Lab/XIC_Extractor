from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from xic_extractor.alignment.cell_quality import CellQualityDecision
from xic_extractor.alignment.identity_gates import (
    EXTREME_BACKFILL_REASON,
    WEAK_SEED_BACKFILL_REASON,
    WEAK_SEED_TOLERATED_REASON,
    SeedQualitySummary,
    classify_single_dr_backfill_dependency,
    is_dr_neutral_loss_tag,
)
from xic_extractor.alignment.matrix import AlignedCell

CELL_EVIDENCE_SUPPORTED_REASON = "cell_evidence_supported_backfill"
DDA_LIMITED_MS2_SHAPE_REASON = "dda_limited_ms2_but_ms1_shape_supported"
NEIGHBOR_INTERFERENCE_BLOCKED_REASON = "neighboring_ms1_interference_blocked"
LOW_MS1_COVERAGE_BLOCKED_REASON = "low_ms1_assessable_coverage_blocked"
RESCUE_ONLY_BLOCKED_REASON = "rescue_only_blocked"
HIGH_BACKFILL_CAPPED_FLAG = "high_backfill_dependency_capped"

PromotionState = Literal["not_applicable", "supported", "blocked"]

_POLICY_BACKFILL_REASONS = {
    EXTREME_BACKFILL_REASON,
    WEAK_SEED_BACKFILL_REASON,
    WEAK_SEED_TOLERATED_REASON,
}
_SUPPORTED_PRIMARY_EVIDENCE = {
    "owner_complete_link",
    "owner_identity",
    "cid_nl_only",
    "multi_sample_detected",
}
_TRACE_CONTINUITY_LABELS = {
    "clean",
    "good",
    "family_centered",
}
_CHEMICAL_MARKERS = (
    "neutral_loss",
    "nl_match",
    "product",
    "fragment",
    "chemical",
    "ms2",
)
_INTERFERENCE_MARKERS = ("neighbor", "interference")
_LOW_COVERAGE_MARKERS = (
    "low_scan_support",
    "skipped_low_scan_support",
    "coverage",
    "unassessable",
)
_MIN_SCAN_SUPPORT = 0.5
_LOW_SCAN_SUPPORT_MAX = 0.2
_MAX_RT_DELTA_SEC = 180.0


@dataclass(frozen=True)
class BackfillCellEvidence:
    sample_stem: str
    status: str
    quality_status: str = ""
    area: float | None = None
    apex_rt: float | None = None
    height: float | None = None
    peak_start_rt: float | None = None
    peak_end_rt: float | None = None
    rt_delta_sec: float | None = None
    trace_quality: str = ""
    scan_support_score: float | None = None
    source_candidate_id: str = ""
    reason: str = ""
    region_local_mixture_diagnostic: str = ""
    region_local_mixture_reason: str = ""
    region_review_reason: str = ""
    region_shadow_status: str = ""
    region_shadow_verdict: str = ""

    @property
    def is_rescued_quantifiable(self) -> bool:
        if self.quality_status:
            return self.quality_status == "rescue_quantifiable"
        return (
            self.status == "rescued"
            and _positive(self.area)
            and self.local_apex_supported
        )

    @property
    def has_complete_peak(self) -> bool:
        return all(
            _finite(value)
            for value in (
                self.area,
                self.apex_rt,
                self.height,
                self.peak_start_rt,
                self.peak_end_rt,
            )
        )

    @property
    def local_apex_supported(self) -> bool:
        if not self.has_complete_peak:
            return False
        assert self.apex_rt is not None
        assert self.peak_start_rt is not None
        assert self.peak_end_rt is not None
        if not self.peak_start_rt <= self.apex_rt <= self.peak_end_rt:
            return False
        return (
            self.rt_delta_sec is not None
            and abs(self.rt_delta_sec) <= _MAX_RT_DELTA_SEC
        )

    @property
    def scan_support(self) -> bool:
        return (
            self.scan_support_score is not None
            and self.scan_support_score >= _MIN_SCAN_SUPPORT
        )

    @property
    def low_scan_support(self) -> bool:
        return (
            self.scan_support_score is not None
            and self.scan_support_score <= _LOW_SCAN_SUPPORT_MAX
        )

    @property
    def trace_continuity(self) -> bool:
        return _normalize(self.trace_quality) in _TRACE_CONTINUITY_LABELS

    @property
    def chemical_support(self) -> bool:
        return _contains_marker(self.reason, _CHEMICAL_MARKERS)

    @property
    def selected_peak_dominance(self) -> bool:
        text = " ".join(
            (
                self.region_local_mixture_diagnostic,
                self.region_local_mixture_reason,
                self.region_review_reason,
                self.region_shadow_status,
                self.region_shadow_verdict,
            ),
        ).lower()
        return (
            "one_envelope_supported" in text
            or "selected_apex" in text
            or "selected_region" in text
            or "dominant" in text
        )

    @property
    def high_neighbor_interference(self) -> bool:
        text = " ".join(
            (
                self.reason,
                self.region_local_mixture_diagnostic,
                self.region_local_mixture_reason,
                self.region_review_reason,
                self.region_shadow_status,
                self.region_shadow_verdict,
            ),
        ).lower()
        return any(marker in text for marker in _INTERFERENCE_MARKERS)

    @property
    def low_assessable_coverage(self) -> bool:
        text = " ".join(
            (
                self.reason,
                self.region_local_mixture_diagnostic,
                self.region_local_mixture_reason,
                self.region_review_reason,
                self.region_shadow_status,
                self.region_shadow_verdict,
            ),
        ).lower()
        return self.low_scan_support or any(marker in text for marker in _LOW_COVERAGE_MARKERS)

    @property
    def additional_ms1_support(self) -> bool:
        return self.scan_support or self.trace_continuity or self.selected_peak_dominance

    @property
    def supported_for_backfill(self) -> bool:
        return (
            self.local_apex_supported
            and not self.high_neighbor_interference
            and not self.low_assessable_coverage
            and (self.additional_ms1_support or self.chemical_support)
        )


@dataclass(frozen=True)
class BackfillPromotionEvidence:
    neutral_loss_tag: str
    primary_evidence: str
    q_detected: int
    q_rescue: int
    cell_count: int
    duplicate_count: int
    ambiguous_count: int
    backfill_dependency: str | None
    seed_quality: SeedQualitySummary | None
    cells: tuple[BackfillCellEvidence, ...] = ()


@dataclass(frozen=True)
class BackfillPromotionDecision:
    state: PromotionState
    reason: str = ""
    confidence: str = ""
    flags: tuple[str, ...] = ()
    supported_rescue_count: int = 0
    assessed_rescue_count: int = 0

    @property
    def supported(self) -> bool:
        return self.state == "supported"

    @property
    def blocked(self) -> bool:
        return self.state == "blocked"


def evidence_from_alignment(
    *,
    neutral_loss_tag: str,
    primary_evidence: str,
    q_detected: int,
    q_rescue: int,
    duplicate_count: int,
    ambiguous_count: int,
    backfill_dependency: str | None,
    seed_quality: SeedQualitySummary | None,
    cells: Sequence[AlignedCell],
    cell_quality: Sequence[CellQualityDecision],
) -> BackfillPromotionEvidence:
    quality_by_sample = {decision.sample_stem: decision for decision in cell_quality}
    return BackfillPromotionEvidence(
        neutral_loss_tag=neutral_loss_tag,
        primary_evidence=primary_evidence,
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=len(cell_quality),
        duplicate_count=duplicate_count,
        ambiguous_count=ambiguous_count,
        backfill_dependency=backfill_dependency,
        seed_quality=seed_quality,
        cells=tuple(
            _cell_from_aligned(cell, quality_by_sample.get(cell.sample_stem))
            for cell in cells
        ),
    )


def evidence_from_tsv_rows(
    review_row: Mapping[str, str],
    cell_rows: Sequence[Mapping[str, str]],
    *,
    seed_quality: SeedQualitySummary | None,
    sample_count: int,
) -> BackfillPromotionEvidence:
    q_detected = _int_value(
        review_row.get("quantifiable_detected_count", "")
        or review_row.get("detected_count", ""),
    )
    q_rescue = _int_value(
        review_row.get("quantifiable_rescue_count", "")
        or review_row.get("accepted_rescue_count", ""),
    )
    duplicate_count = _int_value(review_row.get("duplicate_assigned_count", ""))
    ambiguous_count = _int_value(review_row.get("ambiguous_ms1_owner_count", ""))
    cell_count = sample_count or len(cell_rows)
    backfill_dependency = classify_single_dr_backfill_dependency(
        neutral_loss_tag=review_row.get("neutral_loss_tag", ""),
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=cell_count,
        seed_quality=seed_quality,
    )
    return BackfillPromotionEvidence(
        neutral_loss_tag=review_row.get("neutral_loss_tag", ""),
        primary_evidence=review_row.get("primary_evidence", ""),
        q_detected=q_detected,
        q_rescue=q_rescue,
        cell_count=cell_count,
        duplicate_count=duplicate_count,
        ambiguous_count=ambiguous_count,
        backfill_dependency=backfill_dependency,
        seed_quality=seed_quality,
        cells=tuple(_cell_from_tsv(row) for row in cell_rows),
    )


def classify_backfill_promotion(
    evidence: BackfillPromotionEvidence,
) -> BackfillPromotionDecision:
    if not _in_policy_scope(evidence):
        return BackfillPromotionDecision(state="not_applicable")
    if evidence.q_detected <= 0 and evidence.q_rescue > 0:
        return BackfillPromotionDecision(
            state="blocked",
            reason=RESCUE_ONLY_BLOCKED_REASON,
            confidence="review",
            flags=("rescue_only",),
        )
    if evidence.q_detected < 2:
        return BackfillPromotionDecision(state="not_applicable")
    if evidence.duplicate_count > evidence.q_detected:
        return BackfillPromotionDecision(
            state="blocked",
            reason="duplicate_claim_pressure",
            confidence="review",
            flags=("duplicate_claim_pressure",),
        )

    rescued = tuple(cell for cell in evidence.cells if cell.is_rescued_quantifiable)
    if evidence.q_rescue > 0 and len(rescued) < evidence.q_rescue:
        return BackfillPromotionDecision(
            state="blocked",
            reason=LOW_MS1_COVERAGE_BLOCKED_REASON,
            confidence="review",
            flags=("low_ms1_assessable_coverage",),
            assessed_rescue_count=len(rescued),
        )

    if evidence.q_rescue > 0 and not rescued:
        return BackfillPromotionDecision(
            state="blocked",
            reason=LOW_MS1_COVERAGE_BLOCKED_REASON,
            confidence="review",
            flags=("low_ms1_assessable_coverage",),
        )

    if any(cell.high_neighbor_interference for cell in rescued):
        return BackfillPromotionDecision(
            state="blocked",
            reason=NEIGHBOR_INTERFERENCE_BLOCKED_REASON,
            confidence="review",
            flags=("neighboring_ms1_interference",),
            assessed_rescue_count=len(rescued),
        )

    if any(cell.low_assessable_coverage or not cell.local_apex_supported for cell in rescued):
        return BackfillPromotionDecision(
            state="blocked",
            reason=LOW_MS1_COVERAGE_BLOCKED_REASON,
            confidence="review",
            flags=("low_ms1_assessable_coverage",),
            assessed_rescue_count=len(rescued),
        )

    supported = tuple(cell for cell in rescued if cell.supported_for_backfill)
    if len(supported) < evidence.q_rescue:
        return BackfillPromotionDecision(
            state="blocked",
            reason=LOW_MS1_COVERAGE_BLOCKED_REASON,
            confidence="review",
            flags=("low_ms1_assessable_coverage",),
            supported_rescue_count=len(supported),
            assessed_rescue_count=len(rescued),
        )

    flags = (HIGH_BACKFILL_CAPPED_FLAG,)
    reason = (
        DDA_LIMITED_MS2_SHAPE_REASON
        if _dda_limited_support(evidence)
        else CELL_EVIDENCE_SUPPORTED_REASON
    )
    return BackfillPromotionDecision(
        state="supported",
        reason=reason,
        confidence="medium",
        flags=flags,
        supported_rescue_count=len(supported),
        assessed_rescue_count=len(rescued),
    )


def _in_policy_scope(evidence: BackfillPromotionEvidence) -> bool:
    if not is_dr_neutral_loss_tag(evidence.neutral_loss_tag):
        return False
    if evidence.primary_evidence not in _SUPPORTED_PRIMARY_EVIDENCE:
        return False
    if evidence.q_rescue <= 0:
        return False
    return evidence.backfill_dependency in _POLICY_BACKFILL_REASONS


def _dda_limited_support(evidence: BackfillPromotionEvidence) -> bool:
    if evidence.backfill_dependency == WEAK_SEED_BACKFILL_REASON:
        return True
    seed_quality = evidence.seed_quality
    return bool(seed_quality is not None and seed_quality.weak_seed_signal)


def _cell_from_aligned(
    cell: AlignedCell,
    quality: CellQualityDecision | None,
) -> BackfillCellEvidence:
    return BackfillCellEvidence(
        sample_stem=cell.sample_stem,
        status=cell.status,
        quality_status="" if quality is None else quality.quality_status,
        area=cell.matrix_area,
        apex_rt=cell.apex_rt,
        height=cell.height,
        peak_start_rt=cell.peak_start_rt,
        peak_end_rt=cell.peak_end_rt,
        rt_delta_sec=cell.rt_delta_sec,
        trace_quality=cell.trace_quality,
        scan_support_score=cell.scan_support_score,
        source_candidate_id=cell.source_candidate_id or "",
        reason=cell.reason,
        region_local_mixture_diagnostic=cell.region_local_mixture_diagnostic,
        region_local_mixture_reason=cell.region_local_mixture_reason,
        region_review_reason=cell.region_review_reason,
        region_shadow_status=cell.region_shadow_status,
        region_shadow_verdict=cell.region_shadow_verdict,
    )


def _cell_from_tsv(row: Mapping[str, str]) -> BackfillCellEvidence:
    return BackfillCellEvidence(
        sample_stem=row.get("sample_stem", ""),
        status=row.get("status", ""),
        area=_float_value(row.get("area", "")),
        apex_rt=_float_value(row.get("apex_rt", "")),
        height=_float_value(row.get("height", "")),
        peak_start_rt=_float_value(row.get("peak_start_rt", "")),
        peak_end_rt=_float_value(row.get("peak_end_rt", "")),
        rt_delta_sec=_float_value(row.get("rt_delta_sec", "")),
        trace_quality=row.get("trace_quality", ""),
        scan_support_score=_float_value(row.get("scan_support_score", "")),
        source_candidate_id=row.get("source_candidate_id", ""),
        reason=row.get("reason", ""),
        region_local_mixture_diagnostic=row.get("region_local_mixture_diagnostic", ""),
        region_local_mixture_reason=row.get("region_local_mixture_reason", ""),
        region_review_reason=row.get("region_review_reason", ""),
        region_shadow_status=row.get("region_shadow_status", ""),
        region_shadow_verdict=row.get("region_shadow_verdict", ""),
    )


def _contains_marker(value: str, markers: Sequence[str]) -> bool:
    text = value.lower()
    return any(marker in text for marker in markers)


def _normalize(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _positive(value: float | None) -> bool:
    return value is not None and value > 0.0


def _finite(value: float | None) -> bool:
    return (
        value is not None
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _float_value(value: object) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("'"):
            value = value[1:]
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int_value(value: object) -> int:
    number = _float_value(value)
    return 0 if number is None else int(number)
