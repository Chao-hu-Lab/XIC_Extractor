from __future__ import annotations

from dataclasses import replace

from xic_extractor.alignment.matrix import AlignedCell
from xic_extractor.peak_detection.region_audit import PeakRegionAuditSummary


def with_region_audit(
    cell: AlignedCell,
    region_audit: PeakRegionAuditSummary | None,
) -> AlignedCell:
    if region_audit is None:
        return cell
    return replace(
        cell,
        region_candidate_count=region_audit.candidate_count,
        region_selected_proposal_sources=region_audit.selected_proposal_sources,
        region_selected_merge_note=region_audit.selected_merge_note,
        region_shadow_status=region_audit.shadow_status,
        region_shadow_verdict=region_audit.shadow_verdict,
        region_merge_suggestion_source=region_audit.merge_suggestion_source,
        region_area_ratio=region_audit.area_ratio,
        region_selected_interval_count=region_audit.selected_interval_count,
        region_selected_interval_gap_max_min=(
            region_audit.selected_interval_gap_max_min
        ),
        region_local_mixture_diagnostic=region_audit.local_mixture_diagnostic,
        region_local_mixture_reason=region_audit.local_mixture_reason,
        region_review_reason=region_audit.review_reason,
    )
