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
    dragStarted = Signal()   # the user grabbed the panel's header
    dragMoved = Signal()     # ... and moved the cursor
    activity = Signal()  # the user did something in the panel: keeps it from closing itself

    def __init__(self, settings: Settings, screen_count: int = 1, animations: bool = True,
                 status: str = "Dinleniyor", dubbing_available: bool = False, idle_close_ms: int = 0):  # 0 = the panel stays until it is closed
        super().__init__()
        self._s = settings
        self._screen_count = screen_count
        self._animations = animations
        self._status = status
        self._live = False
        self._scan = (0, 0)
        self._dubbing_available = dubbing_available
        self._idle_close_ms = idle_close_ms
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

    @Property(str, notify=changed)
    def panelScreen(self) -> str:
        return self._s.panel_screen

    @Property(list, notify=changed)
    def hotkeyParts(self) -> list:
        return self._s.hotkey.split("+")

    @Property(str, constant=True)
    def sansFamily(self) -> str:
        return first_available(SANS_FAMILIES)

    @Property(str, constant=True)
    def serifFamily(self) -> str:
        return first_available(SERIF_FAMILIES)

    @Property(int, constant=True)
    def idleCloseMs(self) -> int:
        return self._idle_close_ms

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
        """What the panel's header says: scan progress, live mode, or the idle text."""
        done, total = self._scan
        if 0 < done < total:
            return f"Öğreniyor {done * 100 // total}%"
        return "Canlı" if self._live else self._status

    def set_status(self, text: str) -> None:
        self._status = text
        self.changed.emit()

    def set_live(self, live: bool) -> None:
        self._live = live
        self.changed.emit()

    def set_scan_progress(self, done: int, total: int) -> None:
        self._scan = (done, total)
        self.changed.emit()

    @Slot(bool)
    def setSubtitlesEnabled(self, value: bool) -> None:
        self._s.subtitles_enabled = value
        self.activity.emit()

    @Slot(bool)
    def setDubbingEnabled(self, value: bool) -> None:
        self._s.dubbing_enabled = value
        self.activity.emit()

    @Slot(int)
    def setFontSize(self, value: int) -> None:
        self._s.font_size = int(value)
        self.activity.emit()

    @Slot(float)
    def setVertical(self, value: float) -> None:
        self._s.vertical = min(1.0, max(0.0, float(value)))
        self.activity.emit()

    @Slot(str)
    def setTextColor(self, value: str) -> None:
        self._s.text_color = value
        self.activity.emit()

    @Slot(str)
    def setBackgroundColor(self, value: str) -> None:
        self._s.background_color = value
        self.activity.emit()

    @Slot(int)
    def setBackgroundOpacity(self, value: int) -> None:
        self._s.background_opacity = int(value)
        self.activity.emit()

    @Slot()
    def cycleScreen(self) -> None:
        """auto -> primary -> 2 -> ... -> auto, limited to the screens that exist."""
        order = ["auto", "primary"] + [str(n) for n in range(2, self._screen_count + 1)]
        current = self._s.screen if self._s.screen in order else "auto"
        self._s.screen = order[(order.index(current) + 1) % len(order)]
        self.activity.emit()

    @Slot()
    def dragStart(self) -> None:
        self.dragStarted.emit()
        self.activity.emit()

    @Slot()
    def dragMove(self) -> None:
        self.dragMoved.emit()
        self.activity.emit()

    @Slot()
    def cyclePanelScreen(self) -> None:
        """auto -> primary -> 2 -> ... -> other -> auto, limited to the screens that exist."""
        order = ["auto", "primary"] + [str(n) for n in range(2, self._screen_count + 1)]
        if self._screen_count > 1:
            order.append("other")   # "a screen the game is not on" means nothing with a single screen
        current = self._s.panel_screen if self._s.panel_screen in order else "auto"
        self._s.panel_screen = order[(order.index(current) + 1) % len(order)]
        self.activity.emit()

    @Slot()
    def resetToDefaults(self) -> None:
        self._s.reset()
        self.activity.emit()

    @Slot()
    def close(self) -> None:
        self.closeRequested.emit()
