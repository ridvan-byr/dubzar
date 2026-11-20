import sys

import numpy as np
import pytest

from dubzar.screen import band_box, is_black


def test_band_covers_the_lower_middle_of_the_monitor():
    left, top, right, bottom = band_box((1920, 0, 3840, 1080))   # a second monitor to the right

    assert left == 1920 + 192 and right == 1920 + 1728
    assert 0.6 * 1080 <= top < bottom <= 1080


def test_band_works_for_a_monitor_left_of_the_primary():
    left, top, right, bottom = band_box((-1920, 0, 0, 1080))

    assert -1920 < left < right < 0


def test_black_frame_detection():
    assert is_black(np.zeros((100, 300, 3), dtype=np.uint8))
    assert not is_black(np.full((100, 300, 3), 60, dtype=np.uint8))
    noisy = np.random.default_rng(0).integers(0, 255, (100, 300, 3), dtype=np.uint8)
    assert not is_black(noisy)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_windows_helpers_do_not_crash():
    from dubzar.screen import exclude_from_capture, foreground_monitor_rect, grab

    rect = foreground_monitor_rect()
    assert rect is None or (rect[2] > rect[0] and rect[3] > rect[1])
    if rect is not None:
        frame = grab(band_box(rect))
        assert frame.ndim == 3 and frame.shape[2] == 3
    assert isinstance(exclude_from_capture(0), bool)   # a bad handle is refused, not fatal


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_foreground_queries_do_not_crash():
    from dubzar.screen import foreground_is_fullscreen, foreground_process_name

    name = foreground_process_name()
    assert name is None or isinstance(name, str)
    assert isinstance(foreground_is_fullscreen(), bool)


def test_game_is_in_front_by_process_name_or_by_filling_the_screen():
    from dubzar.screen import game_in_front

    assert game_in_front("GTA5.exe", process="gta5.exe", fullscreen=False)          # name wins, case-insensitive
    assert not game_in_front("GTA5.exe", process="WindowsTerminal.exe", fullscreen=True)
    assert game_in_front(None, process="anything.exe", fullscreen=True)             # unknown game: fullscreen only
    assert not game_in_front(None, process="anything.exe", fullscreen=False)
