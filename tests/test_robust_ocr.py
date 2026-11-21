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


class LineReader:
    """Each call returns a prepared list of lines (text, y), so a test can make each variant wrong somewhere else."""

    def __init__(self, *readings):
        self.readings = list(readings)

    def read(self, image):
        lines = self.readings.pop(0) if self.readings else []
        return [OcrLine(text, 0.5, y) for text, y in lines]


def test_the_best_reading_of_each_line_is_taken_from_a_different_variant():
    """On a real frame one variant read line 3 perfectly and lost line 4, another did the opposite."""
    one = [("Keep your head down", 0.2), ("and stay quiet", 0.5), ("zzz qqq", 0.8)]
    two = [("Kecp yoor hoad dowm", 0.2), ("and stay quiet", 0.5), ("right now", 0.8)]
    three = [("Keep your head down", 0.2), ("and stay quicl", 0.5)]
    reader = LineReader(one, two, three, [], [], [])

    lines = RobustOcr(reader, VOCAB, good_enough=1.01).read(FRAME)

    assert [l.text for l in sorted(lines, key=lambda l: l.center_y)] == [
        "Keep your head down", "and stay quiet", "right now"]


def test_a_line_seen_by_only_one_variant_and_garbled_is_dropped():
    reader = LineReader([("Keep your head down", 0.2), ("r 11", 0.8)], [("Keep your head down", 0.2)], [], [], [], [])

    lines = RobustOcr(reader, VOCAB, good_enough=1.01).read(FRAME)

    assert [l.text for l in lines] == ["Keep your head down"]


def test_the_merged_reading_competes_with_the_best_whole_reading():
    """Merging lines is not always better: when one variant read everything well, a patchwork must not replace it."""
    whole = [("Keep your head down", 0.2), ("and stay quiet", 0.5), ("right now", 0.8)]
    noisy_a = [("Keep your hcad down", 0.2), ("stay", 0.5)]
    noisy_b = [("Keep your head", 0.21), ("and stay quiet", 0.52), ("zzz", 0.79)]
    reader = LineReader(whole, noisy_a, noisy_b, [], [], [])

    lines = RobustOcr(reader, VOCAB, good_enough=1.01).read(FRAME)

    assert [l.text for l in sorted(lines, key=lambda l: l.center_y)] == [
        "Keep your head down", "and stay quiet", "right now"]


# --- the cascade: a fast, good primary reader, with the older one as a safety net -------------------------------
from dubzar.ocr import CascadeOcr  # noqa: E402


class Fixed:
    def __init__(self, *texts, language="fixed"):
        self.texts, self.calls, self.language = texts, 0, language

    def read(self, image):
        self.calls += 1
        return [OcrLine(t, 0.5, 0.3 + 0.2 * i) for i, t in enumerate(self.texts) if t]


def test_a_good_primary_reading_is_final_and_the_fallback_is_not_consulted():
    primary, fallback = Fixed("Keep your head down and stay quiet."), Fixed("zzz")

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert texts(lines) == ["Keep your head down and stay quiet."] and fallback.calls == 0


def test_an_empty_primary_reading_falls_back():
    primary, fallback = Fixed(), Fixed("Keep your head down.")

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert texts(lines) == ["Keep your head down."]


def test_a_doubtful_primary_reading_is_compared_with_the_fallback_and_the_better_one_wins():
    primary, fallback = Fixed("Kecp yoor hoad dowm"), Fixed("Keep your head down and stay quiet.")

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert texts(lines) == ["Keep your head down and stay quiet."]


def test_the_primary_readings_get_the_same_repairs_as_everything_else():
    primary, fallback = Fixed("Ilve picked up"), Fixed("")

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert texts(lines)[0].startswith("I've")


class Lines:
    """A reader returning given (text, y, confidence) lines."""

    def __init__(self, *items):
        self.items, self.calls = items, 0

    def read(self, image):
        self.calls += 1
        return [OcrLine(t, 0.5, y, 0.09, c) for t, y, c in self.items]


def test_a_confident_primary_is_never_second_guessed_even_when_the_dictionary_does_not_know_its_words():
    primary = Lines(("Omega Red: [in Russian accent] Find him.", 0.4, 0.97))
    fallback = Lines(("Om go Red: Lin Russian acgntJ Find him.", 0.4, 0.0))

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert texts(lines) == ["Omega Red: [in Russian accent] Find him."] and fallback.calls == 0


def test_only_the_doubtful_line_is_replaced_from_the_fallback():
    primary = Lines(("Ju Yeah, t' how B plants work", 0.30, 0.79), ("keep your head down and stay quiet", 0.60, 0.98))
    fallback = Lines(("Keep your head down and stay quiet right now", 0.30, 0.0), ("zzzz qqqq", 0.60, 0.0))

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert texts(sorted(lines, key=lambda l: l.center_y)) == [
        "Keep your head down and stay quiet right now", "keep your head down and stay quiet"]


def test_a_line_only_the_fallback_found_is_added_when_it_reads_like_english():
    primary = Lines(("Keep your head down", 0.30, 0.98), ("zz", 0.5, 0.40))
    fallback = Lines(("Keep your head down", 0.30, 0.0), ("stay quiet right now", 0.80, 0.0))

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert "stay quiet right now" in texts(lines)


def test_garbage_only_the_fallback_found_is_not_added():
    primary = Lines(("zz", 0.5, 0.40))
    fallback = Lines(("Keep your head down", 0.30, 0.0), ("qqq xxx zzz", 0.80, 0.0))

    assert "qqq xxx zzz" not in texts(CascadeOcr(primary, fallback, VOCAB).read(FRAME))


def test_a_fallback_line_that_repeats_what_the_primary_already_read_is_not_added_again():
    """Two engines split the same text into lines differently; the second split must not be appended as new lines."""
    primary = Lines(("Keep your head down and stay", 0.30, 0.98), ("quiet right now", 0.55, 0.60))
    fallback = Lines(("Keep your head down", 0.25, 0.0), ("and stay quiet right now", 0.62, 0.0))

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    words = " ".join(texts(lines)).lower().split()
    assert words.count("keep") == 1 and words.count("quiet") == 1


def test_corner_text_like_a_watermark_neither_triggers_the_fallback_nor_gets_matched_with_real_lines():
    primary = Lines(("Keep your head down and stay quiet", 0.40, 0.98), ("MKIceAnd", 0.62, 0.88))
    primary.items = (primary.items[0], ("MKIceAnd", 0.62, 0.88))
    corner = OcrLine("MKIceAnd", 0.92, 0.62, 0.09, 0.88)

    class WithCorner(Lines):
        def read(self, image):
            return super().read(image) + [corner]

    primary = WithCorner(("Keep your head down and stay quiet", 0.40, 0.98))
    fallback = Lines(("Keep your head down", 0.40, 0.0), ("stay quiet", 0.62, 0.0))

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert fallback.calls == 0 and texts(lines) == ["Keep your head down and stay quiet"]


def test_a_fallback_line_that_reads_as_english_comes_back_as_trusted_so_no_second_reading_is_needed():
    primary = Lines(("Ju Yeah, t' how B plants work", 0.30, 0.54), ("keep your head down and stay quiet", 0.60, 0.98))
    fallback = Lines(("Keep your head down and stay quiet right now", 0.30, 0.0))

    lines = sorted(CascadeOcr(primary, fallback, VOCAB).read(FRAME), key=lambda l: l.center_y)

    assert lines[0].text.startswith("Keep your head") and lines[0].confidence >= 0.9


def test_a_fallback_line_that_does_not_read_as_english_stays_untrusted():
    primary = Lines(("zzzz qqqq", 0.30, 0.50),)
    fallback = Lines(("Keep yoor hcad", 0.30, 0.0),)

    lines = CascadeOcr(primary, fallback, VOCAB).read(FRAME)

    assert all(l.confidence < 0.9 for l in lines)


def test_a_fallback_reader_can_be_limited_to_a_few_variants():
    reader = ScriptedReader("zzz qqq", "xxx yyy", "vvv www", "uuu ttt", "sss rrr", "ppp ooo")

    RobustOcr(reader, VOCAB, max_variants=2).read(FRAME)

    assert reader.calls == 2
