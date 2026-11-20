"""Live subtitles: recognise what the game says right now, show it, and remember it."""

import hashlib
import logging
import queue
import threading
from typing import Callable

from dubzar.asr import Transcriber
from dubzar.fingerprint import Matcher, fingerprint
from dubzar.index import IndexStore
from dubzar.models import Cue
from dubzar.segmenter import SR, Segment, SpeechSegmenter
from dubzar.translate import Translator

log = logging.getLogger(__name__)

MATCHER_WINDOW_S = 3.0    # how much recent audio the streaming matcher keeps (Matcher's own default)
MAX_BACKLOG = 3          # segments waiting for recognition; older ones are stale and dropped
MIN_AUDIO_S = 0.25        # shorter than this is a click or a breath, not a line
LEARN_MIN_S = 0.8         # only learn lines long enough to be recognised again reliably
LEARN_MAX_S = 12.05       # longer means the segmenter had to cut it: not a whole line


class LiveEngine:
    """Turns speech segments into subtitles.

    1. Fast path: if the index already knows the audio, use its subtitle (no model runs).
    2. Otherwise recognise and translate it, show it, and, when the recognition is confident
       and the segment looks like a whole line, learn it so the next time takes the fast path.
    Doubtful recognitions are neither shown nor learned: a wrong subtitle is worse than none.
    """

    def __init__(self, store: IndexStore, transcriber: Transcriber, translator: Translator,
                 on_cue: Callable[[Cue], None], min_confidence: float = 0.6, min_votes: int = 8):
        self._store = store
        self._transcriber = transcriber
        self._translator = translator
        self._on_cue = on_cue
        self._min_confidence = min_confidence
        self._min_votes = min_votes

    def process(self, segment: Segment) -> Cue | None:
        samples = segment.samples
        duration = len(samples) / SR
        if duration < MIN_AUDIO_S:
            return None

        hashes = fingerprint(samples)
        known = self._known_cue(samples) if hashes else None
        if known is not None:
            self._on_cue(known)
            return known

        transcription = self._transcriber.transcribe(samples)
        if transcription is None or transcription.confidence < self._min_confidence:
            return None
        text_tr = self._translator.translate(transcription.text).strip()
        if not text_tr:
            return None

        digest = hashlib.sha256(samples.tobytes()).hexdigest()
        cue = Cue("live/" + digest[:12], transcription.text, text_tr, duration)
        self._on_cue(cue)
        if hashes and LEARN_MIN_S <= duration <= LEARN_MAX_S:
            self._store.add_line(cue, hashes, digest)
        return cue

    def _known_cue(self, samples) -> Cue | None:
        result = Matcher(self._store.lookup, min_votes=self._min_votes).feed(samples)
        return self._store.get_cue(result.line_id) if result is not None else None


class LivePipeline:
    """Feeds one audio stream to both paths and keeps them from repeating each other.

    * Known lines: the streaming matcher recognises them within a few hundred milliseconds, so the
      subtitle appears while the line is still being spoken (same as ``run_matching``).
    * Unknown lines: a segmenter cuts the speech, a worker thread recognises and translates each
      segment (slow, so it never blocks the audio) and learns it for next time.
    If the matcher already showed a line during a segment, the worker's copy of it is dropped.
    Times are stream times (seconds of audio fed), so the logic does not depend on the wall clock.
    """

    def __init__(self, store: IndexStore, transcriber: Transcriber, translator: Translator,
                 on_cue: Callable[[Cue], None], min_confidence: float = 0.6):
        self._store = store
        self._on_cue = on_cue
        self._matcher = Matcher(store.lookup)
        self._segmenter = SpeechSegmenter()
        self._engine = LiveEngine(store, transcriber, translator, self._engine_cue, min_confidence)
        self._elapsed = 0.0                    # seconds of audio fed so far
        self._quiet_until: dict[str, float] = {}   # do not re-trigger a line while it is still playing
        self._instant_at: dict[str, float] = {}    # when the matcher last showed each line
        self._segments: queue.Queue = queue.Queue()
        self._current: Segment | None = None
        self._worker = threading.Thread(target=self._work, name="dubzar-live", daemon=True)
        self._worker.start()

    def feed(self, chunk) -> None:
        self._elapsed += len(chunk) / SR
        result = self._matcher.feed(chunk)
        if result is not None:
            self._matcher.reset()
            cue = self._store.get_cue(result.line_id)
            if cue is not None and self._elapsed >= self._quiet_until.get(cue.line_id, 0.0):
                self._quiet_until[cue.line_id] = self._elapsed + cue.duration_s
                self._instant_at[cue.line_id] = self._elapsed
                self._on_cue(cue)
        for segment in self._segmenter.feed(chunk):
            self._enqueue(segment)

    def close(self, timeout: float = 5.0) -> None:
        """Hand over the unfinished segment, let the worker finish what is queued, and stop it."""
        for segment in self._segmenter.flush():
            self._enqueue(segment)
        self._segments.put(None)
        self._worker.join(timeout)

    def _enqueue(self, segment: Segment) -> None:
        while self._segments.qsize() >= MAX_BACKLOG:  # recognition is behind: stale lines are not worth showing
            try:
                self._segments.get_nowait()
                log.warning("live recognition is behind; dropping an old segment")
            except queue.Empty:
                break
        self._segments.put(segment)

    def _engine_cue(self, cue: Cue) -> None:
        segment = self._current
        shown = self._instant_at.get(cue.line_id)
        if segment is not None and shown is not None and shown >= segment.start_s - 0.5:
            return  # the matcher already showed this line while it was playing
        # The matcher's buffer still holds the end of this line: without this it would match the line we
        # just showed (or just learned) and show it a second time.
        self._quiet_until[cue.line_id] = max(self._quiet_until.get(cue.line_id, 0.0), self._elapsed + MATCHER_WINDOW_S)
        self._on_cue(cue)

    def _work(self) -> None:
        while True:
            segment = self._segments.get()
            if segment is None:
                return
            self._current = segment
            try:
                self._engine.process(segment)
            except Exception:
                log.exception("live recognition failed for a segment")
