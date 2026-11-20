import logging
import os
import re
import shutil
import threading
import warnings
from pathlib import Path
from typing import Callable, Protocol, Sequence

from dubzar.errors import ModelMissingError
from dubzar.textsplit import split_pieces

MODEL_NAME = "Helsinki-NLP/opus-mt-tc-big-en-tr"
# The repository also holds TensorFlow/Flax copies of the weights; we only ever need the PyTorch ones.
TRANSLATION_VERSION = "3"  # bump when the way text is prepared or translated changes: remembered lines are then redone
NUM_BEAMS = 4  # Opus-MT default; fewer beams are faster but a little less accurate
UNNEEDED_FILES = ["tf_model.h5", "*.h5", "flax_model*", "*.msgpack", "*.zip", "*.md"]


log = logging.getLogger(__name__)
CT2_FOLDER_NAME = "opus-mt-tc-big-en-tr-int8-v1"


class Translator(Protocol):
    def translate(self, text: str, context: Sequence[str] = ()) -> str:
        """Translate English ``text`` to Turkish. ``context`` holds earlier lines
        of the same scene for translators that can use it."""


def ct2_model_dir() -> Path:
    """Where the converted (int8) model lives: next to the app's other data, not in the Hugging Face cache."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "Dubzar" / "models" / CT2_FOLDER_NAME


def _make_pipeline(local_only: bool, threads: int = 0) -> Callable[[str], str]:
    """The real Opus-MT translation function (text -> text); a seam so tests need no model.

    CTranslate2 with int8 weights is about six times faster and needs a seventh of the memory of the plain PyTorch
    model, with the same translations (measured: experiments/ct2_benchmark.py). If it cannot start for any reason
    other than the model being absent, the PyTorch model is used instead."""
    try:
        return _make_ct2_pipeline(local_only, threads)
    except (OSError, ValueError):
        raise                      # the model is not on this computer: the caller explains how to get it
    except Exception as exc:
        log.warning("CTranslate2 çeviri motoru başlatılamadı (%s); PyTorch kullanılıyor (daha yavaş)", exc)
        return _make_torch_pipeline(local_only, threads)


def _make_ct2_pipeline(local_only: bool, threads: int = 0) -> Callable[[str], str]:
    # Only sentencepiece is needed at run time. Importing the transformers library just for its tokenizer cost about
    # twenty seconds at every start; it is imported only for the one-time conversion below.
    import ctranslate2
    import sentencepiece
    from huggingface_hub import snapshot_download

    folder = snapshot_download(MODEL_NAME, local_files_only=local_only, ignore_patterns=UNNEEDED_FILES)
    model_dir = ct2_model_dir()
    if not (model_dir / "model.bin").exists():
        log.info("çeviri modeli hızlı biçime çevriliyor (yalnızca bir kez, birkaç saniye)")
        model_dir.parent.mkdir(parents=True, exist_ok=True)
        partial = model_dir.with_name(model_dir.name + ".partial")
        shutil.rmtree(partial, ignore_errors=True)
        ctranslate2.converters.TransformersConverter(folder).convert(str(partial), quantization="int8")
        partial.rename(model_dir)  # only a finished conversion ever gets the real name
    translator = ctranslate2.Translator(str(model_dir), device="cpu", compute_type="int8", intra_threads=threads)
    source_spm, target_spm = sentencepiece.SentencePieceProcessor(), sentencepiece.SentencePieceProcessor()
    source_spm.Load(str(Path(folder) / "source.spm"))
    target_spm.Load(str(Path(folder) / "target.spm"))

    def translate(text: str) -> str:
        # What the Marian tokenizer does: sentencepiece pieces of the source (the model's vocabulary maps them to ids)
        # plus the end marker; the output pieces are joined by the target sentencepiece model.
        pieces = source_spm.encode(text, out_type=str)[:255] + ["</s>"]
        best = translator.translate_batch([pieces], beam_size=NUM_BEAMS, max_decoding_length=256)[0].hypotheses[0]
        return target_spm.decode_pieces([piece for piece in best if piece not in ("</s>", "<pad>")])

    return translate


def _make_torch_pipeline(local_only: bool, threads: int = 0) -> Callable[[str], str]:
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
    # The checkpoint is stored as float16, which the processor handles slowly: float32 is about 30% faster on a
    # CPU (same translations, measured) for roughly half a gigabyte more memory.
    model = AutoModelForSeq2SeqLM.from_pretrained(folder, dtype=torch.float32).eval()

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
