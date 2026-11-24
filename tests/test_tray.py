import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dubzar.settings import Settings
from dubzar.ui.tray import TrayIcon


def test_the_tray_menu_opens_the_panel_switches_subtitles_and_quits():
    QApplication.instance() or QApplication([])
    settings, calls = Settings(), []
    tray = TrayIcon(settings, lambda: calls.append("panel"), lambda: calls.append("quit"))

    texts = [action.text() for action in tray.menu.actions() if not action.isSeparator()]
    assert texts == ["Ayarlar", "Altyazı açık", "Dubzar'dan çık"]

    tray._open.trigger()
    tray._quit.trigger()
    assert calls == ["panel", "quit"]

    tray._subtitles.setChecked(False)
    assert settings.subtitles_enabled is False
    settings.subtitles_enabled = True                      # changed from the panel: the menu follows
    assert tray._subtitles.isChecked()
