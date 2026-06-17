"""
Application-wide logging.

Every module gets its own named logger via get_logger(__name__), but they
all share one rotating file handler so logs land in a single place
(%LOCALAPPDATA%/Spotlight/logs/spotlight.log) without flooding disk.
"""

import logging
import logging.handlers
import sys

from utils.constants import LOG_DIR, LOG_FILE

_configured = False


def _configure_root() -> None:
    """Idempotently configure the root 'spotlight' logger. Safe to call
    multiple times — only does real work once per process."""
    global _configured
    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("spotlight")
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.propagate = False

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger nested under 'spotlight'.

    Usage: logger = get_logger(__name__)
    """
    _configure_root()
    return logging.getLogger(f"spotlight.{name}")
