from pathlib import Path

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
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
    QDoubleSpinBox,
)


class SettingsSection(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._dirty = False

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
        body_layout.setVerticalSpacing(12)
        card_layout.addWidget(body)

        self._data_dir_edit = QLineEdit()
        self._dll_dir_edit = QLineEdit()
        self._smooth_points_spin = QSpinBox()
        self._smooth_sigma_spin = QDoubleSpinBox()
        self._save_button = QPushButton("💾 儲存設定")
        self._save_button.setObjectName("btn_save")
        self._save_button.setVisible(False)

        self._smooth_points_spin.setRange(1, 999)
        self._smooth_sigma_spin.setRange(0.1, 999.0)
        self._smooth_sigma_spin.setDecimals(2)
        self._smooth_sigma_spin.setSingleStep(0.1)

        body_layout.addWidget(QLabel("Data directory"), 0, 0)
        body_layout.addWidget(self._data_dir_edit, 0, 1)
        body_layout.addWidget(self._make_browse_button(self._data_dir_edit), 0, 2)

        body_layout.addWidget(QLabel("DLL directory"), 1, 0)
        body_layout.addWidget(self._dll_dir_edit, 1, 1)
        body_layout.addWidget(self._make_browse_button(self._dll_dir_edit), 1, 2)

        body_layout.addWidget(QLabel("Smoothing"), 2, 0)
        smoothing_layout = QHBoxLayout()
        smoothing_layout.setContentsMargins(0, 0, 0, 0)
        smoothing_layout.addWidget(self._smooth_points_spin)
        smoothing_layout.addWidget(self._smooth_sigma_spin)
        body_layout.addLayout(smoothing_layout, 2, 1, 1, 2)

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
            QSignalBlocker(self._smooth_points_spin),
            QSignalBlocker(self._smooth_sigma_spin),
        ]
        try:
            self._data_dir_edit.setText(settings.get("data_dir", ""))
            self._dll_dir_edit.setText(settings.get("dll_dir", ""))
            self._smooth_points_spin.setValue(int(settings.get("smooth_points", "15") or 15))
            self._smooth_sigma_spin.setValue(float(settings.get("smooth_sigma", "3.0") or 3.0))
        finally:
            del blockers
        self._set_dirty(False)

    def get_values(self) -> dict[str, str]:
        return {
            "data_dir": self._data_dir_edit.text().strip(),
            "dll_dir": self._dll_dir_edit.text().strip(),
            "smooth_points": str(self._smooth_points_spin.value()),
            "smooth_sigma": f"{self._smooth_sigma_spin.value():.1f}",
        }

    def is_valid(self) -> bool:
        data_dir = self._data_dir_edit.text().strip()
        return bool(data_dir) and Path(data_dir).exists()

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    def _wire_signals(self) -> None:
        self._data_dir_edit.textChanged.connect(lambda _text: self._set_dirty(True))
        self._dll_dir_edit.textChanged.connect(lambda _text: self._set_dirty(True))
        self._smooth_points_spin.valueChanged.connect(lambda _value: self._set_dirty(True))
        self._smooth_sigma_spin.valueChanged.connect(lambda _value: self._set_dirty(True))
        self._save_button.clicked.connect(self._save)

    def _make_browse_button(self, target: QLineEdit) -> QPushButton:
        button = QPushButton("Browse…")
        button.clicked.connect(lambda: self._browse_for_directory(target))
        return button

    def _browse_for_directory(self, target: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select directory", target.text())
        if directory:
            target.setText(directory)

    def _save(self) -> None:
        self._set_dirty(False)
        self.settings_saved.emit()

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._save_button.setVisible(dirty)
