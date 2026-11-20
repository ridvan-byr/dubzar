import sys

import numpy as np
import pytest

pytest.importorskip("winrt.windows.media.ocr")
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows OCR")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from dubzar.ocr import OcrLine, WindowsOcr  # noqa: E402


def subtitle_image(text: str, size: int = 44) -> np.ndarray:
    image = Image.new("RGB", (1400, 140), (20, 20, 24))
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
    ImageDraw.Draw(image).text((60, 40), text, font=font, fill=(245, 245, 245))
    return np.asarray(image)


def test_reads_a_rendered_subtitle_with_its_position():
    ocr = WindowsOcr()

    lines = ocr.read(subtitle_image("Keep your head down and stay quiet."))

    assert lines, "no text found"
    joined = " ".join(line.text for line in lines).lower()
    assert "keep your head down" in joined
    assert all(isinstance(line, OcrLine) for line in lines)
    assert 0.0 <= lines[0].center_x <= 1.0 and 0.0 <= lines[0].center_y <= 1.0


def test_blank_image_gives_no_lines():
    assert WindowsOcr().read(np.zeros((120, 600, 3), dtype=np.uint8)) == []
