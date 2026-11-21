"""A subtitle must reach the screen quickly: one confident reading is enough, the picture is only read when its
text changed, and a cheap look at the strip decides when."""

import numpy as np
import pytest

from dubzar.ocr import OcrLine
from dubzar.screen_source import ScreenSubtitleSource
from dubzar.subtitle_tracker import SubtitleTracker, Update

LINE = "Keep your head down and stay quiet."
OTHER = "We need more time, they are almost here."


class FakeOcr:
    def __init__(self, *readings, confidence=0.97):
        self.readings, self.confidence, self.calls = list(readings), confidence, 0

    def read(self, image):
        self.calls += 1
        text = self.readings.pop(0) if self.readings else self.last
        self.last = text
        return [OcrLine(text, 0.5, 0.6, 0.09, self.confidence)] if text else []


class Translate:
    def translate(self, text, context=()):
        return "TR: " + text


class Watcher:
    """Scripted 'did the text change?' answers."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.commits = 0

    def changed(self, frame):
        return self.answers.pop(0) if self.answers else False

    def commit(self):
        self.commits += 1


FRAME = np.full((60, 200, 3), 90, dtype=np.uint8)


def make(ocr, watcher, clock=None):
    cues, clears = [], []
    kwargs = {"clock": clock} if clock else {}
    source = ScreenSubtitleSource(lambda: FRAME, ocr, Translate(), cues.append, lambda: clears.append(1),
                                  watcher=watcher, **kwargs)
    return source, cues, clears


# --- the tracker -----------------------------------------------------------------------------------------------
def test_a_trusted_reading_confirms_a_new_subtitle_at_once():
    tracker = SubtitleTracker()

    assert tracker.update([LINE], trusted=True) == Update(LINE, False)
    assert tracker.update([LINE], trusted=True) == Update(None, False)           # the same subtitle: nothing new


def test_a_trusted_reading_replaces_the_current_subtitle_at_once():
    tracker = SubtitleTracker()
    tracker.update([LINE], trusted=True)

    assert tracker.update([OTHER], trusted=True).text == OTHER


def test_an_untrusted_reading_still_needs_a_second_sighting():
    tracker = SubtitleTracker()

    assert tracker.update([LINE]).text is None
    assert tracker.update([LINE]).text == LINE


def test_the_tracker_says_when_it_is_waiting_for_more_readings():
    tracker = SubtitleTracker(gone_frames=2)
    assert not tracker.unsettled                                 # nothing going on

    tracker.update([LINE])
    assert tracker.unsettled                                     # a candidate waiting for its second sighting
    tracker.update([LINE])
    assert not tracker.unsettled                                 # confirmed and showing: settled

    tracker.update([])
    assert tracker.unsettled                                     # it may be gone: needs another empty reading
    tracker.update([])
    assert not tracker.unsettled                                 # cleared


# --- the source ------------------------------------------------------------------------------------------------
def test_one_confident_reading_shows_the_translation():
    source, cues, _ = make(FakeOcr(LINE), Watcher(True))

    source.poll_once()

    assert [c.text_tr for c in cues] == ["TR: " + LINE]
    assert source.ocr_calls == 1


def test_an_unchanged_strip_is_not_read_again():
    source, cues, _ = make(FakeOcr(LINE), Watcher(True, False, False, False))

    for _ in range(4):
        source.poll_once()

    assert source.ocr_calls == 1 and len(cues) == 1


def test_a_changed_strip_is_read_again_and_the_new_subtitle_shown():
    source, cues, _ = make(FakeOcr(LINE, OTHER), Watcher(True, False, True))

    for _ in range(3):
        source.poll_once()

    assert [c.text_src for c in cues] == [LINE, OTHER]


ODD = "Zorgon flimbar quizzle wobbly frumpet snorkel."          # five words no dictionary knows


def test_an_untrusted_reading_is_confirmed_by_reading_again_even_though_the_picture_did_not_change():
    source, cues, _ = make(FakeOcr(ODD, confidence=0.0), Watcher(True, False))

    source.poll_once()
    assert cues == []                                            # one sighting is not enough
    source.poll_once()                                           # the strip did not change, but a confirmation is due

    assert [c.text_src for c in cues] == [ODD] and source.ocr_calls == 2


def test_a_doubtful_reader_whose_text_is_clean_english_is_trusted_by_the_dictionary():
    """Two lines out of three were not sure, but the merged text is a complete, ordinary English sentence."""
    source, cues, _ = make(FakeOcr(LINE, confidence=0.6), Watcher(True))

    source.poll_once()

    assert [c.text_src for c in cues] == [LINE] and source.ocr_calls == 1


def test_a_short_clean_fragment_is_not_trusted_by_the_dictionary_alone():
    source, cues, _ = make(FakeOcr("Keep your head", confidence=0.6), Watcher(True, False))

    source.poll_once()

    assert cues == []


def test_a_subtitle_that_goes_away_is_cleared_even_though_nothing_else_changes():
    source, cues, clears = make(FakeOcr(LINE, "", ""), Watcher(True, True, False, False))

    for _ in range(4):
        source.poll_once()

    assert clears == [1]


def test_a_forgotten_strip_is_read_now_and_then_anyway():
    now = {"t": 0.0}
    source, cues, _ = make(FakeOcr(LINE), Watcher(True), clock=lambda: now["t"])
    source.poll_once()
    calls = source.ocr_calls

    now["t"] += 10.0                                             # a long quiet time: the heartbeat reads once more
    source.poll_once()

    assert source.ocr_calls == calls + 1


def test_readings_that_find_nothing_make_polling_back_off_and_finding_a_subtitle_resets_it():
    source, _, _ = make(FakeOcr("", "", "", "", LINE), Watcher(True, True, True, True, True))

    for _ in range(4):
        source.poll_once()
    backed_off = source.current_wait
    source.poll_once()

    assert backed_off >= 1.0                             # readings kept finding nothing: far apart
    assert source.current_wait == 0.2                    # a subtitle appeared: the quick rhythm again


def test_looking_is_slow_while_no_subtitle_has_been_seen_for_a_while_and_quick_during_a_conversation():
    """A look costs a screenshot (about 50 ms): in plain gameplay, which is most of the time, it is done less often."""
    now = {"t": 0.0}
    source, _, _ = make(FakeOcr(LINE), Watcher(True), clock=lambda: now["t"])

    assert source.current_wait == 0.6                    # nothing seen yet: relaxed
    source.poll_once()
    assert source.current_wait == 0.2                    # a subtitle: quick
    now["t"] += 14
    assert source.current_wait == 0.2                    # a short pause in the conversation: still quick
    now["t"] += 10
    assert source.current_wait == 0.6                    # a long quiet time: relaxed again


def test_the_delay_from_appearing_to_showing_is_recorded():
    now = {"t": 100.0}
    source, _, _ = make(FakeOcr(LINE), Watcher(True), clock=lambda: now["t"])

    source.poll_once()

    assert source.last_latency_s == pytest.approx(0.0, abs=1e-6)
