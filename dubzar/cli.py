"""Command line.

``python -m dubzar setup --allow-download``   download the models once (the installer does this)
``python -m dubzar run``   live subtitles; the index grows as the game talks (the shortcut runs this)
``python -m dubzar scan <audio_dir> --index game.db``   scan extracted voice files into the index
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from dubzar.asr import Transcriber, WhisperTranscriber
from dubzar.errors import ModelMissingError
from dubzar.index import IndexStore
from dubzar.live import LivePipeline
from dubzar.memory import MemoizedTranslator, TranslationMemory
from dubzar.models import Cue
from dubzar.scan import scan_folder
from dubzar.settings import Settings, default_settings_path, load_settings
from dubzar.translate import MODEL_NAME, TRANSLATION_VERSION, OpusMtTranslator, ThreadSafeTranslator, Translator

POSITIONS = {"top": 0.0, "center": 0.5, "bottom": 1.0}


def default_index_path() -> str:
    base = os.environ.get("APPDATA") or str(Path.home())
    return str(Path(base) / "Dubzar" / "live.db")


def default_log_path() -> Path:
    return Path(default_index_path()).with_name("dubzar.log")


def redirect_output_if_windowless(log_file: Path | str):
    """Started from a shortcut with pythonw there is no console: ``print`` would crash on a missing stdout, and any
    error would vanish. Send both streams to a log file instead. Returns the open file, or None with a console."""
    if sys.stdout is not None and sys.stderr is not None:
        return None
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = handle
    return handle


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


def _open_memory(path: str | None, glossary: dict[str, str]) -> TranslationMemory:
    """The translation memory: a line translated once is answered from this file from then on. Entries belong to
    this model, this way of translating and this glossary, so changing any of them starts fresh."""
    file = Path(path) if path else default_settings_path().with_name("translations.db")
    file.parent.mkdir(parents=True, exist_ok=True)
    glossary_id = hashlib.sha256(json.dumps(glossary, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    return TranslationMemory(file, f"{MODEL_NAME}|v{TRANSLATION_VERSION}|{glossary_id}")


def _build_models(args, glossary: dict[str, str], transcriber: Transcriber | None,
                  translator: Translator | None) -> tuple[Transcriber, Translator]:
    """The real models unless fakes are injected. A model that is not on this computer is never
    downloaded unless ``--allow-download`` was given; ``ModelMissingError`` carries the explanation."""
    if transcriber is None:
        transcriber = WhisperTranscriber(model_size=args.whisper_model, device=args.device,
                                         allow_download=args.allow_download, cpu_threads=args.cpu_threads)
        transcriber.load()
    if translator is None:
        model = OpusMtTranslator(glossary=glossary, allow_download=args.allow_download, threads=args.cpu_threads)
        model.load()
        translator = MemoizedTranslator(model, _open_memory(getattr(args, "memory", None), glossary))
    return transcriber, ThreadSafeTranslator(translator)


def _cmd_scan(args, transcriber: Transcriber | None, translator: Translator | None) -> int:
    folder = Path(args.folder)
    if not folder.is_dir():
        return _error(f"ses klasörü bulunamadı: {folder}")
    try:
        glossary = _load_glossary(args.glossary)
    except (OSError, ValueError) as exc:
        return _error(f"glossary okunamadı: {exc}")
    try:
        transcriber, translator = _build_models(args, glossary, transcriber, translator)
    except ModelMissingError as exc:
        return _error(str(exc))

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


def _settings_for_run(args) -> Settings:
    """Saved settings, with any command-line flags applied on top (not saved by the flags themselves)."""
    settings = load_settings(args.settings_file)
    if args.font_size is not None:
        settings.font_size = args.font_size
    if args.position is not None:
        settings.vertical = POSITIONS[args.position]
    if args.screen is not None:
        settings.screen = args.screen
    if args.game_exe is not None:
        settings.game_exe = args.game_exe
    return settings


def _configure_logging(debug: bool) -> None:
    """--debug prints what the live mode does (levels, segments, why a subtitle was or was not shown)."""
    logging.basicConfig(level=logging.INFO if debug else logging.WARNING, format="%(asctime)s %(message)s",
                        datefmt="%H:%M:%S", force=True)
    if debug:
        logging.getLogger("dubzar").setLevel(logging.DEBUG)        # our own detail (read times), not other libraries'


def _cmd_setup(args, transcriber: Transcriber | None, translator: Translator | None) -> int:
    """Fetch the two models the app needs. The installer runs this after the user agreed to the download."""
    if not args.allow_download:
        return _error("modeller yalnızca izninizle indirilir: --allow-download ile yeniden çalıştırın.")
    steps = (
        ("konuşma tanıma modeli (~75 MB)", lambda: WhisperTranscriber(
            model_size="tiny", device="cpu", allow_download=True).load()),
        ("çeviri modeli (~480 MB) ve hızlı biçime dönüştürme", lambda: OpusMtTranslator(allow_download=True).load()),
    )
    for name, step in steps:
        print(f"İndiriliyor: {name} …", flush=True)
        try:
            step()
        except Exception as exc:  # noqa: BLE001 - tell the installer what failed, with the reason
            return _error(f"{name} hazırlanamadı: {exc}")
    print("Hazır: modeller bu bilgisayarda.", flush=True)
    return 0


def _cmd_run(args, audio_chunks: Iterable[np.ndarray] | None, on_cue: Callable[[Cue], None] | None,
             transcriber: Transcriber | None, translator: Translator | None) -> int:
    redirect_output_if_windowless(args.log_file or default_log_path())
    _configure_logging(args.debug)
    try:
        settings = _settings_for_run(args)
        glossary = _load_glossary(args.glossary)
    except (OSError, ValueError) as exc:
        return _error(str(exc))
    if args.game_exe and not args.audio_dir:
        return _error("--game-exe yalnızca --audio-dir ile anlamlı: arka plan taraması için ses klasörü gerekir.")
    if args.audio_dir and not settings.game_exe:
        return _error("--audio-dir için oyunun süreç adı da gerekir (--game-exe GTA5.exe): "
                      "tarama, oyun çalışırken duraklar.")
    if args.audio_dir and not Path(args.audio_dir).is_dir():
        return _error(f"ses klasörü bulunamadı: {args.audio_dir}")
    try:
        transcriber, translator = _build_models(args, glossary, transcriber, translator)
    except ModelMissingError as exc:
        return _error(str(exc))

    Path(args.index).parent.mkdir(parents=True, exist_ok=True)  # first run: the app's data folder does not exist yet
    store = IndexStore(args.index)  # created when it does not exist yet: live mode needs no prior scan
    try:
        if audio_chunks is not None:  # tests and offline replay: no capture, no window
            pipeline = LivePipeline(store, transcriber, translator, on_cue or (lambda cue: None))
            for chunk in audio_chunks:
                pipeline.feed(chunk)
            pipeline.close()
            return 0
        from dubzar.app import run_live  # imports Qt, which the other commands do not need

        def make_scan_transcriber() -> Transcriber:
            scanner_model = WhisperTranscriber(model_size=args.scan_model, device="auto",
                                               allow_download=args.allow_download, cpu_threads=args.cpu_threads)
            scanner_model.load()
            return scanner_model

        return run_live(store, args.index, settings, transcriber, translator,
                        audio_dir=args.audio_dir, make_scan_transcriber=make_scan_transcriber,
                        screen_ocr=not args.no_screen_ocr)
    finally:
        store.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dubzar", description="Türkçe oyun altyazısı ve dublajı")
    sub = parser.add_subparsers(dest="command", required=True)

    def model_flags(p, whisper_default: str, device_default: str, threads_default: int) -> None:
        p.add_argument("--whisper-model", default=whisper_default,
                       help=f"tiny, base, small ... (varsayılan: {whisper_default})")
        p.add_argument("--device", choices=("cpu", "auto"), default=device_default,
                       help=f"konuşma tanıma cihazı; auto ekran kartını dener (varsayılan: {device_default})")
        p.add_argument("--cpu-threads", type=int, default=threads_default,
                       help="modellerin kullanacağı işlemci iş parçacığı sayısı; 0 = kütüphane varsayılanı "
                            f"(varsayılan: {threads_default}; canlı modda oyuna çekirdek kalsın diye düşük)")
        p.add_argument("--memory", help="çeviri belleği dosyası: bir kez çevrilen satır bir daha çevrilmez "
                                        "(varsayılan: %%APPDATA%%/Dubzar/translations.db)")
        p.add_argument("--allow-download", action="store_true",
                       help="eksik modelleri indirmeye izin ver (varsayılan: indirme yok, eksikse hata verir)")
        p.add_argument("--glossary", help="terim sözlüğü JSON dosyası: {\"İngilizce\": \"Türkçe\"}")

    setup = sub.add_parser("setup", help="gerekli modelleri bir kez indir (kurulum bunu çalıştırır)")
    setup.add_argument("--allow-download", action="store_true", help="indirmeye izin ver (zorunlu)")

    scan = sub.add_parser("scan", help="oyunun ses dosyalarını tara ve altyazı indeksi oluştur")
    scan.add_argument("folder", help="çıkarılmış ses dosyalarının klasörü")
    scan.add_argument("--index", required=True, help="indeks dosyası (.db)")
    model_flags(scan, "small", "auto", 0)
    scan.add_argument("--retry-skipped", action="store_true",
                      help="önceden konuşmasız diye atlanan dosyaları yeniden dene (daha iyi model sonrası)")

    run = sub.add_parser("run", help="oyun sesini dinle ve Türkçe altyazıyı canlı göster; indeks oynadıkça büyür")
    run.add_argument("--index", default=default_index_path(),
                     help="indeks dosyası (yoksa oluşturulur; varsayılan: %%APPDATA%%/Dubzar/live.db)")
    run.add_argument("--log-file", help="konsol yoksa (kısayoldan başlatınca) çıktının yazılacağı dosya "
                                        "(varsayılan: %%APPDATA%%/Dubzar/dubzar.log)")
    model_flags(run, "tiny", "cpu", 2)
    run.add_argument("--debug", action="store_true",
                     help="ne olduğunu yaz: ses seviyesi, yakalanan parçalar, tanıma sonucu, altyazı neden gösterilmedi")
    run.add_argument("--no-screen-ocr", action="store_true",
                     help="oyunun ekrandaki altyazısını okuma (varsayılan: açık; yalnızca ses dinlenir)")
    run.add_argument("--audio-dir", help="çıkarılmış ses dosyaları: oyun kapalıyken arka planda taranır")
    run.add_argument("--game-exe", help="oyunun süreç adı (örn. GTA5.exe): çalışırken arka plan taraması bekler")
    run.add_argument("--scan-model", default="small", help="arka plan taraması için Whisper modeli (varsayılan: small)")
    run.add_argument("--font-size", type=int, help="bu çalıştırma için yazı boyutu (kayıtlı ayarı geçersiz kılar)")
    run.add_argument("--position", choices=tuple(POSITIONS), help="bu çalıştırma için konum: top, center, bottom")
    run.add_argument("--screen", help="bu çalıştırma için ekran: auto (oyunun ekranı), primary veya 1, 2, ...")
    run.add_argument("--settings-file", help="ayar dosyası (varsayılan: %%APPDATA%%/Dubzar/settings.json)")
    return parser


def main(argv: list[str] | None = None, *, transcriber: Transcriber | None = None,
         translator: Translator | None = None, audio_chunks: Iterable[np.ndarray] | None = None,
         on_cue: Callable[[Cue], None] | None = None) -> int:
    """Entry point. The keyword arguments let tests inject fakes instead of real models/devices."""
    args = build_parser().parse_args(argv)
    if args.command == "setup":
        return _cmd_setup(args, transcriber, translator)
    if args.command == "scan":
        return _cmd_scan(args, transcriber, translator)
    return _cmd_run(args, audio_chunks, on_cue, transcriber, translator)
