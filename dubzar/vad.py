"""Neural voice detection (Silero VAD, the model faster-whisper already ships with): tells speech from music."""

import numpy as np

WINDOW = 512     # samples per decision (32 ms at 16 kHz)
CONTEXT = 64     # the model also sees the last 64 samples of the previous window


class SileroSpeechDetector:
    """Stateful, streaming: call ``is_speech`` with consecutive 512-sample windows."""

    def __init__(self, threshold: float = 0.5):
        from faster_whisper.vad import get_vad_model

        self._session = get_vad_model().session
        self._threshold = threshold
        self.reset()

    def reset(self) -> None:
        self._h = np.zeros((1, 1, 128), dtype=np.float32)
        self._c = np.zeros((1, 1, 128), dtype=np.float32)
        self._context = np.zeros(CONTEXT, dtype=np.float32)

    def probability(self, window: np.ndarray) -> float:
        if len(window) != WINDOW:
            raise ValueError(f"expected {WINDOW} samples, got {len(window)}")
        row = np.concatenate([self._context, window.astype(np.float32)])[None, :]
        out, self._h, self._c = self._session.run(None, {"input": row, "h": self._h, "c": self._c})
        self._context = window[-CONTEXT:].astype(np.float32)
        return float(np.ravel(out)[0])

    def is_speech(self, window: np.ndarray) -> bool:
        return self.probability(window) >= self._threshold
