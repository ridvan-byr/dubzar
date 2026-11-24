"""Game text speaks to the player as "sen". The model writes commands in the polite plural ("Rehineleri kurtarın."); for a bare
English command this puts the last word in the singular ("kurtar"). Only a one-clause command is touched, so a sentence is never
left half plural and half singular.
"""

import re

IMPERATIVE_VERBS = frozenset("""
accept activate approach arm ask attack avoid back bring break buy call capture carry catch check choose clear climb close collect
come complete confirm continue cover craft crouch defeat defend defuse deliver destroy disable disarm drag drive drop eliminate
enter equip escape escort examine exit explore find finish fire fix flee fly follow get give go grab guard hack head heal help hide
hit hold hurry insert inspect interact investigate jump keep kill leave let listen load lock look lose make meet move open pay
pick place plant press protect pull push put reach read reload remember repair rescue retreat return run save scan search select
sell shoot show sneak speak start stay steal stop swim switch take talk target throw track trust try turn unlock upgrade use wait
watch wear
ambush aim block dodge distract infiltrate lead lure rob sabotage sit stand tell warn wake tap survive chase pursue ignore stab slash sprint breach clean cut dig fill grab hang haul jam kick knock lift mark mix pass pour prepare raise rush set shut sit stack tie wipe
""".split())

_WORD = re.compile(r"[A-Za-z']+")
_END = re.compile(r"^(?P<body>.*?)(?P<word>[^\s.!?…,;:]+)(?P<tail>[.!?…\"')]*)$", re.DOTALL)
_SOFTENED = {"gid": "git", "ed": "et"}                  # gidin -> git, edin -> et


def is_command(english: str) -> bool:
    """A bare, one-clause command: starts with a command verb (or "Don't" + verb), no comma, no "and"."""
    text = english.strip()
    if "," in text or re.search(r"\band\b", text, re.IGNORECASE):
        return False
    words = _WORD.findall(text)
    if not words:
        return False
    first = words[0].lower()
    if first in ("don't", "never"):
        first = words[1].lower() if len(words) > 1 else ""
    elif first == "do" and len(words) > 2 and words[1].lower() == "not":
        first = words[2].lower()
    return first in IMPERATIVE_VERBS


def _singular(word: str) -> str:
    low = word.lower()
    if len(low) < 4:
        return word
    if low.endswith(("yın", "yin", "yun", "yün")):
        stem = word[:-3]
    elif low.endswith(("ın", "in", "un", "ün")):
        stem = word[:-2]
    else:
        return word
    return _SOFTENED.get(stem.lower(), stem) if stem.lower() in _SOFTENED else stem


def singular_command(turkish: str) -> str:
    """The last word of ``turkish`` from polite plural to singular command, if it looks like one."""
    match = _END.match(turkish.strip())
    if not match:
        return turkish
    return match.group("body") + _singular(match.group("word")) + match.group("tail")
