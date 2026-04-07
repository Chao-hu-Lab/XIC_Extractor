import io
import re
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class PipelineWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, scripts_dir: Path) -> None:
        super().__init__()
        self._scripts_dir = scripts_dir
        self._process: subprocess.Popen[str] | None = None
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()

    def run(self) -> None:
        try:
            total_files = self._run_ps1()
            if self._stop_requested:
                return
            stdout = self._run_python()
            if self._stop_requested:
                return
            self.finished.emit(self._parse_summary(stdout, total_files))
        except Exception as exc:
            if not self._stop_requested:
                self.error.emit(str(exc))
        finally:
            self._process = None

    def _run_ps1(self) -> int:
        if getattr(sys, "frozen", False):
            root_dir = Path(sys.executable).parent
        else:
            root_dir = self._scripts_dir.parent

        command = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self._scripts_dir / "01_extract_xic.ps1"),
            "-RootDir",
            str(root_dir),
        ]
        total_files = 0
        self._process = subprocess.Popen(
            command,
            cwd=str(root_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )

        assert self._process.stdout is not None
        for raw_line in self._process.stdout:
            line = raw_line.rstrip()
            if match := re.search(r"Files\s+:\s+(\d+)", line):
                total_files = int(match.group(1))
                continue
            if match := re.search(r"\s+\[\s*(\d+)/\s*(\d+)\]\s+(.+)", line):
                current = int(match.group(1))
                total = int(match.group(2))
                filename = match.group(3).strip()
                total_files = total
                self.progress.emit(current, total, filename)

        return_code = self._process.wait()
        if self._stop_requested:
            return total_files
        if return_code != 0:
            raise RuntimeError("01_extract_xic.ps1 failed.")
        return total_files

    def _run_python(self) -> str:
        from scripts.csv_to_excel import run as _csv_to_excel_run

        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = self._scripts_dir.parent

        buf = io.StringIO()
        with redirect_stdout(buf):
            _csv_to_excel_run(base_dir)
        return buf.getvalue()

    def _parse_summary(self, stdout: str, total_files: int) -> dict:
        excel_path = ""
        nl_warn_count = 0
        targets: list[dict[str, int | str | bool]] = []
        seen_labels: set[str] = set()
        istd_warnings: list[dict[str, int | str]] = []

        for line in stdout.splitlines():
            if match := re.search(r"Saved\s+:\s+(.+)", line):
                excel_path = match.group(1).strip()
                continue

            confirmed = re.search(
                r"\s+(\S+)_RT detected \(NL confirmed\): (\d+)/(\d+)",
                line,
            )
            if confirmed:
                label = confirmed.group(1)
                targets.append(
                    {
                        "label": label,
                        "detected": int(confirmed.group(2)),
                        "total": int(confirmed.group(3)),
                        "nl_confirmed": True,
                    }
                )
                seen_labels.add(label)
                continue

            basic = re.search(r"\s+(\S+)_RT detected: (\d+)/(\d+)", line)
            if basic and basic.group(1) not in seen_labels:
                targets.append(
                    {
                        "label": basic.group(1),
                        "detected": int(basic.group(2)),
                        "total": int(basic.group(3)),
                        "nl_confirmed": False,
                    }
                )
                seen_labels.add(basic.group(1))
                continue

            if warn_match := re.search(r"\s+\S+\s+OK:\d+\s+WARN:(\d+)\s+ND:\d+", line):
                nl_warn_count += int(warn_match.group(1))

            if istd_nd := re.search(r"^ISTD_ND:\s+(\S+)\s+(\d+)/(\d+)", line):
                istd_warnings.append(
                    {
                        "label": istd_nd.group(1),
                        "detected": int(istd_nd.group(2)),
                        "total": int(istd_nd.group(3)),
                    }
                )

        return {
            "total_files": total_files,
            "targets": targets,
            "nl_warn_count": nl_warn_count,
            "excel_path": excel_path,
            "istd_warnings": istd_warnings,
        }
