from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox

from gui.sections.targets_section import TargetsSection


def _sample_targets() -> list[dict[str, str]]:
    return [
        {
            "label": "258.1085",
            "mz": "258.1085",
            "rt_min": "8.0",
            "rt_max": "10.0",
            "ppm_tol": "20",
            "neutral_loss_da": "116.0474",
            "nl_ppm_warn": "20",
            "nl_ppm_max": "50",
        },
        {
            "label": "242.1136",
            "mz": "242.1136",
            "rt_min": "11.0",
            "rt_max": "13.0",
            "ppm_tol": "20",
            "neutral_loss_da": "",
            "nl_ppm_warn": "",
            "nl_ppm_max": "",
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
    assert targets[0]["label"] == "258.1085"
    assert targets[0]["neutral_loss_da"] == "116.0474"
    assert targets[1]["neutral_loss_da"] == ""


def test_nl_combo_shows_preset(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    combo = section._table.cellWidget(0, 5)
    assert isinstance(combo, QComboBox)
    assert combo.currentText() == "dR · 116.0474"


def test_add_row(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    qtbot.mouseClick(section._add_button, Qt.MouseButton.LeftButton)
    assert section._table.rowCount() == 3
