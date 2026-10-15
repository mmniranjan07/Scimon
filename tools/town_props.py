"""Outdoor props for the revamped town: trees, lamp posts, benches, fences, hedges, signs, market stall, scarecrow...

All sprites are native 16 px-per-tile art, bottom anchored.  Dark outline colour keeps them readable on grass.
"""
from pix import *

OUTLINE = rgb("#1f2a22")
WOOD = rgb("#a87848")
WOOD_L = rgb("#c9955c")
WOOD_D = rgb("#7a5230")
WOOD_DD = rgb("#563620")
IRON = rgb("#3b4752")
IRON_L = rgb("#5d6c78")
CREAM = rgb("#f1e6c8")
CREAM_D = rgb("#cdbf9c")


def shadow_ellipse(im, cx, cy, rx, ry, a=70):
    """Soft ground shadow (drawn first, under the sprite)."""
    sh = new(im.width, im.height)
    d = Pen(sh)
    d.ellipse(cx - rx, cy - ry, rx * 2, ry * 2, (10, 25, 15, a))
    sh.alpha_composite(im)
    return sh


# ------------------------------------------------------------------------------------------------ trees
def _blob(p, cx, cy, r, c):
    p.ellipse(cx - r, cy - r, r * 2 + 1, r * 2 + 1, c)


def _canopy(w, h, blobs, dark, mid, light, hi, seed, spots=None):
    im = new(w, h)
    p = Pen(im)
    for cx, cy, r in blobs:
        _blob(p, cx, cy, r, dark)
    for cx, cy, r in blobs:
        _blob(p, cx - 1, cy - 2, max(1, r - 2), mid)
    for cx, cy, r in blobs:
        _blob(p, cx - 2, cy - 4, max(1, r - 5), light)
    r_ = rng("leaf", seed)
    # leaf speckle: lighter clusters on top, darker nicks beneath
    for _ in range(60):
        x, y = r_.randrange(w), r_.randrange(h)
        c = im.getpixel((x, y))
        if c[3] == 0:
            continue
        if y < h * 0.45:
            if r_.random() < 0.5:
                p.dot(x, y, hi)
        elif r_.random() < 0.5:
            p.dot(x, y, shade(dark, 0.85))
    if spots:
        for x, y, c in spots:
            p.dot(x, y, c)
    return im


def tree_oak(v=0):
    dark, mid, light, hi = rgb("#245f31"), rgb("#2f7a3a"), rgb("#43963f"), rgb("#6fc254")
    if v == 1:
        dark, mid, light, hi = rgb("#2a6a35"), rgb("#3a8a3c"), rgb("#58a845"), rgb("#86d05a")
    if v == 2:
        dark, mid, light, hi = rgb("#1f5a3a"), rgb("#2b7447"), rgb("#3f9059"), rgb("#6cc384")
    W, H = 36, 46
    im = new(W, H)
    p = Pen(im)
    # trunk + roots
    p.rect(15, 28, 6, 15, WOOD_D)
    p.rect(16, 28, 3, 15, WOOD)
    p.dot(15, 43, WOOD_DD)
    p.rect(13, 41, 3, 2, WOOD_D)
    p.rect(20, 41, 3, 2, WOOD_D)
    p.hline(14, 43, 8, WOOD_DD)
    p.vline(17, 30, 9, WOOD_L)
    blobs = [(18, 14, 11), (9, 20, 8), (27, 20, 8), (18, 8, 8), (14, 24, 6), (23, 24, 6)]
    can = _canopy(W, H, blobs, dark, mid, light, hi, ("oak", v))
    im.alpha_composite(can)
    im = outline(im, OUTLINE)
    return shadow_ellipse(im, im.width // 2, im.height - 4, 11, 3, 60)


def tree_pine(v=0):
    W, H = 30, 48
    im = new(W, H)
    p = Pen(im)
    p.rect(13, 38, 4, 8, WOOD_D)
    p.rect(14, 38, 2, 8, WOOD)
    tiers = [(15, 2, 5), (15, 9, 8), (15, 17, 10), (15, 26, 12), (15, 34, 13)]
    dark, mid, light = rgb("#1c4f33"), rgb("#2a6b43"), rgb("#3f8a55")
    for cx, top, half in tiers:
        for i in range(0, 9):
            y = top + i
            hw = int(half * (i + 1) / 9)
            p.hline(cx - hw, y, hw * 2 + 1, mid)
            p.hline(cx - hw, y, max(1, hw // 2 + 1), light)
            p.dot(cx + hw, y, dark)
            p.dot(cx + hw - 1, y, dark)
        p.hline(cx - half, top + 9, half * 2 + 1, dark)
    r = rng("pine", v)
    for _ in range(40):
        x, y = r.randrange(W), r.randrange(8, 44)
        if p.get(x, y)[3] and p.get(x, y)[:3] == mid[:3]:
            p.dot(x, y, shade(mid, 1.18))
    im = outline(im, OUTLINE)
    return shadow_ellipse(im, im.width // 2, im.height - 4, 10, 3, 60)


def tree_blossom(v=0):
    dark, mid, light, hi = rgb("#c4547e"), rgb("#e07aa0"), rgb("#f2a3c0"), rgb("#ffd6e4")
    if v == 1:
        dark, mid, light, hi = rgb("#8e66c8"), rgb("#aa84e0"), rgb("#c6a8f2"), rgb("#e8dcff")
    W, H = 34, 44
    im = new(W, H)
    p = Pen(im)
    p.rect(14, 27, 6, 15, WOOD_D)
    p.rect(15, 27, 3, 15, WOOD)
    p.rect(12, 40, 3, 2, WOOD_D)
    p.rect(19, 40, 3, 2, WOOD_D)
    blobs = [(17, 14, 10), (9, 19, 7), (25, 19, 7), (17, 8, 7), (13, 22, 6), (22, 22, 6)]
    can = _canopy(W, H, blobs, dark, mid, light, hi, ("blossom", v))
    im.alpha_composite(can)
    im = outline(im, rgb("#4a2238") if v == 0 else rgb("#32224a"))
    return shadow_ellipse(im, im.width // 2, im.height - 4, 10, 3, 60)


def tree_glow():
    """Riven's bioluminescent flora, kept from the original look but redrawn to match the new style."""
    W, H = 28, 46
    im = new(W, H)
    p = Pen(im)
    p.rect(11, 18, 6, 26, rgb("#0d2b30"))
    p.rect(13, 18, 2, 26, rgb("#31e8ff"))
    p.rect(11, 42, 2, 2, rgb("#0d2b30"))
    p.rect(15, 42, 2, 2, rgb("#0d2b30"))
    blobs = [(14, 10, 8), (7, 14, 6), (21, 14, 6)]
    can = _canopy(W, H, blobs, rgb("#5a3a9a"), rgb("#8f5fe0"), rgb("#b98bff"), rgb("#e6d1ff"), "glow")
    im.alpha_composite(can)
    im = outline(im, rgb("#1a1030"))
    return shadow_ellipse(im, im.width // 2, im.height - 4, 9, 3, 60)


def bush(v=0):
    W, H = 20, 16
    im = new(W, H)
    p = Pen(im)
    cols = [(rgb("#245f31"), rgb("#3a8a3c"), rgb("#6fc254")), (rgb("#2a6a35"), rgb("#4a9a44"), rgb("#86d05a"))][v % 2]
    for cx, cy, r in ((6, 9, 5), (12, 8, 6), (10, 5, 4)):
        _blob(p, cx, cy, r, cols[0])
    for cx, cy, r in ((6, 8, 3), (12, 7, 4), (10, 4, 2)):
        _blob(p, cx, cy, r, cols[1])
    for x, y in ((5, 6), (11, 5), (14, 7), (9, 3)):
        p.dot(x, y, cols[2])
    im = outline(im, OUTLINE)
    return im


def rock_small(v=0):
    im = new(16, 12)
    p = Pen(im)
    p.ellipse(2, 3, 12, 8, rgb("#7d8590"))
    p.ellipse(3, 3, 9, 6, rgb("#a3abb4"))
    p.dot(5, 4, rgb("#d1d7de"))
    p.dot(6, 4, rgb("#d1d7de"))
    p.hline(3, 9, 9, rgb("#5f6670"))
    return outline(im, OUTLINE)


# ------------------------------------------------------------------------------------------------ lamps, benches, signs
def lamp_post():
    W, H = 14, 40
    im = new(W, H)
    p = Pen(im)
    p.rect(6, 12, 2, 26, IRON)
    p.vline(6, 12, 26, IRON_L)
    p.rect(4, 36, 6, 3, IRON)
    p.rect(5, 34, 4, 2, IRON_L)
    p.rect(3, 9, 8, 3, IRON)
    p.hline(3, 9, 8, IRON_L)
    # lantern housing
    p.rect(3, 2, 8, 8, rgb("#fff1b0"))
    p.rect(4, 3, 6, 6, rgb("#ffe27a"))
    p.rect(5, 4, 3, 2, rgb("#fffbe0"))
    p.vline(3, 2, 8, IRON)
    p.vline(10, 2, 8, IRON)
    p.vline(6, 2, 8, IRON)
    p.vline(7, 2, 8, IRON)
    p.rect(3, 2, 8, 1, IRON)
    p.rect(2, 1, 10, 2, IRON_L)
    p.rect(5, 0, 4, 1, IRON)
    im = outline(im, rgb("#1c2128"))
    return im


def bench(v=0):
    W, H = 28, 18
    im = new(W, H)
    p = Pen(im)
    wood, wood_l, wood_d = (WOOD, WOOD_L, WOOD_D) if v == 0 else (rgb("#8c6a58"), rgb("#ab8670"), rgb("#654a3c"))
    # legs
    p.rect(3, 10, 3, 6, IRON)
    p.rect(22, 10, 3, 6, IRON)
    # back rest
    for i, y in enumerate((1, 4)):
        p.rect(1, y, 26, 2, wood)
        p.hline(1, y, 26, wood_l)
        p.hline(1, y + 1, 26, wood_d)
    p.rect(2, 1, 2, 9, wood_d)
    p.rect(24, 1, 2, 9, wood_d)
    # seat
    p.rect(0, 8, 28, 4, wood)
    p.hline(0, 8, 28, wood_l)
    p.hline(0, 11, 28, wood_d)
    p.vline(14, 8, 4, wood_d)
    im = outline(im, OUTLINE)
    return im


def planter(kind=0):
    W, H = 18, 18
    im = new(W, H)
    p = Pen(im)
    pal = [("#e8584c", "#ffd24a"), ("#f08cb0", "#fff0f6"), ("#b78cf0", "#ffe27a"), ("#fff4d6", "#f2a33a")][kind % 4]
    # box
    p.rect(1, 9, 16, 8, WOOD)
    p.rect(1, 9, 16, 2, WOOD_L)
    p.hline(1, 16, 16, WOOD_D)
    p.vline(5, 11, 5, WOOD_D)
    p.vline(12, 11, 5, WOOD_D)
    # foliage + flowers
    for x in range(2, 16, 3):
        p.rect(x, 5, 3, 5, rgb("#2f7a3a"))
        p.dot(x + 1, 4, rgb("#43963f"))
    r = rng("planter", kind)
    for x in range(3, 16, 3):
        y = 3 + r.randrange(3)
        p.dot(x, y, rgb(pal[0]))
        p.dot(x + 1, y, rgb(pal[0]))
        p.dot(x, y + 1, rgb(pal[0]))
        p.dot(x + 1, y - 1, rgb(pal[1]))
    return outline(im, OUTLINE)


def signpost():
    W, H = 22, 30
    im = new(W, H)
    p = Pen(im)
    p.rect(9, 5, 3, 24, WOOD_D)
    p.vline(9, 5, 24, WOOD)
    # arrow boards
    p.rect(2, 4, 15, 6, WOOD_L)
    p.rect(2, 4, 15, 1, rgb("#e3b87a"))
    p.rect(16, 5, 2, 4, WOOD_L)
    p.dot(18, 6, WOOD_L)
    p.hline(2, 9, 15, WOOD_D)
    p.rect(5, 6, 8, 1, WOOD_DD)
    p.rect(5, 8, 5, 1, WOOD_DD)
    p.rect(6, 12, 14, 5, WOOD)
    p.rect(3, 12, 3, 4, WOOD)
    p.hline(6, 16, 14, WOOD_D)
    p.rect(8, 13, 8, 1, WOOD_DD)
    return outline(im, OUTLINE)


def notice_board():
    W, H = 34, 36
    im = new(W, H)
    p = Pen(im)
    p.rect(3, 12, 3, 22, WOOD_D)
    p.rect(28, 12, 3, 22, WOOD_D)
    p.rect(1, 2, 32, 22, WOOD_D)
    p.rect(3, 4, 28, 18, rgb("#d9c79a"))
    p.rect(3, 4, 28, 1, rgb("#efe2bc"))
    # pinned notes
    notes = [(5, 6, 7, 8, "#ffffff"), (14, 7, 6, 7, "#ffe9a8"), (22, 6, 7, 9, "#cfe9ff"), (8, 15, 6, 5, "#ffd1d1")]
    for x, y, w, h, c in notes:
        p.rect(x, y, w, h, rgb(c))
        p.hline(x + 1, y + 2, w - 2, rgb("#8d8d8d"))
        p.hline(x + 1, y + 4, w - 3, rgb("#8d8d8d"))
        p.dot(x + w // 2, y, rgb("#e0453c"))
    p.rect(0, 0, 34, 3, WOOD)
    p.hline(0, 0, 34, WOOD_L)
    p.rect(1, 3, 32, 1, WOOD_DD)
    return outline(im, OUTLINE)


def mailbox():
    W, H = 12, 22
    im = new(W, H)
    p = Pen(im)
    p.rect(5, 9, 2, 12, WOOD_D)
    p.rect(1, 3, 10, 7, rgb("#4a86c9"))
    p.rect(1, 3, 10, 2, rgb("#78acea"))
    p.rect(2, 5, 8, 4, rgb("#3a6fa8"))
    p.rect(8, 0, 2, 5, rgb("#e0453c"))
    p.rect(8, 0, 3, 2, rgb("#e0453c"))
    return outline(im, OUTLINE)


def barrel():
    im = new(14, 16)
    p = Pen(im)
    p.rect(1, 2, 12, 13, rgb("#9a6a3a"))
    p.rect(3, 1, 8, 1, rgb("#c18c52"))
    p.vline(4, 2, 13, rgb("#b8844a"))
    p.vline(9, 2, 13, rgb("#7a5230"))
    p.hline(1, 5, 12, IRON)
    p.hline(1, 11, 12, IRON)
    p.hline(2, 2, 10, rgb("#c18c52"))
    return outline(im, OUTLINE)


def crate_stack():
    im = new(24, 22)
    p = Pen(im)

    def crate(x, y, c):
        p.rect(x, y, 11, 10, c)
        p.frame(x, y, 11, 10, WOOD_DD)
        p.hline(x + 1, y + 1, 9, shade(c, 1.15))
        p.line(x + 1, y + 1, x + 9, y + 8, WOOD_D)
    crate(1, 11, WOOD)
    crate(12, 11, WOOD_L)
    crate(6, 1, rgb("#b9824f"))
    p.rect(4, 3, 3, 3, rgb("#e0453c"))   # a few tomatoes poking out
    p.rect(7, 4, 2, 2, rgb("#e8a52e"))
    return outline(im, OUTLINE)


def hay_bale():
    im = new(22, 16)
    p = Pen(im)
    p.rect(1, 2, 20, 12, rgb("#e0bc4e"))
    p.rect(1, 2, 20, 2, rgb("#f6dc7c"))
    for x in (5, 11, 17):
        p.vline(x, 2, 12, rgb("#9a7a2a"))
    p.hline(1, 13, 20, rgb("#b8923a"))
    for x, y in ((3, 6), (8, 8), (14, 5), (19, 9)):
        p.hline(x, y, 2, rgb("#f6dc7c"))
    return outline(im, OUTLINE)


def market_stall(v=0):
    """48 px wide striped awning stall with a produce counter."""
    W, H = 52, 50
    im = new(W, H)
    p = Pen(im)
    a, b = ((rgb("#e0583a"), rgb("#f6ecd2")) if v == 0 else (rgb("#3f9a98"), rgb("#f6ecd2")))
    # posts
    p.rect(3, 12, 3, 36, WOOD_D)
    p.rect(46, 12, 3, 36, WOOD_D)
    # back panel
    p.rect(6, 12, 40, 22, rgb("#cdb48a"))
    p.hline(6, 12, 40, rgb("#e6d2a6"))
    # awning
    for i in range(0, 52, 4):
        c = a if (i // 4) % 2 == 0 else b
        p.rect(i, 3, 4, 12, c)
        p.rect(i, 15, 4, 3, shade(c, 0.9))
        p.dot(i + 1, 18, shade(c, 0.85))
        p.dot(i + 2, 18, shade(c, 0.85))
    p.hline(0, 3, 52, shade(a, 1.25))
    p.hline(0, 14, 52, shade(a, 0.78))
    # counter
    p.rect(2, 32, 48, 14, WOOD)
    p.rect(2, 32, 48, 2, WOOD_L)
    p.rect(2, 44, 48, 2, WOOD_D)
    for x in (14, 26, 38):
        p.vline(x, 34, 10, WOOD_D)
    # produce on counter
    for x, c in ((6, "#e0453c"), (10, "#e0453c"), (8, "#e8a52e"), (30, "#6fc254"), (34, "#6fc254"), (32, "#8fd870"),
                 (18, "#e8a52e"), (22, "#e8a52e"), (20, "#f2cf4a"), (42, "#b78cf0"), (45, "#b78cf0")):
        p.rect(x, 28, 3, 4, rgb(c))
        p.dot(x + 1, 28, shade(rgb(c), 1.3))
    return outline(im, OUTLINE)


def scarecrow():
    im = new(20, 32)
    p = Pen(im)
    p.rect(9, 8, 2, 22, WOOD_D)
    p.rect(1, 12, 18, 2, WOOD_D)           # arms
    p.rect(5, 12, 10, 10, rgb("#4a86c9"))  # shirt
    p.rect(5, 12, 10, 2, rgb("#78acea"))
    p.rect(7, 22, 6, 6, rgb("#6a5a3a"))
    p.rect(7, 5, 6, 6, rgb("#e0bc8a"))      # head
    p.dot(8, 7, OUTLINE)
    p.dot(11, 7, OUTLINE)
    p.hline(8, 9, 4, OUTLINE)
    p.rect(4, 4, 12, 2, rgb("#c9a14a"))     # hat brim
    p.rect(6, 0, 8, 5, rgb("#b8923a"))
    p.rect(6, 3, 8, 1, rgb("#c13c3c"))
    for x in (0, 17):
        p.rect(x, 11, 3, 3, rgb("#e0bc4e"))  # straw hands
    return outline(im, OUTLINE)


def well():
    im = new(26, 32)
    p = Pen(im)
    p.rect(2, 16, 22, 14, rgb("#bfb39a"))
    p.rect(2, 16, 22, 3, rgb("#e0d6bc"))
    for y in (22, 27):
        p.hline(2, y, 22, rgb("#9c9078"))
    for x in (8, 15, 20):
        p.vline(x, 19, 4, rgb("#9c9078"))
    p.rect(4, 17, 18, 3, rgb("#2f6f9f"))
    p.rect(3, 4, 3, 14, WOOD_D)
    p.rect(20, 4, 3, 14, WOOD_D)
    p.rect(0, 0, 26, 5, rgb("#b04a3a"))
    p.rect(2, 0, 22, 2, rgb("#d86a52"))
    p.hline(0, 4, 26, rgb("#7e2f26"))
    p.vline(13, 5, 8, WOOD_DD)
    p.rect(11, 11, 4, 4, rgb("#7a5230"))
    return outline(im, OUTLINE)


def fountain_jet(frame):
    """Animated spray drawn over the centre of the pond (3 frames)."""
    im = new(24, 30)
    p = Pen(im)
    p.ellipse(2, 20, 20, 8, rgb("#9fd4f0"))
    p.ellipse(4, 22, 16, 5, rgb("#d9f1ff"))
    # basin pedestal
    p.rect(9, 12, 6, 12, rgb("#d9cdb0"))
    p.rect(9, 12, 2, 12, rgb("#efe5cd"))
    p.rect(6, 10, 12, 3, rgb("#cbbd9f"))
    p.hline(6, 10, 12, rgb("#efe5cd"))
    h = (7, 9, 8)[frame % 3]
    p.vline(12, 10 - h, h, rgb("#d9f6ff"))
    p.vline(11, 10 - h + 2, h - 2, rgb("#9fd4f0"))
    for dx, dy in ((-5, 3), (-3, 1), (3, 1), (5, 3), (-4, 6), (4, 6)):
        p.dot(12 + dx, 10 - h + dy + (frame % 2), rgb("#e8faff"))
        p.dot(12 + dx // 2, 10 - h + dy - 1, rgb("#b8e4fa"))
    return im


def reeds(v=0):
    im = new(16, 22)
    p = Pen(im)
    r = rng("reeds", v)
    for x in (2, 5, 8, 11, 13):
        h = r.randrange(10, 20)
        p.vline(x, 22 - h, h, rgb("#4f8f3a"))
        p.vline(x + 1, 22 - h + 2, h - 2, rgb("#6fc254"))
        if r.random() < 0.6:
            p.rect(x, 22 - h - 3, 2, 4, rgb("#7a5230"))
    return im


def lilypads():
    im = new(16, 16)
    p = Pen(im)
    for x, y, f in ((2, 3, 0), (9, 8, 1), (4, 10, 0)):
        p.ellipse(x, y, 6, 4, rgb("#3f9a46"))
        p.ellipse(x + 1, y, 4, 3, rgb("#58b85a"))
        p.dot(x + 5, y + 1, rgb("#3f86bd"))
        if f:
            p.dot(x + 2, y, rgb("#ffd6e4"))
            p.dot(x + 3, y, rgb("#ffffff"))
    return im


def flag(frame):
    """Small pennant for the town hall tower / lab mast (animated, 2 frames)."""
    im = new(14, 10)
    p = Pen(im)
    o = frame % 2
    for x in range(12):
        y = int(1.2 * ((x // 3 + o) % 2))
        p.rect(x, y + (x // 6), 1, 5 - x // 5, rgb("#d1552f"))
    p.rect(0, 0, 2, 6, rgb("#f0e0b8"))
    return im


def build(out_dir):
    import os
    os.makedirs(out_dir, exist_ok=True)

    def save(name, im):
        im.save(os.path.join(out_dir, name + ".png"))
    for v in range(3):
        save(f"tree_oak_{v}", tree_oak(v))
    for v in range(2):
        save(f"tree_pine_{v}", tree_pine(v))
        save(f"tree_blossom_{v}", tree_blossom(v))
        save(f"bush_{v}", bush(v))
        save(f"bench_{v}", bench(v))
        save(f"market_{v}", market_stall(v))
    save("tree_glow", tree_glow())
    save("rock_small", rock_small())
    save("lamp_post", lamp_post())
    for k in range(4):
        save(f"planter_{k}", planter(k))
    save("signpost", signpost())
    save("notice_board", notice_board())
    save("mailbox", mailbox())
    save("barrel", barrel())
    save("crate_stack", crate_stack())
    save("hay_bale", hay_bale())
    save("scarecrow", scarecrow())
    save("well", well())
    for f in range(3):
        save(f"fountain_{f}", fountain_jet(f))
    save("reeds_0", reeds(0))
    save("reeds_1", reeds(1))
    save("lilypads", lilypads())
    for f in range(2):
        save(f"flag_{f}", flag(f))


if __name__ == "__main__":
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else "../assets/town")
