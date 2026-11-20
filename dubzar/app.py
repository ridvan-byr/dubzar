"""The live app: listens to the game, shows subtitles, opens the settings panel on a hotkey."""

import queue
import signal
import sys
import threading

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from dubzar.capture import LoopbackCapture, queue_chunks, run_matching
from dubzar.fingerprint import Matcher
from dubzar.hotkey import GlobalHotkey
from dubzar.index import IndexStore
from dubzar.overlay import detect_exclusive_fullscreen
from dubzar.overlay_window import OverlayWindow
from dubzar.settings import Settings
from dubzar.ui.controller import SettingsController
from dubzar.ui.intro import IntroWindow
from dubzar.ui.panel import PanelWindow
from dubzar.ui.saver import SettingsSaver
from dubzar.ui.screens import target_screen
from dubzar.ui.system import animations_enabled

PREVIEW_TEXT = "Sessiz ol… Birisi geliyor."
EXCLUSIVE_WARNING = (
    "Uyarı: tam ekran (exclusive) bir oyun algılandı, altyazı görünmeyebilir. "
    "Oyunu 'pencereli tam ekran' (borderless) modda çalıştırın."
)


class _Bridge(QObject):
    """Carries events from worker threads (matching, hotkey) to the GUI thread."""

    cue = Signal(object)
    toggle_panel = Signal()


def run_live(store: IndexStore, matcher: Matcher, settings: Settings) -> int:
    app = QApplication(sys.argv)
    animations = animations_enabled()
    controller = SettingsController(settings, screen_count=len(app.screens()), animations=animations)
    overlay = OverlayWindow(settings)
    panel = PanelWindow(controller)
    intro = IntroWindow(animations)
    saver = SettingsSaver(settings)
    bridge = _Bridge()

    bridge.cue.connect(overlay.show_cue)
    panel.on_closed(lambda: overlay.set_preview(None))

    def toggle_panel() -> None:
        if panel.is_open:
            panel.hide()
            return
        overlay.set_preview(PREVIEW_TEXT)  # so the user sees what they are adjusting
        panel.show(target_screen(settings.screen))

    bridge.toggle_panel.connect(toggle_panel)

    hotkey = GlobalHotkey(bridge.toggle_panel.emit)
    if hotkey.start(settings.hotkey):
        intro.show_hint("ile ayarları aç", settings.screen, keys=settings.hotkey.split("+"))
    else:
        print(f"Uyarı: {settings.hotkey} kısayolu başka bir program tarafından kullanılıyor. "
              "Ayarlar dosyasından başka bir kısayol seçin.", flush=True)
        intro.show_hint("Kısayol kullanımda, ayarlar paneli açılamaz", settings.screen, 8000)

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
        hotkey.stop()
        capture.stop()
        audio.put(None)
        worker.join(timeout=2)
        saver.flush()
    return 0
