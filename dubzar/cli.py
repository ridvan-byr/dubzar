"""Command line: ``python -m dubzar scan <audio_dir> --index game.db`` then ``... run --index game.db``."""

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from dubzar.asr import Transcriber, WhisperTranscriber
from dubzar.capture import run_matching
from dubzar.fingerprint import Matcher
from dubzar.index import IndexStore
from dubzar.models import Cue
from dubzar.settings import Settings, load_settings
from dubzar.scan import scan_folder
from dubzar.translate import OpusMtTranslator, Translator

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


POSITIONS = {"top": 0.0, "center": 0.5, "bottom": 1.0}


def _settings_for_run(args) -> Settings:
    """Saved settings, with any command-line flags applied on top (not saved by the flags themselves)."""
    settings = load_settings(args.settings_file)
    if args.font_size is not None:
        settings.font_size = args.font_size
    if args.position is not None:
        settings.vertical = POSITIONS[args.position]
    if args.screen is not None:
        settings.screen = args.screen
    return settings


def _cmd_run(args, audio_chunks: Iterable[np.ndarray] | None,
             on_cue: Callable[[Cue], None] | None) -> int:
    try:
        settings = _settings_for_run(args)
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
        from dubzar.app import run_live  # imports Qt, which the other commands do not need

        return run_live(store, matcher, settings)
    finally:
        store.close()


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
    if args.command == "scan":
        return _cmd_scan(args, transcriber, translator)
    return _cmd_run(args, audio_chunks, on_cue)
