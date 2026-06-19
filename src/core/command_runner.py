"""
CommandRunner executes the action implied by pressing Enter on a result:
open a file with its default app, open a folder in Explorer, or launch
an application.

This is intentionally narrow in Phase 1 — it only knows how to "open
the thing at this path." Natural-language command parsing ("shutdown
pc", "open downloads", etc.) is explicitly Phase 2 scope and is not
implemented here yet.
"""

from __future__ import annotations

import os
import subprocess

from models.result_model import SearchResult
from utils.logger import get_logger

logger = get_logger(__name__)


class CommandRunner:
    @staticmethod
    def launch(result: SearchResult) -> bool:
        """Open the given result with the OS default handler.
        Returns True on apparent success, False if the path is gone."""
        path = result.path
        if not os.path.exists(path):
            logger.warning("Launch failed, path no longer exists: %s", path)
            return False

        try:
            # os.startfile is the correct, lightweight way to do this on
            # Windows — it defers entirely to the shell's file association,
            # so .exe launches, folders open in Explorer, and documents
            # open in whatever app the user has set as default.
            os.startfile(path)  # type: ignore[attr-defined]
            logger.info("Launched: %s", path)
            return True
        except AttributeError:
            # os.startfile only exists on Windows. Fall back for
            # development on macOS/Linux so the app is still runnable.
            try:
                opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
                subprocess.Popen([opener, path])
                return True
            except Exception as exc:
                logger.error("Fallback launch failed for %s: %s", path, exc)
                return False
        except OSError as exc:
            logger.error("Failed to launch %s: %s", path, exc)
            return False
