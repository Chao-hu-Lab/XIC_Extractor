from gui.styles import APPLICATION_FONT_FAMILY, APPLICATION_FONT_POINT_SIZE, STYLESHEET


def test_stylesheet_uses_single_windows_ui_font_stack() -> None:
    expected_font_stack = (
        'font-family: "Segoe UI Variable", "Segoe UI", '
        '"Microsoft JhengHei UI", sans-serif;'
    )
    assert expected_font_stack in STYLESHEET


def test_application_font_contract_matches_stylesheet_primary_font() -> None:
    assert APPLICATION_FONT_FAMILY == "Segoe UI Variable"
    assert APPLICATION_FONT_POINT_SIZE == 10
    assert APPLICATION_FONT_FAMILY in STYLESHEET
