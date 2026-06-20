"""
A single, restrained animation: fade + slight scale-up on show, the
reverse on hide. This is the ONE motion moment in the app — used
consistently rather than adding different effects elsewhere, which is
what would start to feel AI-generated/showy rather than premium.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect
from PySide6.QtWidgets import QWidget

from utils.constants import ANIMATION_DURATION_MS


def fade_in(widget: QWidget, on_finished=None) -> QPropertyAnimation:
    effect = widget.graphicsEffect()
    widget.setWindowOpacity(0.0)

    anim = QPropertyAnimation(widget, b"windowOpacity", widget)
    anim.setDuration(ANIMATION_DURATION_MS)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    if on_finished:
        anim.finished.connect(on_finished)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def fade_out(widget: QWidget, on_finished=None) -> QPropertyAnimation:
    anim = QPropertyAnimation(widget, b"windowOpacity", widget)
    anim.setDuration(ANIMATION_DURATION_MS)
    anim.setStartValue(widget.windowOpacity())
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.Type.InCubic)
    if on_finished:
        anim.finished.connect(on_finished)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def grow_height(widget: QWidget, target_height: int) -> QPropertyAnimation:
    """Used when the results list expands the window from the
    collapsed search-bar-only height to fit the result rows."""
    start_rect = widget.geometry()
    end_rect = QRect(start_rect.x(), start_rect.y(), start_rect.width(), target_height)

    anim = QPropertyAnimation(widget, b"geometry", widget)
    anim.setDuration(ANIMATION_DURATION_MS)
    anim.setStartValue(start_rect)
    anim.setEndValue(end_rect)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim
