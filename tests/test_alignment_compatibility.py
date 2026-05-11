from pathlib import Path
from types import SimpleNamespace

import pytest

from xic_extractor.alignment.compatibility import (
    are_candidates_compatible,
    can_attach_to_cluster,
    observed_loss_is_compatible,
    ppm_distance,
    product_mz_is_compatible,
    rt_seconds_difference,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.models import AlignmentCluster, build_alignment_cluster


def test_different_neutral_loss_tag_is_incompatible():
    existing = _candidate("existing", neutral_loss_tag="NL141")
    candidate = _candidate("candidate", neutral_loss_tag="NL120")

    assert are_candidates_compatible(existing, candidate, AlignmentConfig()) is False


def test_same_mz_rt_with_product_mz_conflict_is_incompatible():
    existing = _candidate("existing", product_mz=300.0000)
    candidate = _candidate("candidate", product_mz=300.0100)

    assert are_candidates_compatible(existing, candidate, AlignmentConfig()) is False


def test_same_mz_rt_with_observed_neutral_loss_conflict_is_incompatible():
    existing = _candidate("existing", observed_neutral_loss_da=141.0000)
    candidate = _candidate("candidate", observed_neutral_loss_da=141.0100)

    assert are_candidates_compatible(existing, candidate, AlignmentConfig()) is False


def test_pairwise_compatibility_requires_all_hard_guards_to_pass():
    existing = _candidate(
        "existing",
        precursor_mz=500.0000,
        product_mz=359.0000,
        observed_neutral_loss_da=141.0000,
        ms1_apex_rt=5.0,
    )
    candidate = _candidate(
        "candidate",
        precursor_mz=500.0100,
        product_mz=359.0050,
        observed_neutral_loss_da=141.0010,
        ms1_apex_rt=5.5,
    )

    assert are_candidates_compatible(existing, candidate, AlignmentConfig()) is True


def test_precursor_mz_guard_uses_max_ppm():
    existing = _candidate("existing", precursor_mz=500.0000)
    candidate = _candidate("candidate", precursor_mz=500.0300)

    assert are_candidates_compatible(existing, candidate, AlignmentConfig()) is False


def test_rt_guard_uses_seconds_difference():
    existing = _candidate("existing", ms1_apex_rt=5.0)
    candidate = _candidate("candidate", ms1_apex_rt=8.1)

    assert are_candidates_compatible(existing, candidate, AlignmentConfig()) is False


def test_anchored_cluster_requires_compatibility_with_every_anchor_member():
    anchor_a = _candidate("anchor-a", product_mz=359.0000)
    anchor_b = _candidate("anchor-b", product_mz=359.0300)
    candidate = _candidate("candidate", product_mz=359.0010)
    cluster = build_alignment_cluster(
        cluster_id="cluster-anchored",
        neutral_loss_tag="NL141",
        members=(anchor_a, anchor_b),
        anchor_members=(anchor_a, anchor_b),
    )

    assert (
        can_attach_to_cluster(
            cluster,
            candidate,
            AlignmentConfig(),
        )
        is False
    )


def test_unanchored_cluster_requires_compatibility_with_every_primary_member():
    primary_a = _candidate("primary-a", product_mz=359.0000)
    primary_b = _candidate("primary-b", product_mz=359.0300)
    candidate = _candidate("candidate", product_mz=359.0010)
    cluster = build_alignment_cluster(
        cluster_id="cluster-unanchored",
        neutral_loss_tag="NL141",
        members=(primary_a, primary_b),
    )

    assert can_attach_to_cluster(cluster, candidate, AlignmentConfig()) is False


def test_anchored_cluster_non_anchor_members_do_not_expand_compatibility_set():
    anchor = _candidate("anchor", product_mz=359.0000)
    non_anchor = _candidate("non-anchor", product_mz=359.0300)
    candidate = _candidate("candidate", product_mz=359.0310)
    cluster = build_alignment_cluster(
        cluster_id="cluster-no-chain",
        neutral_loss_tag="NL141",
        members=(anchor, non_anchor),
        anchor_members=(anchor,),
    )

    assert (
        can_attach_to_cluster(
            cluster,
            candidate,
            AlignmentConfig(),
        )
        is False
    )


def test_anchored_cluster_uses_stored_anchor_members_without_call_site_repeating_them():
    anchor = _candidate("anchor", product_mz=359.0000)
    non_anchor = _candidate("non-anchor", product_mz=359.0300)
    candidate = _candidate("candidate", product_mz=359.0010)
    cluster = build_alignment_cluster(
        cluster_id="cluster-compatible",
        neutral_loss_tag="NL141",
        members=(anchor, non_anchor),
        anchor_members=(anchor,),
    )

    assert can_attach_to_cluster(cluster, candidate, AlignmentConfig()) is True


def test_malformed_anchored_cluster_without_anchor_members_fails_closed():
    anchor = _candidate("anchor")
    candidate = _candidate("candidate")
    cluster = AlignmentCluster(
        cluster_id="cluster-malformed",
        neutral_loss_tag="NL141",
        cluster_center_mz=500.0,
        cluster_center_rt=5.0,
        cluster_product_mz=359.0,
        cluster_observed_neutral_loss_da=141.0,
        has_anchor=True,
        members=(anchor,),
    )

    with pytest.raises(ValueError, match="compatibility.*anchor_members"):
        can_attach_to_cluster(cluster, candidate, AlignmentConfig())


def test_cid_compatibility_rejects_unsupported_fragmentation_model_values():
    existing = _candidate("existing")
    candidate = _candidate("candidate")
    unsupported_config = SimpleNamespace(
        max_ppm=50.0,
        max_rt_sec=180.0,
        product_mz_tolerance_ppm=20.0,
        observed_loss_tolerance_ppm=20.0,
        fragmentation_model="hcd",
    )

    with pytest.raises(ValueError, match='fragmentation_model must be "cid_nl" in v1'):
        are_candidates_compatible(existing, candidate, unsupported_config)


def test_small_compatibility_helpers_use_ppm_and_rt_seconds():
    assert ppm_distance(500.0, 500.01) == pytest.approx(20.0)
    assert rt_seconds_difference(
        _candidate("left", ms1_apex_rt=5.0),
        _candidate("right", ms1_apex_rt=5.5),
    ) == pytest.approx(30.0)
    assert product_mz_is_compatible(
        _candidate("left", product_mz=300.0),
        _candidate("right", product_mz=300.005),
        max_ppm=20.0,
    )
    assert observed_loss_is_compatible(
        _candidate("left", observed_neutral_loss_da=141.0),
        _candidate("right", observed_neutral_loss_da=141.002),
        max_ppm=20.0,
    )


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("precursor_mz", True),
        ("product_mz", "300.0"),
        ("observed_neutral_loss_da", 0.0),
        ("observed_neutral_loss_da", float("nan")),
        ("ms1_apex_rt", float("inf")),
    ],
)
def test_numeric_validation_errors_name_field_and_compatibility_context(
    field,
    bad_value,
):
    existing = _candidate("existing")
    candidate = _candidate("candidate")
    candidate = _replace_candidate_field(candidate, field, bad_value)

    with pytest.raises(ValueError, match=rf"compatibility.*{field}"):
        are_candidates_compatible(existing, candidate, AlignmentConfig())


def test_numeric_validation_errors_name_missing_field_and_compatibility_context():
    existing = _candidate("existing")
    candidate = SimpleNamespace(
        neutral_loss_tag="NL141",
        precursor_mz=500.0,
        product_mz=359.0,
        best_seed_rt=5.0,
        ms1_apex_rt=5.0,
    )

    with pytest.raises(ValueError, match="compatibility.*observed_neutral_loss_da"):
        are_candidates_compatible(existing, candidate, AlignmentConfig())


@pytest.mark.parametrize(
    "bad_value",
    [True, "180", 0.0, float("nan"), float("inf")],
)
def test_config_numeric_validation_errors_name_field_and_compatibility_context(
    bad_value,
):
    existing = _candidate("existing")
    candidate = _candidate("candidate")
    config = AlignmentConfig(max_rt_sec=180.0)
    object.__setattr__(config, "max_rt_sec", bad_value)

    with pytest.raises(ValueError, match="compatibility config field 'max_rt_sec'"):
        are_candidates_compatible(existing, candidate, config)


def _candidate(
    candidate_id: str,
    *,
    neutral_loss_tag: str = "NL141",
    precursor_mz: float = 500.0000,
    product_mz: float = 359.0000,
    observed_neutral_loss_da: float = 141.0000,
    best_seed_rt: float = 5.0,
    ms1_apex_rt: float | None = 5.0,
):
    from xic_extractor.discovery.models import DiscoveryCandidate

    return DiscoveryCandidate(
        review_priority="LOW",
        evidence_score=0,
        evidence_tier="E",
        ms2_support="weak",
        ms1_support="found",
        rt_alignment="aligned",
        family_context="singleton",
        candidate_id=candidate_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_neutral_loss_da,
        best_seed_rt=best_seed_rt,
        seed_event_count=1,
        ms1_peak_found=ms1_apex_rt is not None,
        ms1_apex_rt=ms1_apex_rt,
        ms1_area=1.0,
        ms2_product_max_intensity=10.0,
        reason="strict NL compatibility test",
        raw_file=Path(f"{candidate_id}.raw"),
        sample_stem=candidate_id,
        best_ms2_scan_id=1,
        seed_scan_ids=(1,),
        neutral_loss_tag=neutral_loss_tag,
        configured_neutral_loss_da=141.0,
        neutral_loss_mass_error_ppm=0.0,
        rt_seed_min=best_seed_rt,
        rt_seed_max=best_seed_rt,
        ms1_search_rt_min=best_seed_rt - 0.1,
        ms1_search_rt_max=best_seed_rt + 0.1,
        ms1_seed_delta_min=None,
        ms1_peak_rt_start=None,
        ms1_peak_rt_end=None,
        ms1_height=None,
        ms1_trace_quality="good",
    )


def _replace_candidate_field(candidate, field: str, value):
    data = candidate.__dict__.copy()
    data[field] = value
    return SimpleNamespace(**data)
