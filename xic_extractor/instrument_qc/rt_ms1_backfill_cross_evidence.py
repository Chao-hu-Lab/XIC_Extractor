from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

RT_SUPPORTED = "rt_supported_shadow_candidate"
RT_UNCERTAIN = "rt_model_uncertain"
RT_CONFLICT = "biological_transfer_conflict"
RT_CLEAN_ONLY = "clean_standard_only_review"

MS1_SUPPORTED = "seed_shape_supported_review_candidate"
MS1_NEIGHBOR = "neighbor_interference_review"
MS1_SHAPE_INSUFFICIENT = "shape_insufficient_review"
MS1_NOT_ASSESSABLE = "not_assessable"


@dataclass(frozen=True)
class RtShadowCellRow:
    feature_id: str
    source_cell_key: str
    sample_stem: str
    feature_mz: str
    raw_feature_rt_min: str
    row_classification: str
    supporting_biological_istd_label: str
    review_reason: str


@dataclass(frozen=True)
class SeedAwareFamilyRow:
    feature_family_id: str
    family_center_mz: str
    family_center_rt: str
    detected_count: int
    accepted_rescue_count: int
    accepted_cell_count: int
    review_classification: str
    recommended_next_action: str
    review_reason: str
    png_paths: str


@dataclass(frozen=True)
class RtMs1CrossEvidenceRow:
    feature_family_id: str
    family_center_mz: str
    family_center_rt: str
    detected_count: int
    accepted_rescue_count: int
    accepted_cell_count: int
    ms1_review_classification: str
    rt_supported_cell_count: int
    rt_uncertain_cell_count: int
    rt_conflict_cell_count: int
    rt_clean_only_cell_count: int
    rt_total_cell_count: int
    supporting_istd_labels: str
    combined_classification: str
    recommended_next_action: str
    review_reason: str
    overlay_png_paths: str


@dataclass(frozen=True)
class RtMs1CrossEvidenceResult:
    rows: tuple[RtMs1CrossEvidenceRow, ...]
    counts_by_classification: dict[str, int]
    total_families: int
    rt_family_count: int
    matched_family_count: int


def build_rt_ms1_backfill_cross_evidence(
    *,
    rt_rows: Sequence[RtShadowCellRow],
    seed_families: Sequence[SeedAwareFamilyRow],
) -> RtMs1CrossEvidenceResult:
    rt_by_family = _group_rt_rows(rt_rows)
    seed_family_ids = {row.feature_family_id for row in seed_families}
    rows = tuple(
        _build_family_row(
            seed_family,
            rt_rows=rt_by_family.get(seed_family.feature_family_id, ()),
        )
        for seed_family in seed_families
    )
    return RtMs1CrossEvidenceResult(
        rows=tuple(
            sorted(
                rows,
                key=lambda row: (
                    _classification_sort_key(row.combined_classification),
                    row.feature_family_id,
                ),
            )
        ),
        counts_by_classification=_counts(row.combined_classification for row in rows),
        total_families=len(rows),
        rt_family_count=len(rt_by_family),
        matched_family_count=len(seed_family_ids & set(rt_by_family)),
    )


def _group_rt_rows(
    rows: Sequence[RtShadowCellRow],
) -> dict[str, tuple[RtShadowCellRow, ...]]:
    grouped: defaultdict[str, list[RtShadowCellRow]] = defaultdict(list)
    for row in rows:
        if row.feature_id:
            grouped[row.feature_id].append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def _build_family_row(
    seed_family: SeedAwareFamilyRow,
    *,
    rt_rows: Sequence[RtShadowCellRow],
) -> RtMs1CrossEvidenceRow:
    rt_counts = Counter(row.row_classification for row in rt_rows)
    rt_supported = rt_counts.get(RT_SUPPORTED, 0)
    rt_uncertain = rt_counts.get(RT_UNCERTAIN, 0)
    rt_conflict = rt_counts.get(RT_CONFLICT, 0)
    rt_clean_only = rt_counts.get(RT_CLEAN_ONLY, 0)
    classification = _classify_cross_evidence(
        ms1_classification=seed_family.review_classification,
        rt_supported_cell_count=rt_supported,
        rt_uncertain_cell_count=rt_uncertain,
        rt_conflict_cell_count=rt_conflict,
        rt_total_cell_count=len(rt_rows),
    )
    return RtMs1CrossEvidenceRow(
        feature_family_id=seed_family.feature_family_id,
        family_center_mz=seed_family.family_center_mz,
        family_center_rt=seed_family.family_center_rt,
        detected_count=seed_family.detected_count,
        accepted_rescue_count=seed_family.accepted_rescue_count,
        accepted_cell_count=seed_family.accepted_cell_count,
        ms1_review_classification=seed_family.review_classification,
        rt_supported_cell_count=rt_supported,
        rt_uncertain_cell_count=rt_uncertain,
        rt_conflict_cell_count=rt_conflict,
        rt_clean_only_cell_count=rt_clean_only,
        rt_total_cell_count=len(rt_rows),
        supporting_istd_labels=_supporting_labels(rt_rows),
        combined_classification=classification,
        recommended_next_action=_recommended_action(classification),
        review_reason=_review_reason(
            classification,
            ms1_classification=seed_family.review_classification,
            rt_supported_cell_count=rt_supported,
            rt_uncertain_cell_count=rt_uncertain,
            rt_conflict_cell_count=rt_conflict,
            rt_total_cell_count=len(rt_rows),
        ),
        overlay_png_paths=seed_family.png_paths,
    )


def _classify_cross_evidence(
    *,
    ms1_classification: str,
    rt_supported_cell_count: int,
    rt_uncertain_cell_count: int,
    rt_conflict_cell_count: int,
    rt_total_cell_count: int,
) -> str:
    has_rt_support = rt_supported_cell_count > 0
    has_rt_conflict = rt_conflict_cell_count > 0
    has_rt_uncertainty = rt_uncertain_cell_count > 0
    if ms1_classification == MS1_SUPPORTED and has_rt_support:
        return "rt_ms1_supported_review_candidate"
    if ms1_classification == MS1_NEIGHBOR and has_rt_support:
        return "rt_supported_ms1_interference_review"
    if ms1_classification == MS1_SUPPORTED and has_rt_conflict:
        return "ms1_supported_rt_conflict_review"
    if ms1_classification == MS1_SUPPORTED and has_rt_uncertainty:
        return "ms1_supported_rt_uncertain_review"
    if ms1_classification == MS1_SUPPORTED and rt_total_cell_count == 0:
        return "ms1_supported_rt_context_missing"
    if ms1_classification == MS1_SUPPORTED:
        return "ms1_only_review"
    if has_rt_support:
        return "rt_only_review"
    if has_rt_conflict:
        return "rt_conflict_review"
    if has_rt_uncertainty:
        return "rt_uncertain_review"
    if ms1_classification in {MS1_SHAPE_INSUFFICIENT, MS1_NOT_ASSESSABLE}:
        return "ms1_not_ready_review"
    return "not_supported"


def _recommended_action(classification: str) -> str:
    if classification == "rt_ms1_supported_review_candidate":
        return "candidate_for_future_opt_in_gate"
    if classification in {
        "rt_supported_ms1_interference_review",
        "ms1_supported_rt_conflict_review",
        "ms1_supported_rt_uncertain_review",
    }:
        return "manual_review_required"
    if classification == "ms1_supported_rt_context_missing":
        return "generate_rt_shadow_context"
    if classification == "rt_only_review":
        return "generate_or_review_seed_specific_overlay"
    return "keep_review_only"


def _review_reason(
    classification: str,
    *,
    ms1_classification: str,
    rt_supported_cell_count: int,
    rt_uncertain_cell_count: int,
    rt_conflict_cell_count: int,
    rt_total_cell_count: int,
) -> str:
    if classification == "rt_ms1_supported_review_candidate":
        return "Seed-aware MS1 shape and local biological-ISTD RT support agree."
    if classification == "rt_supported_ms1_interference_review":
        return (
            "RT support exists, but neighboring MS1 interference blocks automatic "
            "use as a production gate candidate."
        )
    if classification == "ms1_supported_rt_conflict_review":
        return (
            "MS1 shape is supported, but local biological ISTD RT evidence "
            "conflicts."
        )
    if classification == "ms1_supported_rt_uncertain_review":
        return "MS1 shape is supported, but RT model uncertainty remains high."
    if classification == "ms1_supported_rt_context_missing":
        return "MS1 shape is supported, but no matching Level 2.5 RT rows were found."
    if classification == "rt_only_review":
        return "RT support exists, but MS1 seed-aware support is not established."
    if classification == "rt_conflict_review":
        return "RT transfer conflict exists and MS1 support is not sufficient."
    if classification == "rt_uncertain_review":
        return "RT rows are present but uncertain and MS1 support is not sufficient."
    if classification == "ms1_not_ready_review":
        return f"MS1 state is {ms1_classification}; keep as review-only."
    return (
        "No combined support; "
        f"rt_supported={rt_supported_cell_count}, "
        f"rt_uncertain={rt_uncertain_cell_count}, "
        f"rt_conflict={rt_conflict_cell_count}, rt_total={rt_total_cell_count}."
    )


def _supporting_labels(rows: Sequence[RtShadowCellRow]) -> str:
    labels = sorted(
        {
            row.supporting_biological_istd_label
            for row in rows
            if row.row_classification == RT_SUPPORTED
            and row.supporting_biological_istd_label
        }
    )
    return ";".join(labels)


def _classification_sort_key(classification: str) -> int:
    priority = {
        "rt_ms1_supported_review_candidate": 0,
        "rt_supported_ms1_interference_review": 1,
        "ms1_supported_rt_conflict_review": 2,
        "ms1_supported_rt_uncertain_review": 3,
        "ms1_supported_rt_context_missing": 4,
        "ms1_only_review": 5,
        "rt_only_review": 6,
        "rt_conflict_review": 7,
        "rt_uncertain_review": 8,
        "ms1_not_ready_review": 9,
        "not_supported": 10,
    }
    return priority.get(classification, 99)


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))
