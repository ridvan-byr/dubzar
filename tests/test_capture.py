import numpy as np
import pytest

from dubzar.capture import bytes_to_mono_16k, run_matching
from dubzar.fingerprint import Matcher, fingerprint
from dubzar.index import IndexStore
from dubzar.models import Cue
from test_fingerprint import LINES, SR, synth_line

CHUNK = 1600  # 100 ms


@pytest.fixture
def store(tmp_path):
    s = IndexStore(str(tmp_path / "game.db"))
    for line_id, samples in LINES.items():
        s.add_line(Cue(line_id, "x", f"tr-{line_id}", 3.0), fingerprint(samples), f"d-{line_id}")
    yield s
    s.close()


def chunks(audio: np.ndarray):
    for i in range(0, len(audio), CHUNK):
        yield audio[i : i + CHUNK]


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def run(store, audio):
    cues: list[Cue] = []
    run_matching(chunks(audio), Matcher(store.lookup), store, cues.append)
    return [c.line_id for c in cues]


def test_emits_cue_once_per_line(store):
    # The rest of a line keeps matching after the first hit; it must not re-trigger.
    assert run(store, LINES["A"]) == ["A"]


def test_no_cue_for_unmatched_audio(store):
    assert run(store, synth_line(99, 2.0)) == []


def test_two_different_lines_emit_two_cues(store):
    audio = np.concatenate([LINES["A"], silence(0.3), LINES["B"]])

    assert run(store, audio) == ["A", "B"]


def test_same_line_can_trigger_again_after_it_ended(store):
    audio = np.concatenate([LINES["A"], silence(1.5), LINES["A"]])

    assert run(store, audio) == ["A", "A"]


def test_bytes_to_mono_16k_downmixes_and_resamples():
    frames = 4800  # 100 ms at 48 kHz
    stereo = np.full((frames, 2), 16384, dtype=np.int16)  # 0.5 full scale

    out = bytes_to_mono_16k(stereo.tobytes(), channels=2, sr=48000)

    assert out.dtype == np.float32
    assert len(out) == 1600
    assert abs(float(out[800]) - 0.5) < 0.01
