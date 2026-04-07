# ISTD Tag, Pairing & NL Scroll Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ISTD tagging (with GUI + Excel ND warnings), ISTD–analyte RT Δ% calculation in the Excel Summary sheet, and fix the NL combo box scroll sensitivity.

**Architecture:** All changes are additive to existing layers (data → UI → analysis → pipeline → results). New CSV columns carry ISTD metadata; `col_meta` dict already flows through all analysis functions so no API changes are needed. The NL scroll fix is a self-contained QComboBox subclass in `targets_section.py`.

**Tech Stack:** Python 3.12, PyQt6, openpyxl, pytest + pytest-qt, uv

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `gui/config_io.py` | Modify | Extend `_TARGETS_FIELDS` with `is_istd`, `istd_pair` |
| `config/targets.csv` | Modify | Add new columns to live data |
| `config/targets.example.csv` | Modify | Add new columns to template |
| `gui/sections/targets_section.py` | Modify | New ISTD + ISTD Pair columns; `_NoScrollComboBox` |
| `scripts/csv_to_excel.py` | Modify | ISTD ND highlight, RT Δ% metric, ISTD_ND print |
| `gui/workers/pipeline_worker.py` | Modify | Parse `ISTD_ND:` lines; add `istd_warnings` to summary |
| `gui/sections/results_section.py` | Modify | ISTD ND warning banner |
| `tests/test_config_io.py` | Modify | Update fixture + add round-trip tests for new fields |
| `tests/test_targets_section.py` | Modify | Fix column indices; add ISTD/pair round-trip tests |
| `tests/test_pipeline_worker.py` | Modify | Add `ISTD_ND` parse test |
| `tests/test_csv_to_excel.py` | Create | Tests for `_load_column_meta` and RT Δ calculation |

---

## Task 1: Data layer — `config_io.py` + CSV files

**Files:**
- Modify: `gui/config_io.py`
- Modify: `config/targets.csv`
- Modify: `config/targets.example.csv`
- Modify: `tests/test_config_io.py`

- [ ] **Step 1: Update `_TARGETS_FIELDS` in `config_io.py`**

In `gui/config_io.py`, change:

```python
_TARGETS_FIELDS = [
    "label",
    "mz",
    "rt_min",
    "rt_max",
    "ppm_tol",
    "neutral_loss_da",
    "nl_ppm_warn",
    "nl_ppm_max",
]
```

to:

```python
_TARGETS_FIELDS = [
    "label",
    "mz",
    "rt_min",
    "rt_max",
    "ppm_tol",
    "neutral_loss_da",
    "nl_ppm_warn",
    "nl_ppm_max",
    "is_istd",
    "istd_pair",
]
```

- [ ] **Step 2: Update `config/targets.example.csv`**

Replace the file content with (preserving existing rows, adding two new columns):

```csv
label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max,is_istd,istd_pair
5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC
d3-5-hmdC,261.127276,8,10,20,116.0474,20,50,true,
5-medC,242.1136,11,13,20,116.0474,20,50,false,d3-5-medC
d3-5-medC,245.132362,11,13,20,116.0474,20,50,true,
N6-HE-dA,296.1354,22,25,20,116.0474,20,50,false,d4-N6-2HE-dA
d4-N6-2HE-dA,300.1605,22,25,20,116.0474,20,50,true,
8-oxodG,284.0989,16,18,20,116.0474,20,50,false,15N5-8-oxodG
15N5-8-oxodG,289.0841,16,18,20,116.0474,20,50,true,
8-oxo-Guo,300.0939,13,15,20,132.0423,20,50,false,"[13C,15N2]-8-oxo-Guo"
"[13C,15N2]-8-oxo-Guo",303.0913,13,15,20,132.0423,20,50,true,
```

- [ ] **Step 3: Update `config/targets.csv` the same way**

Apply the identical column additions to `config/targets.csv` (same rows as the example above, since the live file mirrors the example for new installs).

- [ ] **Step 4: Write failing tests**

In `tests/test_config_io.py`, update the `tmp_config` fixture and add two tests:

```python
@pytest.fixture()
def tmp_config(tmp_path):
    (tmp_path / "settings.csv").write_text(
        "key,value,description\ndata_dir,C:\\data,資料目錄\ndll_dir,C:\\dll,DLL路徑\n"
        "smooth_sigma,3.0,sigma\nsmooth_points,15,points\n",
        encoding="utf-8-sig",
    )
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max,is_istd,istd_pair\n"
        "5-hmdC,258.1085,8.0,10.0,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8.0,10.0,20,116.0474,20,50,true,\n",
        encoding="utf-8-sig",
    )
    return tmp_path


def test_write_targets_round_trips_with_istd_fields(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    write_targets(
        [
            {
                "label": "5-hmdC",
                "mz": "258.1085",
                "rt_min": "8.0",
                "rt_max": "10.0",
                "ppm_tol": "20",
                "neutral_loss_da": "116.0474",
                "nl_ppm_warn": "20",
                "nl_ppm_max": "50",
                "is_istd": "false",
                "istd_pair": "d3-5-hmdC",
            }
        ]
    )
    targets = read_targets()
    assert targets[0]["is_istd"] == "false"
    assert targets[0]["istd_pair"] == "d3-5-hmdC"


def test_read_targets_backward_compat_missing_istd_cols(tmp_path, monkeypatch):
    """Old CSV without is_istd/istd_pair columns reads without error."""
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max\n"
        "5-hmdC,258.1085,8,10,20,116.0474,20,50\n",
        encoding="utf-8-sig",
    )
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_path)
    targets = read_targets()
    # Missing columns return empty string via .get() at call sites — raw dict just won't have the key
    assert targets[0]["label"] == "5-hmdC"
    assert targets[0].get("is_istd", "false") == "false"
```

- [ ] **Step 5: Run tests to verify they fail (new tests only)**

```bash
uv run pytest tests/test_config_io.py::test_write_targets_round_trips_with_istd_fields tests/test_config_io.py::test_read_targets_backward_compat_missing_istd_cols -v
```

Expected: `test_write_targets_round_trips_with_istd_fields` FAIL (fields not yet in `_TARGETS_FIELDS`), `test_read_targets_backward_compat_missing_istd_cols` PASS (already works via dict).

- [ ] **Step 6: Verify `_TARGETS_FIELDS` change makes the first test pass**

```bash
uv run pytest tests/test_config_io.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add gui/config_io.py config/targets.csv config/targets.example.csv tests/test_config_io.py
git commit -m "feat: add is_istd and istd_pair fields to targets CSV schema"
```

---

## Task 2: UI — new columns + NL scroll fix in `targets_section.py`

**Files:**
- Modify: `gui/sections/targets_section.py`
- Modify: `tests/test_targets_section.py`

- [ ] **Step 1: Write failing tests first**

Replace `tests/test_targets_section.py` with (updates column indices, adds new assertions):

```python
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QComboBox

from gui.sections.targets_section import TargetsSection


def _sample_targets() -> list[dict[str, str]]:
    return [
        {
            "label": "5-hmdC",
            "mz": "258.1085",
            "rt_min": "8.0",
            "rt_max": "10.0",
            "ppm_tol": "20",
            "neutral_loss_da": "116.0474",
            "nl_ppm_warn": "20",
            "nl_ppm_max": "50",
            "is_istd": "false",
            "istd_pair": "d3-5-hmdC",
        },
        {
            "label": "d3-5-hmdC",
            "mz": "261.1273",
            "rt_min": "8.0",
            "rt_max": "10.0",
            "ppm_tol": "20",
            "neutral_loss_da": "116.0474",
            "nl_ppm_warn": "20",
            "nl_ppm_max": "50",
            "is_istd": "true",
            "istd_pair": "",
        },
    ]


def test_load_row_count(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    assert section._table.rowCount() == 2


def test_get_targets_round_trips(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    targets = section.get_targets()
    assert targets[0]["label"] == "5-hmdC"
    assert targets[0]["neutral_loss_da"] == "116.0474"
    assert targets[1]["neutral_loss_da"] == "116.0474"


def test_nl_combo_shows_preset(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    # NL is now _COL_NL = 7 (after adding ISTD col 1 and ISTD Pair col 2)
    combo = section._table.cellWidget(0, section._COL_NL)
    assert isinstance(combo, QComboBox)
    assert combo.currentText() == "dR · 116.0474"


def test_add_row(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    qtbot.mouseClick(section._add_button, Qt.MouseButton.LeftButton)
    assert section._table.rowCount() == 3


def test_istd_checkbox_round_trips(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    # Row 0: is_istd=false → unchecked; Row 1: is_istd=true → checked
    cb0 = section._table.cellWidget(0, section._COL_ISTD)
    cb1 = section._table.cellWidget(1, section._COL_ISTD)
    assert isinstance(cb0, QCheckBox)
    assert not cb0.isChecked()
    assert cb1.isChecked()
    targets = section.get_targets()
    assert targets[0]["is_istd"] == "false"
    assert targets[1]["is_istd"] == "true"


def test_istd_pair_round_trips(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    targets = section.get_targets()
    assert targets[0]["istd_pair"] == "d3-5-hmdC"
    assert targets[1]["istd_pair"] == ""
```

- [ ] **Step 2: Run to confirm failures**

```bash
uv run pytest tests/test_targets_section.py -v
```

Expected: `test_nl_combo_shows_preset`, `test_istd_checkbox_round_trips`, `test_istd_pair_round_trips` FAIL; others PASS.

- [ ] **Step 3: Implement changes in `targets_section.py`**

Replace the entire file with the updated version:

```python
import csv
from pathlib import Path

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
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

_TABLE_HEADERS = ["Label", "ISTD", "ISTD Pair", "m/z", "RT min", "RT max", "ppm", "NL(Da)", ""]
# column indices
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
    """QComboBox that only responds to wheel events when it has keyboard focus.

    Without this, scrolling the main window accidentally changes the selected NL preset.
    """

    def wheelEvent(self, event) -> None:
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class TargetsSection(QWidget):
    targets_saved = pyqtSignal()

    # Expose for tests
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

    # ── Public API ──────────────────────────────────────────────────────────────

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

            istd_cb = self._table.cellWidget(row, _COL_ISTD)
            assert isinstance(istd_cb, QCheckBox)
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

    # ── Private ─────────────────────────────────────────────────────────────────

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
            self._table.setItem(
                row, _COL_PAIR, QTableWidgetItem(target.get("istd_pair", ""))
            )

        # ISTD checkbox (centred)
        istd_cb = QCheckBox()
        istd_cb.setChecked(target.get("is_istd", "false").lower() == "true")
        istd_cb.setStyleSheet("margin-left: auto; margin-right: auto;")
        istd_cb.stateChanged.connect(lambda _: self._set_dirty(True))
        self._table.setCellWidget(row, _COL_ISTD, istd_cb)

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
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_targets_section.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run full suite to catch regressions**

```bash
uv run pytest --tb=short -q
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add gui/sections/targets_section.py tests/test_targets_section.py
git commit -m "feat: add ISTD checkbox, ISTD Pair column, and NL scroll fix"
```

---

## Task 3: Analysis — `csv_to_excel.py` ISTD changes

**Files:**
- Modify: `scripts/csv_to_excel.py`
- Create: `tests/test_csv_to_excel.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_csv_to_excel.py`:

```python
import statistics
from pathlib import Path

import pytest

from scripts.csv_to_excel import _load_column_meta, _safe_float


# ── _load_column_meta ──────────────────────────────────────────────────────────

def _write_targets(tmp_path: Path, rows: str) -> None:
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max,is_istd,istd_pair\n"
        + rows,
        encoding="utf-8-sig",
    )


def test_load_column_meta_is_istd(tmp_path):
    _write_targets(
        tmp_path,
        "5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    meta = _load_column_meta(tmp_path)
    assert meta["5-hmdC_RT"]["is_istd"] is False
    assert meta["d3-5-hmdC_RT"]["is_istd"] is True


def test_load_column_meta_istd_pair(tmp_path):
    _write_targets(
        tmp_path,
        "5-hmdC,258.1085,8,10,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8,10,20,116.0474,20,50,true,\n",
    )
    meta = _load_column_meta(tmp_path)
    assert meta["5-hmdC_RT"]["istd_pair"] == "d3-5-hmdC"
    assert meta["d3-5-hmdC_RT"]["istd_pair"] == ""


def test_load_column_meta_backward_compat(tmp_path):
    """targets.csv without is_istd/istd_pair columns reads without error."""
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max\n"
        "5-hmdC,258.1085,8,10,20,116.0474,20,50\n",
        encoding="utf-8-sig",
    )
    meta = _load_column_meta(tmp_path)
    assert meta["5-hmdC_RT"]["is_istd"] is False
    assert meta["5-hmdC_RT"]["istd_pair"] == ""


# ── RT Δ% helper (inline logic test) ──────────────────────────────────────────

def _rt_delta_pct(rt_analyte: float, rt_istd: float) -> float:
    return abs(rt_analyte - rt_istd) / rt_istd * 100


def test_rt_delta_pct_exact():
    assert abs(_rt_delta_pct(9.0, 9.1) - (0.1 / 9.1 * 100)) < 1e-9


def test_rt_delta_mean_sd():
    deltas = [_rt_delta_pct(9.0, 9.1), _rt_delta_pct(9.2, 9.1)]
    mean = sum(deltas) / len(deltas)
    sd = statistics.stdev(deltas)
    assert abs(mean - (0.1 / 9.1 * 100)) < 0.01
    assert sd >= 0
```

- [ ] **Step 2: Run to confirm failures**

```bash
uv run pytest tests/test_csv_to_excel.py -v
```

Expected: `test_load_column_meta_is_istd`, `test_load_column_meta_istd_pair`, `test_load_column_meta_backward_compat` FAIL (attributes not yet on meta); formula tests PASS.

- [ ] **Step 3: Update `_load_column_meta()` in `csv_to_excel.py`**

Inside the `for row in csv.DictReader(f):` loop, after `palette_idx += 1`, add the new meta entries to the `_RT` dict:

```python
meta[f"{label}_RT"] = {
    "type": "ms1_rt",
    "palette": pal,
    "label": label,
    "nl_col": nl_col,
    "is_istd": row.get("is_istd", "false").lower() == "true",
    "istd_pair": row.get("istd_pair", "").strip(),
}
```

(The `_Int` and `_NL` entries do not need these fields.)

- [ ] **Step 4: Run meta tests**

```bash
uv run pytest tests/test_csv_to_excel.py -v
```

Expected: all PASS.

- [ ] **Step 5: Add ISTD ND highlighting in `_build_data_sheet()`**

In the data-row loop, find the existing ND/ERROR handling block:

```python
# MS1 / sample: ND or ERROR → orange warning cell
if raw_val in ND_ERROR:
    cell.value = raw_val
    _apply(cell, fill=_fill("FFE0B2"), alignment=CENTER, border=BORDER)
    continue
```

Replace with:

```python
# MS1 / sample: ND or ERROR → orange (ISTD: deep orange to signal warning)
if raw_val in ND_ERROR:
    cell.value = raw_val
    is_istd = meta.get("is_istd", False)
    nd_hex = "FF7043" if is_istd else "FFE0B2"
    _apply(cell, fill=_fill(nd_hex), alignment=CENTER, border=BORDER)
    continue
```

- [ ] **Step 6: Add `RT Δ vs ISTD (%)` metric row in `_build_summary_sheet()`**

Add `"RT Δ vs ISTD (%)"` to the metrics list:

```python
metrics = [f"{g} ({len(group_rows[g])})" for g in _GROUPS] + [
    "Total Detection",
    "Mean RT (min)",
    "Mean Int",
    "NL ✓/⚠/✗",
    "RT Δ vs ISTD (%)",
]
```

Add the corresponding `elif` branch inside the per-compound loop (after the `elif metric == "NL ✓/⚠/✗":` block):

```python
elif metric == "RT Δ vs ISTD (%)":
    istd_label = col_meta.get(rt_key, {}).get("istd_pair", "")
    if not istd_label:
        val = "—"
    else:
        istd_rt_key = f"{istd_label}_RT"
        istd_nl_col = col_meta.get(istd_rt_key, {}).get("nl_col")
        deltas: list[float] = []
        for r in rows:
            # Analyte NL check
            if nl_key:
                anal_nl = r.get(nl_key, "")
                if anal_nl != "OK" and not anal_nl.startswith("WARN_"):
                    continue
            # ISTD NL check
            if istd_nl_col:
                istd_nl = r.get(istd_nl_col, "")
                if istd_nl != "OK" and not istd_nl.startswith("WARN_"):
                    continue
            rt_a = _safe_float(r.get(rt_key, ""))
            rt_i = _safe_float(r.get(istd_rt_key, ""))
            if rt_a is None or rt_i is None or rt_i == 0:
                continue
            deltas.append(abs(rt_a - rt_i) / rt_i * 100)
        if not deltas:
            val = "—"
        else:
            import statistics
            mean_d = sum(deltas) / len(deltas)
            sd_d = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
            val = f"{mean_d:.2f}±{sd_d:.2f}% (n={len(deltas)})"
```

Note: `import statistics` inside the branch is fine for a stdlib module; move to top-of-file if preferred.

- [ ] **Step 7: Add ISTD_ND print lines in `run()`**

At the end of `run()`, after the existing `for k in ms2_cols:` block, add:

```python
# ISTD ND warnings — printed for pipeline_worker to parse
for k in ms1_cols:
    if not col_meta.get(k, {}).get("is_istd", False):
        continue
    label_name = k.replace("_RT", "")
    nl_col_k = col_meta.get(k, {}).get("nl_col")
    if nl_col_k:
        n_det = sum(
            1
            for r in rows
            if _safe_float(r.get(k, "")) is not None
            and (
                r.get(nl_col_k, "") == "OK"
                or r.get(nl_col_k, "").startswith("WARN_")
            )
        )
    else:
        n_det = sum(1 for r in rows if _safe_float(r.get(k, "")) is not None)
    if n_det < len(rows):
        print(f"ISTD_ND: {label_name} {n_det}/{len(rows)}")
```

Also move `import statistics` to the top of the file (with the other stdlib imports).

- [ ] **Step 8: Run full test suite**

```bash
uv run pytest --tb=short -q
```

Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add scripts/csv_to_excel.py tests/test_csv_to_excel.py
git commit -m "feat: ISTD ND highlight, RT delta metric, and ISTD_ND print in csv_to_excel"
```

---

## Task 4: Pipeline — parse `ISTD_ND` lines

**Files:**
- Modify: `gui/workers/pipeline_worker.py`
- Modify: `tests/test_pipeline_worker.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_pipeline_worker.py`:

```python
def test_parse_istd_nd_warning():
    stdout = (
        "Saved : C:\\output\\xic_results.xlsx\n"
        "  d3-5-hmdC_RT detected (NL confirmed): 18/20\n"
        "  d3-5-hmdC_NL116  OK:15  WARN:3  ND:5\n"
        "ISTD_ND: d3-5-hmdC 18/20\n"
    )
    result = _worker()._parse_summary(stdout, 20)
    assert result["istd_warnings"] == [
        {"label": "d3-5-hmdC", "detected": 18, "total": 20}
    ]


def test_parse_no_istd_warnings():
    stdout = "Saved : C:\\o.xlsx\n  5-hmdC_RT detected (NL confirmed): 20/20\n"
    result = _worker()._parse_summary(stdout, 20)
    assert result["istd_warnings"] == []
```

- [ ] **Step 2: Run to confirm failures**

```bash
uv run pytest tests/test_pipeline_worker.py::test_parse_istd_nd_warning tests/test_pipeline_worker.py::test_parse_no_istd_warnings -v
```

Expected: both FAIL (`KeyError: 'istd_warnings'`).

- [ ] **Step 3: Update `_parse_summary()` in `pipeline_worker.py`**

Add `istd_warnings` initialisation at the top of the method, a parsing block in the loop, and the key in the return dict:

```python
def _parse_summary(self, stdout: str, total_files: int) -> dict:
    excel_path = ""
    nl_warn_count = 0
    targets: list[dict[str, int | str | bool]] = []
    seen_labels: set[str] = set()
    istd_warnings: list[dict[str, int | str]] = []   # ← new

    for line in stdout.splitlines():
        if match := re.search(r"Saved\s+:\s+(.+)", line):
            excel_path = match.group(1).strip()
            continue

        confirmed = re.search(
            r"\s+(\S+)_RT detected \(NL confirmed\): (\d+)/(\d+)",
            line,
        )
        if confirmed:
            label = confirmed.group(1)
            targets.append(
                {
                    "label": label,
                    "detected": int(confirmed.group(2)),
                    "total": int(confirmed.group(3)),
                    "nl_confirmed": True,
                }
            )
            seen_labels.add(label)
            continue

        basic = re.search(r"\s+(\S+)_RT detected: (\d+)/(\d+)", line)
        if basic and basic.group(1) not in seen_labels:
            targets.append(
                {
                    "label": basic.group(1),
                    "detected": int(basic.group(2)),
                    "total": int(basic.group(3)),
                    "nl_confirmed": False,
                }
            )
            seen_labels.add(basic.group(1))
            continue

        if warn_match := re.search(r"\s+\S+\s+OK:\d+\s+WARN:(\d+)\s+ND:\d+", line):
            nl_warn_count += int(warn_match.group(1))
            continue

        # ISTD ND warning line   ← new block
        if istd_nd := re.search(r"^ISTD_ND:\s+(\S+)\s+(\d+)/(\d+)", line):
            istd_warnings.append(
                {
                    "label": istd_nd.group(1),
                    "detected": int(istd_nd.group(2)),
                    "total": int(istd_nd.group(3)),
                }
            )

    return {
        "total_files": total_files,
        "targets": targets,
        "nl_warn_count": nl_warn_count,
        "excel_path": excel_path,
        "istd_warnings": istd_warnings,   # ← new
    }
```

- [ ] **Step 4: Run all pipeline tests**

```bash
uv run pytest tests/test_pipeline_worker.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest --tb=short -q
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add gui/workers/pipeline_worker.py tests/test_pipeline_worker.py
git commit -m "feat: parse ISTD_ND warning lines in pipeline_worker"
```

---

## Task 5: Results — ISTD warning banner

**Files:**
- Modify: `gui/sections/results_section.py`

> Note: `ResultsSection` is a pure GUI widget. No automated test is added here — manual smoke test described below is sufficient.

- [ ] **Step 1: Add `_istd_warn_label` widget in `__init__()`**

In `ResultsSection.__init__()`, after the `self._error_label` block (around line 93), add:

```python
self._istd_warn_label = QLabel()
self._istd_warn_label.setWordWrap(True)
self._istd_warn_label.setAlignment(
    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
)
self._istd_warn_label.setStyleSheet(
    "background-color: #FF7043; color: white; font-weight: 600;"
    " padding: 8px 12px; border-radius: 4px;"
)
self._istd_warn_label.setVisible(False)
self._body_layout.addWidget(self._istd_warn_label)
```

- [ ] **Step 2: Update `update_results()` to show/hide the banner**

In `update_results()`, after `self._error_label.setVisible(False)` and before `self._clear_grid()`, add:

```python
istd_warnings = summary.get("istd_warnings", [])
if istd_warnings:
    parts = [
        f"{w['label']} ({w['detected']}/{w['total']})"
        for w in istd_warnings
    ]
    self._istd_warn_label.setText("⚠ ISTD 未全偵測：" + "、".join(parts))
    self._istd_warn_label.setVisible(True)
else:
    self._istd_warn_label.setVisible(False)
```

- [ ] **Step 3: Update `show_error()` to also hide the banner**

In `show_error()`, after `self._open_button.setVisible(False)`, add:

```python
self._istd_warn_label.setVisible(False)
```

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest --tb=short -q
```

Expected: all PASS.

- [ ] **Step 5: Manual smoke test**

Launch the app and run an analysis where at least one ISTD is not detected in all samples. Verify:
- The orange banner appears above the result cards.
- The banner lists the affected ISTD label(s) with their detection counts.
- When re-running with all ISTDs fully detected, the banner disappears.

- [ ] **Step 6: Commit**

```bash
git add gui/sections/results_section.py
git commit -m "feat: show ISTD ND warning banner in results section"
```

---

## Final Check

- [ ] **Run full test suite one last time**

```bash
uv run pytest --tb=short -q
```

Expected: all PASS, no warnings.

- [ ] **Verify branch is ready for PR**

```bash
git log master..HEAD --oneline
```

Expected output (5 commits):

```
feat: show ISTD ND warning banner in results section
feat: parse ISTD_ND warning lines in pipeline_worker
feat: ISTD ND highlight, RT delta metric, and ISTD_ND print in csv_to_excel
feat: add ISTD checkbox, ISTD Pair column, and NL scroll fix
feat: add is_istd and istd_pair fields to targets CSV schema
```
