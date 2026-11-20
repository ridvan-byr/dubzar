import numpy as np
import pytest

pytest.importorskip("PIL")
from dubzar.ocr import OcrLine, RobustOcr  # noqa: E402
from dubzar.textfix import Vocabulary  # noqa: E402

WORDS = "the job was never same after accident keep your head down and stay quiet right now".split()
VOCAB = Vocabulary({w: -3.0 for w in WORDS})
FRAME = np.full((40, 120, 3), 30, dtype=np.uint8)


class ScriptedReader:
    """Returns a scripted reading per call, so a test can say what each image variant 'reads'."""

    def __init__(self, *readings):
        self.readings = list(readings)
        self.calls = 0

    def read(self, image):
        self.calls += 1
        text = self.readings.pop(0) if self.readings else ""
        return [OcrLine(text, 0.5, 0.5)] if text else []


def texts(lines):
    return [l.text for l in lines]


def test_two_variants_that_agree_are_enough_and_no_more_are_read():
    reader = ScriptedReader("Keep your head down.", "keep your head down", "SHOULD NOT BE READ")

    lines = RobustOcr(reader, VOCAB).read(FRAME)

    assert texts(lines) == ["Keep your head down."] and reader.calls == 2


def test_one_clean_reading_alone_is_not_trusted_because_it_may_be_a_fragment():
    reader = ScriptedReader("give his children a better future.", "He worked hard all his life to give his children a better future.")

    lines = RobustOcr(reader, VOCAB).read(FRAME)

    assert reader.calls >= 2


def test_misreadings_are_repaired_before_judging():
    reader = ScriptedReader("Keep your head dovvn and stay quiet.")      # vv for w would not be fixed, but stay/quiet are

    lines = RobustOcr(reader, VOCAB).read(FRAME)

    assert reader.calls >= 1 and "Keep your head" in texts(lines)[0]


def test_a_garbled_reading_triggers_other_variants_and_the_best_one_wins():
    reader = ScriptedReader("Tiıe zzierıziz zil", "Kecp yoor hoad dowm", "Keep your head down and stay quiet.", "", "", "")

    lines = RobustOcr(reader, VOCAB).read(FRAME)

    assert texts(lines) == ["Keep your head down and stay quiet."]
    assert reader.calls >= 3


def test_nothing_readable_gives_nothing():
    reader = ScriptedReader("", "", "", "", "")

    assert RobustOcr(reader, VOCAB).read(FRAME) == []


def test_it_stops_as_soon_as_two_variants_agree_on_good_text():
    good = "The job was never the same after the accident."
    reader = ScriptedReader("zzz qqq", good, good, "SHOULD NOT BE READ")

    RobustOcr(reader, VOCAB).read(FRAME)

    assert reader.calls == 3


def test_the_reading_most_variants_agree_on_wins_a_close_call():
    reader = ScriptedReader("Keep your head down", "Stay quiet right now", "Keep your head down", "Stay quiet right now", "Keep your head down")

    lines = RobustOcr(reader, VOCAB, good_enough=1.01).read(FRAME)

    assert texts(lines) == ["Keep your head down"]


def test_a_longer_complete_reading_beats_a_short_clean_fragment():
    reader = ScriptedReader("zzz", "Keep your", "Keep your head down and stay quiet right now.", "")

    lines = RobustOcr(reader, VOCAB, good_enough=1.01).read(FRAME)      # never early-stop: compare all variants

    assert texts(lines) == ["Keep your head down and stay quiet right now."]


def test_real_turkish_text_is_not_folded_into_english_looking_garbage():
    """The Turkish-letter repair is for English words the Turkish engine mangled. A game that already shows Turkish
    must keep its Turkish letters, so the tracker can recognise and ignore it."""
    turkish = "Ve şey, duyduğuma göre pek fazla yokmuş"
    reader = ScriptedReader(turkish, turkish, turkish, turkish, turkish, turkish)

    lines = RobustOcr(reader, VOCAB).read(FRAME)

    assert texts(lines) == [turkish]


def test_english_mangled_by_the_turkish_engine_is_still_repaired():
    reader = ScriptedReader("Keep your head dovvn and stay quıet.", "Keep your head dovvn and stay quıet.")

    lines = RobustOcr(reader, VOCAB).read(FRAME)

    assert "ı" not in texts(lines)[0]
