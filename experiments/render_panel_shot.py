"""Renders the real settings panel to PNG files for the website: python experiments/render_panel_shot.py <out folder>."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication

from dubzar.settings import Settings
from dubzar.ui.controller import SettingsController
from dubzar.ui.panel import PanelWindow


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication([])
    for mode in ("light", "high"):
        settings = Settings()
        settings.performance = mode
        panel = PanelWindow(SettingsController(settings, animations=False))
        panel.show(QRect(0, 0, 1920, 1080))
        end = time.time() + 1.2
        while time.time() < end:
            app.processEvents()
        panel.view.grabWindow().save(str(out / f"panel-{mode}.png"))
        panel.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
