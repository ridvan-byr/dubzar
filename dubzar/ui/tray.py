"""The notification-area icon (bottom right of the taskbar): Dubzar runs in the background from the moment it starts, and this
is where it is reached and closed. Left click opens the settings panel; the menu can switch the subtitles and quit."""

from pathlib import Path
from typing import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from dubzar.settings import Settings

ICON_FILE = Path(__file__).with_name("dubzar.ico")


class TrayIcon:
    def __init__(self, settings: Settings, open_panel: Callable[[], None], quit_app: Callable[[], None]):
        self._settings = settings
        self.icon = QSystemTrayIcon(QIcon(str(ICON_FILE)))
        self.icon.setToolTip("Dubzar çalışıyor")
        self.menu = QMenu()
        self._open = QAction("Ayarlar")
        self._open.triggered.connect(lambda: open_panel())
        self._subtitles = QAction("Altyazı açık")
        self._subtitles.setCheckable(True)
        self._subtitles.setChecked(settings.subtitles_enabled)
        self._subtitles.toggled.connect(self._switch_subtitles)
        self._quit = QAction("Dubzar'dan çık")
        self._quit.triggered.connect(lambda: quit_app())
        for action in (self._open, self._subtitles):
            self.menu.addAction(action)
        self.menu.addSeparator()
        self.menu.addAction(self._quit)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(lambda reason: open_panel() if reason == QSystemTrayIcon.Trigger else None)
        settings.on_change(self._settings_changed)

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self.icon.show()

    def hide(self) -> None:
        self.icon.hide()

    def _switch_subtitles(self, on: bool) -> None:
        self._settings.subtitles_enabled = on

    def _settings_changed(self, name: str) -> None:
        if name == "subtitles_enabled" and self._subtitles.isChecked() != self._settings.subtitles_enabled:
            self._subtitles.setChecked(self._settings.subtitles_enabled)
