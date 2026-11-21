import numpy as np

from dubzar.ocr import OcrLine
from dubzar.region_notes import RegionNoteSource

FRAME = np.full((60, 200, 3), 90, dtype=np.uint8)


class Reader:
    def __init__(self, *screens, confidence=0.97):
        self.screens, self.confidence, self.calls = list(screens), confidence, 0

    def read(self, image):
        self.calls += 1
        text = self.screens.pop(0) if self.screens else self.last
        self.last = text
        return [OcrLine(t, 0.2, 0.1 + 0.08 * k, 0.05, self.confidence) for k, t in enumerate(text)]


class Translate:
    def translate(self, text, context=()):
        return "TR(" + text + ")"


class Scripted:
    def __init__(self, *answers):
        self.answers, self.commits = list(answers), 0

    def changed(self, frame):
        return self.answers.pop(0) if self.answers else False

    def commit(self):
        self.commits += 1


def make(reader, *answers, regions=1):
    notes = []
    watchers = iter([Scripted(*answers) for _ in range(regions)])
    source = RegionNoteSource(lambda: [FRAME] * regions, reader, Translate(), notes.append,
                              watcher_factory=lambda: next(watchers))
    return source, notes


def test_a_corner_objective_is_read_translated_and_shown_once():
    source, notes = make(Reader(["Find the missing courier"]), True, False, False)

    for _ in range(3):
        source.poll_once()

    assert [n.text_tr for n in notes] == ["TR(Find the missing courier)"] and source.ocr_calls == 1


def test_nothing_is_read_while_the_corner_does_not_change():
    source, notes = make(Reader(["Find the missing courier"]), False, False, False)

    for _ in range(3):
        source.poll_once()

    assert source.ocr_calls == 0 and notes == []


def test_a_changed_objective_is_shown_again_and_a_vanished_one_is_forgotten():
    source, notes = make(Reader(["Find the missing courier"], ["Deliver the package"], [], ["Deliver the package"]),
                         True, True, True, True)

    for _ in range(4):
        source.poll_once()

    assert [n.text_src for n in notes] == ["Find the missing courier", "Deliver the package", "Deliver the package"]


def test_a_doubtful_reading_is_confirmed_by_a_second_one_before_it_is_shown():
    odd = ["Find the courier near the old Zorgan docks"]            # mostly real words, but the reader is not sure
    source, notes = make(Reader(odd, confidence=0.3), True, False)

    source.poll_once()
    assert notes == []
    source.poll_once()                                                         # no change, but a confirmation is due

    assert [n.text_src for n in notes] == [odd[0]] and source.ocr_calls == 2


def test_numbers_and_ammo_counters_are_not_translated():
    source, notes = make(Reader(["30 / 120"]), True)

    source.poll_once()

    assert notes == []


def test_each_corner_is_watched_on_its_own():
    source, notes = make(Reader(["Find the missing courier"], ["Reach the safe house"]), True, regions=2)

    source.poll_once()

    assert [n.text_src for n in notes] == ["Find the missing courier", "Reach the safe house"]


def test_garbled_text_such_as_a_video_title_is_not_shown():
    source, notes = make(Reader(["TA SAN ANDREAS GamepIay WaIktnrougN FULL GAME 4K 6UFPS"]), True)

    source.poll_once()

    assert notes == []


def test_corners_wait_while_the_subtitle_strip_needs_the_reader():
    notes = []
    busy = {"now": True}
    source = RegionNoteSource(lambda: [FRAME], Reader(["Find the missing courier"]), Translate(), notes.append,
                              watcher_factory=lambda: Scripted(True, True), defer=lambda: busy["now"])

    source.poll_once()
    assert source.ocr_calls == 0
    busy["now"] = False
    source.poll_once()

    assert [n.text_src for n in notes] == ["Find the missing courier"]
