from collections import defaultdict

import numpy as np

from dubzar.audio import to_mono_16k
from dubzar.fingerprint import Matcher, fingerprint

SR = 16000
LINE_SECONDS = 3.0


def synth_line(seed: int, seconds: float = LINE_SECONDS) -> np.ndarray:
    """Speech-like test signal: every 50 ms three random tones in 300-3800 Hz."""
    rng = np.random.default_rng(seed)
    seg = int(0.05 * SR)
    t = np.arange(seg) / SR
    parts = []
    for _ in range(int(seconds / 0.05)):
        freqs = rng.uniform(300, 3800, size=3)
        parts.append(sum(np.sin(2 * np.pi * f * t) for f in freqs) / 3)
    return np.concatenate(parts).astype(np.float32)


def add_noise(x: np.ndarray, snr_db: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sigma = np.sqrt(np.mean(x**2) / 10 ** (snr_db / 10))
    return (x + rng.normal(0, sigma, size=x.shape)).astype(np.float32)


def build_lookup(lines: dict[str, np.ndarray]):
    table: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for line_id, samples in lines.items():
        for h, anchor in fingerprint(samples):
            table[h].append((line_id, anchor))

    def lookup(hashes: list[int]) -> list[tuple[str, int, int]]:
        found = []
        for qi, h in enumerate(hashes):
            for line_id, anchor in table.get(h, ()):
                found.append((line_id, anchor, qi))
        return found

    return lookup


LINES = {name: synth_line(seed) for name, seed in [("A", 1), ("B", 2), ("C", 3)]}
LOOKUP = build_lookup(LINES)


def feed_chunks(matcher: Matcher, audio: np.ndarray, chunk: int = 1600):
    """Feed audio in 100 ms chunks; return (result, chunks_used)."""
    for i in range(0, len(audio), chunk):
        result = matcher.feed(audio[i : i + chunk])
        if result is not None:
            return result, i // chunk + 1
    return None, len(audio) // chunk


def test_to_mono_16k_downmixes_and_resamples():
    stereo_48k = np.ones((48000, 2), dtype=np.float32)

    out = to_mono_16k(stereo_48k, 48000)

    assert out.dtype == np.float32
    assert out.ndim == 1
    assert len(out) == 16000


def test_matches_line_from_first_300ms():
    matcher = Matcher(LOOKUP)

    result, used = feed_chunks(matcher, LINES["B"][: int(0.3 * SR)])

    assert result is not None and result.line_id == "B"
    assert used <= 3


def test_matches_when_query_is_not_frame_aligned():
    matcher = Matcher(LOOKUP)

    result, _ = feed_chunks(matcher, LINES["B"][1000 : 1000 + int(0.3 * SR)])

    assert result is not None and result.line_id == "B"


def test_matches_with_noise_at_10db():
    matcher = Matcher(LOOKUP)
    noisy = add_noise(LINES["B"][: int(0.6 * SR)], 10, seed=7)

    result, _ = feed_chunks(matcher, noisy)

    assert result is not None and result.line_id == "B"


def test_returns_none_for_unrelated_audio():
    matcher = Matcher(LOOKUP)
    unrelated = synth_line(99, 1.0)

    result, _ = feed_chunks(matcher, unrelated)

    assert result is None


def test_low_snr_returns_none_not_wrong_line():
    # Review Focus 2: music/effects over speech must never yield a wrong subtitle.
    for line_id, samples in LINES.items():
        matcher = Matcher(LOOKUP)
        noisy = add_noise(samples[: int(0.6 * SR)], 0, seed=11)

        result, _ = feed_chunks(matcher, noisy)

        assert result is None or result.line_id == line_id


def test_reset_clears_buffered_audio():
    matcher = Matcher(LOOKUP)
    matcher.feed(LINES["A"][: int(0.1 * SR)])

    matcher.reset()
    result, _ = feed_chunks(matcher, LINES["B"][: int(0.3 * SR)])

    assert result is not None and result.line_id == "B"
