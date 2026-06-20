"""
SettingsWindow: NOT part of Phase 1.

Phase 1's feature list has no settings UI — only SettingsManager
(core/settings_manager.py) exists, providing working persistence that
a real settings window can be built on top of later. This file is a
structural placeholder so `ui/` matches the target architecture.

Explicitly marked, not silently included as fake functionality.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


class SettingsWindow(QWidget):
    """Intentionally unimplemented in Phase 1."""

    def __init__(self, parent=None):
        super().__init__(parent)
