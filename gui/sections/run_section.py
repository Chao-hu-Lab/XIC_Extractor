from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class RunSection(QWidget):
    run_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._running = False

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
        title = QLabel("③ Run")
        title.setObjectName("section_title")
        header_layout.addWidget(title)
        card_layout.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(12)

        self._button = QPushButton("開始執行")
        self._button.setObjectName("btn_run")
        self._button.clicked.connect(self._on_button_clicked)
        body.addWidget(self._button)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        body.addWidget(self._progress)

        self._status_label = QLabel("尚未開始")
        body.addWidget(self._status_label)

        card_layout.addLayout(body)

    def set_progress(self, current: int, total: int, filename: str) -> None:
        progress_max = max(total, 1)
        self._progress.setRange(0, progress_max)
        self._progress.setValue(current)
        self._status_label.setText(f"處理中 {current}/{total}: {filename}")

    def set_running(self, running: bool) -> None:
        self._running = running
        self._button.setText("停止執行" if running else "開始執行")
        self._button.setObjectName("btn_stop" if running else "btn_run")
        self._button.style().unpolish(self._button)
        self._button.style().polish(self._button)
        self._button.update()

    def set_complete(self, total: int) -> None:
        progress_max = max(total, 1)
        self._progress.setRange(0, progress_max)
        self._progress.setValue(total)
        self._status_label.setText(f"完成，共 {total} 個檔案")

    def set_error(self, message: str) -> None:
        self._status_label.setText(f"錯誤: {message}")

    def _on_button_clicked(self) -> None:
        if self._running:
            self.stop_clicked.emit()
            return
        self.run_clicked.emit()
