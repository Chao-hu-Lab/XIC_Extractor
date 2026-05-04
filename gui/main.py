import multiprocessing
import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import APPLICATION_FONT_FAMILY, APPLICATION_FONT_POINT_SIZE


def configure_application(app) -> None:
    app.setApplicationName("XIC Extractor")
    app.setFont(QFont(APPLICATION_FONT_FAMILY, APPLICATION_FONT_POINT_SIZE))


def main() -> None:
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    configure_application(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
