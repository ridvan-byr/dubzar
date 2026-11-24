"""The large second model of High mode: Gemma 4 12B (4-bit) served by llama.cpp's server on the graphics card.

Opus-MT translates every line fast on the processor. The lines it is unsure about (see translate.UNSURE_BELOW) are sent here
for a second translation. On a human-rated check this model made far fewer serious mistakes than Opus-MT (idioms, slang),
at about 0.85 s per line, but it needs about 7 GB of graphics-card memory. So it starts only in High mode, only when the
card has that much memory free, and every failure falls back to the Opus-MT translation: the subtitle never waits on it
longer than ``timeout_s`` and never breaks because of it.
"""

import json
import logging
import os
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

MODEL_FILE = "gemma-4-12b-it-qat-q4_0.gguf"
MIN_FREE_VRAM_MB = 7000          # measured: the server takes about 6.7 GB with a 1024-token window
PROMPT = ("Translate the following English video game subtitle into natural spoken Turkish. Translate idioms and slang by "
          "meaning into the natural Turkish equivalent, never word for word. Address the player or a single person as "
          "'sen'. Produce only the Turkish translation.{terms}\n\n{text}")


def _data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "Dubzar"


def default_server_exe() -> Path:
    return Path(os.environ.get("DUBZAR_LLAMA_SERVER") or _data_dir() / "llama" / "llama-server.exe")


def default_model_file() -> Path:
    return Path(os.environ.get("DUBZAR_QUALITY_MODEL") or _data_dir() / "models" / MODEL_FILE)


def free_vram_mb() -> int | None:
    """Free memory of the card with the most of it (NVIDIA only); None when it cannot be read."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return max(int(line.strip()) for line in out.splitlines() if line.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def clean_answer(answer: str, source: str) -> str | None:
    """The model's reply when it is a usable subtitle, else None (the Opus-MT translation stays)."""
    text = answer.strip().strip('"“”').strip()
    if not text or "\n" in text:
        return None
    if len(text) > 4 * len(source) + 20 or text.lower() == source.lower():
        return None                                   # runaway output, or the English echoed back
    return text


class QualityModel:
    def __init__(self, server_exe: Path | None = None, model_file: Path | None = None, *, timeout_s: float = 2.5,
                 vram_probe: Callable[[], int | None] = free_vram_mb,
                 post: Callable[[str, dict, float], dict] | None = None):
        self._server = Path(server_exe) if server_exe else default_server_exe()
        self._model = Path(model_file) if model_file else default_model_file()
        self._timeout = timeout_s
        self._vram_probe = vram_probe
        self._post = post or _http_post
        self._proc: subprocess.Popen | None = None
        self._port = 0
        self._lock = threading.Lock()
        self.state = "off"                 # off | starting | ready | unavailable
        self.reason = ""

    def start(self) -> None:
        """Starts in the background: the app is usable at once and gains the large model when it is up."""
        with self._lock:
            if self.state in ("starting", "ready"):
                return
            self.state, self.reason = "starting", ""
        threading.Thread(target=self._start, daemon=True, name="quality-model").start()

    def stop(self) -> None:
        with self._lock:
            proc, self._proc = self._proc, None
            self.state, self.reason = "off", ""
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _fail(self, reason: str) -> None:
        log.info("büyük çeviri modeli kullanılamıyor: %s (Opus-MT ile devam)", reason)
        with self._lock:
            self.state, self.reason = "unavailable", reason

    def _start(self) -> None:
        if not self._server.exists() or not self._model.exists():
            return self._fail("model dosyaları bu bilgisayarda yok")
        free = self._vram_probe()
        if free is None:
            return self._fail("NVIDIA ekran kartı bulunamadı")
        if free < MIN_FREE_VRAM_MB:
            return self._fail(f"ekran kartında yeterli boş bellek yok ({free} MB boş, {MIN_FREE_VRAM_MB} MB gerekir)")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self._port = probe.getsockname()[1]
        env = dict(os.environ, PATH=str(self._server.parent) + os.pathsep + os.environ.get("PATH", ""))
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        try:
            proc = subprocess.Popen([str(self._server), "-m", str(self._model), "-ngl", "99", "-c", "1024", "-np", "1",
                                     "--port", str(self._port), "--host", "127.0.0.1", "--jinja"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, creationflags=flags)
        except OSError as exc:
            return self._fail(f"sunucu başlatılamadı ({exc})")
        with self._lock:
            self._proc = proc
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return self._fail("sunucu kendiliğinden kapandı")
            if self.state == "off":                       # stopped while starting
                return
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self._port}/health", timeout=2) as reply:
                    if json.load(reply).get("status") == "ok":
                        break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        else:
            self.stop()
            return self._fail("sunucu zamanında hazır olmadı")
        with self._lock:
            if self.state == "off":
                return
            self.state = "ready"
        log.info("büyük çeviri modeli hazır")

    def second_opinion(self, text: str, draft: str, glossary: dict[str, str]) -> str | None:
        """The large model's translation of ``text``, or None when it is not ready, fails or answers unusably."""
        if self.state != "ready":
            return None
        terms = ""
        if glossary:
            used = {en: tr for en, tr in glossary.items() if en.lower() in text.lower()}
            if used:
                terms = " Use these Turkish terms: " + "; ".join(f"{en} = {tr}" for en, tr in used.items()) + "."
        body = {"messages": [{"role": "user", "content": PROMPT.format(terms=terms, text=text)}], "temperature": 0,
                "max_tokens": 160, "chat_template_kwargs": {"enable_thinking": False}}
        try:
            reply = self._post(f"http://127.0.0.1:{self._port}/v1/chat/completions", body, self._timeout)
            return clean_answer(reply["choices"][0]["message"]["content"], text)
        except Exception as exc:  # noqa: BLE001 - a slow or broken second model must never cost a subtitle
            log.debug("büyük model yanıt vermedi: %s", exc)
            return None


def _http_post(url: str, body: dict, timeout: float) -> dict:
    request = urllib.request.Request(url, json.dumps(body).encode("utf-8"), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as reply:
        return json.load(reply)


_shared: QualityModel | None = None


def shared() -> QualityModel:
    """The one large model of this process: the translator asks it, the app starts and stops it with the mode."""
    global _shared
    if _shared is None:
        _shared = QualityModel()
    return _shared
