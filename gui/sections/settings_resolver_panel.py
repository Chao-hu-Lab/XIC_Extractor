from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.sections.settings_constants import (
    _GUI_UNBOUNDED_FLOAT_MAX,
    _LOCAL_MINIMUM_GUI_PRESET,
)
from gui.sections.settings_controls import ResolverControls
from gui.sections.settings_widgets import _LabeledSpin, _set_float_range
from xic_extractor.settings_schema import RESOLVER_MODES


def configure_resolver_controls(controls: ResolverControls) -> None:
    controls.mode_combo.addItems(list(RESOLVER_MODES))
    controls.smooth_window_spin.setRange(3, 999)
    controls.smooth_window_spin.setSingleStep(2)
    controls.smooth_polyorder_spin.setRange(1, 10)
    controls.ms1_morphology_smoothing_window_spin.setRange(3, 999)
    controls.ms1_morphology_smoothing_window_spin.setSingleStep(2)
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


def _labeled_spin_grid(items: list[QWidget], columns: int = 3) -> QGridLayout:
    """Lay labeled spins out in a wrapping grid instead of one wide row.

    A QHBoxLayout cannot wrap, so packing every resolver spin into a single row
    forced the whole settings card wider than the viewport and triggered a
    global horizontal scrollbar. A fixed-column grid wraps onto extra rows and
    keeps the card within the available width even at the minimum window size
    (3 columns fit the ~554px panel width budget at 960px windows).
    """
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(8)
    for index, widget in enumerate(items):
        grid.addWidget(widget, index // columns, index % columns)
    grid.setColumnStretch(columns, 1)  # keep cells compact and left-aligned
    return grid


def build_resolver_mode_row(controls: ResolverControls) -> QWidget:
    """Just the resolver Mode selector. Kept visible in the main settings panel;
    the per-mode numeric detail lives behind a collapsible section built by
    build_resolver_detail_panel()."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(QLabel("Mode"))
    layout.addWidget(controls.mode_combo)
    layout.addStretch()
    return row


def build_resolver_detail_panel(controls: ResolverControls) -> QWidget:
    """The per-mode numeric profiles (legacy savgol + local-minimum). Rarely
    tuned per run, so the caller places this inside a collapsed-by-default
    section; the legacy/local panels still show/hide by resolver mode."""
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    controls.legacy_panel.setLayout(
        _labeled_spin_grid(
            [
                _LabeledSpin("Window", controls.smooth_window_spin),
                _LabeledSpin("Polyorder", controls.smooth_polyorder_spin),
                _LabeledSpin(
                    "MS1 smooth",
                    controls.ms1_morphology_smoothing_window_spin,
                ),
                _LabeledSpin("Peak height", controls.peak_rel_height_spin),
                _LabeledSpin("Prominence", controls.peak_min_prominence_ratio_spin),
            ]
        )
    )
    layout.addWidget(controls.legacy_panel)

    local_layout = QVBoxLayout(controls.local_minimum_panel)
    local_layout.setContentsMargins(0, 0, 0, 0)
    local_layout.setSpacing(8)
    local_layout.addLayout(
        _labeled_spin_grid(
            [
                _LabeledSpin("Chrom threshold", controls.chrom_threshold_spin),
                _LabeledSpin("Search range", controls.min_search_range_min_spin),
                _LabeledSpin("Min rel height", controls.min_relative_height_spin),
                _LabeledSpin("Min abs height", controls.min_absolute_height_spin),
                _LabeledSpin("Top/edge", controls.min_ratio_top_edge_spin),
                _LabeledSpin("Min duration", controls.peak_duration_min_spin),
                _LabeledSpin("Max duration", controls.peak_duration_max_spin),
                _LabeledSpin("Min scans", controls.min_scans_spin),
            ]
        )
    )

    preset_row = QHBoxLayout()
    preset_row.setContentsMargins(0, 0, 0, 0)
    preset_row.addWidget(controls.apply_local_minimum_preset_button)
    preset_row.addStretch()
    local_layout.addLayout(preset_row)
    layout.addWidget(controls.local_minimum_panel)

    return panel


def update_resolver_profile_visibility(controls: ResolverControls) -> None:
    resolver_mode = controls.mode_combo.currentText()
    controls.legacy_panel.setVisible(
        resolver_mode in {"legacy_savgol", "region_first_safe_merge"}
    )
    controls.local_minimum_panel.setVisible(
        resolver_mode in {"local_minimum", "region_first_safe_merge"}
    )


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
