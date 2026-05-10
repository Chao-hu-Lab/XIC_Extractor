from dataclasses import dataclass

import pytest

from xic_extractor.alignment.models import (
    AlignmentCluster,
    build_alignment_cluster,
    calculate_alignment_cluster_center,
)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    precursor_mz: float
    product_mz: float
    observed_neutral_loss_da: float
    best_seed_rt: float = 1.0
    ms1_apex_rt: float | None = 1.0
    ms1_area: float | None = 1.0


def test_anchor_cluster_center_uses_anchor_members_only():
    low_area_anchor = _candidate(
        candidate_id="anchor-low-area",
        precursor_mz=100.0,
        product_mz=50.0,
        observed_neutral_loss_da=50.0,
        ms1_apex_rt=1.0,
        ms1_area=1.0,
    )
    high_area_anchor = _candidate(
        candidate_id="anchor-high-area",
        precursor_mz=104.0,
        product_mz=54.0,
        observed_neutral_loss_da=50.2,
        ms1_apex_rt=1.4,
        ms1_area=10_000.0,
    )
    non_anchor = _candidate(
        candidate_id="non-anchor",
        precursor_mz=500.0,
        product_mz=450.0,
        observed_neutral_loss_da=60.0,
        ms1_apex_rt=9.0,
        ms1_area=50_000.0,
    )

    cluster = build_alignment_cluster(
        cluster_id="cluster-1",
        neutral_loss_tag="NL50",
        members=(low_area_anchor, high_area_anchor, non_anchor),
        anchor_members=(low_area_anchor, high_area_anchor),
    )

    assert cluster == AlignmentCluster(
        cluster_id="cluster-1",
        neutral_loss_tag="NL50",
        cluster_center_mz=102.0,
        cluster_center_rt=1.2,
        cluster_product_mz=52.0,
        cluster_observed_neutral_loss_da=50.1,
        has_anchor=True,
        members=(low_area_anchor, high_area_anchor, non_anchor),
    )


def test_non_anchor_cluster_center_uses_all_members():
    first = _candidate(
        candidate_id="first",
        precursor_mz=100.0,
        product_mz=50.0,
        observed_neutral_loss_da=49.8,
        ms1_apex_rt=1.0,
    )
    second = _candidate(
        candidate_id="second",
        precursor_mz=104.0,
        product_mz=54.0,
        observed_neutral_loss_da=50.2,
        ms1_apex_rt=1.4,
    )
    third = _candidate(
        candidate_id="third",
        precursor_mz=500.0,
        product_mz=450.0,
        observed_neutral_loss_da=60.0,
        ms1_apex_rt=9.0,
    )

    cluster = build_alignment_cluster(
        cluster_id="cluster-2",
        neutral_loss_tag="NL50",
        members=(first, second, third),
    )

    assert cluster.cluster_center_mz == 104.0
    assert cluster.cluster_center_rt == 1.4
    assert cluster.cluster_product_mz == 54.0
    assert cluster.cluster_observed_neutral_loss_da == 50.2
    assert cluster.has_anchor is False


def test_center_uses_best_seed_rt_when_ms1_apex_rt_is_missing():
    fallback_rt = _candidate(
        candidate_id="fallback-rt",
        precursor_mz=100.0,
        product_mz=50.0,
        observed_neutral_loss_da=50.0,
        best_seed_rt=2.5,
        ms1_apex_rt=None,
    )

    center = calculate_alignment_cluster_center((fallback_rt,))

    assert center == (100.0, 2.5, 50.0, 50.0, False)


def test_empty_center_input_raises_clear_value_error():
    with pytest.raises(ValueError, match="requires at least one member"):
        calculate_alignment_cluster_center(())


def _candidate(
    *,
    candidate_id: str,
    precursor_mz: float,
    product_mz: float,
    observed_neutral_loss_da: float,
    best_seed_rt: float = 1.0,
    ms1_apex_rt: float | None = 1.0,
    ms1_area: float | None = 1.0,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_neutral_loss_da,
        best_seed_rt=best_seed_rt,
        ms1_apex_rt=ms1_apex_rt,
        ms1_area=ms1_area,
    )
