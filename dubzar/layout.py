"""Where on the screen the dialogue is: of everything read in the subtitle area, which lines belong together."""

from dubzar.ocr import OcrLine

MAX_GAP_LINES = 2.6      # lines closer than this many line heights belong to one block (name line, wrapped text)
ASSUMED_HEIGHT = 0.09    # when a reader does not say how tall its lines are: a typical share of the subtitle area


def dialogue_block(lines: list[OcrLine]) -> list[OcrLine]:
    """The block of lines that is the dialogue. A hint far above it (``HOLD TO USE ARMOR PLATES``), a quest line at
    the edge or a stray number sit in separate groups and are left out; of several groups, the one with the most
    words wins, and the lower one on a tie."""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda l: l.center_y)
    groups = [[ordered[0]]]
    for line in ordered[1:]:
        previous = groups[-1][-1]
        height = max(line.height, previous.height) or ASSUMED_HEIGHT
        if line.center_y - previous.center_y > MAX_GAP_LINES * height:
            groups.append([line])
        else:
            groups[-1].append(line)
    return max(groups, key=lambda g: (sum(len(l.text.split()) for l in g), g[-1].center_y))


STICKY_OTHERS = 3         # a line that stayed while this many different things were said around it is not dialogue
STICKY_SECONDS = 4.0
FORGET_SECONDS = 12.0


def _key(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


class StickyLines:
    """Objective and quest lines stay on screen while people talk ('Go to the club' under every subtitle). A line that
    has stayed through several different conversations is HUD, so it is taken out before the dialogue is chosen."""

    def __init__(self):
        self._seen: dict[str, list] = {}        # key -> [first seen, last seen, set of what was around it]

    def filter(self, lines: list[OcrLine], now: float) -> list[OcrLine]:
        return self.split(lines, now)[0]

    def split(self, lines: list[OcrLine], now: float) -> tuple[list[OcrLine], list[OcrLine]]:
        """(dialogue lines, HUD lines)"""
        for key in [k for k, rec in self._seen.items() if now - rec[1] > FORGET_SECONDS]:
            del self._seen[key]
        keys = [_key(l.text) for l in lines]
        for line, key in zip(lines, keys):
            if len(key) < 4 or line.text.rstrip().endswith(":"):
                continue                                   # too short to be sure, or a speaker's name
            around = frozenset(k for k in keys if k != key)
            record = self._seen.setdefault(key, [now, now, set()])
            record[1] = now
            record[2].add(around)
        kept, hud = [], []
        for line, key in zip(lines, keys):
            record = self._seen.get(key)
            sticky = (record is not None and now - record[0] >= STICKY_SECONDS
                      and len(record[2] - {frozenset()}) >= STICKY_OTHERS)
            (hud if sticky else kept).append(line)
        return kept, hud
