import numpy as np

from dubzar.ocr import OcrLine
from dubzar.screen_source import ScreenSubtitleSource

PICTURE = np.full((80, 400, 3), 90, dtype=np.uint8)
def pictures(n):
    """Frames whose background keeps changing (a moving game scene), so OCR runs on each."""
    return [np.full((80, 400, 3), 60 + 7 * i, dtype=np.uint8) for i in range(n)]


BLACK = np.zeros((80, 400, 3), dtype=np.uint8)
TEXT = "Keep your head down and stay quiet."


def line(text, x=0.5, y=0.6):
    return OcrLine(text, x, y)


class FakeOcr:
    def __init__(self, script):
        self.script, self.calls = list(script), 0

    def read(self, image):
        self.calls += 1
        return self.script.pop(0) if self.script else []


class Translate:
    def __init__(self):
        self.seen = []

    def translate(self, text, context=()):
        self.seen.append(text)
        return "TR: " + text


class AlwaysChanged:
    """These tests use flat pictures without any text-like pixels: treat every picture as changed, so each poll reads."""

    def changed(self, frame):
        return True

    def commit(self):
        pass


def make(frames, ocr_script, **kw):
    frames = list(frames)
    cues, clears = [], []
    kw.setdefault("watcher", AlwaysChanged())
    source = ScreenSubtitleSource(lambda: frames.pop(0) if frames else PICTURE, FakeOcr(ocr_script), Translate(),
                                  cues.append, lambda: clears.append(1), **kw)
    return source, cues, clears


def test_shows_the_translated_subtitle_once_it_is_confirmed_and_clears_it_when_it_goes():
    source, cues, clears = make(pictures(5), [[line(TEXT)], [line(TEXT)], [line(TEXT)], [], []])

    for _ in range(5):
        source.poll_once()

    assert [c.text_tr for c in cues] == ["TR: " + TEXT]
    assert cues[0].until_cleared and cues[0].text_src == TEXT
    assert clears == [1]


def test_corner_logos_are_not_part_of_the_subtitle():
    watermark = line("MKIceAndFire Studios", x=0.9)
    source, cues, _ = make(pictures(2), [[watermark, line(TEXT)]] * 2)

    source.poll_once(); source.poll_once()

    assert [c.text_src for c in cues] == [TEXT]


def test_black_frames_switch_the_source_off_without_running_ocr():
    source, cues, _ = make([BLACK] * 12, [], black_limit=5)

    for _ in range(12):
        source.poll_once()

    assert source.blocked and cues == [] and source.ocr_calls == 0


def test_a_picture_after_black_frames_recovers():
    source, _, _ = make([BLACK] * 6 + [PICTURE] * 2, [], black_limit=5)

    for _ in range(8):
        source.poll_once()

    assert not source.blocked


def test_active_while_a_subtitle_is_showing_so_speech_recognition_can_rest():
    source, _, _ = make(pictures(4), [[line(TEXT)]] * 3 + [[]])

    assert not source.active
    source.poll_once(); source.poll_once()
    assert source.active
    source.poll_once(); source.poll_once()


def test_no_monitor_means_nothing_happens():
    cues = []
    source = ScreenSubtitleSource(lambda: None, FakeOcr([]), Translate(), cues.append, lambda: None)

    source.poll_once()

    assert cues == [] and not source.blocked
