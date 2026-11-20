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
