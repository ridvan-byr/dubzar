"""Does GPU reading work with ONLY the pip packages the installer would add (no torch around), even when ctranslate2
(with its own cuDNN) is imported afterwards, as the app does?

Run with the python of a clean venv:
    <venv>/Scripts/python.exe experiments/gpu_pkg_check.py <folder with the two RapidOCR models> <band.png>
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402


def main() -> int:
    models, band = Path(sys.argv[1]), Path(sys.argv[2])
    import dubzar.ocr_rapid as rapid

    torch_here = any((Path(p) / "torch").is_dir() for p in sys.path)
    print("torch in this environment:", torch_here)
    print("CUDA library folders found:", [Path(p).parent.name + "/" + Path(p).name for p in rapid._cuda_library_folders()])
    ready = rapid.cuda_ready(rapid._a_model_file(models))                 # what the app does first, before the models
    print("cuda_ready:", ready)
    import ctranslate2  # noqa: F401  (its cut-down cuDNN loads now, as in the app)

    reader = rapid.RapidOcr(threads=2, gpu=True, model_dir=models)
    print("reader:", reader.language, "| gpu:", reader.gpu)
    image = np.asarray(Image.open(band).convert("RGB"))
    reader.read(image)
    began = time.perf_counter()
    lines = reader.read(image)
    print(f"read: {1000 * (time.perf_counter() - began):.0f} ms |", " ".join(l.text for l in lines)[:90])
    return 0 if reader.gpu else 1


if __name__ == "__main__":
    sys.exit(main())
