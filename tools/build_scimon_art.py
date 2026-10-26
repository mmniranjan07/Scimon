"""Wild Scimon art for the wider region: one original still per species, generated in the established style
(chunky pixel-art robots, dark outline, type-coloured body + decorations) so `assets/scimon/<id>-front.png`
drops straight into assets.mon_image like the existing art.

Pure Pillow, seeded by species id -- deterministic and safe to re-run.  Part-based composition: a body
archetype (round bot, boxy bot, droplet, bug, crawler, orb) on a coarse art grid, visor + core light, type
decorations, then a 1 px outline pass and a x5 nearest-neighbour scale.

    python3 tools/build_scimon_art.py [id ...]     # all 100 by default; --sheet writes a contact sheet
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pix import Pen, new, outline, rgb, shade  # noqa: E402
from data import SPECIES, WILD_HOME, TYPE_COLORS, CHAIN_OF  # noqa: E402

EVOLUTION_CHAINS = CHAIN_OF  # noqa: E402
from species_expanded import SPECIES_TABLE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "..", "assets", "scimon")
OUTLINE = (40, 36, 44, 255)
SCALE = 5
GW, GH = 50, 42                    # art grid, scaled x5 -> 250x210 like the existing ~256 px stills

# biome-flavoured archetype choices (order biases which bodies a biome's species get)
BIOME_BODIES = {
    "meadow": ("round", "bug", "boxy", "orb"),
    "forest": ("bug", "round", "orb"),
    "water": ("droplet", "orb", "round"),
    "highland": ("round", "orb", "droplet"),
    "volcanic": ("bug", "crawler", "round"),
    "cave": ("crawler", "boxy", "round"),
    "tunnel": ("boxy", "crawler", "round"),
    "city": ("boxy", "orb", "round"),
    "ghost": ("orb", "droplet", "bug"),
    "sea": ("droplet", "orb"),
    "plateau": ("round", "orb", "bug"),
}


def _c(hexstr):
    return rgb(hexstr)


def _ramp(primary, secondary):
    """(base, light, dark, deep, accent) from the species' type colours."""
    base = _c(primary)
    light = shade(base, 1.22)
    dark = shade(base, 0.74)
    deep = shade(base, 0.5)
    accent = _c(secondary) if secondary else shade(base, 1.45)
    return base, light, dark, deep, accent


# --------------------------------------------------------------------------- primitives (art grid units)
def _ell(p, cx, cy, rx, ry, col):
    p.ellipse(cx - rx, cy - ry, rx * 2 + 1, ry * 2 + 1, col)


def _panel(p, x, y, w, h, base, light, dark):
    p.rect(x, y, w, h, base)
    p.hline(x, y, w, light)
    p.vline(x, y, h, light)
    p.hline(x, y + h - 1, w, dark)
    p.vline(x + w - 1, y, h, dark)


def _glow_dot(p, cx, cy, r, col):
    _ell(p, cx, cy, r + 1, r + 1, shade(col, 0.55))
    _ell(p, cx, cy, r, r, col)
    _ell(p, cx - 1, cy - 1, max(1, r - 1), max(1, r - 1), shade(col, 1.5))


# --------------------------------------------------------------------------- bodies (drawn on the grid)
def body_round(p, rng, base, light, dark, deep):
    cx, w, top = 25, 26 + rng.randrange(6), 12 + rng.randrange(3)
    _ell(p, cx, top + 13, w // 2, 13, dark)
    _ell(p, cx, top + 12, w // 2 - 1, 12, base)
    _ell(p, cx - 4, top + 8, w // 3, 6, light)
    p.rect(cx - 2, top + 24, 5, 5, deep)            # hip mounts
    p.rect(cx - 8, top + 24, 5, 5, deep)
    for lx in (cx - 7, cx - 1):
        p.rect(lx, top + 28, 4, 6, dark)
        p.rect(lx - 1, top + 33, 6, 2, deep)
    return top + 34                                  # ground line


def body_boxy(p, rng, base, light, dark, deep):
    x, y, w, h = 15 + rng.randrange(4), 13 + rng.randrange(3), 22 + rng.randrange(6), 15 + rng.randrange(3)
    _panel(p, x, y, w, h, base, light, dark)
    for i in range(2, w - 2, 5):                     # panel seams
        p.vline(x + i, y + 2, h - 4, dark)
    p.rect(x - 2, y + h, w + 4, 5, deep)             # the tread deck
    for tx in range(x - 2, x + w + 2, 4):            # treads
        p.rect(tx, y + h + 3, 3, 4, dark)
    p.rect(x + 2, y + 3, w - 4, 5, deep)             # visor slot backing
    return y + h + 7


def body_droplet(p, rng, base, light, dark, deep):
    cx, top = 25, 8 + rng.randrange(3)
    _ell(p, cx, top + 8, 11, 9, dark)
    _ell(p, cx, top + 7, 10, 8, base)
    _ell(p, cx - 3, top + 4, 4, 3, light)
    for i, w in enumerate((8, 5, 3)):                # taper to a point
        p.rect(cx - w // 2, top + 15 + i * 3, w, 3, base if i < 2 else dark)
    p.rect(cx - 13, top + 8, 3, 6, dark)             # side fins
    p.rect(cx + 11, top + 8, 3, 6, dark)
    return top + 25


def body_bug(p, rng, base, light, dark, deep):
    cx, cy, rx, ry = 25, 22 + rng.randrange(3), 13 + rng.randrange(3), 9 + rng.randrange(2)
    _ell(p, cx, cy, rx, ry, dark)
    _ell(p, cx, cy - 1, rx - 1, ry - 1, base)
    _ell(p, cx - 4, cy - 4, rx // 2, ry // 2, light)
    for i in range(3):                               # three legs a side
        lx = cx - rx + 2 + i * (2 * rx - 4) // 2
        p.rect(lx - 1, cy + ry - 2, 2, 6 + (i % 2) * 2, deep)
    p.rect(cx - 1, cy - ry - 5, 2, 6, dark)          # antennae
    p.rect(cx + 4, cy - ry - 4, 2, 5, dark)
    return cy + ry + 6


def body_crawler(p, rng, base, light, dark, deep):
    x, y, w, h = 11 + rng.randrange(4), 20 + rng.randrange(3), 30 - rng.randrange(4), 11
    _panel(p, x, y, w, h, base, light, dark)
    for i in range(1, w - 1, 6):                     # back plates
        p.rect(x + i, y - 3, 4, 3, dark)
    for lx in (x + 3, x + w // 2 - 2, x + w - 7):    # four stubby legs
        p.rect(lx, y + h, 3, 6, deep)
        p.rect(lx - 1, y + h + 5, 5, 2, dark)
        p.rect(lx + w // 2 - 1, y + h, 3, 6, deep)
        p.rect(lx + w // 2 - 2, y + h + 5, 5, 2, dark)
    return y + h + 7


def body_orb(p, rng, base, light, dark, deep):
    cx, cy, r = 25, 20 + rng.randrange(3), 10 + rng.randrange(3)
    _ell(p, cx, cy, r + 1, r + 1, dark)
    _ell(p, cx, cy, r, r, base)
    _ell(p, cx - 3, cy - 4, r // 2, r // 3, light)
    for i in range(4):                               # orbit bits
        a = i * 90 + rng.randrange(30)
        import math
        ox, oy = cx + int(math.cos(a * math.pi / 180) * (r + 5)), cy + int(math.sin(a * math.pi / 180) * (r + 3))
        p.rect(ox, oy, 3, 3, deep)
    p.rect(cx - 5, cy + r + 2, 3, 3, deep)           # hover fins
    p.rect(cx + 3, cy + r + 2, 3, 3, deep)
    return cy + r + 6


BODIES = {"round": body_round, "boxy": body_boxy, "droplet": body_droplet, "bug": body_bug,
          "crawler": body_crawler, "orb": body_orb}


# --------------------------------------------------------------------------- type decorations
def _leaves(p, rng, cx, top, accent):
    for _ in range(2 + rng.randrange(2)):
        x = cx + rng.randrange(-14, 12)
        y = top + rng.randrange(-2, 4)
        _ell(p, x, y, 4, 2, accent)
        _ell(p, x, y, 2, 1, shade(accent, 1.3))
        p.rect(x + 3, y + 1, 3, 1, shade(accent, 0.6))


def _flames(p, rng, cx, top, accent):
    for _ in range(2 + rng.randrange(2)):
        x = cx + rng.randrange(-10, 9)
        h = 4 + rng.randrange(4)
        p.rect(x, top - h, 3, h, accent)
        p.rect(x, top - h, 2, h - 2, shade(accent, 1.4))
        p.rect(x + 1, top - h - 2, 1, 2, accent)


def _shards(p, rng, cx, top, accent):
    for _ in range(3):
        x = cx + rng.randrange(-12, 11)
        h = 4 + rng.randrange(4)
        y = top + 2 + rng.randrange(3)
        p.rect(x, y - h, 3, h, accent)
        p.vline(x, y - h, h, shade(accent, 1.4))
        p.vline(x + 2, y - h, h, shade(accent, 0.7))


def _plates(p, rng, cx, top, accent):
    for i in range(2 + rng.randrange(2)):
        w = 6 + rng.randrange(4)
        x = cx - 10 + i * 8
        p.rect(x, top - 2 + rng.randrange(3), w, 4, accent)
        p.hline(x, top - 2, w, shade(accent, 1.25))


def _rivets(p, rng, cx, top, base):
    for _ in range(5):
        p.dot(cx - 10 + rng.randrange(20), top + 4 + rng.randrange(10), shade(base, 1.35))


def _antenna(p, rng, cx, top, accent):
    p.rect(cx - 1, top - 9, 2, 9, shade(accent, 0.7))
    p.rect(cx - 2, top - 11, 4, 3, accent)
    if rng.random() < 0.7:
        p.rect(cx + 6, top - 7, 2, 7, shade(accent, 0.7))
        p.rect(cx + 5, top - 9, 4, 3, accent)


def _clouds(p, rng, cx, top, accent):
    for _ in range(2 + rng.randrange(2)):
        x = cx + rng.randrange(-14, 11)
        _ell(p, x, top + 3 + rng.randrange(3), 4, 2, shade(accent, 1.1))
        _ell(p, x + 2, top + 1 + rng.randrange(3), 3, 2, accent)


def _drips(p, rng, cx, top, accent):
    x = cx + rng.randrange(-8, 6)
    p.rect(x, top + 16, 5, 4, shade(accent, 0.8))
    p.rect(x + 1, top + 20, 3, 2, accent)
    for _ in range(2):
        p.rect(x - 3 + rng.randrange(12), top + 24 + rng.randrange(4), 2, 2, accent)


def _wings(p, rng, cx, top, accent):
    p.rect(8, top + 6, 7, 3, shade(accent, 0.85))
    p.rect(35, top + 6, 7, 3, shade(accent, 0.85))
    p.rect(6, top + 9, 5, 2, accent)
    p.rect(39, top + 9, 5, 2, accent)


def _rays(p, rng, cx, top, accent):
    for i in range(-2, 3):
        x = cx + i * 7
        p.rect(x, top - 8 - (3 - abs(i)) * 2, 2, 4 + (3 - abs(i)) * 2, accent)


def _halo(p, rng, cx, cy, accent):
    for i in range(0, 360, 12):
        import math
        x = cx + int(math.cos(i * math.pi / 180) * 19)
        y = cy + int(math.sin(i * math.pi / 180) * 8)
        p.rect(x, y, 2, 2, accent if i % 24 else shade(accent, 1.4))


def _glitches(p, rng, cx, top, accent):
    for _ in range(6):
        x, y = cx - 14 + rng.randrange(28), top + rng.randrange(22)
        p.rect(x, y, 3, 2, accent if rng.random() < 0.5 else shade(accent, 1.4))


def _motes(p, rng, cx, cy, accent):
    for _ in range(7):
        p.rect(cx - 18 + rng.randrange(36), cy - 12 + rng.randrange(26), 2, 2, accent)


def _stars(p, rng, cx, cy, accent):
    for _ in range(6):
        x, y = cx - 20 + rng.randrange(40), cy - 14 + rng.randrange(24)
        p.rect(x, y, 1, 1, shade(accent, 1.6))
        if rng.random() < 0.4:
            p.rect(x - 1, y, 3, 1, shade(accent, 1.2))


def _wisps(p, rng, cx, cy, accent):
    for _ in range(3):
        x = cx + rng.randrange(-16, 14)
        h = 5 + rng.randrange(5)
        y = cy - 8 + rng.randrange(16)
        p.rect(x, y - h, 2, h, shade(accent, 1.1))
        p.rect(x + (2 if rng.random() < 0.5 else -1), y - h - 2, 1, 2, accent)


DECOR = {
    "Botanic": lambda p, r, cx, top, acc, base: _leaves(p, r, cx, top, acc),
    "Bio": lambda p, r, cx, top, acc, base: _leaves(p, r, cx, top, acc) or _drips(p, r, cx, top, acc),
    "Atmospheric": lambda p, r, cx, top, acc, base: _clouds(p, r, cx, top, acc),
    "Chemical": lambda p, r, cx, top, acc, base: _drips(p, r, cx, top, acc),
    "Mechanical": lambda p, r, cx, top, acc, base: _antenna(p, r, cx, top, acc) or _rivets(p, r, cx, top, base),
    "Radiant": lambda p, r, cx, top, acc, base: _rays(p, r, cx, top, acc),
    "Hydro": lambda p, r, cx, top, acc, base: _drips(p, r, cx, top, acc),
    "Cryo": lambda p, r, cx, top, acc, base: _shards(p, r, cx, top, acc),
    "Thermal": lambda p, r, cx, top, acc, base: _flames(p, r, cx, top, acc),
    "Geologic": lambda p, r, cx, top, acc, base: _plates(p, r, cx, top, acc),
    "Metallic": lambda p, r, cx, top, acc, base: _rivets(p, r, cx, top, base) or _plates(p, r, cx, top, acc),
    "Electric": lambda p, r, cx, top, acc, base: _antenna(p, r, cx, top, acc),
    "Quantum": lambda p, r, cx, top, acc, base: _halo(p, r, cx, top + 12, acc),
    "Plasma": lambda p, r, cx, top, acc, base: _antenna(p, r, cx, top, acc) or _glitches(p, r, cx, top, acc),
    "Nano": lambda p, r, cx, top, acc, base: _motes(p, r, cx, top + 12, acc),
    "Digital": lambda p, r, cx, top, acc, base: _glitches(p, r, cx, top, acc),
    "Cosmic": lambda p, r, cx, top, acc, base: _stars(p, r, cx, top + 12, acc) or _halo(p, r, cx, top + 12, acc),
    "Shadow": lambda p, r, cx, top, acc, base: _wisps(p, r, cx, top + 12, acc),
}


def _visor(p, rng, x, y, w, accent):
    p.rect(x, y, w, 5, (28, 28, 34, 255))
    eyes = 1 if rng.random() < 0.4 else 2
    if eyes == 1:
        ex = x + w // 2 - 2
        p.rect(ex, y + 1, 4, 3, shade(accent, 1.5))
        p.rect(ex + 1, y + 1, 2, 2, (255, 255, 255, 255))
    else:
        for ex in (x + 2, x + w - 5):
            p.rect(ex, y + 1, 3, 3, shade(accent, 1.5))
            p.rect(ex, y + 1, 1, 1, (255, 255, 255, 255))


def chain_stage(sid):
    """0 = first stage (baby/base), 1 = middle, 2 = final (of a multi-stage line)."""
    chain = EVOLUTION_CHAINS.get(sid)
    if not chain or len(chain) == 1:
        return 1 if sid in SPECIES else 1
    return chain.index(sid) if sid in chain else 1


def render_species(sid):
    """One species' front still as a PIL image (250x210, chunky pixels, dark outline).
    Stage styling: babies are smaller with a big visor, finals gain a crest + aura motes."""
    import random
    from PIL import Image
    sp = SPECIES[sid]
    rng = random.Random(zlib_seed(sid))
    biome = WILD_HOME[sid]
    body_name = BIOME_BODIES[biome][zlib_seed(sid) % len(BIOME_BODIES[biome])]
    secondary = TYPE_COLORS[sp.types[1]] if len(sp.types) > 1 else None
    base, light, dark, deep, accent = _ramp(TYPE_COLORS[sp.types[0]], secondary)
    im = new(GW, GH)
    p = Pen(im)
    ground = BODIES[body_name](p, rng, base, light, dark, deep)
    # visor + core, positioned by archetype
    if body_name == "boxy":
        _visor(p, rng, 18, 15, 14, accent)
        _glow_dot(p, 25, 26, 2, accent)
    elif body_name == "droplet":
        _visor(p, rng, 20, 12, 10, accent)
    elif body_name == "bug":
        _visor(p, rng, 19, 17, 12, accent)
        _glow_dot(p, 25, 26, 2, accent)
    elif body_name == "crawler":
        _visor(p, rng, 18, 22, 14, accent)
    elif body_name == "orb":
        _glow_dot(p, 25, 19, 3, accent)
        p.rect(21, 24, 8, 3, (28, 28, 34, 255))
        p.rect(22, 25, 2, 1, shade(accent, 1.5))
        p.rect(26, 25, 2, 1, shade(accent, 1.5))
    else:
        _visor(p, rng, 19, 16, 12, accent)
        _glow_dot(p, 25, 27, 2, accent)
    # type decorations
    decor = DECOR.get(sp.types[0])
    if decor:
        decor(p, rng, 25, 14, accent, base)
    if len(sp.types) > 1 and sp.types[1] in DECOR and rng.random() < 0.6:
        DECOR[sp.types[1]](p, rng, 25, 14, accent, base)
    stage = chain_stage(sid)
    if stage == 0:                                        # the baby: shrink the whole silhouette
        im = im.resize((int(im.width * 0.82), int(im.height * 0.82)), Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (GW + 2, GH + 2), (0, 0, 0, 0))
        canvas.alpha_composite(im, ((GW + 2 - im.width) // 2, (GH + 2 - im.height) // 2 + 2))
        im = canvas
    elif stage == 2 and len(EVOLUTION_CHAINS.get(sid, [])) > 1:   # the final: a crest + aura motes
        p2 = Pen(im)
        cx, top = im.width // (2 * SCALE), 1
        p2.rect(cx - 1, top, 2, 3, rgb("#ffe27a"))
        r2 = random.Random(zlib_seed(sid) ^ 0xFFFF)
        for _ in range(6):
            p2.dot(2 + r2.randrange(im.width // SCALE - 4), 2 + r2.randrange(im.height // SCALE - 4),
                   rgb("#fff7c9"))
    im = outline(im, OUTLINE)
    return im.resize((im.width * SCALE, im.height * SCALE), Image.Resampling.NEAREST)


def zlib_seed(sid):
    import zlib
    return zlib.crc32(str(sid).encode())


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sheet = "--sheet" in sys.argv
    if args:
        ids = args
    else:
        ids = [sid for sid in SPECIES if not os.path.exists(os.path.join(OUTDIR, f"{sid}-front.png"))
               or os.path.getmtime(os.path.join(OUTDIR, f"{sid}-front.png")) < os.path.getmtime(__file__)]
        if not ids:
            print("all sprites up to date")
            return
    from PIL import Image
    made = 0
    for sid in ids:
        img = render_species(sid)
        img.save(os.path.join(OUTDIR, f"{sid}-front.png"))
        made += 1
        if sheet:
            img.thumbnail((96, 96))
    print(f"wrote {made} sprites -> {os.path.relpath(OUTDIR, HERE)}")
    if sheet:
        cols = 10
        rows = (len(ids) + cols - 1) // cols
        cell = 100
        board = Image.new("RGBA", (cols * cell, rows * cell), (112, 142, 112, 255))
        for i, sid in enumerate(ids):
            img = render_species(sid)
            img.thumbnail((cell - 4, cell - 4))
            board.alpha_composite(img, ((i % cols) * cell + 2, (i // cols) * cell + 2))
        board.save(os.path.join(HERE, "..", "assets", "scimon", "_contact_sheet.png"))
        print("contact sheet -> assets/scimon/_contact_sheet.png")


if __name__ == "__main__":
    main()
