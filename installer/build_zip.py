"""Builds the installer zip for a friend: python installer/build_zip.py  ->  dist/Dubzar-Kurulum-<version>.zip

Layout inside the zip (one top-level folder, so extracting does not scatter files):
    Dubzar-Kurulum/Kur.bat, Kaldir.bat, kur.ps1, kaldir.ps1, OKU-BENI.txt
    Dubzar-Kurulum/app/dubzar/...       the program (no tests, no caches)
    Dubzar-Kurulum/app/requirements.txt, app/LISANSLAR.md
    Dubzar-Kurulum/wheels/*.whl, models/...  the Python packages and the two models, so nothing is downloaded
PowerShell scripts are written with a UTF-8 BOM (Windows PowerShell 5.1 would garble Turkish letters without it) and
batch files with CRLF line endings.
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).parent
TOP = "Dubzar-Kurulum"

EXTRA_NOTICE = """

## Ek bilgiler

- **Çeviri modeli:** Helsinki-NLP / OPUS-MT (opus-mt-tc-big-en-tr), CC-BY-4.0.
  https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-en-tr
  Dubzar ile gelen sürüm bu modelin CTranslate2 biçimine dönüştürülmüş ve int8 olarak nicemlenmiş halidir (değiştirilmiştir);
  özgün model Helsinki-NLP / Tiedemann ve ekibine aittir.
- **Konuşma tanıma:** Whisper tiny (OpenAI, MIT), faster-whisper için CTranslate2 biçiminde (Systran).
- **Metin okuma:** RapidOCR (Apache-2.0) ve PaddleOCR'ın PP-OCR modelleri (Apache-2.0), `app/models/rapidocr/` içinde
  paketle birlikte gelir.
- **PySide6 (Qt for Python)** LGPL-3.0 ile lisanslıdır; ayrı, değiştirilmemiş bir paket (`wheels/` klasörü) olarak
  gelir ve kullanıcı tarafından yerine başka bir sürüm kurulabilir.
- Python paketleri kendi lisanslarıyla kurulur: faster-whisper (MIT), CTranslate2 (MIT), numpy/scipy (BSD) vb.
"""


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)


def app_files():
    for path in sorted((ROOT / "dubzar").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            yield path, f"{TOP}/app/dubzar/{path.relative_to(ROOT / 'dubzar').as_posix()}"


def rapidocr_models() -> list[Path]:
    """The two model files the text reader needs, from the installed rapidocr package (the app ships them, so the
    installer never downloads them from a third-party site)."""
    import rapidocr

    folder = Path(rapidocr.__file__).parent / "models"
    sys.path.insert(0, str(ROOT))
    from dubzar.ocr_rapid import DET_MODEL, REC_MODEL

    files = [folder / DET_MODEL, folder / REC_MODEL]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        raise SystemExit(f"RapidOCR model files are missing ({missing}); run the app once so they are downloaded, then build.")
    return files


WHEELS = ROOT / "dist" / "wheels"      # made by: pip wheel -r installer/requirements.txt -w dist/wheels


def bundled_models() -> list[tuple[Path, str]]:
    """(file, path inside the zip's models folder) for the translation model (already converted to int8, with its two
    tokenizer files) and the Whisper tiny model, taken from this computer: the installer then downloads nothing."""
    sys.path.insert(0, str(ROOT))
    from dubzar.translate import CT2_FOLDER_NAME, MODEL_NAME, SPM_FILES, ct2_model_dir

    hub = Path.home() / ".cache" / "huggingface" / "hub"
    opus = sorted((hub / ("models--" + MODEL_NAME.replace("/", "--")) / "snapshots").glob("*"))
    whisper = sorted((hub / "models--Systran--faster-whisper-tiny" / "snapshots").glob("*"))
    if not opus or not whisper or not (ct2_model_dir() / "model.bin").exists():
        raise SystemExit("The models are missing on this computer; run 'dubzar setup --allow-download' first, then build.")
    files = [(ct2_model_dir() / n, f"{CT2_FOLDER_NAME}/{n}") for n in ("model.bin", "config.json", "shared_vocabulary.json")]
    files += [(opus[-1] / n, f"{CT2_FOLDER_NAME}/{n}") for n in SPM_FILES]
    files += [(f.resolve(), f"faster-whisper-tiny/{f.name}") for f in whisper[-1].iterdir()]
    return files


def build(out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"Dubzar-Kurulum-{version()}.zip"
    target.unlink(missing_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path, arc in app_files():
            z.write(path, arc)
        z.write(HERE / "requirements.txt", f"{TOP}/app/requirements.txt")
        for model in rapidocr_models():
            z.write(model, f"{TOP}/app/models/rapidocr/{model.name}")
        for wheel in sorted(WHEELS.glob("*.whl")):
            z.write(wheel, f"{TOP}/wheels/{wheel.name}", compress_type=zipfile.ZIP_STORED)
        for file, name in bundled_models():
            z.write(file, f"{TOP}/models/{name}", compress_type=zipfile.ZIP_STORED)
        licenses = (ROOT / "docs" / "LICENSES.md").read_text(encoding="utf-8") + EXTRA_NOTICE
        z.writestr(f"{TOP}/app/LISANSLAR.md", licenses.encode("utf-8"))
        for name in ("kur.ps1", "kaldir.ps1"):
            z.writestr(f"{TOP}/{name}", (HERE / name).read_text(encoding="utf-8").replace("\r\n", "\n")
                       .replace("\n", "\r\n").encode("utf-8-sig"))
        for name in ("Kur.bat", "Kaldir.bat"):
            text = (HERE / name).read_text(encoding="ascii").replace("\r\n", "\n").replace("\n", "\r\n")
            z.writestr(f"{TOP}/{name}", text.encode("ascii"))
        z.writestr(f"{TOP}/OKU-BENI.txt", (HERE / "OKU-BENI.txt").read_text(encoding="utf-8")
                   .replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8-sig"))
    return target


if __name__ == "__main__":
    result = build()
    print(f"{result}  ({result.stat().st_size / 1e6:.1f} MB)")
    sys.exit(0)
