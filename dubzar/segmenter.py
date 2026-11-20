"""Splits a live audio stream into speech segments (one per spoken line, roughly)."""

from collections import deque
from dataclasses import dataclass

import numpy as np

SR = 16000
FRAME = 160  # 10 ms
PRE_ROLL_FRAMES = 15   # context kept before the first loud frame (150 ms)
TAIL_FRAMES = 15       # context kept after the last loud frame (150 ms)


@dataclass(frozen=True)
class Segment:
    samples: np.ndarray
    start_s: float
    end_s: float


class SpeechSegmenter:
    """Energy based end-pointing for 16 kHz mono float32 audio.

    A segment starts after ``min_speech_s`` of audio above ``threshold_db``, ends after
    ``end_silence_s`` of quiet, and is cut at ``max_segment_s`` no matter what (continuous
    music or talk must not make the delay unbounded). The result does not depend on how
    the stream is split into chunks.
    """

    def __init__(self, threshold_db: float = -40.0, min_speech_s: float = 0.25,
                 end_silence_s: float = 0.45, max_segment_s: float = 12.0):
        self._threshold_db = threshold_db
        self._min_speech = round(min_speech_s * SR / FRAME)
        self._end_silence = round(end_silence_s * SR / FRAME)
        self._max_frames = round(max_segment_s * SR / FRAME)
        self._pending = np.zeros(0, dtype=np.float32)   # less than one frame, waiting for more audio
        self._frame_index = 0                            # index of the next frame to be classified
        self._preroll: deque = deque(maxlen=PRE_ROLL_FRAMES)
        self._candidate: list[np.ndarray] = []           # loud frames not yet long enough to count as speech
        self._active: list[np.ndarray] | None = None     # frames of the segment being collected
        self._active_start = 0                           # frame index where the active segment begins
        self._quiet_run = 0                              # consecutive quiet frames at the end of the active segment

    def feed(self, chunk: np.ndarray) -> list[Segment]:
        data = np.concatenate([self._pending, np.asarray(chunk, dtype=np.float32)])
        usable = (len(data) // FRAME) * FRAME
        self._pending = data[usable:]
        out: list[Segment] = []
        for start in range(0, usable, FRAME):
            self._classify(data[start:start + FRAME], out)
        return out

    def flush(self) -> list[Segment]:
        """Return the segment still being collected (if it holds enough speech) and reset."""
        out: list[Segment] = []
        if self._active is not None:
            loud = len(self._active) - self._quiet_run
            if loud >= self._min_speech:
                out.append(self._finish())
        self._reset()
        return out

    def _classify(self, frame: np.ndarray, out: list[Segment]) -> None:
        rms = float(np.sqrt(np.mean(frame * frame))) if len(frame) else 0.0
        loud = 20 * np.log10(rms + 1e-9) > self._threshold_db
        index = self._frame_index
        self._frame_index += 1

        if self._active is None:
            if loud:
                self._candidate.append(frame)
                if len(self._candidate) >= self._min_speech:
                    self._active = list(self._preroll) + self._candidate
                    self._active_start = index + 1 - len(self._active)
                    self._candidate = []
                    self._quiet_run = 0
            else:
                self._candidate = []  # a blip too short to be speech
                self._preroll.append(frame)
            return

        self._active.append(frame)
        self._quiet_run = 0 if loud else self._quiet_run + 1
        if self._quiet_run >= self._end_silence:
            if len(self._active) - self._quiet_run >= self._min_speech:  # not just the tail of a forced cut
                out.append(self._finish())
            self._reset()
        elif len(self._active) >= self._max_frames:
            out.append(self._finish())
            self._active, self._active_start, self._quiet_run = [], index + 1, 0  # keep going, no gap

    def _finish(self) -> Segment:
        frames = self._active
        excess = max(0, self._quiet_run - TAIL_FRAMES)
        if excess:
            frames = frames[:-excess]
        samples = np.concatenate(frames) if frames else np.zeros(0, dtype=np.float32)
        start = self._active_start * FRAME / SR
        return Segment(samples, start, start + len(samples) / SR)

    def _reset(self) -> None:
        self._active = None
        self._candidate = []
        self._quiet_run = 0
        self._preroll.clear()
