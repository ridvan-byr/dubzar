"""The live app: listens to the game, shows subtitles, learns, and opens the settings panel on a hotkey."""

import logging
import queue
import signal
import sys
import threading
from typing import Callable

from PySide6.QtCore import QObject, QRect, QTimer, Signal, qInstallMessageHandler
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
from dubzar.screen import (band_box, corner_boxes, exclude_from_capture, foreground_is_fullscreen, foreground_monitor_rect,
                           foreground_process_name, game_in_front, grab)
from dubzar.performance import profile_for
from dubzar.region_notes import RegionNoteSource
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
    note = Signal(object)
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


class _NoReader:
    def read(self, image):
        return []


def make_reader(profile=None):
    """The best text reader this computer can run: RapidOCR (measured far better on real game frames), with the
    Windows engine behind it as a safety net; either alone when the other is unavailable; None when neither is."""
    from dubzar import ocr as ocr_module

    windows = windows_engine = primary = None
    try:
        windows_engine = ocr_module.WindowsOcr()
    except Exception as exc:  # noqa: BLE001
        log.info("Windows OCR yok (%s)", exc)
    try:
        from dubzar.ocr_rapid import RapidOcr

        # Readings are rare now (only when the subtitle changes), so a short burst on 4 threads (0.38 s instead of
        # 0.66 s on 2) is worth it; the process runs at below-normal priority, the game keeps its cores.
        primary = RapidOcr(threads=profile.ocr_threads if profile else 4, gpu=bool(profile and profile.gpu_ocr))
    except Exception as exc:  # noqa: BLE001
        log.info("RapidOCR yok (%s)", exc)
    if primary is not None and windows_engine is not None:
        # two preparations are enough as a safety net behind RapidOCR (and cheaper)
        return ocr_module.CascadeOcr(primary, ocr_module.RobustOcr(windows_engine, max_variants=2))
    if primary is not None:
        return ocr_module.CascadeOcr(primary, _NoReader())
    if windows_engine is not None:
        return ocr_module.RobustOcr(windows_engine)          # on its own it keeps all its preparations
    return None


class _SharedReader:
    """One OCR engine serves the subtitle band and the corners: one reading at a time."""

    def __init__(self, reader):
        self._reader, self._lock = reader, threading.Lock()
        self.language = reader.language

    def read(self, image):
        with self._lock:
            return self._reader.read(image)


def make_screen_source(settings: Settings, translator: Translator, bridge):
    """Reads the game's own English subtitles from the screen; None when Windows OCR is unavailable.
    Returns (subtitle source, corner notes source)."""
    return _make_screen_source(settings, translator, bridge)


def _make_screen_source(settings: Settings, translator: Translator, bridge):
    """Reads the game's own English subtitles from the screen; None when Windows OCR is unavailable."""
    profile = profile_for(settings.performance)
    ocr = make_reader(profile)
    ocr = _SharedReader(ocr) if ocr is not None else None
    if ocr is None:
        log.warning("ekrandaki altyazı okuma kullanılamıyor (ne RapidOCR ne Windows OCR çalışıyor); yalnızca ses dinlenecek")
        return None, None
    log.info("ekrandaki altyazı okuma hazır (okuyucu: %s, mod: %s)", ocr.language, profile.label)

    def grab_frame():
        if not game_in_front(settings.game_exe, foreground_process_name(), foreground_is_fullscreen()):
            return None
        rect = foreground_monitor_rect()
        return grab(band_box(rect)) if rect else None

    def grab_corners():
        if not game_in_front(settings.game_exe, foreground_process_name(), foreground_is_fullscreen()):
            return None
        rect = foreground_monitor_rect()
        return [grab(box) for box in corner_boxes(rect)] if rect else None

    subtitles = ScreenSubtitleSource(grab_frame, ocr, translator, bridge.cue.emit, bridge.clear.emit,
                                     on_note=bridge.note.emit, poll_s=profile.poll_s, idle_poll_s=profile.idle_poll_s)
    corners = RegionNoteSource(grab_corners, ocr, translator, bridge.note.emit, poll_s=profile.corner_poll_s,
                               defer=lambda: subtitles.busy)

    def mode_changed(name: str) -> None:
        if name != "performance":
            return
        chosen = profile_for(settings.performance)
        subtitles.set_rhythm(chosen.poll_s, chosen.idle_poll_s)       # the pace changes at once;
        corners.set_rhythm(chosen.corner_poll_s)
        if chosen.gpu_ocr != profile.gpu_ocr:                          # the reader that does the work, at the next start
            log.info("mod değişti: okuyucu (ekran kartı/işlemci) program yeniden başlayınca değişir")

    settings.on_change(mode_changed)
    return subtitles, corners


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
    bridge.note.connect(overlay.show_note)
    for window in (overlay, backdrop, panel.view, intro.view):  # our own subtitle must never be read back by OCR
        exclude_from_capture(int(window.winId()))
    bridge.scan_progress.connect(controller.set_scan_progress)
    panel.on_closed(lambda: overlay.set_preview(None))
    controller.quitRequested.connect(app.quit)
    panel.on_closed(backdrop.dismiss)

    def veil_game_screen(panel_screen) -> None:
        """Like the Steam overlay: when the panel is over the game, the game's screen is dimmed behind it."""
        if panel_screen == target_screen("auto"):
            backdrop.set_clear_rect(QRect())
            backdrop.show_on(panel_screen)
        else:
            backdrop.dismiss()

    def bring_to_front() -> None:
        """Windows that do not take focus are not brought forward by show(): without this the panel stayed under the
        veil (measured: subtitle > veil > panel). Wanted, from the top: panel, subtitle preview, veil."""
        overlay.raise_()
        panel.raise_to_top()

    # the veil leaves the subtitle preview clear, so its colours are judged over the real picture
    overlay.placed.connect(lambda rect: backdrop.set_clear_rect(rect) if backdrop.isVisible() else None)

    def toggle_panel() -> None:
        if panel.is_open:
            panel.hide()
            return
        panel_screen = target_screen(settings.panel_screen)
        veil_game_screen(panel_screen)      # before the preview and the panel, so they stay above the veil
        overlay.set_preview(PREVIEW_TEXT)  # so the user sees what they are adjusting
        panel.show(panel_screen)
        bring_to_front()

    def follow_panel_screen_setting(name: str) -> None:
        """Picking another screen in the panel moves the open panel there at once (it used to wait for the next open)."""
        if name != "panel_screen" or not panel.is_open:
            return
        panel_screen = target_screen(settings.panel_screen)
        veil_game_screen(panel_screen)
        panel.move_to(panel_screen)
        bring_to_front()

    settings.on_change(follow_panel_screen_setting)

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

    screen_source, corner_source = make_screen_source(settings, translator, bridge) if screen_ocr else (None, None)
    pipeline = LivePipeline(store, transcriber, translator, bridge.cue.emit, segmenter=make_segmenter(),
                            skip_recognition=(lambda: screen_source.active) if screen_source else (lambda: False))
    if screen_source is not None:
        screen_source.start()
        corner_source.start()
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
        panel.close()       # unload the windows' QML first, so quitting prints no "of null" errors
        intro.close()
        hotkey.stop()
        if screen_source is not None:
            screen_source.stop()
            corner_source.stop()
        capture.stop()
        audio.put(None)
        feeder.join(2)
        pipeline.close(2)
        if scanner is not None:
            scanner.stop()
        saver.flush()
    return 0
