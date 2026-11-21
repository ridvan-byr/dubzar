"""Dialogue and objective lines are different channels: two people talking are translated apart, and a quest line
that stays on screen becomes a short note instead of being glued to the subtitle."""

import numpy as np

from dubzar.ocr import OcrLine
from dubzar.screen_source import ScreenSubtitleSource

FRAME = np.full((60, 200, 3), 90, dtype=np.uint8)


class Reads:
    def __init__(self, *screens):
        self.screens = list(screens)

    def read(self, image):
        return self.screens.pop(0) if self.screens else self.last_screen

    @property
    def last_screen(self):
        return []


class Translate:
    def __init__(self):
        self.asked = []

    def translate(self, text, context=()):
        self.asked.append(text)
        return "TR(" + text + ")"


class Always:
    def changed(self, frame):
        return True

    def commit(self):
        pass


def line(text, y, confidence=0.97):
    return OcrLine(text, 0.5, y, 0.05, confidence)


def make(screens):
    cues, notes = [], []
    translator = Translate()
    source = ScreenSubtitleSource(lambda: FRAME, Reads(*screens), translator, cues.append, lambda: None,
                                  watcher=Always(), on_note=notes.append)
    return source, cues, notes, translator


def test_two_people_talking_at_once_are_translated_and_shown_as_two_lines():
    both = [line("Nate: Yeah, I know it.", 0.70), line("Rafe: Then why did you ask?", 0.78)]
    source, cues, _, translator = make([both])

    source.poll_once()

    assert translator.asked == ["Nate: Yeah, I know it.", "Rafe: Then why did you ask?"]
    assert cues[0].text_tr == "TR(Nate: Yeah, I know it.)\nTR(Rafe: Then why did you ask?)"


def test_a_quest_line_that_stays_becomes_a_note_and_stays_out_of_the_subtitle():
    quest = line("Go to the club", 0.86)
    talk = ["Keep your head down.", "We need more time.", "They are almost here.", "Stay close to me, please."]
    clock = {"t": 0.0}
    cues, notes = [], []
    translator = Translate()
    screens = [[line(said, 0.78), quest] for said in talk]
    source = ScreenSubtitleSource(lambda: FRAME, Reads(*screens), translator, cues.append, lambda: None,
                                  watcher=Always(), on_note=notes.append, clock=lambda: clock["t"])

    for _ in talk:
        source.poll_once()
        clock["t"] += 2.0

    assert [n.text_src for n in notes] == ["Go to the club"]                    # noticed once, after it stayed
    assert notes[0].duration_s > 0 and not notes[0].until_cleared
    assert cues[-1].text_src == talk[-1]                                        # the last subtitle is clean
