from PyQt6.QtWidgets import QScrollArea


def test_main_window_uses_resizable_page_scroll_area(monkeypatch, qtbot) -> None:
    import gui.main_window as module

    monkeypatch.setattr(module, "read_settings", lambda: {})
    monkeypatch.setattr(module, "read_targets", lambda: [])
    window = module.MainWindow()
    qtbot.addWidget(window)

    scroll = window.centralWidget()

    assert isinstance(scroll, QScrollArea)
    assert scroll.widgetResizable()
