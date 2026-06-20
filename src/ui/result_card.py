"""
ResultCard renders one row in the results list: icon, title, subtitle,
and a small category tag on the right (e.g. "Application", "Recent").

Selection is shown via a left accent bar + subtle background tint
rather than a full border, which reads as calmer at a glance when
scanning a list of up to 9 rows.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from models.result_model import SearchResult
from utils.constants import (
    CATEGORY_APP,
    CATEGORY_FILE,
    CATEGORY_FOLDER,
    CATEGORY_HISTORY,
    RESULT_ROW_HEIGHT,
)
from utils.helpers import truncate_middle

ACCENT_COLOR = "#FF8A3D"
TEXT_PRIMARY = "#F2F1ED"
TEXT_MUTED = "#8C8C94"
SELECTED_BG = "#2C2A26"  # warm-tinted dark, not a generic blue highlight

_CATEGORY_LABELS = {
    CATEGORY_APP: "Application",
    CATEGORY_FILE: "File",
    CATEGORY_FOLDER: "Folder",
    CATEGORY_HISTORY: "Recent",
}

# Fallback glyphs used until a real extracted icon is available —
# keeps every row visually anchored even before icon caching finishes.
_CATEGORY_GLYPHS = {
    CATEGORY_APP: "▣",
    CATEGORY_FILE: "▤",
    CATEGORY_FOLDER: "▢",
    CATEGORY_HISTORY: "↺",
}


class ResultCard(QWidget):
    def __init__(self, result: SearchResult, parent=None):
        super().__init__(parent)
        self.result = result
        self._selected = False
        self.setFixedHeight(RESULT_ROW_HEIGHT)
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(12)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(28, 28)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_icon()
        layout.addWidget(self.icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        self.title_label = QLabel(self.result.title)
        self.title_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600; "
            f'font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;'
        )
        text_col.addWidget(self.title_label)

        subtitle_text = truncate_middle(self.result.subtitle, 64) if self.result.subtitle else ""
        self.subtitle_label = QLabel(subtitle_text)
        self.subtitle_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; "
            f'font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;'
        )
        text_col.addWidget(self.subtitle_label)

        layout.addLayout(text_col, stretch=1)

        tag_text = _CATEGORY_LABELS.get(self.result.category, "")
        self.tag_label = QLabel(tag_text)
        self.tag_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; "
            f'font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;'
        )
        self.tag_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.tag_label)

        # Left accent bar — hidden until selected. Using a real widget
        # rather than a border avoids the layout reflow a border-width
        # change would otherwise cause on selection.
        self.accent_bar = QLabel(self)
        self.accent_bar.setFixedWidth(3)
        self.accent_bar.setStyleSheet(f"background: {ACCENT_COLOR}; border-radius: 2px;")
        self.accent_bar.hide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.accent_bar.setGeometry(0, 4, 3, self.height() - 8)

    def _set_icon(self) -> None:
        if self.result.icon_path:
            pix = QPixmap(self.result.icon_path)
            if not pix.isNull():
                self.icon_label.setPixmap(
                    pix.scaled(
                        24, 24,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        glyph = _CATEGORY_GLYPHS.get(self.result.category, "▤")
        self.icon_label.setText(glyph)
        self.icon_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.accent_bar.setVisible(selected)
        self._apply_style()

    def _apply_style(self) -> None:
        bg = SELECTED_BG if self._selected else "transparent"
        self.setStyleSheet(f"QWidget {{ background: {bg}; border-radius: 8px; }}")
