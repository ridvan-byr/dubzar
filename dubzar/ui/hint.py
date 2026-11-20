"""The small pill shown when the game starts: how to open the settings panel."""

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from dubzar.ui.screens import target_screen

FADE_IN_MS, FADE_OUT_MS, TOP_MARGIN = 160, 400, 28


class HintToast(QWidget):
    def __init__(self, animations: bool = True):
        super().__init__()
        self._animations = animations
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._label = QLabel(alignment=Qt.AlignCenter)
        self._label.setStyleSheet(
            "color: #F7F5F0; background: rgba(43, 38, 34, 0.96); border: 1px solid #4A423B;"
            "border-radius: 15px; padding: 6px 16px; font-size: 13px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    @property
    def text(self) -> str:
        return self._label.text()

    def show_hint(self, text: str, screen_setting: str = "auto", hold_ms: int = 5000) -> None:
        self._label.setText(text)
        self.adjustSize()
        screen = target_screen(screen_setting)
        self.move(screen.x() + (screen.width() - self.width()) // 2, screen.y() + TOP_MARGIN)
        self.setWindowOpacity(0.0 if self._animations else 1.0)
        self.show()
        if self._animations:
            self._animate(0.0, 1.0, FADE_IN_MS)
        self._hide_timer.start(hold_ms)

    def _fade_out(self) -> None:
        if not self._animations:
            self.hide()
            return
        self._animate(1.0, 0.0, FADE_OUT_MS)
        self._fade.finished.connect(self._hide_when_faded)

    def _hide_when_faded(self) -> None:
        self._fade.finished.disconnect(self._hide_when_faded)
        self.hide()

    def _animate(self, start: float, end: float, ms: int) -> None:
        self._fade.stop()
        self._fade.setDuration(ms)
        self._fade.setStartValue(start)
        self._fade.setEndValue(end)
        self._fade.start()
