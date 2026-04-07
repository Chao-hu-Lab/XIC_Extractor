import csv
from pathlib import Path

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui import config_io

_TABLE_HEADERS = [
    "Label",
    "ISTD",
    "ISTD Pair",
    "m/z",
    "RT min",
    "RT max",
    "ppm",
    "NL(Da)",
    "",
]
(
    _COL_LABEL,
    _COL_ISTD,
    _COL_PAIR,
    _COL_MZ,
    _COL_RT_MIN,
    _COL_RT_MAX,
    _COL_PPM,
    _COL_NL,
    _COL_DEL,
) = range(9)

_NL_PRESETS: list[tuple[str, str]] = [
    ("", "—"),
    ("116.0474", "dR · 116.0474"),
    ("132.0423", "R · 132.0423"),
    ("146.0579", "MeR · 146.0579"),
]
_VALUE_TO_DISPLAY = {v: d for v, d in _NL_PRESETS}
_DISPLAY_TO_VALUE = {d: v for v, d in _NL_PRESETS}

_DEFAULT_PPM = "20"
_DEFAULT_NL_PPM_WARN = "20"
_DEFAULT_NL_PPM_MAX = "50"


class _NoScrollComboBox(QComboBox):
    """Only change the selection when the combo box itself has focus."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)


class TargetsSection(QWidget):
    targets_saved = pyqtSignal()

    _COL_NL = _COL_NL
    _COL_ISTD = _COL_ISTD

    def __init__(self) -> None:
        super().__init__()
        self._dirty = False
        self._is_loading = False
        self._row_meta: list[dict[str, str]] = []

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
        title = QLabel("② 分析目標")
        title.setObjectName("section_title")
        header_layout.addWidget(title)
        header_layout.addStretch()
        card_layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(16, 16, 16, 0)
        self._import_button = QPushButton("⬆ 匯入 CSV")
        self._add_button = QPushButton("＋ 新增目標")
        self._add_button.setObjectName("btn_add")
        self._save_button = QPushButton("💾 儲存目標")
        self._save_button.setObjectName("btn_save")
        self._save_button.setVisible(False)
        toolbar.addWidget(self._import_button)
        toolbar.addStretch()
        toolbar.addWidget(self._add_button)
        toolbar.addWidget(self._save_button)
        card_layout.addLayout(toolbar)

        self._table = QTableWidget(0, len(_TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(_TABLE_HEADERS)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setColumnWidth(_COL_LABEL, 160)
        self._table.setColumnWidth(_COL_ISTD, 55)
        self._table.setColumnWidth(_COL_PAIR, 130)
        self._table.setColumnWidth(_COL_MZ, 100)
        self._table.setColumnWidth(_COL_RT_MIN, 90)
        self._table.setColumnWidth(_COL_RT_MAX, 90)
        self._table.setColumnWidth(_COL_PPM, 70)
        self._table.setColumnWidth(_COL_NL, 150)
        self._table.setColumnWidth(_COL_DEL, 60)
        card_layout.addWidget(self._table)

        self._table.itemChanged.connect(self._on_item_changed)
        self._add_button.clicked.connect(self._on_add_row)
        self._save_button.clicked.connect(self._save)
        self._import_button.clicked.connect(self._on_import)

    def load(self, targets: list[dict[str, str]]) -> None:
        self._is_loading = True
        self._row_meta = []
        self._table.setRowCount(0)
        try:
            for target in targets:
                self._append_row(target)
        finally:
            self._is_loading = False
        self._set_dirty(False)

    def get_targets(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for row in range(self._table.rowCount()):
            meta = self._row_meta[row]
            nl_combo = self._table.cellWidget(row, _COL_NL)
            assert isinstance(nl_combo, QComboBox)
            nl_value = _DISPLAY_TO_VALUE.get(
                nl_combo.currentText(), nl_combo.currentText()
            )
            if nl_value == "—":
                nl_value = ""

            istd_container = self._table.cellWidget(row, _COL_ISTD)
            istd_cb = istd_container.findChild(QCheckBox)
            assert istd_cb is not None
            is_istd = "true" if istd_cb.isChecked() else "false"

            result.append(
                {
                    "label": self._table.item(row, _COL_LABEL).text().strip(),
                    "mz": self._table.item(row, _COL_MZ).text().strip(),
                    "rt_min": self._table.item(row, _COL_RT_MIN).text().strip(),
                    "rt_max": self._table.item(row, _COL_RT_MAX).text().strip(),
                    "ppm_tol": self._table.item(row, _COL_PPM).text().strip()
                    or _DEFAULT_PPM,
                    "neutral_loss_da": nl_value,
                    "nl_ppm_warn": meta.get("nl_ppm_warn", _DEFAULT_NL_PPM_WARN),
                    "nl_ppm_max": meta.get("nl_ppm_max", _DEFAULT_NL_PPM_MAX),
                    "is_istd": is_istd,
                    "istd_pair": self._table.item(row, _COL_PAIR).text().strip(),
                }
            )
        return result

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    def _append_row(self, target: dict[str, str] | None = None) -> None:
        target = target or {}
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_meta.append(
            {
                "nl_ppm_warn": target.get("nl_ppm_warn", _DEFAULT_NL_PPM_WARN),
                "nl_ppm_max": target.get("nl_ppm_max", _DEFAULT_NL_PPM_MAX),
            }
        )

        with QSignalBlocker(self._table):
            self._table.setItem(
                row, _COL_LABEL, QTableWidgetItem(target.get("label", ""))
            )
            self._table.setItem(
                row, _COL_PAIR, QTableWidgetItem(target.get("istd_pair", ""))
            )
            self._table.setItem(row, _COL_MZ, QTableWidgetItem(target.get("mz", "")))
            self._table.setItem(
                row, _COL_RT_MIN, QTableWidgetItem(target.get("rt_min", ""))
            )
            self._table.setItem(
                row, _COL_RT_MAX, QTableWidgetItem(target.get("rt_max", ""))
            )
            self._table.setItem(
                row, _COL_PPM, QTableWidgetItem(target.get("ppm_tol", _DEFAULT_PPM))
            )

        istd_cb = QCheckBox()
        istd_cb.setChecked(target.get("is_istd", "false").lower() == "true")
        istd_cb.stateChanged.connect(lambda _: self._set_dirty(True))
        istd_container = QWidget()
        istd_layout = QHBoxLayout(istd_container)
        istd_layout.setContentsMargins(0, 0, 0, 0)
        istd_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        istd_layout.addWidget(istd_cb)
        self._table.setCellWidget(row, _COL_ISTD, istd_container)

        nl_combo = self._make_nl_combo(target.get("neutral_loss_da", ""))
        self._table.setCellWidget(row, _COL_NL, nl_combo)

        delete_button = QPushButton("✕")
        delete_button.setObjectName("btn_delete")
        delete_button.clicked.connect(self._on_delete_clicked)
        self._table.setCellWidget(row, _COL_DEL, delete_button)

    def _make_nl_combo(self, value: str) -> _NoScrollComboBox:
        combo = _NoScrollComboBox()
        combo.setEditable(True)
        for _val, display in _NL_PRESETS:
            combo.addItem(display)
        display = _VALUE_TO_DISPLAY.get(value, value or "—")
        idx = combo.findText(display)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setEditText(value)
        combo.currentTextChanged.connect(lambda _: self._set_dirty(True))
        return combo

    def _on_item_changed(self, _item: QTableWidgetItem) -> None:
        if not self._is_loading:
            self._set_dirty(True)

    def _on_add_row(self) -> None:
        self._append_row()
        self._set_dirty(True)

    def _on_delete_clicked(self) -> None:
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        row = self._find_widget_row(button, _COL_DEL)
        if row >= 0:
            self._table.removeRow(row)
            del self._row_meta[row]
            self._set_dirty(True)

    def _on_import(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "匯入目標 CSV", "", "CSV Files (*.csv)"
        )
        if not filename:
            return
        with Path(filename).open(newline="", encoding="utf-8-sig") as handle:
            self.load(list(csv.DictReader(handle)))
        self._set_dirty(True)

    def _find_widget_row(self, widget: QWidget, column: int) -> int:
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, column) is widget:
                return row
        return -1

    def _save(self) -> None:
        config_io.write_targets(self.get_targets())
        self._set_dirty(False)
        self.targets_saved.emit()

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._save_button.setVisible(dirty)
