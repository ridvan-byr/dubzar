"""Subtitle timing, overlay settings and fullscreen detection (no GUI dependency)."""

import ctypes
import sys

from dubzar.models import Cue

TAIL_S = 0.5  # a subtitle stays this long after its line ends
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


def pick_screen_index(screen_origins: list[tuple[int, int]],
                      monitor_origin: tuple[int, int] | None, setting: str) -> int:
    """Index into ``screen_origins`` (top-left of each screen; index 0 is the primary).

    Never fails: an unknown monitor or a screen number that is not plugged in
    falls back to the primary screen.
    """
    if setting == "auto":
        return screen_origins.index(monitor_origin) if monitor_origin in screen_origins else 0
    if setting.isdigit() and int(setting) - 1 < len(screen_origins):
        return int(setting) - 1
    return 0


def foreground_monitor_origin() -> tuple[int, int] | None:
    """Top-left corner of the monitor the foreground window is on, or None if unknown."""
    if sys.platform != "win32":
        return None
    from ctypes import wintypes

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    return int(info.rcMonitor.left), int(info.rcMonitor.top)


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
