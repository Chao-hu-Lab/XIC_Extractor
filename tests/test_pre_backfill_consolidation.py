from typing import cast

import pytest

import xic_extractor.alignment.pre_backfill_consolidation as pre_mod
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix, CellStatus
from xic_extractor.alignment.owner_clustering import OwnerAlignedFeature
from xic_extractor.alignment.ownership_models import IdentityEvent, SampleLocalMS1Owner
from xic_extractor.alignment.pre_backfill_consolidation import (
    consolidate_pre_backfill_identity_families,
    recenter_pre_backfill_identity_families,
)
from xic_extractor.peak_detection.hypotheses import IntegrationResult


def test_pre_backfill_consolidation_merges_identity_compatible_samples() -> None:
    feature_a = _feature("FAM000001", sample_stem="sample-a", rt=8.00)
    feature_b = _feature("FAM000002", sample_stem="sample-b", rt=8.05)

    features = consolidate_pre_backfill_identity_families(
        (feature_a, feature_b),
        config=AlignmentConfig(),
    )

    primary = [feature for feature in features if not feature.review_only]
    losers = [feature for feature in features if feature.review_only]
    assert len(primary) == 1
    assert {owner.sample_stem for owner in primary[0].owners} == {
        "sample-a",
        "sample-b",
    }
    assert primary[0].confirm_local_owners_with_backfill is True
    assert primary[0].backfill_seed_centers == ((500.0, 8.0), (500.0, 8.05))
    assert primary[0].group_construction_role == "pre_backfill_successor_adapter"
    assert primary[0].group_delivery_role == "pre_backfill_successor_adapter"
    assert (
        primary[0].group_membership_source
        == "pre_backfill_cross_sample_peak_group_projection"
    )
    assert primary[0].consolidation_state == "primary_winner"
    assert primary[0].consolidation_source_group_hypothesis_id == (
        "FAM000001;FAM000002"
    )
    assert "pre_backfill_identity_consolidated" in primary[0].evidence
    assert len(losers) == 1
    assert losers[0].consolidation_state == "primary_loser"
    assert losers[0].consolidation_winner_group_hypothesis_id == "FAM000001"
    assert "winner=" in losers[0].evidence


def test_pre_backfill_consolidation_keeps_same_sample_features_separate() -> None:
    feature_a = _feature("FAM000001", sample_stem="sample-a", rt=8.00)
    feature_b = _feature("FAM000002", sample_stem="sample-a", rt=8.05)

    features = consolidate_pre_backfill_identity_families(
        (feature_a, feature_b),
        config=AlignmentConfig(),
    )

    assert [feature.review_only for feature in features] == [False, False]
    assert [len(feature.owners) for feature in features] == [1, 1]


def test_pre_backfill_consolidation_keeps_incompatible_product_separate() -> None:
    feature_a = _feature("FAM000001", sample_stem="sample-a", product_mz=383.9526)
    feature_b = _feature("FAM000002", sample_stem="sample-b", product_mz=400.0)

    features = consolidate_pre_backfill_identity_families(
        (feature_a, feature_b),
        config=AlignmentConfig(),
    )

    assert [feature.review_only for feature in features] == [False, False]


def test_pre_backfill_consolidation_caps_backfill_seed_centers() -> None:
    features = consolidate_pre_backfill_identity_families(
        (
            _feature("FAM000001", sample_stem="sample-a", rt=8.0),
            _feature("FAM000002", sample_stem="sample-b", rt=8.1),
            _feature("FAM000003", sample_stem="sample-c", rt=8.2),
            _feature("FAM000004", sample_stem="sample-d", rt=8.3),
            _feature("FAM000005", sample_stem="sample-e", rt=8.4),
        ),
        config=AlignmentConfig(),
    )

    primary = next(feature for feature in features if not feature.review_only)

    assert primary.backfill_seed_centers == (
        (500.0, 8.0),
        (500.0, 8.4),
    )


def test_pre_backfill_consolidation_reuses_sample_stem_sets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = (
        _feature("FAM000001", sample_stem="sample-a", rt=8.0),
        _feature("FAM000002", sample_stem="sample-b", rt=8.1),
        _feature("FAM000003", sample_stem="sample-c", rt=8.2),
    )
    calls: list[str] = []
    original = pre_mod._sample_stems

    def tracking_sample_stems(feature: OwnerAlignedFeature) -> set[str]:
        calls.append(feature.feature_family_id)
        return original(feature)

    monkeypatch.setattr(pre_mod, "_sample_stems", tracking_sample_stems)

    consolidated = consolidate_pre_backfill_identity_families(
        features,
        config=AlignmentConfig(),
    )

    assert calls == ["FAM000001", "FAM000002", "FAM000003"]
    assert [feature.consolidation_state for feature in consolidated] == [
        "primary_loser",
        "primary_winner",
        "primary_loser",
    ]


def test_recenter_pre_backfill_identity_family_uses_present_cell_rts() -> None:
    feature = _feature("FAM000001", sample_stem="sample-a", rt=9.5)
    feature = OwnerAlignedFeature(
        **{
            **feature.__dict__,
            "evidence": (
                "owner_complete_link;owner_count=2;"
                "pre_backfill_identity_consolidated;family_count=2"
            ),
        }
    )
    matrix = AlignmentMatrix(
        clusters=(feature,),
        cells=(
            _cell("sample-a", "FAM000001", apex_rt=8.0),
            _cell("sample-b", "FAM000001", apex_rt=10.0),
            _cell("sample-c", "FAM000001", apex_rt=None, status="absent"),
        ),
        sample_order=("sample-a", "sample-b", "sample-c"),
    )

    recentered = recenter_pre_backfill_identity_families(matrix)

    recentered_feature = cast(OwnerAlignedFeature, recentered.clusters[0])
    assert recentered_feature.family_center_rt == 9.0
    assert [cell.rt_delta_sec for cell in recentered.cells] == [-60.0, 60.0, None]


def _feature(
    feature_family_id: str,
    *,
    sample_stem: str,
    rt: float = 8.0,
    product_mz: float = 383.9526,
) -> OwnerAlignedFeature:
    owner = _owner(sample_stem, feature_family_id, apex_rt=rt)
    return OwnerAlignedFeature(
        feature_family_id=feature_family_id,
        neutral_loss_tag="NL116",
        family_center_mz=500.0,
        family_center_rt=rt,
        family_product_mz=product_mz,
        family_observed_neutral_loss_da=116.0474,
        has_anchor=True,
        owners=(owner,),
        evidence="single_sample_local_owner",
    )


def _owner(
    sample_stem: str,
    suffix: str,
    *,
    apex_rt: float = 8.5,
) -> SampleLocalMS1Owner:
    event = IdentityEvent(
        candidate_id=f"{sample_stem}#{suffix}",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        neutral_loss_tag="NL116",
        precursor_mz=500.0,
        product_mz=383.9526,
        observed_neutral_loss_da=116.0474,
        seed_rt=apex_rt,
        evidence_score=80,
        seed_event_count=2,
    )
    return SampleLocalMS1Owner(
        owner_id=f"OWN-{sample_stem}-{suffix}",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        precursor_mz=500.0,
        owner_apex_rt=apex_rt,
        owner_peak_start_rt=apex_rt - 0.05,
        owner_peak_end_rt=apex_rt + 0.05,
        owner_area=1000.0,
        owner_height=100.0,
        primary_identity_event=event,
        supporting_events=(),
        identity_conflict=False,
        assignment_reason="owner_exact_apex_match",
        selected_integration=_integration(),
    )


def _integration() -> IntegrationResult:
    return IntegrationResult(
        rt_left_min=8.45,
        rt_apex_min=8.5,
        rt_right_min=8.55,
        raw_apex_rt_min=8.5,
        rt_width_min=0.1,
        height_raw=100.0,
        height_smoothed=100.0,
        area_raw_counts_seconds=1000.0,
        area_baseline_corrected=900.0,
        baseline_type="asls",
        boundary_sources=("test_owner",),
        area_ms1_morphology=900.0,
        ms1_morphology_area_source="gaussian15_positive_asls_residual",
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    *,
    apex_rt: float | None,
    status: CellStatus = "detected",
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,
        area=100.0 if status != "absent" else None,
        apex_rt=apex_rt,
        height=10.0 if status != "absent" else None,
        peak_start_rt=(apex_rt - 0.05) if apex_rt is not None else None,
        peak_end_rt=(apex_rt + 0.05) if apex_rt is not None else None,
        rt_delta_sec=None,
        trace_quality=status,
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason=status,
    )
