from dubzar.memory import MemoizedTranslator, TranslationMemory


class Counting:
    def __init__(self, answer="çeviri"):
        self.calls, self.answer = [], answer

    def translate(self, text, context=()):
        self.calls.append(text)
        return self.answer


def test_remembers_a_translation_across_restarts(tmp_path):
    path = tmp_path / "memory.db"
    first = TranslationMemory(path, namespace="m1")
    first.put("Keep your head down.", "Başını aşağıda tut.")
    first.close()

    second = TranslationMemory(path, namespace="m1")

    assert second.get("Keep your head down.") == "Başını aşağıda tut."
    assert second.count() == 1


def test_ocr_wobble_and_punctuation_hit_the_same_entry(tmp_path):
    memory = TranslationMemory(tmp_path / "m.db", namespace="m1")
    memory.put("Okay, looking good.", "Tamam, iyi görünüyor.")

    assert memory.get("Okay, Iooking good!") == "Tamam, iyi görünüyor."   # I/l confusion, different punctuation
    assert memory.get("  okay,   LOOKING good ") == "Tamam, iyi görünüyor."
    assert memory.get("Something else entirely") is None


def test_different_namespace_does_not_share_entries(tmp_path):
    path = tmp_path / "m.db"
    TranslationMemory(path, namespace="model-a").put("Hello there", "Merhaba")

    assert TranslationMemory(path, namespace="model-b").get("Hello there") is None


def test_memoized_translator_asks_the_model_once(tmp_path):
    inner = Counting()
    translator = MemoizedTranslator(inner, TranslationMemory(tmp_path / "m.db", namespace="m1"))

    assert translator.translate("Watch your six!") == "çeviri"
    assert translator.translate("Watch your six!") == "çeviri"
    assert translator.translate("Watch your six") == "çeviri"      # same line without the "!"

    assert inner.calls == ["Watch your six!"]


def test_empty_translations_are_not_remembered(tmp_path):
    inner = Counting(answer="")
    translator = MemoizedTranslator(inner, TranslationMemory(tmp_path / "m.db", namespace="m1"))

    translator.translate("Hello there friend"); translator.translate("Hello there friend")

    assert len(inner.calls) == 2


def test_cli_builds_a_translator_that_remembers(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from dubzar import cli
    from dubzar.translate import OpusMtTranslator

    class FakeOpus(OpusMtTranslator):
        def __init__(self, *a, **k):
            super().__init__(*a, backend=lambda text: "T:" + text, **k)

        def load(self):
            pass

    monkeypatch.setattr(cli, "OpusMtTranslator", FakeOpus)
    monkeypatch.setattr(cli, "WhisperTranscriber", lambda **k: SimpleNamespace(load=lambda: None))
    args = SimpleNamespace(whisper_model="tiny", device="cpu", allow_download=False, cpu_threads=0,
                           memory=str(tmp_path / "memory.db"))

    _, translator = cli._build_models(args, {}, None, None)
    assert translator.translate("Keep your head down.") == "T:Keep your head down."
    _, again = cli._build_models(args, {}, None, None)          # a fresh start: the memory file answers
    assert again.translate("keep your head down") == "T:Keep your head down."
