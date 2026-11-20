"""Smoke test with the real model. Needs faster-whisper, a model download and
Windows speech synthesis (System.Speech). Run with: pytest -m slow"""

import subprocess
import sys

import pytest
from scipy.io import wavfile

from dubzar.asr import WhisperTranscriber
from dubzar.audio import to_mono_16k

pytestmark = pytest.mark.slow

_SPEAK = (
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$s.SetOutputToWaveFile($args[0]); $s.Speak('Hello, this is a test.'); $s.Dispose()"
)


@pytest.mark.skipif(sys.platform != "win32", reason="uses Windows speech synthesis")
def test_real_model_transcribes_english_speech(tmp_path):
    pytest.importorskip("faster_whisper")
    wav = tmp_path / "speech.wav"
    subprocess.run(["powershell", "-NoProfile", "-Command", _SPEAK, str(wav)], check=True)
    sr, data = wavfile.read(wav)
    samples = to_mono_16k(data.astype("float32") / 32768.0, sr)

    result = WhisperTranscriber(model_size="tiny", device="cpu").transcribe(samples)

    assert result is not None
    assert result.language == "en"
    assert "test" in result.text.lower()
