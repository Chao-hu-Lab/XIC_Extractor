from xic_extractor.discovery.evidence_config import (
    DEFAULT_EVIDENCE_PROFILE,
    DiscoveryEvidenceThresholds,
    DiscoveryEvidenceWeights,
)


def test_default_evidence_profile_pins_v1_weights() -> None:
    weights = DEFAULT_EVIDENCE_PROFILE.weights
    assert DEFAULT_EVIDENCE_PROFILE.name == "default"
    assert weights.ms1_peak_present == 25
    assert weights.ms1_peak_absent == 5
    assert weights.seed_event_per == 8
    assert weights.seed_event_max == 25
    assert weights.rt_aligned == 15
    assert weights.rt_near == 10
    assert weights.rt_shifted == 5
    assert weights.product_intensity_high == 10
    assert weights.product_intensity_med == 5
    assert weights.area_high == 10
    assert weights.area_med == 5
    assert weights.scan_support_high == 5
    assert weights.scan_support_low == -10
    assert weights.legacy_trace_quality_high == 5
    assert weights.legacy_trace_quality_low == -10
    assert weights.superfamily_representative == 5
    assert weights.superfamily_member == -5


def test_default_evidence_profile_pins_v1_thresholds() -> None:
    thresholds = DEFAULT_EVIDENCE_PROFILE.thresholds
    assert thresholds.rt_aligned_max_min == 0.05
    assert thresholds.rt_near_max_min == 0.20
    assert thresholds.rt_shifted_max_min == 0.40
    assert thresholds.product_intensity_high_min == 100_000.0
    assert thresholds.product_intensity_med_min == 10_000.0
    assert thresholds.area_high_min == 1_000_000.0
    assert thresholds.area_med_min == 100_000.0
    assert thresholds.ms1_support_strong_area_min == 10_000_000.0
    assert thresholds.ms1_support_moderate_area_min == 1_000_000.0
    assert thresholds.scan_support_target == 10
    assert thresholds.scan_support_high_score_min == 0.8
    assert thresholds.scan_support_low_score_max == 0.2


def test_evidence_weights_are_frozen_and_hashable() -> None:
    first = DiscoveryEvidenceWeights()
    second = DiscoveryEvidenceWeights()
    assert hash(first) == hash(second)


def test_evidence_thresholds_are_frozen_and_hashable() -> None:
    first = DiscoveryEvidenceThresholds()
    second = DiscoveryEvidenceThresholds()
    assert hash(first) == hash(second)
