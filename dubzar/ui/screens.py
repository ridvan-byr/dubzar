from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication

from dubzar.overlay import foreground_monitor_origin, pick_screen_index


def target_screen(setting: str) -> QRect:
    """Geometry of the screen chosen by the ``screen`` setting (see ``pick_screen_index``)."""
    screens = QGuiApplication.screens()  # index 0 is the primary screen
    origins = [(s.geometry().x(), s.geometry().y()) for s in screens]
    return screens[pick_screen_index(origins, foreground_monitor_origin(), setting)].geometry()
