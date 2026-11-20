import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import soundfile as sf

from dubzar.asr import Transcriber
from dubzar.audio import to_mono_16k
from dubzar.fingerprint import Matcher, fingerprint
from dubzar.index import IndexStore
from dubzar.models import Cue
from dubzar.translate import Translator

log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3", ".flac"}
LIVE_PREFIX = "live/"  # line ids the live mode creates; a scanned file replaces them
SR = 16000


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
    retry_skipped: bool = False,
) -> ScanReport:
    """Index every audio file under ``folder``; safe to re-run after an interruption.

    ``line_id`` is the file's path relative to ``folder`` (with ``/`` separators).
    Audio already in the index (same content) is skipped before any model runs, and
    so is audio that earlier had no usable speech, unless ``retry_skipped`` is set
    (use it after switching to a better speech model).
    A file that cannot be read or processed is counted as failed and the scan goes on;
    it is tried again on the next run.
    """
    root = Path(folder)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    counts = {"indexed": 0, "skipped_duplicate": 0, "skipped_no_speech": 0, "failed": 0}

    for done, path in enumerate(files, start=1):
        line_id = path.relative_to(root).as_posix()
        try:
            outcome = _process(path, line_id, store, transcriber, translator, retry_skipped)
        except Exception:
            log.exception("scan failed for %s", line_id)
            outcome = "failed"
        counts[outcome] += 1
        on_progress(done, len(files))

    return ScanReport(**counts)


def _process(path: Path, line_id: str, store: IndexStore, transcriber: Transcriber,
             translator: Translator, retry_skipped: bool) -> str:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    samples = to_mono_16k(data, sr)
    digest = hashlib.sha256(samples.tobytes()).hexdigest()
    existing = store.line_id_for_digest(digest)
    superseded = set()
    if existing is not None:
        if not existing.startswith(LIVE_PREFIX):
            return "skipped_duplicate"
        superseded.add(existing)  # identical audio the live mode learned: the file takes over

    if not retry_skipped and store.is_skipped(digest):
        return "skipped_no_speech"

    hashes = fingerprint(samples)
    if not hashes:  # silence or too short: nothing the matcher could ever recognise
        return "skipped_no_speech"
    transcription = transcriber.transcribe(samples)
    text_tr = translator.translate(transcription.text).strip() if transcription else ""
    if not text_tr:
        store.add_skipped(digest)
        return "skipped_no_speech"

    superseded |= _live_lines_for(samples, store)
    for old_id in superseded:  # only after the file is known to be good, so nothing is lost on failure
        store.remove_line(old_id)
    cue = Cue(line_id, transcription.text, text_tr, transcription.duration_s)
    store.add_line(cue, hashes, digest)
    return "indexed"


def _live_lines_for(samples, store: IndexStore) -> set[str]:
    """Live-learned lines whose audio is (a slightly different cut of) this file."""
    if not store.has_live_lines():
        return set()
    found = set()
    for window in (samples[: 3 * SR], samples[-3 * SR:]):
        result = Matcher(store.lookup).feed(window)
        if result is not None and result.line_id.startswith(LIVE_PREFIX):
            found.add(result.line_id)
    return found
