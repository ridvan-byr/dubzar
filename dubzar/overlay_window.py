"""The on-screen subtitle window: frameless, always on top, click-through, never takes focus."""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from dubzar.models import Cue
from dubzar.overlay import OverlaySettings, SubtitleTimeline

TICK_MS = 100
SCREEN_WIDTH_FRACTION = 0.8
EDGE_MARGIN_FRACTION = 0.06


class OverlayWindow(QWidget):
    def __init__(self, settings: OverlaySettings):
        super().__init__()
        self._settings = settings
        self._timeline = SubtitleTimeline()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._label = QLabel(alignment=Qt.AlignCenter, wordWrap=True)
        self._label.setStyleSheet(
            f"color: {settings.color}; background: rgba(0, 0, 0, 150);"
            f"border-radius: 8px; padding: 8px 16px; font-size: {settings.font_size}px;"
            "font-weight: 600;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)
        self._timer.start(TICK_MS)

    @property
    def text(self) -> str:
        return self._label.text()

    def show_cue(self, cue: Cue, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._timeline.show(cue, now)
        self.tick(now)

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        text = self._timeline.current(now)
        if text is None:
            self._label.setText("")
            self.hide()
            return
        if text != self._label.text() or not self.isVisible():
            self._label.setText(text)
            self._place()
            self.show()

    def _place(self) -> None:
        screen = QGuiApplication.primaryScreen().geometry()
        width = int(screen.width() * SCREEN_WIDTH_FRACTION)
        self._label.setFixedWidth(width)
        self.adjustSize()
        x = screen.x() + (screen.width() - self.width()) // 2
        margin = int(screen.height() * EDGE_MARGIN_FRACTION)
        y = {
            "top": screen.y() + margin,
            "center": screen.y() + (screen.height() - self.height()) // 2,
            "bottom": screen.y() + screen.height() - self.height() - margin,
        }[self._settings.position]
        self.move(x, y)


def _demo() -> None:
    """Show sample subtitles for a few seconds: python -m dubzar.overlay_window"""
    import ctypes
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = OverlayWindow(OverlaySettings())
    samples = ["Merhaba, bu bir altyazı denemesidir.", "İkinci satır: oyunun üstünde görünmeli."]
    state = {"i": 0}

    def next_cue():
        if state["i"] >= len(samples):
            app.quit()
            return
        window.show_cue(Cue(f"demo{state['i']}", "", samples[state["i"]], 2.0))
        if state["i"] == 0 and sys.platform == "win32":
            ex = ctypes.windll.user32.GetWindowLongW(int(window.winId()), -20) & 0xFFFFFFFF
            flags = {"TRANSPARENT": 0x20, "TOPMOST": 0x8, "LAYERED": 0x80000,
                     "NOACTIVATE": 0x08000000, "TOOLWINDOW": 0x80}
            print({name: bool(ex & bit) for name, bit in flags.items()}, flush=True)
        state["i"] += 1

    timer = QTimer()
    timer.timeout.connect(next_cue)
    timer.start(3000)
    next_cue()
    app.exec()


if __name__ == "__main__":
    _demo()
