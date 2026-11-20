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
