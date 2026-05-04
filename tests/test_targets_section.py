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


def test_targets_table_keeps_readable_minimum_height(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)

    assert section._table.minimumHeight() >= 260


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
    cb0 = section._table.cellWidget(0, section._COL_ISTD).findChild(QCheckBox)
    cb1 = section._table.cellWidget(1, section._COL_ISTD).findChild(QCheckBox)
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
