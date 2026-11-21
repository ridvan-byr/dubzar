import numpy as np
import pytest

pytest.importorskip("faster_whisper")
from dubzar.vad import WINDOW, SileroSpeechDetector  # noqa: E402


def test_silence_and_steady_tone_are_not_speech():
    vad = SileroSpeechDetector()
    t = np.arange(WINDOW * 40) / 16000
    music = (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

    assert not any(vad.is_speech(np.zeros(WINDOW, dtype=np.float32)) for _ in range(20))
    vad.reset()
    assert sum(vad.is_speech(music[i:i + WINDOW]) for i in range(0, len(music), WINDOW)) <= 2


def test_rejects_wrong_window_size():
    with pytest.raises(ValueError):
        SileroSpeechDetector().is_speech(np.zeros(100, dtype=np.float32))
