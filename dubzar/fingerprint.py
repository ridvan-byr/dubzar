"""Landmark audio fingerprinting and a streaming matcher.

Input audio is 16 kHz mono float32 (see ``audio.to_mono_16k``). A fingerprint is
a list of ``(hash, anchor_frame)``: spectrogram peaks are paired with nearby
later peaks and each pair is packed into a 22-bit hash. A query matches a line
when many of its hashes hit that line at one consistent time offset.
"""

from collections import Counter
from typing import Callable

import numpy as np
from scipy.ndimage import maximum_filter
from scipy.signal import stft

from dubzar.models import MatchResult

SR = 16000
NPERSEG = 512
HOP = 256  # 16 ms per frame
PEAK_NEIGHBORHOOD = (15, 7)  # (frequency bins, frames)
PEAK_FLOOR_DB = 40.0  # peaks must be within this many dB of the loudest bin
SILENCE_DB = -80.0  # below this the audio is treated as silence
MAX_DT = 48  # pair window in frames (~770 ms)
FAN_OUT = 6


def _peaks(samples: np.ndarray) -> list[tuple[int, int]]:
    """Return spectrogram peaks as (frame, freq_bin), sorted by frame."""
    if len(samples) < NPERSEG:
        return []
    _, _, z = stft(samples, fs=SR, nperseg=NPERSEG, noverlap=NPERSEG - HOP,
                   boundary=None, padded=False)
    db = 20 * np.log10(np.abs(z) + 1e-6)
    top = db.max()
    if top < SILENCE_DB:
        return []
    is_peak = (db == maximum_filter(db, size=PEAK_NEIGHBORHOOD)) & (db > top - PEAK_FLOOR_DB)
    freqs, frames = np.nonzero(is_peak)
    order = np.lexsort((freqs, frames))
    return [(int(frames[i]), int(freqs[i])) for i in order]


def fingerprint(samples: np.ndarray) -> list[tuple[int, int]]:
    """Return ``(hash, anchor_frame)`` pairs for 16 kHz mono audio."""
    peaks = _peaks(np.asarray(samples, dtype=np.float32))
    out: list[tuple[int, int]] = []
    for i, (t1, f1) in enumerate(peaks):
        paired = 0
        for t2, f2 in peaks[i + 1:]:
            dt = t2 - t1
            if dt > MAX_DT:
                break
            if dt < 1:
                continue
            out.append(((((f1 >> 1) << 14) | ((f2 >> 1) << 6) | dt), t1))
            paired += 1
            if paired >= FAN_OUT:
                break
    return out


Lookup = Callable[[list[int]], list[tuple[str, int, int]]]


class Matcher:
    """Feeds on live audio chunks and reports the indexed line being played.

    ``lookup(hashes)`` returns ``(line_id, line_anchor_frame, query_hash_index)``
    for every index entry whose hash equals ``hashes[query_hash_index]``.
    A wrong subtitle is worse than none, so ambiguous matches return ``None``.
    """

    def __init__(self, lookup: Lookup, min_votes: int = 8, window_s: float = 3.0,
                 min_audio_s: float = 0.2, margin: float = 2.0):
        self._lookup = lookup
        self._min_votes = min_votes
        self._max_samples = int(window_s * SR)
        self._min_samples = int(min_audio_s * SR)
        self._margin = margin
        self._buffer = np.zeros(0, dtype=np.float32)

    def reset(self) -> None:
        self._buffer = np.zeros(0, dtype=np.float32)

    def feed(self, samples: np.ndarray) -> MatchResult | None:
        chunk = np.asarray(samples, dtype=np.float32)
        self._buffer = np.concatenate([self._buffer, chunk])[-self._max_samples:]
        if len(self._buffer) < self._min_samples:
            return None
        query = fingerprint(self._buffer)
        if not query:
            return None
        hits = self._lookup([h for h, _ in query])
        votes: Counter[tuple[str, int]] = Counter()
        for line_id, line_anchor, qi in hits:
            votes[(line_id, line_anchor - query[qi][1])] += 1
        return self._decide(votes)

    def _decide(self, votes: Counter) -> MatchResult | None:
        best: dict[str, tuple[int, int]] = {}  # line_id -> (score, offset)
        for (line_id, delta), _ in votes.items():
            # tolerate +-1 frame of drift between query and index frame grids
            score = sum(votes.get((line_id, delta + d), 0) for d in (-1, 0, 1))
            if line_id not in best or score > best[line_id][0]:
                best[line_id] = (score, delta)
        if not best:
            return None
        ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)
        top_id, (top_score, top_delta) = ranked[0]
        if top_score < self._min_votes:
            return None
        if len(ranked) > 1 and top_score < self._margin * ranked[1][1][0]:
            return None
        return MatchResult(top_id, top_delta, top_score)
