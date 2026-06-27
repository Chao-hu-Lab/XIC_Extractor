from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from gui.config_io import read_settings, read_targets, write_settings, write_targets
from gui.dialogs import confirm_stop
from gui.sections.results_section import ResultsSection
from gui.sections.run_section import RunSection
from gui.sections.settings_section import SettingsSection
from gui.sections.targets_section import TargetsSection
from gui.workers.pipeline_worker import PipelineWorker


class TargetedView(QWidget):
    status_message = pyqtSignal(str, int)
    state_changed = pyqtSignal(str)

    def __init__(self, config_dir: Path) -> None:
        super().__init__()
        self._config_dir = config_dir
        self._worker: PipelineWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._settings = SettingsSection()
        self._targets = TargetsSection()
        self._run = RunSection()
        self._results = ResultsSection()

        layout.addWidget(self._settings)
        layout.addWidget(self._targets)
        layout.addWidget(self._run)
        layout.addWidget(self._results)
        layout.addStretch()

        self._settings.settings_saved.connect(self._save_settings)
        self._settings.settings_saved.connect(
            lambda: self.status_message.emit("設定已儲存", 3000)
        )
        self._targets.targets_saved.connect(self._save_targets)
        self._targets.targets_saved.connect(
            lambda: self.status_message.emit(
                f"目標已儲存，共 {self._targets._table.rowCount()} 筆", 3000
            )
        )
        self._run.run_clicked.connect(self._on_run)
        self._run.stop_clicked.connect(self._on_stop)

    def load_config(self) -> None:
        self._load_config()

    def _load_config(self) -> None:
        settings: dict[str, str] = {}
        targets: list[dict[str, str]] = []
        try:
            settings = read_settings()
        except FileNotFoundError:
            settings = {}

        try:
            targets = read_targets()
        except FileNotFoundError:
            targets = []

        migrated = self._settings.load(settings)
        if migrated and self._settings.is_valid():
            write_settings(self._settings.get_values())
        self._targets.load(targets)
        self.status_message.emit(f"已載入 {len(targets)} 個目標", 0)

    def _save_settings(self) -> None:
        write_settings(self._settings.get_values())

    def _save_targets(self) -> None:
        write_targets(self._targets.get_targets())

    def _on_run(self) -> None:
        if not self._settings.is_valid():
            self.status_message.emit("設定值無效，請修正後再執行", 5000)
            return
        self._save_settings()
        self._save_targets()
        self._settings.set_enabled(False)
        self._targets.set_enabled(False)
        self._run.set_running(True)
        self.status_message.emit("開始執行 pipeline...", 0)
        self.state_changed.emit("執行中…")

        self._worker = PipelineWorker(self._config_dir)
        self._worker.progress.connect(self._run.set_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def is_busy(self) -> bool:
        return self._worker is not None

    def emit_state(self) -> None:
        self.state_changed.emit("執行中…" if self._worker is not None else "就緒")

    def refresh_theme(self) -> None:
        """Replay the results cards so their baked-in colours follow the theme."""
        self._results.refresh_theme()

    def trigger_run(self) -> None:
        if self._worker is None:
            self._on_run()

    def trigger_stop(self, *, confirm: bool = True) -> None:
        if self._worker is not None:
            self._on_stop(confirm=confirm)

    def _on_stop(self, *, confirm: bool = True) -> None:
        if self._worker is not None:
            if confirm and not confirm_stop(self):
                return
            self._worker.stop()
            if not self._worker.wait(1000):
                self.status_message.emit("正在停止，等待目前階段結束...", 5000)
                return
            self._worker = None
        self._run.set_running(False)
        self._settings.set_enabled(True)
        self._targets.set_enabled(True)
        self.status_message.emit("已停止執行", 3000)
        self.state_changed.emit("就緒")

    def _on_finished(self, summary: dict) -> None:
        self._run.set_complete(summary["total_files"])
        self._run.set_running(False)
        self._settings.set_enabled(True)
        self._targets.set_enabled(True)
        self._results.update_results(summary)
        self.status_message.emit("Pipeline 執行完成", 5000)
        self.state_changed.emit("完成")
        self._worker = None

    def _on_error(self, message: str) -> None:
        self._run.set_running(False)
        self._run.set_error(message)
        self._settings.set_enabled(True)
        self._targets.set_enabled(True)
        self._results.show_error(message)
        self.status_message.emit(f"執行失敗: {message}", 5000)
        self.state_changed.emit("執行失敗")
        self._worker = None

    def _on_cancelled(self) -> None:
        self._run.set_running(False)
        self._settings.set_enabled(True)
        self._targets.set_enabled(True)
        self.status_message.emit("已停止執行", 3000)
        self.state_changed.emit("就緒")
        self._worker = None
