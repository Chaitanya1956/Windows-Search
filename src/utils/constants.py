"""
Central constants for the application.
Nothing here should ever import from another src module — this sits
at the bottom of the dependency graph so it can be imported anywhere
without circular-import risk.
"""

from pathlib import Path
import os

# --------------------------------------------------------------------------
# Application identity
# --------------------------------------------------------------------------
APP_NAME = "Spotlight"
APP_ORG = "SpotlightApp"

# --------------------------------------------------------------------------
# Filesystem locations
# --------------------------------------------------------------------------
# %LOCALAPPDATA%/Spotlight  (falls back to a local folder on non-Windows
# dev machines so the app is still runnable for development/testing)
_local_appdata = os.environ.get("LOCALAPPDATA")
if _local_appdata:
    APP_DATA_DIR = Path(_local_appdata) / APP_NAME
else:
    APP_DATA_DIR = Path.home() / f".{APP_NAME.lower()}"

DB_PATH = APP_DATA_DIR / "index.sqlite3"
LOG_DIR = APP_DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "spotlight.log"

# --------------------------------------------------------------------------
# Global hotkey
# --------------------------------------------------------------------------
# win32con virtual key codes / modifiers are resolved in window_service.py.
# Kept here as plain descriptive strings so they can later be made
# user-configurable without touching the hotkey implementation.
HOTKEY_MODIFIER = "alt"
HOTKEY_KEY = "space"

# --------------------------------------------------------------------------
# Indexing
# --------------------------------------------------------------------------
# Root folders scanned by default. Extended per-user later via settings.
DEFAULT_INDEX_ROOTS = [
    str(Path.home() / "Desktop"),
    str(Path.home() / "Documents"),
    str(Path.home() / "Downloads"),
    str(Path.home() / "Pictures"),
]

# Directory names skipped entirely during indexing (case-insensitive match
# on the final path component). Keeps the index free of noise and avoids
# wasting cycles walking huge generated trees.
IGNORED_DIR_NAMES = {
    "node_modules", "__pycache__", ".git", ".svn", ".hg",
    "$recycle.bin", "system volume information", "windows",
    "programdata", "appdata", ".venv", "venv", "site-packages",
    "dist", "build", ".cache",
}

# File extensions considered indexable. Anything else is skipped to keep
# the index relevant (binaries, system files, etc. are not useful in a
# launcher search).
INDEXABLE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".md", ".xlsx", ".xls", ".csv",
    ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
    ".mp4", ".mov", ".mkv", ".avi", ".mp3", ".wav", ".zip", ".rar",
    ".py", ".js", ".ts", ".json", ".exe", ".lnk",
}

# Maximum directory depth walked from each root. Prevents pathological
# slow scans on deeply nested folders while still covering normal usage.
MAX_INDEX_DEPTH = 12

# How often (seconds) the background indexer does a full incremental
# rescan pass on top of the real-time watchdog events.
PERIODIC_RESCAN_INTERVAL_SEC = 600  # 10 minutes

# --------------------------------------------------------------------------
# Search behaviour
# --------------------------------------------------------------------------
SEARCH_DEBOUNCE_MS = 60          # delay after keystroke before querying
MAX_RESULTS_DISPLAYED = 9        # keep result list short = fast to scan
FUZZY_SCORE_THRESHOLD = 45       # 0-100, rapidfuzz score cutoff
MAX_HISTORY_ITEMS = 200          # capped so the table never grows unbounded

# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
WINDOW_WIDTH = 680
WINDOW_COLLAPSED_HEIGHT = 64      # height with just the search bar
RESULT_ROW_HEIGHT = 56
MAX_VISIBLE_ROWS = MAX_RESULTS_DISPLAYED

ANIMATION_DURATION_MS = 140

# Result categories — used both for icons and for the future filter bar.
CATEGORY_APP = "app"
CATEGORY_FILE = "file"
CATEGORY_FOLDER = "folder"
CATEGORY_HISTORY = "history"
