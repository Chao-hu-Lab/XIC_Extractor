from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.owner_area import median_owner_area, positive_finite
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.alignment.ownership_models import AmbiguousOwnerRecord

_BACKFILL_SUPERSEDES_LOCAL_AREA_RATIO = 3.0
_LOCAL_OWNER_LOW_FAMILY_FRACTION = 0.25
_BACKFILL_FAMILY_SUPPORT_FRACTION = 0.5


def build_owner_alignment_matrix(
    features: tuple[OwnerAlignedFeature, ...],
    *,
    sample_order: tuple[str, ...],
    ambiguous_by_sample: Mapping[str, tuple[AmbiguousOwnerRecord, ...]],
    rescued_cells: tuple[AlignedCell, ...],
) -> AlignmentMatrix:
    cells: list[AlignedCell] = []
    rescued_by_feature_sample = {
        (cell.cluster_id, cell.sample_stem): cell for cell in rescued_cells
    }
    for feature in features:
        owners_by_sample = {owner.sample_stem: owner for owner in feature.owners}
        for sample_stem in sample_order:
            if feature.ambiguous_sample_stem == sample_stem:
                cells.append(_feature_ambiguous_cell(feature, sample_stem))
                continue
            owner = owners_by_sample.get(sample_stem)
            if owner is not None:
                detected = _detected_cell(feature, owner)
                rescued = rescued_by_feature_sample.get(
                    (feature.feature_family_id, sample_stem)
                )
                cells.append(_detected_or_confirmed_cell(feature, detected, rescued))
                continue
            rescued = rescued_by_feature_sample.get(
                (feature.feature_family_id, sample_stem)
            )
            if rescued is not None:
                cells.append(rescued)
                continue
            ambiguous_records = ambiguous_by_sample.get(sample_stem, ())
            if ambiguous_records:
                cells.append(_ambiguous_cell(feature, sample_stem, ambiguous_records))
                continue
            cells.append(_absent_cell(feature, sample_stem))
    return AlignmentMatrix(
        clusters=features,
        cells=tuple(cells),
        sample_order=sample_order,
    )


def ambiguous_records_by_sample(
    records: tuple[AmbiguousOwnerRecord, ...],
) -> dict[str, tuple[AmbiguousOwnerRecord, ...]]:
    grouped: dict[str, list[AmbiguousOwnerRecord]] = {}
    for record in records:
        grouped.setdefault(record.sample_stem, []).append(record)
    return {sample: tuple(items) for sample, items in grouped.items()}


def _detected_cell(feature: OwnerAlignedFeature, owner) -> AlignedCell:
    event = owner.primary_identity_event
    return AlignedCell(
        sample_stem=owner.sample_stem,
        cluster_id=feature.feature_family_id,
        status="detected",
        area=owner.owner_area,
        apex_rt=owner.owner_apex_rt,
        height=owner.owner_height,
        peak_start_rt=owner.owner_peak_start_rt,
        peak_end_rt=owner.owner_peak_end_rt,
        rt_delta_sec=(owner.owner_apex_rt - feature.family_center_rt) * 60.0,
        trace_quality=owner.assignment_reason,
        scan_support_score=None,
        source_candidate_id=event.candidate_id,
        source_raw_file=None,
        reason="sample-local MS1 owner with original MS2 evidence",
    )


def _detected_or_confirmed_cell(
    feature: OwnerAlignedFeature,
    detected: AlignedCell,
    rescued: AlignedCell | None,
) -> AlignedCell:
    if (
        rescued is not None
        and feature.confirm_local_owners_with_backfill
        and _rescued_supersedes_detected(feature, detected, rescued)
    ):
        return replace(
            rescued,
            reason=(
                "owner-centered MS1 backfill superseded low local owner; "
                f"local_owner_area={detected.area}; "
                f"local_owner_rt={detected.apex_rt}; "
                f"source_reason={detected.reason}"
            ),
        )
    return detected


def _rescued_supersedes_detected(
    feature: OwnerAlignedFeature,
    detected: AlignedCell,
    rescued: AlignedCell,
) -> bool:
    detected_area = positive_finite(detected.area)
    rescued_area = positive_finite(rescued.area)
    if detected_area is None or rescued_area is None:
        return False
    if rescued_area < detected_area * _BACKFILL_SUPERSEDES_LOCAL_AREA_RATIO:
        return False

    family_area = median_owner_area(feature)
    if family_area is None:
        return True
    return (
        detected_area <= family_area * _LOCAL_OWNER_LOW_FAMILY_FRACTION
        and rescued_area >= family_area * _BACKFILL_FAMILY_SUPPORT_FRACTION
    )


def _ambiguous_cell(
    feature: OwnerAlignedFeature,
    sample_stem: str,
    records: tuple[AmbiguousOwnerRecord, ...],
) -> AlignedCell:
    candidate_ids = sorted(
        candidate_id for record in records for candidate_id in record.candidate_ids
    )
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status="ambiguous_ms1_owner",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="ambiguous_ms1_owner",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason=(
            "checked local MS1 region is ambiguous"
            if not candidate_ids
            else f"checked local MS1 region is ambiguous: {';'.join(candidate_ids)}"
        ),
    )


def _feature_ambiguous_cell(
    feature: OwnerAlignedFeature,
    sample_stem: str,
) -> AlignedCell:
    candidate_ids = ";".join(feature.ambiguous_candidate_ids)
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status="ambiguous_ms1_owner",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="ambiguous_ms1_owner",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason=(
            "checked local MS1 region is ambiguous"
            if not candidate_ids
            else f"checked local MS1 region is ambiguous: {candidate_ids}"
        ),
    )


def _absent_cell(feature: OwnerAlignedFeature, sample_stem: str) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status="absent",
        area=None,
        apex_rt=None,
        height=None,
        peak_start_rt=None,
        peak_end_rt=None,
        rt_delta_sec=None,
        trace_quality="absent",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="no local MS1 owner",
    )
