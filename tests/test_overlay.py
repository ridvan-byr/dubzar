import os

import pytest

from dubzar.models import Cue
from dubzar.overlay import (
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
    from dubzar.settings import Settings

    window = OverlayWindow(Settings())
    window.show_cue(cue("selam", 1.0), now=0.0)
    window.tick(now=0.5)
    assert window.text == "selam"

    window.tick(now=2.0)
    assert window.text == ""
    assert not window.isVisible()


def test_window_follows_settings_live(qapp):
    from dubzar.overlay_window import OverlayWindow
    from dubzar.settings import Settings

    settings = Settings()
    window = OverlayWindow(settings)
    window.show_cue(cue("selam", 60.0), now=0.0)
    window.tick(now=1.0)

    settings.text_color = "#FFD166"
    settings.background_color = "#102030"
    settings.background_opacity = 50
    settings.font_size = 40

    style = window.label_style
    assert "#FFD166" in style and "40px" in style
    assert "rgba(16, 32, 48, 0.5)" in style


def test_window_moves_with_the_vertical_setting(qapp):
    from dubzar.overlay_window import OverlayWindow
    from dubzar.settings import Settings

    settings = Settings(vertical=0.0)
    window = OverlayWindow(settings)
    window.show_cue(cue("selam", 60.0), now=0.0)
    top = window.y()

    settings.vertical = 1.0

    assert window.y() > top


def test_turning_subtitles_off_hides_the_window_and_on_brings_it_back(qapp):
    from dubzar.overlay_window import OverlayWindow
    from dubzar.settings import Settings

    settings = Settings()
    window = OverlayWindow(settings)
    window.show_cue(cue("selam", 60.0), now=0.0)
    window.tick(now=1.0)
    assert window.isVisible()

    settings.subtitles_enabled = False
    window.tick(now=1.1)
    assert not window.isVisible()

    settings.subtitles_enabled = True
    window.tick(now=1.2)
    assert window.isVisible()


def test_preview_text_stays_up_until_cleared_even_with_no_cue(qapp):
    from dubzar.overlay_window import OverlayWindow
    from dubzar.settings import Settings

    window = OverlayWindow(Settings())
    window.set_preview("Örnek altyazı")
    window.tick(now=999.0)
    assert window.text == "Örnek altyazı" and window.isVisible()

    window.set_preview(None)
    window.tick(now=999.0)
    assert not window.isVisible()


# --- screen choice -----------------------------------------------------------
from dubzar.overlay import foreground_monitor_origin, pick_screen_index  # noqa: E402

TWO_SCREENS = [(0, 0), (-1920, 0)]  # primary at the origin, a second one on its left


def test_auto_picks_the_screen_the_foreground_window_is_on():
    assert pick_screen_index(TWO_SCREENS, (-1920, 0), "auto") == 1
    assert pick_screen_index(TWO_SCREENS, (0, 0), "auto") == 0


def test_auto_falls_back_to_primary_when_the_monitor_is_unknown():
    assert pick_screen_index(TWO_SCREENS, None, "auto") == 0
    assert pick_screen_index(TWO_SCREENS, (5000, 5000), "auto") == 0


def test_primary_always_means_the_first_screen():
    assert pick_screen_index(TWO_SCREENS, (-1920, 0), "primary") == 0


def test_numbered_screen_is_one_based_and_never_crashes():
    assert pick_screen_index(TWO_SCREENS, None, "2") == 1
    assert pick_screen_index(TWO_SCREENS, None, "3") == 0  # unplugged monitor: use primary


def test_foreground_monitor_origin_is_a_point_or_none_on_this_machine():
    origin = foreground_monitor_origin()

    assert origin is None or (len(origin) == 2 and all(isinstance(v, int) for v in origin))


def test_other_screen_avoids_the_games_screen():
    assert pick_screen_index(TWO_SCREENS, (-1920, 0), "other") == 0  # game on screen 2 -> panel on primary
    assert pick_screen_index(TWO_SCREENS, (0, 0), "other") == 1      # game on primary -> panel on the other


def test_other_screen_falls_back_to_the_games_screen_when_alone():
    assert pick_screen_index([(0, 0)], (0, 0), "other") == 0
    assert pick_screen_index(TWO_SCREENS, None, "other") == 1  # game unknown: assume primary
