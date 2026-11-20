"""Getting a subtitle picture ready for text recognition. Game subtitles are small, sit on busy scenes, and are
usually light letters with a dark outline: separating the letters from the scene before reading removes most of
the garbage a reader produces on a cluttered background. All steps return an RGB image (black text on white
where the text was isolated)."""

import numpy as np
from PIL import Image
from scipy import ndimage

UPSCALE = 2
BRIGHT_FLOOR = 150          # letters are never darker than this
OUTLINE_REACH = 3           # pixels: how close to a dark pixel a letter pixel must be


def _luminance(frame: np.ndarray) -> np.ndarray:
    f = frame.astype(np.float32)
    return 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]


def upscale(frame: np.ndarray, factor: int = UPSCALE) -> np.ndarray:
    height, width = frame.shape[:2]
    return np.asarray(Image.fromarray(frame).resize((width * factor, height * factor), Image.LANCZOS))


def _mask_to_image(mask: np.ndarray) -> np.ndarray:
    """A boolean text mask as black letters on white, enlarged with smooth edges."""
    gray = np.where(mask, 0, 255).astype(np.uint8)
    big = Image.fromarray(gray).resize((gray.shape[1] * UPSCALE, gray.shape[0] * UPSCALE), Image.BICUBIC)
    return np.asarray(big.convert("RGB"))


def _bright_threshold(lum: np.ndarray, percentile: float = 96) -> float:
    return float(min(235.0, max(BRIGHT_FLOOR, np.percentile(lum, percentile))))


def bright_on_white(frame: np.ndarray) -> np.ndarray:
    lum = _luminance(frame)
    return _mask_to_image(lum >= _bright_threshold(lum))


def dark_on_white(frame: np.ndarray) -> np.ndarray:
    lum = _luminance(frame)
    return _mask_to_image(lum <= float(np.percentile(lum, 7)) + 25)


def outlined_on_white(frame: np.ndarray) -> np.ndarray:
    """Letters only where a bright pixel sits right next to a dark one (the outline): a big bright wall or sky has
    no such edge pixels inside it, and is dropped."""
    lum = _luminance(frame)
    bright = lum >= max(BRIGHT_FLOOR, _bright_threshold(lum) - 25)
    dark = lum <= 70
    near_dark = ndimage.binary_dilation(dark, iterations=OUTLINE_REACH)
    letters = bright & near_dark
    letters = ndimage.binary_closing(letters, iterations=1) | letters
    return _mask_to_image(letters)


def contrast_on_white(frame: np.ndarray, boost: float = 45.0) -> np.ndarray:
    """Letters are pixels clearly brighter than their own neighbourhood: works when a bright patch or box sits behind
    the text, where a plain brightness threshold would pick up the whole patch."""
    lum = _luminance(frame)
    return _mask_to_image(lum > ndimage.uniform_filter(lum, size=31) + boost)


def variants(frame: np.ndarray):
    """(name, image) in the order they are worth trying. Measured on synthetic game subtitles (experiments/
    ocr_variant_study.py): the enlarged picture is the best single reading, and each of the others is right on
    frames the rest get wrong, so together they read far more than any one alone."""
    yield "x2", upscale(frame)
    yield "raw", frame
    yield "bright", bright_on_white(frame)
    yield "dark", dark_on_white(frame)
    yield "contrast", contrast_on_white(frame)
    yield "x3", upscale(frame, 3)
