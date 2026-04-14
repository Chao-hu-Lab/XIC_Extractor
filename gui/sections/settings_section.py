from pathlib import Path

from PyQt6.QtCore import Qt, QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QLabel,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
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
        self._save_button = QPushButton("儲存設定")
        self._save_button.setObjectName("btn_save")
        self._save_button.setVisible(False)

        self._smooth_window_spin.setRange(3, 999)
        self._smooth_window_spin.setSingleStep(2)
        self._smooth_polyorder_spin.setRange(1, 10)

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

        # ── Smoothing row ────────────────────────────────────────────────────
        body_layout.addWidget(QLabel("Smoothing"), 3, 0)
        smoothing_layout = QHBoxLayout()
        smoothing_layout.setContentsMargins(0, 0, 0, 0)
        smoothing_layout.setSpacing(16)
        smoothing_layout.addWidget(_LabeledSpin("Window", self._smooth_window_spin))
        smoothing_layout.addWidget(
            _LabeledSpin("Polyorder", self._smooth_polyorder_spin)
        )
        smoothing_layout.addStretch()
        body_layout.addLayout(smoothing_layout, 3, 1, 1, 2)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(16, 0, 16, 16)
        button_row.addStretch()
        button_row.addWidget(self._save_button)
        card_layout.addLayout(button_row)

        self._wire_signals()

    def load(self, settings: dict[str, str]) -> None:
        blockers = [
            QSignalBlocker(self._data_dir_edit),
            QSignalBlocker(self._dll_dir_edit),
            QSignalBlocker(self._smooth_window_spin),
            QSignalBlocker(self._smooth_polyorder_spin),
        ]
        try:
            migrated, _ = migrate_settings_dict(settings)
            self._settings_values = dict(CANONICAL_SETTINGS_DEFAULTS)
            self._settings_values.update(migrated)
            self._data_dir_edit.setText(self._settings_values.get("data_dir", ""))
            self._dll_dir_edit.setText(self._settings_values.get("dll_dir", ""))
            self._smooth_window_spin.setValue(
                int(self._settings_values.get("smooth_window", "15") or 15)
            )
            self._smooth_polyorder_spin.setValue(
                int(self._settings_values.get("smooth_polyorder", "3") or 3)
            )
        finally:
            del blockers
        self._set_dirty(False)

    def get_values(self) -> dict[str, str]:
        values = dict(self._settings_values)
        values.update(
            {
                "data_dir": self._data_dir_edit.text().strip(),
                "dll_dir": self._dll_dir_edit.text().strip(),
                "smooth_window": str(self._smooth_window_spin.value()),
                "smooth_polyorder": str(self._smooth_polyorder_spin.value()),
            }
        )
        return values

    def is_valid(self) -> bool:
        data_dir = self._data_dir_edit.text().strip()
        return bool(data_dir) and Path(data_dir).exists()

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    def _wire_signals(self) -> None:
        self._data_dir_edit.textChanged.connect(self._validate_data_dir)
        self._data_dir_edit.textChanged.connect(lambda _: self._set_dirty(True))
        self._dll_dir_edit.textChanged.connect(lambda _: self._set_dirty(True))
        self._smooth_window_spin.valueChanged.connect(lambda _: self._set_dirty(True))
        self._smooth_polyorder_spin.valueChanged.connect(lambda _: self._set_dirty(True))
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
