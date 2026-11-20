import os
import struct
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtSvg")

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "dubzar" / "ui"
ICO = UI / "dubzar.ico"
LOGO = UI / "dubzar-logo.svg"
SIZES = {16, 24, 32, 48, 64, 128, 256}


@pytest.fixture(scope="module")
def qapp():
    # always a QApplication: a bare QGuiApplication left behind would crash later widget tests
    return QApplication.instance() or QApplication([])


def test_ico_has_every_standard_size_as_png_entries():
    data = ICO.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    assert (reserved, kind) == (0, 1)

    sizes = set()
    for i in range(count):
        w, h, _, _, planes, bits, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        size = w or 256
        sizes.add(size)
        assert w == h and (planes, bits) == (1, 32)
        assert data[offset:offset + 8] == b"\x89PNG\r\n\x1a\n", "entries are PNG-compressed"
        assert offset + length <= len(data)

    assert sizes == SIZES


def test_qt_reads_the_ico_and_offers_the_sizes(qapp):
    icon = QIcon(str(ICO))

    assert not icon.isNull()
    assert {s.width() for s in icon.availableSizes()} >= {16, 32, 48, 256}


def test_tight_logo_is_valid_and_has_the_cropped_aspect_ratio(qapp):
    renderer = QSvgRenderer(str(LOGO))

    assert renderer.isValid()
    box = renderer.viewBoxF()
    assert 2.0 < box.width() / box.height() < 2.6  # big D next to "ubzar", no empty margins


def test_logo_text_is_outlines_not_a_font_reference():
    assert "<text" not in LOGO.read_text(encoding="utf-8")  # must render the same on any machine


def test_logo_files_are_listed_as_package_data():
    config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "*.svg" in config and "*.ico" in config
