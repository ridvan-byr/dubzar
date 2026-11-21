"""Fast conversation: subtitles replace each other every HOLD seconds, back to back. How many reach the screen, and
how long are they visible? Real reader and translator, real labelled frames.

python experiments/fast_dialogue_probe.py [--hold 1.5] [--frames 2,13,18,24,25,29,31,5,8,10]
"""

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", type=float, default=1.5)
    ap.add_argument("--frames", default="2,13,18,24,25,29,31,5,8,10")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    import real_frames_eval as rf
    from dubzar.app import make_reader
    from dubzar.screen_source import ScreenSubtitleSource
    from dubzar.translate import OpusMtTranslator

    labels = json.load(open(ROOT / "experiments" / "real_frames" / "labels.json", encoding="utf-8"))
    bands = rf.load_bands(labels)
    reader, translator = make_reader(), OpusMtTranslator(threads=2)
    translator.load()
    ids = [int(i) for i in args.frames.split(",")]
    rng = np.random.default_rng(1)
    clock = {"t0": None}

    def current():
        if clock["t0"] is None:
            return None
        k = int((time.perf_counter() - clock["t0"]) // args.hold)
        return k if k < len(ids) else None

    def grab():
        k = current()
        base = bands[ids[k] - 1] if k is not None else bands[ids[0] - 1] * 0
        noise = rng.integers(-3, 4, base.shape, dtype=np.int16)
        return np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    shown = []                                           # (time, index of the subtitle on screen when shown, source)

    def on_cue(cue):
        shown.append((time.perf_counter() - clock["t0"], cue.text_src))

    source = ScreenSubtitleSource(grab, reader, translator, on_cue, lambda: None)
    source.start()
    time.sleep(1.0)
    clock["t0"] = time.perf_counter()
    time.sleep(args.hold * len(ids) + 3)
    source.stop()
    got = 0
    for k, idx in enumerate(ids):
        start, end = k * args.hold, (k + 1) * args.hold
        label = labels["lines"][idx - 1] if "lines" in labels else ""
        hits = [(t, s) for t, s in shown if start <= t < end + 3 and s.lower()[:12] in str(label).lower() or False]
        print(f"#{idx:2d} ekranda {start:4.1f}-{end:4.1f} sn")
    print(f"{len(shown)} altyazı gösterildi / {len(ids)} gönderildi")
    for t, s in shown:
        print(f"  {t:5.2f} sn  {s[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
