"""Which image preparations actually help? Each variant alone, and the best a perfect chooser could do with them."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(errors="replace", encoding="utf-8")
import ocr_benchmark as ob
from dubzar import imageprep as ip
from dubzar.ocr import WindowsOcr
from dubzar.textfix import fix_text


def lum(f): return ip._luminance(f)
def mask_img(mask): return ip._mask_to_image(mask)
def bright_pct(p): return lambda f: mask_img(lum(f) >= max(150, np.percentile(lum(f), p)))
def local_contrast(k): return lambda f: mask_img(lum(f) > ndimage.uniform_filter(lum(f), size=31) + k)
def upscale_n(n): return lambda f: ip.upscale(f, n)
def dark_pct(p): return lambda f: mask_img(lum(f) <= np.percentile(lum(f), p) + 25)
def outlined(offset): return lambda f: ip._mask_to_image(ndimage.binary_dilation(lum(f) <= 70, iterations=3) & (lum(f) >= max(150, ip._bright_threshold(lum(f)) - offset)))
def maxchan(f): return mask_img(f.max(axis=2) >= max(160, np.percentile(f.max(axis=2), 93)))

VARIANTS = {
    "raw": lambda f: f, "x2": upscale_n(2), "x3": upscale_n(3),
    "bright p93 (şimdiki)": ip.bright_on_white, "bright p88": bright_pct(88), "bright p96": bright_pct(96),
    "outlined -25 (şimdiki)": ip.outlined_on_white, "outlined -50": outlined(50), "outlined 0": outlined(0),
    "dark (şimdiki)": ip.dark_on_white, "dark p15": dark_pct(15),
    "yerel kontrast +25": local_contrast(25), "yerel kontrast +45": local_contrast(45), "max kanal": maxchan,
}

texts, frames = ob.make_dataset(160, 3)
ocr = WindowsOcr()
exact = {k: [] for k in VARIANTS}
for t, f in zip(texts, frames):
    for name, fn in VARIANTS.items():
        read = fix_text(ob.lines_to_text(ocr.read(fn(f))))
        exact[name].append(ob.squash(read).lower() == ob.squash(t).lower())      # case-insensitive here
n = len(texts)
print(f"{'varyant':26s} tek başına doğru")
for name in VARIANTS: print(f"{name:26s} {100*sum(exact[name])/n:5.1f}%")
union = [any(exact[k][i] for k in VARIANTS) for i in range(n)]
print(f"\nHEPSİ birlikte (mükemmel seçici, üst sınır): {100*sum(union)/n:.1f}%")
# greedy: which variants add the most
chosen, covered = [], [False] * n
for _ in range(6):
    best = max(VARIANTS, key=lambda k: sum(exact[k][i] and not covered[i] for i in range(n)) if k not in chosen else -1)
    gain = sum(exact[best][i] and not covered[i] for i in range(n))
    if gain == 0: break
    chosen.append(best); covered = [c or exact[best][i] for i, c in enumerate(covered)]
    print(f"  + {best:26s} +{gain} kare (toplam {100*sum(covered)/n:.1f}%)")
