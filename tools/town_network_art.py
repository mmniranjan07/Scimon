"""Environmental art for the wider region (routes.py / towns.py / kanto.py): bridges, piers, volcanic ground,
monuments, crystals, tunnel beams and the two landmark buildings (lighthouse, windmill, league hall).

Same rules as the other town generators: native 16 px-per-tile art, dark outline, soft shadows, seeded RNG --
so everything matches the assets/town/ look.  Walkable tiles are exactly 16x16 (they are blitted as TILEs);
props are bottom-anchored sprites; buildings keep the doorway centred on their footprint's bottom edge.

    python3 tools/town_network_art.py         # writes assets/town/*.png (safe to re-run, deterministic)
"""
import os

from pix import *

import town_buildings as tb

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "..", "assets", "town")
OUT = tb.OUT

WOOD, WOOD_L, WOOD_D, WOOD_DD = rgb("#a87848"), rgb("#c9955c"), rgb("#7a5230"), rgb("#563620")
ROPE = rgb("#c9b087")
IRON = rgb("#3b4752")
STONE, STONE_L, STONE_D = rgb("#9aa4ac"), rgb("#c2cbd2"), rgb("#6a757d")
BASALT, BASALT_L, BASALT_D = rgb("#4a4448"), rgb("#6a6166"), rgb("#332e32")
LAVA, LAVA_L, LAVA_D = rgb("#e86a2a"), rgb("#ffd24a"), rgb("#a83a1a")
CRYSTAL, CRYSTAL_L = rgb("#8fd8f0"), rgb("#d8f4ff")
LEAF_D, LEAF = rgb("#2a5a34"), rgb("#3f8a44")


def _grain(p, seed, w, h, colors, count=14):
    r = rng("grain", seed)
    for _ in range(count):
        p.dot(r.randrange(w), r.randrange(h), colors[r.randrange(len(colors))])


def _plank_run(p, x, y, w, h, vertical, seed="pl"):
    """Weathered planks filling (x, y, w, h); seams across the walking direction + a few nail dots."""
    p.rect(x, y, w, h, WOOD)
    if vertical:
        for i, px in enumerate(range(x, x + w, 4)):
            p.vline(px, y, h, WOOD_L if i % 2 == 0 else WOOD_D)
        for yy in range(y + 2, y + h, 5):
            p.hline(x, yy, w, WOOD_DD)
    else:
        for i, py in enumerate(range(y, y + h, 4)):
            p.hline(x, py, w, WOOD_L if i % 2 == 0 else WOOD_D)
        for xx in range(x + 2, x + w, 5):
            p.vline(xx, y, h, WOOD_DD)
    _grain(p, seed, w, h, (WOOD_L, WOOD_D), 10)


def _rail(p, x0, y0, x1, y1, post_every=5):
    """A rope-and-post rail along a line (posts on the near side, rope between the tops)."""
    vertical = x0 == x1
    n = abs((y1 - y0) if vertical else (x1 - x0))
    for s in range(0, n + 1, post_every):
        px, py = (x0, y0 + s) if vertical else (x0 + s, y0)
        p.rect(px, py - 3, 1, 4, WOOD_D)
        p.dot(px, py - 4, WOOD_L)
    if vertical:
        p.vline(x0, y0 - 3, n + 1, ROPE)
    else:
        p.hline(x0, y0 - 3, n + 1, ROPE)


# --------------------------------------------------------------------------- bridges / piers (walkable tiles)
def bridge_h():
    im = new(16, 16)
    p = Pen(im)
    _plank_run(p, 0, 3, 16, 10, vertical=False, seed="bh")
    for x in (0, 14):                       # side rails (the water shows at the tile's top/bottom edge)
        p.vline(x, 1, 3, WOOD_D)
        p.vline(x + 1, 1, 3, WOOD_L)
    p.hline(0, 1, 16, WOOD_DD)
    p.hline(0, 14, 16, WOOD_DD)
    return tb.finish(im, "bridge_h", OUTDIR)


def bridge_v():
    im = new(16, 16)
    p = Pen(im)
    _plank_run(p, 3, 0, 10, 16, vertical=True, seed="bv")
    for y in (0, 14):
        p.hline(1, y, 3, WOOD_D)
        p.hline(1, y + 1, 3, WOOD_L)
    p.vline(1, 0, 16, WOOD_DD)
    p.vline(14, 0, 16, WOOD_DD)
    return tb.finish(im, "bridge_v", OUTDIR)


def pier_plank():
    im = new(16, 16)
    p = Pen(im)
    _plank_run(p, 0, 0, 16, 16, vertical=False, seed="pp")
    p.hline(0, 0, 16, WOOD_DD)
    p.hline(0, 15, 16, shade(WOOD, 0.72))
    return tb.finish(im, "pier_plank", OUTDIR)


def mooring_post():
    im = new(12, 22)
    p = Pen(im)
    p.rect(4, 4, 4, 16, WOOD_D)
    p.vline(4, 4, 16, WOOD_L)
    p.vline(7, 4, 16, WOOD_DD)
    p.rect(3, 2, 6, 3, WOOD)
    p.rect(2, 12, 8, 2, WOOD_L)             # the coiled rope's lip
    p.rect(3, 13, 6, 1, ROPE)
    p.rect(3, 15, 6, 1, ROPE)
    p.rect(1, 19, 10, 2, shade(STONE, 0.9))  # stone footing
    return tb.finish(im, "mooring_post", OUTDIR)


# --------------------------------------------------------------------------- volcanic ground / lava / rocks
def volcanic_ground(v=0):
    im = new(16, 16)
    p = Pen(im)
    p.rect(0, 0, 16, 16, BASALT if v != 2 else BASALT_D)
    r = rng("volc", v)
    for _ in range(5):                       # cracked slabs
        x, y, w, h = r.randrange(12), r.randrange(12), r.randrange(3, 6), r.randrange(2, 5)
        p.rect(x, y, w, h, BASALT_L if r.random() < 0.5 else BASALT_D)
        p.frame(x, y, w, h, BASALT_D)
    for _ in range(8):
        p.dot(r.randrange(16), r.randrange(16), BASALT_L if r.random() < 0.6 else LAVA_D)
    return tb.finish(im, f"volcanic_ground_{v}", OUTDIR)


def lava_pool(frame=0):
    im = new(16, 16)
    p = Pen(im)
    p.rect(0, 0, 16, 16, BASALT)
    p.ellipse(1, 2, 14, 12, LAVA_D)
    p.ellipse(2, 3, 12, 10, LAVA)
    r = rng("lava", frame)
    for _ in range(7):                       # bright crust islands (shift one frame to the next)
        x, y = 3 + r.randrange(9), 4 + r.randrange(7)
        p.ellipse(x, y, 3 + frame, 2, LAVA_L)
    p.ellipse(4 + frame * 2, 5, 5, 3, LAVA_L)
    return tb.finish(im, f"lava_pool_{frame}", OUTDIR)


def cinder_rock():
    im = new(20, 16)
    p = Pen(im)
    p.ellipse(1, 5, 18, 10, BASALT_D)
    p.ellipse(3, 4, 13, 9, BASALT)
    p.ellipse(5, 4, 7, 5, BASALT_L)
    p.rect(6, 6, 3, 2, LAVA_D)               # still-warm seams
    p.rect(11, 8, 2, 1, LAVA_D)
    return tb.finish(im, "cinder_rock", OUTDIR)


# --------------------------------------------------------------------------- Dusklight monument / Mt. Crescent crystal
def monument():
    im = new(16, 30)
    p = Pen(im)
    p.rect(2, 24, 12, 4, shade(STONE, 0.85))         # base
    p.rect(3, 23, 10, 2, STONE_L)
    p.rect(4, 8, 8, 16, STONE)                       # the stone
    p.vline(4, 8, 16, STONE_L)
    p.vline(11, 8, 16, shade(STONE, 0.7))
    p.ellipse(4, 4, 8, 6, STONE)                     # rounded top
    p.ellipse(5, 5, 6, 4, STONE_L)
    p.rect(6, 12, 4, 1, shade(STONE, 0.7))           # a worn inscription
    p.rect(6, 14, 4, 1, shade(STONE, 0.7))
    p.rect(6, 16, 3, 1, shade(STONE, 0.7))
    p.rect(13, 18, 2, 7, IRON)                       # a small lantern on a hook
    p.rect(12, 16, 4, 3, shade(IRON, 1.2))
    p.rect(13, 17, 2, 1, rgb("#ffe27a"))
    return tb.finish(im, "monument", OUTDIR)


def moon_crystal():
    im = new(16, 26)
    p = Pen(im)
    p.ellipse(1, 20, 14, 5, shade(STONE, 0.8))       # stony base
    for cx, top, w, h in ((7, 2, 3, 18), (4, 9, 2, 11), (11, 8, 2, 12)):
        p.rect(cx, top, w, h, CRYSTAL)
        p.vline(cx, top, h, CRYSTAL_L)
        p.vline(cx + w - 1, top, h, shade(CRYSTAL, 0.72))
        for i in range(top, top + h, 3):
            p.dot(cx + 1, i, CRYSTAL_L)
        p.rect(cx - 1, top + 1, w + 2, 2, CRYSTAL_L)  # the faceted tip
    p.rect(6, 1, 2, 2, CRYSTAL_L)
    return tb.finish(im, "moon_crystal", OUTDIR)


# --------------------------------------------------------------------------- Hollowgate beams / Seaglass / arch / cart
def tunnel_beam():
    im = new(16, 30)
    p = Pen(im)
    p.rect(2, 2, 12, 4, WOOD_D)              # the lintel
    p.hline(2, 2, 12, WOOD_L)
    p.rect(2, 5, 12, 1, WOOD_DD)
    p.rect(2, 6, 3, 20, WOOD)                # posts
    p.rect(11, 6, 3, 20, WOOD)
    p.vline(2, 6, 20, WOOD_L)
    p.vline(13, 6, 20, WOOD_DD)
    p.rect(5, 9, 6, 4, IRON)                 # a caged lantern
    p.rect(6, 10, 4, 2, rgb("#ffcf5e"))
    p.rect(2, 26, 12, 2, STONE_D)            # footing
    return tb.finish(im, "tunnel_beam", OUTDIR)


def seaglass(v=0):
    im = new(16, 16)
    p = Pen(im)
    base = [rgb("#7fd8c9"), rgb("#a9e8d8"), rgb("#7fc9e8")][v]
    r = rng("sglass", v)
    for _ in range(4):
        x, y = 2 + r.randrange(10), 2 + r.randrange(10)
        w, h = 2 + r.randrange(3), 2 + r.randrange(2)
        p.rect(x, y, w, h, base)
        p.hline(x, y, w, shade(base, 1.25))
        p.hline(x, y + h - 1, w, shade(base, 0.7))
    return tb.finish(im, f"seaglass_{v}", OUTDIR)


def garden_arch():
    im = new(16, 30)
    p = Pen(im)
    p.rect(2, 4, 2, 24, WOOD_D)              # posts
    p.rect(12, 4, 2, 24, WOOD_D)
    p.vline(2, 4, 24, WOOD_L)
    p.rect(2, 2, 12, 3, WOOD_D)              # the arch's top bar
    p.hline(2, 2, 12, WOOD_L)
    for x, y in ((3, 6), (4, 10), (3, 14), (11, 7), (12, 11), (11, 15)):   # climbing green
        p.ellipse(x - 1, y - 1, 3, 3, LEAF)
        p.dot(x, y - 1, LEAF_D)
    p.rect(4, 3, 3, 2, LEAF)
    p.rect(9, 2, 3, 2, LEAF)
    return tb.finish(im, "garden_arch", OUTDIR)


def quarry_cart():
    im = new(22, 16)
    p = Pen(im)
    p.rect(2, 4, 18, 8, IRON)                # the tub
    p.rect(3, 3, 16, 2, shade(IRON, 1.25))
    p.rect(4, 6, 14, 4, shade(IRON, 0.7))
    p.ellipse(5, 5, 5, 3, STONE_L)           # ore lumps
    p.ellipse(11, 5, 5, 3, STONE)
    for wx in (4, 14):                       # wheels
        p.ellipse(wx, 10, 5, 5, WOOD_DD)
        p.ellipse(wx + 1, 11, 3, 3, WOOD_D)
        p.dot(wx + 2, 12, WOOD_L)
    return tb.finish(im, "quarry_cart", OUTDIR)


# --------------------------------------------------------------------------- landmark buildings
def lighthouse():
    """A 2x3-footprint tower (sprite 32 wide x 88 tall, bottom-anchored like every building)."""
    im = new(32, 88)
    p = Pen(im)
    p.ellipse(0, 78, 32, 10, shade(STONE_D, 0.85))       # rock base
    p.rect(4, 76, 24, 8, STONE_D)
    for band in range(4):                                 # the striped tower, tapering
        y0 = 64 - band * 14
        w = 20 - band * 2
        x0 = 16 - w // 2
        col = STONE_L if band % 2 == 0 else rgb("#d15a4a")
        p.rect(x0, y0, w, 14, col)
        p.vline(x0, y0, 14, shade(col, 1.12))
        p.vline(x0 + w - 1, y0, 14, shade(col, 0.75))
    p.rect(8, 20, 16, 6, IRON)                            # the gallery
    p.rect(10, 8, 12, 12, rgb("#2a3038"))                 # lamp room
    p.rect(12, 10, 8, 8, rgb("#ffe27a"))                  # the beacon
    p.rect(11, 9, 2, 2, rgb("#fff7c9"))
    p.rect(8, 4, 16, 4, rgb("#d1552f"))                   # the cap
    p.rect(9, 2, 14, 3, rgb("#d1552f"))
    p.rect(14, 68, 4, 10, tb.DOOR_C if hasattr(tb, "DOOR_C") else rgb("#8a5a3a"))  # a service door
    return tb.finish(im, "bld_lighthouse", OUTDIR)


def windmill():
    """A 3x4-footprint windmill (48 x 76), stone tower + wooden cap + an X of sails in front."""
    im = new(48, 76)
    p = Pen(im)
    p.rect(6, 34, 36, 36, STONE)                          # the stone tower
    p.vline(6, 34, 36, STONE_L)
    p.vline(41, 34, 36, shade(STONE, 0.72))
    _grain(p, "wmstone", 48, 76, (STONE_D, STONE_L), 22)
    p.rect(8, 30, 32, 5, WOOD_D)                          # the cap's rim
    p.rect(10, 20, 28, 11, rgb("#b9603f"))                # the wooden cap
    p.rect(10, 20, 28, 3, shade(rgb("#b9603f"), 1.2))
    # the four sails: panels on the diagonals, beams back to the hub
    hub = (24, 22)
    for cx, cy, fx, fy in ((9, 8, 4, 2), (39, 8, 33, 2), (39, 36, 33, 30), (9, 36, 4, 30)):
        p.line(hub[0], hub[1], cx, cy, WOOD_D)
        p.line(hub[0] + 1, hub[1], cx + 1, cy, WOOD_L)
    for fx, fy in ((4, 2), (33, 2), (33, 30), (4, 30)):
        p.rect(fx, fy, 11, 13, WOOD_L)
        p.frame(fx, fy, 11, 13, WOOD_DD)
        for i in range(2, 13, 3):
            p.hline(fx + 1, fy + i, 9, WOOD_D)
    p.rect(hub[0] - 2, hub[1] - 2, 5, 5, WOOD_DD)         # the hub
    p.rect(hub[0] - 1, hub[1] - 1, 3, 3, WOOD_L)
    tb.window(p, 12, 44, 8, 10, frame=tb.rgb("#f3ead2"))
    tb.door(p, 20, 56, 8, 14)                             # door centred on x=24
    tb.steps(p, 19, 70, 10, n=2)
    return tb.finish(im, "bld_windmill", OUTDIR)


def plateau_hall():
    """The league hall on Astrion Plateau: a 5x6-footprint grand building (80 x 108), columns + glass + beacon."""
    im = new(80, 108)
    p = Pen(im)
    wall, trim, glass_t, glass_b = rgb("#e8e2d0"), rgb("#c9b98a"), rgb("#bfe9ff"), rgb("#5fa3cf")
    p.rect(6, 34, 68, 66, wall)                           # the main block
    p.hline(6, 34, 68, shade(wall, 0.85))
    tb.plinth(p, 6, 96, 68)
    for cx in (8, 22, 50, 64):                            # four columns
        tb.column(p, cx, 36, 58, w=6)
    p.rect(4, 28, 72, 8, trim)                            # the architrave
    p.hline(4, 28, 72, shade(trim, 1.15))
    tb.hip_roof(p, 0, 8, 80, 22, rgb("#3f5a7a"), inset=14, seed=("plateau",))
    tb.solar(p, 14, 12, 20, 10)                           # solar roof faces, like the lab's
    tb.solar(p, 46, 12, 20, 10)
    p.rect(30, 44, 20, 40, rgb("#20262e"))                # the great glass door
    tb.glass_panel(p, 32, 46, 16, 36, top=glass_t, bot=glass_b, cols=2, rows=4)
    p.rect(30, 44, 20, 2, trim)
    p.rect(38, 60, 4, 4, rgb("#ffe27a"))                  # the beacon seal
    p.rect(36, 84, 8, 2, trim)
    tb.window(p, 14, 74, 10, 12, frame=trim, shutters=tb.rgb("#4c7a8a"))
    tb.window(p, 56, 74, 10, 12, frame=trim, shutters=tb.rgb("#4c7a8a"))
    tb.chimney(p, 66, 0, 12, shade(rgb("#a8a89c"), 1.0))
    return tb.finish(im, "bld_plateau", OUTDIR)


def tower():
    """The region's great tower (Dusklight's monument tower): a 3x8-footprint spire, 48 x 132 native."""
    im = new(48, 132)
    p = Pen(im)
    p.rect(8, 26, 32, 100, STONE)                         # the stone shaft
    p.vline(8, 26, 100, STONE_L)
    p.vline(39, 26, 100, shade(STONE, 0.7))
    _grain(p, "twrstone", 48, 132, (STONE_D, STONE_L), 30)
    for i, wy in enumerate(range(34, 118, 16)):           # tall lit windows, three ranks
        for wx in (13, 22, 31):
            p.rect(wx, wy, 6, 10, rgb("#2a3038"))
            p.rect(wx + 1, wy + 1, 4, 8, rgb("#ffe27a") if (wx + wy) % 2 else rgb("#ffcf5e"))
    p.rect(4, 20, 40, 8, STONE_D)                         # the belfry deck
    p.rect(8, 8, 32, 12, STONE)                           # the belfry
    for wx in (12, 20, 28, 34):
        p.rect(wx, 10, 4, 8, rgb("#221c26"))              # bell arches
        p.rect(wx + 1, 11, 2, 5, rgb("#ffcf5e"))
    p.rect(6, 2, 36, 7, rgb("#4a4560"))                   # the spire roof
    p.rect(10, 0, 28, 4, rgb("#4a4560"))
    p.rect(22, -0 + 0, 4, 0 + 0, rgb("#ffcf5e"))          # (tip glint baked on the deck below)
    p.rect(23, 0, 2, 2, rgb("#ffe27a"))
    p.rect(6, 118, 36, 8, shade(STONE, 0.8))              # the base course
    p.rect(12, 126, 24, 6, STONE_D)
    return tb.finish(im, "bld_tower", OUTDIR)


def gatehouse():
    """A route guard hut: 2x3-footprint, 32 x 52 native, timber upper + stone base."""
    im = new(32, 52)
    p = Pen(im)
    p.rect(4, 26, 24, 20, STONE)                          # stone base
    p.vline(4, 26, 20, STONE_L)
    p.vline(27, 26, 20, shade(STONE, 0.72))
    p.rect(6, 16, 20, 10, WOOD)                           # timber upper
    p.hline(6, 16, 20, WOOD_L)
    for wx in (8, 14, 20):
        p.vline(wx, 18, 6, WOOD_D)
    p.rect(2, 8, 28, 9, rgb("#7a5230"))                   # the shingle roof
    p.rect(0, 4, 32, 6, rgb("#8a5f38"))
    p.hline(0, 4, 32, shade(rgb("#8a5f38"), 1.2))
    p.rect(5, 20, 6, 6, rgb("#2a3038"))                   # a watch window
    p.rect(6, 21, 4, 4, rgb("#ffcf5e"))
    p.rect(12, 34, 8, 12, rgb("#8a5a3a"))                 # the doorway, centred
    p.rect(12, 34, 8, 1, shade(rgb("#8a5a3a"), 1.25))
    p.rect(4, 44, 24, 3, STONE_D)                         # step
    return tb.finish(im, "bld_gatehouse", OUTDIR)


def deptstore():
    """Verdance's Grand Mart: a 4x6-footprint department store, 64 x 104 native, glass front + awning."""
    im = new(64, 104)
    p = Pen(im)
    wall = rgb("#e9d8a6")
    p.rect(4, 30, 56, 66, wall)                           # the block
    p.hline(4, 30, 56, shade(wall, 0.85))
    tb.plinth(p, 4, 92, 56)
    tb.hip_roof(p, 0, 12, 64, 20, rgb("#b9603f"), inset=8, seed=("deptstore",))
    p.rect(4, 24, 56, 8, rgb("#fbf5e2"))                  # the sign band
    for wx in range(8, 52, 12):                           # upper windows
        tb.window(p, wx, 40, 10, 12, frame=rgb("#fbf5e2"))
        tb.window(p, wx, 58, 10, 12, frame=rgb("#fbf5e2"))
    tb.awning(p, 4, 74, 56, 8, rgb("#d1552f"), rgb("#fbf5e2"))   # the striped awning
    tb.glass_panel(p, 8, 80, 48, 14, top=rgb("#bfe9ff"), bot=rgb("#5fa3cf"), cols=3, rows=1)
    p.rect(30, 80, 4, 14, shade(wall, 0.8))               # the double-door divider
    tb.steps(p, 22, 96, 20, n=2)
    return tb.finish(im, "bld_deptstore", OUTDIR)


def museum():
    """Stonreach's Museum of Science: a 4x5-footprint hall, 64 x 84 native, columns + dome."""
    im = new(64, 84)
    p = Pen(im)
    wall, trim = rgb("#dcd6c4"), rgb("#a89a7c")
    p.rect(4, 34, 56, 42, wall)
    p.hline(4, 34, 56, shade(wall, 0.85))
    tb.plinth(p, 4, 72, 56)
    for cx in (6, 20, 36, 50):                            # a columned portico
        tb.column(p, cx, 36, 36, w=6)
    p.rect(2, 28, 60, 8, trim)                            # the architrave
    p.hline(2, 28, 60, shade(trim, 1.15))
    p.ellipse(12, 8, 40, 24, rgb("#5f7f9a"))              # the dome
    p.ellipse(16, 10, 32, 16, shade(rgb("#5f7f9a"), 1.2))
    p.rect(31, 2, 2, 8, trim)                             # the finial
    p.rect(28, 6, 8, 3, trim)
    tb.window(p, 12, 60, 10, 10, frame=trim)
    tb.window(p, 42, 60, 10, 10, frame=trim)
    p.rect(26, 56, 12, 16, rgb("#8a5a3a"))                # the doorway
    p.rect(26, 56, 12, 2, shade(rgb("#8a5a3a"), 1.25))
    tb.steps(p, 24, 74, 16, n=2)
    return tb.finish(im, "bld_museum", OUTDIR)


def mansion():
    """Cinderfall's old mansion: a 4x6-footprint manor, 64 x 100 native, dark and shuttered."""
    im = new(64, 100)
    p = Pen(im)
    wall = rgb("#8a8078")
    p.rect(4, 32, 56, 60, wall)
    p.hline(4, 32, 56, shade(wall, 0.85))
    tb.plinth(p, 4, 88, 56)
    tb.hip_roof(p, 0, 10, 64, 24, rgb("#3a3440"), inset=8, seed=("mansion",))
    tb.chimney(p, 50, 2, 14, shade(rgb("#5a5460"), 1.0))
    for wx in (10, 26, 42):                               # shuttered, mean little windows
        tb.window(p, wx, 42, 10, 12, frame=rgb("#4a4550"), shutters=rgb("#2e2a36"))
        tb.window(p, wx, 62, 10, 12, frame=rgb("#4a4550"), shutters=rgb("#2e2a36"))
    p.rect(12, 52, 2, 6, rgb("#7a4a3a"))                  # a boarded cross
    p.rect(46, 52, 2, 6, rgb("#7a4a3a"))
    p.rect(26, 74, 12, 18, rgb("#2a2630"))                # a dark doorway
    p.rect(26, 74, 12, 2, rgb("#4a4550"))
    tb.steps(p, 24, 92, 16, n=2)
    return tb.finish(im, "bld_mansion", OUTDIR)


def build_all():
    os.makedirs(OUTDIR, exist_ok=True)
    bridge_h(); bridge_v(); pier_plank(); mooring_post()
    for v in range(3):
        volcanic_ground(v)
    for f in range(2):
        lava_pool(f)
    cinder_rock(); monument(); moon_crystal(); tunnel_beam()
    for v in range(3):
        seaglass(v)
    garden_arch(); quarry_cart(); lighthouse(); windmill(); plateau_hall()
    tower(); gatehouse(); deptstore(); museum(); mansion()


if __name__ == "__main__":
    build_all()
    print("network art done ->", os.path.relpath(OUTDIR, HERE))
