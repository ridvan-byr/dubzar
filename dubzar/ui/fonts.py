"""The bundled UI fonts (SIL Open Font License; see ``fonts/OFL-*.txt`` and docs/LICENSES.md)."""

from pathlib import Path

from PySide6.QtGui import QFontDatabase

FONT_DIR = Path(__file__).with_name("fonts")
FONT_FILES = ("DMSans.ttf", "InstrumentSerif-Italic.ttf")


def load_bundled_fonts() -> list[str]:
    """Register the bundled fonts with Qt and return the family names they provide."""
    families: list[str] = []
    for name in FONT_FILES:
        font_id = QFontDatabase.addApplicationFont(str(FONT_DIR / name))
        if font_id < 0:
            raise RuntimeError(f"could not load bundled font {name}")
        families.extend(QFontDatabase.applicationFontFamilies(font_id))
    return families
