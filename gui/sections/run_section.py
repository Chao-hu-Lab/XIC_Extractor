from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.ui import section_card


class RunSection(QWidget):
    run_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._ready = True
        self._elapsed_seconds = 0

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card, body = section_card("③ Run", "執行並顯示進度")
        root_layout.addWidget(card)

        self._ready_hint = QLabel("")
        self._ready_hint.setObjectName("ready_hint_ok")
        self._ready_hint.setWordWrap(True)
        body.addWidget(self._ready_hint)

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
        self._elapsed_label.setObjectName("elapsed_label")
        self._elapsed_label.setVisible(False)
        status_row.addWidget(self._status_label, 1)
        status_row.addWidget(self._elapsed_label)
        body.addLayout(status_row)

        # Elapsed timer (fires every second in the main thread — safe for Qt)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_ready(self, ready: bool, missing: list[str]) -> None:
        """Reflect whether the current config can run, and what is missing."""
        self._ready = ready
        if ready:
            self._ready_hint.setObjectName("ready_hint_ok")
            self._ready_hint.setText("✓ 設定完整，可以執行")
        else:
            self._ready_hint.setObjectName("ready_hint_block")
            self._ready_hint.setText("尚缺：" + "、".join(missing))
        self._repolish(self._ready_hint)
        if not self._running:
            self._button.setEnabled(ready)

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
            self._ready_hint.setVisible(False)
            self._button.setEnabled(True)
        else:
            self._timer.stop()
            self._ready_hint.setVisible(True)
            self._button.setEnabled(self._ready)

        self._button.setText("停止執行" if running else "開始執行")
        self._button.setObjectName("btn_stop" if running else "btn_run")
        self._repolish(self._button)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()

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
