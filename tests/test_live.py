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


def test_middling_confidence_is_shown_but_not_learned(store):
    middling = FakeTranscriber(result=Transcription("hello", "en", 3.0, confidence=0.65))
    live, cues = engine(store, middling)

    assert live.process(segment(1, 3.0)) is not None and len(cues) == 1
    assert store.count_lines() == 0  # a shaky transcript must not become a permanent fingerprint


def test_confidence_at_the_threshold_is_accepted(store):
    ok = FakeTranscriber(result=Transcription("hello", "en", 1.5, confidence=0.6))
    live, cues = engine(store, ok, min_confidence=0.6)

    assert live.process(segment(1, 1.5)) is not None


@pytest.mark.parametrize("seconds", [0.5, 7.0])
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


# --- the pipeline: instant cues for known lines + live recognition for unknown ones ------------
import threading  # noqa: E402
import time  # noqa: E402

from dubzar.live import MAX_BACKLOG, LivePipeline  # noqa: E402


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def wait_until(condition, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.005)
    return condition()


def pipeline(store, transcriber=None, **kwargs):
    cues: list[Cue] = []
    return LivePipeline(store, transcriber or FakeTranscriber(), PrefixTranslator(), cues.append, **kwargs), cues


def play(pl, audio, cues=None, chunk=1600):
    """Feed audio in 100 ms chunks; if ``cues`` is given, return the stream time (s) at which each new cue showed up."""
    seen_at: list[float] = []
    for i in range(0, len(audio), chunk):
        before = len(cues) if cues is not None else 0
        pl.feed(audio[i : i + chunk])
        if cues is not None and len(cues) > before:
            seen_at.extend([(i + chunk) / SR] * (len(cues) - before))
    return seen_at


def line(seed: float = 1, seconds: float = 1.5):
    return np.concatenate([silence(0.3), synth_line(seed, seconds), silence(1.0)])


def test_unknown_line_is_recognised_after_it_ends_and_then_learned(store):
    transcriber = FakeTranscriber()
    pl, cues = pipeline(store, transcriber)

    play(pl, line())
    pl.close()

    assert len(cues) == 1 and cues[0].line_id.startswith("live/")
    assert transcriber.calls == 1 and store.count_lines() == 1


def test_known_line_shows_instantly_and_the_live_path_does_not_repeat_it(store):
    # the line starts at 0.3 s and lasts 1.5 s; a known line must show up long before it ends
    transcriber = FakeTranscriber()
    pl, cues = pipeline(store, transcriber)
    play(pl, line())
    assert wait_until(lambda: len(cues) == 1)

    gap = 3.5  # a line does not repeat within a couple of seconds; the matcher is muted for 3 s after a cue
    shown_at = play(pl, np.concatenate([silence(gap), line()]), cues)
    pl.close()

    assert len(cues) == 2 and transcriber.calls == 1  # no second recognition, no duplicate cue
    assert shown_at and shown_at[0] - gap < 1.0  # 0.3 s of silence + a few hundred ms of the line, not the full 1.8 s


def test_a_known_line_can_be_shown_again_later(store):
    pl, cues = pipeline(store)
    play(pl, line())
    assert wait_until(lambda: len(cues) == 1)

    play(pl, np.concatenate([line(), silence(3.0), line()]))
    pl.close()

    assert len(cues) == 3  # learned once, then shown instantly twice


def test_an_engine_error_does_not_stop_the_pipeline(store):
    class FlakyOnce(FakeTranscriber):
        def transcribe(self, samples):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("translation model is missing")
            return self.result

    pl, cues = pipeline(store, FlakyOnce())

    play(pl, np.concatenate([line(1), line(2)]))
    pl.close()

    assert len(cues) == 1  # the first line was lost to the error, the second one still worked


def test_close_flushes_a_line_that_was_still_being_collected(store):
    pl, cues = pipeline(store)

    play(pl, np.concatenate([silence(0.3), synth_line(1, 1.5)]))  # no trailing silence yet
    assert cues == []
    pl.close()

    assert len(cues) == 1


def test_backlog_is_bounded_when_recognition_is_slower_than_speech(store):
    release = threading.Event()
    handled: list[int] = []

    class Slow(FakeTranscriber):
        def transcribe(self, samples):
            release.wait(5)
            handled.append(1)
            return self.result

    pl, cues = pipeline(store, Slow())
    audio = np.concatenate([line(seed) for seed in range(1, 11)])  # ten distinct lines

    play(pl, audio)
    release.set()
    pl.close()

    assert len(handled) <= MAX_BACKLOG + 1  # stale lines are dropped, not shown ten seconds late


# --- diagnostics: the user must be able to see WHY no subtitle appeared ---------------------------
import logging  # noqa: E402


def test_engine_explains_a_doubtful_recognition(store, caplog):
    doubtful = FakeTranscriber(result=Transcription("hello", "en", 1.5, confidence=0.3))
    live, cues = engine(store, doubtful)

    with caplog.at_level(logging.INFO, logger="dubzar.live"):
        live.process(segment(1, 1.5))

    text = caplog.text
    assert "hello" in text and "0.30" in text and "gösterilmedi" in text


def test_engine_explains_when_nothing_was_recognised(store, caplog):
    live, cues = engine(store, FakeTranscriber(result=None))

    with caplog.at_level(logging.INFO, logger="dubzar.live"):
        live.process(segment(7, 3.0))

    assert "konuşma bulunamadı" in caplog.text


def test_engine_logs_what_it_showed_and_learned(store, caplog):
    live, cues = engine(store)

    with caplog.at_level(logging.INFO, logger="dubzar.live"):
        live.process(segment(1, 1.5))
        live.process(segment(1, 1.5))

    assert "TR:hello" in caplog.text and "öğrenildi" in caplog.text and "indekste" in caplog.text


def test_pipeline_warns_once_when_no_game_audio_arrives(store, caplog):
    pl, cues = pipeline(store)

    with caplog.at_level(logging.WARNING, logger="dubzar.live"):
        play(pl, silence(12.0))  # twelve seconds of dead silence from the capture device
        play(pl, silence(5.0))
    pl.close()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and "ses" in r.getMessage()]
    assert len(warnings) == 1  # said once, not every chunk


def test_pipeline_does_not_warn_when_audio_is_arriving(store, caplog):
    pl, cues = pipeline(store)

    with caplog.at_level(logging.WARNING, logger="dubzar.live"):
        play(pl, np.concatenate([synth_line(1, 12.0), silence(1.0)]))
    pl.close()

    assert not [r for r in caplog.records if r.levelno == logging.WARNING and "alınmıyor" in r.getMessage()]


def test_pipeline_reports_the_audio_level_when_debugging(store, caplog):
    pl, cues = pipeline(store)

    with caplog.at_level(logging.INFO, logger="dubzar.live"):
        play(pl, np.concatenate([synth_line(1, 4.5), silence(0.5)]))
    pl.close()

    assert "ses seviyesi" in caplog.text


def test_pipeline_uses_the_segmenter_it_is_given(store):
    from dubzar.segmenter import SpeechSegmenter

    seen = []

    class Spy(SpeechSegmenter):
        def feed(self, chunk):
            seen.append(len(chunk))
            return super().feed(chunk)

    pipeline = LivePipeline(store, FakeTranscriber(), PrefixTranslator(), lambda cue: None, segmenter=Spy())
    pipeline.feed(np.zeros(1600, dtype=np.float32))
    pipeline.close()

    assert seen == [1600]


def test_recognition_rests_while_the_screen_source_shows_the_games_subtitles(store):
    transcriber = FakeTranscriber()
    live, cues = engine(store, transcriber, skip_recognition=lambda: True)

    assert live.process(segment(1, 3.0)) is None
    assert transcriber.calls == 0 and cues == []


def test_recognition_runs_again_when_the_screen_source_goes_quiet(store):
    resting = {"on": True}
    transcriber = FakeTranscriber()
    live, cues = engine(store, transcriber, skip_recognition=lambda: resting["on"])

    live.process(segment(1, 3.0))
    resting["on"] = False

    assert live.process(segment(2, 3.0)) is not None and transcriber.calls == 1
