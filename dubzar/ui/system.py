"""Small Windows facts the UI respects."""

import ctypes
import sys


def animations_enabled() -> bool:
    """False when the user turned off Windows' "Show animations" (reduced motion)."""
    if sys.platform != "win32":
        return True
    from ctypes import wintypes

    enabled = wintypes.BOOL(1)
    ok = ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)  # SPI_GETCLIENTAREAANIMATION
    return bool(enabled.value) if ok else True
