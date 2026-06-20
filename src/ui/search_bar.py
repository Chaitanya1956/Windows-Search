"""
SearchBar is the single-line input at the top of the launcher. Visually
it IS the launcher when collapsed — no title bar, no chrome, just the
input and (once results exist) the list below it.

Design tokens (consistent with main_window.py and result_card.py):
  Background:   #1C1C20  (near-black, slightly warm rather than pure
                blue-black — keeps long sessions easier on the eyes)
  Surface:      #242429  (one step up, used for the window panel itself)
  Accent:       #FF8A3D  (warm amber — the signature touch; used only
                for the focus glow and selection state, nowhere else)
  Text primary: #F2F1ED
  Text muted:   #8C8C94
  Font:         Segoe UI Variable (falls back to Segoe UI, then system
                default) — native-feeling on Windows 11 rather than
                importing a web font that would fight the OS look.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit

ACCENT_COLOR = "#FF8A3D"
TEXT_PRIMARY = "#F2F1ED"
TEXT_MUTED = "#8C8C94"

_SEARCH_BAR_STYLE = f"""
QLineEdit {{
    background: transparent;
    border: none;
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 21px;
    font-weight: 400;
    padding: 0px 4px;
    selection-background-color: {ACCENT_COLOR};
    selection-color: #1C1C20;
}}
"""


class SearchBar(QLineEdit):
    text_changed_debounced = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search apps, files, and folders…")
        self.setStyleSheet(_SEARCH_BAR_STYLE)
        self.setFixedHeight(56)
        self.setFrame(False)
        self.setClearButtonEnabled(False)
        self.setAttribute_default_focus()

    def setAttribute_default_focus(self) -> None:
        # Named for clarity at the call site; just ensures the bar can
        # receive focus immediately when the window is shown so the
        # user can start typing with zero clicks.
        from PySide6.QtCore import Qt
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def clear_and_reset(self) -> None:
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)
