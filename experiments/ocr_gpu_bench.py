"""RapidOCR on the CPU against the GPU (onnxruntime-gpu) on the labelled real subtitle bands.

Run with the python of a venv that has onnxruntime-gpu (it must not be the app's own environment):
    experiments/ort_gpu_env/Scripts/python.exe experiments/ocr_gpu_bench.py <folder of band PNGs> <rapidocr models folder>
"""

import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


def make(threads: int, models: Path, cuda: bool):
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

    params = {
        "Rec.lang_type": LangRec.EN, "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE,
        "Det.limit_type": "max", "Det.limit_side_len": 1536,
        "Det.model_path": str(models / "PP-OCRv6_det_small.onnx"),
        "Rec.model_path": str(models / "en_PP-OCRv5_rec_mobile.onnx"),
        "EngineConfig.onnxruntime.intra_op_num_threads": threads, "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }
    if cuda:
        params["EngineConfig.onnxruntime.use_cuda"] = True
    return RapidOCR(params=params)


def main() -> int:
    sys.stdout.reconfigure(errors="replace", encoding="utf-8")
    bands_dir, models = Path(sys.argv[1]), Path(sys.argv[2])
    for extra in sys.argv[3:]:
        os.add_dll_directory(extra)                                    # CUDA 12 / cuDNN 9 libraries
    import onnxruntime as ort

    print("onnxruntime", ort.__version__, ort.get_available_providers())
    images = [np.asarray(Image.open(p).convert("RGB")) for p in sorted(bands_dir.glob("*.png"))]
    for name, threads, cuda in (("CPU 4 thread", 4, False), ("GPU (CUDA)", 2, True)):
        engine = make(threads, models, cuda)
        for image in images[:3]:
            engine(image, use_cls=False)                               # warm up
        times, texts = [], []
        for image in images:
            began = time.perf_counter()
            out = engine(image, use_cls=False)
            times.append(time.perf_counter() - began)
            texts.append(" ".join(out.txts) if out.txts else "")
        print(f"{name:13s} ortalama {1000 * np.mean(times):6.0f} ms | en yavaş {1000 * max(times):6.0f} ms | "
              f"CPU süresi: ölçülmedi", flush=True)
        Path(f"ocr_gpu_bench_{'gpu' if cuda else 'cpu'}.txt").write_text("\n".join(texts), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
