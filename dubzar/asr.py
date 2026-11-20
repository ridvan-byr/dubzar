import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import numpy as np

from dubzar.errors import ModelMissingError

log = logging.getLogger(__name__)

SR = 16000


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str
    duration_s: float
    confidence: float = 1.0  # 0..1; low means the recognition is doubtful (noise, music, very short)


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
                 model_factory: Callable[[str], Any] | None = None, allow_download: bool = False,
                 cpu_threads: int = 0):
        self._model_size = model_size
        self._device = device
        self._source_language = source_language
        self._model = model
        self._allow_download = allow_download
        self._cpu_threads = cpu_threads  # 0 = the library default; a small number keeps cores free for the game
        self._factory = model_factory or self._default_factory

    def _default_factory(self, device: str) -> Any:
        from faster_whisper import WhisperModel

        return WhisperModel(self._model_size, device=device, local_files_only=not self._allow_download,
                            cpu_threads=self._cpu_threads)

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = self._factory(self._device)
        return self._model

    def load(self) -> None:
        """Create the model now (slow), so a missing model shows up before the game starts.

        Models are only downloaded when ``allow_download`` is set; otherwise a missing model
        raises ``ModelMissingError`` with the flag that grants the download.
        """
        try:
            self._get_model()
        except (OSError, ValueError) as exc:
            raise ModelMissingError(
                f"Whisper modeli '{self._model_size}' bu bilgisayarda yok. İndirmek için --allow-download "
                f"ile yeniden çalıştırın. ({exc})"
            ) from exc

    def _run(self, samples: np.ndarray) -> tuple[str, str, float]:
        segments, info = self._get_model().transcribe(
            np.asarray(samples, dtype=np.float32), vad_filter=True
        )
        parts = list(segments)
        text = " ".join(s.text.strip() for s in parts).strip()
        return text, info.language, _confidence(parts)

    def transcribe(self, samples: np.ndarray) -> Transcription | None:
        try:
            text, language, confidence = self._run(samples)
        except RuntimeError as exc:
            if self._device == "cpu":
                raise
            log.warning("GPU transcription failed (%s); switching to CPU", exc)
            self._device, self._model = "cpu", None
            text, language, confidence = self._run(samples)
        if not text or language != self._source_language:
            return None
        return Transcription(text, language, len(samples) / SR, confidence)


def _confidence(segments: list) -> float:
    """exp(mean avg_logprob) * (1 - mean no_speech_prob), clamped to 0..1.

    Segments without scores (test fakes) count as fully confident.
    """
    if not segments:
        return 1.0
    logprob = sum(getattr(s, "avg_logprob", 0.0) for s in segments) / len(segments)
    no_speech = sum(getattr(s, "no_speech_prob", 0.0) for s in segments) / len(segments)
    return max(0.0, min(1.0, math.exp(logprob) * (1.0 - no_speech)))
