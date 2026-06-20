"""
MainWindow is the floating launcher panel itself: frameless, translucent,
rounded, centered on screen. It owns the visible widget tree (search bar
+ result list) and wires user input through to the search engine and
command runner.

It does NOT contain business logic (search ranking, indexing, etc.) —
that all lives in core/. This file's job is purely: lay out widgets,
respond to input events, and call into core/services for the actual
work.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QVBoxLayout,
    QWidget,
)

from core.cache_manager import CacheManager
from core.command_runner import CommandRunner
from core.search_engine import SearchEngine
from models.result_model import SearchResult
from services.window_service import WindowService
from ui.animations import fade_in, fade_out
from ui.result_card import ResultCard
from ui.search_bar import SearchBar
from utils.constants import (
    MAX_VISIBLE_ROWS,
    RESULT_ROW_HEIGHT,
    SEARCH_DEBOUNCE_MS,
    WINDOW_COLLAPSED_HEIGHT,
    WINDOW_WIDTH,
)
from utils.helpers import make_debouncer
from utils.logger import get_logger

logger = get_logger(__name__)

PANEL_BG = "rgba(28, 28, 32, 235)"   # near-black, slight transparency
PANEL_BORDER = "rgba(255, 255, 255, 18)"


class MainWindow(QWidget):
    def __init__(self, cache: CacheManager, search_engine: SearchEngine):
        super().__init__()
        self.cache = cache
        self.search_engine = search_engine
        self.command_runner = CommandRunner()

        self._result_cards: List[ResultCard] = []
        self._current_results: List[SearchResult] = []
        self._selected_index = 0

        self._configure_window_flags()
        self._build_ui()
        self._apply_shadow()

        self._debounce_trigger = make_debouncer(self, SEARCH_DEBOUNCE_MS)

    # -- window setup -----------------------------------------------------

    def _configure_window_flags(self) -> None:
        # FramelessWindowHint removes the title bar/borders entirely;
        # Tool hint keeps it out of the taskbar (it lives in the tray
        # instead); StaysOnTopHint is what lets Alt+Space summon it
        # over whatever app currently has focus.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(WINDOW_WIDTH)
        self.resize(WINDOW_WIDTH, WINDOW_COLLAPSED_HEIGHT)

    def _apply_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

    def _build_ui(self) -> None:
        self.setStyleSheet(
            f"""
            #panel {{
                background: {PANEL_BG};
                border: 1px solid {PANEL_BORDER};
                border-radius: 16px;
            }}
            """
        )
        self.setObjectName("panel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.search_bar = SearchBar(self)
        bar_wrapper = QWidget(self)
        bar_wrapper.setObjectName("panel")
        bar_layout = QVBoxLayout(bar_wrapper)
        bar_layout.setContentsMargins(20, 4, 20, 4)
        bar_layout.addWidget(self.search_bar)
        root.addWidget(bar_wrapper)

        self.results_container = QWidget(self)
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(8, 4, 8, 10)
        self.results_layout.setSpacing(2)
        root.addWidget(self.results_container)
        self.results_container.hide()

        self.search_bar.textChanged.connect(self._on_text_changed)

        from widgets.keyboard_handler import KeyboardHandler
        self._keyboard_handler = KeyboardHandler(
            on_move_down=self._select_next,
            on_move_up=self._select_previous,
            on_confirm=self._launch_selected,
            on_escape=self.hide_launcher,
        )
        self.search_bar.installEventFilter(self._keyboard_handler)

    # -- search flow -----------------------------------------------------

    def _on_text_changed(self, text: str) -> None:
        self._debounce_trigger(lambda: self._run_search(text))

    def _run_search(self, text: str) -> None:
        text = text.strip()
        if not text:
            results = self.search_engine.recent_items(MAX_VISIBLE_ROWS)
        else:
            results = self.search_engine.search(text, MAX_VISIBLE_ROWS)
        self._render_results(results)

    def _render_results(self, results: List[SearchResult]) -> None:
        # Clear existing cards. For up to 9 rows this rebuild is cheap
        # enough (<1ms) that a more complex diffing/reuse scheme would
        # be premature optimization here.
        for card in self._result_cards:
            card.setParent(None)
            card.deleteLater()
        self._result_cards.clear()

        self._current_results = results
        self._selected_index = 0

        if not results:
            self.results_container.hide()
            self._resize_to_content()
            return

        for i, result in enumerate(results):
            card = ResultCard(result, self.results_container)
            card.set_selected(i == 0)
            self.results_layout.addWidget(card)
            self._result_cards.append(card)

        self.results_container.show()
        self._resize_to_content()

    def _resize_to_content(self) -> None:
        row_count = len(self._current_results)
        extra = (RESULT_ROW_HEIGHT * row_count + 14) if row_count else 0
        target_height = WINDOW_COLLAPSED_HEIGHT + extra
        self.resize(WINDOW_WIDTH, target_height)

    # -- keyboard navigation -----------------------------------------------------

    def _select_next(self) -> None:
        if not self._result_cards:
            return
        self._set_selected_index((self._selected_index + 1) % len(self._result_cards))

    def _select_previous(self) -> None:
        if not self._result_cards:
            return
        self._set_selected_index((self._selected_index - 1) % len(self._result_cards))

    def _set_selected_index(self, index: int) -> None:
        if 0 <= self._selected_index < len(self._result_cards):
            self._result_cards[self._selected_index].set_selected(False)
        self._selected_index = index
        self._result_cards[index].set_selected(True)

    def _launch_selected(self) -> None:
        if not self._current_results:
            return
        result = self._current_results[self._selected_index]
        success = self.command_runner.launch(result)
        if success:
            self.cache.record_launch(result.path, result.title, result.category)
            self.hide_launcher()
        else:
            logger.warning("Could not launch selected result: %s", result.path)

    # -- show / hide -----------------------------------------------------

    def show_launcher(self) -> None:
        self.search_bar.clear_and_reset()
        self.resize(WINDOW_WIDTH, WINDOW_COLLAPSED_HEIGHT)
        self.results_container.hide()
        WindowService.show_and_focus(self)
        self.search_bar.setFocus()
        fade_in(self)
        # Pre-populate with recent items so the launcher never opens
        # to a completely empty, purposeless-looking panel.
        QTimer.singleShot(0, lambda: self._run_search(""))

    def hide_launcher(self) -> None:
        fade_out(self, on_finished=self.hide)

    def toggle_launcher(self) -> None:
        if self.isVisible():
            self.hide_launcher()
        else:
            self.show_launcher()

    def closeEvent(self, event) -> None:
        # Closing the window (e.g. Alt+F4) just hides it — the app
        # keeps running in the tray. Only the tray's Quit action or
        # QApplication.quit() actually exits.
        event.ignore()
        self.hide_launcher()
