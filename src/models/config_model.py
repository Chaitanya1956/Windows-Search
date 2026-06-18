"""
Typed configuration object. settings_manager.py reads/writes this to/from
a JSON file on disk; every other module receives an already-constructed
ConfigModel rather than touching the file directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from utils.constants import DEFAULT_INDEX_ROOTS, HOTKEY_KEY, HOTKEY_MODIFIER


@dataclass
class ConfigModel:
    theme: str = "dark"
    hotkey_modifier: str = HOTKEY_MODIFIER
    hotkey_key: str = HOTKEY_KEY
    index_roots: List[str] = field(default_factory=lambda: list(DEFAULT_INDEX_ROOTS))
    excluded_paths: List[str] = field(default_factory=list)
    launch_on_startup: bool = False
    animations_enabled: bool = True
    max_results: int = 9

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "hotkey_modifier": self.hotkey_modifier,
            "hotkey_key": self.hotkey_key,
            "index_roots": self.index_roots,
            "excluded_paths": self.excluded_paths,
            "launch_on_startup": self.launch_on_startup,
            "animations_enabled": self.animations_enabled,
            "max_results": self.max_results,
        }

    @staticmethod
    def from_dict(data: dict) -> "ConfigModel":
        defaults = ConfigModel()
        return ConfigModel(
            theme=data.get("theme", defaults.theme),
            hotkey_modifier=data.get("hotkey_modifier", defaults.hotkey_modifier),
            hotkey_key=data.get("hotkey_key", defaults.hotkey_key),
            index_roots=data.get("index_roots", defaults.index_roots),
            excluded_paths=data.get("excluded_paths", defaults.excluded_paths),
            launch_on_startup=data.get("launch_on_startup", defaults.launch_on_startup),
            animations_enabled=data.get("animations_enabled", defaults.animations_enabled),
            max_results=data.get("max_results", defaults.max_results),
        )
