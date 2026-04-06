from PyQt6.QtCore import Qt

from gui.sections.targets_section import TargetsSection


def _sample_targets() -> list[dict[str, str]]:
    return [
        {
            "label": "258.1085",
            "description": "MS1",
            "mz": "258.1085",
            "ms_level": "1",
            "rt_min": "8.0",
            "rt_max": "10.0",
            "ppm_tol": "20",
            "neutral_loss_da": "",
            "nl_ppm_warn": "",
            "nl_ppm_max": "",
        },
        {
            "label": "258.1085_NL116",
            "description": "MS2",
            "mz": "258.1085",
            "ms_level": "2",
            "rt_min": "8.0",
            "rt_max": "10.0",
            "ppm_tol": "20",
            "neutral_loss_da": "116.0474",
            "nl_ppm_warn": "20",
            "nl_ppm_max": "50",
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
    assert targets[1]["neutral_loss_da"] == "116.0474"


def test_ms1_nl_cell_readonly(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    item = section._table.item(0, 6)
    assert not bool(item.flags() & Qt.ItemFlag.ItemIsEditable)


def test_add_row(qtbot):
    section = TargetsSection()
    qtbot.addWidget(section)
    section.load(_sample_targets())
    qtbot.mouseClick(section._add_button, Qt.MouseButton.LeftButton)
    assert section._table.rowCount() == 3
