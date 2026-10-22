"""Tiny pixel-art helpers shared by the town / building generators (native 16 px-per-tile art, PIL based)."""
import random
from PIL import Image, ImageDraw


def rgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def new(w, h, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (w, h), fill)


class Pen:
    """Draw on an RGBA image with integer pixel coordinates (inclusive-exclusive rects)."""

    def __init__(self, im):
        self.im = im
        self.d = ImageDraw.Draw(im)
        self.px = im.load()

    def dot(self, x, y, c):
        if 0 <= x < self.im.width and 0 <= y < self.im.height:
            self.px[x, y] = c if len(c) == 4 else c + (255,)

    def rect(self, x, y, w, h, c):
        if w <= 0 or h <= 0:
            return
        self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=c if len(c) == 4 else c + (255,))

    def frame(self, x, y, w, h, c):
        self.d.rectangle([x, y, x + w - 1, y + h - 1], outline=c if len(c) == 4 else c + (255,))

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        self.d.line([x0, y0, x1, y1], fill=c if len(c) == 4 else c + (255,))

    def ellipse(self, x, y, w, h, c):
        self.d.ellipse([x, y, x + w - 1, y + h - 1], fill=c if len(c) == 4 else c + (255,))

    def paste(self, spr, x, y):
        self.im.alpha_composite(spr, (x, y))

    def get(self, x, y):
        return self.px[x, y]


def shade(c, k):
    """Multiply the rgb of colour c by k (k<1 darker, k>1 lighter)."""
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + ((c[3],) if len(c) == 4 else (255,))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def outline(im, color=(32, 26, 36, 255), inner=False):
    """1 px outline around the opaque pixels of a sprite (returns a new, 2 px larger sprite)."""
    w, h = im.size
    out = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    src = im.load()
    dst = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] > 0:
                dst[x + 1, y + 1] = src[x, y]
    base = out.copy().load()
    for y in range(h + 2):
        for x in range(w + 2):
            if base[x, y][3] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w + 2 and 0 <= ny < h + 2 and base[nx, ny][3] > 0:
                        dst[x, y] = color
                        break
    return out


def rng(*seed):
    """Deterministic RNG from any hashable-ish seed parts (zlib.crc32, so the art is identical on every run)."""
    import zlib
    return random.Random(zlib.crc32("|".join(str(p) for p in seed).encode()))
