import multiprocessing
import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import APPLICATION_FONT_FAMILY, APPLICATION_FONT_POINT_SIZE
from gui.wheel_guard import WheelGuard


def configure_application(app) -> None:
    app.setApplicationName("XIC Extractor")
    font = QFont(APPLICATION_FONT_FAMILY, APPLICATION_FONT_POINT_SIZE)
    _enable_tabular_figures(font)
    app.setFont(font)


def _enable_tabular_figures(font: QFont) -> None:
    # Tabular (fixed-width) figures so numeric columns — the targets table, the
    # resolver spin grid, the result tiles — align digit-to-digit instead of
    # jittering on a narrow '1' vs a wide '8'. Qt QSS cannot express this, so it
    # is set as an OpenType feature on the application font (inherited by every
    # widget that does not replace its font outright).
    if not hasattr(font, "setFeature") or not hasattr(QFont, "Tag"):
        return
    font.setFeature(QFont.Tag("tnum"), 1)


def install_wheel_guard(app: QApplication) -> WheelGuard:
    guard = getattr(app, "_xic_wheel_guard", None)
    if isinstance(guard, WheelGuard):
        return guard
    guard = WheelGuard(app)
    setattr(app, "_xic_wheel_guard", guard)
    app.installEventFilter(guard)
    return guard


def main() -> None:
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    configure_application(app)
    install_wheel_guard(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
