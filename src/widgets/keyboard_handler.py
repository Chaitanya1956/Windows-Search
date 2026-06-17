"""
KeyboardHandler centralizes the "arrow keys move selection, Enter
launches, Escape hides" behavior that defines a keyboard-first launcher.

It's implemented as a QObject event filter installed on the search
input, rather than overriding keyPressEvent directly on the widget, so
this logic stays in its own file and main_window.py doesn't have to
mix UI layout code with input handling.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent


class KeyboardHandler(QObject):
    def __init__(
        self,
        on_move_down: Callable[[], None],
        on_move_up: Callable[[], None],
        on_confirm: Callable[[], None],
        on_escape: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self.on_move_down = on_move_down
        self.on_move_up = on_move_up
        self.on_confirm = on_confirm
        self.on_escape = on_escape

    def eventFilter(self, watched, event) -> bool:
        if event.type() != QEvent.Type.KeyPress:
            return False

        key_event: QKeyEvent = event
        key = key_event.key()

        if key == Qt.Key.Key_Down:
            self.on_move_down()
            return True
        if key == Qt.Key.Key_Up:
            self.on_move_up()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.on_confirm()
            return True
        if key == Qt.Key.Key_Escape:
            self.on_escape()
            return True

        return False
