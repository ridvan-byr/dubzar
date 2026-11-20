"""Repairs what OCR typically gets wrong in English subtitles (I/l mix-ups, digits and brackets for letters, the
Turkish engine's accented letters, lost apostrophes), using a vocabulary of real English words.

The vocabulary comes for free from the translation model itself: its sentencepiece file holds every whole word the
model knows, with a frequency-like score. A word is only rewritten when it is NOT a known word and a small set of
look-alike substitutions turns it into one that is.
"""

import itertools
import math
import re
from functools import lru_cache
from pathlib import Path

TWO_LETTER_WORDS = set("an as at be by do go he if in is it me my no of oh ok on or so to up us we".split())
VALID_SUFFIXES = {"s", "t", "re", "ve", "ll", "d", "m"}                 # the part after the apostrophe
NEVER_WORDS = {                                                        # contractions that lost their apostrophe
    "dont": "don't", "cant": "can't", "didnt": "didn't", "doesnt": "doesn't", "isnt": "isn't", "arent": "aren't",
    "wasnt": "wasn't", "werent": "weren't", "hasnt": "hasn't", "havent": "haven't", "hadnt": "hadn't",
    "couldnt": "couldn't", "wouldnt": "wouldn't", "shouldnt": "shouldn't", "youre": "you're", "theyre": "they're",
    "ive": "I've", "youve": "you've", "weve": "we've", "theyve": "they've", "im": "I'm", "thats": "that's",
    "whats": "what's", "theres": "there's",
}
TURKISH_LETTERS = set("ıİşŞğĞçÇöÖüÜ")
FOLD = str.maketrans("ıİşŞğĞçÇöÖüÜâîû", "iIsSgGcCoOuUaiu")           # the Turkish engine's letters back to English
QUOTES = str.maketrans({"’": "'", "‘": "'", "´": "'", "`": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
STRAY = set("•§¤~^¬°¦*#@_=+<>{}\\·")
RUN = re.compile(r"[A-Za-z0-9'|\[\]]+")
# Some game fonts draw the apostrophe as a big tick that OCR reads as a letter or a mark: I've -> Ilve, don't -> don!t
APOSTROPHE_MARK = re.compile(r"(?<=[A-Za-z])[!:;|](?=(?:s|t|m|d|ll|ve|re)\b)")
LONE_I_SUFFIX = re.compile(r"\b[Il1|]\s+(m|ve|d)\b")             # "I m" : the apostrophe was dropped
I_CONTRACTION = re.compile(r"^[Il1|][lIJtij1!:;|](ve|m)$")          # Ilve, Itve, lJve, Ilm
SPLIT_PENALTY = 1.0
SHORT_PARTS = TWO_LETTER_WORDS | {"a", "i"}

# What each observed character may really be (lower case). Only used on words that are not real words.
LOOKALIKES = {
    "i": "l", "l": "i", "1": "li", "|": "li", "[": "li", "]": "li",
    "0": "o", "5": "s", "8": "b", "6": "bg", "2": "z", "z": "sx",
    "c": "eo", "e": "co", "u": "vn", "v": "uy", "n": "rhu", "r": "n", "h": "bk", "b": "h", "a": "oe", "o": "ae",
    "q": "g", "g": "q", "y": "v",
}
LETTER_L_CLASS = set("il1|[]")            # for names and capitalised words only these swaps are allowed
DIGRAPHS = {"rn": ["m"], "m": ["rn"], "vv": ["w"], "w": ["vv"], "cl": ["d"], "d": ["cl"], "li": ["h"], "ii": ["n", "u"]}
CHANGE_PENALTY = 2.0
RARE_LOGP = -10.0       # a real word this rare may still be a misreading of a much commoner one
RARE_MARGIN = 2.0       # ... if the commoner look-alike is better by this much after the change penalty


class Vocabulary:
    """Lower-case English words with a log-frequency score (higher = more common)."""

    def __init__(self, scores: dict[str, float]):
        self._scores = scores

    def known(self, word: str) -> bool:
        return word in self._scores

    def logp(self, word: str) -> float:
        return self._scores.get(word, -30.0)

    @classmethod
    def from_sentencepiece(cls, path: str | Path) -> "Vocabulary":
        import sentencepiece

        sp = sentencepiece.SentencePieceProcessor()
        sp.Load(str(path))
        scores: dict[str, float] = {}
        for i in range(sp.GetPieceSize()):
            piece = sp.IdToPiece(i)
            if not piece.startswith("▁"):
                continue
            word = piece[1:].lower()
            if not word.isascii() or not word.isalpha():
                continue
            if len(word) == 1 and word not in "ai" or len(word) == 2 and word not in TWO_LETTER_WORDS:
                continue   # short pieces are mostly word fragments, not words
            scores[word] = max(scores.get(word, -99.0), sp.GetScore(i))
        return cls(scores)


@lru_cache(maxsize=1)
def default_vocabulary() -> Vocabulary | None:
    """The vocabulary of the translation model installed on this computer, or None when it is not there."""
    try:
        from huggingface_hub import snapshot_download

        from dubzar.translate import MODEL_NAME, UNNEEDED_FILES

        folder = snapshot_download(MODEL_NAME, local_files_only=True, ignore_patterns=UNNEEDED_FILES)
        return Vocabulary.from_sentencepiece(Path(folder) / "source.spm")
    except Exception:  # noqa: BLE001 - no vocabulary just means no dictionary repair
        return None


def _is_word(vocab: Vocabulary, low: str) -> bool:
    if vocab.known(low):
        return True
    if "'" in low:
        stem, _, suffix = low.partition("'")
        return suffix in VALID_SUFFIXES and (vocab.known(stem) or (stem.endswith("n") and vocab.known(stem[:-1]))
                                              or stem in ("i", "don", "can", "won", "ain"))
    return False


def _variants(core: str, restricted: bool):
    """Candidate rewrites of ``core``: up to two look-alike substitutions (one letter class only when ``restricted``)."""
    low = core.lower()
    options = []
    for i, ch in enumerate(low):
        if restricted:
            alts = [a for a in LOOKALIKES.get(ch, "") if ch in LETTER_L_CLASS and a in "li"]
        else:
            alts = list(LOOKALIKES.get(ch, ""))
        if alts:
            options.append((i, alts))
    limit = 1 if restricted or len(low) < 5 else 2
    for count in range(1, limit + 1):
        for chosen in itertools.combinations(options, count):
            for alts in itertools.product(*[a for _, a in chosen]):
                chars = list(core)
                for (i, _), replacement in zip(chosen, alts):
                    upper = chars[i].isupper() and core.isupper()
                    chars[i] = replacement.upper() if upper else replacement
                yield "".join(chars), count
    if not restricted:
        for pattern, replacements in DIGRAPHS.items():
            if pattern in low:
                for replacement in replacements:
                    yield (low.replace(pattern, replacement) if core.islower() else core.replace(pattern, replacement)), 1


def _segment(core: str, vocab: Vocabulary) -> str | None:
    """Words that ran together ("tradefreely") split into the real words they are made of, or None."""
    low = core.lower()
    n = len(low)
    if n < 5 or not low.isalpha():
        return None
    best: list[tuple[float, list[int]] | None] = [None] * (n + 1)
    best[0] = (0.0, [])
    for end in range(1, n + 1):
        for start in range(max(0, end - 14), end):
            before = best[start]
            part = low[start:end]
            if before is None or len(before[1]) >= 3 or not vocab.known(part):
                continue
            if len(part) < 3 and part not in SHORT_PARTS:
                continue
            value = before[0] + vocab.logp(part) - SPLIT_PENALTY
            if best[end] is None or value > best[end][0]:
                best[end] = (value, before[1] + [end - start])
    if best[n] is None or len(best[n][1]) < 2:
        return None
    lengths = best[n][1]
    if min(lengths) <= 2 and n < 6:
        return None
    parts, position = [], 0
    for length in lengths:
        parts.append(core[position: position + length])
        position += length
    return " ".join(parts)


def _match_case(original: str, fixed: str) -> str:
    if original.isupper() and len(original) > 1:
        return fixed.upper()
    return fixed


def _fix_word(token: str, vocab: Vocabulary, sentence_start: bool) -> str:
    lead = token[: len(token) - len(token.lstrip("'"))]
    trail = token[len(token.rstrip("'")):] if token.rstrip("'") else ""
    core = token.strip("'")
    if not core or not any(c.isalpha() or c in "|[]" for c in core):
        return token                                   # numbers and the like
    low = core.lower()
    if core in ("l", "|", "[", "]"):
        return lead + "I" + trail                      # a lone stroke is the pronoun I
    if low in NEVER_WORDS:
        fixed = NEVER_WORDS[low]
        return lead + (fixed[0].upper() + fixed[1:] if core[0].isupper() or fixed[0] == "I" else fixed) + trail
    if any(c.isupper() for c in core[1:]) and not core.isupper() and _is_word(vocab, low):
        return lead + core[0] + core[1:].lower() + trail          # liKing, tHe: stray capitals inside a real word
    capitalised = core[0].isupper() and not core.isupper()
    known = _is_word(vocab, low)
    if not known and I_CONTRACTION.match(core):
        return lead + "I'" + ("ve" if low.endswith("ve") else "m") + trail     # Ilve -> I've, Ilm -> I'm
    if known and (capitalised or core.isupper() or vocab.logp(low) >= RARE_LOGP):
        return token                                   # a normal word, or a name that may be one
    if core.isupper() and len(core) <= 3:
        return token                                   # an acronym
    best, best_value = None, None
    for candidate, changes in _variants(core, restricted=capitalised):
        cand_low = candidate.lower()
        if not _is_word(vocab, cand_low):
            continue
        value = vocab.logp(cand_low) - CHANGE_PENALTY * changes
        if best_value is None or value > best_value:
            best, best_value = candidate, value
    if best is None and not known and not capitalised:
        split = _segment(core, vocab)
        if split:
            return lead + (split[0].upper() + split[1:] if sentence_start else split) + trail
    if best is None or (known and best_value <= vocab.logp(low) + RARE_MARGIN):
        return token
    best = _match_case(core, best)
    if sentence_start or (core[0].isupper() and not capitalised):
        best = best[0].upper() + best[1:]
    return lead + best + trail


def _sentence_starts(text: str):
    """Yield (match, at_sentence_start) for each word-like run in ``text``."""
    for match in RUN.finditer(text):
        before = text[: match.start()].rstrip()
        yield match, (not before) or before[-1] in ".!?:" or before.endswith("-")


def fix_text(text: str, vocab: Vocabulary | None = None) -> str:
    """The text with common OCR misreadings repaired; unchanged words stay exactly as they were."""
    vocab = vocab or default_vocabulary()
    text = text.translate(FOLD).translate(QUOTES)
    text = LONE_I_SUFFIX.sub(lambda m: "I'" + m.group(1), APOSTROPHE_MARK.sub("'", text))
    if vocab is not None:
        pieces, last = [], 0
        for match, start in _sentence_starts(text):
            pieces.append(text[last: match.start()])
            word = _fix_word(match.group(), vocab, start)
            before = text[: match.start()].rstrip()
            if (before and before[-1] in ".!?" and not before.endswith("..") and word[:1].islower()
                    and word.isalpha() and len(word) > 1):
                word = word[0].upper() + word[1:]          # a new sentence begins here
            pieces.append(word)
            last = match.end()
        pieces.append(text[last:])
        text = "".join(pieces)
    text = "".join(c for c in text if c not in STRAY)
    return re.sub(r"\s+", " ", text).strip()


def word_counts(text: str, vocab: Vocabulary | None = None) -> tuple[float, float]:
    """(credit, total): how many of the words are real English (capitalised unknown words, probably names, count for
    half) out of all of them."""
    vocab = vocab or default_vocabulary()
    if vocab is None:
        return 0.0, 0.0
    credit = total = 0.0
    for match in RUN.finditer(text):
        core = match.group().strip("'")
        if not any(c.isalpha() for c in core):
            continue
        total += 1
        low = core.lower()
        if _is_word(vocab, low) or low in NEVER_WORDS:
            credit += 1
        elif core[0].isupper() and len(core) > 2:
            credit += 0.5
    return credit, total


def text_quality(text: str, vocab: Vocabulary | None = None) -> float:
    """0..1: the share of real English words in the text."""
    credit, total = word_counts(text, vocab)
    return credit / total if total else 0.0
