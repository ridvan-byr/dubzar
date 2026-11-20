"""Does screen capture + Windows OCR see a game's own subtitles? (experiment, not part of the app)

Usage:  python experiments/fullscreen_capture_probe.py
1. Start the game, turn its subtitles ON, get to a scene with a spoken, subtitled line. (Run this from a
   terminal you started BEFORE the game; do not alt-tab afterwards.)
2. The probe waits 15 s (long enough to start a conversation in the game), takes ONE screenshot of the lower
   part of the screen, and tells you whether it came back black and what Windows OCR read.
Nothing is sent anywhere; the screenshot is saved next to this file (experiments/probe_out/).
"""

import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import ImageGrab

HERE = Path(__file__).parent
OUT = HERE / "probe_out"
WAIT_S = 15


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for left in range(WAIT_S, 0, -1):
        print(f"\r{left:2d} sn sonra ekran yakalanacak (oyunda altyazılı bir konuşma olsun)…", end="", flush=True)
        time.sleep(1)
    started = time.perf_counter()
    shot = ImageGrab.grab()
    took_ms = (time.perf_counter() - started) * 1000
    w, h = shot.size
    lower = shot.crop((int(w * 0.15), int(h * 0.65), int(w * 0.85), int(h * 0.97)))
    full_path, lower_path = OUT / "full.png", OUT / "lower.png"
    shot.save(full_path)
    lower.save(lower_path)

    pixels = np.asarray(shot)
    mean, spread = float(pixels.mean()), float(pixels.std())
    print(f"\nyakalama: {w}x{h}, {took_ms:.0f} ms, ortalama parlaklık {mean:.1f}, değişim {spread:.1f}")
    if mean < 2 and spread < 2:
        print("SONUÇ: görüntü SİYAH geldi, bu modda ekran yakalanamıyor.")
    else:
        print("SONUÇ: görüntü geldi (siyah değil). Aşağıda OCR'ın okuduğu yazılar:")
    for lang in ("tr", "en-US"):
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "ocr_test.ps1"),
             "-Path", str(lower_path), "-Lang", lang],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"--- OCR ({lang}) ---\n{result.stdout.strip()}")
    print(f"\nGörüntüler: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
