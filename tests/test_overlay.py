import os

import pytest

from dubzar.models import Cue
from dubzar.overlay import (
    OverlaySettings,
    SubtitleTimeline,
    detect_exclusive_fullscreen,
    is_exclusive_fullscreen,
)


def cue(text: str = "merhaba", duration: float = 2.0) -> Cue:
    return Cue("a1", "hello", text, duration)


def test_returns_none_before_any_cue():
    assert SubtitleTimeline().current(now=0.0) is None


def test_text_visible_until_duration_plus_tail():
    timeline = SubtitleTimeline()
    timeline.show(cue(duration=2.0), now=10.0)

    assert timeline.current(now=10.0) == "merhaba"
    assert timeline.current(now=12.4) == "merhaba"
    assert timeline.current(now=12.6) is None


def test_new_cue_replaces_old_immediately():
    timeline = SubtitleTimeline()
    timeline.show(cue("ilk", 5.0), now=0.0)
    timeline.show(cue("ikinci", 1.0), now=1.0)

    assert timeline.current(now=1.1) == "ikinci"
    assert timeline.current(now=2.6) is None  # the second cue's own end, not the first's


def test_settings_defaults_and_validation():
    assert OverlaySettings() == OverlaySettings(font_size=28, position="bottom", color="#ffffff")
    with pytest.raises(ValueError):
        OverlaySettings(position="left")
    with pytest.raises(ValueError):
        OverlaySettings(font_size=0)


@pytest.mark.parametrize("state,expected", [
    (1, False), (2, False), (3, True), (4, False), (5, False), (6, False), (7, False),
])
def test_only_d3d_exclusive_state_counts_as_exclusive_fullscreen(state, expected):
    # Review Focus 1: exclusive fullscreen hides our overlay, so it must be detectable.
    assert is_exclusive_fullscreen(state) is expected


def test_detect_exclusive_fullscreen_returns_bool_on_this_machine():
    assert isinstance(detect_exclusive_fullscreen(), bool)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qtwidgets = pytest.importorskip("PySide6.QtWidgets")
    return qtwidgets.QApplication.instance() or qtwidgets.QApplication([])


def test_window_shows_cue_and_hides_it_after_its_time(qapp):
    from dubzar.overlay_window import OverlayWindow

    window = OverlayWindow(OverlaySettings())
    window.show_cue(cue("selam", 1.0), now=0.0)
    window.tick(now=0.5)
    assert window.text == "selam"

    window.tick(now=2.0)
    assert window.text == ""
    assert not window.isVisible()
