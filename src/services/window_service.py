"""
WindowService owns two things:
  1. The global hotkey registration (Alt+Space) that works even when
     the app has no focus — this is what makes it a "launcher" rather
     than a regular window.
  2. Show/hide/center/toggle logic for the main window, including
     making sure it grabs keyboard focus immediately on show so the
     user can type without an extra click.

Global hotkeys are registered via the `keyboard` library, which hooks
at the OS level. The hotkey callback fires on keyboard's own listener
thread, so it hands off to the Qt main thread via a Signal rather than
touching widgets directly from a non-Qt thread.
"""

from __future__ import annotations

import keyboard
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QGuiApplication

from utils.constants import HOTKEY_KEY, HOTKEY_MODIFIER
from utils.logger import get_logger

logger = get_logger(__name__)


class WindowService(QObject):
    # Emitted from the keyboard-hook thread, consumed on the Qt main
    # thread by whatever connects to it (main_window.py). Signals are
    # the standard, thread-safe way to bridge this in Qt.
    toggle_requested = Signal()

    def __init__(self):
        super().__init__()
        self._hotkey_handle = None

    def register_hotkey(self, modifier: str = HOTKEY_MODIFIER, key: str = HOTKEY_KEY) -> None:
        combo = f"{modifier}+{key}"
        try:
            self._hotkey_handle = keyboard.add_hotkey(
                combo, self._on_hotkey_pressed, suppress=False
            )
            logger.info("Global hotkey registered: %s", combo)
        except Exception as exc:
            logger.error("Failed to register hotkey %s: %s", combo, exc)

    def unregister_hotkey(self) -> None:
        if self._hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_handle)
            except (KeyError, ValueError):
                pass
            self._hotkey_handle = None

    def _on_hotkey_pressed(self) -> None:
        # Runs on keyboard's hook thread — just emit the signal and
        # let Qt's event loop marshal the actual UI work to the main
        # thread safely.
        self.toggle_requested.emit()

    @staticmethod
    def center_on_screen(widget: QWidget) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - widget.width()) // 2
        # Slightly above true vertical center, matching Spotlight/Raycast
        # conventions — a dead-center launcher feels visually low.
        y = geo.y() + int(geo.height() * 0.28)
        widget.move(x, y)

    @staticmethod
    def show_and_focus(widget: QWidget) -> None:
        WindowService.center_on_screen(widget)
        widget.show()
        widget.raise_()
        widget.activateWindow()
