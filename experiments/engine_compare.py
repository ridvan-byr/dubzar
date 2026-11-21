"""Compare text readers on real game frames: our Windows-OCR pipeline, RapidOCR (PP-OCRv5 English) and OnnxTR (PARSeq).

python experiments/engine_compare.py [--folder "C:/Users/hp/Desktop/Oyun Kareleri"] [--json out.json]
"""
import argparse
import glob
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dubzar.ocr import OcrLine, RobustOcr, WindowsOcr  # noqa: E402
from dubzar.screen import band_box  # noqa: E402
from dubzar.subtitle_tracker import subtitle_text  # noqa: E402
from dubzar.textfix import fix_text  # noqa: E402


class RapidReader:
    def __init__(self):
        from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

        logging.getLogger("RapidOCR").setLevel(logging.ERROR)
        self.engine = RapidOCR(params={"Rec.lang_type": LangRec.EN, "Rec.ocr_version": OCRVersion.PPOCRV5,
                                       "Rec.model_type": ModelType.MOBILE})

    def read(self, image):
        h, w = image.shape[:2]
        out = self.engine(image)
        if out.txts is None:
            return []
        lines = []
        for text, box in zip(out.txts, out.boxes):
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            lines.append(OcrLine(text, float(np.mean(xs)) / w, float(np.mean(ys)) / h))
        return lines


class OnnxTRReader:
    def __init__(self):
        from onnxtr.models import ocr_predictor

        self.model = ocr_predictor(det_arch="db_mobilenet_v3_large", reco_arch="parseq")

    def read(self, image):
        result = self.model([image])
        lines = []
        for block in result.pages[0].blocks:
            for line in block.lines:
                (x0, y0), (x1, y1) = line.geometry
                text = " ".join(w.value for w in line.words)
                lines.append(OcrLine(text, (x0 + x1) / 2, (y0 + y1) / 2))
        return lines


def to_text(lines):
    central = [l.text for l in sorted(lines, key=lambda l: l.center_y) if 0.2 <= l.center_x <= 0.8]
    return subtitle_text(central) or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=r"C:\Users\hp\Desktop\Oyun Kareleri")
    ap.add_argument("--json")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    files = sorted(glob.glob(str(Path(args.folder) / "*.png")))
    readers = {"windows": RobustOcr(WindowsOcr()), "rapid": RapidReader()}
    try:
        readers["onnxtr"] = OnnxTRReader()
    except Exception as exc:  # noqa: BLE001
        print("OnnxTR başlatılamadı:", str(exc)[:150])
    results, times = {k: [] for k in readers}, {k: 0.0 for k in readers}
    for f in files:
        full = np.asarray(Image.open(f).convert("RGB"))
        h, w = full.shape[:2]
        l, t, r, b = band_box((0, 0, w, h))
        band = full[t:b, l:r]
        for name, reader in readers.items():
            t0 = time.perf_counter()
            text = to_text(reader.read(band))
            times[name] += time.perf_counter() - t0
            results[name].append(text)
    for name in readers:
        print(f"{name:8s} ortalama {times[name] / len(files) * 1000:6.0f} ms/kare")
    if args.json:
        Path(args.json).write_text(json.dumps({"files": files, **results}, ensure_ascii=False, indent=1), encoding="utf-8")
    for i in range(len(files)):
        print(f"\n{i + 1:2d}.")
        for name in readers:
            print(f"   {name:8s} {results[name][i]}")


if __name__ == "__main__":
    main()
