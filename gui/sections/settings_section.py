from pathlib import Path

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
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

from xic_extractor.config import migrate_settings_dict
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


class _LabeledSpin(QWidget):
    """SpinBox with a sub-label and explicit − / + buttons.

    Solves the Qt arrow-button hit-target problem: removes the built-in
    arrows and replaces them with 28×28 px buttons that never overlap the
    text field.
    """

    def __init__(self, label: str, spin: QAbstractSpinBox) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #57606a; font-size: 9pt;")
        lay.addWidget(lbl)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        _btn_style = "font-size: 14pt; font-weight: 600; padding: 0;"

        btn_minus = QPushButton("−")
        btn_minus.setFixedSize(32, 32)
        btn_minus.setStyleSheet(_btn_style)
        btn_minus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_minus.clicked.connect(lambda: spin.stepBy(-1))

        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(32, 32)
        btn_plus.setStyleSheet(_btn_style)
        btn_plus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_plus.clicked.connect(lambda: spin.stepBy(1))

        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setMinimumWidth(60)

        row.addWidget(btn_minus)
        row.addWidget(spin, 1)
        row.addWidget(btn_plus)
        lay.addLayout(row)


class SettingsSection(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._dirty = False
        self._settings_values = dict(CANONICAL_SETTINGS_DEFAULTS)

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
        self._save_button = QPushButton("儲存設定")
        self._save_button.setObjectName("btn_save")
        self._save_button.setVisible(False)

        self._smooth_window_spin.setRange(3, 999)
        self._smooth_window_spin.setSingleStep(2)
        self._smooth_polyorder_spin.setRange(1, 10)
        self._peak_rel_height_spin.setRange(0.50, 0.99)
        self._peak_rel_height_spin.setSingleStep(0.01)
        self._peak_rel_height_spin.setDecimals(2)
        self._peak_min_prominence_ratio_spin.setRange(0.01, 0.50)
        self._peak_min_prominence_ratio_spin.setSingleStep(0.01)
        self._peak_min_prominence_ratio_spin.setDecimals(2)
        self._ms2_precursor_tol_da_spin.setRange(0.01, 10.0)
        self._ms2_precursor_tol_da_spin.setSingleStep(0.1)
        self._ms2_precursor_tol_da_spin.setDecimals(2)
        self._nl_min_intensity_ratio_spin.setRange(0.01, 1.0)
        self._nl_min_intensity_ratio_spin.setSingleStep(0.01)
        self._nl_min_intensity_ratio_spin.setDecimals(2)

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

        body_layout.addWidget(QLabel("Signal processing"), 3, 0)
        smoothing_layout = QHBoxLayout()
        smoothing_layout.setContentsMargins(0, 0, 0, 0)
        smoothing_layout.setSpacing(16)
        smoothing_layout.addWidget(_LabeledSpin("Window", self._smooth_window_spin))
        smoothing_layout.addWidget(
            _LabeledSpin("Polyorder", self._smooth_polyorder_spin)
        )
        smoothing_layout.addWidget(
            _LabeledSpin("Peak height", self._peak_rel_height_spin)
        )
        smoothing_layout.addWidget(
            _LabeledSpin("Prominence", self._peak_min_prominence_ratio_spin)
        )
        smoothing_layout.addStretch()
        body_layout.addLayout(smoothing_layout, 3, 1, 1, 2)

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
        ms2_layout.addWidget(self._count_no_ms2_checkbox)
        ms2_layout.addStretch()
        body_layout.addLayout(ms2_layout, 4, 1, 1, 2)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(16, 0, 16, 16)
        button_row.addStretch()
        button_row.addWidget(self._save_button)
        card_layout.addLayout(button_row)

        self._wire_signals()

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
        ]
        try:
            migrated, _ = migrate_settings_dict(settings)
            self._settings_values = dict(CANONICAL_SETTINGS_DEFAULTS)
            self._settings_values.update(migrated)
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
        )

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

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
        self._save_button.clicked.connect(self._save)

    def _validate_data_dir(self, text: str) -> None:
        stripped = text.strip()
        invalid = bool(stripped) and not Path(stripped).exists()
        self._data_dir_error.setVisible(invalid)
        self._data_dir_edit.setStyleSheet("border-color: #cf222e;" if invalid else "")

    def _make_browse_button(self, target: QLineEdit) -> QPushButton:
        button = QPushButton("Browse…")
        button.clicked.connect(lambda: self._browse_for_directory(target))
        return button

    def _browse_for_directory(self, target: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Select directory", target.text()
        )
        if directory:
            target.setText(directory)

    def _save(self) -> None:
        self._set_dirty(False)
        self.settings_saved.emit()

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._save_button.setVisible(dirty)


def _int_value(settings: dict[str, str], key: str) -> int:
    try:
        return int(settings.get(key, CANONICAL_SETTINGS_DEFAULTS[key]))
    except ValueError:
        return int(CANONICAL_SETTINGS_DEFAULTS[key])


def _float_value(settings: dict[str, str], key: str) -> float:
    try:
        return float(settings.get(key, CANONICAL_SETTINGS_DEFAULTS[key]))
    except ValueError:
        return float(CANONICAL_SETTINGS_DEFAULTS[key])
