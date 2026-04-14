from gui.sections.settings_section import SettingsSection


def _canonical_settings() -> dict[str, str]:
    return {
        "data_dir": "C:\\data",
        "dll_dir": "C:\\dll",
        "smooth_window": "17",
        "smooth_polyorder": "2",
        "peak_rel_height": "0.90",
        "peak_min_prominence_ratio": "0.15",
        "ms2_precursor_tol_da": "0.4",
        "nl_min_intensity_ratio": "0.02",
        "count_no_ms2_as_detected": "true",
    }


def test_settings_section_saves_canonical_keys_after_canonical_load(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    migrated = section.load(_canonical_settings())

    values = section.get_values()

    assert migrated is False
    assert values["smooth_window"] == "17"
    assert values["smooth_polyorder"] == "2"
    assert values["peak_rel_height"] == "0.90"
    assert values["peak_min_prominence_ratio"] == "0.15"
    assert values["ms2_precursor_tol_da"] == "0.4"
    assert values["nl_min_intensity_ratio"] == "0.02"
    assert values["count_no_ms2_as_detected"] == "true"
    assert "smooth_points" not in values
    assert "smooth_sigma" not in values


def test_settings_section_migrates_legacy_smoothing_keys_on_save(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    migrated = section.load(
        {
            "data_dir": "C:\\data",
            "dll_dir": "C:\\dll",
            "smooth_points": "19",
            "smooth_sigma": "3.0",
        }
    )

    values = section.get_values()

    assert migrated is True
    assert values["smooth_window"] == "19"
    assert values["smooth_polyorder"] == "3"
    assert values["peak_rel_height"] == "0.95"
    assert "smooth_points" not in values
    assert "smooth_sigma" not in values


def test_settings_section_exposes_new_processing_controls(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.load(_canonical_settings())

    section._peak_rel_height_spin.setValue(0.88)
    section._peak_min_prominence_ratio_spin.setValue(0.25)
    section._ms2_precursor_tol_da_spin.setValue(0.7)
    section._nl_min_intensity_ratio_spin.setValue(0.03)
    section._count_no_ms2_checkbox.setChecked(False)

    values = section.get_values()

    assert values["peak_rel_height"] == "0.88"
    assert values["peak_min_prominence_ratio"] == "0.25"
    assert values["ms2_precursor_tol_da"] == "0.7"
    assert values["nl_min_intensity_ratio"] == "0.03"
    assert values["count_no_ms2_as_detected"] == "false"


def test_settings_section_numeric_rules_do_not_require_existing_paths(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.load(
        {
            **_canonical_settings(),
            "data_dir": "C:\\missing-data",
            "dll_dir": "C:\\missing-dll",
        }
    )

    assert section.is_valid()

    section._smooth_window_spin.setValue(4)
    assert not section.is_valid()

    section._smooth_window_spin.setValue(5)
    section._smooth_polyorder_spin.setValue(5)
    assert not section.is_valid()
