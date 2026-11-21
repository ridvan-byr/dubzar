"""Text in the corners of the screen (quest goals, objectives, notices): read when it changes, translated once and shown
as a small note. A cheap look at each corner decides when to read, so plain gameplay costs next to nothing."""

import hashlib
import logging
import threading
import time
from typing import Callable, Sequence

import numpy as np

from dubzar.layout import dialogue_block
from dubzar.models import Cue
from dubzar.ocr import CONFIDENT
from dubzar.screen import is_black
from dubzar.subtitle_tracker import same_subtitle, subtitle_text
from dubzar.textfix import text_quality
from dubzar.textmask import TextChangeWatcher

log = logging.getLogger(__name__)

NOTE_SHOW_S = 8.0
DICTIONARY_TRUST = 0.9
MIN_QUALITY = 0.8          # a note must be mostly real English words
POLL_S = 0.5


class RegionNoteSource:
    """``grab_regions()`` returns one picture per watched region (or None while the game is not in front)."""

    def __init__(self, grab_regions: Callable[[], Sequence[np.ndarray] | None], ocr, translator,
                 on_note: Callable[[Cue], None], poll_s: float = POLL_S, watcher_factory=TextChangeWatcher,
                 defer: Callable[[], bool] = lambda: False):
        self._grab = grab_regions
        self._ocr = ocr
        self._translator = translator
        self._on_note = on_note
        self._poll_s = poll_s
        self._factory = watcher_factory
        self._defer = defer                    # true while the subtitle band needs the reader: corners can wait
        self._watchers: list = []
        self._last: list[str | None] = []
        self._pending: list[str | None] = []
        self._memo: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ocr_calls = 0

    def set_rhythm(self, poll_s: float) -> None:
        self._poll_s = poll_s

    def poll_once(self) -> None:
        if self._defer():
            return
        frames = self._grab()
        if not frames:
            return
        while len(self._watchers) < len(frames):
            self._watchers.append(self._factory())
            self._last.append(None)
            self._pending.append(None)
        for i, frame in enumerate(frames):
            if frame is None or is_black(frame):
                continue
            changed = self._watchers[i].changed(frame)
            if not (changed or self._pending[i] is not None):
                continue                                   # nothing new there: no reading
            self._watchers[i].commit()
            self._read(i, frame)

    def _read(self, i: int, frame: np.ndarray) -> None:
        self.ocr_calls += 1
        block = sorted(dialogue_block(list(self._ocr.read(frame))), key=lambda l: l.center_y)
        text = subtitle_text([l.text for l in block])
        if text is None:
            self._pending[i] = None
            self._last[i] = None                           # the text went away: the next one is new
            return
        if text_quality(text) < MIN_QUALITY:
            self._pending[i] = None                        # garbled or not English words (a video title, a logo)
            return
        sure = all(l.confidence >= CONFIDENT for l in block) or text_quality(text) >= DICTIONARY_TRUST
        if not sure and not (self._pending[i] and same_subtitle(self._pending[i], text)):
            self._pending[i] = text                        # one doubtful sighting: look again before showing
            return
        self._pending[i] = None
        if self._last[i] is not None and same_subtitle(self._last[i], text):
            return
        self._last[i] = text
        translated = self._translate(text)
        if translated:
            log.info("köşe yazısı okundu: '%s' → '%s'", text.replace("\n", " | "), translated.replace("\n", " | "))
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
            self._on_note(Cue("corner/" + digest, text, translated, NOTE_SHOW_S))

    def _translate(self, text: str) -> str:
        parts = []
        for line in text.split("\n"):
            if line not in self._memo:
                self._memo[line] = self._translator.translate(line).strip()
                if len(self._memo) > 200:
                    self._memo.pop(next(iter(self._memo)))
            if self._memo[line]:
                parts.append(self._memo[line])
        return "\n".join(parts)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="dubzar-corners", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(2)

    def _run(self) -> None:
        while not self._stop.wait(self._poll_s):
            try:
                self.poll_once()
            except Exception:
                log.exception("corner text read failed")
