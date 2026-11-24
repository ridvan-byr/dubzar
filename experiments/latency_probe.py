"""How long after a subtitle appears on screen is its Turkish translation shown?

A moving scene without subtitles is played for a moment, then a real game frame (with its subtitle) replaces it; the
time until the app emits the Turkish cue is measured. Uses the real reader and translator on the labelled real frames.

python experiments/latency_probe.py [--module path/to/old_screen_source.py] [--trials 6]
"""

import argparse
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))


def load_source_class(path: str | None):
    if path is None:
        from dubzar.screen_source import ScreenSubtitleSource

        return ScreenSubtitleSource
    spec = importlib.util.spec_from_file_location("old_screen_source", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ScreenSubtitleSource


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module")
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--performance", default="light", choices=("light", "high"))
    ap.add_argument("--frames", default="2,13,18,24,25,29,31")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")

    import real_frames_eval as rf
    from dubzar.app import make_reader
    from dubzar.translate import OpusMtTranslator

    labels = json.load(open(ROOT / "experiments" / "real_frames" / "labels.json", encoding="utf-8"))
    bands = rf.load_bands(labels)
    from dubzar.performance import profile_for

    profile = profile_for(args.performance)
    reader, translator = make_reader(profile), OpusMtTranslator(threads=2)
    print("okuyucu:", getattr(reader, "language", "?"), "| mod:", profile.label)
    translator.load()
    source_class = load_source_class(args.module)
    rng = np.random.default_rng(1)
    indices = [int(i) for i in args.frames.split(",")][: args.trials]
    results = []
    for idx in indices:
        subtitle = bands[idx - 1]
        # a scene with no subtitle: another frame's upper part, jittering like a moving picture
        h, w = subtitle.shape[:2]
        scene = rf.load_bands.__globals__["np"].asarray(
            __import__("PIL.Image", fromlist=["Image"]).open(str(Path(labels["folder"]) / labels["files"][idx - 1])).convert("RGB"))
        empty = scene[int(0.05 * scene.shape[0]): int(0.05 * scene.shape[0]) + h, int(0.06 * scene.shape[1]): int(0.06 * scene.shape[1]) + w]
        start = {"t": None}
        shown = threading.Event()
        cue_time = {}

        def grab():
            base = subtitle if start["t"] is not None and time.perf_counter() >= start["t"] else empty
            noise = rng.integers(-3, 4, base.shape, dtype=np.int16)
            return np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        def on_cue(cue):
            cue_time.setdefault("t", time.perf_counter())
            shown.set()

        source = source_class(grab, reader, translator, on_cue, lambda: None, poll_s=profile.poll_s,
                              idle_poll_s=profile.idle_poll_s)
        source.start()
        time.sleep(1.2)                          # the scene runs for a while, no subtitle
        start["t"] = time.perf_counter()         # the subtitle appears NOW
        ok = shown.wait(15)
        source.stop()
        latency = cue_time["t"] - start["t"] if ok else float("nan")
        results.append(latency)
        print(f"#{idx:2d}: altyazı ekrana çıktıktan {latency:5.2f} sn sonra Türkçesi gösterildi")
    print(f"ortalama {np.nanmean(results):.2f} sn | en iyi {np.nanmin(results):.2f} | en kötü {np.nanmax(results):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
