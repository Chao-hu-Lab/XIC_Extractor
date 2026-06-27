"""App-wide guard against accidental wheel-scroll value changes.

Qt spin boxes, combo boxes and sliders consume wheel events and change their
value whenever the cursor is over them. In a long scrolling form that means
scrolling the page silently edits whatever parameter the cursor happens to pass
over, especially after the field has focus from a previous click. This filter
scrolls the enclosing scroll area instead; users can still edit with typing,
arrow keys, combo popups, and explicit +/- controls.

The wheel is delivered to the deepest widget under the cursor — for a spin box
that is its internal QLineEdit, not the spin box itself — so we look for a
guarded input at or *above* the event target.
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QComboBox,
    QWidget,
)

_GUARDED = (QAbstractSpinBox, QComboBox, QAbstractSlider)


class WheelGuard(QObject):
    """Install on the QApplication to stop hover-scroll from editing values."""

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:
        if event is None or event.type() != QEvent.Type.Wheel:
            return False
        guarded = self._guarded_input(obj)
        if guarded is None:
            return False
        # Scroll the nearest scroll area directly (re-dispatching the in-flight
        # event crashes Qt) and swallow it so the value never moves.
        if isinstance(event, QWheelEvent):
            self._scroll_page(guarded, event)
        return True

    @staticmethod
    def _guarded_input(obj: QObject | None) -> QWidget | None:
        """The guarded input at or above the event target, or None.

        Stops at a scroll area: past that we are on the page/table itself, not on
        an input, so the wheel should scroll normally.
        """
        widget = obj
        while isinstance(widget, QWidget):
            if isinstance(widget, _GUARDED):
                return widget
            if isinstance(widget, QAbstractScrollArea):
                return None
            widget = widget.parentWidget()
        return None

    @staticmethod
    def _scroll_page(widget: QWidget, event: QWheelEvent) -> None:
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea):
                bar = parent.verticalScrollBar()
                if bar is not None:
                    bar.setValue(bar.value() - event.angleDelta().y())
                return
            parent = parent.parentWidget()
