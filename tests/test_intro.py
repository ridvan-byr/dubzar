import os
import re
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

pytest.importorskip("PySide6.QtQuick")

from pathlib import Path  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from dubzar.ui.intro import IntroWindow  # noqa: E402

UI = Path(__file__).resolve().parents[1] / "dubzar" / "ui"


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def wait_until(condition, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.005)
    return condition()


def test_logo_layers_share_one_viewbox_so_they_stack_exactly():
    boxes = {name: re.search(r'viewBox="([^"]+)"', (UI / name).read_text(encoding="utf-8")).group(1)
             for name in ("dubzar-logo.svg", "dubzar-logo-d.svg", "dubzar-logo-word.svg")}

    assert len(set(boxes.values())) == 1, boxes


def test_d_layer_has_no_letters_and_word_layer_has_no_d():
    d_only = (UI / "dubzar-logo-d.svg").read_text(encoding="utf-8")
    word_only = (UI / "dubzar-logo-word.svg").read_text(encoding="utf-8")

    assert d_only.count("<path") == 1 and "#FFB224" in d_only and "#F7F5F0" not in d_only
    assert word_only.count("<path") == 1 and "#F7F5F0" in word_only and "#FFB224" not in word_only


def test_intro_plays_the_reveal_in_order_and_then_hides(qapp):
    intro = IntroWindow(animations=True, time_scale=0.04)

    intro.show_hint("ile ayarları aç", keys=["Ctrl", "Shift", "D"], hold_ms=100)
    assert intro.view.isVisible()
    assert intro.progress("dP") < 1.0  # the D has not finished appearing yet

    assert wait_until(lambda: intro.progress("dP") >= 0.99)
    assert intro.progress("wP") < 1.0 or intro.progress("dP") >= 0.99  # D first, letters later
    assert wait_until(lambda: intro.progress("wP") >= 0.99)
    assert wait_until(lambda: intro.progress("hP") >= 0.99)  # then the hint
    assert wait_until(lambda: not intro.view.isVisible())


def test_letters_start_after_the_d(qapp):
    intro = IntroWindow(animations=True, time_scale=1.0)
    intro.show_hint("x", hold_ms=100)

    # at 40% of the D's own duration the letters must not have started moving
    assert wait_until(lambda: 0.2 < intro.progress("dP") < 0.95, 1.0)
    assert intro.progress("wP") == 0.0
    intro.hide()


def test_reduced_motion_shows_the_final_state_at_once_and_hides_after_the_hold(qapp):
    intro = IntroWindow(animations=False, time_scale=1.0)

    intro.show_hint("ile ayarları aç", hold_ms=80)

    assert all(intro.progress(p) == 1.0 for p in ("dP", "wP", "fP", "hP"))
    assert intro.view.isVisible()
    assert wait_until(lambda: not intro.view.isVisible())


def test_intro_exposes_the_message_and_keys(qapp):
    intro = IntroWindow(animations=False)

    intro.show_hint("ile ayarları aç", keys=["Ctrl", "Shift", "D"], hold_ms=5000)

    assert intro.message == "ile ayarları aç"
    assert intro.keys == ["Ctrl", "Shift", "D"]
    intro.hide()


def test_showing_again_restarts_the_animation(qapp):
    intro = IntroWindow(animations=True, time_scale=0.04)
    intro.show_hint("x", hold_ms=2000)
    assert wait_until(lambda: intro.progress("hP") >= 0.99)

    intro.show_hint("y", hold_ms=2000)

    assert intro.progress("dP") < 1.0 and intro.message == "y"
    intro.hide()


def test_closing_the_intro_unloads_its_qml_so_shutdown_prints_no_errors(qapp):
    """Quitting used to print a wall of 'Cannot read property ... of null' from Intro.qml: the model was destroyed
    while the view still evaluated bindings against it."""
    from PySide6.QtCore import QCoreApplication, qInstallMessageHandler

    from dubzar.ui.intro import IntroWindow

    messages = []
    previous = qInstallMessageHandler(lambda mode, context, message: messages.append(message))
    try:
        window = IntroWindow(animations=True)
        window.show_hint("ile ayarları aç", "auto", keys=["Ctrl", "Shift", "D"])
        QCoreApplication.processEvents()
        window.close()
        window._model = None                      # what tearing the objects down at exit does
        for _ in range(5):
            QCoreApplication.processEvents()
    finally:
        qInstallMessageHandler(previous)

    assert not [m for m in messages if "TypeError" in m], messages
