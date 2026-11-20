import numpy as np

from dubzar.segmenter import Segment, SpeechSegmenter
from test_fingerprint import SR, synth_line

CHUNK = 1600


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def run(audio: np.ndarray, chunk: int = CHUNK, **kwargs) -> list[Segment]:
    segmenter = SpeechSegmenter(**kwargs)
    out: list[Segment] = []
    for i in range(0, len(audio), chunk):
        out.extend(segmenter.feed(audio[i : i + chunk]))
    out.extend(segmenter.flush())
    return out


def length(segment: Segment) -> float:
    return segment.end_s - segment.start_s


def test_splits_two_lines_separated_by_silence():
    audio = np.concatenate([silence(0.5), synth_line(1, 1.5), silence(1.0), synth_line(2, 2.0), silence(1.0)])

    segments = run(audio)

    assert len(segments) == 2
    assert abs(length(segments[0]) - 1.8) < 0.4  # 1.5 s of speech plus a little context on each side
    assert abs(length(segments[1]) - 2.3) < 0.4
    assert segments[0].end_s < segments[1].start_s


def test_segment_samples_match_its_reported_span():
    segments = run(np.concatenate([silence(0.3), synth_line(1, 1.0), silence(1.0)]))

    assert len(segments) == 1
    assert abs(len(segments[0].samples) / SR - length(segments[0])) < 0.02


def test_ignores_blips_shorter_than_min_speech():
    audio = np.concatenate([silence(0.5), synth_line(1, 0.1), silence(1.0)])

    assert run(audio) == []


def test_silence_only_returns_nothing():
    assert run(silence(5.0)) == []


def test_force_cuts_continuous_audio_at_max_segment_s():
    # Review Focus 4: music or endless talk must not make the latency unbounded.
    audio = synth_line(3, 30.0)

    segments = run(audio)

    assert len(segments) >= 3
    assert all(length(s) <= 12.01 for s in segments)
    assert sum(length(s) for s in segments) >= 29.8  # nothing is lost between the cuts


def test_flush_returns_the_unfinished_segment():
    segmenter = SpeechSegmenter()
    audio = np.concatenate([silence(0.3), synth_line(1, 1.0)])
    fed = [s for i in range(0, len(audio), CHUNK) for s in segmenter.feed(audio[i : i + CHUNK])]

    assert fed == []
    assert len(segmenter.flush()) == 1
    assert segmenter.flush() == []  # nothing left the second time


def test_chunk_boundaries_do_not_change_the_result():
    audio = np.concatenate([silence(0.4), synth_line(1, 1.2), silence(0.9), synth_line(2, 1.6), silence(0.9)])

    a, b = run(audio, chunk=1600), run(audio, chunk=733)

    assert len(a) == len(b) == 2
    assert all(abs(x.start_s - y.start_s) < 0.01 and abs(x.end_s - y.end_s) < 0.01 for x, y in zip(a, b))


def test_no_silent_segment_appears_after_a_forced_cut():
    # speech that ends exactly at the 12 s limit, then silence: the leftover must not become an empty "segment"
    audio = np.concatenate([synth_line(4, 12.0), silence(1.5)])

    segments = run(audio)

    assert len(segments) >= 1
    assert all(float(np.abs(s.samples).max()) > 0.05 for s in segments)
