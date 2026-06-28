from PyQt6.QtWidgets import QScrollArea


class _CloseEvent:
    def __init__(self) -> None:
        self.accepted = False
        self.ignored = False

    def accept(self) -> None:
        self.accepted = True

    def ignore(self) -> None:
        self.ignored = True


def test_main_window_wraps_each_view_in_resizable_scroll_area(
    monkeypatch, qtbot
) -> None:
    # After the workspace refactor the central widget is the sidebar+stack shell;
    # each view is wrapped in its own resizable scroll area inside the stack.
    import gui.views.targeted_view as targeted_module

    monkeypatch.setattr(targeted_module, "read_settings", lambda: {})
    monkeypatch.setattr(targeted_module, "read_targets", lambda: [])

    import gui.main_window as module

    window = module.MainWindow()
    qtbot.addWidget(window)

    stack = window._stack
    assert stack.count() == len(module._VIEWS)
    for index in range(stack.count()):
        page = stack.widget(index)
        assert isinstance(page, QScrollArea)
        assert page.widgetResizable()


def test_close_event_requests_stop_for_busy_view_before_accepting(
    monkeypatch, qtbot
) -> None:
    import gui.main_window as module
    import gui.views.targeted_view as targeted_module

    monkeypatch.setattr(targeted_module, "read_settings", lambda: {})
    monkeypatch.setattr(targeted_module, "read_targets", lambda: [])
    monkeypatch.setattr(module, "confirm_close_while_busy", lambda _parent: True)

    window = module.MainWindow()
    qtbot.addWidget(window)
    busy = {"value": True}
    stop_confirms: list[bool] = []

    def stop_targeted(*, confirm=True):
        stop_confirms.append(confirm)
        busy["value"] = False

    window.targeted_view.is_busy = lambda: busy["value"]  # type: ignore[method-assign]
    window.targeted_view.trigger_stop = stop_targeted  # type: ignore[method-assign]
    window.untargeted_view.is_busy = lambda: False  # type: ignore[method-assign]
    window.untargeted_view.persist_config = lambda: None  # type: ignore[method-assign]
    window._save_window_state = lambda: None  # type: ignore[method-assign]

    event = _CloseEvent()
    window.closeEvent(event)

    assert stop_confirms == [False]
    assert event.accepted is True
    assert event.ignored is False


def test_close_event_waits_when_busy_view_has_not_stopped(
    monkeypatch, qtbot
) -> None:
    import gui.main_window as module
    import gui.views.targeted_view as targeted_module

    monkeypatch.setattr(targeted_module, "read_settings", lambda: {})
    monkeypatch.setattr(targeted_module, "read_targets", lambda: [])
    monkeypatch.setattr(module, "confirm_close_while_busy", lambda _parent: True)

    window = module.MainWindow()
    qtbot.addWidget(window)
    stop_confirms: list[bool] = []
    window.targeted_view.is_busy = lambda: True  # type: ignore[method-assign]
    window.targeted_view.trigger_stop = (  # type: ignore[method-assign]
        lambda *, confirm=True: stop_confirms.append(confirm)
    )
    window.untargeted_view.is_busy = lambda: False  # type: ignore[method-assign]

    event = _CloseEvent()
    window.closeEvent(event)

    assert stop_confirms == [False]
    assert event.accepted is False
    assert event.ignored is True
    assert "正在停止工作" in window.statusBar().currentMessage()
