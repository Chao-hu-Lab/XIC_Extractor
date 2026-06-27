"""Shared confirmation dialogs that guard against accidental, costly actions."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QWidget

from gui import styles


def _ask(parent: QWidget, title: str, text: str, confirm_label: str) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    yes = box.addButton(confirm_label, QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)  # default to the safe (cancel) action
    box.exec()
    return box.clickedButton() is yes


def confirm_stop(parent: QWidget) -> bool:
    """Confirm stopping an in-progress run (already-finished stages are kept)."""
    return _ask(
        parent,
        "停止執行",
        "確定要停止目前的執行嗎？\n已完成的階段會保留，未完成的會中斷。",
        "停止執行",
    )


def confirm_close_while_busy(parent: QWidget) -> bool:
    """Confirm closing the window while a run is still active."""
    return _ask(
        parent,
        "執行仍在進行",
        "有工作正在執行中，關閉視窗會先要求中斷。\n若目前階段尚未停止，視窗會等待停止後再關閉。",
        "關閉並中斷",
    )


def show_about(parent: QWidget, version: str) -> None:
    """Show the application's About dialog."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("關於 XIC Extractor")
    box.setText("<b>XIC Extractor</b>")
    box.setInformativeText(
        f"版本 {version}<br><br>"
        "代謝組學 LC-MS 工具：目標式萃取、非目標峰偵測與跨樣本對齊。<br><br>"
        f"<span style='color:{styles.ACTIVE['text_muted']};'>Chao-hu Lab</span>"
    )
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()
