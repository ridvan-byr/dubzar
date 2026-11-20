"""Live subtitles: recognise what the game says right now, show it, and remember it."""

import hashlib
from typing import Callable

from dubzar.asr import Transcriber
from dubzar.fingerprint import Matcher, fingerprint
from dubzar.index import IndexStore
from dubzar.models import Cue
from dubzar.segmenter import SR, Segment
from dubzar.translate import Translator

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
