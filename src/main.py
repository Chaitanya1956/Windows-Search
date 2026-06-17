"""
Entry point. Run with:  python main.py  (from inside src/)

Responsibilities, and only these:
  - Create the QApplication
  - Build the Launcher (which wires up cache/search/indexing)
  - Build MainWindow and SystemTray
  - Register the global hotkey
  - Start the Qt event loop

No business logic lives here — everything is delegated to the modules
built for that purpose. This keeps main.py readable as a "what starts
in what order" map of the whole app.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.launcher import Launcher
from services.window_service import WindowService
from ui.main_window import MainWindow
from utils.logger import get_logger
from widgets.system_tray import SystemTray

logger = get_logger("main")


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # the tray icon keeps it alive

    launcher = Launcher()
    launcher.start()

    window = MainWindow(launcher.cache, launcher.search_engine)

    window_service = WindowService()
    window_service.toggle_requested.connect(window.toggle_launcher)
    window_service.register_hotkey(
        launcher.settings_manager.config.hotkey_modifier,
        launcher.settings_manager.config.hotkey_key,
    )

    tray_icon = QIcon.fromTheme("system-search")
    if tray_icon.isNull():
        # fromTheme can return a null icon on Windows (no freedesktop
        # icon theme) — fall back to a built-in Qt standard icon so the
        # tray still shows something rather than a blank/missing icon.
        from PySide6.QtWidgets import QStyle
        tray_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
    tray = SystemTray(window, tray_icon)
    tray.show()

    app.aboutToQuit.connect(window_service.unregister_hotkey)
    app.aboutToQuit.connect(launcher.shutdown)

    logger.info("Spotlight is running. Press Alt+Space to open the launcher.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
