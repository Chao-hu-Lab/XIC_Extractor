from __future__ import annotations

import pytest

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.discovery.models import DiscoverySettings, NeutralLossProfile
from xic_extractor.presets import PresetError, apply_to_alignment, apply_to_discovery
from xic_extractor.presets.loader import load_preset
from xic_extractor.presets.models import Preset, PresetTag


def test_apply_to_discovery_builds_single_dr_settings() -> None:
    preset = load_preset("dna_dr")
    expected_profile = NeutralLossProfile("DNA_dR", 116.0474)
    expected_defaults = DiscoverySettings(
        neutral_loss_profiles=(expected_profile,),
        selected_tag_names=("DNA_dR",),
        tag_combine_mode="single",
    )

    settings = apply_to_discovery(preset)

    assert settings == expected_defaults


def test_apply_to_discovery_merges_preset_then_explicit_tuning() -> None:
    preset = Preset(
        name="Custom DNA dR",
        description="Custom preset",
        tags=(PresetTag(strategy="neutral_loss", name="DNA_dR", value=116.0474),),
        combine_mode="single",
        discovery_overrides={"rt_max": 30.0, "nl_tolerance_ppm": 15.0},
        alignment_overrides={},
        source="test",
    )

    settings = apply_to_discovery(
        preset,
        explicit_tuning_overrides={"rt_max": 20.0},
    )

    assert settings.rt_max == pytest.approx(20.0)
    assert settings.nl_tolerance_ppm == pytest.approx(15.0)


def test_apply_to_alignment_returns_runtime_standard_peak_options() -> None:
    preset = load_preset("dna_dr")

    alignment_config, run_overrides = apply_to_alignment(preset)

    assert alignment_config == AlignmentConfig()
    assert run_overrides == {
        "standard_peak_backfill": True,
        "standard_peak_backfill_chunk_size": 120,
        "standard_peak_backfill_publication_mode": "matrix-only",
        "standard_peak_backfill_write_gallery": False,
        "standard_peak_backfill_reuse_existing": False,
        "standard_peak_backfill_min_shape_r": pytest.approx(0.95),
    }


def test_apply_to_alignment_maps_legacy_gallery_to_deep_audit() -> None:
    preset = Preset(
        name="Legacy gallery",
        description="Legacy gallery",
        tags=(PresetTag(strategy="neutral_loss", name="DNA_dR", value=116.0474),),
        combine_mode="single",
        discovery_overrides={},
        alignment_overrides={
            "standard_peak_backfill": True,
            "standard_peak_backfill_write_gallery": True,
        },
        source="test",
    )

    _, run_overrides = apply_to_alignment(preset)

    assert run_overrides["standard_peak_backfill_publication_mode"] == "deep-audit"
    assert run_overrides["standard_peak_backfill_write_gallery"] is True


def test_apply_to_alignment_publication_mode_overrides_legacy_gallery() -> None:
    preset = Preset(
        name="Explicit mode",
        description="Explicit mode",
        tags=(PresetTag(strategy="neutral_loss", name="DNA_dR", value=116.0474),),
        combine_mode="single",
        discovery_overrides={},
        alignment_overrides={
            "standard_peak_backfill": True,
            "standard_peak_backfill_publication_mode": "matrix-only",
            "standard_peak_backfill_write_gallery": True,
        },
        source="test",
    )

    _, run_overrides = apply_to_alignment(preset)

    assert run_overrides["standard_peak_backfill_publication_mode"] == "matrix-only"
    assert run_overrides["standard_peak_backfill_write_gallery"] is False


def test_apply_to_alignment_review_gallery_keeps_gallery_surface_enabled() -> None:
    preset = Preset(
        name="Review gallery",
        description="Review gallery",
        tags=(PresetTag(strategy="neutral_loss", name="DNA_dR", value=116.0474),),
        combine_mode="single",
        discovery_overrides={},
        alignment_overrides={
            "standard_peak_backfill": True,
            "standard_peak_backfill_publication_mode": "review-gallery",
        },
        source="test",
    )

    _, run_overrides = apply_to_alignment(preset)

    assert run_overrides["standard_peak_backfill_publication_mode"] == "review-gallery"
    assert run_overrides["standard_peak_backfill_write_gallery"] is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("standard_peak_backfill", "yes", "standard_peak_backfill"),
        ("standard_peak_backfill_chunk_size", 0, "standard_peak_backfill_chunk_size"),
        (
            "standard_peak_backfill_write_gallery",
            "no",
            "standard_peak_backfill_write_gallery",
        ),
        (
            "standard_peak_backfill_min_shape_r",
            1.5,
            "standard_peak_backfill_min_shape_r",
        ),
        (
            "standard_peak_backfill_publication_mode",
            "gallery",
            "standard_peak_backfill_publication_mode",
        ),
    ],
)
def test_apply_to_alignment_rejects_invalid_runtime_options(
    field: str,
    value: object,
    message: str,
) -> None:
    preset = Preset(
        name="Invalid alignment",
        description="Invalid alignment",
        tags=(PresetTag(strategy="neutral_loss", name="DNA_dR", value=116.0474),),
        combine_mode="single",
        discovery_overrides={},
        alignment_overrides={field: value},
        source="test",
    )

    with pytest.raises(PresetError, match=message):
        apply_to_alignment(preset)
