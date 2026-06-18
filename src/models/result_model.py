"""
Data model for a single search result row.

Every search source (app index, file index, history) produces these,
so the UI layer only ever has to know about ONE shape regardless of
where the result came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from utils.constants import CATEGORY_FILE


@dataclass(slots=True)
class SearchResult:
    title: str                     # display name, e.g. "Chemistry Notes.pdf"
    path: str                      # full path or launch target
    category: str = CATEGORY_FILE  # one of CATEGORY_* in constants.py
    subtitle: str = ""             # secondary line, e.g. folder path
    score: float = 0.0             # fuzzy-match score, used for ordering
    icon_path: Optional[str] = None  # resolved lazily by the UI layer
    is_directory: bool = False
    # Free-form bag for category-specific extras (e.g. app exe args)
    # without forcing every category to carry every possible field.
    extra: dict = field(default_factory=dict)

    def sort_key(self) -> tuple:
        """Higher score first; on ties, shorter titles first (tends to
        be the more 'exact' match, e.g. 'chem.txt' over 'chemistry_2.txt')."""
        return (-self.score, len(self.title))
