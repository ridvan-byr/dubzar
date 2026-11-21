"""Subtitles read straight from the screen: the game's own English subtitle, translated.

Exact words and exact timing (the text is on screen exactly while it is spoken) at a fraction of the cost of
listening: no speech model runs while this source finds subtitles.
"""

import hashlib
import logging
import queue
import threading
import time
from typing import Callable, Protocol, Sequence

import numpy as np

from dubzar.models import Cue
from dubzar.layout import dialogue_block
from dubzar.ocr import CONFIDENT, OcrLine, central_lines
from dubzar.screen import is_black
from dubzar.subtitle_tracker import SubtitleTracker, subtitle_text
from dubzar.textfix import text_quality
from dubzar.textmask import TextChangeWatcher
from dubzar.translate import Translator

log = logging.getLogger(__name__)

SETTLE_S = 0.04         # pause before the quick second look at something that just appeared
HEARTBEAT_S = 3.0           # read the strip at least this often even if it looks unchanged (a safety net)
BACKOFF_CAP_S = 1.5         # the longest pause between looks when readings keep finding nothing
IDLE_AFTER_S = 15.0         # no subtitle seen for this long: plain gameplay, look less often
IDLE_POLL_S = 0.3           # (a look is a screenshot, about 50 ms; subtitles are on screen for seconds)
DICTIONARY_TRUST = 0.97     # a reading this entirely made of real English words ...
TRUST_MIN_WORDS = 5         # ... and long enough not to be a fragment, is believed without a second reading
HOLD_ACTIVE_S = 8.0         # after the last subtitle was seen, keep speech recognition resting this long
BLACK_LIMIT = 10            # consecutive black frames before we conclude capture is blocked


class Reader(Protocol):
    def read(self, image: np.ndarray) -> Sequence[OcrLine]: ...


class ScreenSubtitleSource:
    def __init__(self, grab_frame: Callable[[], np.ndarray | None], ocr: Reader, translator: Translator,
                 on_cue: Callable[[Cue], None], on_clear: Callable[[], None], poll_s: float = 0.12,
                 black_limit: int = BLACK_LIMIT, clock: Callable[[], float] = time.monotonic, watcher=None):
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
        self._watcher = watcher or TextChangeWatcher()
        self._last_read_at = float("-inf")
        self._wasted = 0                        # readings in a row that found no subtitle
        self._event_at: float | None = None     # when the strip first changed for the subtitle now being waited for
        self.last_latency_s: float | None = None
        self._translations: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ocr_calls = 0
        self._pending: queue.Queue = queue.Queue()
        self._epoch = 0                         # grows when the subtitle is cleared: older queued cues are stale
        self._worker: threading.Thread | None = None

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

        now = self._clock()
        changed = self._watcher.changed(frame)             # a few milliseconds: did the text-like pixels change?
        if not changed and getattr(self._watcher, "settling", False):
            time.sleep(SETTLE_S)                           # something just appeared: is it standing still? ask now,
            again = self._grab()                           # not one poll later
            if again is not None:
                frame = again
                changed = self._watcher.changed(frame)
        if changed and self._event_at is None:
            self._event_at = now
        # Read when the strip changed, when a decision is still pending (a second sighting, or a subtitle that may
        # have gone), and now and then anyway. Never otherwise: reading costs half a second of two cores.
        if not (changed or self._tracker.unsettled or now - self._last_read_at >= HEARTBEAT_S):
            return
        reason = "değişim" if changed else "doğrulama" if self._tracker.unsettled else "nabız"
        self._watcher.commit()
        self._last_read_at = now
        self.ocr_calls += 1
        began = time.perf_counter()
        lines = list(self._ocr.read(frame))
        read_s = time.perf_counter() - began
        block = sorted(dialogue_block(central_lines(lines)), key=lambda l: l.center_y)   # the dialogue, not a HUD hint
        texts = [l.text for l in block]
        found = subtitle_text(texts) is not None
        if found:
            self._last_seen = self._clock()
        text = subtitle_text(texts)
        trusted = bool(block) and all(l.confidence >= CONFIDENT for l in block)         # the reader is sure
        if not trusted and text is not None and len(text.split()) >= TRUST_MIN_WORDS:
            trusted = text_quality(text) >= DICTIONARY_TRUST                            # or the text is plainly English
        update = self._tracker.update(texts, trusted)
        log.debug("okuma: sebep=%s, %.2f sn, satır=%d, güvenli=%s, yeni=%s, bekleyen=%s",
                  reason, read_s, len(block), trusted, bool(update.text), self._tracker.unsettled)
        if not update.text and not update.cleared and not self._tracker.unsettled:
            self._event_at = None            # a change that brought nothing new must not inflate the next delay
        if update.cleared:
            log.info("oyunun altyazısı ekrandan kalktı")
            self._epoch += 1
            self._on_clear()
            self._event_at = None
        if update.text:
            self._show(update.text)
        self._wasted = 0 if (found or self._tracker.unsettled) else self._wasted + 1

    @property
    def current_wait(self) -> float:
        """How long to pause before the next look: the normal rhythm, longer while readings keep finding nothing (a
        busy scene without subtitles must not make us read all the time)."""
        quiet = self._clock() - self._last_seen >= IDLE_AFTER_S and not self._tracker.unsettled
        base = max(self._poll_s, IDLE_POLL_S) if quiet else self._poll_s
        return min(BACKOFF_CAP_S, max(base, self._poll_s * (2 ** min(self._wasted, 4))))   # the larger, not the product

    def _show(self, text: str) -> None:
        if self._worker is not None:                       # translating takes a few tenths of a second: do it beside
            self._pending.put((text, self._epoch, self._event_at))   # the reading, so the next subtitle is read meanwhile
            self._event_at = None
            return
        self._emit(text, self._event_at)
        self._event_at = None

    def _translate_loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._pending.get(timeout=0.2)
            except queue.Empty:
                continue
            while not self._pending.empty():               # a newer subtitle is already waiting: the older one has
                item = self._pending.get_nowait()          # left the screen, skip it
            text, epoch, event_at = item
            if epoch != self._epoch:
                continue                                   # cleared since: do not show a ghost
            try:
                self._emit(text, event_at)
            except Exception:
                log.exception("subtitle translation failed")

    def _emit(self, text: str, event_at: float | None) -> None:
        translated = self._translations.get(text)
        if translated is None:
            began = time.perf_counter()
            translated = self._translator.translate(text).strip()
            log.debug("çeviri: %.2f sn (%d kelime)", time.perf_counter() - began, len(text.split()))
            self._translations[text] = translated
            if len(self._translations) > 200:
                self._translations.pop(next(iter(self._translations)))
        if not translated:
            return
        if event_at is not None:
            self.last_latency_s = self._clock() - event_at
            log.info("altyazı gecikmesi: ekranda belirdikten ~%.2f sn sonra gösterildi", self.last_latency_s)
        log.info("oyunun altyazısı okundu: '%s' → '%s'", text, translated)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        self._on_cue(Cue("ocr/" + digest, text, translated, 0.0, until_cleared=True))

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="dubzar-screen", daemon=True)
        self._worker = threading.Thread(target=self._translate_loop, name="dubzar-screen-translate", daemon=True)
        self._thread.start()
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        for thread in (self._thread, self._worker):
            if thread is not None:
                thread.join(2)

    def _run(self) -> None:
        while not self._stop.wait(self.current_wait):
            try:
                self.poll_once()
            except Exception:
                log.exception("screen subtitle read failed")
