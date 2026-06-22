"""
AppService discovers installed applications by scanning the Start Menu
shortcut folders (the same approach Windows Search itself uses) rather
than querying the registry, which is slower and noisier with uninstall
entries that aren't actually launchable.

Icon extraction uses pywin32 to pull the icon embedded in the .exe or
.lnk target and caches it to disk as a .png so the UI never has to
re-extract it on every search.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

from utils.constants import APP_DATA_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

_ICON_CACHE_DIR = APP_DATA_DIR / "icon_cache"

_START_MENU_DIRS = [
    Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if os.environ.get("APPDATA") else None,
]


class AppService:
    def __init__(self):
        _ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def discover_apps(self) -> List[Tuple[str, str, Optional[str]]]:
        """Returns a list of (path, display_name, icon_path) tuples for
        every .lnk shortcut found under the Start Menu directories."""
        found: list[tuple[str, str, Optional[str]]] = []
        seen_names: set[str] = set()

        for base in _START_MENU_DIRS:
            if base is None or not base.exists():
                continue
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    if not fname.lower().endswith(".lnk"):
                        continue
                    name = fname[:-4]
                    if name.lower() in seen_names:
                        continue  # avoid duplicate entries across the two Start Menu dirs
                    full_path = os.path.join(root, fname)
                    icon_path = self._extract_icon(full_path, name)
                    found.append((full_path, name, icon_path))
                    seen_names.add(name.lower())

        logger.info("Discovered %d applications from Start Menu", len(found))
        return found

    def _extract_icon(self, shortcut_path: str, app_name: str) -> Optional[str]:
        """Extract and cache a .png icon for a shortcut. Returns the
        cached file path, or None if extraction isn't possible (e.g.
        running on a non-Windows dev machine without pywin32)."""
        safe_name = "".join(c for c in app_name if c.isalnum() or c in (" ", "_", "-")).strip()
        cache_path = _ICON_CACHE_DIR / f"{safe_name}.png"
        if cache_path.exists():
            return str(cache_path)

        try:
            import win32com.client
            import win32gui
            import win32ui
            import win32con
            from PIL import Image

            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            target = shortcut.Targetpath or shortcut_path

            large, _small = win32gui.ExtractIconEx(target, 0)
            if not large:
                return None
            hicon = large[0]

            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, 32, 32)
            hdc_mem = hdc.CreateCompatibleDC()
            hdc_mem.SelectObject(hbmp)
            hdc_mem.DrawIcon((0, 0), hicon)

            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer(
                "RGBA",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr, "raw", "BGRA", 0, 1,
            )
            img.save(str(cache_path))

            win32gui.DestroyIcon(hicon)
            return str(cache_path)
        except Exception as exc:
            # Non-fatal: the app still indexes, it just shows a
            # generic fallback icon in the UI.
            logger.debug("Icon extraction skipped for %s: %s", app_name, exc)
            return None
