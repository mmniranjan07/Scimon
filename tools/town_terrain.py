"""Terrain tiles for the revamped Riven Town (native 16x16 art, scaled x3 by the game).

Sand, shoreline water and the ocean are NOT generated here: they keep the original code in map.py, untouched.
"""
from pix import *

# ---------------------------------------------------------------- palette (warm coastal-eco village)
G0 = rgb("#428939")          # original grass base, kept so the town still matches the beach edge
G_DK = rgb("#37772f")
G_LT = rgb("#559a40")
G_HI = rgb("#6cb04c")
G_TUFT = rgb("#2f6a2b")

STONE_L = rgb("#e6dcc6")
STONE = rgb("#d6cab0")
STONE_D = rgb("#bcae92")
STONE_DD = rgb("#9c8e76")
MORTAR = rgb("#a89a80")
TEAL_IN = rgb("#5fb7b0")

DIRT = rgb("#7a5a3c")
DIRT_L = rgb("#8c6a48")
DIRT_D = rgb("#5e4430")

OUT = rgb("#2a2430")


def grass(variant):
    r = rng("grass", variant)
    im = new(16, 16, G0)
    p = Pen(im)
    for _ in range(26):
        p.dot(r.randrange(16), r.randrange(16), r.choice([G_DK, G_DK, G_LT, G_LT, G_HI]))
    # little tufts (wrap-safe: keep inside the tile)
    for _ in range(2 + variant % 2):
        x, y = r.randrange(1, 14), r.randrange(3, 14)
        p.dot(x, y, G_TUFT)
        p.dot(x + 1, y - 1, G_TUFT)
        p.dot(x + 2, y, G_TUFT)
        p.dot(x + 1, y, G_LT)
    return im


def grass_flowers(variant):
    im = grass(variant + 5)
    p = Pen(im)
    r = rng("gf", variant)
    palettes = [("#f4f0e8", "#f2cf4a"), ("#f2cf4a", "#e07a2e"), ("#f08cb0", "#f6e6a0"), ("#b9a2f0", "#f6e6a0"),
                ("#ef6b73", "#f6e6a0")]
    for i in range(3 + (variant % 2)):
        x, y = r.randrange(1, 14), r.randrange(2, 13)
        petal, core = palettes[(variant + i) % len(palettes)]
        p.dot(x, y, rgb(core))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.dot(x + dx, y + dy, rgb(petal))
        p.dot(x, y + 2, G_TUFT)
        p.dot(x, y + 3, G_TUFT)
    return im


def tall_grass(variant):
    """Wild-encounter grass: thick overlapping blades, noticeably taller/darker than the lawn."""
    r = rng("tg", variant)
    im = new(16, 16, G_DK)
    p = Pen(im)
    for _ in range(18):
        p.dot(r.randrange(16), r.randrange(16), r.choice([G_TUFT, G0]))
    blades = [(1, 6, 7), (4, 4, 9), (7, 5, 8), (10, 3, 10), (13, 5, 8)]
    for i, (x, top, h) in enumerate(blades):
        top += (variant + i) % 2
        cx = x
        for k in range(h):
            y = top + k
            wob = 1 if (k < 3 and (i + variant) % 2) else 0
            p.dot(cx + wob, y, rgb("#2f7a31"))
            p.dot(cx + 1 + wob, y, rgb("#4aa243") if k < h - 2 else rgb("#2a6a2c"))
            if k < 5:
                p.dot(cx + 2 + wob, y + 1, rgb("#63bd58"))
        p.dot(cx + wob, top - 1, rgb("#63bd58"))
        p.dot(cx + 1 + wob, top - 1, rgb("#7fd46a"))
    p.rect(0, 14, 16, 2, G_TUFT)
    for x in range(0, 16, 2):
        p.dot(x, 13, rgb("#3e9a3c"))
    return im


# ---------------------------------------------------------------- cobblestone road + plaza pavers
def _cobble(seed, tone="road"):
    r = rng("cobble", seed, tone)
    base = STONE if tone == "road" else rgb("#e0d3b8")
    im = new(16, 16, MORTAR)
    p = Pen(im)
    rows = [(0, 5), (5, 5), (10, 6)]
    for ri, (y0, h) in enumerate(rows):
        x = -r.randrange(0, 5)
        while x < 16:
            w = r.choice([5, 6, 7])
            c = shade(base, r.choice([0.96, 1.0, 1.03, 0.93]))
            p.rect(x + 1, y0 + 1, w - 1, h - 1, c)
            p.hline(x + 1, y0 + 1, w - 1, shade(c, 1.1))
            p.hline(x + 1, y0 + h - 1, w - 1, shade(c, 0.86))
            if r.random() < 0.35:
                p.dot(x + 2 + r.randrange(max(1, w - 3)), y0 + 2 + r.randrange(max(1, h - 3)), shade(c, 0.9))
            x += w
    return im


def path_base(variant):
    return _cobble(variant, "road")


def plaza_base(variant):
    im = new(16, 16, rgb("#d9cdb2"))
    p = Pen(im)
    big = rgb("#e6dac2") if (variant % 2 == 0) else rgb("#d2c5aa")
    p.rect(0, 0, 16, 16, big)
    p.frame(0, 0, 16, 16, rgb("#b9ac92"))
    p.hline(1, 1, 14, shade(big, 1.07))
    p.vline(1, 1, 14, shade(big, 1.05))
    p.hline(1, 14, 14, shade(big, 0.9))
    p.vline(14, 1, 14, shade(big, 0.92))
    r = rng("plaza", variant)
    for _ in range(3):
        p.dot(r.randrange(3, 13), r.randrange(3, 13), shade(big, 0.9))
    return im


def path_edges(neighbors):
    """Overlay for a path tile whose N/E/S/W neighbours are grass: kerb stone + a few grass blades hanging over.
    neighbors: dict dir -> True if that side is NOT road."""
    im = new(16, 16)
    p = Pen(im)
    kerb, kerb_hi, kerb_lo = rgb("#a39579"), rgb("#c9bca1"), rgb("#7e725b")
    if neighbors.get("n"):
        p.hline(0, 0, 16, kerb_lo)
        p.hline(0, 1, 16, kerb)
        p.hline(0, 2, 16, kerb_hi)
    if neighbors.get("s"):
        p.hline(0, 15, 16, kerb_lo)
        p.hline(0, 14, 16, kerb)
        p.hline(0, 13, 16, shade(MORTAR, 0.95))
    if neighbors.get("w"):
        p.vline(0, 0, 16, kerb_lo)
        p.vline(1, 0, 16, kerb)
        p.vline(2, 0, 16, kerb_hi)
    if neighbors.get("e"):
        p.vline(15, 0, 16, kerb_lo)
        p.vline(14, 0, 16, kerb)
        p.vline(13, 0, 16, shade(MORTAR, 0.95))
    return im


# ---------------------------------------------------------------- crops and farm soil
CROPS = {
    "tomato": ("#2f7a31", "#d9402f"),
    "cabbage": ("#5fae55", "#9fd58a"),
    "wheat": ("#c9a84a", "#e8cf78"),
    "carrot": ("#3d8f3a", "#e88a2a"),
    "lettuce": ("#7ccb5a", "#b8ec86"),
    "berry": ("#2f6f3a", "#7c5ad6"),
}


def crop_tile(kind, variant=0):
    leaf, fruit = (rgb(c) for c in CROPS[kind])
    r = rng("crop", kind, variant)
    im = new(16, 16, DIRT)
    p = Pen(im)
    for _ in range(18):
        p.dot(r.randrange(16), r.randrange(16), r.choice([DIRT_L, DIRT_D]))
    for y in (2, 8, 14):                # raised furrow rows
        p.hline(0, y, 16, DIRT_D)
        p.hline(0, y + 1, 16, DIRT_L)
    xs = (2, 7, 12)
    for i, x in enumerate(xs):
        for row_y in (1, 7):
            base_y = row_y + 4
            if kind == "wheat":
                p.vline(x + 1, base_y - 5, 6, rgb("#8a7a34"))
                p.rect(x, base_y - 7, 3, 3, fruit)
                p.dot(x + 1, base_y - 8, leaf)
                p.dot(x, base_y - 5, shade(fruit, 0.85))
            elif kind == "cabbage" or kind == "lettuce":
                p.rect(x - 1, base_y - 3, 5, 4, leaf)
                p.rect(x, base_y - 4, 3, 1, leaf)
                p.rect(x + 1, base_y - 2, 2, 2, fruit)
                p.hline(x - 1, base_y, 5, shade(leaf, 0.7))
            elif kind == "carrot":
                p.rect(x, base_y - 4, 3, 3, leaf)
                p.dot(x + 1, base_y - 5, leaf)
                p.dot(x, base_y - 5, shade(leaf, 1.2))
                p.dot(x + 1, base_y - 1, fruit)
                p.dot(x + 1, base_y, fruit)
            else:   # tomato / berry bushes with fruit dots
                p.rect(x - 1, base_y - 4, 5, 4, leaf)
                p.hline(x, base_y - 5, 3, shade(leaf, 1.15))
                p.dot(x, base_y - 3, fruit)
                p.dot(x + 2, base_y - 2, fruit)
                p.dot(x + 1, base_y - 4, fruit)
                p.hline(x - 1, base_y, 5, shade(leaf, 0.65))
    return im


# ---------------------------------------------------------------- stone sea-wall (town edge above the beach)
def seawall(variant):
    """Promenade balustrade between the town and the sand.  Bottom rows meet the sand exactly as before."""
    r = rng("seawall", variant)
    im = new(16, 16)
    p = Pen(im)
    base = rgb("#cdbf9f")
    p.rect(0, 0, 16, 16, G0)
    for _ in range(14):
        p.dot(r.randrange(16), r.randrange(8), r.choice([G_DK, G_LT]))
    # kerb walkway strip on the grass side
    p.rect(0, 5, 16, 3, rgb("#d9ccb0"))
    p.hline(0, 5, 16, rgb("#efe5cd"))
    p.hline(0, 7, 16, rgb("#b5a78a"))
    # wall body
    p.rect(0, 8, 16, 8, base)
    p.hline(0, 8, 16, rgb("#e9ddc2"))
    for y in (11, 14):
        p.hline(0, y, 16, rgb("#b0a284"))
    off = 0 if variant % 2 == 0 else 4
    for y0 in (8, 11, 14):
        for x in range(-off + (0 if y0 == 11 else 8), 16, 8):
            if 0 <= x < 16:
                p.vline(x, y0, 3, rgb("#b0a284"))
    p.hline(0, 15, 16, rgb("#8e8167"))
    # teal conduit light band (the town's signature) set into the coping
    p.hline(0, 6, 16, rgb("#b5a78a"))
    if variant % 4 == 1:
        p.rect(7, 9, 2, 1, rgb("#6be6ee"))
    return im


def sea_pillar():
    """Gate post at each side of the beach stairs, topped with a glowing lantern."""
    im = new(16, 24)
    p = Pen(im)
    p.rect(3, 8, 10, 16, rgb("#c3b594"))
    p.rect(3, 8, 10, 2, rgb("#e6dbc0"))
    p.rect(3, 10, 2, 14, rgb("#d6caac"))
    p.rect(11, 10, 2, 14, rgb("#a89a7c"))
    p.hline(3, 16, 10, rgb("#a89a7c"))
    p.hline(3, 21, 10, rgb("#a89a7c"))
    p.rect(2, 6, 12, 3, rgb("#d9cdb0"))
    p.rect(2, 6, 12, 1, rgb("#f0e6cc"))
    p.rect(5, 1, 6, 5, rgb("#3a5a62"))
    p.rect(6, 2, 4, 3, rgb("#7ef2ff"))
    p.rect(6, 2, 2, 1, rgb("#d6ffff"))
    p.rect(4, 0, 8, 1, rgb("#2e4a52"))
    p.hline(0, 23, 16, rgb("#7e725b"))
    return im


# ---------------------------------------------------------------- pond (new 'w' tile) + coping
WATER = rgb("#3f86bd")
WATER_L = rgb("#5aa0d0")
WATER_D = rgb("#2f6f9f")
WATER_DD = rgb("#285f8a")


def pond_water(frame):
    """Four-frame shimmering pond tile; frames offset so neighbouring tiles ripple together."""
    im = new(16, 16, WATER)
    p = Pen(im)
    p.rect(0, 0, 16, 16, WATER)
    p.hline(0, 14, 16, WATER_D)
    p.hline(0, 15, 16, WATER_DD)
    p.hline(0, 7, 16, shade(WATER, 0.97))
    f = frame % 4
    for (x, y, w) in ((2, 3, 5), (9, 10, 4), (11, 4, 3)):
        xx = (x + f * 2) % 14
        p.hline(xx, y, w, WATER_L)
    p.hline((6 + f * 3) % 12, 12, 3, shade(WATER_L, 1.1))
    return im


def pond_coping(side):
    """Cut stone rim; 'side' in n/s/e/w (art drawn on the land tile that touches the water)."""
    im = new(16, 16)
    p = Pen(im)
    top, mid, low = rgb("#eadfc6"), rgb("#cbbd9f"), rgb("#8e8167")
    if side == "n":
        p.rect(0, 10, 16, 6, mid)
        p.hline(0, 10, 16, top)
        p.hline(0, 11, 16, shade(top, 0.95))
        p.hline(0, 15, 16, low)
        for x in (3, 11):
            p.vline(x, 11, 4, shade(mid, 0.82))
    elif side == "s":
        p.rect(0, 0, 16, 6, mid)
        p.hline(0, 0, 16, top)
        p.hline(0, 5, 16, shade(mid, 0.8))
        p.hline(0, 6, 16, low)
        for x in (3, 11):
            p.vline(x, 1, 4, shade(mid, 0.82))
    elif side == "w":
        p.rect(10, 0, 6, 16, mid)
        p.vline(10, 0, 16, top)
        p.vline(11, 0, 16, shade(top, 0.95))
        p.vline(15, 0, 16, low)
        for y in (3, 11):
            p.hline(11, y, 4, shade(mid, 0.82))
    elif side == "e":
        p.rect(0, 0, 6, 16, mid)
        p.vline(0, 0, 16, shade(mid, 0.9))
        p.vline(5, 0, 16, shade(mid, 0.8))
        p.vline(6, 0, 16, low)
        for y in (3, 11):
            p.hline(1, y, 4, shade(mid, 0.82))
    return im


# ---------------------------------------------------------------- fences + hedges (autotiled by map.py)
FENCE = rgb("#f4ecd8")
FENCE_L = rgb("#ffffff")
FENCE_D = rgb("#c9bca0")
FENCE_DD = rgb("#8e816a")


def fence_h(variant=0):
    """Picket fence seen from the front; the tile is transparent so it sits on the grass drawn below."""
    im = new(16, 16)
    p = Pen(im)
    for rail_y in (6, 11):
        p.hline(0, rail_y, 16, FENCE_D)
        p.hline(0, rail_y + 1, 16, FENCE_DD)
    for i, x in enumerate((1, 5, 9, 13)):
        top = 3 + (i % 2) * 0
        p.rect(x, top + 1, 3, 11, FENCE)
        p.dot(x + 1, top, FENCE)
        p.vline(x, top + 1, 11, FENCE_L)
        p.vline(x + 2, top + 1, 11, FENCE_D)
        p.hline(x, 13, 3, FENCE_DD)
    p.hline(0, 14, 16, rgb("#2f6a2b", 90))
    return im


def fence_v():
    """Fence running away from the viewer: a row of post caps over a single rail."""
    im = new(16, 16)
    p = Pen(im)
    p.rect(6, 0, 4, 16, FENCE_D)
    p.vline(6, 0, 16, FENCE_L)
    p.vline(9, 0, 16, FENCE_DD)
    for y in (1, 8):
        p.rect(5, y, 6, 5, FENCE)
        p.hline(5, y, 6, FENCE_L)
        p.hline(5, y + 4, 6, FENCE_DD)
        p.dot(5, y + 4, FENCE_D)
    p.rect(5, 15, 6, 1, rgb("#2f6a2b", 110))
    return im


def fence_post():
    im = new(16, 16)
    p = Pen(im)
    p.rect(5, 2, 6, 12, FENCE)
    p.vline(5, 2, 12, FENCE_L)
    p.vline(10, 2, 12, FENCE_DD)
    p.rect(4, 1, 8, 2, FENCE_L)
    p.hline(4, 2, 8, FENCE_D)
    p.hline(5, 14, 6, rgb("#2f6a2b", 110))
    return im


def hedge(kind):
    """kind: mid / l / r / solo.  Dense clipped hedge, 12 px tall, rounded at its open ends."""
    r = rng("hedge", kind)
    im = new(16, 16)
    p = Pen(im)
    top = 3
    for y in range(top, 15):
        for x in range(16):
            t = (y - top) / 11
            c = mix(rgb("#4aa243"), rgb("#2a6a2f"), t)
            p.dot(x, y, c)
    for _ in range(46):
        x, y = r.randrange(16), r.randrange(top, 14)
        p.dot(x, y, r.choice([rgb("#6fc254"), rgb("#1f5a2a"), rgb("#3f9a46")]))
    p.hline(0, top, 16, rgb("#7fd46a"))
    p.hline(0, 14, 16, rgb("#1f4a24"))
    p.hline(0, 15, 16, rgb("#2f6a2b", 120))
    # scalloped top
    for x in range(16):
        if (x // 3) % 2:
            p.dot(x, top - 1, rgb("#4aa243"))
    if kind in ("l", "solo"):
        for y in range(top - 1, 16):
            p.dot(0, y, (0, 0, 0, 0))
        for y in range(top, 15):
            p.dot(1, y, rgb("#1f5a2a") if y > top + 1 else (0, 0, 0, 0))
        p.dot(0, 14, (0, 0, 0, 0))
    if kind in ("r", "solo"):
        for y in range(top - 1, 16):
            p.dot(15, y, (0, 0, 0, 0))
        for y in range(top, 15):
            p.dot(14, y, rgb("#1f5a2a") if y > top + 1 else (0, 0, 0, 0))
    # dark outline on exposed edges
    return im


def build(out_dir):
    import os
    os.makedirs(out_dir, exist_ok=True)

    def save(name, im):
        im.save(os.path.join(out_dir, name + ".png"))

    for v in range(4):
        save(f"grass_{v}", grass(v))
        save(f"gflower_{v}", grass_flowers(v))
        save(f"tallgrass_{v}", tall_grass(v))
        save(f"road_{v}", path_base(v))
        save(f"plaza_{v}", plaza_base(v))
        save(f"pond_{v}", pond_water(v))
        save(f"seawall_{v}", seawall(v))
    for k in CROPS:
        for v in range(2):
            save(f"crop_{k}_{v}", crop_tile(k, v))
    for s in "nsew":
        save(f"coping_{s}", pond_coping(s))
    save("sea_pillar", sea_pillar())
    save("fence_h", fence_h())
    save("fence_v", fence_v())
    save("fence_post", fence_post())
    for k in ("mid", "l", "r", "solo"):
        save(f"hedge_{k}", hedge(k))
    for key in ("n", "s", "e", "w"):
        save(f"kerb_{key}", path_edges({key: True}))


if __name__ == "__main__":
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else "../assets/town")
