"""Subtitles read straight from the screen: the game's own English subtitle, translated.

Exact words and exact timing (the text is on screen exactly while it is spoken) at a fraction of the cost of
listening: no speech model runs while this source finds subtitles.
"""

import hashlib
import logging
import threading
import time
from typing import Callable, Protocol, Sequence

import numpy as np

from dubzar.models import Cue
from dubzar.ocr import OcrLine
from dubzar.screen import is_black
from dubzar.subtitle_tracker import SubtitleTracker, subtitle_text
from dubzar.translate import Translator

log = logging.getLogger(__name__)

CENTER_X = (0.2, 0.8)       # subtitles sit in the middle; logos and map labels sit in the corners
HOLD_ACTIVE_S = 8.0         # after the last subtitle was seen, keep speech recognition resting this long
BLACK_LIMIT = 10            # consecutive black frames before we conclude capture is blocked
IDLE_SIGNATURE_DIFF = 0.5   # mean pixel change below this: the picture is unchanged, reuse the last OCR result


class Reader(Protocol):
    def read(self, image: np.ndarray) -> Sequence[OcrLine]: ...


class ScreenSubtitleSource:
    def __init__(self, grab_frame: Callable[[], np.ndarray | None], ocr: Reader, translator: Translator,
                 on_cue: Callable[[Cue], None], on_clear: Callable[[], None], poll_s: float = 0.35,
                 black_limit: int = BLACK_LIMIT, clock: Callable[[], float] = time.monotonic):
        self._grab = grab_frame
        self._ocr = ocr
        self._translator = translator
        self._on_cue = on_cue
        self._on_clear = on_clear
        self._poll_s = poll_s
        self._black_limit = black_limit
        self._clock = clock
        self._tracker = SubtitleTracker()
        self._black = 0
        self._last_seen = float("-inf")
        self._last_signature: np.ndarray | None = None
        self._last_lines: list[OcrLine] = []
        self._translations: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ocr_calls = 0

    @property
    def blocked(self) -> bool:
        """Screenshots of the game come back black: this source cannot work in the current display mode."""
        return self._black >= self._black_limit

    @property
    def active(self) -> bool:
        """The game has shown subtitles lately, so listening to its audio is not needed."""
        return self._clock() - self._last_seen < HOLD_ACTIVE_S

    def poll_once(self) -> None:
        frame = self._grab()
        if frame is None:
            return
        if is_black(frame):
            self._black += 1
            if self._black == self._black_limit:
                log.warning("ekran görüntüsü siyah geliyor: oyunun altyazısı okunamıyor (tam ekran modu "
                            "yakalamayı engelliyor olabilir); ses tanımaya dönülüyor")
            return
        if self._black >= self._black_limit:
            log.info("ekran görüntüsü yeniden geliyor: oyunun altyazısı okunuyor")
        self._black = 0

        lines = self._lines_for(frame)
        central = [l for l in lines if CENTER_X[0] <= l.center_x <= CENTER_X[1]]
        texts = [l.text for l in central]
        if subtitle_text(texts) is not None:
            self._last_seen = self._clock()
        update = self._tracker.update(texts)
        if update.cleared:
            log.info("oyunun altyazısı ekrandan kalktı")
            self._on_clear()
        if update.text:
            self._show(update.text)

    def _lines_for(self, frame: np.ndarray) -> list[OcrLine]:
        signature = frame[::8, ::8].astype(np.int16)
        if (self._last_signature is not None and signature.shape == self._last_signature.shape
                and float(np.abs(signature - self._last_signature).mean()) < IDLE_SIGNATURE_DIFF):
            return self._last_lines
        self.ocr_calls += 1
        lines = list(self._ocr.read(frame))
        self._last_signature, self._last_lines = signature, lines
        return lines

    def _show(self, text: str) -> None:
        translated = self._translations.get(text)
        if translated is None:
            translated = self._translator.translate(text).strip()
            self._translations[text] = translated
            if len(self._translations) > 200:
                self._translations.pop(next(iter(self._translations)))
        if not translated:
            return
        log.info("oyunun altyazısı okundu: '%s' → '%s'", text, translated)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        self._on_cue(Cue("ocr/" + digest, text, translated, 0.0, until_cleared=True))

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="dubzar-screen", daemon=True)
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
                log.exception("screen subtitle read failed")
