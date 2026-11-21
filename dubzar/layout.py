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
