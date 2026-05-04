from gui.main import configure_application
from gui.styles import APPLICATION_FONT_FAMILY, APPLICATION_FONT_POINT_SIZE


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
