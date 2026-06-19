"""
FileIndexer is responsible for keeping CacheManager's `files` table in
sync with the real filesystem.

Two mechanisms work together:
  1. A one-time (or "if stale") full walk of the configured root folders,
     run on a background thread so the UI never blocks on disk I/O.
  2. A watchdog Observer that watches those same roots and pushes
     create/delete/move events into the cache in real time afterward.

This means: no polling, no repeated full-disk scans, and the index
stays accurate as the user adds/removes/renames files.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import List

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from core.cache_manager import CacheManager
from utils.constants import (
    IGNORED_DIR_NAMES,
    INDEXABLE_EXTENSIONS,
    MAX_INDEX_DEPTH,
)
from utils.helpers import file_extension, is_ignored_dir, safe_path_exists
from utils.logger import get_logger

logger = get_logger(__name__)

_BULK_FLUSH_SIZE = 500  # rows buffered before a bulk DB insert


class _WatchdogHandler(FileSystemEventHandler):
    """Translates raw filesystem events into CacheManager calls.

    Runs on watchdog's own background thread — kept intentionally tiny
    and non-blocking; any heavier work (stat calls) is still cheap
    enough per-event to be fine here, since these fire one at a time
    rather than in the thousands like the initial scan does.
    """

    def __init__(self, cache: CacheManager):
        super().__init__()
        self.cache = cache

    def _stat_and_upsert(self, path: str) -> None:
        if not safe_path_exists(path):
            return
        try:
            st = os.stat(path)
            is_dir = os.path.isdir(path)
        except OSError:
            return

        ext = "" if is_dir else file_extension(path)
        if not is_dir and ext not in INDEXABLE_EXTENSIONS:
            return

        name = os.path.basename(path)
        parent = os.path.dirname(path)
        self.cache.upsert_file(
            path=path,
            name=name,
            parent_dir=parent,
            extension=ext,
            is_dir=is_dir,
            size_bytes=getattr(st, "st_size", 0),
            mtime=getattr(st, "st_mtime", 0.0),
        )

    def on_created(self, event):
        self._stat_and_upsert(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._stat_and_upsert(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            self.cache.delete_files_under(event.src_path)
        else:
            self.cache.delete_file(event.src_path)

    def on_moved(self, event):
        # Treat as delete-old + create-new; simplest correct handling
        # for renames and cross-folder moves alike.
        if event.is_directory:
            self.cache.delete_files_under(event.src_path)
        else:
            self.cache.delete_file(event.src_path)
        self._stat_and_upsert(event.dest_path)


class FileIndexer:
    def __init__(self, cache: CacheManager, roots: List[str]):
        self.cache = cache
        self.roots = [r for r in roots if safe_path_exists(r)]
        self._observer: Observer | None = None
        self._scan_thread: threading.Thread | None = None
        self._stop_flag = threading.Event()

    # -- public API -----------------------------------------------------

    def start(self) -> None:
        """Kick off the initial scan (background thread) and start
        watching for live changes. Non-blocking — returns immediately."""
        self._scan_thread = threading.Thread(
            target=self._run_initial_scan, name="IndexerScanThread", daemon=True
        )
        self._scan_thread.start()
        self._start_watchdog()

    def stop(self) -> None:
        self._stop_flag.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)

    # -- initial scan -----------------------------------------------------

    def _run_initial_scan(self) -> None:
        started = time.time()
        total = 0
        for root in self.roots:
            if self._stop_flag.is_set():
                return
            total += self._scan_root(root)
        elapsed = time.time() - started
        logger.info("Initial scan complete: %d items in %.2fs across %d roots",
                     total, elapsed, len(self.roots))
        self.cache.set_meta("last_full_scan_at", str(time.time()))

    def _scan_root(self, root: str) -> int:
        count = 0
        buffer: list[tuple] = []
        root_depth = root.rstrip(os.sep).count(os.sep)

        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            if self._stop_flag.is_set():
                break

            depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
            if depth >= MAX_INDEX_DEPTH:
                dirnames[:] = []
                continue

            # Prune ignored directories in-place so os.walk never
            # descends into them — this is what keeps scans fast.
            dirnames[:] = [d for d in dirnames if not is_ignored_dir(d)]

            for dname in dirnames:
                full = os.path.join(dirpath, dname)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                buffer.append((full, dname, dirpath, "", True, 0, st.st_mtime))
                count += 1

            for fname in filenames:
                ext = file_extension(fname)
                if ext not in INDEXABLE_EXTENSIONS:
                    continue
                full = os.path.join(dirpath, fname)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                buffer.append((full, fname, dirpath, ext, False, st.st_size, st.st_mtime))
                count += 1

            if len(buffer) >= _BULK_FLUSH_SIZE:
                self.cache.upsert_files_bulk(buffer)
                buffer.clear()

        if buffer:
            self.cache.upsert_files_bulk(buffer)

        return count

    # -- live watching -----------------------------------------------------

    def _start_watchdog(self) -> None:
        self._observer = Observer()
        handler = _WatchdogHandler(self.cache)
        for root in self.roots:
            try:
                self._observer.schedule(handler, root, recursive=True)
            except OSError as exc:
                logger.warning("Could not watch %s: %s", root, exc)
        self._observer.start()
        logger.info("Watchdog observer started for %d roots", len(self.roots))
