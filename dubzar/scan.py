import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import soundfile as sf

from dubzar.asr import Transcriber
from dubzar.audio import to_mono_16k
from dubzar.fingerprint import fingerprint
from dubzar.index import IndexStore
from dubzar.models import Cue
from dubzar.translate import Translator

log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3", ".flac"}


@dataclass(frozen=True)
class ScanReport:
    indexed: int
    skipped_duplicate: int
    skipped_no_speech: int
    failed: int


def scan_folder(
    folder: str,
    store: IndexStore,
    transcriber: Transcriber,
    translator: Translator,
    on_progress: Callable[[int, int], None] = lambda done, total: None,
) -> ScanReport:
    """Index every audio file under ``folder``; safe to re-run after an interruption.

    ``line_id`` is the file's path relative to ``folder`` (with ``/`` separators).
    Audio already in the index (same content) is skipped before any model runs.
    A file that cannot be read or processed is counted as failed and the scan goes on.
    """
    root = Path(folder)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    counts = {"indexed": 0, "skipped_duplicate": 0, "skipped_no_speech": 0, "failed": 0}

    for done, path in enumerate(files, start=1):
        line_id = path.relative_to(root).as_posix()
        try:
            outcome = _process(path, line_id, store, transcriber, translator)
        except Exception:
            log.exception("scan failed for %s", line_id)
            outcome = "failed"
        counts[outcome] += 1
        on_progress(done, len(files))

    return ScanReport(**counts)


def _process(path: Path, line_id: str, store: IndexStore,
             transcriber: Transcriber, translator: Translator) -> str:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    samples = to_mono_16k(data, sr)
    digest = hashlib.sha256(samples.tobytes()).hexdigest()
    if store.has_digest(digest):
        return "skipped_duplicate"

    hashes = fingerprint(samples)
    if not hashes:  # silence or too short: nothing the matcher could ever recognise
        return "skipped_no_speech"
    transcription = transcriber.transcribe(samples)
    if transcription is None:
        return "skipped_no_speech"
    text_tr = translator.translate(transcription.text).strip()
    if not text_tr:
        return "skipped_no_speech"

    cue = Cue(line_id, transcription.text, text_tr, transcription.duration_s)
    store.add_line(cue, hashes, digest)
    return "indexed"
