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
    section.load(_canonical_settings())

    values = section.get_values()

    assert values["smooth_window"] == "17"
    assert values["smooth_polyorder"] == "2"
    assert values["peak_rel_height"] == "0.90"
    assert values["count_no_ms2_as_detected"] == "true"
    assert "smooth_points" not in values
    assert "smooth_sigma" not in values


def test_settings_section_migrates_legacy_smoothing_keys_on_save(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.load(
        {
            "data_dir": "C:\\data",
            "dll_dir": "C:\\dll",
            "smooth_points": "19",
            "smooth_sigma": "3.0",
        }
    )

    values = section.get_values()

    assert values["smooth_window"] == "19"
    assert values["smooth_polyorder"] == "3"
    assert "smooth_points" not in values
    assert "smooth_sigma" not in values
