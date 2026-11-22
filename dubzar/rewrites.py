"""English-side rewrites: slang, idioms and game senses that a general translation model reads wrongly are put into plainer English
before translation ("got jumped" -> "was ambushed"). Each rewrite was checked against the model (the plainer sentence translates
well); text that does not match is left exactly as it was.
"""

import re
from typing import Callable

_SAVE_OBJECT = re.compile(r"\b(game|progress|data|file|settings|changes|profile|character|slot)\b", re.IGNORECASE)
_SAVE_WORD = re.compile(r"\bsav(e|es|ed|ing)\b", re.IGNORECASE)
_SAVE_AS_RECORD = {"e": "record", "es": "records", "ed": "recorded", "ing": "recording"}      # "recorded" -> "kaydedildi"


def _keep_case(original: str, replacement: str) -> str:
    return replacement[0].upper() + replacement[1:] if original[:1].isupper() else replacement


def _save_sense(text: str) -> str:
    """"Your game has been saved" is about storing, not rescuing: the model says "kurtarıldı". "Recorded" gets "kaydedildi"."""
    if not (_SAVE_OBJECT.search(text) and _SAVE_WORD.search(text)):
        return text
    return _SAVE_WORD.sub(lambda m: _keep_case(m.group(), _SAVE_AS_RECORD[m.group(1).lower()]), text)


def _simple(pattern: str, replacement: str) -> Callable[[str], str]:
    compiled = re.compile(pattern, re.IGNORECASE)
    return lambda text: compiled.sub(lambda m: _keep_case(m.group(), replacement), text)


def _mapped(pattern: str, mapping: dict[str, str]) -> Callable[[str], str]:
    compiled = re.compile(pattern, re.IGNORECASE)
    return lambda text: compiled.sub(lambda m: _keep_case(m.group(), mapping[m.group(1).lower()]), text)


def _tip_off(text: str) -> str:
    return re.sub(r"\btip(ped|s|ping)? (me|you|him|her|us|them|\w+) off\b",
                  lambda m: {"ped": "warned", "s": "warns", "ping": "warning", None: "warn"}[m.group(1) and m.group(1).lower()] + " " + m.group(2),
                  text, flags=re.IGNORECASE)


def _tick_off(text: str) -> str:
    return re.sub(r"\btick(ed|s|ing)? (me|you|him|her|us|them) off\b",
                  lambda m: {"ed": "annoyed", "s": "annoys", "ing": "annoying", None: "annoy"}[m.group(1) and m.group(1).lower()] + " " + m.group(2),
                  text, flags=re.IGNORECASE)


REWRITES: list[Callable[[str], str]] = [
    _save_sense,
    _mapped(r"\b(got|get|gets|getting) jumped\b", {"got": "was ambushed", "get": "get ambushed", "gets": "gets ambushed",
                                                  "getting": "getting ambushed"}),
    _simple(r"\bball[- ]?buster(?=s?\b)", "troublemaker"),
    _simple(r"\bno dice\b", "not happening"),
    _simple(r"\bwannabe\b", "poser"),
    lambda text: re.sub(r"\b(?:the )?timer (?:expires|runs out|ends)\b", "time runs out", text, flags=re.IGNORECASE),
    _tip_off,
    _tick_off,
    _simple(r"\bcut the crap\b", "stop the nonsense"),
    _simple(r"^beat it\b", "get lost"),
    _simple(r"\bfreaking\b", "really"),
    _simple(r"\bson of a gun\b", "rascal"),
    lambda text: re.sub(r"\b(evil|darkness|something|beast|monster|power|force) stirs\b", r"\1 is awakening", text,
                        flags=re.IGNORECASE),
    _simple(r"^take out (?=the |a |an |all |every )", "kill "),
    _simple(r"\blet it be known that\b", "everyone should know that"),
    _simple(r"\bagainst the crown\b", "against the king"),
    _simple(r"\bpulling my leg\b", "joking with me"),
    _mapped(r"\b(this|that|my|your|his|her|their|our) ride\b", {"this": "this car", "that": "that car", "my": "my car",
                                                                 "your": "your car", "his": "his car", "her": "her car",
                                                                 "their": "their car", "our": "our car"}),
]


def apply_rewrites(text: str) -> str:
    for rewrite in REWRITES:
        text = rewrite(text)
    return text
