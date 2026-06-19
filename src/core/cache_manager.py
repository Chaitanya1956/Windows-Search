"""
CacheManager owns the single SQLite database used for the file/app index
and history. It is the ONLY module that writes raw SQL — every other
module calls methods on this class, which keeps schema changes localized
to one file.

SQLite is opened with WAL journaling so the background indexer (writer)
and the UI search thread (reader) don't block each other.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from utils.constants import DB_PATH, MAX_HISTORY_ITEMS
from utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    parent_dir  TEXT NOT NULL,
    extension   TEXT,
    is_dir      INTEGER NOT NULL DEFAULT 0,
    size_bytes  INTEGER DEFAULT 0,
    mtime       REAL DEFAULT 0,
    indexed_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_dir);

CREATE TABLE IF NOT EXISTS apps (
    path        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    icon_path   TEXT,
    indexed_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apps_name ON apps(name);

CREATE TABLE IF NOT EXISTS history (
    path            TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,
    launch_count    INTEGER NOT NULL DEFAULT 1,
    last_launched_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS index_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


class CacheManager:
    """Thread-safe-ish wrapper around one SQLite file.

    SQLite connections aren't shared across threads by default, so each
    thread that needs DB access calls `get_connection()`, which lazily
    creates a thread-local connection. All connections point at the same
    on-disk file, and WAL mode lets reads and writes coexist.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    # -- connection handling -------------------------------------------------

    def get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=10,
                check_same_thread=False,
            )
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self.get_connection()
        conn.executescript(_SCHEMA)
        conn.commit()
        logger.info("Database schema ready at %s", self.db_path)

    # -- files / folders -------------------------------------------------

    def upsert_file(
        self,
        path: str,
        name: str,
        parent_dir: str,
        extension: str,
        is_dir: bool,
        size_bytes: int,
        mtime: float,
    ) -> None:
        conn = self.get_connection()
        conn.execute(
            """
            INSERT INTO files (path, name, parent_dir, extension, is_dir,
                                size_bytes, mtime, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name=excluded.name,
                parent_dir=excluded.parent_dir,
                extension=excluded.extension,
                is_dir=excluded.is_dir,
                size_bytes=excluded.size_bytes,
                mtime=excluded.mtime,
                indexed_at=excluded.indexed_at
            """,
            (path, name, parent_dir, extension, int(is_dir), size_bytes, mtime, time.time()),
        )

    def upsert_files_bulk(self, rows: Sequence[tuple]) -> None:
        """rows: (path, name, parent_dir, extension, is_dir, size_bytes, mtime)
        Bulk insert is dramatically faster than per-row upsert during the
        initial full scan (single transaction vs thousands)."""
        conn = self.get_connection()
        now = time.time()
        conn.executemany(
            """
            INSERT INTO files (path, name, parent_dir, extension, is_dir,
                                size_bytes, mtime, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name=excluded.name,
                parent_dir=excluded.parent_dir,
                extension=excluded.extension,
                is_dir=excluded.is_dir,
                size_bytes=excluded.size_bytes,
                mtime=excluded.mtime,
                indexed_at=excluded.indexed_at
            """,
            [(p, n, pd, ext, int(d), sz, mt, now) for (p, n, pd, ext, d, sz, mt) in rows],
        )
        conn.commit()

    def delete_file(self, path: str) -> None:
        conn = self.get_connection()
        conn.execute("DELETE FROM files WHERE path = ?", (path,))
        conn.commit()

    def delete_files_under(self, dir_path: str) -> None:
        """Remove a whole subtree from the index (used when a watched
        folder itself is deleted/moved)."""
        conn = self.get_connection()
        conn.execute("DELETE FROM files WHERE path = ? OR path LIKE ?", (dir_path, dir_path + "\\%"))
        conn.commit()

    def get_known_paths_under(self, root: str) -> set:
        conn = self.get_connection()
        cur = conn.execute(
            "SELECT path FROM files WHERE path = ? OR path LIKE ?",
            (root, root + "\\%"),
        )
        return {row["path"] for row in cur.fetchall()}

    def search_files(self, query_like: str, limit: int) -> List[sqlite3.Row]:
        """Cheap SQL-level prefilter (substring match) before fuzzy
        ranking in Python. Keeps the candidate set small even with a
        large index, so RapidFuzz only scores a few hundred rows, not
        the whole table."""
        conn = self.get_connection()
        cur = conn.execute(
            "SELECT path, name, parent_dir, extension, is_dir FROM files "
            "WHERE name LIKE ? LIMIT ?",
            (f"%{query_like}%", limit),
        )
        return cur.fetchall()

    def file_count(self) -> int:
        conn = self.get_connection()
        return conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    # -- apps -------------------------------------------------------------

    def upsert_apps_bulk(self, rows: Sequence[tuple]) -> None:
        """rows: (path, name, icon_path)"""
        conn = self.get_connection()
        now = time.time()
        conn.executemany(
            """
            INSERT INTO apps (path, name, icon_path, indexed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name=excluded.name,
                icon_path=excluded.icon_path,
                indexed_at=excluded.indexed_at
            """,
            [(p, n, ic, now) for (p, n, ic) in rows],
        )
        conn.commit()

    def search_apps(self, query_like: str, limit: int) -> List[sqlite3.Row]:
        conn = self.get_connection()
        cur = conn.execute(
            "SELECT path, name, icon_path FROM apps WHERE name LIKE ? LIMIT ?",
            (f"%{query_like}%", limit),
        )
        return cur.fetchall()

    def all_apps(self) -> List[sqlite3.Row]:
        conn = self.get_connection()
        return conn.execute("SELECT path, name, icon_path FROM apps").fetchall()

    # -- history ------------------------------------------------------------

    def record_launch(self, path: str, title: str, category: str) -> None:
        conn = self.get_connection()
        now = time.time()
        conn.execute(
            """
            INSERT INTO history (path, title, category, launch_count, last_launched_at)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(path) DO UPDATE SET
                launch_count = launch_count + 1,
                last_launched_at = excluded.last_launched_at,
                title = excluded.title
            """,
            (path, title, category, now),
        )
        conn.commit()
        self._trim_history(conn)

    def _trim_history(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            DELETE FROM history WHERE path NOT IN (
                SELECT path FROM history
                ORDER BY last_launched_at DESC
                LIMIT ?
            )
            """,
            (MAX_HISTORY_ITEMS,),
        )
        conn.commit()

    def recent_history(self, limit: int) -> List[sqlite3.Row]:
        conn = self.get_connection()
        return conn.execute(
            "SELECT path, title, category, launch_count, last_launched_at "
            "FROM history ORDER BY last_launched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def search_history(self, query_like: str, limit: int) -> List[sqlite3.Row]:
        conn = self.get_connection()
        return conn.execute(
            "SELECT path, title, category, launch_count, last_launched_at "
            "FROM history WHERE title LIKE ? "
            "ORDER BY launch_count DESC, last_launched_at DESC LIMIT ?",
            (f"%{query_like}%", limit),
        ).fetchall()

    # -- meta (used to know if first-run full scan already happened) -----

    def get_meta(self, key: str) -> Optional[str]:
        conn = self.get_connection()
        row = conn.execute("SELECT value FROM index_meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO index_meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
