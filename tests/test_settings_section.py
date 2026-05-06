from gui.sections.settings_section import SettingsSection


def _canonical_settings() -> dict[str, str]:
    return {
        "data_dir": "C:\\data",
        "dll_dir": "C:\\dll",
        "smooth_window": "17",
        "smooth_polyorder": "2",
        "peak_rel_height": "0.90",
        "peak_min_prominence_ratio": "0.15",
        "resolver_mode": "legacy_savgol",
        "resolver_chrom_threshold": "0.05",
        "resolver_min_search_range_min": "0.04",
        "resolver_min_relative_height": "0.05",
        "resolver_min_absolute_height": "25.0",
        "resolver_min_ratio_top_edge": "1.3",
        "resolver_peak_duration_min": "0.03",
        "resolver_peak_duration_max": "1.00",
        "resolver_min_scans": "5",
        "ms2_precursor_tol_da": "0.4",
        "nl_min_intensity_ratio": "0.02",
        "count_no_ms2_as_detected": "true",
        "injection_order_source": "",
        "rolling_window_size": "5",
        "dirty_matrix_mode": "false",
        "rt_prior_library_path": "",
        "emit_score_breakdown": "false",
        "emit_review_report": "false",
        "keep_intermediate_csv": "false",
        "nl_rt_anchor_search_margin_min": "2.0",
        "nl_rt_anchor_half_window_min": "1.0",
        "nl_fallback_half_window_min": "2.0",
        "parallel_mode": "serial",
        "parallel_workers": "1",
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
    assert values["parallel_mode"] == "serial"
    assert values["parallel_workers"] == "1"
    assert values["emit_review_report"] == "false"
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


def test_settings_section_rejects_invalid_loaded_parallel_settings(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)

    section.load(
        {
            **_canonical_settings(),
            "parallel_mode": "proces",
            "parallel_workers": "0",
        }
    )

    assert not section.is_valid()
    values = section.get_values()
    assert values["parallel_mode"] == "proces"
    assert values["parallel_workers"] == "0"
