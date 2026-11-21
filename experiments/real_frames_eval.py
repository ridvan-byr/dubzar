"""Score text readers against hand-labelled real game frames (experiments/real_frames/labels.json).

python experiments/real_frames_eval.py [--readers windows,rapid,...] [--show]
Errors are measured on words (letters, digits, apostrophes; case and punctuation ignored), because the words are what
gets translated.
"""
import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from dubzar.screen import band_box  # noqa: E402


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))


def edit(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def score(truth: str, read: str) -> tuple[float, float, int]:
    tw, rw = words(truth), words(read)
    wer = edit(tw, rw) / max(1, len(tw))
    cer = edit(" ".join(tw), " ".join(rw)) / max(1, len(" ".join(tw)))
    return wer, cer, edit(tw, rw)


def load_bands(labels):
    bands = []
    for name in labels["files"]:
        a = np.asarray(Image.open(Path(labels["folder"]) / name).convert("RGB"))
        h, w = a.shape[:2]
        l, t, r, b = band_box((0, 0, w, h))
        bands.append(a[t:b, l:r])
    return bands


def evaluate(name, read_text, bands, labels, show=False):
    read_text(bands[0])                                   # warm-up (model start, first-call setup)
    t0 = time.perf_counter()
    outputs = [read_text(b) for b in bands]
    per_frame = (time.perf_counter() - t0) / len(bands) * 1000
    results = [score(t, o) for t, o in zip(labels["labels"], outputs)]
    perfect = sum(1 for _, _, e in results if e == 0)
    near = sum(1 for _, _, e in results if e <= 1)
    wer = sum(r[0] for r in results) / len(results)
    cer = sum(r[1] for r in results) / len(results)
    print(f"{name:34s} hatasız {perfect:2d}/31 | ≤1 kelime hatası {near:2d}/31 | kelime hatası {wer*100:5.1f}% | harf hatası {cer*100:5.1f}% | {per_frame:5.0f} ms/kare")
    if show:
        for i, (t, o, r) in enumerate(zip(labels["labels"], outputs, results), 1):
            if r[2]:
                print(f"   {i:2d}. ({r[2]} hata)\n       doğru: {t}\n       okuma: {o}")
    return outputs
