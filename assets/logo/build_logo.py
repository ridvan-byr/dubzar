"""Builds the Dubzar logo SVGs: python assets/logo/build_logo.py

The mark is a "D" whose counter is a die pip. The wordmark is Instrument Serif Italic
converted to outlines, so the SVG needs no font installed.
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QFont, QGuiApplication, QImage, QPainter, QPainterPath  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from dubzar.ui.fonts import load_bundled_fonts  # noqa: E402

AMBER, GRAPHITE, CREAM = "#FFB224", "#0E0F11", "#F7F5F0"
OUT = Path(__file__).parent
UI_DIR = Path(__file__).resolve().parents[2] / "dubzar" / "ui"  # logo + icon shipped inside the package
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)

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


D_H = 264.0  # height of the D mark in its own units
TEXT_SIZE, TEXT_GAP, TEXT_DY = 170, 1.0, -6.0  # tuned by hand in the reveal tuner
TEXT_ASCENDER_RATIO = 0.48  # tallest small letter as a fraction of the D's height


def reveal_geometry(align: str):
    """Layout of the big-D lockup. ``align``: "baseline" (letters sit on the D's bottom edge)
    or "pip" (letters' x-height is centred on the D's pip line)."""
    probe_font = QFont("Instrument Serif")
    probe_font.setItalic(True)
    probe_font.setPixelSize(204)
    b = QPainterPath(); b.addText(0, 0, probe_font, "b")
    x = QPainterPath(); x.addText(0, 0, probe_font, "x")
    asc204, xh204 = -b.boundingRect().top(), -x.boundingRect().top()
    size = TEXT_SIZE
    xh = xh204 * size / 204
    margin, gap = 60.0, TEXT_GAP
    d_left, d_bottom = margin, margin + D_H
    text_x = d_left + 232 + gap
    baseline = d_bottom + TEXT_DY if align == "baseline" else (margin + D_H / 2) + xh / 2
    word, right = wordmark_path("ubzar", size, text_x, baseline)
    return dict(margin=margin, d_left=d_left, d_bottom=d_bottom, text_x=text_x, word=word, right=right,
                width=right + margin, height=margin * 2 + D_H, gap=gap)


def d_markup(g: dict, extra: str = "") -> str:
    # mark() is drawn in a 512 box with the D at x 140..372, y 124..388; move it to d_left / d_bottom
    return mark(AMBER, f"translate({g['d_left'] - 140:.2f} {g['d_bottom'] - 388:.2f})") if not extra else extra


# reveal timing (milliseconds) and easing, shared with the preview script
EASE = "cubic-bezier(.2,.8,.2,1)"
D_IN_MS = 360
WORD_DELAY_MS, WORD_MS, WORD_FADE_MS = 520, 720, 280


def reveal_svgs(g: dict) -> tuple[str, str]:
    """(animated SVG, final-state SVG): the letters slide out from behind the D's rounded right edge.

    The letters are clipped to "everything right of the hole, except the D's own silhouette", so they
    are hidden by the D (never seen through the pip) and appear exactly where its curve ends.
    The D is drawn after the letters so a 1.5-unit overlap hides the anti-aliasing seam.
    """
    import math

    word_w = g["right"] - g["text_x"]
    w, h = int(g["width"]), int(g["height"])
    left, bottom = g["d_left"], g["d_bottom"]
    cx, cy, radius = left + 100, bottom - 132, 132.0     # centre and radius of the D's round bowl
    x_c = left + 175                                      # right of the pip's hole (which ends at left + 166)
    r_clip = radius - 1.5
    half = math.sqrt(r_clip**2 - (x_c - cx) ** 2)
    clip_d = (f"M{x_c:.2f} 0H{w}V{h}H{x_c:.2f}Z "
              f"M{x_c:.2f} {cy - half:.2f}A{r_clip} {r_clip} 0 0 1 {x_c:.2f} {cy + half:.2f}Z")
    slide = (g["text_x"] + word_w) - x_c + 24             # starts fully hidden left of the clip
    lead = g["width"] / 2 - (left + 116)                  # the D starts centred, then glides to its place
    d = f'<path d="{D_PATH}" fill="{AMBER}" fill-rule="evenodd" transform="translate({left - 140:.2f} {bottom - 388:.2f})"/>'
    word = f'<path d="{g["word"]}" fill="{CREAM}"/>'
    css = (
        f".d{{transform-box:fill-box;transform-origin:50% 50%;animation:dIn {D_IN_MS}ms {EASE} both}}"
        f"@keyframes dIn{{from{{opacity:0;transform:scale(.88)}}to{{opacity:1;transform:none}}}}"
        f".lead{{animation:lead {WORD_MS}ms {EASE} {WORD_DELAY_MS}ms both}}"
        f"@keyframes lead{{from{{transform:translateX({lead:.1f}px)}}to{{transform:none}}}}"
        f".slide{{animation:slide {WORD_MS}ms {EASE} {WORD_DELAY_MS}ms both}}"
        f"@keyframes slide{{from{{transform:translateX({-slide:.1f}px)}}to{{transform:none}}}}"
        f".word{{animation:fade {WORD_FADE_MS}ms linear {WORD_DELAY_MS}ms both}}"
        f"@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}"
        f"@media (prefers-reduced-motion:reduce){{.d,.lead,.slide,.word{{animation:none}}}}"
    )
    nl = chr(10)
    animated = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="Dubzar">'
        f"<style>{css}</style>"
        f'<defs><clipPath id="c"><path d="{clip_d}" clip-rule="evenodd"/></clipPath></defs>'
        f'<g class="lead"><g clip-path="url(#c)"><g class="slide"><g class="word">{word}</g></g></g>'
        f'<g class="d">{d}</g></g></svg>{nl}'
    )
    return animated, svg(w, h, word + d)

def tight_logo(g: dict) -> str:
    """The final lockup cropped to its own bounds (no margins), for use inside the app."""
    left, top = g["d_left"], g["margin"]
    box = f"{left:.1f} {top:.1f} {g['right'] - left:.1f} {D_H:.1f}"
    body = f'<path d="{g["word"]}" fill="{CREAM}"/>' + d_markup(g)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" role="img" aria-label="Dubzar">{body}</svg>'
            + chr(10))


def write_ico(badge_svg: Path, target: Path) -> None:
    """Windows icon with PNG-compressed entries (supported since Vista) at every standard size."""
    renderer = QSvgRenderer(str(badge_svg))
    pngs = []
    for size in ICON_SIZES:
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        pngs.append((size, bytes(data)))
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, blobs = b"", b""
    for size, png in pngs:
        side = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        blobs += png
    target.write_bytes(header + entries + blobs)


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
    # integrated wordmarks: a D drawn to the serif's own measurements, then "ubzar" in Instrument Serif Italic
    size = 204
    font = QFont("Instrument Serif")
    font.setItalic(True)
    font.setPixelSize(size)

    def box(ch: str):
        q = QPainterPath()
        q.addText(0, 0, font, ch)
        return q, q.boundingRect()

    _, d_box = box("D")
    _, b_box = box("b")
    x_height = -box("x")[1].top()
    cap = -d_box.top()                                   # the font's real capital height
    stem_path, _ = box("l")
    band = QPainterPath()
    band.addRect(-500, -x_height * 0.45, 1000, 3)
    serif_stem = stem_path.intersected(band).boundingRect().width()  # thick stem of the letters, ~14 px

    baseline = -b_box.top() + 40                          # 40 px of room above the tallest letter
    left, gap = 40.0, 12.0
    height = int(baseline + 40)

    def finish(name: str, d_markup: str, d_width: float) -> None:
        rest, right = wordmark_path("ubzar", size, left + d_width + gap, baseline)
        body = d_markup + f'<path d="{rest}" fill="{CREAM}"/>'
        (OUT / name).write_text(svg(int(right + 40), height, body), encoding="utf-8")

    # A: the solid D-pip, scaled so its height is the capital height and its width is the font's own D
    k = cap / 264
    finish("dubzar-wordmark-solid.svg",
           mark(AMBER, f"translate({left - 140 * k:.2f} {baseline - 388 * k:.2f}) scale({k:.4f})"), 232 * k)

    # B: a light D (strokes ~1.7x the serif stem) with a solid pip inside, so it sits in the same weight family
    h, w, s = cap, cap * 0.84, serif_stem * 1.7
    r = h / 2
    top, x0 = baseline - h, left
    outer = f"M{x0:.2f} {top:.2f}H{x0 + w - r:.2f}A{r:.2f} {r:.2f} 0 0 1 {x0 + w - r:.2f} {baseline:.2f}H{x0:.2f}Z"
    ri = r - s
    inner = (f"M{x0 + s:.2f} {top + s:.2f}H{x0 + w - r:.2f}A{ri:.2f} {ri:.2f} 0 0 1 {x0 + w - r:.2f} "
             f"{baseline - s:.2f}H{x0 + s:.2f}Z")
    pip_r = h * 0.15
    cx = x0 + s + (w - 2 * s) * 0.56
    cy = top + h / 2
    d_line = (f'<path d="{outer}{inner}" fill="{AMBER}" fill-rule="evenodd"/>'
              f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{pip_r:.2f}" fill="{AMBER}"/>')
    finish("dubzar-wordmark-line.svg", d_line, w)
    g = reveal_geometry("baseline")
    animated, final = reveal_svgs(g)
    (OUT / "dubzar-reveal.svg").write_text(animated, encoding="utf-8")
    (OUT / "dubzar-reveal-final.svg").write_text(final, encoding="utf-8")
    UI_DIR.joinpath("dubzar-logo.svg").write_text(tight_logo(g), encoding="utf-8")
    UI_DIR.joinpath("dubzar-mark.svg").write_text((OUT / "dubzar-mark.svg").read_text(encoding="utf-8"), encoding="utf-8")
    write_ico(OUT / "dubzar-badge.svg", UI_DIR / "dubzar.ico")
    print("written:", *sorted(p.name for p in OUT.glob("dubzar-*.svg")))


if __name__ == "__main__":
    main()
