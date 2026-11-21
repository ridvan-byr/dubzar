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


def test_gpu_parameters_are_added_only_when_asked_for(tmp_path):
    pytest.importorskip("rapidocr")
    import dubzar.ocr_rapid as rapid

    plain = rapid.engine_params(threads=2, det_max_side=1536, model_dir=tmp_path)
    gpu = rapid.engine_params(threads=2, det_max_side=1536, model_dir=tmp_path, gpu=True)

    assert "EngineConfig.onnxruntime.use_cuda" not in plain
    assert gpu["EngineConfig.onnxruntime.use_cuda"] is True


def test_the_gpu_is_not_used_when_onnxruntime_has_no_cuda(monkeypatch):
    import dubzar.ocr_rapid as rapid

    class NoCuda:
        @staticmethod
        def get_available_providers():
            return ["CPUExecutionProvider"]

    monkeypatch.setitem(__import__("sys").modules, "onnxruntime", NoCuda)

    assert rapid.cuda_ready(model=None) is False


def test_a_reader_asked_for_the_gpu_falls_back_to_the_cpu_when_there_is_none(monkeypatch):
    import dubzar.ocr_rapid as rapid

    monkeypatch.setattr(rapid, "cuda_ready", lambda model: False)
    engine = FakeEngine(FakeOutput(None, None))

    reader = rapid.RapidOcr(threads=2, gpu=True, engine=engine)

    assert reader.gpu is False and "GPU" not in reader.language


def test_the_graphics_card_libraries_are_loaded_before_the_translation_engine_in_high_mode(monkeypatch, tmp_path):
    import dubzar.cli as cli
    import dubzar.ocr_rapid as rapid

    order = []
    monkeypatch.setattr(rapid, "prepare_cuda_early", lambda: order.append("cuda"))
    monkeypatch.setattr(cli, "_build_models", lambda *a, **k: order.append("models") or (None, None))
    monkeypatch.setattr(cli, "IndexStore", lambda path: type("S", (), {"close": lambda self: None})())
    monkeypatch.setattr("dubzar.app.run_live", lambda *a, **k: 0, raising=False)
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"performance": "high"}', encoding="utf-8")

    cli.main(["run", "--settings-file", str(settings_file), "--index", str(tmp_path / "i.db"), "--log-file",
              str(tmp_path / "log.txt")])

    assert order[:2] == ["cuda", "models"]
