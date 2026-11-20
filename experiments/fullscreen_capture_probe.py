"""Does screen capture + Windows OCR see a game's own subtitles? (experiment, not part of the app)

Usage:  python experiments/fullscreen_capture_probe.py
1. Start the probe in a terminal. After a short countdown it records for 30 s: switch to the game (or a video
   with burned-in subtitles) during the countdown and play a stretch with spoken, subtitled lines.
2. Every 1.5 s it grabs the lower part of the screen, then reports how many frames came back black, which
   window was in front, and every text line Windows OCR read (with how many frames it appeared in).
Nothing is sent anywhere; the frames are saved next to this file (experiments/probe_out/).
"""

import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import ImageGrab

HERE = Path(__file__).parent
OUT = HERE / "probe_out"
START_S = 10   # time to switch to the game
WAIT_S = 30    # recording length


def foreground_window_title() -> str:
    """Which window is in front at the moment of the capture (so we know what was measured)."""
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buffer, 256)
    return buffer.value or "(başlıksız pencere)"


def ocr_lines(image_path: Path, lang: str) -> list[str]:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "ocr_test.ps1"),
         "-Path", str(image_path), "-Lang", lang],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [line[6:].strip() for line in result.stdout.splitlines() if line.startswith("LINE: ")]


def main() -> int:
    sys.stdout.reconfigure(errors="replace")  # a Turkish console cannot print every character OCR may return
    OUT.mkdir(exist_ok=True)
    for left in range(START_S, 0, -1):
        print(f"\r{left:2d} sn sonra kayıt başlıyor (oyuna/videoya geçin)…  ", end="", flush=True)
        time.sleep(1)
    print("\nKAYIT BAŞLADI: altyazılı konuşma bölümünü oynatın…", flush=True)
    frames = []
    started = time.perf_counter()
    while time.perf_counter() - started < WAIT_S:
        title = foreground_window_title()
        t0 = time.perf_counter()
        shot = ImageGrab.grab()
        took = (time.perf_counter() - t0) * 1000
        w, h = shot.size
        path = OUT / f"lower_{len(frames):02d}.png"
        shot.crop((int(w * 0.10), int(h * 0.70), int(w * 0.90), int(h * 0.97))).save(path)
        pixels = np.asarray(shot)
        frames.append((path, title, took, float(pixels.mean()), float(pixels.std())))
        time.sleep(1.5)

    black = sum(1 for f in frames if f[3] < 2 and f[4] < 2)
    print(f"\n{len(frames)} kare alındı, {black} tanesi siyah. Önde olan pencereler: "
          f"{sorted({f[1] for f in frames})}")
    print(f"yakalama süresi ortalama {sum(f[2] for f in frames) / len(frames):.0f} ms")
    seen: dict[str, int] = {}
    for path, *_ in frames:
        for line in ocr_lines(path, "tr"):
            seen[line] = seen.get(line, 0) + 1
    print("\nOCR'ın okuduğu yazılar (kaç karede göründüğüyle):")
    for line, count in sorted(seen.items(), key=lambda kv: -kv[1]):
        print(f"  {count:2d}x  {line}")
    if not seen:
        print("  (hiçbir şey okunmadı: altyazı yok ya da okunamadı)")
    print(f"\nGörüntüler: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
