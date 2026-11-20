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


def _voice_over_music(voice_seconds_at: list[tuple[float, float]], total: float) -> np.ndarray:
    """Steady music (-26 dB: far above the energy threshold, so an energy segmenter never sees quiet)
    with louder 'voice' bursts (amplitude 0.3) at the given (start, end) times."""
    t = np.arange(int(total * SR)) / SR
    audio = (0.05 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    for start, end in voice_seconds_at:
        a, b = int(start * SR), int(end * SR)
        audio[a:b] += (0.3 * np.sin(2 * np.pi * 440 * t[a:b])).astype(np.float32)
    return audio


def _is_voice(frame: np.ndarray) -> bool:
    return float(np.max(np.abs(frame))) > 0.15  # stands in for the neural VAD: ignores the steady music


def test_custom_classifier_cuts_lines_even_when_music_never_goes_quiet():
    audio = _voice_over_music([(1.0, 3.0), (6.0, 8.0)], total=10.0)

    energy_only = run(audio)
    custom = run(audio, frame=512, is_speech=_is_voice, end_silence_s=0.5)

    assert len(energy_only) == 1 and length(energy_only[0]) > 9   # music glues everything into one cut
    assert len(custom) == 2
    assert 1.8 < length(custom[0]) < 3.0 and 1.8 < length(custom[1]) < 3.0


def test_classifier_decides_the_frame_size_not_the_caller_chunking():
    audio = _voice_over_music([(1.0, 3.0)], total=5.0)

    a = run(audio, chunk=1600, frame=512, is_speech=_is_voice)
    b = run(audio, chunk=777, frame=512, is_speech=_is_voice)

    assert [(s.start_s, s.end_s) for s in a] == [(s.start_s, s.end_s) for s in b]
