from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from gui.sections.settings_section import SettingsSection
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


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


def test_advanced_section_collapsed_by_default(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()

    assert section.advanced_section.isVisible()
    assert not section.advanced_section._content.isVisible()


def test_advanced_section_expands_on_click(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()

    qtbot.mouseClick(section.advanced_section._toggle, Qt.MouseButton.LeftButton)

    assert section.advanced_section._content.isVisible()


def test_advanced_section_contains_required_flags(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()

    advanced_keys = set(section.advanced_section_field_keys())

    assert {
        "keep_intermediate_csv",
        "emit_score_breakdown",
        "emit_review_report",
        "dirty_matrix_mode",
        "count_no_ms2_as_detected",
        "rolling_window_size",
        "rt_prior_library_path",
        "injection_order_source",
        "resolver_mode",
        "resolver_chrom_threshold",
        "resolver_min_search_range_min",
        "resolver_min_relative_height",
        "resolver_min_absolute_height",
        "resolver_min_ratio_top_edge",
        "resolver_peak_duration_min",
        "resolver_peak_duration_max",
        "resolver_min_scans",
        "nl_rt_anchor_search_margin_min",
        "nl_rt_anchor_half_window_min",
        "nl_fallback_half_window_min",
        "parallel_mode",
        "parallel_workers",
    } <= advanced_keys


def test_rt_prior_library_gui_label_marks_developer_debug(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.load(_canonical_settings())

    labels = section.findChildren(QLabel)
    text = "\n".join(label.text() for label in labels)

    assert "RT prior library" in text
    assert "developer/debug" in text


def test_advanced_section_uses_compact_rows_for_related_controls(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()

    keep_layout, keep_index = _containing_layout(
        section._keep_intermediate_csv_checkbox
    )
    score_layout, score_index = _containing_layout(
        section._emit_score_breakdown_checkbox
    )
    report_layout, report_index = _containing_layout(
        section._emit_review_report_checkbox
    )
    dirty_layout, dirty_index = _containing_layout(section._dirty_matrix_mode_checkbox)
    no_ms2_layout, no_ms2_index = _containing_layout(section._count_no_ms2_checkbox)
    mode_layout, mode_index = _containing_layout(section._parallel_mode_combo)
    workers_layout, workers_index = _containing_layout(section._parallel_workers_spin)

    assert _direct_grid_position(section._dirty_matrix_mode_checkbox) is None
    assert _direct_grid_position(section._count_no_ms2_checkbox) is None
    assert keep_layout is score_layout is report_layout is dirty_layout is no_ms2_layout
    assert [keep_index, score_index, report_index, dirty_index, no_ms2_index] == [
        0,
        1,
        2,
        3,
        4,
    ]
    assert mode_layout is workers_layout
    assert mode_index < workers_index


def test_resolver_profiles_show_legacy_controls_for_legacy_mode(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load({**_canonical_settings(), "resolver_mode": "legacy_savgol"})

    assert section._legacy_resolver_panel.isVisible()
    assert not section._local_minimum_resolver_panel.isVisible()
    assert section._smooth_window_spin.isVisible()
    assert section._peak_min_prominence_ratio_spin.isVisible()
    assert not section._resolver_chrom_threshold_spin.isVisible()
    assert not section._resolver_min_ratio_top_edge_spin.isVisible()
    assert section._resolver_mode_combo.isVisible()


def test_resolver_profiles_show_local_controls_for_local_minimum_mode(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load({**_canonical_settings(), "resolver_mode": "local_minimum"})

    assert not section._legacy_resolver_panel.isVisible()
    assert section._local_minimum_resolver_panel.isVisible()
    assert not section._smooth_window_spin.isVisible()
    assert not section._peak_min_prominence_ratio_spin.isVisible()
    assert section._resolver_chrom_threshold_spin.isVisible()
    assert section._resolver_min_ratio_top_edge_spin.isVisible()
    assert section._apply_local_minimum_preset_button.isVisible()


def test_switching_to_local_minimum_preserves_inactive_custom_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "resolver_mode": "legacy_savgol",
            "resolver_min_search_range_min": "0.123",
            "resolver_min_ratio_top_edge": "2.5",
            "resolver_peak_duration_max": "3.5",
        }
    )

    section._resolver_mode_combo.setCurrentText("local_minimum")

    values = section.get_values()
    assert values["resolver_mode"] == "local_minimum"
    assert values["resolver_min_search_range_min"] == "0.123"
    assert values["resolver_min_ratio_top_edge"] == "2.5"
    assert values["resolver_peak_duration_max"] == "3.5"


def test_apply_local_minimum_preset_button_applies_validated_preset(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "resolver_mode": "local_minimum",
            "resolver_min_search_range_min": "0.123",
            "resolver_min_ratio_top_edge": "2.5",
            "resolver_peak_duration_max": "3.5",
        }
    )

    section._apply_local_minimum_preset_button.click()

    values = section.get_values()
    assert values["resolver_chrom_threshold"] == "0.05"
    assert values["resolver_min_search_range_min"] == "0.08"
    assert values["resolver_min_relative_height"] == "0.0"
    assert values["resolver_min_ratio_top_edge"] == "1.7"
    assert values["resolver_peak_duration_min"] == "0.0"
    assert values["resolver_peak_duration_max"] == "10.0"


def test_local_minimum_profile_allows_zero_floor_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load({**_canonical_settings(), "resolver_mode": "local_minimum"})

    section._resolver_min_relative_height_spin.setValue(0.0)
    section._resolver_peak_duration_min_spin.setValue(0.0)

    values = section.get_values()
    assert values["resolver_min_relative_height"] == "0"
    assert values["resolver_peak_duration_min"] == "0"


def test_local_minimum_profile_rejects_duration_min_above_max(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load({**_canonical_settings(), "resolver_mode": "local_minimum"})

    section._resolver_peak_duration_min_spin.setValue(20.0)
    section._resolver_peak_duration_max_spin.setValue(10.0)

    assert not section.is_valid()


def test_local_minimum_profile_preserves_cli_valid_large_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "resolver_mode": "local_minimum",
            "resolver_min_search_range_min": "120.0",
            "resolver_min_ratio_top_edge": "120.0",
            "resolver_peak_duration_min": "120.0",
            "resolver_peak_duration_max": "120.0",
        }
    )

    values = section.get_values()

    assert values["resolver_min_search_range_min"] == "120.0"
    assert values["resolver_min_ratio_top_edge"] == "120.0"
    assert values["resolver_peak_duration_min"] == "120.0"
    assert values["resolver_peak_duration_max"] == "120.0"


def test_loading_local_minimum_preserves_existing_local_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "resolver_mode": "local_minimum",
            "resolver_min_search_range_min": "0.123",
            "resolver_min_ratio_top_edge": "2.5",
            "resolver_peak_duration_max": "3.5",
        }
    )

    values = section.get_values()
    assert values["resolver_min_search_range_min"] == "0.123"
    assert values["resolver_min_ratio_top_edge"] == "2.5"
    assert values["resolver_peak_duration_max"] == "3.5"


def test_advanced_section_edits_round_trip_through_get_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(_canonical_settings())

    section._keep_intermediate_csv_checkbox.setChecked(True)
    section._emit_score_breakdown_checkbox.setChecked(True)
    section._emit_review_report_checkbox.setChecked(True)
    section._dirty_matrix_mode_checkbox.setChecked(True)
    section._count_no_ms2_checkbox.setChecked(False)
    section._rolling_window_size_spin.setValue(9)
    section._rt_prior_library_path_edit.setText("C:\\data\\rt_prior.csv")
    section._injection_order_source_edit.setText("C:\\data\\sample_order.csv")
    section._resolver_mode_combo.setCurrentText("local_minimum")
    section._resolver_min_absolute_height_spin.setValue(80.0)
    section._nl_rt_anchor_half_window_min_spin.setValue(0.75)
    section._parallel_mode_combo.setCurrentText("process")
    section._parallel_workers_spin.setValue(4)

    values = section.get_values()

    assert values["keep_intermediate_csv"] == "true"
    assert values["emit_score_breakdown"] == "true"
    assert values["emit_review_report"] == "true"
    assert values["dirty_matrix_mode"] == "true"
    assert values["count_no_ms2_as_detected"] == "false"
    assert values["rolling_window_size"] == "9"
    assert values["rt_prior_library_path"] == "C:\\data\\rt_prior.csv"
    assert values["injection_order_source"] == "C:\\data\\sample_order.csv"
    assert values["resolver_mode"] == "local_minimum"
    assert values["resolver_min_absolute_height"] == "80"
    assert values["nl_rt_anchor_half_window_min"] == "0.75"
    assert values["parallel_mode"] == "process"
    assert values["parallel_workers"] == "4"


def test_advanced_section_preserves_loaded_strings_without_edits(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(_canonical_settings())

    values = section.get_values()

    assert values["resolver_min_absolute_height"] == "25.0"
    assert values["resolver_peak_duration_max"] == "1.00"
    assert values["nl_rt_anchor_search_margin_min"] == "2.0"
    assert values["parallel_mode"] == "serial"
    assert values["parallel_workers"] == "1"


def test_parallel_defaults_match_canonical_settings_defaults(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            key: value
            for key, value in _canonical_settings().items()
            if key not in {"parallel_mode", "parallel_workers"}
        }
    )

    values = section.get_values()

    assert values["parallel_mode"] == CANONICAL_SETTINGS_DEFAULTS["parallel_mode"]
    assert values["parallel_workers"] == CANONICAL_SETTINGS_DEFAULTS["parallel_workers"]


def test_parallel_loaded_values_round_trip_through_get_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "parallel_mode": "process",
            "parallel_workers": "4",
        }
    )

    values = section.get_values()

    assert values["parallel_mode"] == "process"
    assert values["parallel_workers"] == "4"


def test_advanced_section_records_small_numeric_edits(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(_canonical_settings())

    section._resolver_min_absolute_height_spin.setValue(25.001)

    values = section.get_values()

    assert values["resolver_min_absolute_height"] == "25.001"


def _grid_position(widget) -> tuple[int, int, int, int]:
    layout = widget.parentWidget().layout()
    index = layout.indexOf(widget)
    assert index >= 0
    return layout.getItemPosition(index)


def _direct_grid_position(widget) -> tuple[int, int, int, int] | None:
    layout = widget.parentWidget().layout()
    index = layout.indexOf(widget)
    if index < 0:
        return None
    return layout.getItemPosition(index)


def _containing_layout(widget):
    layout = widget.parentWidget().layout()
    found = _find_layout_item(layout, widget)
    assert found is not None
    return found


def _find_layout_item(layout, widget):
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is widget:
            return layout, index
        nested = item.layout()
        if nested is not None:
            found = _find_layout_item(nested, widget)
            if found is not None:
                return found
    return None
