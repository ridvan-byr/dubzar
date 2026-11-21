"""Wiring of the better reader into the app: where its models live, which lines count as dialogue, how fast we poll."""

import numpy as np
import pytest

from dubzar.ocr import OcrLine
from test_screen_source import make, pictures


def test_bundled_models_are_used_when_they_are_shipped_with_the_app(tmp_path):
    pytest.importorskip("rapidocr")
    import dubzar.ocr_rapid as rapid

    folder = tmp_path / "models" / "rapidocr"
    folder.mkdir(parents=True)
    (folder / rapid.DET_MODEL).write_bytes(b"x")
    (folder / rapid.REC_MODEL).write_bytes(b"x")

    params = rapid.engine_params(threads=2, det_max_side=1536, model_dir=folder)

    assert params["Det.model_path"].endswith(rapid.DET_MODEL) and params["Rec.model_path"].endswith(rapid.REC_MODEL)


def test_without_shipped_models_the_library_finds_its_own(tmp_path):
    pytest.importorskip("rapidocr")
    import dubzar.ocr_rapid as rapid

    params = rapid.engine_params(threads=2, det_max_side=1536, model_dir=tmp_path / "nothing-here")

    assert "Det.model_path" not in params and "Rec.model_path" not in params


def test_the_app_looks_for_models_next_to_its_code():
    import dubzar.ocr_rapid as rapid

    assert rapid.bundled_model_dir().name == "rapidocr" and rapid.bundled_model_dir().parent.name == "models"


def test_a_hud_hint_above_the_dialogue_is_not_translated_with_it():
    hint = OcrLine("HOLD TO USE ARMOR PLATES", 0.5, 0.02, 0.09)
    dialogue = [OcrLine("Laswell: How many?", 0.5, 0.46, 0.09),
                OcrLine("Ghost: There's a cove with four boats.", 0.5, 0.64, 0.09)]
    source, cues, _ = make(pictures(2), [[hint, *dialogue]] * 2)

    source.poll_once()
    source.poll_once()

    assert [c.text_src for c in cues] == ["Laswell: How many? Ghost: There's a cove with four boats."]


def test_the_app_prefers_rapidocr_with_windows_behind_it_and_degrades_gracefully(monkeypatch):
    import dubzar.app as app
    import dubzar.ocr as ocr

    class Marker:
        language = "marker"

        def read(self, image):
            return []

    monkeypatch.setattr(ocr, "WindowsOcr", lambda: Marker())
    reader = app.make_reader()

    assert reader is not None and reader.language


def test_nothing_readable_means_no_reader(monkeypatch):
    import dubzar.app as app
    import dubzar.ocr as ocr

    def broken():
        raise RuntimeError("no OCR language installed")

    monkeypatch.setattr(ocr, "WindowsOcr", broken)
    monkeypatch.setitem(__import__("sys").modules, "dubzar.ocr_rapid", None)    # an import that fails

    assert app.make_reader() is None
