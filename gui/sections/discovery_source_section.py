from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.ui import field_label, section_card

_MODE_LABELS = (
    ("full", "完整：RAW 資料夾 → discovery + alignment"),
    ("discovery_only", "只 discovery：單一 RAW 檔"),
    ("align_only", "只 alignment：既有 discovery 輸出"),
)

# Which path fields each mode actually needs (others are hidden, not greyed).
_MODE_FIELDS = {
    "full": {"raw_dir", "dll_dir", "output_dir"},
    "discovery_only": {"raw_file", "dll_dir", "output_dir"},
    "align_only": {"raw_dir", "batch_index", "dll_dir", "output_dir"},
}

_FIELD_TOOLTIPS = {
    "raw_dir": "包含多個 .raw 檔的資料夾，整批跑 discovery 與對齊。",
    "raw_file": "單一 .raw 檔，只跑 discovery 不做跨樣本對齊。",
    "batch_index": "既有的 discovery_batch_index.csv，跳過 discovery 直接對齊。",
    "dll_dir": "Thermo RAW 讀取所需的 DLL 目錄。",
    "output_dir": "TSV / 工作簿 / gallery 等輸出的寫入位置。",
}


class _PathField:
    """A label / line-edit / browse triplet laid out on a shared grid row so
    every field's input column aligns."""

    def __init__(
        self,
        grid: QGridLayout,
        row: int,
        label: str,
        *,
        directory: bool,
        tooltip: str,
        on_change: object,
    ) -> None:
        self._directory = directory
        self._label = field_label(label)
        self._label.setToolTip(tooltip)
        self._edit = QLineEdit()
        self._edit.setToolTip(tooltip)
        self._edit.textChanged.connect(on_change)  # type: ignore[arg-type]
        self._browse = QPushButton("瀏覽…")
        self._browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse.clicked.connect(self._on_browse)
        grid.addWidget(self._label, row, 0)
        grid.addWidget(self._edit, row, 1)
        grid.addWidget(self._browse, row, 2)

    def value(self) -> str:
        return self._edit.text().strip()

    def set_value(self, value: str) -> None:
        self._edit.setText(value)

    def set_visible(self, visible: bool) -> None:
        for widget in (self._label, self._edit, self._browse):
            widget.setVisible(visible)

    def set_invalid(self, invalid: bool) -> None:
        self._edit.setProperty("invalid", invalid)
        style = self._edit.style()
        if style is not None:
            style.unpolish(self._edit)
            style.polish(self._edit)

    def _on_browse(self) -> None:
        if self._directory:
            chosen = QFileDialog.getExistingDirectory(
                self._edit, "選擇資料夾", self.value()
            )
        else:
            chosen, _ = QFileDialog.getOpenFileName(
                self._edit, "選擇檔案", self.value()
            )
        if chosen:
            self._edit.setText(chosen)


class DiscoverySourceSection(QWidget):
    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card, body = section_card("① 來源", "RAW 來源與輸出位置")
        root.addWidget(card)

        mode_row = QHBoxLayout()
        mode_row.addWidget(field_label("模式"))
        self._mode = QComboBox()
        for key, label in _MODE_LABELS:
            self._mode.addItem(label, key)
        self._mode.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self._mode, 1)
        body.addLayout(mode_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        body.addLayout(grid)

        emit = self.changed.emit
        self._fields = {
            "raw_dir": _PathField(
                grid, 0, "RAW 資料夾", directory=True,
                tooltip=_FIELD_TOOLTIPS["raw_dir"], on_change=emit,
            ),
            "raw_file": _PathField(
                grid, 1, "單一 RAW 檔", directory=False,
                tooltip=_FIELD_TOOLTIPS["raw_file"], on_change=emit,
            ),
            "batch_index": _PathField(
                grid, 2, "discovery_batch_index", directory=False,
                tooltip=_FIELD_TOOLTIPS["batch_index"], on_change=emit,
            ),
            "dll_dir": _PathField(
                grid, 3, "DLL 目錄", directory=True,
                tooltip=_FIELD_TOOLTIPS["dll_dir"], on_change=emit,
            ),
            "output_dir": _PathField(
                grid, 4, "輸出目錄", directory=True,
                tooltip=_FIELD_TOOLTIPS["output_dir"], on_change=emit,
            ),
        }
        self._apply_mode_visibility()

    def load(self, values: Mapping[str, object]) -> None:
        mode = _string_value(values, "mode", default="full")
        index = self._mode.findData(mode)
        self._mode.setCurrentIndex(index if index >= 0 else 0)
        self._fields["raw_dir"].set_value(_string_value(values, "raw_dir"))
        self._fields["raw_file"].set_value(_string_value(values, "raw_file"))
        self._fields["batch_index"].set_value(
            _string_value(values, "discovery_batch_index")
        )
        self._fields["dll_dir"].set_value(_string_value(values, "dll_dir"))
        self._fields["output_dir"].set_value(_string_value(values, "output_dir"))
        self._apply_mode_visibility()

    def get_values(self) -> dict[str, str]:
        return {
            "mode": self._mode_key(),
            "raw_dir": self._fields["raw_dir"].value(),
            "raw_file": self._fields["raw_file"].value(),
            "discovery_batch_index": self._fields["batch_index"].value(),
            "dll_dir": self._fields["dll_dir"].value(),
            "output_dir": self._fields["output_dir"].value(),
        }

    def is_valid(self) -> bool:
        return not self.missing_fields()

    def missing_fields(self) -> list[str]:
        """Human-readable names of required fields that are empty or invalid."""
        values = self.get_values()
        mode = values["mode"]
        problems: list[tuple[str, bool]] = [
            ("輸出目錄", not values["output_dir"]),
            ("DLL 目錄", not _is_dir(values["dll_dir"])),
        ]
        if mode == "full":
            problems.append(("RAW 資料夾", not _is_dir(values["raw_dir"])))
        elif mode == "discovery_only":
            problems.append(("單一 RAW 檔", not _is_file(values["raw_file"])))
        elif mode == "align_only":
            problems.append(("RAW 資料夾", not _is_dir(values["raw_dir"])))
            problems.append(
                ("discovery_batch_index", not _is_file(values["discovery_batch_index"]))
            )
        self._refresh_invalid(mode, values)
        return [name for name, bad in problems if bad]

    def set_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    # ── Private ─────────────────────────────────────────────────────────────

    def _refresh_invalid(self, mode: str, values: Mapping[str, str]) -> None:
        checks = {
            "raw_dir": not _is_dir(values["raw_dir"]),
            "raw_file": not _is_file(values["raw_file"]),
            "batch_index": not _is_file(values["discovery_batch_index"]),
            "dll_dir": not _is_dir(values["dll_dir"]),
            "output_dir": not values["output_dir"],
        }
        needed = _MODE_FIELDS[mode]
        for key, field in self._fields.items():
            field.set_invalid(key in needed and checks[key])

    def _mode_key(self) -> str:
        mode = self._mode.currentData()
        return str(mode if mode is not None else "full")

    def _on_mode_changed(self, _index: int) -> None:
        self._apply_mode_visibility()
        self.changed.emit()

    def _apply_mode_visibility(self) -> None:
        needed = _MODE_FIELDS[self._mode_key()]
        for key, field in self._fields.items():
            field.set_visible(key in needed)


def _is_dir(value: str) -> bool:
    return bool(value) and Path(value).is_dir()


def _is_file(value: str) -> bool:
    return bool(value) and Path(value).is_file()


def _string_value(
    values: Mapping[str, object],
    key: str,
    *,
    default: str = "",
) -> str:
    value = values.get(key, default)
    return value if isinstance(value, str) else default
