"""
Launcher is the composition root for everything in core/services — it
builds the CacheManager, kicks off app discovery and file indexing, and
hands back a ready-to-use SearchEngine. main.py calls this once at
startup and otherwise doesn't need to know how these pieces fit
together.
"""

from __future__ import annotations

import threading

from core.cache_manager import CacheManager
from core.file_indexer import FileIndexer
from core.search_engine import SearchEngine
from core.settings_manager import SettingsManager
from services.app_service import AppService
from utils.logger import get_logger

logger = get_logger(__name__)


class Launcher:
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.cache = CacheManager()
        self.app_service = AppService()
        self.search_engine = SearchEngine(self.cache)
        self.file_indexer = FileIndexer(
            self.cache, self.settings_manager.config.index_roots
        )

    def start(self) -> None:
        """Kick off background work. Returns immediately — app
        discovery and the initial file scan both run on background
        threads so the UI is interactive instantly."""
        threading.Thread(
            target=self._discover_apps, name="AppDiscoveryThread", daemon=True
        ).start()
        self.file_indexer.start()
        logger.info("Launcher started: background indexing and app discovery underway.")

    def _discover_apps(self) -> None:
        apps = self.app_service.discover_apps()
        rows = [(path, name, icon) for (path, name, icon) in apps]
        if rows:
            self.cache.upsert_apps_bulk(rows)
        logger.info("App discovery complete: %d apps cached.", len(rows))

    def shutdown(self) -> None:
        self.file_indexer.stop()
        self.cache.close()
