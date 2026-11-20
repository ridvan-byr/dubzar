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
