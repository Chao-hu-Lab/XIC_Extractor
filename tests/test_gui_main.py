import gui.main as module
from gui.main import configure_application, install_wheel_guard
from gui.styles import APPLICATION_FONT_FAMILY, APPLICATION_FONT_POINT_SIZE
from gui.wheel_guard import WheelGuard


class _FakeApplication:
    def __init__(self) -> None:
        self.application_name: str | None = None
        self.font = None

    def setApplicationName(self, name: str) -> None:
        self.application_name = name

    def setFont(self, font) -> None:
        self.font = font


def test_configure_application_sets_app_name_and_font() -> None:
    app = _FakeApplication()

    configure_application(app)

    assert app.application_name == "XIC Extractor"
    assert app.font.family() == APPLICATION_FONT_FAMILY
    assert app.font.pointSize() == APPLICATION_FONT_POINT_SIZE


def test_configure_application_allows_qt_without_font_feature_api(monkeypatch) -> None:
    class LegacyFont:
        def __init__(self, family: str, point_size: int) -> None:
            self._family = family
            self._point_size = point_size

        def family(self) -> str:
            return self._family

        def pointSize(self) -> int:
            return self._point_size

    monkeypatch.setattr(module, "QFont", LegacyFont)
    app = _FakeApplication()

    configure_application(app)

    assert app.font.family() == APPLICATION_FONT_FAMILY
    assert app.font.pointSize() == APPLICATION_FONT_POINT_SIZE


def test_configure_application_enables_tabular_figures_when_supported(
    monkeypatch,
) -> None:
    class FeatureFont:
        class Tag:
            def __init__(self, name: str) -> None:
                self.name = name

        def __init__(self, family: str, point_size: int) -> None:
            self._family = family
            self._point_size = point_size
            self.features: list[tuple[str, int]] = []

        def family(self) -> str:
            return self._family

        def pointSize(self) -> int:
            return self._point_size

        def setFeature(self, tag: Tag, value: int) -> None:
            self.features.append((tag.name, value))

    monkeypatch.setattr(module, "QFont", FeatureFont)
    app = _FakeApplication()

    configure_application(app)

    assert app.font.family() == APPLICATION_FONT_FAMILY
    assert app.font.pointSize() == APPLICATION_FONT_POINT_SIZE
    assert app.font.features == [("tnum", 1)]


def test_install_wheel_guard_keeps_single_application_reference(qapp) -> None:
    previous = getattr(qapp, "_xic_wheel_guard", None)
    if previous is not None:
        qapp.removeEventFilter(previous)
        delattr(qapp, "_xic_wheel_guard")

    guard = install_wheel_guard(qapp)
    second = install_wheel_guard(qapp)

    try:
        assert isinstance(guard, WheelGuard)
        assert second is guard
        assert qapp._xic_wheel_guard is guard
    finally:
        qapp.removeEventFilter(guard)
        delattr(qapp, "_xic_wheel_guard")
