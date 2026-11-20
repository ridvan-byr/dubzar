"""Subtitle timing, overlay settings and fullscreen detection (no GUI dependency)."""

import ctypes
import sys
from dataclasses import dataclass

from dubzar.models import Cue

TAIL_S = 0.5  # a subtitle stays this long after its line ends
POSITIONS = ("top", "center", "bottom")
_QUNS_RUNNING_D3D_FULL_SCREEN = 3  # SHQUERYUSERNOTIFICATIONSTATE value


class SubtitleTimeline:
    """Decides which subtitle is on screen at a given time."""

    def __init__(self) -> None:
        self._text: str | None = None
        self._until = 0.0

    def show(self, cue: Cue, now: float) -> None:
        """Replace whatever is showing with ``cue``; it ends ``duration_s + TAIL_S`` later."""
        self._text = cue.text_tr
        self._until = now + cue.duration_s + TAIL_S

    def current(self, now: float) -> str | None:
        return self._text if self._text is not None and now < self._until else None


@dataclass(frozen=True)
class OverlaySettings:
    font_size: int = 28
    position: str = "bottom"
    color: str = "#ffffff"

    def __post_init__(self) -> None:
        if self.position not in POSITIONS:
            raise ValueError(f"position must be one of {POSITIONS}, got {self.position!r}")
        if self.font_size <= 0:
            raise ValueError("font_size must be positive")


def is_exclusive_fullscreen(notification_state: int) -> bool:
    """True for Windows' 'exclusive-mode Direct3D application is running' state.

    Exclusive fullscreen is the only mode our overlay window cannot appear over;
    borderless fullscreen and windowed games are fine.
    """
    return notification_state == _QUNS_RUNNING_D3D_FULL_SCREEN


def detect_exclusive_fullscreen() -> bool:
    """Ask Windows whether an exclusive-fullscreen Direct3D app is in the foreground."""
    if sys.platform != "win32":
        return False
    state = ctypes.c_int()
    if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) != 0:
        return False
    return is_exclusive_fullscreen(state.value)
