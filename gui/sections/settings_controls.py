from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)


@dataclass(frozen=True)
class ResolverControls:
    mode_combo: QComboBox
    legacy_panel: QWidget
    local_minimum_panel: QWidget
    apply_local_minimum_preset_button: QPushButton
    smooth_window_spin: QSpinBox
    smooth_polyorder_spin: QSpinBox
    peak_rel_height_spin: QDoubleSpinBox
    peak_min_prominence_ratio_spin: QDoubleSpinBox
    chrom_threshold_spin: QDoubleSpinBox
    min_search_range_min_spin: QDoubleSpinBox
    min_relative_height_spin: QDoubleSpinBox
    min_absolute_height_spin: QDoubleSpinBox
    min_ratio_top_edge_spin: QDoubleSpinBox
    peak_duration_min_spin: QDoubleSpinBox
    peak_duration_max_spin: QDoubleSpinBox
    min_scans_spin: QSpinBox


@dataclass(frozen=True)
class AdvancedControls:
    keep_intermediate_csv_checkbox: QCheckBox
    emit_score_breakdown_checkbox: QCheckBox
    emit_review_report_checkbox: QCheckBox
    dirty_matrix_mode_checkbox: QCheckBox
    count_no_ms2_checkbox: QCheckBox
    rolling_window_size_spin: QSpinBox
    rt_prior_library_path_edit: QLineEdit
    injection_order_source_edit: QLineEdit
    nl_rt_anchor_search_margin_min_spin: QDoubleSpinBox
    nl_rt_anchor_half_window_min_spin: QDoubleSpinBox
    nl_fallback_half_window_min_spin: QDoubleSpinBox
    parallel_mode_combo: QComboBox
    parallel_workers_spin: QSpinBox
