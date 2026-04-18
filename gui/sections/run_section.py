from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RunSection(QWidget):
    run_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._elapsed_seconds = 0

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
        body.setSpacing(10)

        self._button = QPushButton("開始執行")
        self._button.setObjectName("btn_run")
        self._button.clicked.connect(self._on_button_clicked)
        body.addWidget(self._button)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        body.addWidget(self._progress)

        # Status + elapsed time on the same row
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        self._status_label = QLabel("尚未開始")
        self._elapsed_label = QLabel("")
        self._elapsed_label.setStyleSheet("color: #57606a; font-size: 9pt;")
        self._elapsed_label.setVisible(False)
        status_row.addWidget(self._status_label, 1)
        status_row.addWidget(self._elapsed_label)
        body.addLayout(status_row)

        card_layout.addLayout(body)

        # Elapsed timer (fires every second in the main thread — safe for Qt)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_progress(self, current: int, total: int, filename: str) -> None:
        progress_max = max(total, 1)
        self._progress.setRange(0, progress_max)
        self._progress.setValue(current)
        self._status_label.setText(f"處理中 {current}/{total}: {filename}")

    def set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._elapsed_seconds = 0
            self._elapsed_label.setText("已執行 00:00")
            self._elapsed_label.setVisible(True)
            self._timer.start()
            self._status_label.setText("準備中...")
            self._progress.setValue(0)
        else:
            self._timer.stop()

        self._button.setText("停止執行" if running else "開始執行")
        self._button.setObjectName("btn_stop" if running else "btn_run")
        self._button.style().unpolish(self._button)
        self._button.style().polish(self._button)
        self._button.update()

    def set_complete(self, total: int) -> None:
        self._timer.stop()
        self._elapsed_label.setVisible(False)
        progress_max = max(total, 1)
        self._progress.setRange(0, progress_max)
        self._progress.setValue(total)
        self._status_label.setText(f"完成，共 {total} 個檔案")

    def set_error(self, message: str) -> None:
        """Show an error state: reset progress bar and display the message."""
        self._timer.stop()
        self._elapsed_label.setVisible(False)
        self._progress.setValue(0)
        self._status_label.setText(f"錯誤: {message}")

    # ── Private ────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._elapsed_seconds += 1
        mins, secs = divmod(self._elapsed_seconds, 60)
        self._elapsed_label.setText(f"已執行 {mins:02d}:{secs:02d}")

    def _on_button_clicked(self) -> None:
        if self._running:
            self.stop_clicked.emit()
            return
        self.run_clicked.emit()
