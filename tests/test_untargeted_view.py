from __future__ import annotations

from gui.sections.discovery_method_section import POSITIVE_DISCOVERY_OVERRIDE_FIELDS
from xic_extractor.presets import apply_to_discovery, load_preset


class _SlowStoppingWorker:
    def __init__(self) -> None:
        self.stop_called = False

    def stop(self) -> None:
        self.stop_called = True

    def wait(self, _timeout_ms: int) -> bool:
        return False


def test_untargeted_stop_waits_for_cancelled_signal_before_restoring_controls(
    monkeypatch,
    qtbot,
) -> None:
    import gui.views.untargeted_view as module

    monkeypatch.setattr(module, "confirm_stop", lambda _parent: True)
    view = module.UntargetedView()
    qtbot.addWidget(view)
    status_messages: list[str] = []
    view.status_message.connect(lambda text, _timeout: status_messages.append(text))

    worker = _SlowStoppingWorker()
    view._worker = worker
    view._source.set_enabled(False)
    view._method.set_enabled(False)
    view._run.set_running(True)

    view._on_stop()

    assert worker.stop_called is True
    assert view.is_busy()
    assert view._source.isEnabled() is False
    assert view._method.isEnabled() is False
    assert status_messages[-1] == "正在停止，等待目前階段結束..."

    view._on_cancelled(worker)

    assert view.is_busy() is False
    assert view._source.isEnabled() is True
    assert view._method.isEnabled() is True
    assert view._run._button.text() == "開始執行"
    assert status_messages[-1] == "已停止執行"


def test_untargeted_view_clamps_persisted_zero_overrides_before_run(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    import gui.views.untargeted_view as module

    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    output_dir = tmp_path / "output"
    for path in (raw_dir, dll_dir, output_dir):
        path.mkdir()
    persisted_config = {
        "mode": "full",
        "preset": "dna_dr",
        "raw_dir": str(raw_dir),
        "raw_file": "",
        "discovery_batch_index": "",
        "dll_dir": str(dll_dir),
        "output_dir": str(output_dir),
        "overrides": {field: 0.0 for field in POSITIVE_DISCOVERY_OVERRIDE_FIELDS},
    }
    monkeypatch.setattr(module, "read_discovery_config", lambda: persisted_config)

    view = module.UntargetedView()
    qtbot.addWidget(view)
    request = view._build_request(view._current_config())

    assert view._run._button.isEnabled() is True
    assert set(request.tuning_overrides) == POSITIVE_DISCOVERY_OVERRIDE_FIELDS
    assert all(
        float(request.tuning_overrides[field]) > 0
        for field in POSITIVE_DISCOVERY_OVERRIDE_FIELDS
    )
    apply_to_discovery(
        load_preset(request.preset),
        explicit_tuning_overrides=request.tuning_overrides,
    )
