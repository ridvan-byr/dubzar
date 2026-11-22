"""Splits a subtitle into sentences and speaker names, so a translator sees one sentence at a time
(models tend to drop whole sentences from multi-sentence input) and never sees "Brian:" as part of the words."""

import re
from dataclasses import dataclass

ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "st", "jr", "sr", "vs", "etc", "prof", "sgt", "lt", "capt", "col", "gen",
                 "no", "inc", "co", "mt"}
NOT_SPEAKERS = {"note", "warning", "tip", "objective", "hint", "remember", "mission", "goal", "task", "caution",
                "important", "attention", "press", "hold", "reminder", "update", "new", "quest",
                # interface labels ("Difficulty: Hard", "Controls: Move, Aim"): a label word that is an ordinary noun is a
                # label, not a person. (A real speaker taken for a label costs little: the name just goes through the model.)
                "difficulty", "controls", "control", "optional", "options", "option", "settings", "setting", "volume",
                "brightness", "language", "health", "ammo", "level", "score", "time", "status", "mode", "chapter", "goals",
                "reward", "rewards", "requirement", "requirements", "location", "destination", "distance", "weight",
                "damage", "speed", "range", "price", "cost", "stats", "name", "class", "type", "skill", "skills", "wanted",
                "tutorial", "info", "information", "description", "effect", "effects", "duration", "cooldown", "armor",
                "armour", "attack", "defense", "defence", "strength", "agility", "stamina", "energy", "mana", "gold",
                "money", "cash", "xp", "rank", "title", "subtitles", "audio", "video", "graphics", "display", "resolution",
                "quality", "sensitivity", "vibration", "save", "load", "slot", "empty", "continue", "day", "part", "act",
                "episode", "page", "result", "results", "progress", "target", "targets", "enemies", "bonus", "tasks",
                "objectives", "missions", "current", "next", "last", "total", "available", "unavailable", "locked"}

_END = re.compile(r"[.!?]+[\"')\]]*\s+")
_NAME_WORD = r"[A-Z][A-Za-z.'\-]*"
_LABEL = re.compile(rf"^({_NAME_WORD}(?: {_NAME_WORD}){{0,2}}):\s+(\S.*)$", re.DOTALL)


@dataclass(frozen=True)
class Piece:
    speaker: str | None
    text: str


def _sentences(text: str) -> list[str]:
    sentences, start = [], 0
    for match in _END.finditer(text):
        before = text[start:match.start()].split()
        last_word = before[-1].strip("\"'([").lower() if before else ""
        nxt = text[match.end():match.end() + 2]
        capital_next = bool(nxt) and (nxt[0].isupper() or (nxt[0] in "\"'([" and len(nxt) > 1 and nxt[1].isupper()))
        initial = len(last_word) == 1 and last_word.isalpha()           # "J. Smith"
        abbreviated = match.group().startswith(".") and (last_word in ABBREVIATIONS or initial)
        if capital_next and not abbreviated:
            sentences.append(text[start:match.end()].strip())
            start = match.end()
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def split_pieces(text: str) -> list[Piece]:
    """Sentences in order, each with the speaker named in front of it (if any)."""
    pieces = []
    for sentence in _sentences(re.sub(r"\s+", " ", text).strip()):
        match = _LABEL.match(sentence)
        if (match and not any(word.rstrip(".").lower() in NOT_SPEAKERS for word in match.group(1).split())
                and re.search(r"[^\W\d_]", match.group(2))):       # "Fuel: 40%" is a label and a value, not words spoken
            pieces.append(Piece(match.group(1), match.group(2).strip()))
        else:
            pieces.append(Piece(None, sentence))
    return pieces
