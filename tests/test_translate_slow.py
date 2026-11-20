"""Smoke test with the real Opus-MT model. Needs transformers + torch and a model
download. Run with: pytest -m slow"""

import pytest

from dubzar.translate import OpusMtTranslator

pytestmark = pytest.mark.slow


def test_real_model_translates_and_enforces_glossary():
    pytest.importorskip("transformers")
    translator = OpusMtTranslator(glossary={"Vault": "Kasa"})

    result = translator.translate("The door is open and the Vault is empty.")

    assert "Kasa" in result
    assert "açık" in result.lower()
