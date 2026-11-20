"""Command line: ``python -m dubzar scan <audio_dir> --index game.db`` then ``... run --index game.db``."""

import argparse
import json
import queue
import signal
import sys
import threading
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from dubzar.asr import Transcriber, WhisperTranscriber
from dubzar.capture import LoopbackCapture, queue_chunks, run_matching
from dubzar.fingerprint import Matcher
from dubzar.index import IndexStore
from dubzar.models import Cue
from dubzar.overlay import OverlaySettings, detect_exclusive_fullscreen
from dubzar.scan import scan_folder
from dubzar.translate import OpusMtTranslator, Translator

EXCLUSIVE_WARNING = (
    "Uyarı: tam ekran (exclusive) bir oyun algılandı, altyazı görünmeyebilir. "
    "Oyunu 'pencereli tam ekran' (borderless) modda çalıştırın."
)


def _error(message: str) -> int:
    print(f"Hata: {message}", file=sys.stderr)
    return 2


def _load_glossary(path: str | None) -> dict[str, str]:
    if path is None:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ValueError("glossary file must be a JSON object of English term -> Turkish term")
    return data


def _cmd_scan(args, transcriber: Transcriber | None, translator: Translator | None) -> int:
    folder = Path(args.folder)
    if not folder.is_dir():
        return _error(f"ses klasörü bulunamadı: {folder}")
    try:
        glossary = _load_glossary(args.glossary)
    except (OSError, ValueError) as exc:
        return _error(f"glossary okunamadı: {exc}")
    transcriber = transcriber or WhisperTranscriber(model_size=args.whisper_model)
    translator = translator or OpusMtTranslator(glossary=glossary)

    store = IndexStore(args.index)
    try:
        report = scan_folder(
            str(folder), store, transcriber, translator,
            on_progress=lambda done, total: print(f"\r{done}/{total}", end="", flush=True),
            retry_skipped=args.retry_skipped,
        )
    finally:
        store.close()
    print(f"\nTamamlandı: {report.indexed} eklendi, {report.skipped_duplicate} zaten vardı, "
          f"{report.skipped_no_speech} konuşmasız/atlandı, {report.failed} hatalı.")
    return 0


def _open_existing_index(path: str) -> IndexStore | None:
    if not Path(path).is_file():
        _error(f"indeks dosyası yok: {path}. Önce 'scan' komutunu çalıştırın.")
        return None
    store = IndexStore(path)
    if store.count_lines() == 0:
        store.close()
        _error("indeks boş. Önce 'scan' komutuyla ses klasörünü tarayın.")
        return None
    return store


def _cmd_run(args, audio_chunks: Iterable[np.ndarray] | None,
             on_cue: Callable[[Cue], None] | None) -> int:
    try:
        settings = OverlaySettings(font_size=args.font_size, position=args.position,
                                   screen=args.screen)
    except ValueError as exc:
        return _error(str(exc))
    store = _open_existing_index(args.index)
    if store is None:
        return 2
    matcher = Matcher(store.lookup)
    try:
        if audio_chunks is not None:  # tests and offline replay: no capture, no window
            run_matching(audio_chunks, matcher, store, on_cue or (lambda cue: None))
            return 0
        return _run_live(store, matcher, settings)
    finally:
        store.close()


def _run_live(store: IndexStore, matcher: Matcher, settings: OverlaySettings) -> int:
    from PySide6.QtCore import QObject, QTimer, Signal
    from PySide6.QtWidgets import QApplication

    from dubzar.overlay_window import OverlayWindow

    class Bridge(QObject):  # carries cues from the matching thread to the GUI thread
        cue = Signal(object)

    app = QApplication(sys.argv)
    window = OverlayWindow(settings)
    bridge = Bridge()
    bridge.cue.connect(window.show_cue)

    audio: queue.Queue = queue.Queue()
    worker = threading.Thread(
        target=run_matching,
        args=(queue_chunks(audio), matcher, store, bridge.cue.emit),
        daemon=True,
    )
    worker.start()
    capture = LoopbackCapture(audio.put)
    capture.start()

    warned = False

    def check_fullscreen() -> None:
        nonlocal warned
        if not warned and detect_exclusive_fullscreen():
            warned = True
            print(EXCLUSIVE_WARNING, flush=True)

    check_fullscreen()
    fullscreen_timer = QTimer()
    fullscreen_timer.timeout.connect(check_fullscreen)
    fullscreen_timer.start(5000)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    wakeup = QTimer()  # lets Python run the Ctrl+C handler while Qt owns the loop
    wakeup.timeout.connect(lambda: None)
    wakeup.start(200)

    print("Dinleniyor. Çıkmak için Ctrl+C.", flush=True)
    try:
        app.exec()
    finally:
        capture.stop()
        audio.put(None)
        worker.join(timeout=2)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dubzar", description="Türkçe oyun altyazısı ve dublajı")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="oyunun ses dosyalarını tara ve altyazı indeksi oluştur")
    scan.add_argument("folder", help="çıkarılmış ses dosyalarının klasörü")
    scan.add_argument("--index", required=True, help="indeks dosyası (.db)")
    scan.add_argument("--glossary", help="terim sözlüğü JSON dosyası: {\"İngilizce\": \"Türkçe\"}")
    scan.add_argument("--whisper-model", default="small", help="tiny, small, medium ... (varsayılan: small)")
    scan.add_argument("--retry-skipped", action="store_true",
                      help="önceden konuşmasız diye atlanan dosyaları yeniden dene (daha iyi model sonrası)")

    run = sub.add_parser("run", help="oyun sesini dinle ve altyazıyı göster")
    run.add_argument("--index", required=True, help="scan ile oluşturulmuş indeks dosyası")
    run.add_argument("--font-size", type=int, default=28)
    run.add_argument("--position", choices=("top", "center", "bottom"), default="bottom")
    run.add_argument("--screen", default="auto",
                     help="altyazının ekranı: auto (oyunun ekranı), primary veya 1, 2, ... (varsayılan: auto)")
    return parser


def main(argv: list[str] | None = None, *, transcriber: Transcriber | None = None,
         translator: Translator | None = None, audio_chunks: Iterable[np.ndarray] | None = None,
         on_cue: Callable[[Cue], None] | None = None) -> int:
    """Entry point. The keyword arguments let tests inject fakes instead of real models/devices."""
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        return _cmd_scan(args, transcriber, translator)
    return _cmd_run(args, audio_chunks, on_cue)
