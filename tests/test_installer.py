import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "installer"))

import build_zip  # noqa: E402


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build_zip.build(tmp_path_factory.mktemp("dist"))


def names(zip_path):
    return zipfile.ZipFile(zip_path).namelist()


def test_zip_has_the_installer_the_program_and_the_icon(built):
    files = names(built)
    top = build_zip.TOP

    for expected in ("Kur.bat", "Kaldir.bat", "kur.ps1", "kaldir.ps1", "OKU-BENI.txt", "app/requirements.txt",
                     "app/LISANSLAR.md", "app/dubzar/__main__.py", "app/dubzar/cli.py", "app/dubzar/ui/dubzar.ico",
                     "app/dubzar/ui/Panel.qml", "app/dubzar/ui/fonts/DMSans.ttf"):
        assert f"{top}/{expected}" in files, expected


def test_zip_carries_the_two_text_reader_models_and_no_other_models(built):
    from dubzar.ocr_rapid import DET_MODEL, REC_MODEL

    shipped = sorted(n.split("/")[-1] for n in names(built) if "/models/" in n)

    assert shipped == sorted([DET_MODEL, REC_MODEL])


def test_zip_carries_no_tests_caches_or_large_weights(built):
    for name in names(built):
        assert "__pycache__" not in name and not name.endswith(".pyc")
        assert "/tests/" not in name and "/experiments/" not in name and "models_" not in name
        assert not name.endswith((".gguf", ".safetensors", ".bin", ".db"))


def test_powershell_scripts_have_a_bom_and_batch_files_are_plain_ascii(built):
    z = zipfile.ZipFile(built)
    for name in ("kur.ps1", "kaldir.ps1", "OKU-BENI.txt"):
        assert z.read(f"{build_zip.TOP}/{name}").startswith(b"\xef\xbb\xbf"), f"{name} needs a UTF-8 BOM"
    for name in ("Kur.bat", "Kaldir.bat"):
        data = z.read(f"{build_zip.TOP}/{name}")
        assert all(b < 128 for b in data) and b"\r\n" in data


def test_requirements_include_the_text_reader():
    text = (ROOT / "installer" / "requirements.txt").read_text()

    assert "rapidocr==" in text and "opencv-python-headless==" in text


def test_requirements_are_pinned_and_the_qt_package_is_the_small_one():
    lines = [l.strip() for l in (ROOT / "installer" / "requirements.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]

    assert all("==" in l for l in lines)
    assert any(l.startswith("PySide6-Essentials==") for l in lines)
    assert not any(l.startswith("PySide6==") for l in lines)     # the full package drags in WebEngine and more


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell")
@pytest.mark.parametrize("script", ["kur.ps1", "kaldir.ps1"])
def test_powershell_scripts_parse(script, tmp_path, built):
    extracted = tmp_path / script
    extracted.write_bytes(zipfile.ZipFile(built).read(f"{build_zip.TOP}/{script}"))
    command = ("$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
               f"'{extracted}', [ref]$null, [ref]$e); if ($e) {{ $e | ForEach-Object {{ $_.Message }}; exit 1 }}")

    result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True)

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_start_shortcut_points_at_the_windowless_python_with_the_d_icon():
    text = (ROOT / "installer" / "kur.ps1").read_text(encoding="utf-8")

    assert "pythonw.exe" in text and "dubzar.ico" in text and '"-m dubzar run"' in text
