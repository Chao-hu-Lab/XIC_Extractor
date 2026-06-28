from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QScrollArea, QSpinBox, QVBoxLayout, QWidget

from gui.wheel_guard import WheelGuard


def _wheel_down_event() -> QWheelEvent:
    return QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )


def test_wheel_guard_scrolls_page_instead_of_focused_spinbox(qapp, qtbot) -> None:
    scroll_area = QScrollArea()
    scroll_area.resize(240, 120)
    qtbot.addWidget(scroll_area)

    content = QWidget()
    layout = QVBoxLayout(content)
    spin = QSpinBox()
    spin.setRange(0, 100)
    spin.setValue(10)
    layout.addWidget(spin)
    spacer = QWidget()
    spacer.setMinimumHeight(600)
    layout.addWidget(spacer)
    scroll_area.setWidget(content)
    scroll_area.setWidgetResizable(True)
    scroll_area.show()
    qapp.processEvents()

    spin.setFocus(Qt.FocusReason.MouseFocusReason)
    qapp.processEvents()
    before_scroll = scroll_area.verticalScrollBar().value()

    guard = WheelGuard(qapp)
    handled = guard.eventFilter(spin.lineEdit(), _wheel_down_event())

    assert handled
    assert spin.value() == 10
    assert scroll_area.verticalScrollBar().value() > before_scroll
