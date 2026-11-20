"""Notices when the game starts, so the hotkey hint can pop up like NVIDIA's or Discord's."""

from typing import Callable


class GameWatcher:
    """Call ``tick()`` every few seconds; ``on_start`` fires each time the game goes from not running to running
    (including a game that is already running at the first look)."""

    def __init__(self, is_running: Callable[[], bool], on_start: Callable[[], None]):
        self._is_running = is_running
        self._on_start = on_start
        self._was_running = False

    def tick(self) -> None:
        running = self._is_running()
        if running and not self._was_running:
            self._on_start()
        self._was_running = running
