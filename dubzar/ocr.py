"""Windows' built-in text recognition (no download, no GPU): reads the text in a screenshot."""

import asyncio
from dataclasses import dataclass

import numpy as np

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
