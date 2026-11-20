from types import SimpleNamespace

import numpy as np

from dubzar.asr import Transcription, WhisperTranscriber

SR = 16000
ONE_SECOND = np.zeros(SR, dtype=np.float32)


class FakeWhisperModel:
    """Mimics faster_whisper.WhisperModel.transcribe -> (segments, info)."""

    def __init__(self, texts: list[str], language: str = "en"):
        self._texts = texts
        self._language = language
        self.calls: list[dict] = []

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        segments = iter(SimpleNamespace(text=t) for t in self._texts)
        info = SimpleNamespace(language=self._language, language_probability=0.99)
        return segments, info


def test_returns_none_for_silence():
    transcriber = WhisperTranscriber(model=FakeWhisperModel([]))

    assert transcriber.transcribe(ONE_SECOND) is None


def test_returns_none_for_whitespace_only_text():
    transcriber = WhisperTranscriber(model=FakeWhisperModel(["  ", " "]))

    assert transcriber.transcribe(ONE_SECOND) is None


def test_returns_none_for_non_english():
    # Review Focus 5: non-English files are skipped, not mistranslated.
    transcriber = WhisperTranscriber(model=FakeWhisperModel(["Merhaba"], language="tr"))

    assert transcriber.transcribe(ONE_SECOND) is None


def test_returns_text_language_and_duration():
    model = FakeWhisperModel([" Hello there. ", "General Kenobi!"])
    transcriber = WhisperTranscriber(model=model)

    result = transcriber.transcribe(np.zeros(int(2.5 * SR), dtype=np.float32))

    assert result == Transcription("Hello there. General Kenobi!", "en", 2.5)


def test_asks_model_to_filter_non_speech():
    model = FakeWhisperModel(["Hi"])

    WhisperTranscriber(model=model).transcribe(ONE_SECOND)

    assert model.calls[0]["vad_filter"] is True


def test_falls_back_to_cpu_when_gpu_libraries_are_missing():
    class GpuBrokenModel:
        def transcribe(self, audio, **kwargs):
            raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")

    created: list[str] = []

    def factory(device: str):
        created.append(device)
        return GpuBrokenModel() if device == "auto" else FakeWhisperModel(["Hello"])

    transcriber = WhisperTranscriber(device="auto", model_factory=factory)

    result = transcriber.transcribe(ONE_SECOND)
    again = transcriber.transcribe(ONE_SECOND)

    assert result is not None and result.text == "Hello"
    assert again is not None
    assert created == ["auto", "cpu"]  # fell back once, then stayed on the CPU


def test_cpu_failure_is_not_swallowed():
    class BrokenModel:
        def transcribe(self, audio, **kwargs):
            raise RuntimeError("out of memory")

    transcriber = WhisperTranscriber(device="cpu", model_factory=lambda device: BrokenModel())

    try:
        transcriber.transcribe(ONE_SECOND)
    except RuntimeError as exc:
        assert "out of memory" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
