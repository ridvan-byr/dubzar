"""Windows' built-in text recognition (no download, no GPU): reads the text in a screenshot."""

import asyncio
from dataclasses import dataclass

import numpy as np

from dubzar import imageprep
from dubzar.textfix import TURKISH_LETTERS, Vocabulary, fix_text, text_quality, word_counts

PREFERRED_LANGUAGES = ("en-US", "en-GB", "en")   # English subtitles; any installed Latin-script engine is the fallback


@dataclass(frozen=True)
class OcrLine:
    text: str
    center_x: float   # 0..1 across the image
    center_y: float   # 0..1 down the image


class WindowsOcr:
    """``read(rgb_image)`` -> the text lines Windows OCR finds, with where they are on the image."""

    def __init__(self) -> None:
        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine

        engine = None
        for tag in PREFERRED_LANGUAGES:
            engine = OcrEngine.try_create_from_language(Language(tag))
            if engine is not None:
                break
        if engine is None:
            engine = OcrEngine.try_create_from_user_profile_languages()  # e.g. only Turkish installed: Latin letters still read
        if engine is None:
            raise RuntimeError("Windows OCR is not available on this computer (no OCR language installed)")
        self._engine = engine
        self.language = engine.recognizer_language.language_tag

    def read(self, image: np.ndarray) -> list[OcrLine]:
        return asyncio.run(self._read(image))

    async def _read(self, image: np.ndarray) -> list[OcrLine]:
        from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.storage.streams import DataWriter

        height, width = image.shape[:2]
        bgra = np.empty((height, width, 4), dtype=np.uint8)
        bgra[..., 0], bgra[..., 1], bgra[..., 2], bgra[..., 3] = image[..., 2], image[..., 1], image[..., 0], 255
        writer = DataWriter()
        writer.write_bytes(bgra.tobytes())
        bitmap = SoftwareBitmap.create_copy_from_buffer(writer.detach_buffer(), BitmapPixelFormat.BGRA8, width, height)
        result = await self._engine.recognize_async(bitmap)
        lines = []
        for line in result.lines:
            words = list(line.words)
            if not words:
                continue
            left = min(w.bounding_rect.x for w in words)
            right = max(w.bounding_rect.x + w.bounding_rect.width for w in words)
            top = min(w.bounding_rect.y for w in words)
            bottom = max(w.bounding_rect.y + w.bounding_rect.height for w in words)
            lines.append(OcrLine(line.text, (left + right) / 2 / width, (top + bottom) / 2 / height))
        return lines


class RobustOcr:
    """Reads a subtitle picture reliably: tries the picture as it is, and if the result does not look like English,
    the same picture prepared in other ways (enlarged, letters separated from the scene), repairs the usual
    misreadings, and keeps the reading with the most real words. Cheap when the first reading is already good."""

    GOOD_ENOUGH = 0.85           # share of real words at which no further variant is tried
    GARBAGE_PENALTY = 0.6        # an unknown word costs this much of a known word's credit
    AGREEMENT_BONUS = 1.0        # each further variant that reads the same text is worth this much credit
    LINE_GAP = 0.07              # lines of different readings closer than this (share of the picture) are the same line

    def __init__(self, reader, vocab: Vocabulary | None = None, good_enough: float = GOOD_ENOUGH):
        self._reader = reader
        self._vocab = vocab
        self._good_enough = good_enough

    @property
    def language(self) -> str:
        return getattr(self._reader, "language", "?")

    def _clean(self, lines: list[OcrLine]) -> list[OcrLine]:
        cleaned = []
        for line in lines:
            fixed = fix_text(line.text, self._vocab)
            if sum(c in TURKISH_LETTERS for c in line.text) >= 2 and text_quality(fixed, self._vocab) < 0.6:
                fixed = line.text.strip()     # it really is Turkish: keep the letters, folding would only mangle it
            if fixed:
                cleaned.append(OcrLine(fixed, line.center_x, line.center_y))
        return cleaned

    def _score(self, lines: list[OcrLine]) -> float:
        credit, total = word_counts(" ".join(l.text for l in lines), self._vocab)
        return credit - self.GARBAGE_PENALTY * (total - credit)

    @staticmethod
    def _key(lines: list[OcrLine]) -> str:
        """What makes two readings 'the same': the letters, ignoring case, punctuation and spacing."""
        return "".join(c for c in " ".join(l.text for l in lines).lower() if c.isalnum())

    def read(self, image: np.ndarray) -> list[OcrLine]:
        """One reading, however clean, may be a fragment of the line (every word valid, half of them missing): it is
        trusted only when a second, differently prepared picture reads the same. Otherwise every variant is tried and
        the reading with the most real words, helped by how many variants agree on it, wins."""
        seen: dict[str, tuple[list[OcrLine], float]] = {}
        votes: dict[str, int] = {}
        readings: list[list[OcrLine]] = []
        for _, variant in imageprep.variants(image):
            lines = self._clean(self._reader.read(variant))
            if not lines:
                continue
            readings.append(lines)
            key = self._key(lines)
            votes[key] = votes.get(key, 0) + 1
            seen.setdefault(key, (lines, self._score(lines)))
            if votes[key] >= 2 and text_quality(" ".join(l.text for l in lines), self._vocab) >= self._good_enough:
                return seen[key][0]
        if not readings:
            return []
        whole = max(seen, key=lambda k: seen[k][1] + self.AGREEMENT_BONUS * (votes[k] - 1))
        best_whole = seen[whole][0]
        merged = self._merge(readings)
        # the patchwork of best lines against the best single reading: whichever holds more real words wins
        return merged if self._score(merged) > self._score(best_whole) else best_whole

    def _merge(self, readings: list[list[OcrLine]]) -> list[OcrLine]:
        """No two variants agreed on the whole text, but each is usually right about some lines (on a real in-game
        frame one variant read line three perfectly and lost line four, another the other way round). So the lines
        of all readings are grouped by where they sit, and for each line the best candidate wins."""
        lines = sorted((l for reading in readings for l in reading), key=lambda l: l.center_y)
        clusters: list[list[OcrLine]] = []
        for line in lines:
            if clusters and line.center_y - clusters[-1][-1].center_y <= self.LINE_GAP:
                clusters[-1].append(line)
            else:
                clusters.append([line])
        merged = []
        for cluster in clusters:
            groups: dict[str, list[OcrLine]] = {}
            for line in cluster:
                groups.setdefault(self._key([line]), []).append(line)

            def value(key: str) -> float:
                first = groups[key][0]
                return self._score([first]) + self.AGREEMENT_BONUS * (len(groups[key]) - 1)

            winner = max(groups, key=value)
            best = groups[winner][0]
            alone = len(groups[winner]) == 1
            if alone and (self._score([best]) <= 0 or text_quality(best.text, self._vocab) < 0.6):
                continue                                   # garbage that only one variant produced
            merged.append(OcrLine(best.text, sum(l.center_x for l in groups[winner]) / len(groups[winner]),
                                  sum(l.center_y for l in groups[winner]) / len(groups[winner])))
        return merged
