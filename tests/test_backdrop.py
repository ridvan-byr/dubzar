import os

import pytest
from PySide6.QtCore import QRect

from dubzar.gamewatch import GameWatcher


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_backdrop_covers_the_given_screen_and_hides(qapp):
    from dubzar.ui.backdrop import Backdrop

    backdrop = Backdrop(animations=False)
    backdrop.show_on(QRect(100, 50, 1920, 1080))

    assert backdrop.isVisible()
    assert backdrop.geometry() == QRect(100, 50, 1920, 1080)

    backdrop.dismiss()
    assert not backdrop.isVisible()


def test_backdrop_never_takes_input_or_focus(qapp):
    from PySide6.QtCore import Qt
    from dubzar.ui.backdrop import Backdrop

    flags = Backdrop(animations=False).windowFlags()
    assert flags & Qt.WindowTransparentForInput and flags & Qt.WindowDoesNotAcceptFocus
    assert flags & Qt.WindowStaysOnTopHint


def test_watcher_fires_once_when_the_game_starts_and_again_after_a_restart():
    state = {"running": False}
    started = []
    watcher = GameWatcher(lambda: state["running"], lambda: started.append(1))

    watcher.tick(); watcher.tick()
    assert started == []

    state["running"] = True
    watcher.tick(); watcher.tick(); watcher.tick()
    assert started == [1]

    state["running"] = False
    watcher.tick()
    state["running"] = True
    watcher.tick()
    assert started == [1, 1]


def test_watcher_counts_a_game_that_is_already_running_at_the_first_look():
    started = []
    GameWatcher(lambda: True, lambda: started.append(1)).tick()
    assert started == [1]


def test_veil_is_light_so_the_game_stays_clearly_visible():
    from dubzar.ui.backdrop import VEIL

    assert VEIL.alpha() <= 70      # about a quarter: it must not hide what the user is adjusting


def test_veil_leaves_a_clear_window_around_the_subtitle_preview(qapp):
    from PySide6.QtGui import QImage
    from dubzar.ui.backdrop import Backdrop

    backdrop = Backdrop(animations=False)
    backdrop.show_on(QRect(100, 50, 800, 600))
    backdrop.set_clear_rect(QRect(300, 500, 300, 60))      # global coordinates: where the subtitle preview sits

    image = QImage(800, 600, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    backdrop.render(image)

    inside = image.pixelColor(300, 480).alpha()            # (400, 530) globally: inside the clear window
    outside = image.pixelColor(50, 50).alpha()
    assert inside == 0 and outside > 0


def test_clear_window_can_be_removed(qapp):
    from PySide6.QtGui import QImage
    from dubzar.ui.backdrop import Backdrop

    backdrop = Backdrop(animations=False)
    backdrop.show_on(QRect(0, 0, 400, 300))
    backdrop.set_clear_rect(QRect(100, 100, 100, 50))
    backdrop.set_clear_rect(QRect())

    image = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    backdrop.render(image)

    assert image.pixelColor(150, 125).alpha() > 0
