"""Builds the installer zip for a friend: python installer/build_zip.py  ->  dist/Dubzar-Kurulum-<version>.zip

Layout inside the zip (one top-level folder, so extracting does not scatter files):
    Dubzar-Kurulum/Kur.bat, Kaldir.bat, kur.ps1, kaldir.ps1, OKU-BENI.txt
    Dubzar-Kurulum/app/dubzar/...       the program (no tests, no caches)
    Dubzar-Kurulum/app/requirements.txt, app/LISANSLAR.md
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
- **PySide6 (Qt for Python)** LGPL-3.0 ile lisanslıdır; kurulum sırasında PyPI'dan ayrı bir paket olarak indirilir,
  Dubzar ile birlikte kopyalanmaz.
- Python paketleri kendi lisanslarıyla kurulur: faster-whisper (MIT), CTranslate2 (MIT), transformers (Apache-2.0),
  PyTorch (BSD), numpy/scipy (BSD) vb.
"""


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)


def app_files():
    for path in sorted((ROOT / "dubzar").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            yield path, f"{TOP}/app/dubzar/{path.relative_to(ROOT / 'dubzar').as_posix()}"


def build(out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"Dubzar-Kurulum-{version()}.zip"
    target.unlink(missing_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path, arc in app_files():
            z.write(path, arc)
        z.write(HERE / "requirements.txt", f"{TOP}/app/requirements.txt")
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
