"""Building exteriors for the revamped Riven Town.  Every sprite is native art (16 px per tile), bottom anchored on its
footprint, with the doorway centred on the sprite so the 'D' tile in worldmap.py lines up with the painted door.

    python tools/town_buildings.py            # writes assets/town/bld_*.png (+ a preview sheet when asked)
"""
import os

from PIL import ImageFont

from pix import *

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(HERE, "..", "assets", "fonts", "PressStart2P-Regular.ttf")
OUT = rgb("#241c2a")


# ------------------------------------------------------------------------------------------------ primitives
def text(im, s, cx, y, color, size=8, shadow=None):
    """Render `s` centred on cx using the game's pixel font at its native 8 px grid."""
    f = ImageFont.truetype(FONT_PATH, size)
    mask = Image.new("L", im.size, 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(mask)
    d.fontmode = "1"
    wtxt = d.textlength(s, font=f)
    x = int(cx - wtxt / 2)
    d.text((x, y), s, font=f, fill=255)
    px = mask.load()
    ip = im.load()
    for yy in range(im.height):
        for xx in range(im.width):
            if px[xx, yy] > 127:
                if shadow and 0 <= xx + 1 < im.width and 0 <= yy + 1 < im.height and px[min(xx + 1, im.width - 1), yy] < 128:
                    pass
                ip[xx, yy] = color
    if shadow:
        sh = Image.new("L", im.size, 0)
        sd = ImageDraw.Draw(sh)
        sd.fontmode = "1"
        sd.text((x + 1, y + 1), s, font=f, fill=255)
        sp = sh.load()
        for yy in range(im.height):
            for xx in range(im.width):
                if sp[xx, yy] > 127 and px[xx, yy] <= 127:
                    ip[xx, yy] = shadow


def plaster(p, x, y, w, h, base, seed="pl", speck=0.05):
    r = rng("plaster", seed)
    p.rect(x, y, w, h, base)
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if r.random() < speck:
                p.dot(xx, yy, shade(base, r.choice([0.93, 1.06])))
    p.vline(x, y, h, shade(base, 1.08))
    p.vline(x + w - 1, y, h, shade(base, 0.86))


def siding(p, x, y, w, h, base, step=3):
    p.rect(x, y, w, h, base)
    for yy in range(y, y + h, step):
        p.hline(x, yy, w, shade(base, 1.08))
        p.hline(x, yy + step - 1, w, shade(base, 0.86))
    p.vline(x, y, h, shade(base, 1.08))
    p.vline(x + w - 1, y, h, shade(base, 0.82))


def brick(p, x, y, w, h, base, mortar=None, seed="br"):
    r = rng("brick", seed)
    mortar = mortar or shade(base, 0.72)
    p.rect(x, y, w, h, mortar)
    for ri, yy in enumerate(range(y, y + h, 4)):
        off = 0 if ri % 2 == 0 else 4
        xx = x - off
        while xx < x + w:
            bw = 7
            c = shade(base, r.choice([0.94, 1.0, 1.05, 0.9]))
            x0, x1 = max(x, xx), min(x + w, xx + bw)
            if x1 > x0:
                p.rect(x0, yy, x1 - x0, min(3, y + h - yy), c)
                p.hline(x0, yy, x1 - x0, shade(c, 1.12))
            xx += 8


def stone(p, x, y, w, h, base, seed="st"):
    r = rng("stone", seed)
    p.rect(x, y, w, h, shade(base, 0.8))
    for ri, yy in enumerate(range(y, y + h, 5)):
        xx = x - (ri % 2) * 5
        while xx < x + w:
            bw = r.choice([8, 10, 12])
            c = shade(base, r.choice([0.95, 1.0, 1.06]))
            x0, x1 = max(x, xx + 1), min(x + w, xx + bw)
            if x1 > x0:
                p.rect(x0, yy + 1, x1 - x0, min(4, y + h - yy - 1), c)
                p.hline(x0, yy + 1, x1 - x0, shade(c, 1.15))
            xx += bw


def hip_roof(p, x, y, w, h, base, inset=8, seed="rf", style="shingle"):
    """3/4-view hip roof: a trapezoid, wide at the eaves.  Light from the upper left."""
    r = rng("roof", seed)
    for i in range(h):
        k = (h - 1 - i) / max(1, h - 1)
        off = int(round(inset * k))
        x0, x1 = x + off, x + w - off
        row_c = shade(base, 1.0 + 0.1 * (1 - k) - 0.0)
        p.hline(x0, y + i, x1 - x0, row_c)
        course = i % 4
        if course == 0:
            p.hline(x0, y + i, x1 - x0, shade(base, 1.18))
        elif course == 3:
            p.hline(x0, y + i, x1 - x0, shade(base, 0.8))
        else:
            step = 5
            sx = x0 + ((i // 4) % 2) * 2
            for xx in range(sx, x1, step):
                p.dot(xx, y + i, shade(base, 0.86))
        p.dot(x0, y + i, shade(base, 1.2))
        p.dot(x1 - 1, y + i, shade(base, 0.7))
    # eave shadow and ridge
    p.hline(x, y + h - 1, w, shade(base, 0.6))
    p.hline(x + inset, y, w - inset * 2, shade(base, 1.3))
    p.hline(x + inset, y + 1, w - inset * 2, shade(base, 1.12))


def flat_parapet(p, x, y, w, h, base):
    p.rect(x, y, w, h, base)
    p.hline(x, y, w, shade(base, 1.2))
    p.hline(x, y + h - 1, w, shade(base, 0.7))
    for xx in range(x + 3, x + w - 2, 6):
        p.vline(xx, y + 1, h - 2, shade(base, 0.9))


def solar(p, x, y, w, h, tilt=True):
    p.rect(x, y, w, h, rgb("#274a8a"))
    p.frame(x, y, w, h, rgb("#cfd8e6"))
    for xx in range(x + 3, x + w - 1, 3):
        p.vline(xx, y + 1, h - 2, rgb("#3a66b4"))
    for yy in range(y + 3, y + h - 1, 3):
        p.hline(x + 1, yy, w - 2, rgb("#3a66b4"))
    p.hline(x + 1, y + 1, min(4, w - 2), rgb("#7aa6e8"))
    p.dot(x + 1, y + 2, rgb("#7aa6e8"))


def window(p, x, y, w, h, frame=rgb("#f3ead2"), glass_t=rgb("#a9d8f2"), glass_b=rgb("#6aa8d6"), lit=False, mullion=True,
           arch=False, sill=True, shutters=None, box=None):
    if shutters:
        sw = max(2, w // 3)
        p.rect(x - sw - 1, y, sw, h, shutters)
        p.rect(x + w + 1, y, sw, h, shutters)
        for yy in range(y + 1, y + h, 3):
            p.hline(x - sw - 1, yy, sw, shade(shutters, 0.8))
            p.hline(x + w + 1, yy, sw, shade(shutters, 0.8))
    p.rect(x - 1, y - 1, w + 2, h + 2, frame)
    for yy in range(h):
        t = yy / max(1, h - 1)
        c = mix(glass_t, glass_b, t) if not lit else mix(rgb("#ffe9a0"), rgb("#f2b84a"), t)
        p.hline(x, y + yy, w, c)
    if arch:
        p.dot(x, y, frame)
        p.dot(x + w - 1, y, frame)
        p.dot(x - 1, y - 1, (0, 0, 0, 0))
    if mullion and w >= 5:
        p.vline(x + w // 2, y, h, frame)
    if mullion and h >= 8:
        p.hline(x, y + h // 2, w, frame)
    if not lit:
        p.dot(x + 1, y + 1, rgb("#ffffff"))
        p.dot(x + 2, y + 1, rgb("#e8f6ff"))
        p.dot(x + 1, y + 2, rgb("#e8f6ff"))
    if sill:
        p.rect(x - 2, y + h + 1, w + 4, 2, shade(frame, 0.82))
        p.hline(x - 2, y + h + 1, w + 4, shade(frame, 1.05))
    if box:
        p.rect(x - 1, y + h + 2, w + 2, 3, rgb("#7a5230"))
        p.hline(x - 1, y + h + 2, w + 2, rgb("#a87848"))
        for i, xx in enumerate(range(x, x + w, 2)):
            p.dot(xx, y + h + 1, box[i % len(box)])
            p.dot(xx, y + h, rgb("#3f9a46"))


def door(p, x, y, w, h, color=rgb("#8a5a3a"), glass=False, arch=False, knob=True, trim=rgb("#f3ead2")):
    p.rect(x - 1, y - 1, w + 2, h + 1, trim)
    p.rect(x, y, w, h, color)
    p.hline(x, y, w, shade(color, 1.2))
    p.vline(x + w // 2, y + 1, h - 1, shade(color, 0.78))
    if glass:
        for gx in (x + 1, x + w // 2 + 1):
            gw = w // 2 - 2
            for yy in range(h - 4):
                p.hline(gx, y + 1 + yy, gw, mix(rgb("#bfe9ff"), rgb("#6aa8d6"), yy / max(1, h - 5)))
            p.dot(gx, y + 1, rgb("#ffffff"))
    else:
        p.rect(x + 1, y + 2, max(1, w // 2 - 2), max(2, h // 2 - 2), shade(color, 1.15))
        p.rect(x + w // 2 + 1, y + 2, max(1, w // 2 - 2), max(2, h // 2 - 2), shade(color, 1.15))
        p.rect(x + 1, y + h // 2 + 1, max(1, w // 2 - 2), max(1, h // 2 - 3), shade(color, 0.92))
        p.rect(x + w // 2 + 1, y + h // 2 + 1, max(1, w // 2 - 2), max(1, h // 2 - 3), shade(color, 0.92))
    if knob:
        p.dot(x + w // 2 - 1, y + h * 2 // 3, rgb("#f0d070"))
        p.dot(x + w // 2 + 1, y + h * 2 // 3, rgb("#f0d070"))


def awning(p, x, y, w, h, a, b, scallop=True):
    sw = 3
    for i, xx in enumerate(range(x, x + w, sw)):
        c = a if i % 2 == 0 else b
        p.rect(xx, y, min(sw, x + w - xx), h, c)
        p.hline(xx, y + h - 1, min(sw, x + w - xx), shade(c, 0.78))
        if scallop:
            p.hline(xx, y + h, min(sw, x + w - xx), c)
            p.dot(xx + 1, y + h + 1, shade(c, 0.9))
    p.hline(x, y, w, shade(a, 1.2))


def steps(p, x, y, w, n=2, base=rgb("#cbbd9f")):
    for i in range(n):
        p.rect(x - i * 2, y + i * 2, w + i * 4, 2, shade(base, 1.0 - 0.08 * i))
        p.hline(x - i * 2, y + i * 2, w + i * 4, shade(base, 1.15))
        p.hline(x - i * 2, y + i * 2 + 1, w + i * 4, shade(base, 0.8))


def plinth(p, x, y, w, base=rgb("#a89a7c")):
    p.rect(x, y, w, 4, base)
    p.hline(x, y, w, shade(base, 1.2))
    for xx in range(x + 3, x + w, 7):
        p.vline(xx, y + 1, 3, shade(base, 0.8))


def chimney(p, x, y, h=10, base=rgb("#a85a42")):
    p.rect(x, y, 6, h, base)
    p.rect(x - 1, y, 8, 2, shade(base, 1.25))
    p.vline(x + 5, y + 2, h - 2, shade(base, 0.75))
    for yy in range(y + 3, y + h, 3):
        p.hline(x, yy, 6, shade(base, 0.85))


def finish(im, name, outdir, keep_outline=True):
    im = outline(im, OUT) if keep_outline else im
    im.save(os.path.join(outdir, name + ".png"))
    return im


# ------------------------------------------------------------------------------------------------ houses (3 wide)
def house(variant):
    W, H = 48, 72
    im = new(W, H)
    p = Pen(im)
    wall, roof, trim, accent, shut = [
        (rgb("#e9dfc4"), rgb("#5c7896"), rgb("#fbf5e2"), rgb("#4a86c9"), rgb("#4c7a8a")),      # player: cream + slate, solar
        (rgb("#d6e0c4"), rgb("#b9603f"), rgb("#fbf5e2"), rgb("#e07a4a"), rgb("#8a6a3a")),      # Toma: sage + terracotta
        (rgb("#f1e3b0"), rgb("#3f8f94"), rgb("#fbf5e2"), rgb("#3f9a98"), rgb("#c9784a")),      # Reya: butter + teal
    ][variant]
    # body
    plaster(p, 3, 36, 42, 32, wall, ("house", variant))
    p.hline(3, 36, 42, shade(wall, 0.8))
    plinth(p, 3, 64, 42)
    # corner quoins
    for yy in range(38, 64, 6):
        p.rect(3, yy, 3, 3, trim)
        p.rect(42, yy, 3, 3, trim)
    # roof
    hip_roof(p, 0, 12, 48, 26, roof, inset=10, seed=("house", variant))
    if variant == 0:      # solar array on the roof faces
        solar(p, 8, 16, 11, 8)
        solar(p, 21, 16, 11, 8)
        p.hline(8, 25, 24, shade(roof, 0.7))
    else:
        # dormer window
        p.rect(18, 17, 12, 11, shade(roof, 1.1))
        p.rect(19, 19, 10, 9, wall)
        window(p, 21, 21, 6, 5, frame=trim, sill=False)
        hip_roof(p, 17, 12, 14, 7, shade(roof, 0.9), inset=5, seed=("dormer", variant))
    # chimney
    chimney(p, 36 if variant != 1 else 9, 6, 14, shade(rgb("#b4604a"), 1.0))
    # windows
    window(p, 8, 43, 8, 10, frame=trim, shutters=shut, box=[rgb("#e8584c"), rgb("#ffd24a"), rgb("#f08cb0")])
    window(p, 32, 43, 8, 10, frame=trim, shutters=shut, box=[rgb("#ffd24a"), rgb("#e8584c"), rgb("#b78cf0")])
    # porch + door (door centred on x=24)
    p.rect(18, 55, 12, 13, trim)
    door(p, 20, 52, 8, 16, color=accent if variant != 1 else rgb("#8a5a3a"))
    p.rect(17, 49, 14, 3, shade(roof, 1.0))
    p.hline(17, 49, 14, shade(roof, 1.25))
    p.hline(17, 51, 14, shade(roof, 0.65))
    steps(p, 19, 68, 10, n=2)
    # wall lantern
    p.rect(33, 52, 2, 3, rgb("#ffe27a"))
    p.dot(33, 51, IRON_)
    return finish(im, f"bld_house_{variant}", OUTDIR)


IRON_ = rgb("#3b4752")
OUTDIR = os.path.join(HERE, "..", "assets", "town")


# ------------------------------------------------------------------------------------------------ shared big-building bits
def glass_panel(p, x, y, w, h, top=rgb("#bfe9ff"), bot=rgb("#5fa3cf"), rib=rgb("#f4f6f4"), cols=0, rows=0, streak=True):
    for yy in range(h):
        p.hline(x, y + yy, w, mix(top, bot, yy / max(1, h - 1)))
    if streak:
        for k in range(0, h, 1):
            xx = x + 2 + k
            if xx < x + w - 1:
                p.dot(xx, y + h - 1 - k, shade(top, 1.15))
                if xx + 1 < x + w - 1:
                    p.dot(xx + 1, y + h - 1 - k, shade(top, 1.08))
    p.frame(x, y, w, h, rib)
    if cols:
        for i in range(1, cols):
            p.vline(x + i * w // cols, y, h, rib)
    if rows:
        for i in range(1, rows):
            p.hline(x, y + i * h // rows, w, rib)


def arch_window(p, x, y, w, h, frame, glass_t=rgb("#a9d8f2"), glass_b=rgb("#6aa8d6")):
    """Round-headed window: frame, glass and a keystone; (x, y) = top-left of the glass."""
    r = w // 2
    for yy in range(h):
        t = yy / max(1, h - 1)
        c = mix(glass_t, glass_b, t)
        if yy < r:
            d = r - yy
            inset = max(0, int(round(r - (r * r - d * d) ** 0.5))) if d <= r else r
        else:
            inset = 0
        p.hline(x + inset, y + yy, w - inset * 2, c)
        p.dot(x + inset - 1, y + yy, frame)
        p.dot(x + w - inset, y + yy, frame)
    p.hline(x + r - 1, y - 1, 2, frame)
    p.hline(x + 2, y, w - 4, frame) if r > 3 else None
    p.rect(x - 1, y + r, 1, h - r + 1, frame)
    p.rect(x + w, y + r, 1, h - r + 1, frame)
    p.hline(x - 1, y + h, w + 2, frame)
    p.vline(x + r, y + 1, h - 1, frame)
    p.hline(x, y + h // 2 + 1, w, frame)
    p.dot(x + 1, y + h - 2, rgb("#ffffff"))
    p.rect(x - 2, y + h + 1, w + 4, 2, shade(frame, 0.8))


def column(p, x, y, h, w=4, base=rgb("#f4ecd6")):
    p.rect(x, y, w, h, base)
    p.vline(x, y, h, shade(base, 1.06))
    p.vline(x + w - 1, y, h, shade(base, 0.78))
    p.vline(x + w - 2, y, h, shade(base, 0.9))
    p.rect(x - 1, y, w + 2, 2, shade(base, 1.05))
    p.rect(x - 1, y + h - 2, w + 2, 2, shade(base, 0.88))


def gear(p, cx, cy, r, c, hole=rgb("#2a2a33")):
    for ang in range(0, 360, 45):
        import math
        a = math.radians(ang)
        tx, ty = int(round(cx + math.cos(a) * (r + 1))), int(round(cy + math.sin(a) * (r + 1)))
        p.rect(tx - 1, ty - 1, 3, 3, c)
    p.ellipse(cx - r + 1, cy - r + 1, (r - 1) * 2 + 1, (r - 1) * 2 + 1, c)
    p.ellipse(cx - 1, cy - 1, 3, 3, hole)
    p.dot(cx - r + 2, cy - 1, shade(c, 1.3))


def vine(p, x, y, h, seed="v"):
    r = rng("vine", seed)
    for k in range(h):
        p.dot(x + (1 if (k // 3) % 2 else 0), y + k, rgb("#2f7a3a"))
        if r.random() < 0.5:
            p.dot(x + r.choice([-2, -1, 2, 3]), y + k, rgb("#4aa243"))


# ------------------------------------------------------------------------------------------------ Astrion Research Lab
def lab():
    W, H = 80, 96
    im = new(W, H)
    p = Pen(im)
    wall, wall_d = rgb("#e4eceb"), rgb("#bcd0d0")
    teal, teal_d, teal_l = rgb("#3f9a98"), rgb("#2c6e70"), rgb("#6ac4c0")
    # wings (low) -----------------------------------------------------------------------------
    for wx in (2, 58):
        plaster(p, wx, 56, 20, 36, wall, ("lab", wx), speck=0.03)
        p.rect(wx - 1, 50, 22, 7, teal)
        p.hline(wx - 1, 50, 22, teal_l)
        p.hline(wx - 1, 56, 22, teal_d)
        solar(p, wx + 1, 40, 18, 10)
        p.line(wx + 4, 49, wx + 4, 50, IRON_)
        glass_panel(p, wx + 3, 62, 14, 16, cols=2, rows=2)
        p.rect(wx + 2, 78, 16, 2, shade(wall, 0.85))
    # central block --------------------------------------------------------------------------
    plaster(p, 20, 44, 40, 48, wall, "labc", speck=0.03)
    p.rect(18, 40, 44, 6, teal)
    p.hline(18, 40, 44, teal_l)
    p.hline(18, 45, 44, teal_d)
    for xx in range(22, 60, 8):
        p.rect(xx, 42, 3, 2, teal_d)
    # dome base ring
    p.rect(24, 34, 32, 6, rgb("#cfdcdc"))
    p.hline(24, 34, 32, rgb("#f4fafa"))
    p.hline(24, 39, 32, rgb("#8aa4a6"))
    # glass dome (half ellipse with lattice)
    cx, cy, rx, ry = 40, 36, 15, 20
    for yy in range(0, ry):
        t = yy / ry
        half = int(round(rx * (1 - (1 - t) ** 2) ** 0.5))
        col = mix(rgb("#d9fbff"), rgb("#4aa7c9"), t)
        p.hline(cx - half, cy - ry + yy, half * 2 + 1, col)
        p.dot(cx - half, cy - ry + yy, rgb("#f4fafa"))
        p.dot(cx + half, cy - ry + yy, rgb("#f4fafa"))
    for k in (-9, -4, 0, 4, 9):                # meridians
        for yy in range(0, ry, 1):
            t = yy / ry
            half = rx * (1 - (1 - t) ** 2) ** 0.5
            xx = int(round(cx + k * half / rx))
            p.dot(xx, cy - ry + yy, rgb("#eef6f6"))
    for yy in (6, 12):                         # parallels
        t = yy / ry
        half = int(round(rx * (1 - (1 - t) ** 2) ** 0.5))
        p.hline(cx - half, cy - ry + yy, half * 2 + 1, rgb("#eef6f6"))
    for x, y, c in ((33, 24, "#7ef2a0"), (36, 27, "#4ad28a"), (45, 26, "#7ef2a0"), (41, 29, "#9ff7ff")):   # glow inside
        p.rect(x, y, 2, 2, rgb(c))
    p.dot(34, 18, rgb("#ffffff"))
    p.dot(35, 17, rgb("#ffffff"))
    # mast + dish
    p.vline(40, 0, 16, IRON_)
    p.vline(39, 4, 12, rgb("#9aa8b0"))
    p.rect(39, 0, 3, 2, rgb("#ff5252"))
    p.rect(40, 0, 1, 1, rgb("#ffd0d0"))
    p.hline(38, 10, 5, IRON_)
    p.rect(60, 32, 8, 3, rgb("#cfdcdc"))        # dish
    p.rect(62, 28, 5, 4, rgb("#f4fafa"))
    p.dot(64, 27, rgb("#f4fafa"))
    p.vline(64, 35, 5, IRON_)
    # facade: sign band, windows, door --------------------------------------------------------
    p.rect(26, 50, 28, 11, rgb("#1f3b44"))
    p.frame(26, 50, 28, 11, teal_l)
    text(im, "LAB", 40, 52, rgb("#8ff6ff"), 8, shadow=rgb("#0c1e24"))
    glass_panel(p, 23, 64, 10, 20, cols=2, rows=3)
    glass_panel(p, 47, 64, 10, 20, cols=2, rows=3)
    p.rect(34, 70, 12, 22, rgb("#dfeaea"))
    door(p, 35, 72, 10, 18, color=teal, glass=True, trim=rgb("#f4fafa"))
    p.rect(32, 66, 16, 4, teal)
    p.hline(32, 66, 16, teal_l)
    p.hline(32, 69, 16, teal_d)
    # glowing conduit light strip along the plinth
    p.rect(2, 90, 76, 2, rgb("#8aa4a6"))
    for xx in range(4, 76, 8):
        p.rect(xx, 91, 4, 1, rgb("#7ef2ff"))
    # planters
    p.rect(22, 86, 8, 5, rgb("#7a5230"))
    p.rect(50, 86, 8, 5, rgb("#7a5230"))
    for xx in (23, 25, 27, 29, 51, 53, 55, 57):
        p.dot(xx, 85, rgb("#4aa243"))
        p.dot(xx, 84, rgb("#8ff6ff") if xx % 4 == 1 else rgb("#ffd6ff"))
    p.rect(30, 92, 20, 2, rgb("#cbbd9f"))
    p.rect(28, 94, 24, 2, rgb("#b0a284"))
    return finish(im, "bld_lab", OUTDIR)


# ------------------------------------------------------------------------------------------------ Town Hall
def hall():
    W, H = 80, 96
    im = new(W, H)
    p = Pen(im)
    wall, trim = rgb("#efe3c4"), rgb("#fbf5e2")
    brick_red, roof = rgb("#b5593e"), rgb("#9d4a38")
    copper, copper_d = rgb("#5fb39a"), rgb("#3d8470")
    # wings -----------------------------------------------------------------------------------
    plaster(p, 3, 58, 74, 34, wall, "hall", speck=0.04)
    for xx in range(3, 78, 3):                     # brick-red quoin stripes at the edges
        pass
    for yy in range(60, 90, 6):
        p.rect(3, yy, 4, 3, brick_red)
        p.rect(73, yy, 4, 3, brick_red)
    # roofs: wings hip + central tower block
    hip_roof(p, 0, 38, 80, 22, roof, inset=12, seed="hallroof")
    # clock tower -----------------------------------------------------------------------------
    plaster(p, 29, 14, 22, 30, wall, "tower", speck=0.03)
    p.rect(27, 12, 26, 3, trim)
    p.hline(27, 12, 26, rgb("#ffffff"))
    p.hline(27, 14, 26, shade(trim, 0.8))
    # spire
    for i in range(14):
        half = 1 + int(i * 12 / 14)
        p.hline(40 - half, 12 - 14 + i + 1, half * 2, shade(copper, 1.0 + 0.1 * (i < 4)))
        p.dot(40 - half, 12 - 14 + i + 1, shade(copper, 1.25))
        p.dot(40 + half - 1, 12 - 14 + i + 1, copper_d)
    p.vline(40, 0, 6, IRON_)
    p.rect(40, 0, 5, 3, rgb("#d1552f"))
    # clock face
    p.ellipse(33, 19, 14, 14, rgb("#3c2e24"))
    p.ellipse(34, 20, 12, 12, rgb("#fff8e6"))
    for (dx, dy) in ((0, -4), (0, 4), (-4, 0), (4, 0)):
        p.dot(40 + dx, 26 + dy, rgb("#3c2e24"))
    p.vline(40, 22, 5, rgb("#2a2a33"))
    p.line(40, 26, 43, 28, rgb("#2a2a33"))
    p.dot(40, 26, rgb("#d1552f"))
    # belfry slits
    p.rect(31, 36, 3, 6, rgb("#3c2e24"))
    p.rect(46, 36, 3, 6, rgb("#3c2e24"))
    # portico with columns + pediment ---------------------------------------------------------
    for i in range(9):                                   # triangular pediment
        half = int(2 + i * 16 / 8)
        p.hline(40 - half, 40 + i, half * 2, trim)
        p.dot(40 - half, 40 + i, rgb("#ffffff"))
        p.dot(40 + half - 1, 40 + i, shade(trim, 0.8))
    p.ellipse(37, 44, 6, 5, rgb("#c97a5a"))
    p.ellipse(38, 45, 4, 3, rgb("#e8b890"))
    p.rect(21, 49, 38, 11, trim)                         # frieze with the carved name
    p.hline(21, 49, 38, rgb("#ffffff"))
    p.hline(21, 59, 38, shade(trim, 0.78))
    p.rect(23, 50, 34, 9, rgb("#3c5a34"))
    text(im, "HALL", 40, 51, rgb("#f3efd6"), 8)
    for xx in (23, 30, 47, 54):
        column(p, xx, 60, 28)
    p.rect(21, 86, 38, 3, shade(trim, 0.85))
    p.hline(21, 86, 38, trim)
    # doors and windows
    door(p, 35, 70, 10, 18, color=rgb("#6e4a2a"), trim=trim)
    p.dot(40, 71, rgb("#f0d070"))
    for wx in (9, 17, 56, 64):
        arch_window(p, wx, 64, 7, 16, trim)
    # flag pole on the right wing
    p.vline(70, 36, 10, IRON_)
    p.rect(70, 36, 5, 3, rgb("#d1552f"))
    steps(p, 30, 88, 20, n=3)
    p.rect(4, 88, 18, 4, rgb("#a89a7c"))
    p.rect(58, 88, 18, 4, rgb("#a89a7c"))
    for xx in (8, 12, 62, 66):
        p.rect(xx, 84, 3, 4, rgb("#3f9a46"))
        p.dot(xx + 1, 83, rgb("#ffd24a"))
    return finish(im, "bld_hall", OUTDIR)


# ------------------------------------------------------------------------------------------------ Library
def library():
    W, H = 80, 96
    im = new(W, H)
    p = Pen(im)
    sand, sand_d = rgb("#dccaa0"), rgb("#bda878")
    slate = rgb("#4a5f8e")
    trim = rgb("#f4ead0")
    stone(p, 3, 54, 74, 38, sand, "lib")
    hip_roof(p, 0, 28, 80, 28, slate, inset=12, seed="libroof")
    # raised centre gable
    stone(p, 24, 28, 32, 28, sand, "libgab")
    for i in range(16):
        half = 3 + int(i * 15 / 15)
        p.hline(40 - half, 14 + i, half * 2, shade(slate, 1.0))
        p.dot(40 - half, 14 + i, shade(slate, 1.3))
        p.dot(40 + half - 1, 14 + i, shade(slate, 0.7))
    p.hline(22, 30, 36, shade(slate, 0.6))
    p.rect(21, 28, 38, 3, trim)
    p.hline(21, 28, 38, rgb("#ffffff"))
    p.rect(39, 6, 2, 9, IRON_)
    # rose window with a book
    p.ellipse(33, 32, 14, 14, trim)
    p.ellipse(34, 33, 12, 12, rgb("#6a86c9"))
    p.ellipse(35, 34, 10, 10, rgb("#a9c4f0"))
    p.vline(40, 34, 10, trim)
    p.hline(35, 39, 10, trim)
    p.rect(37, 36, 3, 5, rgb("#d9402f"))
    p.rect(41, 36, 3, 5, rgb("#f2cf4a"))
    # lintel with name carved
    p.rect(8, 58, 64, 10, shade(sand, 1.06))
    p.hline(8, 58, 64, rgb("#efe5cd"))
    p.hline(8, 67, 64, sand_d)
    text(im, "LIBRARY", 40, 59, rgb("#3a4a78"), 8)
    # tall arched windows
    for wx in (9, 20, 54, 65):
        arch_window(p, wx, 71, 7, 14, trim)
    # door
    p.rect(33, 72, 14, 18, trim)
    door(p, 34, 73, 12, 17, color=rgb("#4a3a68"), trim=trim)
    p.rect(34, 70, 12, 3, rgb("#6a86c9"))
    p.hline(34, 70, 12, rgb("#a9c4f0"))
    p.rect(30, 72, 3, 18, rgb("#e6dcc0"))
    p.rect(47, 72, 3, 18, rgb("#e6dcc0"))
    # banners
    for bx in (27, 51):
        p.rect(bx, 72, 3, 9, rgb("#d1552f"))
        p.dot(bx + 1, 81, rgb("#d1552f"))
        p.rect(bx + 1, 74, 1, 3, rgb("#f6e6a0"))
    # ivy on the left wall
    vine(p, 5, 58, 28, "ivyL")
    vine(p, 6, 66, 20, "ivyL2")
    p.rect(2, 88, 76, 4, rgb("#9c8e6c"))
    p.hline(2, 88, 76, rgb("#c9bd9c"))
    steps(p, 33, 90, 14, n=2)
    # hedge planters
    for hx in (6, 62):
        p.rect(hx, 86, 14, 6, rgb("#2f7a3a"))
        p.hline(hx, 85, 14, rgb("#4aa243"))
        for xx in range(hx + 1, hx + 13, 4):
            p.dot(xx, 86, rgb("#ffd6e4"))
    return finish(im, "bld_library", OUTDIR)


# ------------------------------------------------------------------------------------------------ Supply Mart
def mart():
    W, H = 80, 96
    im = new(W, H)
    p = Pen(im)
    cream, brickc = rgb("#f3e2bd"), rgb("#c0603a")
    # body + parapet
    plaster(p, 3, 36, 74, 56, cream, "mart", speck=0.04)
    brick(p, 3, 36, 74, 12, brickc, seed="martbr")
    flat_parapet(p, 1, 30, 78, 8, rgb("#9c4a30"))
    # rooftop sign box
    p.rect(19, 10, 42, 22, rgb("#2e3b44"))
    p.frame(19, 10, 42, 22, rgb("#f2cf4a"))
    p.rect(21, 12, 38, 18, rgb("#1f2b33"))
    for xx in range(23, 58, 6):
        p.dot(xx, 12, rgb("#f2cf4a"))
        p.dot(xx, 29, rgb("#f2cf4a"))
    text(im, "MART", 40, 17, rgb("#ffe27a"), 8, shadow=rgb("#7a3a1a"))
    p.rect(31, 6, 2, 5, IRON_)
    p.rect(47, 6, 2, 5, IRON_)
    # roof clutter: solar + AC
    solar(p, 6, 22, 11, 8)
    solar(p, 63, 22, 11, 8)
    p.rect(30, 25, 0, 0, IRON_)
    # big awning
    awning(p, 3, 52, 74, 7, rgb("#d9402f"), rgb("#f7ecd2"))
    # display windows
    for wx in (7, 49):
        glass_panel(p, wx, 64, 24, 20, rows=2, cols=3)
        for gx, gc in ((wx + 3, "#e8584c"), (wx + 9, "#f2cf4a"), (wx + 15, "#6fc254"), (wx + 4, "#4a86c9"), (wx + 11, "#b78cf0"), (wx + 17, "#f08a3a")):
            gy = 68 if gx % 2 else 76
            p.rect(gx, gy + 4 if gx < wx + 8 else gy + 2, 4, 5, rgb(gc))
        p.rect(wx - 1, 84, 26, 3, rgb("#8a5a3a"))
        p.hline(wx - 1, 84, 26, rgb("#c18c52"))
    # door
    p.rect(32, 64, 16, 28, rgb("#f7ecd2"))
    door(p, 33, 66, 14, 24, color=rgb("#3f9a98"), glass=True, trim=rgb("#f7ecd2"))
    p.rect(35, 60, 10, 4, rgb("#2e3b44"))
    p.rect(36, 61, 8, 2, rgb("#ffe27a"))
    p.rect(41, 62, 0, 0, rgb("#ffe27a"))
    # base
    p.rect(2, 90, 76, 4, rgb("#9c8e6c"))
    p.hline(2, 90, 76, rgb("#c9bd9c"))
    steps(p, 33, 92, 14, n=2)
    return finish(im, "bld_mart", OUTDIR)


# ------------------------------------------------------------------------------------------------ Cush's Repair Nook
def cush():
    W, H = 80, 68
    im = new(W, H)
    p = Pen(im)
    wall, red = rgb("#f0d8c4"), rgb("#d1552f")
    plaster(p, 3, 22, 74, 42, wall, "cush", speck=0.05)
    siding(p, 3, 22, 74, 6, rgb("#e8c4a8"))
    # sawtooth workshop roof
    for x0 in (0, 27, 54):
        w = 26
        p.rect(x0, 10, w, 13, red)
        for i in range(0, 13, 2):
            p.hline(x0, 10 + i, w, shade(red, 1.2 if (i // 2) % 2 == 0 else 0.92))
        p.hline(x0, 10, w, shade(red, 1.45))
        p.hline(x0, 22, w, shade(red, 0.6))
        p.rect(x0, 3, w, 7, rgb("#c9d4dc"))
        p.hline(x0, 3, w, rgb("#eef4f8"))
        for xx in range(x0 + 4, x0 + w, 5):
            p.vline(xx, 4, 6, rgb("#8a9aa6"))
    # exhaust stack
    p.rect(68, 0, 5, 12, rgb("#6a7480"))
    p.rect(68, 0, 1, 12, rgb("#9aa4ae"))
    p.hline(67, 0, 7, rgb("#9aa4ae"))
    # name plate
    p.rect(23, 25, 34, 11, rgb("#f7e6d6"))
    p.frame(23, 25, 34, 11, rgb("#8a4a30"))
    text(im, "CUSH", 40, 27, rgb("#8a2f18"), 8)
    gear(p, 29, 46, 4, red)
    gear(p, 51, 46, 4, red)
    # workshop bay with bench
    p.rect(5, 34, 16, 24, rgb("#3a2e36"))
    for yy in range(34, 48, 3):
        p.hline(5, yy, 16, rgb("#6a5a68"))
    p.rect(6, 48, 14, 10, rgb("#52424a"))
    p.rect(6, 48, 14, 2, rgb("#a87848"))
    p.rect(8, 44, 4, 4, rgb("#9aa4ae"))
    p.rect(14, 40, 5, 8, rgb("#e0b040"))
    p.rect(15, 41, 3, 2, rgb("#7ef2ff"))
    p.rect(4, 32, 18, 3, rgb("#c9d4dc"))
    # tool board
    p.rect(59, 34, 16, 18, rgb("#8a6a44"))
    p.frame(59, 34, 16, 18, rgb("#563620"))
    for tx, tc in ((61, "#c9d4dc"), (65, "#e0453c"), (69, "#f2cf4a")):
        p.rect(tx, 37, 2, 10, rgb(tc))
        p.rect(tx - 1, 36, 4, 2, rgb("#2a2a33"))
    # door on the doorway tile
    p.rect(34, 42, 12, 22, rgb("#f7e6d6"))
    door(p, 35, 45, 10, 19, color=rgb("#e05a72"), trim=rgb("#f7e6d6"))
    p.rect(33, 40, 14, 3, red)
    p.hline(33, 40, 14, shade(red, 1.3))
    # tyres
    for ty in (52, 56):
        p.ellipse(60, ty, 12, 7, rgb("#2a2a33"))
        p.ellipse(63, ty + 2, 6, 3, rgb("#6a6a78"))
    p.rect(2, 62, 76, 3, rgb("#9c8e6c"))
    p.hline(2, 62, 76, rgb("#c9bd9c"))
    steps(p, 35, 64, 10, n=2)
    return finish(im, "bld_cush", OUTDIR)


# ------------------------------------------------------------------------------------------------ Greenhouses
def _plants_inside(p, x, y, w, h, seed, fruit=True):
    r = rng("inside", seed)
    p.rect(x, y, w, h, rgb("#2b5a3a"))
    for _ in range(int(w * h / 14)):
        xx, yy = x + r.randrange(w), y + r.randrange(h)
        p.rect(xx, yy, 3, 2, r.choice([rgb("#3f9a46"), rgb("#58b85a"), rgb("#2f7a3a"), rgb("#6fc254")]))
    if fruit:
        for _ in range(int(w * h / 60)):
            p.dot(x + r.randrange(w), y + r.randrange(h), r.choice([rgb("#e0453c"), rgb("#f2cf4a"), rgb("#e8861e")]))


def greenhouse_a():
    W, H = 80, 96
    im = new(W, H)
    p = Pen(im)
    rib, rib_d = rgb("#f4f6f4"), rgb("#aab4ae")
    # foundation + frame
    p.rect(3, 70, 74, 22, rgb("#cbbd9f"))
    brick(p, 3, 76, 74, 16, rgb("#b0644a"), seed="gha")
    # glass body with plants inside
    _plants_inside(p, 5, 44, 70, 28, "ghA")
    glass_panel(p, 3, 42, 74, 30, cols=7, rows=1, top=rgb("#d6f4ff"), bot=rgb("#8cc8e0"))
    # roof: gabled glass, lit from left
    for i in range(30):
        k = i / 29
        inset = int(round(30 * (1 - k)))
        x0, x1 = 3 + inset, 77 - inset
        for xx in range(x0, x1):
            t = i / 29
            c = mix(rgb("#e6fbff"), rgb("#8cc8e0"), 1 - t * 0.6)
            p.dot(xx, 12 + i, c)
        p.dot(x0, 12 + i, rib)
        p.dot(x1 - 1, 12 + i, rib_d)
    for xx in range(14, 70, 8):                      # rafters
        for i in range(30):
            k = i / 29
            inset = int(round(30 * (1 - k)))
            if 3 + inset < xx < 77 - inset:
                p.dot(xx, 12 + i, rib)
    p.hline(30, 12, 20, rib)
    p.rect(33, 6, 14, 6, rib)
    p.frame(33, 6, 14, 6, rib_d)
    p.hline(34, 8, 12, rgb("#8cc8e0"))
    # sign + door
    p.rect(18, 52, 44, 11, rgb("#2e6a3a"))
    p.frame(18, 52, 44, 11, rgb("#f2cf4a"))
    text(im, "FARMS", 40, 54, rgb("#f3efd6"), 8, shadow=rgb("#16301c"))
    p.rect(33, 66, 14, 24, rib)
    door(p, 34, 68, 12, 22, color=rgb("#5fae55"), glass=True, trim=rib)
    # crates of produce
    for cx, ccol in ((6, "#e0453c"), (19, "#f2cf4a"), (51, "#6fc254"), (64, "#e8861e")):
        p.rect(cx, 80, 12, 10, rgb("#a87848"))
        p.frame(cx, 80, 12, 10, rgb("#563620"))
        for k in range(3):
            p.rect(cx + 1 + k * 4, 77, 3, 4, rgb(ccol))
            p.dot(cx + 2 + k * 4, 77, shade(rgb(ccol), 1.3))
    p.rect(2, 90, 76, 3, rgb("#9c8e6c"))
    steps(p, 34, 92, 12, n=2)
    return finish(im, "bld_farm_a", OUTDIR)


def greenhouse_b():
    W, H = 80, 96
    im = new(W, H)
    p = Pen(im)
    rib, rib_d = rgb("#f4f6f4"), rgb("#aab4ae")
    teal = rgb("#3f9a98")
    p.rect(3, 72, 74, 20, rgb("#c3cfc8"))
    siding(p, 3, 78, 74, 14, rgb("#e8eee8"))
    _plants_inside(p, 5, 40, 70, 34, "ghB")
    # misting pipes
    p.hline(5, 48, 70, rgb("#9aa8b0"))
    for xx in range(9, 74, 8):
        p.dot(xx, 49, rgb("#bfe9ff"))
        p.dot(xx - 1, 51, rgb("#bfe9ff"))
        p.dot(xx + 1, 52, rgb("#e8faff"))
    glass_panel(p, 3, 38, 74, 36, cols=8, rows=2, top=rgb("#d9f4ff"), bot=rgb("#8cc8e0"))
    # barrel-vault roof (rounded)
    for i in range(24):
        t = i / 23
        inset = int(round(14 * (1 - (1 - (1 - t)) ** 0.5))) if False else int(round(16 * (1 - t) ** 2))
        x0, x1 = 3 + inset, 77 - inset
        for xx in range(x0, x1):
            c = mix(rgb("#e8fbff"), rgb("#8cc8e0"), 0.15 + 0.55 * (1 - t))
            p.dot(xx, 14 + i, c)
        p.dot(x0, 14 + i, rib)
        p.dot(x1 - 1, 14 + i, rib_d)
    for xx in range(11, 72, 8):
        for i in range(24):
            t = i / 23
            inset = int(round(16 * (1 - t) ** 2))
            if 3 + inset <= xx < 77 - inset:
                p.dot(xx, 14 + i, rib)
    p.hline(19, 14, 42, rib)
    # roof vents (open)
    for vx in (14, 54):
        p.rect(vx, 8, 12, 6, rib)
        p.rect(vx + 1, 9, 10, 4, rgb("#8cc8e0"))
        p.line(vx + 1, 13, vx + 6, 9, rib)
    # wind turbine on the right end + water tank
    p.vline(70, 0, 16, IRON_)
    p.line(70, 4, 66, 0, rgb("#e6ecef"))
    p.line(70, 4, 74, 1, rgb("#e6ecef"))
    p.line(70, 4, 70, 9, rgb("#e6ecef"))
    p.dot(70, 4, rgb("#d1552f"))
    p.rect(60, 62, 14, 22, rgb("#6a8aa0"))
    p.rect(60, 62, 14, 3, rgb("#a9c0d0"))
    p.vline(61, 62, 22, rgb("#a9c0d0"))
    p.hline(60, 70, 14, rgb("#4e6a7e"))
    p.hline(60, 78, 14, rgb("#4e6a7e"))
    # sign + door
    p.rect(5, 54, 36, 11, rgb("#2e6a3a"))
    p.frame(5, 54, 36, 11, rgb("#f2cf4a"))
    text(im, "GROW", 23, 56, rgb("#f3efd6"), 8)
    p.rect(33, 66, 14, 24, rib)
    door(p, 34, 68, 12, 22, color=teal, glass=True, trim=rib)
    # hanging baskets
    for bx in (10, 26):
        p.vline(bx + 3, 66, 4, IRON_)
        p.rect(bx, 70, 7, 4, rgb("#7a5230"))
        for k in range(0, 7, 2):
            p.dot(bx + k, 69, rgb("#4aa243"))
            p.dot(bx + k + 1, 68, rgb("#f08cb0") if k % 4 == 0 else rgb("#f2cf4a"))
    p.rect(2, 90, 76, 3, rgb("#9c8e6c"))
    steps(p, 34, 92, 12, n=2)
    return finish(im, "bld_farm_b", OUTDIR)


def build_all():
    os.makedirs(OUTDIR, exist_ok=True)
    for v in range(3):
        house(v)
    lab(); hall(); library(); mart(); cush(); greenhouse_a(); greenhouse_b()


if __name__ == "__main__":
    build_all()
    print("buildings done")
