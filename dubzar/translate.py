import re
from typing import Callable, Protocol, Sequence

MODEL_NAME = "Helsinki-NLP/opus-mt-tc-big-en-tr"


class Translator(Protocol):
    def translate(self, text: str, context: Sequence[str] = ()) -> str:
        """Translate English ``text`` to Turkish. ``context`` holds earlier lines
        of the same scene for translators that can use it."""


class OpusMtTranslator:
    """English to Turkish with Opus-MT and an enforced glossary.

    Glossary terms (matched case-insensitively, whole words, longest first) are
    swapped for opaque placeholders before translation and replaced by their
    Turkish form afterwards, so the model cannot translate them differently.
    ``backend`` (text -> text) can be injected for tests; otherwise the
    transformers pipeline is created lazily on first use.
    """

    def __init__(self, glossary: dict[str, str] | None = None,
                 backend: Callable[[str], str] | None = None):
        self._glossary = glossary or {}
        self._backend = backend

    def _get_backend(self) -> Callable[[str], str]:
        if self._backend is None:
            from transformers import pipeline

            pipe = pipeline("translation", model=MODEL_NAME)
            self._backend = lambda text: pipe(text, max_length=256)[0]["translation_text"]
        return self._backend

    def translate(self, text: str, context: Sequence[str] = ()) -> str:
        text = text.strip()
        if not text:
            return ""
        protected, restore = self._protect_terms(text)
        translated = self._get_backend()(protected)
        for placeholder, target in restore.items():
            translated = translated.replace(placeholder, target)
        return translated

    def _protect_terms(self, text: str) -> tuple[str, dict[str, str]]:
        restore: dict[str, str] = {}
        terms = sorted(self._glossary, key=len, reverse=True)
        for i, term in enumerate(terms):
            placeholder = f"Qx{i}z"
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            text, count = pattern.subn(placeholder, text)
            if count:
                restore[placeholder] = self._glossary[term]
        return text, restore
