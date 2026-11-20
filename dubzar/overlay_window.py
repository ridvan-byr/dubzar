"""The on-screen subtitle window: frameless, always on top, click-through, never takes focus.

It follows a live ``Settings`` object: colors, size, position, screen and the
subtitles on/off switch all apply the moment they change.
"""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from dubzar.models import Cue
from dubzar.overlay import SubtitleTimeline, foreground_monitor_origin, pick_screen_index
from dubzar.settings import Settings
from dubzar.ui.controller import SANS_FAMILIES, first_available
from dubzar.ui.fonts import load_bundled_fonts

TICK_MS = 100
SCREEN_WIDTH_FRACTION = 0.8
EDGE_MARGIN_FRACTION = 0.06
PAD_X, PAD_Y = 18, 8     # inside the box, around the text (must match the stylesheet)


class OverlayWindow(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._timeline = SubtitleTimeline()
        self._preview: str | None = None
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        load_bundled_fonts()  # before the stylesheet names the family
        self._label = QLabel(alignment=Qt.AlignCenter, wordWrap=True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        self._restyle()
        settings.on_change(self._on_setting_changed)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)
        self._timer.start(TICK_MS)

    @property
    def text(self) -> str:
        return self._label.text()

    @property
    def label_style(self) -> str:
        return self._label.styleSheet()

    def set_preview(self, text: str | None) -> None:
        """Show ``text`` until cleared (``None``), e.g. while the settings panel is open."""
        self._preview = text
        self.tick()

    def show_cue(self, cue: Cue, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._timeline.show(cue, now)
        self.tick(now)

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        text = self._preview if self._preview is not None else self._timeline.current(now)
        if text is None or not self._settings.subtitles_enabled:
            self._label.setText("")
            self.hide()
            return
        if text != self._label.text() or not self.isVisible():
            self._label.setText(text)
            self._place()
            self.show()

    def _on_setting_changed(self, name: str) -> None:
        self._restyle()
        if name == "subtitles_enabled":
            self.tick()
        elif self.isVisible():
            self._place()

    def _restyle(self) -> None:
        s = self._settings
        bg = QColor(s.background_color)
        self._label.setStyleSheet(
            f"color: {s.text_color}; background: rgba({bg.red()}, {bg.green()}, {bg.blue()}, "
            f"{s.background_opacity / 100:g}); border-radius: 10px; padding: {PAD_Y}px {PAD_X}px; "
            f"font-family: '{first_available(SANS_FAMILIES)}'; font-size: {s.font_size}px; font-weight: 600;"
        )

    def _box_width(self, max_width: int) -> int:
        """The box hugs its text (like a video subtitle) instead of spanning the screen; long text wraps at max_width."""
        font = QFont(first_available(SANS_FAMILIES))
        font.setPixelSize(self._settings.font_size)
        font.setWeight(font.Weight.DemiBold)
        metrics = QFontMetrics(font)
        inner = max_width - 2 * PAD_X
        wrapped = metrics.boundingRect(QRect(0, 0, inner, 10_000), Qt.TextWordWrap | Qt.AlignCenter, self._label.text())
        return min(max_width, wrapped.width() + 2 * PAD_X + 4)  # +4: slack so the last word never wraps by a pixel

    def _place(self) -> None:
        screens = QGuiApplication.screens()  # index 0 is the primary screen
        origins = [(s.geometry().x(), s.geometry().y()) for s in screens]
        index = pick_screen_index(origins, foreground_monitor_origin(), self._settings.screen)
        screen = screens[index].geometry()
        self._label.setFixedWidth(self._box_width(int(screen.width() * SCREEN_WIDTH_FRACTION)))
        self.adjustSize()
        margin = int(screen.height() * EDGE_MARGIN_FRACTION)
        room = max(0, screen.height() - self.height() - 2 * margin)
        self.move(screen.x() + (screen.width() - self.width()) // 2,
                  screen.y() + margin + int(self._settings.vertical * room))


def _demo() -> None:
    """Show sample subtitles for a few seconds: python -m dubzar.overlay_window"""
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = OverlayWindow(Settings())
    window.show_cue(Cue("demo", "", "Merhaba, bu bir altyazı denemesidir.", 4.0))
    QTimer.singleShot(5500, app.quit)
    app.exec()


if __name__ == "__main__":
    _demo()
