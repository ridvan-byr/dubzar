"""The settings panel window: a frameless, always-on-top, focus-taking Qt Quick view."""

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QUrl
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtQuick import QQuickView

from dubzar.ui.controller import SettingsController
from dubzar.ui.fonts import load_bundled_fonts

QML_FILE = Path(__file__).with_name("Panel.qml")
EDGE = 24  # distance from the screen edge, in pixels
KEEP_VISIBLE = 80  # when dragged, at least this much of the panel stays on the desktop


class PanelWindow:
    def __init__(self, controller: SettingsController, cursor_pos=QCursor.pos):
        self._controller = controller
        self._cursor_pos = cursor_pos          # a seam: tests move a fake cursor
        self._grab: tuple[QPoint, QPoint] | None = None   # cursor and window position when the drag began
        load_bundled_fonts()  # before the QML reads the font family names
        self.view = QQuickView()
        # DoesNotAcceptFocus: showing the panel must never pull the keyboard focus away from the game
        # (a game that loses focus can minimise, pause or stall). The mouse still works when the cursor is free.
        self.view.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.view.setColor(Qt.transparent)
        fmt = self.view.format()
        fmt.setAlphaBufferSize(8)
        self.view.setFormat(fmt)
        self.view.setResizeMode(QQuickView.SizeViewToRootObject)
        self.view.rootContext().setContextProperty("ctl", controller)
        self.view.setSource(QUrl.fromLocalFile(str(QML_FILE)))
        if self.view.status() != QQuickView.Ready:
            errors = "; ".join(e.toString() for e in self.view.errors())
            raise RuntimeError(f"settings panel QML failed to load: {errors}")
        self._root = self.view.rootObject()
        self._root.closed.connect(self.view.hide)
        self._root.closed.connect(self._notify_closed)
        self._closed_callbacks: list = []
        controller.closeRequested.connect(self.hide)
        controller.dragStarted.connect(self._drag_started)
        controller.dragMoved.connect(self._drag_moved)

    def on_closed(self, callback) -> None:
        """Call ``callback()`` once the panel has finished closing."""
        self._closed_callbacks.append(callback)

    def _notify_closed(self) -> None:
        for callback in list(self._closed_callbacks):
            callback()

    @property
    def is_open(self) -> bool:
        return bool(self._root.property("open"))

    def show(self, screen: QRect) -> None:
        """Open the panel at the right edge of ``screen`` (a screen geometry)."""
        self.move_to(screen)
        self.view.show()
        self._root.setProperty("open", True)

    def move_to(self, screen: QRect) -> None:
        """Put the panel at its usual place on ``screen``, also while it is open (the screen setting changed)."""
        self.view.setPosition(screen.x() + screen.width() - self.view.width() - EDGE,
                              screen.y() + (screen.height() - self.view.height()) // 2)

    def _drag_started(self) -> None:
        self._grab = (self._cursor_pos(), QPoint(self.view.x(), self.view.y()))

    def _drag_moved(self) -> None:
        if self._grab is None:
            return
        start_cursor, start_pos = self._grab
        target = start_pos + (self._cursor_pos() - start_cursor)   # relative to the grab: no drift
        desktop = QRect()
        for screen in QGuiApplication.screens():
            desktop = desktop.united(screen.geometry())
        x = min(max(target.x(), desktop.left() - self.view.width() + KEEP_VISIBLE), desktop.right() - KEEP_VISIBLE)
        y = min(max(target.y(), desktop.top()), desktop.bottom() - KEEP_VISIBLE)
        self.view.setPosition(x, y)

    def hide(self) -> None:
        self._root.setProperty("open", False)  # the window hides when the fade-out finishes

    def toggle(self, screen: QRect) -> None:
        self.hide() if self.is_open else self.show(screen)
