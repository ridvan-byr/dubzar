"""Background scan: grows the index while the game is not running."""

import threading
from typing import Callable

import psutil

from dubzar.asr import Transcriber
from dubzar.index import IndexStore
from dubzar.scan import scan_folder
from dubzar.translate import Translator


def is_process_running(name: str) -> bool:
    """True when a process with this executable name (case-insensitive) is running."""
    wanted = name.lower()
    return any((p.info["name"] or "").lower() == wanted for p in psutil.process_iter(["name"]))


class BackgroundScanner:
    """Runs ``scan_folder`` on a worker thread and waits whenever the game process is running.

    Without a ``game_exe`` it does nothing: we cannot tell when the game is open, and a scan
    that competes with the game is exactly what this design avoids.
    The models are created inside the worker (loading them is slow) and the worker opens its
    own index connection.
    """

    def __init__(self, folder: str, store_path: str,
                 make_transcriber: Callable[[], Transcriber], make_translator: Callable[[], Translator],
                 game_exe: str | None, on_progress: Callable[[int, int], None],
                 is_running: Callable[[str], bool] = is_process_running, poll_s: float = 2.0):
        self._folder = folder
        self._store_path = store_path
        self._make_transcriber = make_transcriber
        self._make_translator = make_translator
        self._game_exe = game_exe
        self._on_progress = on_progress
        self._is_running = is_running
        self._poll_s = poll_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._progress = (0, 0)

    @property
    def progress(self) -> tuple[int, int]:
        """(files looked at, files in total); (0, 0) until the scan has begun."""
        return self._progress

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self._game_exe is None or self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="dubzar-background-scan", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(2)

    def _report(self, done: int, total: int) -> None:
        self._progress = (done, total)
        self._on_progress(done, total)

    def _run(self) -> None:
        store = IndexStore(self._store_path)
        try:
            scan_folder(
                self._folder, store, self._make_transcriber(), self._make_translator(),
                on_progress=self._report,
                should_pause=lambda: self._is_running(self._game_exe),
                pause_poll_s=self._poll_s,
                stop_event=self._stop,
            )
        finally:
            store.close()
