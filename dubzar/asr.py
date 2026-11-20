import logging
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import numpy as np

log = logging.getLogger(__name__)

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

    With ``device="auto"`` the GPU is preferred. If the GPU libraries turn out to be
    unusable (a RuntimeError, e.g. missing CUDA DLLs) it falls back to the CPU once
    and stays there. ``model`` / ``model_factory`` can be injected (tests); otherwise
    the model is created lazily so importing this module does not need faster-whisper.
    """

    def __init__(self, model_size: str = "small", device: str = "auto",
                 source_language: str = "en", model: Any = None,
                 model_factory: Callable[[str], Any] | None = None):
        self._model_size = model_size
        self._device = device
        self._source_language = source_language
        self._model = model
        self._factory = model_factory or self._default_factory

    def _default_factory(self, device: str) -> Any:
        from faster_whisper import WhisperModel

        return WhisperModel(self._model_size, device=device)

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = self._factory(self._device)
        return self._model

    def _run(self, samples: np.ndarray) -> tuple[str, str]:
        segments, info = self._get_model().transcribe(
            np.asarray(samples, dtype=np.float32), vad_filter=True
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return text, info.language

    def transcribe(self, samples: np.ndarray) -> Transcription | None:
        try:
            text, language = self._run(samples)
        except RuntimeError as exc:
            if self._device == "cpu":
                raise
            log.warning("GPU transcription failed (%s); switching to CPU", exc)
            self._device, self._model = "cpu", None
            text, language = self._run(samples)
        if not text or language != self._source_language:
            return None
        return Transcription(text, language, len(samples) / SR)
