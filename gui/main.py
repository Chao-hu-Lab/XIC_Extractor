import multiprocessing
import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> None:
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("XIC Extractor")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
