from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QScrollArea, QStatusBar, QVBoxLayout, QWidget

from gui.config_io import read_settings, read_targets, write_settings, write_targets
from gui.sections.results_section import ResultsSection
from gui.sections.run_section import RunSection
from gui.sections.settings_section import SettingsSection
from gui.sections.targets_section import TargetsSection
from gui.styles import STYLESHEET
from gui.workers.pipeline_worker import PipelineWorker

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _ROOT / "scripts"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._worker: PipelineWorker | None = None

        self.setWindowTitle("XIC Extractor")
        self.resize(1100, 860)
        self.setStyleSheet(STYLESHEET)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setCentralWidget(scroll)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)
        scroll.setWidget(container)

        self._settings = SettingsSection()
        self._targets = TargetsSection()
        self._run = RunSection()
        self._results = ResultsSection()

        container_layout.addWidget(self._settings)
        container_layout.addWidget(self._targets)
        container_layout.addWidget(self._run)
        container_layout.addWidget(self._results)
        container_layout.addStretch()

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._settings.settings_saved.connect(self._save_settings)
        self._settings.settings_saved.connect(lambda: self._status_bar.showMessage("設定已儲存", 3000))
        self._targets.targets_saved.connect(self._save_targets)
        self._targets.targets_saved.connect(
            lambda: self._status_bar.showMessage(f"目標已儲存，共 {self._targets._table.rowCount()} 筆", 3000)
        )
        self._run.run_clicked.connect(self._on_run)
        self._run.stop_clicked.connect(self._on_stop)

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

        self._settings.load(settings)
        self._targets.load(targets)
        self._status_bar.showMessage(f"已載入 {len(targets)} 個目標")

    def _save_settings(self) -> None:
        write_settings(self._settings.get_values())

    def _save_targets(self) -> None:
        write_targets(self._targets.get_targets())

    def _on_run(self) -> None:
        self._save_settings()
        self._save_targets()
        self._settings.set_enabled(False)
        self._targets.set_enabled(False)
        self._run.set_running(True)
        self._run.set_error("執行中...")
        self._status_bar.showMessage("開始執行 pipeline...")

        self._worker = PipelineWorker(_SCRIPTS_DIR)
        self._worker.progress.connect(self._run.set_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(1000)
            self._worker = None
        self._run.set_running(False)
        self._settings.set_enabled(True)
        self._targets.set_enabled(True)
        self._status_bar.showMessage("已停止執行", 3000)

    def _on_finished(self, summary: dict) -> None:
        self._run.set_complete(summary["total_files"])
        self._run.set_running(False)
        self._settings.set_enabled(True)
        self._targets.set_enabled(True)
        self._results.update_results(summary)
        self._status_bar.showMessage("Pipeline 執行完成", 5000)
        self._worker = None

    def _on_error(self, message: str) -> None:
        self._run.set_running(False)
        self._run.set_error(message)
        self._settings.set_enabled(True)
        self._targets.set_enabled(True)
        self._results.show_error(message)
        self._status_bar.showMessage(f"執行失敗: {message}", 5000)
        self._worker = None
