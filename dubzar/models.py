from dataclasses import dataclass


@dataclass(frozen=True)
class Cue:
    """One indexed voice line with its Turkish subtitle."""

    line_id: str
    text_src: str
    text_tr: str
    duration_s: float
    speaker: str | None = None
    until_cleared: bool = False   # shown while the game's own subtitle is on screen, not for a fixed time


@dataclass(frozen=True)
class MatchResult:
    """Result of matching live audio against the index."""

    line_id: str
    offset_frames: int
    votes: int
