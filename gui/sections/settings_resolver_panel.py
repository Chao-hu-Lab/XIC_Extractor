from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gui.sections.settings_constants import (
    _GUI_UNBOUNDED_FLOAT_MAX,
    _LOCAL_MINIMUM_GUI_PRESET,
)
from gui.sections.settings_controls import ResolverControls
from gui.sections.settings_widgets import _LabeledSpin, _set_float_range


def configure_resolver_controls(controls: ResolverControls) -> None:
    controls.mode_combo.addItems(["legacy_savgol", "local_minimum"])
    controls.smooth_window_spin.setRange(3, 999)
    controls.smooth_window_spin.setSingleStep(2)
    controls.smooth_polyorder_spin.setRange(1, 10)
    controls.peak_rel_height_spin.setRange(0.50, 0.99)
    controls.peak_rel_height_spin.setSingleStep(0.01)
    controls.peak_rel_height_spin.setDecimals(2)
    controls.peak_min_prominence_ratio_spin.setRange(0.01, 0.50)
    controls.peak_min_prominence_ratio_spin.setSingleStep(0.01)
    controls.peak_min_prominence_ratio_spin.setDecimals(2)

    controls.min_scans_spin.setRange(1, 999)
    _set_float_range(controls.chrom_threshold_spin, 0.0, 1.0, 3)
    _set_float_range(
        controls.min_search_range_min_spin,
        0.001,
        _GUI_UNBOUNDED_FLOAT_MAX,
        3,
    )
    _set_float_range(controls.min_relative_height_spin, 0.0, 1.0, 3)
    _set_float_range(
        controls.min_absolute_height_spin,
        0.0,
        _GUI_UNBOUNDED_FLOAT_MAX,
        3,
    )
    _set_float_range(
        controls.min_ratio_top_edge_spin,
        1.01,
        _GUI_UNBOUNDED_FLOAT_MAX,
        3,
    )
    _set_float_range(
        controls.peak_duration_min_spin,
        0.0,
        _GUI_UNBOUNDED_FLOAT_MAX,
        3,
    )
    _set_float_range(
        controls.peak_duration_max_spin,
        0.001,
        _GUI_UNBOUNDED_FLOAT_MAX,
        3,
    )


def build_peak_resolver_panel(controls: ResolverControls) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    mode_layout = QHBoxLayout()
    mode_layout.setContentsMargins(0, 0, 0, 0)
    mode_layout.setSpacing(8)
    mode_layout.addWidget(QLabel("Mode"))
    mode_layout.addWidget(controls.mode_combo)
    mode_layout.addStretch()
    layout.addLayout(mode_layout)

    legacy_layout = QHBoxLayout(controls.legacy_panel)
    legacy_layout.setContentsMargins(0, 0, 0, 0)
    legacy_layout.setSpacing(16)
    legacy_layout.addWidget(_LabeledSpin("Window", controls.smooth_window_spin))
    legacy_layout.addWidget(_LabeledSpin("Polyorder", controls.smooth_polyorder_spin))
    legacy_layout.addWidget(_LabeledSpin("Peak height", controls.peak_rel_height_spin))
    legacy_layout.addWidget(
        _LabeledSpin("Prominence", controls.peak_min_prominence_ratio_spin)
    )
    legacy_layout.addStretch()
    layout.addWidget(controls.legacy_panel)

    local_layout = QVBoxLayout(controls.local_minimum_panel)
    local_layout.setContentsMargins(0, 0, 0, 0)
    local_layout.setSpacing(8)
    local_row_1 = QHBoxLayout()
    local_row_1.setContentsMargins(0, 0, 0, 0)
    local_row_1.setSpacing(16)
    local_row_1.addWidget(
        _LabeledSpin("Chrom threshold", controls.chrom_threshold_spin)
    )
    local_row_1.addWidget(
        _LabeledSpin("Search range", controls.min_search_range_min_spin)
    )
    local_row_1.addWidget(
        _LabeledSpin("Min rel height", controls.min_relative_height_spin)
    )
    local_row_1.addWidget(
        _LabeledSpin("Min abs height", controls.min_absolute_height_spin)
    )
    local_row_1.addStretch()
    local_layout.addLayout(local_row_1)

    local_row_2 = QHBoxLayout()
    local_row_2.setContentsMargins(0, 0, 0, 0)
    local_row_2.setSpacing(16)
    local_row_2.addWidget(_LabeledSpin("Top/edge", controls.min_ratio_top_edge_spin))
    local_row_2.addWidget(_LabeledSpin("Min duration", controls.peak_duration_min_spin))
    local_row_2.addWidget(_LabeledSpin("Max duration", controls.peak_duration_max_spin))
    local_row_2.addWidget(_LabeledSpin("Min scans", controls.min_scans_spin))
    local_row_2.addWidget(controls.apply_local_minimum_preset_button)
    local_row_2.addStretch()
    local_layout.addLayout(local_row_2)
    layout.addWidget(controls.local_minimum_panel)

    return panel


def update_resolver_profile_visibility(controls: ResolverControls) -> None:
    is_local = controls.mode_combo.currentText() == "local_minimum"
    controls.legacy_panel.setVisible(not is_local)
    controls.local_minimum_panel.setVisible(is_local)


def apply_local_minimum_preset(
    controls: ResolverControls, settings_values: dict[str, str]
) -> None:
    settings_values.update(_LOCAL_MINIMUM_GUI_PRESET)
    controls.chrom_threshold_spin.setValue(
        float(_LOCAL_MINIMUM_GUI_PRESET["resolver_chrom_threshold"])
    )
    controls.min_search_range_min_spin.setValue(
        float(_LOCAL_MINIMUM_GUI_PRESET["resolver_min_search_range_min"])
    )
    controls.min_relative_height_spin.setValue(
        float(_LOCAL_MINIMUM_GUI_PRESET["resolver_min_relative_height"])
    )
    controls.min_absolute_height_spin.setValue(
        float(_LOCAL_MINIMUM_GUI_PRESET["resolver_min_absolute_height"])
    )
    controls.min_ratio_top_edge_spin.setValue(
        float(_LOCAL_MINIMUM_GUI_PRESET["resolver_min_ratio_top_edge"])
    )
    controls.peak_duration_min_spin.setValue(
        float(_LOCAL_MINIMUM_GUI_PRESET["resolver_peak_duration_min"])
    )
    controls.peak_duration_max_spin.setValue(
        float(_LOCAL_MINIMUM_GUI_PRESET["resolver_peak_duration_max"])
    )
    controls.min_scans_spin.setValue(
        int(_LOCAL_MINIMUM_GUI_PRESET["resolver_min_scans"])
    )
