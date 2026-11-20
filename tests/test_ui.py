import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

pytest.importorskip("PySide6.QtQuick")

from PySide6.QtCore import QPointF, QRect, Qt  # noqa: E402
from PySide6.QtQuick import QQuickItem  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from dubzar.settings import Settings, load_settings  # noqa: E402
from dubzar.ui.controller import SettingsController  # noqa: E402
from dubzar.ui.panel import PanelWindow  # noqa: E402
from dubzar.ui.saver import SettingsSaver  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def wait_until(condition, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def test_controller_setters_write_through_to_settings(qapp):
    settings = Settings()
    ctl = SettingsController(settings)

    ctl.setFontSize(36)
    ctl.setTextColor("#ffd166")
    ctl.setBackgroundOpacity(80)
    ctl.setVertical(2.5)  # out of range is clamped, not rejected
    ctl.setSubtitlesEnabled(False)

    assert (settings.font_size, settings.text_color, settings.background_opacity) == (36, "#FFD166", 80)
    assert settings.vertical == 1.0
    assert settings.subtitles_enabled is False


def test_controller_emits_changed_so_qml_bindings_refresh(qapp):
    settings = Settings()
    ctl = SettingsController(settings)
    seen = []
    ctl.changed.connect(lambda: seen.append(1))

    settings.font_size = 40

    assert seen == [1]
    assert ctl.fontSize == 40


def test_cycle_screen_visits_only_screens_that_exist(qapp):
    settings = Settings()
    ctl = SettingsController(settings, screen_count=3)

    visited = [settings.screen]
    for _ in range(4):
        ctl.cycleScreen()
        visited.append(settings.screen)

    assert visited == ["auto", "primary", "2", "3", "auto"]


def test_single_screen_cycles_between_auto_and_primary_only(qapp):
    settings = Settings()
    ctl = SettingsController(settings, screen_count=1)

    ctl.cycleScreen()
    ctl.cycleScreen()

    assert settings.screen == "auto"


def test_saver_writes_once_after_a_burst_of_changes(qapp, tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings()
    SettingsSaver(settings, path, delay_ms=50)

    for size in (30, 31, 32, 33):  # a slider drag
        settings.font_size = size
    assert not path.exists()  # nothing written mid-drag

    assert wait_until(path.exists)
    assert load_settings(path).font_size == 33


def test_saver_flush_saves_pending_changes_immediately(qapp, tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings()
    saver = SettingsSaver(settings, path, delay_ms=60_000)

    settings.dubbing_enabled = False
    saver.flush()

    assert load_settings(path).dubbing_enabled is False


def test_saver_flush_with_no_changes_writes_nothing(qapp, tmp_path):
    path = tmp_path / "settings.json"
    SettingsSaver(Settings(), path).flush()

    assert not path.exists()


@pytest.fixture
def panel(qapp):
    settings = Settings()
    ctl = SettingsController(settings, screen_count=2, animations=False)
    window = PanelWindow(ctl)
    window.show(QRect(0, 0, 1280, 720))
    wait_until(lambda: window.view.isExposed(), 1.0)
    yield window, settings
    window.view.hide()


def center_of(window, name):
    item = window.view.rootObject().findChild(QQuickItem, name)
    assert item is not None, f"no QML item named {name}"
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    return point.toPoint()


def test_panel_opens_at_the_right_edge_and_closes_with_the_escape_key(qapp, panel):
    window, _ = panel
    assert window.is_open
    assert window.view.x() + window.view.width() <= 1280

    QTest.keyClick(window.view, Qt.Key_Escape)

    assert wait_until(lambda: not window.is_open)
    assert wait_until(lambda: not window.view.isVisible())


def test_clicking_the_subtitle_toggle_turns_subtitles_off(qapp, panel):
    window, settings = panel

    QTest.mouseClick(window.view, Qt.LeftButton, Qt.NoModifier, center_of(window, "subtitleToggle"))

    assert wait_until(lambda: settings.subtitles_enabled is False)


def test_reset_button_restores_the_defaults(qapp, panel):
    window, settings = panel
    settings.font_size = 44
    settings.text_color = "#FF8FA3"
    settings.vertical = 0.1

    QTest.mouseClick(window.view, Qt.LeftButton, Qt.NoModifier, center_of(window, "resetButton"))

    assert wait_until(lambda: settings == Settings())


def test_dragging_the_position_pad_moves_the_subtitle(qapp, panel):
    window, settings = panel
    settings.vertical = 1.0
    pad = window.view.rootObject().findChild(QQuickItem, "positionPad")
    top = pad.mapToScene(QPointF(pad.width() / 2, 4)).toPoint()

    QTest.mouseClick(window.view, Qt.LeftButton, Qt.NoModifier, top)

    assert wait_until(lambda: settings.vertical < 0.3)


def test_bundled_fonts_register_and_cover_turkish_text(qapp):
    from PySide6.QtGui import QFont, QFontMetricsF

    from dubzar.ui.fonts import load_bundled_fonts

    families = load_bundled_fonts()

    assert "DM Sans" in families and "Instrument Serif" in families
    for family in ("DM Sans", "Instrument Serif"):
        metrics = QFontMetricsF(QFont(family))
        missing = [c for c in "ğĞşŞİıöÖüÜçÇâ·…" if not metrics.inFontUcs4(ord(c))]
        assert not missing, f"{family} lacks {missing}"


def test_controller_prefers_the_bundled_fonts_once_loaded(qapp):
    from dubzar.ui.fonts import load_bundled_fonts

    load_bundled_fonts()
    ctl = SettingsController(Settings())

    assert (ctl.sansFamily, ctl.serifFamily) == ("DM Sans", "Instrument Serif")


def test_font_files_ship_with_their_licenses():
    from dubzar.ui.fonts import FONT_DIR

    names = {p.name for p in FONT_DIR.iterdir()}
    assert {"DMSans.ttf", "InstrumentSerif-Italic.ttf", "OFL-DMSans.txt", "OFL-InstrumentSerif.txt"} <= names


def test_status_shows_scan_percentage_while_scanning(qapp):
    ctl = SettingsController(Settings())
    ctl.set_live(True)

    ctl.set_scan_progress(34, 100)

    assert ctl.status == "Öğreniyor 34%"


def test_status_is_live_when_nothing_is_being_scanned(qapp):
    ctl = SettingsController(Settings())

    assert ctl.status == "Dinleniyor"  # nothing running yet
    ctl.set_live(True)
    assert ctl.status == "Canlı"
    ctl.set_scan_progress(0, 0)  # a scan that has not started yet
    assert ctl.status == "Canlı"


def test_status_goes_back_to_live_when_the_scan_finishes(qapp):
    ctl = SettingsController(Settings())
    ctl.set_live(True)
    ctl.set_scan_progress(99, 100)
    assert ctl.status == "Öğreniyor 99%"

    ctl.set_scan_progress(100, 100)

    assert ctl.status == "Canlı"


def test_status_change_notifies_the_panel(qapp):
    ctl = SettingsController(Settings())
    seen = []
    ctl.changed.connect(lambda: seen.append(1))

    ctl.set_scan_progress(10, 100)

    assert seen == [1]


# --- the panel closes itself so it never stays on the screen by accident ---------------------------
def test_panel_closes_itself_after_a_period_without_interaction(qapp):
    ctl = SettingsController(Settings(), animations=False, idle_close_ms=120)
    window = PanelWindow(ctl)
    window.show(QRect(0, 0, 1280, 720))
    assert window.is_open

    assert wait_until(lambda: not window.is_open, 3.0)
    assert wait_until(lambda: not window.view.isVisible(), 3.0)


def test_using_the_panel_keeps_it_open(qapp):
    ctl = SettingsController(Settings(), animations=False, idle_close_ms=250)
    window = PanelWindow(ctl)
    window.show(QRect(0, 0, 1280, 720))

    for size in range(30, 40):  # ~0.6 s of dragging a slider: far longer than the idle limit
        ctl.setFontSize(size)
        wait_until(lambda: False, 0.06)
    assert window.is_open

    assert wait_until(lambda: not window.is_open, 3.0)  # and once the user stops, it still closes


# --- harmless Qt/Windows chatter must not bury the real messages -----------------------------------
def test_qt_geometry_chatter_is_dropped_but_real_messages_are_kept(capsys):
    from dubzar.app import qt_message_filter

    chatter = ("QWindowsWindow::setGeometry: Unable to set geometry 1536x54+192+854 on "
               "QWidgetWindow/OverlayWindowClassWindow. Resulting geometry 1920x68+192+854")
    qt_message_filter(None, None, chatter)
    qt_message_filter(None, None, "QML error: something real went wrong")

    err = capsys.readouterr().err
    assert "Unable to set geometry" not in err
    assert "something real went wrong" in err


def test_showing_the_panel_never_takes_keyboard_focus_from_the_game(qapp):
    from PySide6.QtCore import Qt

    ctl = SettingsController(Settings(), animations=False)
    window = PanelWindow(ctl)

    assert window.view.flags() & Qt.WindowDoesNotAcceptFocus


def test_panel_screen_defaults_to_the_other_screen_and_cycles(qapp):
    settings = Settings()
    ctl = SettingsController(settings, screen_count=3)

    visited = [settings.panel_screen]
    for _ in range(5):
        ctl.cyclePanelScreen()
        visited.append(settings.panel_screen)

    assert visited == ["other", "auto", "primary", "2", "3", "other"]


def test_panel_screen_rejects_nonsense():
    import pytest
    with pytest.raises(ValueError):
        Settings(panel_screen="left")
    assert Settings(panel_screen="other").panel_screen == "other"
