from pathlib import Path

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.sections.settings_advanced_panel import (
    build_advanced_section,
    configure_advanced_controls,
    load_advanced_values,
)
from gui.sections.settings_constants import _ADVANCED_SETTING_KEYS
from gui.sections.settings_controls import AdvancedControls, ResolverControls
from gui.sections.settings_resolver_panel import (
    apply_local_minimum_preset,
    build_peak_resolver_panel,
    configure_resolver_controls,
    update_resolver_profile_visibility,
)
from gui.sections.settings_value_helpers import (
    _float_setting_text,
    _float_value,
    _int_setting_text,
    _int_value,
    _invalid_parallel_mode,
    _invalid_parallel_workers,
)
from gui.sections.settings_widgets import CollapsibleSection, _LabeledSpin
from xic_extractor.config import migrate_settings_dict
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


class SettingsSection(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._dirty = False
        self._settings_values = dict(CANONICAL_SETTINGS_DEFAULTS)
        self._invalid_parallel_mode: str | None = None
        self._invalid_parallel_workers: str | None = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("section_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        root_layout.addWidget(card)

        header = QFrame()
        header.setObjectName("section_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        title = QLabel("① Settings")
        title.setObjectName("section_title")
        header_layout.addWidget(title)
        card_layout.addWidget(header)

        body = QWidget()
        body_layout = QGridLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setHorizontalSpacing(12)
        body_layout.setVerticalSpacing(8)
        card_layout.addWidget(body)

        self._data_dir_edit = QLineEdit()
        self._dll_dir_edit = QLineEdit()
        self._smooth_window_spin = QSpinBox()
        self._smooth_polyorder_spin = QSpinBox()
        self._peak_rel_height_spin = QDoubleSpinBox()
        self._peak_min_prominence_ratio_spin = QDoubleSpinBox()
        self._ms2_precursor_tol_da_spin = QDoubleSpinBox()
        self._nl_min_intensity_ratio_spin = QDoubleSpinBox()
        self._count_no_ms2_checkbox = QCheckBox("將 NO_MS2 視為偵測到")
        self._keep_intermediate_csv_checkbox = QCheckBox("保留中間 CSV 檔")
        self._emit_score_breakdown_checkbox = QCheckBox("輸出 Score Breakdown sheet")
        self._emit_review_report_checkbox = QCheckBox("輸出 Review Report HTML")
        self._dirty_matrix_mode_checkbox = QCheckBox("啟用 dirty matrix mode")
        self._rolling_window_size_spin = QSpinBox()
        self._rt_prior_library_path_edit = QLineEdit()
        self._injection_order_source_edit = QLineEdit()
        self._resolver_mode_combo = QComboBox()
        self._resolver_chrom_threshold_spin = QDoubleSpinBox()
        self._resolver_min_search_range_min_spin = QDoubleSpinBox()
        self._resolver_min_relative_height_spin = QDoubleSpinBox()
        self._resolver_min_absolute_height_spin = QDoubleSpinBox()
        self._resolver_min_ratio_top_edge_spin = QDoubleSpinBox()
        self._resolver_peak_duration_min_spin = QDoubleSpinBox()
        self._resolver_peak_duration_max_spin = QDoubleSpinBox()
        self._resolver_min_scans_spin = QSpinBox()
        self._nl_rt_anchor_search_margin_min_spin = QDoubleSpinBox()
        self._nl_rt_anchor_half_window_min_spin = QDoubleSpinBox()
        self._nl_fallback_half_window_min_spin = QDoubleSpinBox()
        self._parallel_mode_combo = QComboBox()
        self._parallel_workers_spin = QSpinBox()
        self._legacy_resolver_panel = QWidget()
        self._local_minimum_resolver_panel = QWidget()
        self._apply_local_minimum_preset_button = QPushButton(
            "Apply Local Minimum Preset"
        )
        self._save_button = QPushButton("儲存設定")
        self._save_button.setObjectName("btn_save")
        self._save_button.setVisible(False)

        self._resolver_controls = ResolverControls(
            mode_combo=self._resolver_mode_combo,
            legacy_panel=self._legacy_resolver_panel,
            local_minimum_panel=self._local_minimum_resolver_panel,
            apply_local_minimum_preset_button=(
                self._apply_local_minimum_preset_button
            ),
            smooth_window_spin=self._smooth_window_spin,
            smooth_polyorder_spin=self._smooth_polyorder_spin,
            peak_rel_height_spin=self._peak_rel_height_spin,
            peak_min_prominence_ratio_spin=self._peak_min_prominence_ratio_spin,
            chrom_threshold_spin=self._resolver_chrom_threshold_spin,
            min_search_range_min_spin=self._resolver_min_search_range_min_spin,
            min_relative_height_spin=self._resolver_min_relative_height_spin,
            min_absolute_height_spin=self._resolver_min_absolute_height_spin,
            min_ratio_top_edge_spin=self._resolver_min_ratio_top_edge_spin,
            peak_duration_min_spin=self._resolver_peak_duration_min_spin,
            peak_duration_max_spin=self._resolver_peak_duration_max_spin,
            min_scans_spin=self._resolver_min_scans_spin,
        )
        self._advanced_controls = AdvancedControls(
            keep_intermediate_csv_checkbox=self._keep_intermediate_csv_checkbox,
            emit_score_breakdown_checkbox=self._emit_score_breakdown_checkbox,
            emit_review_report_checkbox=self._emit_review_report_checkbox,
            dirty_matrix_mode_checkbox=self._dirty_matrix_mode_checkbox,
            count_no_ms2_checkbox=self._count_no_ms2_checkbox,
            rolling_window_size_spin=self._rolling_window_size_spin,
            rt_prior_library_path_edit=self._rt_prior_library_path_edit,
            injection_order_source_edit=self._injection_order_source_edit,
            nl_rt_anchor_search_margin_min_spin=(
                self._nl_rt_anchor_search_margin_min_spin
            ),
            nl_rt_anchor_half_window_min_spin=self._nl_rt_anchor_half_window_min_spin,
            nl_fallback_half_window_min_spin=self._nl_fallback_half_window_min_spin,
            parallel_mode_combo=self._parallel_mode_combo,
            parallel_workers_spin=self._parallel_workers_spin,
        )

        configure_resolver_controls(self._resolver_controls)
        self._ms2_precursor_tol_da_spin.setRange(0.01, 10.0)
        self._ms2_precursor_tol_da_spin.setSingleStep(0.1)
        self._ms2_precursor_tol_da_spin.setDecimals(2)
        self._nl_min_intensity_ratio_spin.setRange(0.01, 1.0)
        self._nl_min_intensity_ratio_spin.setSingleStep(0.01)
        self._nl_min_intensity_ratio_spin.setDecimals(2)
        configure_advanced_controls(self._advanced_controls)

        # ── Data directory row ───────────────────────────────────────────────
        body_layout.addWidget(QLabel("Data directory"), 0, 0)
        body_layout.addWidget(self._data_dir_edit, 0, 1)
        body_layout.addWidget(self._make_browse_button(self._data_dir_edit), 0, 2)

        self._data_dir_error = QLabel("路徑不存在")
        self._data_dir_error.setStyleSheet("color: #cf222e; font-size: 9pt;")
        self._data_dir_error.setVisible(False)
        body_layout.addWidget(self._data_dir_error, 1, 1)

        # ── DLL directory row ────────────────────────────────────────────────
        body_layout.addWidget(QLabel("DLL directory"), 2, 0)
        body_layout.addWidget(self._dll_dir_edit, 2, 1)
        body_layout.addWidget(self._make_browse_button(self._dll_dir_edit), 2, 2)

        body_layout.addWidget(QLabel("Peak resolver"), 3, 0)
        body_layout.addWidget(
            build_peak_resolver_panel(self._resolver_controls), 3, 1, 1, 2
        )

        body_layout.addWidget(QLabel("MS2 / NL"), 4, 0)
        ms2_layout = QHBoxLayout()
        ms2_layout.setContentsMargins(0, 0, 0, 0)
        ms2_layout.setSpacing(16)
        ms2_layout.addWidget(
            _LabeledSpin("Precursor tol", self._ms2_precursor_tol_da_spin)
        )
        ms2_layout.addWidget(
            _LabeledSpin("Min intensity", self._nl_min_intensity_ratio_spin)
        )
        ms2_layout.addStretch()
        body_layout.addLayout(ms2_layout, 4, 1, 1, 2)

        self.advanced_section = CollapsibleSection("⚙ Advanced — debug 與方法開發專用")
        build_advanced_section(
            self.advanced_section,
            self._advanced_controls,
            self._make_file_browse_button,
        )
        body_layout.addWidget(self.advanced_section, 5, 0, 1, 3)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(16, 0, 16, 16)
        button_row.addStretch()
        button_row.addWidget(self._save_button)
        card_layout.addLayout(button_row)

        self._wire_signals()
        self._update_resolver_profile_visibility()

    def load(self, settings: dict[str, str]) -> bool:
        blockers = [
            QSignalBlocker(self._data_dir_edit),
            QSignalBlocker(self._dll_dir_edit),
            QSignalBlocker(self._smooth_window_spin),
            QSignalBlocker(self._smooth_polyorder_spin),
            QSignalBlocker(self._peak_rel_height_spin),
            QSignalBlocker(self._peak_min_prominence_ratio_spin),
            QSignalBlocker(self._ms2_precursor_tol_da_spin),
            QSignalBlocker(self._nl_min_intensity_ratio_spin),
            QSignalBlocker(self._count_no_ms2_checkbox),
            QSignalBlocker(self._keep_intermediate_csv_checkbox),
            QSignalBlocker(self._emit_score_breakdown_checkbox),
            QSignalBlocker(self._emit_review_report_checkbox),
            QSignalBlocker(self._dirty_matrix_mode_checkbox),
            QSignalBlocker(self._rolling_window_size_spin),
            QSignalBlocker(self._rt_prior_library_path_edit),
            QSignalBlocker(self._injection_order_source_edit),
            QSignalBlocker(self._resolver_mode_combo),
            QSignalBlocker(self._resolver_chrom_threshold_spin),
            QSignalBlocker(self._resolver_min_search_range_min_spin),
            QSignalBlocker(self._resolver_min_relative_height_spin),
            QSignalBlocker(self._resolver_min_absolute_height_spin),
            QSignalBlocker(self._resolver_min_ratio_top_edge_spin),
            QSignalBlocker(self._resolver_peak_duration_min_spin),
            QSignalBlocker(self._resolver_peak_duration_max_spin),
            QSignalBlocker(self._resolver_min_scans_spin),
            QSignalBlocker(self._nl_rt_anchor_search_margin_min_spin),
            QSignalBlocker(self._nl_rt_anchor_half_window_min_spin),
            QSignalBlocker(self._nl_fallback_half_window_min_spin),
            QSignalBlocker(self._parallel_mode_combo),
            QSignalBlocker(self._parallel_workers_spin),
        ]
        try:
            migrated, _ = migrate_settings_dict(settings)
            self._settings_values = dict(CANONICAL_SETTINGS_DEFAULTS)
            self._settings_values.update(migrated)
            self._invalid_parallel_mode = _invalid_parallel_mode(
                self._settings_values.get("parallel_mode", "")
            )
            self._invalid_parallel_workers = _invalid_parallel_workers(
                self._settings_values.get("parallel_workers", "")
            )
            self._data_dir_edit.setText(self._settings_values.get("data_dir", ""))
            self._dll_dir_edit.setText(self._settings_values.get("dll_dir", ""))
            self._smooth_window_spin.setValue(
                _int_value(self._settings_values, "smooth_window")
            )
            self._smooth_polyorder_spin.setValue(
                _int_value(self._settings_values, "smooth_polyorder")
            )
            self._peak_rel_height_spin.setValue(
                _float_value(self._settings_values, "peak_rel_height")
            )
            self._peak_min_prominence_ratio_spin.setValue(
                _float_value(self._settings_values, "peak_min_prominence_ratio")
            )
            self._ms2_precursor_tol_da_spin.setValue(
                _float_value(self._settings_values, "ms2_precursor_tol_da")
            )
            self._nl_min_intensity_ratio_spin.setValue(
                _float_value(self._settings_values, "nl_min_intensity_ratio")
            )
            self._count_no_ms2_checkbox.setChecked(
                self._settings_values.get("count_no_ms2_as_detected", "false").lower()
                == "true"
            )
            load_advanced_values(
                self._settings_values,
                self._advanced_controls,
                self._resolver_controls,
            )
            self._update_resolver_profile_visibility()
        finally:
            del blockers
        self._set_dirty(False)
        return migrated != settings

    def get_values(self) -> dict[str, str]:
        values = dict(self._settings_values)
        values.update(
            {
                "data_dir": self._data_dir_edit.text().strip(),
                "dll_dir": self._dll_dir_edit.text().strip(),
                "smooth_window": str(self._smooth_window_spin.value()),
                "smooth_polyorder": str(self._smooth_polyorder_spin.value()),
                "peak_rel_height": f"{self._peak_rel_height_spin.value():.2f}",
                "peak_min_prominence_ratio": (
                    f"{self._peak_min_prominence_ratio_spin.value():.2f}"
                ),
                "ms2_precursor_tol_da": f"{self._ms2_precursor_tol_da_spin.value():g}",
                "nl_min_intensity_ratio": (
                    f"{self._nl_min_intensity_ratio_spin.value():.2f}"
                ),
                "count_no_ms2_as_detected": (
                    "true" if self._count_no_ms2_checkbox.isChecked() else "false"
                ),
                "keep_intermediate_csv": (
                    "true"
                    if self._keep_intermediate_csv_checkbox.isChecked()
                    else "false"
                ),
                "emit_score_breakdown": (
                    "true"
                    if self._emit_score_breakdown_checkbox.isChecked()
                    else "false"
                ),
                "emit_review_report": (
                    "true" if self._emit_review_report_checkbox.isChecked() else "false"
                ),
                "dirty_matrix_mode": (
                    "true" if self._dirty_matrix_mode_checkbox.isChecked() else "false"
                ),
                "rolling_window_size": _int_setting_text(
                    self._settings_values,
                    "rolling_window_size",
                    self._rolling_window_size_spin,
                ),
                "rt_prior_library_path": (
                    self._rt_prior_library_path_edit.text().strip()
                ),
                "injection_order_source": (
                    self._injection_order_source_edit.text().strip()
                ),
                "resolver_mode": self._resolver_mode_combo.currentText(),
                "resolver_chrom_threshold": _float_setting_text(
                    self._settings_values,
                    "resolver_chrom_threshold",
                    self._resolver_chrom_threshold_spin,
                ),
                "resolver_min_search_range_min": _float_setting_text(
                    self._settings_values,
                    "resolver_min_search_range_min",
                    self._resolver_min_search_range_min_spin,
                ),
                "resolver_min_relative_height": _float_setting_text(
                    self._settings_values,
                    "resolver_min_relative_height",
                    self._resolver_min_relative_height_spin,
                ),
                "resolver_min_absolute_height": _float_setting_text(
                    self._settings_values,
                    "resolver_min_absolute_height",
                    self._resolver_min_absolute_height_spin,
                ),
                "resolver_min_ratio_top_edge": _float_setting_text(
                    self._settings_values,
                    "resolver_min_ratio_top_edge",
                    self._resolver_min_ratio_top_edge_spin,
                ),
                "resolver_peak_duration_min": _float_setting_text(
                    self._settings_values,
                    "resolver_peak_duration_min",
                    self._resolver_peak_duration_min_spin,
                ),
                "resolver_peak_duration_max": _float_setting_text(
                    self._settings_values,
                    "resolver_peak_duration_max",
                    self._resolver_peak_duration_max_spin,
                ),
                "resolver_min_scans": _int_setting_text(
                    self._settings_values,
                    "resolver_min_scans",
                    self._resolver_min_scans_spin,
                ),
                "nl_rt_anchor_search_margin_min": _float_setting_text(
                    self._settings_values,
                    "nl_rt_anchor_search_margin_min",
                    self._nl_rt_anchor_search_margin_min_spin,
                ),
                "nl_rt_anchor_half_window_min": _float_setting_text(
                    self._settings_values,
                    "nl_rt_anchor_half_window_min",
                    self._nl_rt_anchor_half_window_min_spin,
                ),
                "nl_fallback_half_window_min": _float_setting_text(
                    self._settings_values,
                    "nl_fallback_half_window_min",
                    self._nl_fallback_half_window_min_spin,
                ),
                "parallel_mode": (
                    self._invalid_parallel_mode
                    if self._invalid_parallel_mode is not None
                    else self._parallel_mode_combo.currentText()
                ),
                "parallel_workers": (
                    self._invalid_parallel_workers
                    if self._invalid_parallel_workers is not None
                    else _int_setting_text(
                        self._settings_values,
                        "parallel_workers",
                        self._parallel_workers_spin,
                    )
                ),
            }
        )
        return values

    def is_valid(self) -> bool:
        values = self.get_values()
        smooth_window = int(values["smooth_window"])
        smooth_polyorder = int(values["smooth_polyorder"])
        peak_rel_height = float(values["peak_rel_height"])
        peak_min_prominence_ratio = float(values["peak_min_prominence_ratio"])
        ms2_precursor_tol_da = float(values["ms2_precursor_tol_da"])
        nl_min_intensity_ratio = float(values["nl_min_intensity_ratio"])
        resolver_min_search_range_min = float(values["resolver_min_search_range_min"])
        resolver_min_relative_height = float(values["resolver_min_relative_height"])
        resolver_min_absolute_height = float(values["resolver_min_absolute_height"])
        resolver_min_ratio_top_edge = float(values["resolver_min_ratio_top_edge"])
        resolver_peak_duration_min = float(values["resolver_peak_duration_min"])
        resolver_peak_duration_max = float(values["resolver_peak_duration_max"])
        resolver_min_scans = int(values["resolver_min_scans"])
        try:
            parallel_workers = int(values["parallel_workers"])
        except ValueError:
            parallel_workers = 0
        return (
            bool(values["data_dir"])
            and bool(values["dll_dir"])
            and smooth_window >= 3
            and smooth_window % 2 == 1
            and 1 <= smooth_polyorder < smooth_window
            and 0.50 <= peak_rel_height <= 0.99
            and 0.01 <= peak_min_prominence_ratio <= 0.50
            and ms2_precursor_tol_da > 0
            and 0 < nl_min_intensity_ratio <= 1
            and values["resolver_mode"] in {"legacy_savgol", "local_minimum"}
            and resolver_min_search_range_min > 0
            and 0 <= resolver_min_relative_height <= 1
            and resolver_min_absolute_height >= 0
            and resolver_min_ratio_top_edge > 1
            and resolver_peak_duration_min >= 0
            and resolver_peak_duration_max > 0
            and resolver_peak_duration_min <= resolver_peak_duration_max
            and resolver_min_scans >= 1
            and values["parallel_mode"] in {"serial", "process"}
            and parallel_workers >= 1
        )

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    def advanced_section_field_keys(self) -> tuple[str, ...]:
        return _ADVANCED_SETTING_KEYS

    def _update_resolver_profile_visibility(self) -> None:
        update_resolver_profile_visibility(self._resolver_controls)

    def _on_resolver_mode_changed(self, _mode: str) -> None:
        self._update_resolver_profile_visibility()
        self._set_dirty(True)

    def _apply_local_minimum_preset(self) -> None:
        apply_local_minimum_preset(self._resolver_controls, self._settings_values)
        self._set_dirty(True)

    def _wire_signals(self) -> None:
        self._data_dir_edit.textChanged.connect(self._validate_data_dir)
        self._data_dir_edit.textChanged.connect(lambda _: self._set_dirty(True))
        self._dll_dir_edit.textChanged.connect(lambda _: self._set_dirty(True))
        self._smooth_window_spin.valueChanged.connect(lambda _: self._set_dirty(True))
        self._smooth_polyorder_spin.valueChanged.connect(
            lambda _: self._set_dirty(True)
        )
        self._peak_rel_height_spin.valueChanged.connect(lambda _: self._set_dirty(True))
        self._peak_min_prominence_ratio_spin.valueChanged.connect(
            lambda _: self._set_dirty(True)
        )
        self._ms2_precursor_tol_da_spin.valueChanged.connect(
            lambda _: self._set_dirty(True)
        )
        self._nl_min_intensity_ratio_spin.valueChanged.connect(
            lambda _: self._set_dirty(True)
        )
        self._count_no_ms2_checkbox.stateChanged.connect(
            lambda _: self._set_dirty(True)
        )
        self._wire_advanced_signals()
        self._save_button.clicked.connect(self._save)

    def _wire_advanced_signals(self) -> None:
        for checkbox in (
            self._keep_intermediate_csv_checkbox,
            self._emit_score_breakdown_checkbox,
            self._emit_review_report_checkbox,
            self._dirty_matrix_mode_checkbox,
        ):
            checkbox.stateChanged.connect(lambda _: self._set_dirty(True))
        for line_edit in (
            self._rt_prior_library_path_edit,
            self._injection_order_source_edit,
        ):
            line_edit.textChanged.connect(lambda _: self._set_dirty(True))
        self._resolver_mode_combo.currentTextChanged.connect(
            self._on_resolver_mode_changed
        )
        self._apply_local_minimum_preset_button.clicked.connect(
            self._apply_local_minimum_preset
        )
        self._parallel_mode_combo.currentTextChanged.connect(
            self._on_parallel_mode_changed
        )
        self._parallel_workers_spin.valueChanged.connect(
            self._on_parallel_workers_changed
        )
        for spin in (
            self._rolling_window_size_spin,
            self._resolver_chrom_threshold_spin,
            self._resolver_min_search_range_min_spin,
            self._resolver_min_relative_height_spin,
            self._resolver_min_absolute_height_spin,
            self._resolver_min_ratio_top_edge_spin,
            self._resolver_peak_duration_min_spin,
            self._resolver_peak_duration_max_spin,
            self._resolver_min_scans_spin,
            self._nl_rt_anchor_search_margin_min_spin,
            self._nl_rt_anchor_half_window_min_spin,
            self._nl_fallback_half_window_min_spin,
        ):
            spin.valueChanged.connect(lambda _: self._set_dirty(True))

    def _on_parallel_mode_changed(self, _text: str) -> None:
        self._invalid_parallel_mode = None
        self._set_dirty(True)

    def _on_parallel_workers_changed(self, _value: int) -> None:
        self._invalid_parallel_workers = None
        self._set_dirty(True)

    def _validate_data_dir(self, text: str) -> None:
        stripped = text.strip()
        invalid = bool(stripped) and not Path(stripped).exists()
        self._data_dir_error.setVisible(invalid)
        self._data_dir_edit.setStyleSheet("border-color: #cf222e;" if invalid else "")

    def _make_browse_button(self, target: QLineEdit) -> QPushButton:
        button = QPushButton("Browse…")
        button.clicked.connect(lambda: self._browse_for_directory(target))
        return button

    def _make_file_browse_button(self, target: QLineEdit) -> QPushButton:
        button = QPushButton("Browse…")
        button.clicked.connect(lambda: self._browse_for_file(target))
        return button

    def _browse_for_directory(self, target: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select directory", target.text()
        )
        if directory:
            target.setText(directory)

    def _browse_for_file(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file", target.text())
        if path:
            target.setText(path)

    def _save(self) -> None:
        self._set_dirty(False)
        self.settings_saved.emit()

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._save_button.setVisible(dirty)
