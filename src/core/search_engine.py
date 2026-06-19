"""
SearchEngine turns a raw query string into a ranked list of SearchResult
objects. It does NOT touch the UI or the filesystem directly — it asks
CacheManager for SQL-prefiltered candidates, then re-ranks them with
fuzzy matching for typo/partial tolerance.

The SQL LIKE prefilter matters for performance: with a large index,
running RapidFuzz over every row would be slow. LIKE narrows it to a
few hundred plausible rows first, and only those get fuzzy-scored.
"""

from __future__ import annotations

import os
from typing import List

from rapidfuzz import fuzz

from core.cache_manager import CacheManager
from models.result_model import SearchResult
from utils.constants import (
    CATEGORY_APP,
    CATEGORY_FILE,
    CATEGORY_FOLDER,
    CATEGORY_HISTORY,
    FUZZY_SCORE_THRESHOLD,
    MAX_RESULTS_DISPLAYED,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# How many raw SQL candidates to pull per source before fuzzy-ranking.
# Wider than MAX_RESULTS_DISPLAYED so good matches aren't missed just
# because LIKE returned them in a less-than-ideal order.
_CANDIDATE_POOL_SIZE = 200

# Fuzzy match weighting per source — history gets a small boost so
# "things you've opened before" edge out a same-scored cold file.
_HISTORY_BOOST = 6.0
_APP_BOOST = 3.0


class SearchEngine:
    def __init__(self, cache: CacheManager):
        self.cache = cache

    def search(self, query: str, limit: int = MAX_RESULTS_DISPLAYED) -> List[SearchResult]:
        query = query.strip()
        if not query:
            return []

        # The SQL LIKE prefilter must stay LOOSE or it defeats fuzzy
        # matching entirely: using the full query as a literal substring
        # means a single typo (e.g. "chme" instead of "chem") causes
        # LIKE to find zero rows, so RapidFuzz never even gets a chance
        # to score anything. Using just the first 1-2 characters keeps
        # the candidate pool wide (typos at the very start of a word are
        # rare) while still being far cheaper than scanning every row.
        prefilter_len = 1 if len(query) <= 2 else 2
        like_fragment = query[:prefilter_len]

        results: list[SearchResult] = []
        results.extend(self._search_apps(query, like_fragment))
        results.extend(self._search_files(query, like_fragment))
        results.extend(self._search_history(query, like_fragment))

        # Deduplicate by path, keeping the highest-scored instance
        # (the same path can appear in both files and history).
        best_by_path: dict[str, SearchResult] = {}
        for r in results:
            existing = best_by_path.get(r.path)
            if existing is None or r.score > existing.score:
                best_by_path[r.path] = r

        ranked = sorted(best_by_path.values(), key=SearchResult.sort_key)
        return ranked[:limit]

    # -- per-source search --------------------------------------------------

    def _search_apps(self, query: str, like_fragment: str) -> List[SearchResult]:
        rows = self.cache.search_apps(like_fragment, _CANDIDATE_POOL_SIZE)
        out = []
        for row in rows:
            score = fuzz.WRatio(query, row["name"])
            if score < FUZZY_SCORE_THRESHOLD:
                continue
            out.append(
                SearchResult(
                    title=row["name"],
                    path=row["path"],
                    category=CATEGORY_APP,
                    subtitle="Application",
                    score=score + _APP_BOOST,
                    icon_path=row["icon_path"],
                )
            )
        return out

    def _search_files(self, query: str, like_fragment: str) -> List[SearchResult]:
        rows = self.cache.search_files(like_fragment, _CANDIDATE_POOL_SIZE)
        out = []
        for row in rows:
            score = fuzz.WRatio(query, row["name"])
            if score < FUZZY_SCORE_THRESHOLD:
                continue
            is_dir = bool(row["is_dir"])
            out.append(
                SearchResult(
                    title=row["name"],
                    path=row["path"],
                    category=CATEGORY_FOLDER if is_dir else CATEGORY_FILE,
                    subtitle=row["parent_dir"],
                    score=score,
                    is_directory=is_dir,
                )
            )
        return out

    def _search_history(self, query: str, like_fragment: str) -> List[SearchResult]:
        rows = self.cache.search_history(like_fragment, _CANDIDATE_POOL_SIZE)
        out = []
        for row in rows:
            score = fuzz.WRatio(query, row["title"])
            if score < FUZZY_SCORE_THRESHOLD:
                continue
            out.append(
                SearchResult(
                    title=row["title"],
                    path=row["path"],
                    category=row["category"],
                    subtitle="Recently used",
                    score=score + _HISTORY_BOOST,
                )
            )
        return out

    def recent_items(self, limit: int = MAX_RESULTS_DISPLAYED) -> List[SearchResult]:
        """Used for the empty-state list (no query typed yet)."""
        rows = self.cache.recent_history(limit)
        return [
            SearchResult(
                title=row["title"],
                path=row["path"],
                category=row["category"],
                subtitle="Recent",
                score=0.0,
                is_directory=os.path.isdir(row["path"]) if os.path.exists(row["path"]) else False,
            )
            for row in rows
        ]
