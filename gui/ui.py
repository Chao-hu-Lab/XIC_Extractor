"""Shared layout primitives so every section follows one spacing system.

Centralising the card/header/label construction here keeps the visual rhythm
consistent (header padding, body padding, inter-field spacing) instead of each
section hard-coding its own margins.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

# Spacing scale (px). Use these instead of ad-hoc numbers.
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20


def titled_card(
    title: str, subtitle: str = ""
) -> tuple[QFrame, QHBoxLayout, QVBoxLayout]:
    """A section card with a styled header. Returns (card, header_layout,
    card_layout). Callers add header actions to header_layout and their own
    body (grid, toolbar, table, …) to card_layout. Use section_card() instead
    when a simple padded vertical body is all you need.

    An optional subtitle renders a muted descriptor under the title so the
    numbered step cards read as a hierarchy rather than equal-weight boxes.
    """
    card = QFrame()
    card.setObjectName("section_card")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(0, 0, 0, 0)
    card_layout.setSpacing(0)

    header = QFrame()
    header.setObjectName("section_header")
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, SPACE_MD)

    title_col = QVBoxLayout()
    title_col.setContentsMargins(0, 0, 0, 0)
    title_col.setSpacing(1)
    label = QLabel(title)
    label.setObjectName("section_title")
    title_col.addWidget(label)
    if subtitle:
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("section_subtitle")
        title_col.addWidget(subtitle_label)
    header_layout.addLayout(title_col)
    card_layout.addWidget(header)
    return card, header_layout, card_layout


def section_card(title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
    """A titled section card with a padded vertical body.

    Body content is laid out with SPACE_LG padding and SPACE_MD between items.
    """
    card, _header_layout, card_layout = titled_card(title, subtitle)
    body = QVBoxLayout()
    body.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
    body.setSpacing(SPACE_MD)
    card_layout.addLayout(body)
    return card, body


def field_label(text: str) -> QLabel:
    """A muted, consistent form-field label."""
    label = QLabel(text)
    label.setObjectName("field_label")
    return label
