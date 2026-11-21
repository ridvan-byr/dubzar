"""Looking at the screen: which monitor the game is on, a screenshot of its subtitle area, and hiding our own
windows from screenshots (so the Turkish subtitle we draw is never read back as if the game had shown it)."""

import ctypes
import sys
from ctypes import wintypes

import numpy as np

WDA_EXCLUDEFROMCAPTURE = 0x11   # Windows 10 2004 and later
BAND_X = (0.06, 0.94)           # the subtitle area: the lower part of the monitor, nearly its full width
BAND_Y = (0.58, 1.00)           # down to the very edge: some games put the last line almost on it
BLACK_MEAN, BLACK_STD = 2.0, 2.0


def _user32():
    """Our own handle to user32: ``ctypes.windll.user32`` is shared, and another module may have given its
    functions argument types that clash with the ones used here."""
    return ctypes.WinDLL("user32")


def band_box(monitor: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, right, bottom = monitor
    width, height = right - left, bottom - top
    return (left + int(width * BAND_X[0]), top + int(height * BAND_Y[0]),
            left + int(width * BAND_X[1]), top + int(height * BAND_Y[1]))


CORNER_X = ((0.02, 0.38), (0.62, 0.98))     # top left and top right: quest goals, objectives, notices
CORNER_Y = (0.03, 0.30)


def corner_boxes(monitor: tuple[int, int, int, int]) -> list[tuple[int, int, int, int]]:
    left, top, right, bottom = monitor
    width, height = right - left, bottom - top
    return [(left + int(width * x0), top + int(height * CORNER_Y[0]),
             left + int(width * x1), top + int(height * CORNER_Y[1])) for x0, x1 in CORNER_X]


def is_black(frame: np.ndarray) -> bool:
    """A frame that is entirely dark and flat: capture is blocked (some exclusive-fullscreen modes), not a dark scene."""
    return float(frame.mean()) < BLACK_MEAN and float(frame.std()) < BLACK_STD


def foreground_monitor_rect() -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) in pixels of the monitor showing the foreground window."""
    if sys.platform != "win32":
        return None

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD)]

    user32 = _user32()
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    r = info.rcMonitor
    return r.left, r.top, r.right, r.bottom


def grab(box: tuple[int, int, int, int]) -> np.ndarray:
    """RGB screenshot of ``box`` (screen pixels, may be on any monitor)."""
    from PIL import ImageGrab

    return np.asarray(ImageGrab.grab(bbox=box, all_screens=True).convert("RGB"))


def exclude_from_capture(hwnd: int) -> bool:
    """Make a window of ours invisible to screenshots and recordings (it still shows on the monitor)."""
    if sys.platform != "win32":
        return False
    user32 = _user32()
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))


def game_in_front(game_exe: str | None, process: str | None, fullscreen: bool) -> bool:
    """Is the game what the user is looking at? By process name when we know it, otherwise by a window that
    fills its monitor (we must not read a terminal or browser as if it were a game's subtitles)."""
    if game_exe:
        return process is not None and process.lower() == game_exe.lower()
    return fullscreen


def _foreground_hwnd():
    user32 = _user32()
    user32.GetForegroundWindow.restype = wintypes.HWND
    return user32.GetForegroundWindow()


def foreground_process_name() -> str | None:
    if sys.platform != "win32":
        return None
    import psutil

    hwnd = _foreground_hwnd()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    _user32().GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        return psutil.Process(pid.value).name()
    except psutil.Error:
        return None


def foreground_is_fullscreen() -> bool:
    """The foreground window covers its whole monitor (exclusive or borderless fullscreen)."""
    if sys.platform != "win32":
        return False
    hwnd = _foreground_hwnd()
    monitor = foreground_monitor_rect()
    if not hwnd or monitor is None:
        return False
    rect = wintypes.RECT()
    if not _user32().GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    return (rect.left, rect.top, rect.right, rect.bottom) == monitor or (
        rect.left <= monitor[0] and rect.top <= monitor[1] and rect.right >= monitor[2] and rect.bottom >= monitor[3])
