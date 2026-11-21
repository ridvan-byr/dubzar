import pytest

from dubzar.translate import OpusMtTranslator


class SpyBackend:
    """Fake MT backend: drops the article and translates one phrase."""

    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, text: str) -> str:
        self.calls.append(text)
        return text.replace("The ", "").replace("is open", "açık")


def test_glossary_term_is_enforced():
    backend = SpyBackend()
    translator = OpusMtTranslator(glossary={"Vault": "Kasa"}, backend=backend)

    assert translator.translate("The Vault is open") == "Kasa açık"


def test_glossary_is_case_insensitive_and_whole_word():
    translator = OpusMtTranslator(glossary={"vault": "Kasa"}, backend=SpyBackend())

    assert translator.translate("The VAULT is open") == "Kasa açık"
    assert translator.translate("The vaulted ceiling is open") == "vaulted ceiling açık"


def test_longer_glossary_terms_win_over_shorter_ones():
    translator = OpusMtTranslator(
        glossary={"Iron": "Demir", "Iron Gate": "Demir Kapı"}, backend=SpyBackend()
    )

    assert translator.translate("The Iron Gate is open") == "Demir Kapı açık"


def test_empty_text_returns_empty_without_calling_backend():
    backend = SpyBackend()
    translator = OpusMtTranslator(backend=backend)

    assert translator.translate("   ") == ""
    assert backend.calls == []


def test_without_glossary_text_goes_to_backend_unchanged():
    backend = SpyBackend()
    translator = OpusMtTranslator(backend=backend)

    translator.translate("The door is open")

    assert backend.calls == ["The door is open"]


def test_dropped_placeholder_does_not_crash():
    translator = OpusMtTranslator(glossary={"Vault": "Kasa"}, backend=lambda text: "tamam")

    assert translator.translate("The Vault is open") == "tamam"


# --- models are never downloaded behind the user's back ---------------------------------------
from dubzar.errors import ModelMissingError  # noqa: E402


def test_translator_load_reports_a_missing_model_clearly(monkeypatch):
    import dubzar.translate as translate

    def no_pipeline(*args, **kwargs):
        raise OSError("not found in the local cache")

    monkeypatch.setattr(translate, "_make_pipeline", no_pipeline)

    with pytest.raises(ModelMissingError) as info:
        OpusMtTranslator().load()

    assert "--allow-download" in str(info.value)


def test_translator_asks_for_local_files_only_unless_downloads_are_allowed(monkeypatch):
    import dubzar.translate as translate

    seen = []

    def fake_pipeline(local_only, threads=0):
        seen.append(local_only)
        return lambda text: text

    monkeypatch.setattr(translate, "_make_pipeline", fake_pipeline)

    OpusMtTranslator().load()
    OpusMtTranslator(allow_download=True).load()

    assert seen == [True, False]


def test_thread_safe_translator_serialises_calls_from_several_threads():
    import threading
    import time

    from dubzar.translate import ThreadSafeTranslator

    running = {"now": 0, "max": 0}

    class Slow:
        def translate(self, text, context=()):
            running["now"] += 1
            running["max"] = max(running["max"], running["now"])
            time.sleep(0.02)
            running["now"] -= 1
            return text.upper()

    shared = ThreadSafeTranslator(Slow())
    threads = [threading.Thread(target=shared.translate, args=("a",)) for _ in range(6)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert running["max"] == 1  # the live path and the background scan never run the model at the same time
    assert shared.translate("x") == "X"


def test_translator_passes_its_cpu_thread_limit_to_the_model(monkeypatch):
    import dubzar.translate as translate

    seen = []
    monkeypatch.setattr(translate, "_make_pipeline", lambda local_only, threads=0: seen.append(threads) or (lambda text: text))

    OpusMtTranslator(threads=2).load()
    OpusMtTranslator().load()

    assert seen == [2, 0]


def test_each_sentence_goes_to_the_model_separately():
    seen = []
    translator = OpusMtTranslator(backend=lambda text: seen.append(text) or "T(" + text + ")")

    result = translator.translate("You think this is a game? People die out here.")

    assert seen == ["You think this is a game?", "People die out here."]
    assert result == "T(You think this is a game?) T(People die out here.)"


def test_speaker_name_never_reaches_the_model_and_is_put_back():
    seen = []
    translator = OpusMtTranslator(backend=lambda text: seen.append(text) or "çeviri")

    result = translator.translate("Brian: But the count was good.")

    assert seen == ["But the count was good."]
    assert result == "Brian: çeviri"


def test_several_speakers_in_one_subtitle():
    translator = OpusMtTranslator(backend=lambda text: "[" + text + "]")

    assert translator.translate("Brian: Hello there. Donnie: Hi, Brian.") == "Brian: [Hello there.] Donnie: [Hi, Brian.]"


# --- the fast CTranslate2 backend, with the PyTorch one as the fallback ---------------------------
def test_fast_backend_is_preferred(monkeypatch):
    import dubzar.translate as translate

    monkeypatch.setattr(translate, "_make_ct2_pipeline", lambda local_only, threads=0: (lambda text: "ct2:" + text))
    monkeypatch.setattr(translate, "_make_torch_pipeline", lambda local_only, threads=0: (lambda text: "torch:" + text))

    assert translate._make_pipeline(True, 2)("hi") == "ct2:hi"


def test_falls_back_to_pytorch_when_the_fast_backend_cannot_start(monkeypatch, caplog):
    import dubzar.translate as translate

    def broken(local_only, threads=0):
        raise RuntimeError("conversion failed")

    monkeypatch.setattr(translate, "_make_ct2_pipeline", broken)
    monkeypatch.setattr(translate, "_make_torch_pipeline", lambda local_only, threads=0: (lambda text: "torch:" + text))

    assert translate._make_pipeline(True, 0)("hi") == "torch:hi"
    assert "CTranslate2" in caplog.text


def test_missing_model_is_not_hidden_by_the_fallback(monkeypatch):
    import dubzar.translate as translate

    def missing(local_only, threads=0):
        raise OSError("not in the local cache")

    monkeypatch.setattr(translate, "_make_ct2_pipeline", missing)
    monkeypatch.setattr(translate, "_make_torch_pipeline", lambda *a, **k: pytest.fail("must not be tried"))

    with pytest.raises(OSError):
        translate._make_pipeline(True, 0)


def test_converted_model_folder_sits_next_to_the_apps_other_data(monkeypatch, tmp_path):
    import dubzar.translate as translate

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    folder = translate.ct2_model_dir()

    assert folder.parent == tmp_path / "Dubzar" / "models"
    assert "int8" in folder.name
