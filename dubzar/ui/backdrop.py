"""A light dark veil over the screen while the settings panel is open (like the Steam overlay's dimming)."""

from PySide6.QtCore import QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

VEIL = QColor(0, 0, 0, 110)  # light: the game stays clearly visible behind it
FADE_MS = 160


class Backdrop(QWidget):
    """Click-through, never takes focus, so the game keeps running and keeps its input."""

    def __init__(self, animations: bool = True):
        super().__init__()
        self._animations = animations
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.finished.connect(self._after_fade)

    def paintEvent(self, event) -> None:
        QPainter(self).fillRect(self.rect(), VEIL)

    def show_on(self, screen: QRect) -> None:
        self._fade.stop()
        self.setGeometry(screen)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self.setWindowOpacity(0.0 if self._animations else 1.0)
        self.show()
        if self._animations:
            self._fade.start()

    def dismiss(self) -> None:
        self._fade.stop()
        if not self._animations or not self.isVisible():
            self.hide()
            return
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _after_fade(self) -> None:
        if self.windowOpacity() <= 0.01:
            self.hide()
