from __future__ import annotations

from pathlib import Path

import pytest

from xic_extractor.presets import PresetError, list_presets, load_preset


def test_load_builtin_dna_dr_preset_enables_standard_peak_backfill() -> None:
    preset = load_preset("dna_dr")

    assert preset.name == "DNA dR"
    assert preset.description.startswith("CID neutral-loss discovery")
    assert preset.combine_mode == "single"
    assert len(preset.tags) == 1
    tag = preset.tags[0]
    assert tag.strategy == "neutral_loss"
    assert tag.name == "DNA_dR"
    assert tag.value == pytest.approx(116.0474)
    assert preset.discovery_overrides == {}
    assert preset.alignment_overrides == {
        "standard_peak_backfill": True,
        "standard_peak_backfill_chunk_size": 120,
        "standard_peak_backfill_publication_mode": "matrix-only",
    }
    assert preset.source == "builtin:dna_dr"


def test_list_presets_works_outside_repo_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert "dna_dr" in list_presets()
    assert "dna_dr_product_ready" in list_presets()


def test_load_builtin_dna_dr_product_ready_preset_stays_sample_universe_safe() -> None:
    preset = load_preset("dna_dr_product_ready")

    assert preset.name == "DNA dR Product Ready"
    assert preset.combine_mode == "single"
    assert preset.tags[0].name == "DNA_dR"
    assert preset.alignment_overrides == {
        "standard_peak_backfill": True,
        "standard_peak_backfill_chunk_size": 240,
        "standard_peak_backfill_publication_mode": "matrix-only",
        "owner_build_xic_backend": "raw-super-window",
    }


def test_existing_path_toml_loads_supported_alignment_options(tmp_path: Path) -> None:
    preset_path = tmp_path / "custom.toml"
    preset_path.write_text(
        """
name = "Custom"
description = "Custom neutral loss"
combine_mode = "single"

[[tag]]
strategy = "neutral_loss"
name = "NL116"
value = 116.0474

[discovery]
rt_max = 20.0

[alignment]
standard_peak_backfill = true
standard_peak_backfill_chunk_size = 24
standard_peak_backfill_publication_mode = "review-gallery"
standard_peak_backfill_min_shape_r = 0.97
owner_build_xic_backend = "raw-super-window"
backfill_expansion_productization = "clean-target-selective"
""".strip(),
        encoding="utf-8",
    )

    preset = load_preset(preset_path)

    assert preset.source == str(preset_path)
    assert preset.discovery_overrides == {"rt_max": 20.0}
    assert preset.alignment_overrides == {
        "standard_peak_backfill": True,
        "standard_peak_backfill_chunk_size": 24,
        "standard_peak_backfill_publication_mode": "review-gallery",
        "standard_peak_backfill_min_shape_r": 0.97,
        "owner_build_xic_backend": "raw-super-window",
        "backfill_expansion_productization": "clean-target-selective",
    }


def test_unknown_alignment_key_is_rejected(tmp_path: Path) -> None:
    preset_path = tmp_path / "preset.toml"
    preset_path.write_text(
        """
name = "Alignment"
description = "Alignment"
combine_mode = "single"

[[tag]]
strategy = "neutral_loss"
name = "NL116"
value = 116.0474

[alignment]
preferred_ppm = 10.0
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PresetError, match="preferred_ppm"):
        load_preset(preset_path)


def test_missing_builtin_error_lists_available_presets() -> None:
    with pytest.raises(PresetError, match="dna_dr_product_ready"):
        load_preset("missing")
