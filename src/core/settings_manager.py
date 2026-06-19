"""
SettingsManager persists a ConfigModel to a JSON file under the app data
directory. There's no settings UI yet in Phase 1, but the read/write
path is fully functional so later phases can build a settings window
on top of it without touching this file.
"""

from __future__ import annotations

import json
from pathlib import Path

from models.config_model import ConfigModel
from utils.constants import APP_DATA_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

_SETTINGS_PATH = APP_DATA_DIR / "settings.json"


class SettingsManager:
    def __init__(self, settings_path: Path = _SETTINGS_PATH):
        self.settings_path = settings_path
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load()

    @property
    def config(self) -> ConfigModel:
        return self._config

    def _load(self) -> ConfigModel:
        if not self.settings_path.exists():
            logger.info("No settings file found, using defaults.")
            cfg = ConfigModel()
            self._save(cfg)
            return cfg
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return ConfigModel.from_dict(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read settings (%s); falling back to defaults.", exc)
            return ConfigModel()

    def _save(self, cfg: ConfigModel) -> None:
        try:
            self.settings_path.write_text(
                json.dumps(cfg.to_dict(), indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.error("Failed to write settings: %s", exc)

    def save(self) -> None:
        self._save(self._config)

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save()
