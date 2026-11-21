import numpy as np
import pytest

from dubzar.ocr import OcrLine


class FakeOutput:
    def __init__(self, txts, boxes):
        self.txts, self.boxes = txts, boxes


class FakeEngine:
    def __init__(self, output):
        self.output, self.calls = output, []

    def __call__(self, image, **kwargs):
        self.calls.append(kwargs)
        return self.output


def box(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def test_lines_come_back_with_normalised_position_and_height():
    from dubzar.ocr_rapid import RapidOcr

    image = np.zeros((200, 1000, 3), dtype=np.uint8)
    engine = FakeEngine(FakeOutput(["Hello there", "second line"], [box(100, 20, 500, 60), box(200, 120, 600, 160)]))

    lines = RapidOcr(engine=engine).read(image)

    assert [l.text for l in lines] == ["Hello there", "second line"]
    assert lines[0].center_x == pytest.approx(0.3) and lines[0].center_y == pytest.approx(0.2)
    assert lines[0].height == pytest.approx(0.2)


def test_nothing_found_gives_no_lines():
    from dubzar.ocr_rapid import RapidOcr

    assert RapidOcr(engine=FakeEngine(FakeOutput(None, None))).read(np.zeros((50, 200, 3), dtype=np.uint8)) == []


def test_the_angle_classifier_is_never_run():
    """Subtitles are never upside down: skipping it saves time on every reading."""
    from dubzar.ocr_rapid import RapidOcr

    engine = FakeEngine(FakeOutput(["Hi there"], [box(0, 0, 10, 10)]))
    RapidOcr(engine=engine).read(np.zeros((50, 200, 3), dtype=np.uint8))

    assert engine.calls[0].get("use_cls") is False


def test_a_real_reading_of_a_rendered_subtitle():
    pytest.importorskip("rapidocr")
    import sys

    from PIL import Image, ImageDraw, ImageFont

    from dubzar.ocr_rapid import RapidOcr

    if sys.platform != "win32":
        pytest.skip("uses a Windows font")
    image = Image.new("RGB", (1200, 160), (25, 25, 30))
    ImageDraw.Draw(image).text((100, 50), "Keep your head down and stay quiet.",
                               font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 44), fill=(245, 245, 245))

    lines = RapidOcr().read(np.asarray(image))

    assert "keep your head down" in " ".join(l.text for l in lines).lower()


def test_idle_spinning_is_switched_off_for_ocr_sessions():
    pytest.importorskip("rapidocr")
    from rapidocr.inference_engine.onnxruntime.main import OrtInferSession

    import dubzar.ocr_rapid as rapid

    rapid.stop_idle_spinning()
    rapid.stop_idle_spinning()                                   # twice is harmless

    class Cfg(dict):
        __getattr__ = dict.get

    options = OrtInferSession._init_sess_opts(Cfg(enable_cpu_mem_arena=False, intra_op_num_threads=2,
                                                   inter_op_num_threads=1))
    assert options.get_session_config_entry("session.intra_op.allow_spinning") == "0"
