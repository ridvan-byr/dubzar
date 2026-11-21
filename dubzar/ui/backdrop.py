"""A light dark veil over the screen while the settings panel is open (like the Steam overlay's dimming)."""

from PySide6.QtCore import QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

VEIL = QColor(0, 0, 0, 56)  # light (about a fifth): the game stays clearly visible behind it
CLEAR_MARGIN = (28, 18)     # extra room around the subtitle preview that stays free of the veil
CLEAR_RADIUS = 22
FADE_MS = 160


class Backdrop(QWidget):
    """Click-through, never takes focus, so the game keeps running and keeps its input."""

    def __init__(self, animations: bool = True):
        super().__init__()
        self._animations = animations
        self._clear = QRect()       # global rectangle kept free of the veil (the subtitle preview)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.finished.connect(self._after_fade)

    def set_clear_rect(self, rect: QRect) -> None:
        """Keep ``rect`` (global coordinates) free of the veil, so the subtitle preview is seen exactly as it will be
        in the game, over the real picture and not over a darkened one. A null rectangle removes the window."""
        self._clear = QRect(rect)
        self.update()

    def paintEvent(self, event) -> None:
        path = QPainterPath()
        path.addRect(self.rect())
        if not self._clear.isNull():
            hole = QPainterPath()
            local = self._clear.translated(-self.geometry().topLeft()).adjusted(
                -CLEAR_MARGIN[0], -CLEAR_MARGIN[1], CLEAR_MARGIN[0], CLEAR_MARGIN[1])
            hole.addRoundedRect(local, CLEAR_RADIUS, CLEAR_RADIUS)
            path = path.subtracted(hole)
        QPainter(self).fillPath(path, VEIL)

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
