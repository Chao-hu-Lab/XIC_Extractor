import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.styles import COLORS


class _Card(QFrame):
    def __init__(self, label: str, value: str, detail: str, color: str) -> None:
        super().__init__()
        self.setObjectName("section_card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        label_widget = QLabel(label.upper())
        label_widget.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9pt; font-weight: 600;"
        )
        value_widget = QLabel(value)
        value_widget.setStyleSheet(
            f"color: {color}; font-size: 20pt; font-weight: 700;"
        )
        detail_widget = QLabel(detail)
        detail_widget.setWordWrap(True)
        detail_widget.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9pt;")

        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        layout.addWidget(detail_widget)
        layout.addStretch()


class ResultsSection(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._excel_path = ""
        self.setVisible(False)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("section_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        root_layout.addWidget(card)

        header = QFrame()
        header.setObjectName("section_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        title = QLabel("④ Results")
        title.setObjectName("section_title")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self._folder_button = QPushButton("開啟資料夾")
        self._folder_button.setObjectName("btn_open_excel")
        self._folder_button.clicked.connect(self._open_folder)
        self._folder_button.setVisible(False)
        header_layout.addWidget(self._folder_button)

        self._open_button = QPushButton("開啟 Excel")
        self._open_button.setObjectName("btn_open_excel")
        self._open_button.clicked.connect(self._open_excel)
        self._open_button.setVisible(False)
        header_layout.addWidget(self._open_button)
        card_layout.addWidget(header)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(16, 16, 16, 16)
        self._body_layout.setSpacing(12)
        card_layout.addWidget(self._body)

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._error_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 600;")
        self._error_label.setVisible(False)
        self._body_layout.addWidget(self._error_label)

        self._istd_warn_label = QLabel()
        self._istd_warn_label.setWordWrap(True)
        self._istd_warn_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._istd_warn_label.setStyleSheet(
            "background-color: #FF7043; color: white; font-weight: 600;"
            " padding: 8px 12px; border-radius: 4px;"
        )
        self._istd_warn_label.setVisible(False)
        self._body_layout.addWidget(self._istd_warn_label)

        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        self._body_layout.addLayout(self._grid)

    def update_results(self, summary: dict) -> None:
        self._excel_path = summary.get("excel_path", "")
        has_path = bool(self._excel_path)
        self._open_button.setVisible(has_path)
        self._folder_button.setVisible(has_path)
        self._error_label.clear()
        self._error_label.setVisible(False)
        istd_warnings = summary.get("istd_warnings", [])
        if istd_warnings:
            parts = [
                f"{warning['label']} ({warning['detected']}/{warning['total']})"
                for warning in istd_warnings
            ]
            self._istd_warn_label.setText("⚠ ISTD 未全偵測：" + "、".join(parts))
            self._istd_warn_label.setVisible(True)
        else:
            self._istd_warn_label.setVisible(False)
        self._clear_grid()

        cards: list[_Card] = []
        for target in summary.get("targets", []):
            cards.append(
                _Card(
                    label=str(target["label"]),
                    value=f"{target['detected']}/{target['total']}",
                    detail=_target_detail(target),
                    color=COLORS["success"]
                    if target.get("detected")
                    else COLORS["text_muted"],
                )
            )

        cards.append(
            _Card(
                label="DIAGNOSTICS",
                value=str(summary.get("diagnostics_count", 0)),
                detail="Issue rows",
                color=COLORS["warning"]
                if summary.get("diagnostics_count", 0)
                else COLORS["success"],
            )
        )
        cards.append(
            _Card(
                label="TOTAL FILES",
                value=str(summary.get("total_files", 0)),
                detail="Processed sample files",
                color=COLORS["primary"],
            )
        )

        for index, card in enumerate(cards):
            row = index // 2
            column = index % 2
            self._grid.addWidget(card, row, column)

        self.setVisible(True)

    def show_error(self, message: str) -> None:
        self._excel_path = ""
        self._open_button.setVisible(False)
        self._folder_button.setVisible(False)
        self._istd_warn_label.setVisible(False)
        self._clear_grid()
        self._error_label.setText(message)
        self._error_label.setVisible(True)
        self.setVisible(True)

    def _open_excel(self) -> None:
        if self._excel_path:
            os.startfile(self._excel_path)

    def _open_folder(self) -> None:
        if self._excel_path:
            from pathlib import Path

            os.startfile(str(Path(self._excel_path).parent))

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def _target_detail(target: dict) -> str:
    detail = (
        f"✓{target.get('nl_ok', 0)} "
        f"⚠{target.get('nl_warn', 0)} "
        f"✗{target.get('nl_fail', 0)} "
        f"—{target.get('nl_no_ms2', 0)}"
    )
    median_area = target.get("median_area")
    if median_area is not None:
        detail += f"\nMedian Area: {float(median_area):,.2f}"
    return detail
