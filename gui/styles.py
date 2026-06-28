LIGHT_PALETTE: dict[str, str] = {
    "primary": "#4f46e5",
    "primary_hover": "#4338ca",
    "primary_soft": "#eef0fd",
    "brand": "#2d1b69",
    "success": "#1a7f37",
    "success_hover": "#15803d",
    "warning": "#9a6700",
    "error": "#cf222e",
    "border": "#e2e5ea",
    "border_strong": "#cfd4dc",
    "bg_app": "#f4f5f7",
    "bg_card": "#ffffff",
    "bg_header": "#f7f8fa",
    "header_bg": "#f7f8fa",
    "header_border": "#e2e5ea",
    "bg_row_alt": "#f7f8fa",
    "bg_subtle": "#fbfbfd",
    "selection": "#e7e9fc",
    "text": "#1c2128",
    "text_muted": "#59626d",
    "icon": "#5b6470",
    "danger_soft": "#fff1ef",
    "danger_border": "#f3b7b0",
    "warn_banner": "#ff7043",
}

DARK_PALETTE: dict[str, str] = {
    "primary": "#8b85f5",
    "primary_hover": "#a7a2f8",
    "primary_soft": "#2b2a45",
    "brand": "#2d1b69",
    "success": "#46b96e",
    "success_hover": "#54c97c",
    "warning": "#d9a441",
    "error": "#f1707a",
    "border": "#363c46",
    "border_strong": "#454c58",
    "bg_app": "#181b21",
    "bg_card": "#222730",
    "bg_header": "#272d36",
    "header_bg": "#222730",
    "header_border": "#2c323b",
    "bg_row_alt": "#262b34",
    "bg_subtle": "#1e222a",
    "selection": "#33324d",
    "text": "#e6e9ee",
    "text_muted": "#aab2bf",
    "icon": "#b6bdc8",
    "danger_soft": "#3a2528",
    "danger_border": "#7a3f44",
    "warn_banner": "#d9663c",
}

APPLICATION_FONT_FAMILY = "Segoe UI Variable"
APPLICATION_FONT_POINT_SIZE = 10
UI_FONT_STACK = (
    '"Segoe UI Variable", "Segoe UI", "Microsoft JhengHei UI", sans-serif'
)

def build_stylesheet(c: dict[str, str]) -> str:
    return f"""
QWidget {{
    color: {c["text"]};
    font-family: {UI_FONT_STACK};
    font-size: 10pt;
}}

/* Scope the app background to the real top-level containers only. A universal
   QWidget {{ background-color }} rule paints the app colour onto every nested
   widget (including a card's header label row and uncovered areas), making the
   section header read as a detached band of app background. Scoping it here lets
   a card's children fall back to transparent so they show the CARD colour, while
   the gaps between cards still show the app background. */
QMainWindow,
QWidget#app_root,
QScrollArea#content_scroll,
QWidget#scroll_content {{
    background-color: {c["bg_app"]};
}}

/* Tab shell */
QTabWidget::pane {{
    border: none;
    background-color: {c["bg_app"]};
    top: -1px;
}}

QTabBar {{
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: {c["text_muted"]};
    font-size: 10.5pt;
    font-weight: 600;
    margin-right: 4px;
    padding: 9px 18px;
}}

QTabBar::tab:hover {{
    color: {c["text"]};
    background-color: {c["primary_soft"]};
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    color: {c["primary"]};
    border-bottom: 2px solid {c["primary"]};
}}

/* App shell: sidebar + branded header */
QWidget#app_root {{
    background-color: {c["bg_app"]};
}}

QFrame#sidebar {{
    background-color: {c["bg_card"]};
    border: none;
    border-right: 1px solid {c["border"]};
}}

QLabel#brand_title {{
    color: {c["text"]};
    font-size: 13pt;
    font-weight: 800;
    background: transparent;
}}

QLabel#brand_sub {{
    color: #97a0ad;
    font-size: 8.5pt;
    font-weight: 600;
    background: transparent;
}}

QPushButton#nav_item {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {c["text_muted"]};
    font-size: 10.5pt;
    font-weight: 600;
    padding: 11px 12px;
    text-align: left;
}}

QPushButton#nav_item:hover {{
    background-color: {c["bg_app"]};
    color: {c["text"]};
}}

QPushButton#nav_item:checked {{
    background-color: {c["primary_soft"]};
    color: {c["primary_hover"]};
    font-weight: 700;
}}

QFrame#app_header {{
    border: none;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {c["brand"]},
        stop: 1 {c["primary"]}
    );
}}

QLabel#header_title {{
    color: #ffffff;
    font-size: 16.5pt;
    font-weight: 800;
    background: transparent;
}}

QLabel#header_subtitle {{
    color: rgba(255, 255, 255, 0.80);
    font-size: 9.5pt;
    font-weight: 500;
    background: transparent;
}}

/* Menu bar */
QMenuBar {{
    background-color: {c["bg_card"]};
    border-bottom: 1px solid {c["border"]};
    padding: 2px 6px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 6px 11px;
    border-radius: 6px;
}}

QMenuBar::item:selected {{
    background-color: {c["primary_soft"]};
    color: {c["primary_hover"]};
}}

QMenu {{
    background-color: {c["bg_card"]};
    border: 1px solid {c["border_strong"]};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 7px 24px 7px 16px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: {c["primary_soft"]};
    color: {c["primary_hover"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {c["border"]};
    margin: 4px 8px;
}}

/* Section cards */
QFrame#section_card {{
    background-color: {c["bg_card"]};
    border: 1px solid {c["border"]};
    border-radius: 10px;
}}

QFrame#section_header {{
    background-color: {c["header_bg"]};
    border: none;
    border-bottom: 1px solid {c["header_border"]};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}

QLabel#section_title {{
    color: {c["text"]};
    font-size: 12.5pt;
    font-weight: 700;
}}

QLabel#section_subtitle {{
    color: {c["text_muted"]};
    font-size: 9pt;
}}

QLabel#field_label {{
    color: {c["text_muted"]};
    font-weight: 600;
}}

QLabel#hint {{
    color: {c["text_muted"]};
    font-size: 9pt;
}}

QLabel#field_error {{
    color: {c["error"]};
    font-size: 9pt;
}}

QLabel#results_error {{
    color: {c["error"]};
    font-weight: 600;
}}

QLabel#istd_warning {{
    background-color: {c["warn_banner"]};
    border-radius: 4px;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 12px;
}}

/* Buttons */
QPushButton {{
    background-color: {c["bg_card"]};
    border: 1px solid {c["border_strong"]};
    border-radius: 7px;
    color: {c["text"]};
    font-weight: 600;
    padding: 8px 14px;
}}

QPushButton:hover {{
    border-color: {c["primary"]};
    background-color: {c["primary_soft"]};
}}

QPushButton:pressed {{
    background-color: {c["selection"]};
}}

QPushButton:checked {{
    border-color: {c["primary"]};
    background-color: {c["primary_soft"]};
    color: {c["primary_hover"]};
}}

QPushButton:disabled {{
    color: {c["text_muted"]};
    background-color: {c["bg_header"]};
    border-color: {c["border"]};
}}

QPushButton#btn_run {{
    background-color: {c["success"]};
    border-color: {c["success"]};
    color: white;
    font-size: 10.5pt;
    font-weight: 700;
    padding: 11px 16px;
}}

QPushButton#btn_run:hover {{
    background-color: {c["success_hover"]};
    border-color: {c["success_hover"]};
}}

QPushButton#btn_run:disabled {{
    background-color: {c["bg_header"]};
    border-color: {c["border"]};
    color: {c["text_muted"]};
}}

QPushButton#btn_stop {{
    background-color: {c["error"]};
    border-color: {c["error"]};
    color: white;
    font-size: 10.5pt;
    font-weight: 700;
    padding: 11px 16px;
}}

QPushButton#btn_stop:hover {{
    background-color: #b91c2b;
    border-color: #b91c2b;
}}

QPushButton#btn_save,
QPushButton#btn_add {{
    background-color: {c["primary"]};
    border-color: {c["primary"]};
    color: white;
    font-weight: 700;
}}

QPushButton#btn_save:hover,
QPushButton#btn_add:hover {{
    background-color: {c["primary_hover"]};
    border-color: {c["primary_hover"]};
}}

QPushButton#btn_delete {{
    background-color: {c["danger_soft"]};
    border-color: {c["danger_border"]};
    color: {c["error"]};
    font-weight: 700;
}}

QPushButton#btn_delete:hover {{
    background-color: {c["danger_border"]};
    border-color: {c["error"]};
}}

/* Collapsible section toggles (QToolButton) — flat, not a grey native button */
QToolButton {{
    background: transparent;
    border: none;
    color: {c["text_muted"]};
    font-weight: 600;
    padding: 6px 2px;
    text-align: left;
}}

QToolButton:hover {{
    color: {c["primary"]};
}}

QToolButton:checked {{
    color: {c["text"]};
}}

/* Tables */
QTableWidget {{
    background-color: {c["bg_card"]};
    alternate-background-color: {c["bg_row_alt"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    gridline-color: {c["border"]};
    selection-background-color: {c["selection"]};
    selection-color: {c["text"]};
}}

QHeaderView::section {{
    background-color: {c["bg_header"]};
    border: none;
    border-bottom: 1px solid {c["border_strong"]};
    border-right: 1px solid {c["border"]};
    color: {c["text_muted"]};
    font-weight: 700;
    padding: 9px;
}}

QTableCornerButton::section {{
    background-color: {c["bg_header"]};
    border: none;
}}

/* Progress */
QProgressBar {{
    background-color: {c["bg_header"]};
    border: 1px solid {c["border"]};
    border-radius: 7px;
    color: {c["text"]};
    font-weight: 600;
    min-height: 18px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {c["primary"]},
        stop: 1 #6366f1
    );
    border-radius: 6px;
}}

/* Status bar */
QStatusBar {{
    background-color: {c["bg_card"]};
    border-top: 1px solid {c["border"]};
    color: {c["text_muted"]};
}}

QStatusBar::item {{
    border: none;
}}

QLabel#status_state {{
    color: {c["text_muted"]};
    font-weight: 700;
    padding: 0 10px;
}}

QLabel#elapsed_label {{
    color: {c["text_muted"]};
    font-size: 9pt;
}}

QFrame#dist_track {{
    background-color: {c["bg_subtle"]};
    border-radius: 8px;
}}

/* Inputs */
QLineEdit,
QSpinBox,
QDoubleSpinBox,
QComboBox {{
    background-color: {c["bg_card"]};
    border: 1px solid {c["border_strong"]};
    border-radius: 7px;
    color: {c["text"]};
    padding: 7px 9px;
    selection-background-color: {c["selection"]};
    selection-color: {c["text"]};
}}

QLineEdit:hover,
QSpinBox:hover,
QDoubleSpinBox:hover,
QComboBox:hover {{
    border-color: {c["primary"]};
}}

QLineEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus {{
    border: 2px solid {c["primary"]};
    padding: 6px 8px;
}}

QLineEdit[invalid="true"] {{
    border-color: {c["error"]};
    background-color: {c["danger_soft"]};
}}

QLabel#ready_hint_ok {{
    color: {c["success"]};
    font-weight: 700;
}}

QLabel#ready_hint_block {{
    color: {c["warning"]};
    font-weight: 700;
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QComboBox QAbstractItemView {{
    background-color: {c["bg_card"]};
    border: 1px solid {c["border_strong"]};
    border-radius: 6px;
    selection-background-color: {c["primary_soft"]};
    selection-color: {c["text"]};
    outline: none;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {c["border_strong"]};
    border-radius: 6px;
    min-height: 28px;
}}

QScrollBar::handle:vertical:hover {{
    background: #b3bac4;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QToolTip {{
    background-color: {c["brand"]};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 9px;
}}
"""


COLORS = LIGHT_PALETTE
STYLESHEET = build_stylesheet(LIGHT_PALETTE)

# The palette currently applied to the app. RichText/HTML content (which the
# stylesheet cannot reach) reads colours from here and is re-rendered on theme
# change via each view's refresh_theme().
ACTIVE: dict[str, str] = dict(LIGHT_PALETTE)


def set_active(palette: dict[str, str]) -> None:
    ACTIVE.clear()
    ACTIVE.update(palette)
