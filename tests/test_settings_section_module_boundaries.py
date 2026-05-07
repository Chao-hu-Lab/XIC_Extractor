from pathlib import Path


def test_settings_section_remains_orchestration_module() -> None:
    source = Path("gui/sections/settings_section.py").read_text(encoding="utf-8")

    assert source.count("\n") < 650
    assert "class _LabeledSpin" not in source
    assert "class CollapsibleSection" not in source
    assert "def _build_advanced_section" not in source
    assert "def _build_peak_resolver_panel" not in source
    assert "def _float_setting_text" not in source
