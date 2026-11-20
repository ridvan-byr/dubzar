"""The live app: listens to the game, shows subtitles, learns, and opens the settings panel on a hotkey."""

import logging
import queue
import signal
import sys
import threading
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from dubzar.asr import Transcriber
from dubzar.background import BackgroundScanner, is_process_running
from dubzar.capture import LoopbackCapture, queue_chunks
from dubzar.gamewatch import GameWatcher
from dubzar.hotkey import GlobalHotkey
from dubzar.index import IndexStore
from dubzar.live import LivePipeline
from dubzar.overlay import detect_exclusive_fullscreen
from dubzar.overlay_window import OverlayWindow
from dubzar.priority import lower_priority
from dubzar.screen import (band_box, exclude_from_capture, foreground_is_fullscreen, foreground_monitor_rect,
                           foreground_process_name, game_in_front, grab)
from dubzar.screen_source import ScreenSubtitleSource
from dubzar.segmenter import SpeechSegmenter
from dubzar.settings import Settings
from dubzar.translate import Translator
from dubzar.ui.backdrop import Backdrop
from dubzar.ui.controller import SettingsController
from dubzar.ui.intro import IntroWindow
from dubzar.ui.panel import PanelWindow
from dubzar.ui.saver import SettingsSaver
from dubzar.ui.screens import target_screen
from dubzar.ui.system import animations_enabled

log = logging.getLogger(__name__)

HINT_DELAY_MS = 6000   # after the game process appears: let its window come up before the hint shows
GAME_POLL_MS = 3000
PREVIEW_TEXT = "Sessiz ol… Birisi geliyor."
EXCLUSIVE_WARNING = (
    "Bilgi: tam ekran (exclusive) bir oyun algılandı. Çoğu oyunda altyazı görünür; görünmezse "
    "oyunu 'pencereli tam ekran' (borderless) modda çalıştırın."
)


def qt_message_filter(mode, context, message: str) -> None:
    """Print Qt's messages, except the harmless "Unable to set geometry" chatter the overlay triggers
    when Windows applies its own size limits (the subtitle still shows in the right place)."""
    if "Unable to set geometry" in message:
        return
    print(message, file=sys.stderr, flush=True)


class _Bridge(QObject):
    """Carries events from worker threads (recognition, hotkey, background scan) to the GUI thread."""

    cue = Signal(object)
    clear = Signal()
    toggle_panel = Signal()
    scan_progress = Signal(int, int)


def make_segmenter() -> SpeechSegmenter:
    """Cut speech with a neural voice detector (ignores music and ambience, so lines end when the voice
    does); if it cannot be loaded, fall back to plain loudness."""
    try:
        from dubzar.vad import WINDOW, SileroSpeechDetector

        return SpeechSegmenter(frame=WINDOW, is_speech=SileroSpeechDetector().is_speech, min_speech_s=0.3,
                               end_silence_s=0.5, max_segment_s=8.0)
    except Exception:
        log.warning("voice detector unavailable; falling back to loudness-based cutting", exc_info=True)
        return SpeechSegmenter(end_silence_s=0.5, max_segment_s=8.0)


def make_screen_source(settings: Settings, translator: Translator, bridge) -> ScreenSubtitleSource | None:
    """Reads the game's own English subtitles from the screen; None when Windows OCR is unavailable."""
    try:
        from dubzar.ocr import WindowsOcr

        ocr = WindowsOcr()
    except Exception as exc:
        log.warning("ekrandaki altyazı okuma kullanılamıyor (%s); yalnızca ses dinlenecek", exc)
        return None
    log.info("ekrandaki altyazı okuma hazır (OCR dili: %s)", ocr.language)

    def grab_frame():
        if not game_in_front(settings.game_exe, foreground_process_name(), foreground_is_fullscreen()):
            return None
        rect = foreground_monitor_rect()
        return grab(band_box(rect)) if rect else None

    return ScreenSubtitleSource(grab_frame, ocr, translator, bridge.cue.emit, bridge.clear.emit)


def run_live(store: IndexStore, store_path: str, settings: Settings, transcriber: Transcriber,
             translator: Translator, *, audio_dir: str | None = None,
             make_scan_transcriber: Callable[[], Transcriber] | None = None, screen_ocr: bool = True) -> int:
    qInstallMessageHandler(qt_message_filter)
    lower_priority()  # the game must always win when the processor is busy
    app = QApplication(sys.argv)
    animations = animations_enabled()
    controller = SettingsController(settings, screen_count=len(app.screens()), animations=animations)
    controller.set_live(True)
    overlay = OverlayWindow(settings)
    panel = PanelWindow(controller)
    intro = IntroWindow(animations)
    backdrop = Backdrop(animations)
    saver = SettingsSaver(settings)
    bridge = _Bridge()

    bridge.cue.connect(overlay.show_cue)
    bridge.clear.connect(overlay.clear_cue)
    for window in (overlay, backdrop, panel.view, intro.view):  # our own subtitle must never be read back by OCR
        exclude_from_capture(int(window.winId()))
    bridge.scan_progress.connect(controller.set_scan_progress)
    panel.on_closed(lambda: overlay.set_preview(None))
    panel.on_closed(backdrop.dismiss)

    def toggle_panel() -> None:
        if panel.is_open:
            panel.hide()
            return
        panel_screen = target_screen(settings.panel_screen)
        if panel_screen == target_screen("auto"):  # the panel is over the game: veil it like Steam's overlay does
            backdrop.show_on(panel_screen)         # (before the preview and the panel, so they stay above it)
        overlay.set_preview(PREVIEW_TEXT)  # so the user sees what they are adjusting
        panel.show(panel_screen)

    bridge.toggle_panel.connect(toggle_panel)

    hotkey = GlobalHotkey(bridge.toggle_panel.emit)
    hotkey_ok = hotkey.start(settings.hotkey)

    def show_hint() -> None:
        if hotkey_ok:
            intro.show_hint("ile ayarları aç", settings.screen, keys=settings.hotkey.split("+"))
        else:
            intro.show_hint("Kısayol kullanımda, ayarlar paneli açılamaz", settings.screen, 8000)

    if not hotkey_ok:
        print(f"Uyarı: {settings.hotkey} kısayolu başka bir program tarafından kullanılıyor. "
              "Ayarlar dosyasından başka bir kısayol seçin.", flush=True)
    watcher = None
    if settings.game_exe:  # like NVIDIA/Discord: the hint appears when the game opens, then fades away
        exe = settings.game_exe
        watcher = GameWatcher(lambda: is_process_running(exe), lambda: QTimer.singleShot(HINT_DELAY_MS, show_hint))
    else:  # the game is unknown: show the hint once now
        show_hint()

    screen_source = make_screen_source(settings, translator, bridge) if screen_ocr else None
    pipeline = LivePipeline(store, transcriber, translator, bridge.cue.emit, segmenter=make_segmenter(),
                            skip_recognition=(lambda: screen_source.active) if screen_source else (lambda: False))
    if screen_source is not None:
        screen_source.start()
    audio: queue.Queue = queue.Queue()

    def feed_pipeline() -> None:
        for chunk in queue_chunks(audio):
            try:
                pipeline.feed(chunk)
            except Exception:
                log.exception("audio chunk handling failed")

    feeder = threading.Thread(target=feed_pipeline, name="dubzar-feed", daemon=True)
    feeder.start()
    capture = LoopbackCapture(audio.put)
    capture.start()

    scanner: BackgroundScanner | None = None
    if audio_dir and settings.game_exe and make_scan_transcriber is not None:
        scanner = BackgroundScanner(audio_dir, store_path, make_scan_transcriber, lambda: translator,
                                    settings.game_exe, bridge.scan_progress.emit)
        scanner.start()
        print(f"Arka plan taraması etkin: {settings.game_exe} çalışırken bekler.", flush=True)

    warned = False

    def check_fullscreen() -> None:
        nonlocal warned
        if not warned and detect_exclusive_fullscreen():
            warned = True
            print(EXCLUSIVE_WARNING, flush=True)

    check_fullscreen()
    game_timer = QTimer()
    if watcher is not None:
        watcher.tick()
        game_timer.timeout.connect(watcher.tick)
        game_timer.start(GAME_POLL_MS)
    fullscreen_timer = QTimer()
    fullscreen_timer.timeout.connect(check_fullscreen)
    fullscreen_timer.start(5000)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    wakeup = QTimer()  # lets Python run the Ctrl+C handler while Qt owns the loop
    wakeup.timeout.connect(lambda: None)
    wakeup.start(200)

    print("Canlı mod: oyun sesi dinleniyor, altyazı gösteriliyor ve öğreniliyor. Çıkmak için Ctrl+C.", flush=True)
    try:
        app.exec()
    finally:
        hotkey.stop()
        if screen_source is not None:
            screen_source.stop()
        capture.stop()
        audio.put(None)
        feeder.join(2)
        pipeline.close(2)
        if scanner is not None:
            scanner.stop()
        saver.flush()
    return 0
