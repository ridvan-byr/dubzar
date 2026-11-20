import sys
import threading
import time

import pytest

from dubzar.hotkey import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, GlobalHotkey, parse_hotkey


def test_parse_ctrl_shift_d():
    assert parse_hotkey("Ctrl+Shift+D") == (MOD_CONTROL | MOD_SHIFT, ord("D"))


def test_parse_is_case_and_space_insensitive():
    assert parse_hotkey("ctrl + alt + f9") == (MOD_CONTROL | MOD_ALT, 0x78)
    assert parse_hotkey("WIN+1") == (MOD_WIN, ord("1"))


@pytest.mark.parametrize("bad", ["D", "Ctrl", "Ctrl+", "+D", "Ctrl+Shift", "Super+D", "Ctrl+F13", "Ctrl+Ö", "Ctrl+Space", ""])
def test_parse_rejects_unusable_hotkeys(bad):
    with pytest.raises(ValueError):
        parse_hotkey(bad)


pytestmark_win = pytest.mark.skipif(sys.platform != "win32", reason="uses the Windows hotkey API")
UNLIKELY = "Ctrl+Alt+Shift+F12"


@pytestmark_win
def test_registers_and_releases_a_global_hotkey():
    hotkey = GlobalHotkey(lambda: None)

    assert hotkey.start(UNLIKELY) is True
    assert hotkey.registered
    hotkey.stop()
    assert not hotkey.registered

    again = GlobalHotkey(lambda: None)  # released, so another owner can take it
    assert again.start(UNLIKELY) is True
    again.stop()


@pytestmark_win
def test_second_owner_of_the_same_hotkey_is_told_it_failed_not_crashed():
    first, second = GlobalHotkey(lambda: None), GlobalHotkey(lambda: None)
    assert first.start(UNLIKELY)

    assert second.start(UNLIKELY) is False
    assert not second.registered

    first.stop()


@pytestmark_win
def test_changing_the_hotkey_moves_the_registration():
    hotkey = GlobalHotkey(lambda: None)
    assert hotkey.start("Ctrl+Alt+Shift+F11")

    assert hotkey.start("Ctrl+Alt+Shift+F12")
    probe = GlobalHotkey(lambda: None)
    assert probe.start("Ctrl+Alt+Shift+F11")  # the old one was released

    probe.stop()
    hotkey.stop()


@pytestmark_win
@pytest.mark.slow
def test_pressing_the_hotkey_calls_the_callback():
    """Injects real key events (Ctrl+Alt+Shift+F12). Run with: pytest -m slow"""
    import ctypes

    pressed = threading.Event()
    hotkey = GlobalHotkey(pressed.set)
    assert hotkey.start(UNLIKELY)
    keybd = ctypes.windll.user32.keybd_event
    keys = [0x11, 0x12, 0x10, 0x7B]  # Ctrl, Alt, Shift, F12
    for vk in keys:
        keybd(vk, 0, 0, 0)
    time.sleep(0.05)
    for vk in reversed(keys):
        keybd(vk, 0, 2, 0)  # KEYEVENTF_KEYUP

    assert pressed.wait(2)
    hotkey.stop()
