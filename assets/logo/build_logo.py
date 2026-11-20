"""Builds the Dubzar logo SVGs: python assets/logo/build_logo.py

The mark is a "D" whose counter is a die pip. The wordmark is Instrument Serif Italic
converted to outlines, so the SVG needs no font installed.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtGui import QFont, QGuiApplication, QPainterPath  # noqa: E402

from dubzar.ui.fonts import load_bundled_fonts  # noqa: E402

AMBER, GRAPHITE, CREAM = "#FFB224", "#0E0F11", "#F7F5F0"
OUT = Path(__file__).parent

# D: stem 64 wide, bowl 64 wide at the right, round pip as the counter. Box 140..372 x 124..388.
D_PATH = "M140 124H240A132 132 0 0 1 240 388H140Z M256 204A52 52 0 1 0 256 308A52 52 0 1 0 256 204Z"


def mark(fill: str, transform: str = "") -> str:
    t = f' transform="{transform}"' if transform else ""
    return f'<path d="{D_PATH}" fill="{fill}" fill-rule="evenodd"{t}/>'


def svg(w: int, h: int, body: str, label: str = "Dubzar") -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">{body}</svg>\n'


def wordmark_path(text: str, size_px: int, x: float, baseline: float) -> tuple[str, float]:
    font = QFont("Instrument Serif")
    font.setItalic(True)
    font.setPixelSize(size_px)
    path = QPainterPath()
    path.addText(x, baseline, font, text)
    d, i = [], 0
    while i < path.elementCount():
        e = path.elementAt(i)
        if e.isMoveTo():
            d.append(f"M{e.x:.2f} {e.y:.2f}")
        elif e.isLineTo():
            d.append(f"L{e.x:.2f} {e.y:.2f}")
        else:  # cubic curve: this element and the next two
            c2, p = path.elementAt(i + 1), path.elementAt(i + 2)
            d.append(f"C{e.x:.2f} {e.y:.2f} {c2.x:.2f} {c2.y:.2f} {p.x:.2f} {p.y:.2f}")
            i += 2
        i += 1
        if i < path.elementCount() and path.elementAt(i).isMoveTo():
            d.append("Z")
    d.append("Z")
    return "".join(d), path.boundingRect().right()


def main() -> None:
    app = QGuiApplication(sys.argv)
    load_bundled_fonts()
    (OUT / "dubzar-mark.svg").write_text(svg(512, 512, mark(AMBER)), encoding="utf-8")
    badge = f'<rect x="32" y="32" width="448" height="448" rx="112" fill="{AMBER}"/>' + mark(GRAPHITE, "translate(256 256) scale(0.78) translate(-256 -256)")
    (OUT / "dubzar-badge.svg").write_text(svg(512, 512, badge), encoding="utf-8")
    # mark scaled 0.9 and centred vertically in a 300-high box; the wordmark baseline sits on the mark's bottom edge
    word, right = wordmark_path("Dubzar", 204, 285, 268.8)
    body = mark(AMBER, "translate(-86 -80.4) scale(0.9)") + f'<path d="{word}" fill="{CREAM}"/>'
    (OUT / "dubzar-lockup.svg").write_text(svg(int(right + 40), 300, body), encoding="utf-8")
    # integrated wordmark: the geometric D-pip is the capital D, followed by "ubzar" in italic serif
    probe = QPainterPath()
    f = QFont("Instrument Serif"); f.setItalic(True); f.setPixelSize(204)
    probe.addText(0, 0, f, "b")
    ascender = -probe.boundingRect().top()            # height of the tallest lower-case letter above the baseline
    k = ascender / 264                                # scale the D (264 units tall) to that height
    baseline, d_left = ascender + 40, 40.0  # 40 units of room above the tallest letter
    d_width = 232 * k
    rest, right = wordmark_path("ubzar", 204, d_left + d_width + 14, baseline)
    d_mark = mark(AMBER, f"translate({d_left - 140 * k:.2f} {baseline - 388 * k:.2f}) scale({k:.4f})")
    (OUT / "dubzar-wordmark.svg").write_text(svg(int(right + 40), int(baseline + 40), d_mark + f'<path d="{rest}" fill="{CREAM}"/>'), encoding="utf-8")
    print("written:", *sorted(p.name for p in OUT.glob("dubzar-*.svg")))


if __name__ == "__main__":
    main()
