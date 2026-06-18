"""
Data model for a launch-history record. Used both to render the
"recent items" empty-state list and, later, to bias search ranking
toward things the user actually opens often (frecency).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HistoryEntry:
    path: str
    title: str
    category: str
    launch_count: int = 1
    last_launched_at: float = 0.0  # unix timestamp
