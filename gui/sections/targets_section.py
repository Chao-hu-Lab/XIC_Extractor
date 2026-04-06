import csv
from pathlib import Path

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class TargetsSection(QWidget):
    targets_saved = pyqtSignal()

    _TABLE_HEADERS = ["Label", "m/z", "RT min", "RT max", "ppm", "MS", "NL(Da)", ""]

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
        title = QLabel("② Targets")
        title.setObjectName("section_title")
        header_layout.addWidget(title)
        header_layout.addStretch()
        card_layout.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(16, 16, 16, 0)
        self._import_button = QPushButton("匯入 CSV")
        self._add_button = QPushButton("新增目標")
        self._add_button.setObjectName("btn_add")
        self._save_button = QPushButton("💾 儲存目標")
        self._save_button.setObjectName("btn_save")
        self._save_button.setVisible(False)
        toolbar.addWidget(self._import_button)
        toolbar.addStretch()
        toolbar.addWidget(self._add_button)
        toolbar.addWidget(self._save_button)
        card_layout.addLayout(toolbar)

        self._table = QTableWidget(0, len(self._TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(self._TABLE_HEADERS)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setColumnWidth(0, 160)
        self._table.setColumnWidth(1, 100)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(4, 70)
        self._table.setColumnWidth(5, 80)
        self._table.setColumnWidth(6, 100)
        self._table.setColumnWidth(7, 80)
        card_layout.addWidget(self._table)

        self._wire_signals()

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
        targets: list[dict[str, str]] = []
        for row in range(self._table.rowCount()):
            meta = self._row_meta[row].copy()
            ms_combo = self._table.cellWidget(row, 5)
            assert isinstance(ms_combo, QComboBox)
            nl_item = self._table.item(row, 6)
            neutral_loss = ""
            if ms_combo.currentText() == "2" and nl_item is not None:
                neutral_loss = nl_item.text().strip()

            targets.append(
                {
                    "label": self._table.item(row, 0).text().strip(),
                    "description": meta.get("description", ""),
                    "mz": self._table.item(row, 1).text().strip(),
                    "ms_level": ms_combo.currentText(),
                    "rt_min": self._table.item(row, 2).text().strip(),
                    "rt_max": self._table.item(row, 3).text().strip(),
                    "ppm_tol": self._table.item(row, 4).text().strip(),
                    "neutral_loss_da": neutral_loss,
                    "nl_ppm_warn": meta.get("nl_ppm_warn", ""),
                    "nl_ppm_max": meta.get("nl_ppm_max", ""),
                }
            )
        return targets

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    def _wire_signals(self) -> None:
        self._table.itemChanged.connect(self._on_item_changed)
        self._add_button.clicked.connect(self._on_add_row)
        self._save_button.clicked.connect(self._save)
        self._import_button.clicked.connect(self._on_import)

    def _append_row(self, target: dict[str, str] | None = None) -> None:
        target = target or {
            "label": "",
            "description": "",
            "mz": "",
            "ms_level": "1",
            "rt_min": "",
            "rt_max": "",
            "ppm_tol": "",
            "neutral_loss_da": "",
            "nl_ppm_warn": "",
            "nl_ppm_max": "",
        }
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_meta.append(
            {
                "description": target.get("description", ""),
                "nl_ppm_warn": target.get("nl_ppm_warn", ""),
                "nl_ppm_max": target.get("nl_ppm_max", ""),
            }
        )

        blockers = [QSignalBlocker(self._table)]
        try:
            self._table.setItem(row, 0, QTableWidgetItem(target.get("label", "")))
            self._table.setItem(row, 1, QTableWidgetItem(target.get("mz", "")))
            self._table.setItem(row, 2, QTableWidgetItem(target.get("rt_min", "")))
            self._table.setItem(row, 3, QTableWidgetItem(target.get("rt_max", "")))
            self._table.setItem(row, 4, QTableWidgetItem(target.get("ppm_tol", "")))

            combo = QComboBox()
            combo.addItems(["1", "2"])
            combo.setCurrentText(target.get("ms_level", "1") or "1")
            combo.currentTextChanged.connect(lambda _value, widget=combo: self._on_ms_combo_changed(widget))
            self._table.setCellWidget(row, 5, combo)

            self._set_nl_item(row, combo.currentText(), target.get("neutral_loss_da", ""))

            delete_button = QPushButton("刪除")
            delete_button.setObjectName("btn_delete")
            delete_button.clicked.connect(lambda: self._delete_row_for_sender())
            self._table.setCellWidget(row, 7, delete_button)
        finally:
            del blockers

    def _set_nl_item(self, row: int, ms_level: str, neutral_loss: str) -> None:
        if ms_level == "1":
            item = QTableWidgetItem("—")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 6, item)
            return

        item = QTableWidgetItem(neutral_loss)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 6, item)

    def _on_ms_combo_changed(self, combo: QComboBox) -> None:
        row = self._find_row_for_widget(combo, 5)
        if row < 0:
            return
        current_item = self._table.item(row, 6)
        current_text = "" if current_item is None or current_item.text() == "—" else current_item.text()
        blocker = QSignalBlocker(self._table)
        try:
            self._set_nl_item(row, combo.currentText(), current_text)
        finally:
            del blocker
        self._set_dirty(True)

    def _on_item_changed(self, _item: QTableWidgetItem) -> None:
        if not self._is_loading:
            self._set_dirty(True)

    def _on_add_row(self) -> None:
        self._append_row()
        self._set_dirty(True)

    def _delete_row_for_sender(self) -> None:
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        row = self._find_row_for_widget(button, 7)
        if row >= 0:
            self._delete_row(row)

    def _delete_row(self, row: int) -> None:
        self._table.removeRow(row)
        del self._row_meta[row]
        self._set_dirty(True)

    def _on_import(self) -> None:
        filename, _filter = QFileDialog.getOpenFileName(self, "Import targets", "", "CSV Files (*.csv)")
        if not filename:
            return
        with Path(filename).open(newline="", encoding="utf-8-sig") as handle:
            self.load(list(csv.DictReader(handle)))
        self._set_dirty(True)

    def _find_row_for_widget(self, widget: QWidget, column: int) -> int:
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, column) is widget:
                return row
        return -1

    def _save(self) -> None:
        self._set_dirty(False)
        self.targets_saved.emit()

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._save_button.setVisible(dirty)
