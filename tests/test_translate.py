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
