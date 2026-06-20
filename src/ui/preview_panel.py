"""
PreviewPanel: NOT part of Phase 1.

File preview (PDFs/images/text without opening them) is listed in the
full project brief but was not included in the Phase 1 feature list
agreed on. This file exists only so the `ui/` package matches the
target architecture and future phases have an obvious place to add it.

Explicitly marked — this is the one intentional placeholder in the
Phase 1 codebase, not silently-dropped functionality.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


class PreviewPanel(QWidget):
    """Intentionally unimplemented in Phase 1. Do not wire into
    main_window.py yet — there is no feature behind it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hide()  # never shown until a future phase implements content
