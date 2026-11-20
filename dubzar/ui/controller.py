"""Bridge between the Settings object and the QML panel."""

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QFontDatabase

from dubzar.settings import Settings


SANS_FAMILIES = ("DM Sans", "Segoe UI Variable Text", "Segoe UI", "Arial")
SERIF_FAMILIES = ("Instrument Serif", "Georgia", "Times New Roman")


def first_available(candidates: tuple[str, ...]) -> str:
    """The first installed font family from ``candidates`` (the last one if none is found)."""
    installed = set(QFontDatabase.families())
    return next((name for name in candidates if name in installed), candidates[-1])


class SettingsController(QObject):
    """Exposes ``Settings`` to QML as bindable properties.

    One ``changed`` signal drives every property: the panel is small, so re-reading
    them all on any change is cheap and keeps the bindings trivially correct.
    """

    changed = Signal()
    closeRequested = Signal()

    def __init__(self, settings: Settings, screen_count: int = 1, animations: bool = True,
                 status: str = "Dinleniyor", dubbing_available: bool = False):
        super().__init__()
        self._s = settings
        self._screen_count = screen_count
        self._animations = animations
        self._status = status
        self._dubbing_available = dubbing_available
        settings.on_change(lambda _name: self.changed.emit())

    @Property(bool, notify=changed)
    def subtitlesEnabled(self) -> bool:
        return self._s.subtitles_enabled

    @Property(bool, notify=changed)
    def dubbingEnabled(self) -> bool:
        return self._s.dubbing_enabled

    @Property(int, notify=changed)
    def fontSize(self) -> int:
        return self._s.font_size

    @Property(float, notify=changed)
    def vertical(self) -> float:
        return self._s.vertical

    @Property(str, notify=changed)
    def textColor(self) -> str:
        return self._s.text_color

    @Property(str, notify=changed)
    def backgroundColor(self) -> str:
        return self._s.background_color

    @Property(int, notify=changed)
    def backgroundOpacity(self) -> int:
        return self._s.background_opacity

    @Property(str, notify=changed)
    def screen(self) -> str:
        return self._s.screen

    @Property(list, notify=changed)
    def hotkeyParts(self) -> list:
        return self._s.hotkey.split("+")

    @Property(str, constant=True)
    def sansFamily(self) -> str:
        return first_available(SANS_FAMILIES)

    @Property(str, constant=True)
    def serifFamily(self) -> str:
        return first_available(SERIF_FAMILIES)

    @Property(bool, constant=True)
    def dubbingAvailable(self) -> bool:
        return self._dubbing_available

    @Property(int, constant=True)
    def screenCount(self) -> int:
        return self._screen_count

    @Property(bool, constant=True)
    def animations(self) -> bool:
        return self._animations

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    def set_status(self, text: str) -> None:
        self._status = text
        self.changed.emit()

    @Slot(bool)
    def setSubtitlesEnabled(self, value: bool) -> None:
        self._s.subtitles_enabled = value

    @Slot(bool)
    def setDubbingEnabled(self, value: bool) -> None:
        self._s.dubbing_enabled = value

    @Slot(int)
    def setFontSize(self, value: int) -> None:
        self._s.font_size = int(value)

    @Slot(float)
    def setVertical(self, value: float) -> None:
        self._s.vertical = min(1.0, max(0.0, float(value)))

    @Slot(str)
    def setTextColor(self, value: str) -> None:
        self._s.text_color = value

    @Slot(str)
    def setBackgroundColor(self, value: str) -> None:
        self._s.background_color = value

    @Slot(int)
    def setBackgroundOpacity(self, value: int) -> None:
        self._s.background_opacity = int(value)

    @Slot()
    def cycleScreen(self) -> None:
        """auto -> primary -> 2 -> ... -> auto, limited to the screens that exist."""
        order = ["auto", "primary"] + [str(n) for n in range(2, self._screen_count + 1)]
        current = self._s.screen if self._s.screen in order else "auto"
        self._s.screen = order[(order.index(current) + 1) % len(order)]

    @Slot()
    def resetToDefaults(self) -> None:
        self._s.reset()

    @Slot()
    def close(self) -> None:
        self.closeRequested.emit()
