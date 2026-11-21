"""How well do we read game-style subtitles? Synthetic frames (many fonts, sizes, colours, outlines/boxes, busy or bright
backgrounds, blur and video compression) with known text; reports exact-match rate, character and word error rates.

python experiments/ocr_benchmark.py [--n 160] [--seed 3]
"""

import argparse
import io
import random
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

FONT_DIR = Path("C:/Windows/Fonts")
FONT_FILES = ["arial.ttf", "arialbd.ttf", "segoeui.ttf", "segoeuib.ttf", "verdana.ttf", "tahoma.ttf", "calibri.ttf",
              "calibrib.ttf", "trebuc.ttf", "georgia.ttf", "times.ttf", "bahnschrift.ttf", "framd.ttf", "impact.ttf",
              "consola.ttf", "comic.ttf"]
COLORS = [(255, 255, 255), (255, 255, 255), (255, 255, 255), (255, 235, 90), (190, 240, 255), (235, 235, 235)]
WIDTH = 1180
REALISTIC = False   # --realistic: the sizes and clean backgrounds of ordinary game subtitles


def available_fonts() -> list[Path]:
    found = [FONT_DIR / f for f in FONT_FILES if (FONT_DIR / f).exists()]
    found.append(ROOT / "dubzar" / "ui" / "fonts" / "DMSans.ttf")
    return found


def sentences(rng: random.Random, n: int) -> list[str]:
    from translation_testset import TESTSET

    pool = [line for _, line, _ in TESTSET]
    pool += [l.strip() for l in (ROOT / "training" / "replay_en.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    pool += [l.split(" ||| ")[0] for l in (ROOT / "training" / "pairs_004.txt").read_text(encoding="utf-8").splitlines() if " ||| " in l]
    pool = [p for p in pool if 12 <= len(p) <= 90]
    rng.shuffle(pool)
    return pool[:n]


def background(rng: random.Random, height: int) -> Image.Image:
    base = rng.choice([(20, 24, 30), (60, 52, 44), (110, 100, 90), (150, 160, 170), (30, 50, 40), (200, 190, 170), (90, 70, 60)])
    arr = np.zeros((height, WIDTH, 3), dtype=np.float32) + np.array(base, dtype=np.float32)
    ys, xs = np.mgrid[0:height, 0:WIDTH]
    for _ in range(rng.randint(2, 6)):                       # soft blobs of other colours: a "scene"
        cx, cy, r = rng.uniform(0, WIDTH), rng.uniform(0, height), rng.uniform(60, 400)
        color = np.array([rng.uniform(0, 255) for _ in range(3)], dtype=np.float32)
        weight = np.exp(-(((xs - cx) ** 2 + (ys - cy) ** 2) / (2 * r * r)))[..., None] * rng.uniform(0.3, 0.9)
        arr = arr * (1 - weight) + color * weight
    if not REALISTIC and rng.random() < 0.3:                 # a bright patch right behind the text: the hard case
        arr[height // 4: 3 * height // 4, rng.randint(100, 500): rng.randint(600, 1100)] += rng.uniform(60, 140)
    arr += np.random.default_rng(rng.randint(0, 10**6)).normal(0, rng.uniform(2, 10), arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def wrap(draw, text, font, limit):
    lines, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= limit or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    return lines + [current]


def render(text: str, rng: random.Random, fonts: list[Path]) -> np.ndarray:
    size = rng.choice([28, 30, 32, 36, 40] if REALISTIC else [20, 22, 24, 26, 28, 30, 32, 36])
    font = ImageFont.truetype(str(rng.choice(fonts)), size)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = wrap(probe, text, font, 900)
    line_h = int(size * 1.35)
    height = line_h * len(lines) + 70
    image = background(rng, height)
    draw = ImageDraw.Draw(image, "RGBA")
    color, style = rng.choice(COLORS), rng.choice(["outline", "outline", "outline", "box", "shadow", "plain"])
    for i, line in enumerate(lines):
        x = (WIDTH - draw.textlength(line, font=font)) / 2
        y = 35 + i * line_h
        if style == "box":
            draw.rectangle((x - 10, y - 3, x + draw.textlength(line, font=font) + 10, y + line_h - 4), fill=(0, 0, 0, 165))
            draw.text((x, y), line, font=font, fill=color)
        elif style == "outline":
            draw.text((x, y), line, font=font, fill=color, stroke_width=max(2, size // 12), stroke_fill=(0, 0, 0))
        elif style == "shadow":
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 220))
            draw.text((x, y), line, font=font, fill=color)
        else:
            draw.text((x, y), line, font=font, fill=color)
    image = image.convert("RGB")
    if rng.random() < 0.5:
        image = image.filter(ImageFilter.GaussianBlur(rng.choice([0.5, 0.8, 1.1])))
    if rng.random() < 0.5:                                    # video compression
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=rng.choice([55, 70, 85]))
        image = Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")
    return np.asarray(image)


def edit_distance(a, b) -> int:
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def squash(text: str) -> str:
    return " ".join(text.split())


def score(truth: list[str], read: list[str]) -> dict:
    exact = cer = wer = near = loose = 0.0
    for t, r in zip(truth, read):
        t, r = squash(t), squash(r)
        loose += t.lower() == r.lower()
        exact += t == r
        cer += edit_distance(t, r) / max(1, len(t))
        word_errors = edit_distance(t.split(), r.split())
        wer += word_errors / max(1, len(t.split()))
        near += word_errors <= 1
    n = len(truth)
    return {"exact": 100 * exact / n, "loose": 100 * loose / n, "cer": 100 * cer / n, "wer": 100 * wer / n,
            "within1": 100 * near / n}


def make_dataset(n: int, seed: int):
    rng = random.Random(seed)
    fonts = available_fonts()
    texts = sentences(rng, n)
    return texts, [render(t, rng, fonts) for t in texts]


def lines_to_text(lines) -> str:
    return " ".join(l.text for l in sorted(lines, key=lambda l: l.center_y))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=160)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--save", help="folder to save the frames and readings (to look at failures)")
    ap.add_argument("--realistic", action="store_true", help="easier, ordinary-subtitle sizes (28-40 px, no bright patch)")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")

    global REALISTIC
    REALISTIC = args.realistic
    texts, frames = make_dataset(args.n, args.seed)
    from dubzar.ocr import WindowsOcr

    readers = {"Windows OCR (şimdiki)": WindowsOcr().read}
    from dubzar.ocr import OcrLine
    from dubzar.textfix import fix_text

    plain = readers["Windows OCR (şimdiki)"]
    readers["+ sözlük düzeltmesi"] = lambda frame: [OcrLine(fix_text(l.text), l.center_x, l.center_y) for l in plain(frame)]
    try:
        from dubzar.ocr import RobustOcr
        readers["Dayanıklı okuyucu (yeni)"] = RobustOcr(WindowsOcr()).read
    except ImportError:
        pass

    for name, read in readers.items():
        started = time.perf_counter()
        outputs = [lines_to_text(read(frame)) for frame in frames]
        per_frame = (time.perf_counter() - started) / len(frames) * 1000
        s = score(texts, outputs)
        print(f"{name:28s} birebir {s['exact']:5.1f}% | büyük/küçük harf hariç {s['loose']:5.1f}% | ≤1 kelime hatası {s['within1']:5.1f}% | "
              f"harf hatası {s['cer']:5.2f}% | kelime hatası {s['wer']:5.2f}% | {per_frame:4.0f} ms/kare")
        if args.save:
            out = Path(args.save); out.mkdir(parents=True, exist_ok=True)
            for i, (t, o, frame) in enumerate(zip(texts, outputs, frames)):
                if squash(t) != squash(o):
                    Image.fromarray(frame).save(out / f"{name[:3]}_{i:03d}.png")
            lines = [f"{t}\n   -> {o}" for t, o in zip(texts, outputs) if squash(t) != squash(o)]
            (out / f"{name[:3]}_errors.txt").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
