"""
Small, generic, dependency-light helper functions shared across modules.
Nothing app-specific lives here — just utility functions that don't
belong to a single module's responsibility.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer

from utils.constants import IGNORED_DIR_NAMES


def is_ignored_dir(dir_name: str) -> bool:
    """True if a directory's bare name should be skipped during indexing."""
    return dir_name.lower() in IGNORED_DIR_NAMES


def human_readable_size(num_bytes: int) -> str:
    """Convert a byte count to a short human string, e.g. 1536 -> '1.5 KB'."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def safe_path_exists(path: str) -> bool:
    """os.path.exists wrapper that never raises (e.g. on a removed USB
    drive mid-scan, permission errors, malformed paths)."""
    try:
        return os.path.exists(path)
    except (OSError, ValueError):
        return False


def file_extension(path: str) -> str:
    """Lower-cased extension including the dot, e.g. '.pdf'. Empty string
    if there is none."""
    return Path(path).suffix.lower()


def make_debouncer(parent, delay_ms: int):
    """Create a single-shot QTimer-based debouncer.

    Returns a `trigger(callback)` function. Calling trigger() repeatedly
    resets the delay so `callback` only fires `delay_ms` after the last
    call — exactly the behaviour we want for "search while typing"
    without firing a query on every keystroke.
    """
    timer = QTimer(parent)
    timer.setSingleShot(True)
    timer.setInterval(delay_ms)

    state = {"callback": None}

    def _on_timeout():
        cb = state["callback"]
        if cb is not None:
            cb()

    timer.timeout.connect(_on_timeout)

    def trigger(callback):
        state["callback"] = callback
        timer.start()  # restarts if already running

    return trigger


def truncate_middle(text: str, max_len: int = 70) -> str:
    """Shorten long paths/strings by snipping the middle, keeping both
    ends visible — more useful than tail-truncation for file paths."""
    if len(text) <= max_len:
        return text
    keep = max_len - 3
    head = keep // 2
    tail = keep - head
    return f"{text[:head]}...{text[-tail:]}"
