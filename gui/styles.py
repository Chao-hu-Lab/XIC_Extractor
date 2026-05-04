COLORS: dict[str, str] = {
    "primary": "#0969da",
    "success": "#1a7f37",
    "warning": "#9a6700",
    "error": "#cf222e",
    "border": "#d0d7de",
    "bg_card": "#ffffff",
    "bg_header": "#f6f8fa",
    "bg_row_alt": "#f6f8fa",
    "selection": "#ddf4ff",
    "text": "#24292f",
    "text_muted": "#57606a",
}

APPLICATION_FONT_FAMILY = "Segoe UI Variable"
APPLICATION_FONT_POINT_SIZE = 10
UI_FONT_STACK = (
    '"Segoe UI Variable", "Segoe UI", "Microsoft JhengHei UI", sans-serif'
)

STYLESHEET = f"""
QWidget {{
    background-color: {COLORS["bg_header"]};
    color: {COLORS["text"]};
    font-family: {UI_FONT_STACK};
    font-size: 10pt;
}}

QFrame#section_card {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
}}

QFrame#section_header {{
    background-color: {COLORS["bg_header"]};
    border: none;
    border-bottom: 1px solid {COLORS["border"]};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

QLabel#section_title {{
    color: {COLORS["text"]};
    font-size: 12pt;
    font-weight: 600;
}}

QPushButton {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    color: {COLORS["text"]};
    padding: 8px 12px;
}}

QPushButton:hover {{
    border-color: {COLORS["primary"]};
}}

QPushButton:disabled {{
    color: {COLORS["text_muted"]};
    background-color: {COLORS["bg_header"]};
}}

QPushButton#btn_run {{
    background-color: {COLORS["success"]};
    border-color: {COLORS["success"]};
    color: white;
    font-weight: 600;
    padding: 10px 14px;
}}

QPushButton#btn_stop {{
    background-color: {COLORS["error"]};
    border-color: {COLORS["error"]};
    color: white;
    font-weight: 600;
    padding: 10px 14px;
}}

QPushButton#btn_save,
QPushButton#btn_add {{
    background-color: {COLORS["primary"]};
    border-color: {COLORS["primary"]};
    color: white;
    font-weight: 600;
}}

QPushButton#btn_open_excel {{
    background-color: {COLORS["success"]};
    border-color: {COLORS["success"]};
    color: white;
    font-weight: 600;
}}

QPushButton#btn_delete {{
    background-color: #ffebe9;
    border-color: #ffb3ad;
    color: {COLORS["error"]};
    font-weight: 600;
}}

QTableWidget {{
    background-color: {COLORS["bg_card"]};
    alternate-background-color: {COLORS["bg_row_alt"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    gridline-color: {COLORS["border"]};
    selection-background-color: {COLORS["selection"]};
    selection-color: {COLORS["text"]};
}}

QHeaderView::section {{
    background-color: {COLORS["bg_header"]};
    border: none;
    border-bottom: 1px solid {COLORS["border"]};
    border-right: 1px solid {COLORS["border"]};
    color: {COLORS["text_muted"]};
    font-weight: 600;
    padding: 8px;
}}

QProgressBar {{
    background-color: {COLORS["bg_header"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    color: {COLORS["text"]};
    min-height: 16px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2da44e,
        stop: 1 {COLORS["success"]}
    );
    border-radius: 5px;
}}

QStatusBar {{
    background-color: {COLORS["bg_header"]};
    border-top: 1px solid {COLORS["border"]};
    color: {COLORS["text_muted"]};
}}

QLineEdit,
QSpinBox,
QDoubleSpinBox,
QComboBox {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    color: {COLORS["text"]};
    padding: 6px 8px;
}}

QLineEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QComboBox:focus {{
    border: 1px solid {COLORS["primary"]};
}}
"""
