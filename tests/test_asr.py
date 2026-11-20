from types import SimpleNamespace

import numpy as np
import pytest

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


class ScoredModel:
    """Like FakeWhisperModel but its segments carry faster-whisper's own quality numbers."""

    def __init__(self, avg_logprob: float, no_speech_prob: float, language: str = "en"):
        self._avg, self._nsp, self._language = avg_logprob, no_speech_prob, language

    def transcribe(self, audio, **kwargs):
        segments = iter([SimpleNamespace(text="Hello", avg_logprob=self._avg, no_speech_prob=self._nsp)])
        return segments, SimpleNamespace(language=self._language, language_probability=0.99)


def test_confidence_is_high_for_a_confident_segment():
    result = WhisperTranscriber(model=ScoredModel(-0.1, 0.01)).transcribe(ONE_SECOND)

    assert result is not None and result.confidence >= 0.85


def test_confidence_is_low_for_a_doubtful_segment():
    result = WhisperTranscriber(model=ScoredModel(-1.5, 0.5)).transcribe(ONE_SECOND)

    assert result is not None and result.confidence < 0.2


def test_existing_callers_still_work_without_confidence():
    assert Transcription("a", "en", 1.0).confidence == 1.0
    result = WhisperTranscriber(model=FakeWhisperModel(["Hello"])).transcribe(ONE_SECOND)
    assert result is not None and result.confidence == 1.0  # segments without scores count as fully confident


# --- models are never downloaded behind the user's back ---------------------------------------
from dubzar.errors import ModelMissingError  # noqa: E402


def test_load_creates_the_model_now_so_problems_show_up_before_the_game_starts():
    created: list[str] = []

    def factory(device: str):
        created.append(device)
        return FakeWhisperModel(["Hi"])

    transcriber = WhisperTranscriber(device="cpu", model_factory=factory)
    transcriber.load()
    transcriber.transcribe(ONE_SECOND)

    assert created == ["cpu"]  # loaded once, reused


def test_a_missing_model_without_download_permission_is_a_clear_error():
    def factory(device: str):
        raise OSError("Cannot find an appropriate cached snapshot folder")

    transcriber = WhisperTranscriber(model_size="small", model_factory=factory)

    with pytest.raises(ModelMissingError) as info:
        transcriber.load()

    assert "small" in str(info.value) and "--allow-download" in str(info.value)


def test_download_is_off_unless_explicitly_allowed():
    assert WhisperTranscriber()._allow_download is False
    assert WhisperTranscriber(allow_download=True)._allow_download is True


# --- the app must not starve the game of CPU ---------------------------------------------------------
def test_whisper_is_given_a_cpu_thread_limit(monkeypatch):
    import sys
    import types

    seen: dict = {}

    class RecordingModel:
        def __init__(self, size, **kwargs):
            seen.update(kwargs)

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=RecordingModel))

    WhisperTranscriber(device="cpu", cpu_threads=2).load()

    assert seen["cpu_threads"] == 2


def test_cpu_threads_default_means_use_the_library_default(monkeypatch):
    import sys
    import types

    seen: dict = {}

    class RecordingModel:
        def __init__(self, size, **kwargs):
            seen.update(kwargs)

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=RecordingModel))

    WhisperTranscriber(device="cpu").load()

    assert seen["cpu_threads"] == 0  # 0 = CTranslate2's own default (all it wants): fine for a scan with the game closed


class DoubtfulLanguageModel:
    """First pass (language left to the model) guesses another language with low certainty; a second pass told
    to expect English reads it. Records each call's ``language`` argument."""

    def __init__(self, guessed="ar", probability=0.69, text="Keep your head down."):
        self.guessed, self.probability, self.text = guessed, probability, text
        self.languages: list = []

    def transcribe(self, audio, **kwargs):
        language = kwargs.get("language")
        self.languages.append(language)
        if language is None:
            info = SimpleNamespace(language=self.guessed, language_probability=self.probability)
        else:
            info = SimpleNamespace(language=language, language_probability=1.0)
        return iter([SimpleNamespace(text=self.text)]), info


def test_a_doubtful_language_guess_is_retried_as_english_instead_of_dropped():
    """Music and effects make Whisper guess 'ar' at 0.69 for a perfectly English line."""
    model = DoubtfulLanguageModel(guessed="ar", probability=0.69)

    result = WhisperTranscriber(model=model).transcribe(ONE_SECOND)

    assert result is not None and result.text == "Keep your head down."
    assert model.languages == [None, "en"]


def test_a_confident_other_language_is_still_rejected_without_a_second_pass():
    """A game voiced in Chinese must not get English-sounding garbage subtitles."""
    model = DoubtfulLanguageModel(guessed="zh", probability=0.97)

    assert WhisperTranscriber(model=model).transcribe(ONE_SECOND) is None
    assert model.languages == [None]


def test_english_needs_no_second_pass():
    model = DoubtfulLanguageModel(guessed="en", probability=0.95)

    assert WhisperTranscriber(model=model).transcribe(ONE_SECOND) is not None
    assert model.languages == [None]
