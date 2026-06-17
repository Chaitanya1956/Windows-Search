"""
SystemTray puts an icon in the Windows system tray with a small context
menu (Show, Quit). Without this, closing the launcher window would have
no way to bring it back except the hotkey — having a tray icon is the
standard, expected behavior for a background launcher utility.
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from utils.logger import get_logger

logger = get_logger(__name__)


class SystemTray(QSystemTrayIcon):
    def __init__(self, main_window: QWidget, icon: QIcon, parent=None):
        super().__init__(icon, parent)
        self.main_window = main_window
        self.setToolTip("Spotlight")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        menu = QMenu()

        show_action = QAction("Show Launcher", menu)
        show_action.triggered.connect(self._show_main_window)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("Quit Spotlight", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _show_main_window(self) -> None:
        from services.window_service import WindowService
        WindowService.show_and_focus(self.main_window)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # Left-click (Trigger) on the tray icon also shows the window —
        # most users try this before finding the right-click menu.
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_main_window()
