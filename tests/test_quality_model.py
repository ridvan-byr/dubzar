from pathlib import Path

from dubzar.quality_model import MIN_FREE_VRAM_MB, QualityModel, clean_answer
from dubzar.translate import OpusMtTranslator, UNSURE_BELOW


def _model(tmp_path, vram=16000, post=None):
    exe, gguf = tmp_path / "llama-server.exe", tmp_path / "m.gguf"
    exe.write_text("x")
    gguf.write_text("x")
    return QualityModel(exe, gguf, vram_probe=lambda: vram, post=post)


def test_answers_that_are_not_a_subtitle_are_refused():
    assert clean_answer('  "Kapıyı aç."  ', "Open the door.") == "Kapıyı aç."
    assert clean_answer("", "Open the door.") is None
    assert clean_answer("Birinci satır\nİkinci satır", "Open the door.") is None
    assert clean_answer("open the door.", "Open the door.") is None            # the English echoed back
    assert clean_answer("x" * 200, "Hi") is None                               # runaway


def test_it_is_unavailable_without_its_files_or_without_enough_graphics_memory(tmp_path):
    missing = QualityModel(tmp_path / "no.exe", tmp_path / "no.gguf", vram_probe=lambda: 16000)
    missing._start()
    assert missing.state == "unavailable" and "dosya" in missing.reason

    small = _model(tmp_path, vram=MIN_FREE_VRAM_MB - 1)
    small._start()
    assert small.state == "unavailable" and "bellek" in small.reason

    no_card = _model(tmp_path, vram=None)
    no_card._start()
    assert no_card.state == "unavailable" and "NVIDIA" in no_card.reason


def test_not_ready_means_no_second_opinion_and_a_failing_server_never_costs_a_subtitle(tmp_path):
    def boom(url, body, timeout):
        raise TimeoutError

    model = _model(tmp_path, post=boom)
    assert model.second_opinion("Hello", "Merhaba", {}) is None                # not started
    model.state = "ready"
    assert model.second_opinion("Hello", "Merhaba", {}) is None                # timed out


def test_the_prompt_carries_the_glossary_terms_that_occur_in_the_line(tmp_path):
    seen = {}

    def post(url, body, timeout):
        seen["prompt"] = body["messages"][0]["content"]
        return {"choices": [{"message": {"content": "Kral Arthur geldi."}}]}

    model = _model(tmp_path, post=post)
    model.state = "ready"
    assert model.second_opinion("King Arthur is here.", "x", {"King Arthur": "Kral Arthur", "Dragon": "Ejderha"}) == "Kral Arthur geldi."
    assert "King Arthur = Kral Arthur" in seen["prompt"] and "Dragon" not in seen["prompt"]


def test_the_translator_asks_the_second_model_only_for_lines_it_is_unsure_about():
    def backend(text):
        backend.last_logprob = backend.sure if "idiom" not in text else UNSURE_BELOW - 1
        return "ilk çeviri"

    backend.last_logprob = None
    backend.sure = UNSURE_BELOW + 1
    translator = OpusMtTranslator(backend=backend)
    asked = []
    translator.second_opinion = lambda text, draft, glossary: asked.append(text) or "ikinci çeviri"

    assert translator.translate("A plain sentence.") == "ilk çeviri"
    assert translator.translate("A strange idiom here.") == "ikinci çeviri"
    assert asked == ["A strange idiom here."]


def test_without_a_second_model_nothing_changes():
    backend = lambda text: "ilk çeviri"
    assert OpusMtTranslator(backend=backend).translate("A strange idiom here.") == "ilk çeviri"
