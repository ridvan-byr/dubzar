"""Global hotkey parsing and registration through the Windows API."""

import ctypes
import sys
import threading
from typing import Callable

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8
_MODIFIERS = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "shift": MOD_SHIFT, "alt": MOD_ALT, "win": MOD_WIN}


def parse_hotkey(text: str) -> tuple[int, int]:
    """Turn ``"Ctrl+Shift+D"`` into ``(modifier_flags, virtual_key_code)``.

    At least one modifier is required: a bare key as a global hotkey would swallow typing.
    Keys: A-Z, 0-9, F1-F12. Raises ValueError for anything else.
    """
    parts = [p.strip() for p in str(text).split("+")]
    if len(parts) < 2 or not all(parts):
        raise ValueError(f"hotkey needs at least one modifier and a key, got {text!r}")
    *mods, key = parts
    flags = 0
    for mod in mods:
        if mod.lower() not in _MODIFIERS:
            raise ValueError(f"unknown modifier {mod!r} in {text!r}")
        flags |= _MODIFIERS[mod.lower()]
    key = key.upper()
    if len(key) == 1 and (key.isascii() and key.isalnum()):
        return flags, ord(key)
    if key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 12:
        return flags, 0x70 + int(key[1:]) - 1
    raise ValueError(f"unsupported key {key!r} in {text!r}")


_WM_HOTKEY, _WM_QUIT, _WM_USER, _PM_NOREMOVE, _MOD_NOREPEAT = 0x0312, 0x0012, 0x0400, 0x0000, 0x4000


class GlobalHotkey:
    """Owns one system-wide hotkey. ``on_press`` is called on the hotkey thread.

    ``start`` returns False (instead of raising) when another program already owns
    the combination, so the app can tell the user to pick another one.
    """

    def __init__(self, on_press: Callable[[], None]):
        self._on_press = on_press
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self.registered = False

    def start(self, hotkey: str) -> bool:
        modifiers, key = parse_hotkey(hotkey)
        self.stop()
        if sys.platform != "win32":
            return False
        outcome: dict = {}
        ready = threading.Event()

        def loop() -> None:
            from ctypes import wintypes

            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, _WM_USER, _WM_USER, _PM_NOREMOVE)  # creates the queue
            outcome["thread_id"] = kernel32.GetCurrentThreadId()
            outcome["ok"] = bool(user32.RegisterHotKey(None, 1, modifiers | _MOD_NOREPEAT, key))
            ready.set()
            if not outcome["ok"]:
                return
            try:
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    if msg.message == _WM_HOTKEY:
                        self._on_press()
            finally:
                user32.UnregisterHotKey(None, 1)

        self._thread = threading.Thread(target=loop, name="dubzar-hotkey", daemon=True)
        self._thread.start()
        ready.wait(2)
        self._thread_id = outcome.get("thread_id")
        self.registered = bool(outcome.get("ok"))
        return self.registered

    def stop(self) -> None:
        thread, thread_id = self._thread, self._thread_id
        self._thread, self._thread_id, self.registered = None, None, False
        if thread is not None and thread.is_alive() and thread_id:
            ctypes.windll.user32.PostThreadMessageW(thread_id, _WM_QUIT, 0, 0)
            thread.join(2)
