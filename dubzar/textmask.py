"""A very cheap look at the subtitle strip: did the text-like pixels change? Reading the strip costs half a second;
this costs a few milliseconds, so it can be done many times a second and the expensive reading only runs when a
subtitle appeared, changed or went away."""

import numpy as np
from scipy import ndimage

STEP = 2                  # look at every second pixel: letters are still several pixels wide
BRIGHT_FLOOR = 150        # letters are never darker than this
OUTLINE_REACH = 2         # a letter pixel sits within this many (small) pixels of a dark one
CHANGE_THRESHOLD = 0.4    # share of text-like pixels that differ from the last reading
STILL_THRESHOLD = 0.5    # text-like pixels that moved more than this since the last look are not a subtitle
MIN_PIXELS = 30          # fewer text-like pixels than this: no subtitle


def text_mask(frame: np.ndarray) -> np.ndarray:
    """Bright pixels with a dark neighbourhood: what game subtitles are made of (light letters, dark outline)."""
    small = frame[::STEP, ::STEP].astype(np.float32)
    lum = 0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]
    bright = lum >= max(BRIGHT_FLOOR, float(np.percentile(lum, 96)) - 15)
    near_dark = ndimage.binary_dilation(lum <= 80, iterations=OUTLINE_REACH)
    return bright & near_dark


def mask_distance(a: np.ndarray, b: np.ndarray) -> float:
    """0 for identical masks, 1 for masks with nothing in common."""
    union = int((a | b).sum())
    return 0.0 if union == 0 else 1.0 - int((a & b).sum()) / union


class TextChangeWatcher:
    """``changed(frame)`` says whether the text-like pixels differ from those of the last *committed* frame (the last
    one that was actually read) and have stayed put since the look before. A subtitle stands still for seconds, while
    bright, dark-edged shapes in a moving game scene are somewhere else on every look: only the still ones count.
    ``commit()`` makes the frame just looked at the new reference."""

    def __init__(self, threshold: float = CHANGE_THRESHOLD, min_pixels: int = MIN_PIXELS,
                 still_threshold: float = STILL_THRESHOLD):
        self._threshold = threshold
        self._min_pixels = min_pixels
        self._still = still_threshold
        self._reference: np.ndarray | None = None
        self._latest: np.ndarray | None = None
        self._previous: np.ndarray | None = None
        self.settling = False         # True: the picture just turned from calm to different - look again right away

    def changed(self, frame: np.ndarray) -> bool:
        self._previous, self._latest = self._latest, text_mask(frame)
        self.settling = False
        if self._previous is None or self._previous.shape != self._latest.shape:
            return False                                   # nothing to compare with yet
        if mask_distance(self._previous, self._latest) > self._still:
            # moving: not text, or text that has only just appeared. It is worth a quick second look only when the
            # look before was calm (a subtitle appearing); a scene that never settles is looked at once per poll.
            if self._reference is None:
                self.settling = int(self._previous.sum()) < self._min_pixels
            else:
                self.settling = (self._reference.shape == self._previous.shape
                                 and mask_distance(self._reference, self._previous) <= self._threshold)
            return False
        if self._reference is None:
            return int(self._latest.sum()) >= self._min_pixels
        if max(int(self._latest.sum()), int(self._reference.sum())) < self._min_pixels:
            return False                                   # nothing text-like then, nothing now
        if self._latest.shape != self._reference.shape:
            return True
        return mask_distance(self._reference, self._latest) > self._threshold

    def commit(self) -> None:
        self._reference = self._latest
