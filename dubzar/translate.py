import re
import threading
import warnings
from typing import Callable, Protocol, Sequence

from dubzar.errors import ModelMissingError
from dubzar.textsplit import split_pieces

MODEL_NAME = "Helsinki-NLP/opus-mt-tc-big-en-tr"
# The repository also holds TensorFlow/Flax copies of the weights; we only ever need the PyTorch ones.
TRANSLATION_VERSION = "2"  # bump when the way text is prepared or translated changes: remembered lines are then redone
NUM_BEAMS = 4  # Opus-MT default; fewer beams are faster but a little less accurate
UNNEEDED_FILES = ["tf_model.h5", "*.h5", "flax_model*", "*.msgpack", "*.zip", "*.md"]


class Translator(Protocol):
    def translate(self, text: str, context: Sequence[str] = ()) -> str:
        """Translate English ``text`` to Turkish. ``context`` holds earlier lines
        of the same scene for translators that can use it."""


def _make_pipeline(local_only: bool, threads: int = 0) -> Callable[[str], str]:
    """The real Opus-MT translation function (text -> text); a seam so tests need no model."""
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    # Resolving the folder ourselves keeps "no download" honest: with local_only the call fails instead of
    # touching the network, and the model below then reads plain local files. (transformers 5 removed the
    # "translation" pipeline shortcut, so the model and tokenizer are used directly.)
    warnings.filterwarnings("ignore", message=".*sacremoses.*")  # optional helper this model does not need
    if threads > 0:
        torch.set_num_threads(threads)  # by default torch takes every core, which starves a running game
    folder = snapshot_download(MODEL_NAME, local_files_only=local_only, ignore_patterns=UNNEEDED_FILES)
    tokenizer = AutoTokenizer.from_pretrained(folder)
    model = AutoModelForSeq2SeqLM.from_pretrained(folder).eval()

    def translate(text: str) -> str:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        with torch.inference_mode():
            output = model.generate(**inputs, max_length=256, num_beams=NUM_BEAMS)
        return tokenizer.decode(output[0], skip_special_tokens=True)

    return translate


class OpusMtTranslator:
    """English to Turkish with Opus-MT and an enforced glossary.

    Glossary terms (matched case-insensitively, whole words, longest first) are
    swapped for opaque placeholders before translation and replaced by their
    Turkish form afterwards, so the model cannot translate them differently.
    ``backend`` (text -> text) can be injected for tests; otherwise the
    transformers pipeline is created lazily on first use.
    """

    def __init__(self, glossary: dict[str, str] | None = None,
                 backend: Callable[[str], str] | None = None, allow_download: bool = False,
                 threads: int = 0):
        self._glossary = glossary or {}
        self._backend = backend
        self._allow_download = allow_download
        self._threads = threads

    def _get_backend(self) -> Callable[[str], str]:
        if self._backend is None:
            self._backend = _make_pipeline(not self._allow_download, self._threads)
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
        parts = []
        for piece in split_pieces(text):  # one sentence at a time; the speaker's name stays out of the model
            body = self._translate_sentence(piece.text)
            parts.append(f"{piece.speaker}: {body}" if piece.speaker else body)
        return " ".join(part for part in parts if part)

    def _translate_sentence(self, text: str) -> str:
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
