"""Game audio capture (WASAPI loopback) and the live matching loop."""

import logging
import queue
import threading
from typing import Callable, Iterable

import numpy as np

from dubzar.audio import TARGET_SR, to_mono_16k
from dubzar.fingerprint import Matcher
from dubzar.index import IndexStore
from dubzar.models import Cue

log = logging.getLogger(__name__)

CHUNK_SECONDS = 0.1  # longer blocks keep per-block resampling edge effects negligible
DEVICE_POLL_SECONDS = 2.0


def bytes_to_mono_16k(data: bytes, channels: int, sr: int) -> np.ndarray:
    """Convert interleaved int16 PCM bytes to mono float32 at 16 kHz."""
    pcm = np.frombuffer(data, dtype=np.int16).reshape(-1, channels)
    return to_mono_16k(pcm.astype(np.float32) / 32768.0, sr)


def queue_chunks(q: "queue.Queue[np.ndarray | None]") -> Iterable[np.ndarray]:
    """Yield chunks from ``q`` until a ``None`` sentinel arrives (checked with ``is``)."""
    while True:
        item = q.get()
        if item is None:
            return
        yield item


def run_matching(chunks: Iterable[np.ndarray], matcher: Matcher, store: IndexStore,
                 on_cue: Callable[[Cue], None]) -> None:
    """Feed 16 kHz mono chunks to ``matcher`` and call ``on_cue`` once per played line.

    After a hit the matcher is reset. The same line is ignored until its
    duration has passed, because the remainder of the line would otherwise match again.
    """
    elapsed = 0.0  # seconds of audio fed so far
    quiet_until: dict[str, float] = {}
    for chunk in chunks:
        elapsed += len(chunk) / TARGET_SR
        result = matcher.feed(chunk)
        if result is None:
            continue
        matcher.reset()
        cue = store.get_cue(result.line_id)
        if cue is None or elapsed < quiet_until.get(cue.line_id, 0.0):
            continue
        quiet_until[cue.line_id] = elapsed + cue.duration_s
        on_cue(cue)


class LoopbackCapture:
    """Captures what the default output device plays and delivers 16 kHz mono chunks.

    Follows the default output device: when the user switches speakers or
    headphones the stream is reopened on the new one. ``device`` optionally
    pins a device by (part of) its name.
    """

    def __init__(self, on_chunk: Callable[[np.ndarray], None], device: str | None = None):
        self._on_chunk = on_chunk
        self._device = device
        self._pa = None
        self._stream = None
        self._current_name: str | None = None
        self._stopping = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        self._stopping.clear()
        self._open()
        threading.Thread(target=self._watch_default_device, daemon=True).start()

    def stop(self) -> None:
        self._stopping.set()
        self._close()

    def _open(self) -> None:
        import pyaudiowpatch as pyaudio

        with self._lock:
            self._pa = pyaudio.PyAudio()
            info = self._loopback_info(self._pa)
            channels = int(info["maxInputChannels"])
            rate = int(info["defaultSampleRate"])

            def callback(in_data, frame_count, time_info, status):
                try:
                    self._on_chunk(bytes_to_mono_16k(in_data, channels, rate))
                except Exception:
                    log.exception("audio chunk handling failed")
                return None, pyaudio.paContinue

            self._stream = self._pa.open(
                format=pyaudio.paInt16, channels=channels, rate=rate, input=True,
                input_device_index=info["index"],
                frames_per_buffer=int(rate * CHUNK_SECONDS), stream_callback=callback,
            )
            self._current_name = info["name"]
            log.info("capturing from %s (%d Hz, %d ch)", info["name"], rate, channels)

    def _close(self) -> None:
        with self._lock:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            if self._pa is not None:
                self._pa.terminate()
                self._pa = None

    def _loopback_info(self, pa) -> dict:
        import pyaudiowpatch as pyaudio

        speakers = pa.get_device_info_by_index(
            pa.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultOutputDevice"]
        )
        wanted = self._device or speakers["name"]
        if speakers.get("isLoopbackDevice") and wanted in speakers["name"]:
            return speakers
        for loopback in pa.get_loopback_device_info_generator():
            if wanted in loopback["name"]:
                return loopback
        raise RuntimeError(f"no loopback device found for {wanted!r}")

    def _default_output_name(self) -> str:
        import pyaudiowpatch as pyaudio

        probe = pyaudio.PyAudio()  # a fresh instance sees device changes; the open one does not
        try:
            index = probe.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultOutputDevice"]
            return probe.get_device_info_by_index(index)["name"]
        finally:
            probe.terminate()

    def _watch_default_device(self) -> None:
        while not self._stopping.wait(DEVICE_POLL_SECONDS):
            if self._device:  # pinned device: nothing to follow
                continue
            try:
                name = self._default_output_name()
                if self._current_name and name not in self._current_name:
                    log.info("default output changed to %s, reconnecting", name)
                    self._close()
                    self._open()
            except Exception:
                log.exception("could not follow default output device")
