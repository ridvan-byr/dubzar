import re
import threading
from typing import Callable, Protocol, Sequence

from dubzar.errors import ModelMissingError

MODEL_NAME = "Helsinki-NLP/opus-mt-tc-big-en-tr"


class Translator(Protocol):
    def translate(self, text: str, context: Sequence[str] = ()) -> str:
        """Translate English ``text`` to Turkish. ``context`` holds earlier lines
        of the same scene for translators that can use it."""


def _make_pipeline(local_only: bool) -> Callable[[str], str]:
    """The real Opus-MT translation function (text -> text); a seam so tests need no model."""
    from transformers import pipeline

    pipe = pipeline("translation", model=MODEL_NAME, model_kwargs={"local_files_only": local_only})
    return lambda text: pipe(text, max_length=256)[0]["translation_text"]


class OpusMtTranslator:
    """English to Turkish with Opus-MT and an enforced glossary.

    Glossary terms (matched case-insensitively, whole words, longest first) are
    swapped for opaque placeholders before translation and replaced by their
    Turkish form afterwards, so the model cannot translate them differently.
    ``backend`` (text -> text) can be injected for tests; otherwise the
    transformers pipeline is created lazily on first use.
    """

    def __init__(self, glossary: dict[str, str] | None = None,
                 backend: Callable[[str], str] | None = None, allow_download: bool = False):
        self._glossary = glossary or {}
        self._backend = backend
        self._allow_download = allow_download

    def _get_backend(self) -> Callable[[str], str]:
        if self._backend is None:
            self._backend = _make_pipeline(not self._allow_download)
        return self._backend

    def load(self) -> None:
        """Create the model now (slow). Downloads only happen with ``allow_download``."""
        try:
            self._get_backend()
        except (OSError, ValueError) as exc:
            raise ModelMissingError(
                f"Çeviri modeli ({MODEL_NAME}) bu bilgisayarda yok. İndirmek için --allow-download "
                f"ile yeniden çalıştırın. ({exc})"
            ) from exc

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


class ThreadSafeTranslator:
    """Lets the live path and the background scan share one translator (and one loaded model)."""

    def __init__(self, inner: Translator):
        self._inner = inner
        self._lock = threading.Lock()

    def translate(self, text: str, context: Sequence[str] = ()) -> str:
        with self._lock:
            return self._inner.translate(text, context)
