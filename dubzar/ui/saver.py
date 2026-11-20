from pathlib import Path

from PySide6.QtCore import QTimer

from dubzar.settings import Settings, save_settings


class SettingsSaver:
    """Writes the settings file shortly after the last change (dragging a slider is one write)."""

    def __init__(self, settings: Settings, path: Path | str | None = None, delay_ms: int = 500):
        self._settings = settings
        self._path = path
        self._pending = False
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self.flush)
        settings.on_change(self._schedule)

    def _schedule(self, _name: str) -> None:
        self._pending = True
        self._timer.start()

    def flush(self) -> None:
        """Save now if anything changed since the last save."""
        self._timer.stop()
        if self._pending:
            self._pending = False
            save_settings(self._settings, self._path)
