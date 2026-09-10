"""Build the application icons from assets/logo.png.

    python packaging/make_icon.py

Writes, next to this file:

    app_icon.ico    Windows: taskbar, Explorer, the installer wizard, the icon
                    PyInstaller stamps into the .exe -- and the window icon Qt
                    draws in the title bar. Qt reads every frame out of it and
                    picks the right one per use, which is why there is no
                    separate PNG: a single large PNG would be scaled down to
                    16px with the wordmark still in it.
    app_icon.icns   macOS: Dock and Finder. Built with iconutil, so this one
                    only appears when run on macOS.

Kept as a script rather than checked-in binaries nobody can regenerate: when
the logo changes, this is the one command that brings every icon along with it.
The build workflow runs it before PyInstaller, so the icons are never stale.

Three things the source artwork cannot do on its own:

  * It is a stacked lockup -- the mark above the EMOTIV wordmark -- at roughly
    4:3. An icon is square, and below about 128px the wordmark is a grey smudge
    that only muddies the silhouette.
  * Even the mark alone is wide: the head and the speech board side by side
    measure 872x573, so fitting it in a square wastes a third of the height. At
    48px and below that costs more than the speech board is worth, so the small
    sizes carry the head alone -- measured at 489x573, which very nearly fills
    a square.
  * macOS and Windows want different shapes. Windows icons run to the edge of
    their square; a macOS icon is a rounded rectangle occupying 824 of 1024
    points, and drawing it full-bleed makes the app loom over its neighbours in
    the Dock.
  * At 16px the line art washes out. Downscaling a 489px drawing to 13px of
    artwork puts most strokes between samples, and the result is mid-grey where
    it should be near-black. So the 16px frame -- and only that one -- is
    drawn from artwork whose ink has been thickened first, by one source pixel per
    output pixel. Measured against the plain version: at 16px it is the
    difference between a smudge and a readable head; at 24px the same
    treatment merges the strokes and makes it worse, which is why the threshold
    is where it is.
"""

import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
SOURCE = os.path.join(ROOT, "assets", "logo.png")

# Crop boxes into the source, all measured from it rather than eyeballed:
# connected-component analysis of the artwork's ink, printed by the analysis in
# this file's history. The source is 1254x1254.
LOCKUP = (192, 254, 1082, 1031)   # mark + EMOTIV wordmark
MARK = (203, 254, 1075, 827)      # head + speech board, no wordmark
TIGHT = (203, 254, 692, 827)      # the head alone: the largest ink component

# The artwork is dark ink on a near-white ground, so the plate stays light --
# on a dark plate the head outline would disappear. The exact background colour
# is sampled from the source in load(), so the pasted crop has no visible seam
# against it.

# Windows sizes. 24 and 64 are not optional: Explorer's list views ask for them
# and scales a neighbour badly when they are missing.
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

# The macOS iconset, as iconutil expects it: (filename, pixel size).
ICNS_SIZES = [
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
]

# macOS Human Interface Guidelines: the rounded rectangle is 824pt in a 1024pt
# canvas, with a corner radius of 185.4pt. Expressed as fractions so they hold
# at every size.
MAC_INSET = (1024 - 824) / 2 / 1024
MAC_RADIUS = 185.4 / 824
WIN_RADIUS = 0.18

# Below this size the line art is thickened before the downscale. See the
# module docstring for the measurement behind the threshold.
BOLD_AT_OR_BELOW = 16


def load():
    """The source artwork, and the plate colour sampled from its own ground."""
    art = Image.open(SOURCE)
    plate = art.convert("RGB").getpixel((5, 5)) + (255,)
    return art.convert("RGBA"), plate


def art_for(source: Image.Image, size: int) -> Image.Image:
    """The crop that still reads at this size."""
    box = LOCKUP if size >= 256 else MARK if size >= 128 else TIGHT
    return source.crop(box)


def render(source: Image.Image, plate: tuple, size: int, mac: bool) -> Image.Image:
    inset = round(size * MAC_INSET) if mac else 0
    plate_size = size - 2 * inset
    radius = max(2, round(plate_size * (MAC_RADIUS if mac else WIN_RADIUS)))

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).rounded_rectangle(
        [inset, inset, size - 1 - inset, size - 1 - inset],
        radius=radius, fill=plate)

    # The lockup needs more air around it than the bare mark does.
    padding = 0.82 if size >= 256 else 0.80
    art = art_for(source, size)
    if size <= BOLD_AT_OR_BELOW:
        # Dark ink on a light ground: the minimum over a neighbourhood grows the
    # dark strokes.
        kernel = max(3, (art.width // size) | 1)
        art = art.filter(ImageFilter.MinFilter(kernel))
    art.thumbnail((round(plate_size * padding), round(plate_size * padding)),
                  Image.LANCZOS)
    canvas.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    return canvas


def write_ico(source, plate) -> None:
    target = os.path.join(HERE, "app_icon.ico")
    frames = [render(source, plate, s, mac=False) for s in ICO_SIZES]
    frames[-1].save(target, format="ICO",
                    sizes=[(f.width, f.height) for f in frames],
                    append_images=frames[:-1])
    print(f"wrote {target} ({', '.join(str(s) for s in ICO_SIZES)})")


def write_icns(source, plate) -> None:
    """macOS only: iconutil ships with Xcode's command line tools."""
    if sys.platform != "darwin":
        print("not macOS — skipping app_icon.icns")
        return
    if not shutil.which("iconutil"):
        print("iconutil not found — skipping app_icon.icns", file=sys.stderr)
        return

    iconset = os.path.join(HERE, "app_icon.iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset)
    for name, size in ICNS_SIZES:
        render(source, plate, size, mac=True).save(os.path.join(iconset, name))

    target = os.path.join(HERE, "app_icon.icns")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", target], check=True)
    shutil.rmtree(iconset, ignore_errors=True)
    print(f"wrote {target}")


def main() -> int:
    if not os.path.exists(SOURCE):
        print(f"missing {SOURCE}", file=sys.stderr)
        return 1
    source, plate = load()
    write_ico(source, plate)
    write_icns(source, plate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
