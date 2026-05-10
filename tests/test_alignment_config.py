import sys

import pytest


def test_alignment_public_api_exports_only_config_cluster_and_entrypoint():
    import xic_extractor.alignment as alignment

    assert alignment.__all__ == (
        "AlignmentConfig",
        "AlignmentCluster",
        "cluster_candidates",
    )
    assert {
        name for name in dir(alignment) if not name.startswith("_")
    } == set(alignment.__all__)
    assert "xic_extractor.discovery.pipeline" not in sys.modules


def test_default_config_matches_v1_alignment_contract():
    from xic_extractor.alignment import AlignmentConfig

    config = AlignmentConfig()

    assert config.preferred_ppm == 20.0
    assert config.max_ppm == 50.0
    assert config.preferred_rt_sec == 60.0
    assert config.max_rt_sec == 180.0
    assert config.product_mz_tolerance_ppm == 20.0
    assert config.observed_loss_tolerance_ppm == 20.0
    assert config.mz_bucket_neighbor_radius == 2
    assert config.anchor_priorities == ("HIGH",)
    assert config.anchor_min_evidence_score == 60
    assert config.anchor_min_seed_events == 2
    assert config.anchor_min_scan_support_score == 0.5
    assert config.rt_unit == "min"
    assert config.fragmentation_model == "cid_nl"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"preferred_ppm": 0.0},
        {"max_ppm": -1.0},
        {"preferred_ppm": 51.0, "max_ppm": 50.0},
        {"preferred_rt_sec": 0.0},
        {"max_rt_sec": -1.0},
        {"preferred_rt_sec": 181.0, "max_rt_sec": 180.0},
        {"product_mz_tolerance_ppm": 0.0},
        {"observed_loss_tolerance_ppm": -1.0},
    ],
)
def test_invalid_tolerance_windows_are_rejected(kwargs):
    from xic_extractor.alignment import AlignmentConfig

    with pytest.raises(ValueError):
        AlignmentConfig(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"anchor_priorities": ()},
        {"anchor_min_evidence_score": -1},
        {"anchor_min_evidence_score": 101},
        {"anchor_min_seed_events": 0},
        {"anchor_min_scan_support_score": -0.1},
        {"anchor_min_scan_support_score": 1.1},
        {"rt_unit": "sec"},
        {"fragmentation_model": "hcd"},
    ],
)
def test_invalid_anchor_and_v1_fixed_fields_are_rejected(kwargs):
    from xic_extractor.alignment import AlignmentConfig

    with pytest.raises(ValueError):
        AlignmentConfig(**kwargs)
