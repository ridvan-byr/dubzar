import numpy as np
import pytest

from dubzar.asr import Transcription
from dubzar.index import IndexStore
from dubzar.live import LiveEngine
from dubzar.models import Cue
from dubzar.segmenter import Segment
from test_fingerprint import SR, synth_line
from test_scan import FakeTranscriber, FakeTranslator, PrefixTranslator


@pytest.fixture
def store(tmp_path):
    s = IndexStore(str(tmp_path / "live.db"))
    yield s
    s.close()


def segment(seed: int, seconds: float) -> Segment:
    return Segment(synth_line(seed, seconds), 0.0, seconds)


def engine(store, transcriber=None, translator=None, **kwargs):
    cues: list[Cue] = []
    live = LiveEngine(store, transcriber or FakeTranscriber(), translator or PrefixTranslator(),
                      cues.append, **kwargs)
    return live, cues


def test_unknown_segment_is_transcribed_shown_and_learned(store):
    live, cues = engine(store)

    cue = live.process(segment(1, 1.5))

    assert cue is not None and cue.text_tr == "TR:hello" and cue.text_src == "hello"
    assert cues == [cue]
    assert cue.line_id.startswith("live/")
    assert store.count_lines() == 1


def test_known_segment_uses_the_index_without_transcribing(store):
    # Review Focus 2: the second time the same line plays, the slow model is not needed.
    transcriber = FakeTranscriber()
    live, cues = engine(store, transcriber)
    first = live.process(segment(1, 1.5))

    second = live.process(segment(1, 1.5))

    assert transcriber.calls == 1
    assert second is not None and second.text_tr == first.text_tr
    assert len(cues) == 2
    assert store.count_lines() == 1


def test_silence_or_music_without_speech_shows_nothing_and_learns_nothing(store):
    # Review Focus 1
    live, cues = engine(store, FakeTranscriber(result=None))

    assert live.process(segment(7, 4.0)) is None
    assert cues == [] and store.count_lines() == 0


def test_low_confidence_is_neither_shown_nor_learned(store):
    doubtful = FakeTranscriber(result=Transcription("hello", "en", 1.5, confidence=0.3))
    live, cues = engine(store, doubtful)

    assert live.process(segment(1, 1.5)) is None
    assert cues == [] and store.count_lines() == 0


def test_confidence_at_the_threshold_is_accepted(store):
    ok = FakeTranscriber(result=Transcription("hello", "en", 1.5, confidence=0.6))
    live, cues = engine(store, ok, min_confidence=0.6)

    assert live.process(segment(1, 1.5)) is not None


@pytest.mark.parametrize("seconds", [0.5, 13.0])
def test_segment_too_short_or_too_long_is_shown_but_not_learned(store, seconds):
    live, cues = engine(store)

    cue = live.process(segment(2, seconds))

    assert cue is not None and cues == [cue]
    assert store.count_lines() == 0


def test_empty_translation_shows_nothing_and_learns_nothing(store):
    live, cues = engine(store, translator=FakeTranslator(output=""))

    assert live.process(segment(1, 1.5)) is None
    assert cues == [] and store.count_lines() == 0


def test_too_little_audio_is_ignored_without_calling_the_model(store):
    transcriber = FakeTranscriber()
    live, cues = engine(store, transcriber)

    assert live.process(Segment(np.zeros(int(0.1 * SR), dtype=np.float32), 0.0, 0.1)) is None
    assert transcriber.calls == 0


def test_different_lines_are_learned_separately_and_both_hit_later(store):
    transcriber = FakeTranscriber()
    live, cues = engine(store, transcriber)
    live.process(segment(1, 1.5))
    live.process(segment(2, 1.5))

    live.process(segment(1, 1.5))
    live.process(segment(2, 1.5))

    assert transcriber.calls == 2 and store.count_lines() == 2
