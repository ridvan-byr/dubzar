from dataclasses import dataclass


@dataclass(frozen=True)
class Cue:
    """One indexed voice line with its Turkish subtitle."""

    line_id: str
    text_src: str
    text_tr: str
    duration_s: float
    speaker: str | None = None


@dataclass(frozen=True)
class MatchResult:
    """Result of matching live audio against the index."""

    line_id: str
    offset_frames: int
    votes: int
