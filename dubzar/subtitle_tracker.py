"""Decides, from what OCR reads on screen frame after frame, which text is the game's current subtitle."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

TURKISH_ONLY = set("şğıçöüİŞĞÇÖÜ")
MIN_CHARS = 8
MIN_WORDS = 2
SAME_RATIO = 0.85   # OCR wobbles between frames ("Iooking" / "looking"): texts this alike are the same subtitle


@dataclass(frozen=True)
class Update:
    text: str | None     # a new subtitle was just confirmed
    cleared: bool        # the subtitle that was showing has gone from the screen


def _line_ok(line: str) -> bool:
    visible = [c for c in line if not c.isspace()]
    if len(visible) < 4:
        return False
    letters = sum(c.isalpha() for c in visible)
    if letters / len(visible) < 0.6:
        return False
    return sum(c in TURKISH_ONLY for c in line) < 2  # our own Turkish text, not the game's


def subtitle_text(lines: list[str]) -> str | None:
    """The lines that look like subtitle text, joined; None when nothing on screen looks like a subtitle."""
    kept = [line.strip() for line in lines if _line_ok(line)]
    if not any(len(line.split()) >= MIN_WORDS for line in kept):  # a lone token is a logo or a sign, not speech
        return None
    text = re.sub(r"\s+", " ", " ".join(kept)).strip()
    return text if len(text) >= MIN_CHARS else None


def _normal(text: str) -> str:
    # capital I, lower-case l, 1 and | look alike to OCR
    return re.sub(r"[Il1|]", "l", text.lower())


def same_subtitle(a: str, b: str) -> bool:
    return SequenceMatcher(None, _normal(a), _normal(b)).ratio() >= SAME_RATIO


class SubtitleTracker:
    """Feed it the OCR lines of each frame. A subtitle counts once it has been seen in two frames in a row
    (a half-drawn or flashing text is not a subtitle yet) and ends after ``gone_frames`` frames without it."""

    def __init__(self, gone_frames: int = 2):
        self._gone_frames = gone_frames
        self._current: str | None = None
        self._candidate: str | None = None
        self._candidate_count = 0
        self._gone = 0

    def update(self, lines: list[str]) -> Update:
        text = subtitle_text(lines)
        if text is None:
            self._candidate, self._candidate_count = None, 0
            self._gone += 1
            if self._current is not None and self._gone >= self._gone_frames:
                self._current = None
                return Update(None, True)
            return Update(None, False)

        self._gone = 0
        if self._current is not None and same_subtitle(text, self._current):
            self._candidate, self._candidate_count = None, 0
            return Update(None, False)
        if self._candidate is not None and same_subtitle(text, self._candidate):
            self._candidate_count += 1
        else:
            self._candidate, self._candidate_count = text, 1
        if self._candidate_count >= 2:
            self._current = text
            self._candidate, self._candidate_count = None, 0
            return Update(text, False)
        return Update(None, False)
