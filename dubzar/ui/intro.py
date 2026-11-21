"""The opening moment: the Dubzar logo reveals itself and tells the user how to open the settings."""

from pathlib import Path

from PySide6.QtCore import Property, QMetaObject, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtQuick import QQuickView

from dubzar.ui.controller import SANS_FAMILIES, first_available
from dubzar.ui.fonts import load_bundled_fonts
from dubzar.ui.screens import target_screen

QML_FILE = Path(__file__).with_name("Intro.qml")
TOP_MARGIN = 28


class IntroModel(QObject):
    """What Intro.qml reads: the hint text, the keys to show, timing and the motion preference."""

    changed = Signal()
    finished = Signal()

    def __init__(self, animations: bool, time_scale: float):
        super().__init__()
        self._animations = animations
        self._time_scale = time_scale
        self._message = ""
        self._keys: list[str] = []
        self._hold_ms = 4000

    @Property(str, notify=changed)
    def message(self) -> str:
        return self._message

    @Property(list, notify=changed)
    def keys(self) -> list:
        return self._keys

    @Property(int, notify=changed)
    def holdMs(self) -> int:
        return self._hold_ms

    @Property(bool, constant=True)
    def animations(self) -> bool:
        return self._animations

    @Property(float, constant=True)
    def timeScale(self) -> float:
        return self._time_scale

    @Property(str, constant=True)
    def sansFamily(self) -> str:
        return first_available(SANS_FAMILIES)

    def configure(self, message: str, keys: list[str], hold_ms: int) -> None:
        self._message, self._keys, self._hold_ms = message, keys, hold_ms
        self.changed.emit()

    @Slot()
    def finish(self) -> None:
        self.finished.emit()


class IntroWindow:
    """Frameless, click-through, never takes focus. ``time_scale`` < 1 speeds the animation up (tests)."""

    def __init__(self, animations: bool = True, time_scale: float = 1.0):
        load_bundled_fonts()
        self._model = IntroModel(animations, time_scale)
        self.view = QQuickView()
        self.view.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                           | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
        self.view.setColor(Qt.transparent)
        fmt = self.view.format()
        fmt.setAlphaBufferSize(8)
        self.view.setFormat(fmt)
        self.view.setResizeMode(QQuickView.SizeViewToRootObject)
        self.view.rootContext().setContextProperty("intro", self._model)
        self.view.setSource(QUrl.fromLocalFile(str(QML_FILE)))
        if self.view.status() != QQuickView.Ready:
            errors = "; ".join(e.toString() for e in self.view.errors())
            raise RuntimeError(f"intro QML failed to load: {errors}")
        self._root = self.view.rootObject()
        self._model.finished.connect(self.hide)

    @property
    def message(self) -> str:
        return self._model.message

    @property
    def keys(self) -> list[str]:
        return list(self._model.keys)

    def progress(self, name: str) -> float:
        """Animation progress 0..1 of one part: dP (D), wP (letters), fP (letter fade), hP (hint), cP (card)."""
        return float(self._root.property(name))

    def show_hint(self, message: str, screen_setting: str = "auto", hold_ms: int = 4000,
                  keys: list[str] | None = None) -> None:
        self._model.configure(message, keys or [], hold_ms)
        screen = target_screen(screen_setting)
        self.view.setPosition(screen.x() + (screen.width() - self.view.width()) // 2, screen.y() + TOP_MARGIN)
        self.view.show()
        QMetaObject.invokeMethod(self._root, "start", Qt.DirectConnection)

    def hide(self) -> None:
        QMetaObject.invokeMethod(self._root, "stop", Qt.DirectConnection)
        self.view.hide()

    def close(self) -> None:
        """Final teardown: unload the QML while its model still exists. Otherwise, as the program quits and the model
        is destroyed first, the view keeps evaluating bindings against nothing and prints a wall of errors."""
        self.view.hide()
        self.view.setSource(QUrl())
