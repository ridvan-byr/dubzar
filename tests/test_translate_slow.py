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


def test_fast_tokenizer_path_gives_the_same_translations_as_the_transformers_one():
    """The app starts in seconds, not twenty, because it does not import transformers: its own sentencepiece
    handling must produce the same text as the library's tokenizer (run with: pytest -m slow)."""
    pytest.importorskip("transformers")
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
    import ctranslate2
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    from translation_testset import TESTSET

    import dubzar.translate as translate

    folder = snapshot_download(translate.MODEL_NAME, local_files_only=True, ignore_patterns=translate.UNNEEDED_FILES)
    tokenizer = AutoTokenizer.from_pretrained(folder)
    engine = ctranslate2.Translator(str(translate.ct2_model_dir()), device="cpu", compute_type="int8", intra_threads=4)

    def with_library(text):
        source = tokenizer.convert_ids_to_tokens(tokenizer.encode(text, truncation=True, max_length=256))
        best = engine.translate_batch([source], beam_size=4, max_decoding_length=256)[0].hypotheses[0]
        return tokenizer.decode(tokenizer.convert_tokens_to_ids(best), skip_special_tokens=True)

    fast = translate._make_ct2_pipeline(True, 4)
    sentences = [line for _, line, _ in TESTSET] + ["Don't move! They're coming — now.", "Sir, it's 5:30; we're late."]

    assert [fast(s) for s in sentences] == [with_library(s) for s in sentences]
