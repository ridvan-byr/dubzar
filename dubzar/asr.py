from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

SR = 16000


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str
    duration_s: float


class Transcriber(Protocol):
    def transcribe(self, samples: np.ndarray) -> Transcription | None:
        """Transcribe 16 kHz mono audio; None when there is no usable speech."""


class WhisperTranscriber:
    """faster-whisper backed transcriber for English source audio.

    ``model`` can be injected (tests); otherwise it is created lazily on first use
    so importing this module does not require faster-whisper.
    """

    def __init__(self, model_size: str = "small", device: str = "auto",
                 source_language: str = "en", model: Any = None):
        self._model_size = model_size
        self._device = device
        self._source_language = source_language
        self._model = model

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device=self._device)
        return self._model

    def transcribe(self, samples: np.ndarray) -> Transcription | None:
        segments, info = self._get_model().transcribe(
            np.asarray(samples, dtype=np.float32), vad_filter=True
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        if not text or info.language != self._source_language:
            return None
        return Transcription(text, info.language, len(samples) / SR)
