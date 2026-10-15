"""Original pixel art for the sprites that used to be cut from third-party packs.

    python tools/generate_original_art.py

Regenerates, from scratch (pure PIL, seeded, no input files), every sprite that previously came from the
Modern Interiors / LRK / overworld-tileset packs: assets/interiors/* (except x_*), assets/characters/*,
assets/town/beach_*.  Names and pixel sizes are the same as before, so layouts and collision are unchanged.
"""
import colorsys
import os
import random

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")

SIZES = {'sofa_beige': (48, 32), 'sofa_beige_back': (48, 32), 'sofa_beige_l': (31, 48), 'sofa_beige_r': (31, 48), 'armchair_beige': (32, 32), 'armchair_beige_back': (32, 32), 'sofa_grey': (48, 32), 'sofa_grey_back': (48, 32), 'armchair_grey': (32, 32), 'armchair_grey_back': (32, 32), 'fireplace_stone': (32, 48), 'fireplace_stone_lit': (32, 48), 'fireplace_brick': (32, 48), 'fireplace_brick_lit': (32, 48), 'table_brown_h': (48, 32), 'table_brown_v': (28, 48), 'chair_brown_back': (16, 32), 'chair_brown_front': (16, 25), 'chair_brown_l': (16, 32), 'chair_brown_r': (16, 32), 'table_round_white': (32, 32), 'chair_white_back': (16, 32), 'chair_white_front': (16, 25), 'table_round_brown': (32, 32), 'rug_white_h': (64, 32), 'rug_white_v': (32, 64), 'rug_dots_h': (64, 32), 'rug_red_h': (64, 32), 'rug_red_v': (32, 64), 'rug_red2_h': (64, 32), 'runner_white': (64, 16), 'runner_olive': (64, 16), 'rug_round_white': (48, 32), 'rug_round_small': (32, 26), 'rug_round_grey': (48, 32), 'tv_off': (36, 20), 'tv_on': (36, 20), 'soundbar': (32, 6), 'speaker_l': (10, 32), 'speaker_r': (10, 32), 'coffee_table': (32, 16), 'stool_a': (16, 16), 'stool_b': (16, 16), 'fridge_white': (24, 56), 'fridge_white_open': (28, 56), 'fridge_steel': (32, 61), 'fridge_steel_open': (51, 61), 'kitchen_run_sink': (121, 47), 'kitchen_run_end': (32, 42), 'stove': (32, 42), 'stove_lit': (32, 42), 'sink_a': (32, 16), 'sink_b': (32, 16), 'wall_cabinets': (128, 23), 'counter_row': (128, 23), 'kitchen_run_sink_olive': (121, 47), 'counter_row_grey': (128, 23), 'wall_cabinets_grey': (128, 23), 'stove_grey_lit': (32, 42), 'sink_grey': (32, 16), 'bookcase_a': (48, 48), 'bookcase_doors': (48, 48), 'cabinet_tall': (16, 48), 'sideboard_a': (48, 45), 'shelf_a': (48, 34), 'desk_items': (48, 25), 'lowcab_a': (48, 25), 'bench_a': (48, 14), 'bookcase_color': (48, 48), 'bookcase_color_doors': (48, 48), 'cabinet_big': (48, 48), 'sideboard_b': (48, 45), 'cabinet_wide': (48, 45), 'shelf_b': (48, 34), 'cabinet_mid': (48, 34), 'narrow_shelf': (16, 34), 'desk_b': (48, 25), 'lowcab_b': (48, 25), 'bookcase_w': (48, 48), 'bookcase_w_doors': (48, 48), 'sideboard_w': (48, 45), 'shelf_w': (48, 34), 'desk_w': (48, 25), 'lowcab_w': (48, 25), 'bookcase_wc': (48, 48), 'bookcase_wc_doors': (48, 48), 'cabinet_big_w': (48, 48), 'sideboard_wc': (48, 45), 'cabinet_wide_w': (48, 45), 'shelf_wc': (48, 34), 'desk_wc': (48, 25), 'doorway_black': (30, 48), 'door_closed': (30, 48), 'door_open': (30, 51), 'window_day': (48, 30), 'window_night': (48, 30), 'lamp_tripod': (16, 47), 'lamp_floor_a': (16, 46), 'lamp_floor_b': (16, 46), 'lamp_table_a': (16, 25), 'lamp_table_b': (16, 25), 'picture_sunset': (32, 16), 'mirror_tall': (16, 46), 'plant_red_pot': (15, 30), 'plant_fern_pot': (16, 31), 'plant_grey_pot': (16, 31), 'picture_hills': (32, 16), 'flowers_pink': (13, 19), 'flowers_blue': (7, 17), 'plant_small': (16, 16), 'clock': (16, 16), 'bed_blue': (41, 33), 'bed_white': (41, 33), 'table_orange': (41, 40), 'table_light': (41, 40), 'bench_orange': (38, 21), 'bookshelf_wood_a': (32, 35), 'bookshelf_wood_b': (34, 32), 'rug_red_gold': (60, 40), 'rug_blue_gold_v': (40, 60), 'rug_red_gold_v': (40, 60), 'mat_green': (24, 18), 'mat_red': (24, 18), 'mat_blue': (24, 18), 'mat_blue2': (24, 18), 'mat_small_red': (16, 16), 'sofa_red': (48, 26), 'store_rack_w': (64, 32), 'store_rack_tall': (21, 31), 'crate_a': (17, 15), 'crate_b': (17, 13), 'window_red': (25, 20), 'window_white': (25, 20), 'door_double': (32, 28), 'steel_door': (64, 25), 'window_sky': (28, 21), 'school_desk_row': (66, 23), 'teacher_desk': (28, 27), 'globe_a': (13, 21), 'globe_b': (13, 21), 'chalkboard': (28, 23), 'board_wall': (26, 13), 'locker_blue': (32, 44), 'whiteboard_stand': (34, 54), 'plant_pot_tall': (14, 23), 'plant_pot_small': (12, 14), 'palm': (23, 31), 'wardrobe_a': (27, 39), 'wardrobe_glass': (27, 27), 'wardrobe_b': (27, 32), 'vanity_a': (28, 30), 'vanity_b': (28, 30), 'dresser_a': (25, 21), 'dresser_b': (48, 24), 'floor_lamp_red': (19, 26), 'floor_lamp_blue': (19, 35), 'floor_lamp_cream': (15, 33), 'store_shelf_a': (96, 34), 'store_shelf_b': (98, 36), 'mirror_stand': (34, 21), 'world_map': (7, 4), 'wall_cream': (48, 28), 'wall_teal': (48, 28), 'wall_white': (48, 28), 'wall_pink': (48, 28), 'wall_sage': (48, 28), 'panel_grey': (48, 28), 'panel_orange': (48, 28), 'panel_brown': (48, 28), 'floor_wood_light': (32, 32), 'floor_wood_pale': (32, 32), 'floor_wood_dark': (32, 32), 'floor_tile_light': (32, 32), 'floor_tile_taupe': (32, 32), 'floor_tile_dark': (32, 32)}


# ------------------------------------------------------------------ colour helpers
def C(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def lit(c, t=0.25):
    return mix(c, (255, 255, 255, 255), t)


def dim(c, t=0.25):
    return mix(c, (20, 12, 24, 255), t)


OL = C("#3a2620")          # warm dark outline used on most furniture
GLASS = C("#bfe4ee")
GLASS_D = C("#86bccb")

WOOD = {
    "brown": dict(top=C("#c58f5e"), face=C("#a36d44"), dark=C("#7a4a30"), line=OL, hi=C("#dcab7c")),
    "white": dict(top=C("#f6f1e8"), face=C("#e3dccd"), dark=C("#b9ae9b"), line=C("#6d6054"), hi=C("#ffffff")),
    "cream": dict(top=C("#f1e4c0"), face=C("#dccb9c"), dark=C("#b09c6a"), line=C("#6f5a3a"), hi=C("#fff8dc")),
    "teal": dict(top=C("#86b7ae"), face=C("#5f9188"), dark=C("#43706a"), line=C("#22403c"), hi=C("#add6cd")),
    "orange": dict(top=C("#e0a060"), face=C("#c8803f"), dark=C("#955a2a"), line=OL, hi=C("#f3bf86")),
    "grey": dict(top=C("#b8bcc4"), face=C("#8f949f"), dark=C("#686d79"), line=C("#2e323c"), hi=C("#d9dce2")),
}


class Pix:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.im.load()

    def p(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = c

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.p(xx, yy, c)

    def frame(self, x, y, w, h, c):
        for xx in range(x, x + w):
            self.p(xx, y, c)
            self.p(xx, y + h - 1, c)
        for yy in range(y, y + h):
            self.p(x, yy, c)
            self.p(x + w - 1, yy, c)

    def hline(self, x, y, n, c):
        for i in range(n):
            self.p(x + i, y, c)

    def vline(self, x, y, n, c):
        for i in range(n):
            self.p(x, y + i, c)

    def ell(self, x, y, w, h, fill, line=None):
        d = ImageDraw.Draw(self.im)
        d.ellipse((x, y, x + w - 1, y + h - 1), fill=fill, outline=line)

    def get(self, x, y):
        return self.px[x, y]

    def paste(self, other, x, y):
        self.im.alpha_composite(other.im, (x, y))


def box(p, x, y, w, h, fill, line=OL, top=None, top_h=0, shade=True):
    """Outlined block with an optional lighter top band and a darker bottom row."""
    p.rect(x, y, w, h, fill)
    if top is not None and top_h:
        p.rect(x + 1, y + 1, w - 2, top_h, top)
    if shade and h > 4:
        p.hline(x + 1, y + h - 2, w - 2, dim(fill, 0.2))
    p.frame(x, y, w, h, line)
    for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):      # soften the corners
        p.p(cx, cy, (0, 0, 0, 0))


def handle(p, x, y, c=C("#f0d890")):
    p.p(x, y, c)
    p.p(x, y + 1, dim(c, 0.3))


def save(name, pix, sub="interiors"):
    want = SIZES.get(name)
    if want and (pix.w, pix.h) != tuple(want):
        raise SystemExit(f"{name}: drew {pix.w}x{pix.h}, expected {want}")
    path = os.path.join(OUT, sub, name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pix.im.save(path)


# =================================================================== seating
def sofa(w, h, col, facing="front"):
    p = Pix(w, h)
    d = dim(col, 0.22)
    if facing == "front":
        box(p, 2, 0, w - 4, h - 12, col)                                 # backrest
        p.hline(4, 2, w - 8, lit(col, 0.35))
        box(p, 0, 7, 9, h - 12, d)                                       # arms
        box(p, w - 9, 7, 9, h - 12, d)
        p.hline(2, 9, 5, lit(d, 0.25)); p.hline(w - 7, 9, 5, lit(d, 0.25))
        sw = w - 16
        box(p, 8, h - 17, sw // 2, 12, lit(col, 0.12))                   # seat cushions
        box(p, 8 + sw // 2, h - 17, sw - sw // 2, 12, lit(col, 0.12))
        p.hline(10, h - 16, sw - 4, lit(col, 0.45))
        for lx in (2, w - 4):
            p.rect(lx, h - 5, 2, 4, OL)
    elif facing == "back":
        box(p, 0, 2, w, h - 8, col)
        p.hline(2, 4, w - 4, lit(col, 0.3))
        p.vline(w // 2, 6, h - 16, dim(col, 0.2))
        for lx in (2, w - 4):
            p.rect(lx, h - 7, 2, 6, OL)
        box(p, 0, 0, w, 5, d)
    else:                                                                # side view, 'l' faces left, 'r' faces right
        back_x = w - 11 if facing == "l" else 0
        seat_x = 0 if facing == "l" else 11
        box(p, back_x, 2, 11, h - 4, dim(col, 0.12))                     # backrest strip
        box(p, seat_x, 2, w - 11, 14, lit(col, 0.1))
        box(p, seat_x, 17, w - 11, 14, lit(col, 0.1))
        box(p, 0, 0, w, 9, d)                                            # far arm cap
        box(p, 0, h - 11, w, 11, d)                                      # near arm
        p.hline(2, h - 9, w - 4, lit(d, 0.3))
    return p


def armchair(w, h, col, facing="front"):
    p = Pix(w, h)
    d = dim(col, 0.22)
    if facing == "front":
        box(p, 3, 0, w - 6, 20, col)
        p.hline(5, 2, w - 10, lit(col, 0.35))
        box(p, 0, 8, 8, h - 10, d); box(p, w - 8, 8, 8, h - 10, d)
        box(p, 7, 17, w - 14, 11, lit(col, 0.12))
        p.hline(9, 18, w - 18, lit(col, 0.45))
        p.hline(11, 22, 6, dim(col, 0.3))                                # a little cushion pattern
        for lx in (2, w - 4):
            p.rect(lx, h - 3, 2, 3, OL)
    else:
        box(p, 0, 3, w, h - 7, col)
        p.hline(2, 5, w - 4, lit(col, 0.3))
        p.vline(w // 2, 9, h - 17, dim(col, 0.2))
        box(p, 0, 0, w, 5, d)
        for lx in (2, w - 4):
            p.rect(lx, h - 4, 2, 4, OL)
    return p


def chair(w, h, facing, wood):
    p = Pix(w, h)
    wd = WOOD[wood]
    seat = C("#d8b48a") if wood == "brown" else C("#f2ede4")
    if facing == "back":
        box(p, 2, 0, w - 4, 15, wd["face"], wd["line"])
        for sx in range(5, w - 4, 3):
            p.vline(sx, 3, 9, wd["dark"])
        box(p, 1, 15, w - 2, 7, wd["top"], wd["line"])
        for lx in (2, w - 4):
            p.rect(lx, 22, 2, h - 22, wd["line"])
    elif facing == "front":
        box(p, 1, 0, w - 2, 9, wd["top"], wd["line"], top=seat, top_h=5)
        box(p, 2, 9, w - 4, 5, wd["face"], wd["line"])
        for lx in (2, w - 4):
            p.rect(lx, 14, 2, h - 14, wd["line"])
    else:
        bx = 1 if facing == "l" else w - 6
        box(p, bx, 0, 5, 20, wd["face"], wd["line"])
        sx = 4 if facing == "l" else 1
        box(p, sx, 15, w - 5, 6, wd["top"], wd["line"], top=seat, top_h=2)
        for lx in (sx + 1, sx + w - 8):
            p.rect(lx, 21, 2, h - 21, wd["line"])
    return p


def stool(col):
    p = Pix(16, 16)
    p.ell(1, 1, 14, 7, col, OL)
    p.ell(3, 2, 8, 3, lit(col, 0.4))
    for lx in (3, 11):
        p.rect(lx, 7, 2, 8, OL)
    p.hline(3, 11, 10, OL)
    return p


# =================================================================== tables / rugs
def table(w, h, wood, round_=False):
    p = Pix(w, h)
    wd = WOOD[wood]
    if round_:
        p.ell(1, 2, w - 2, h - 12, wd["top"], wd["line"])
        p.ell(5, 4, w - 12, h - 18, lit(wd["top"], 0.25))
        p.rect(w // 2 - 2, h - 10, 4, 8, wd["line"])
        p.hline(w // 2 - 6, h - 3, 12, wd["line"])
        p.hline(w // 2 - 5, h - 2, 10, wd["dark"])
    else:
        th = max(8, h // 3)
        box(p, 0, 0, w, th + 3, wd["top"], wd["line"], top=wd["hi"], top_h=2)
        p.rect(1, th + 1, w - 2, 2, wd["face"])
        for lx in (2, w - 5):
            p.rect(lx, th + 3, 3, h - th - 3, wd["line"])
            p.vline(lx + 1, th + 3, h - th - 4, wd["dark"])
    return p


def table_v(w, h, wood):
    p = Pix(w, h)
    wd = WOOD[wood]
    box(p, 0, 0, w, h - 8, wd["top"], wd["line"], top=wd["hi"], top_h=2)
    p.hline(2, h - 11, w - 4, wd["face"])
    for lx in (2, w - 5):
        p.rect(lx, h - 8, 3, 8, wd["line"])
    return p


def rug(w, h, base, border, motif=None, fringe=False, round_=False):
    p = Pix(w, h)
    if round_:
        p.ell(0, 0, w, h, border, dim(border, 0.35))
        p.ell(3, 2, w - 6, h - 4, base)
        p.ell(w // 2 - 6, h // 2 - 3, 12, 6, border)
        p.ell(w // 2 - 3, h // 2 - 1, 6, 3, lit(base, 0.2))
        return p
    p.rect(0, 0, w, h, border)
    p.frame(0, 0, w, h, dim(border, 0.35))
    p.rect(3, 3, w - 6, h - 6, base)
    p.frame(3, 3, w - 6, h - 6, dim(base, 0.25))
    if motif == "dots":
        for yy in range(6, h - 5, 5):
            for xx in range(6 + (yy // 5 % 2) * 3, w - 5, 6):
                p.p(xx, yy, lit(base, 0.55))
    elif motif == "diamond":
        cx, cy = w // 2, h // 2
        for r in range(0, min(w, h) // 2 - 6, 3):
            for k in range(-r, r + 1):
                p.p(cx + k, cy - (r - abs(k)), lit(base, 0.4)); p.p(cx + k, cy + (r - abs(k)), lit(base, 0.4))
    elif motif == "stripes":
        for xx in range(8, w - 6, 6):
            p.vline(xx, 4, h - 8, lit(base, 0.35))
    elif motif == "weave":
        for yy in range(5, h - 4, 3):
            p.hline(5, yy, w - 10, dim(base, 0.12))
    if fringe:
        for xx in range(1, w - 1, 2):
            p.p(xx, 0, lit(border, 0.5)); p.p(xx, h - 1, lit(border, 0.5))
    return p


def runner(w, h, base, border):
    p = Pix(w, h)
    p.rect(0, 1, w, h - 2, border)
    p.frame(0, 1, w, h - 2, dim(border, 0.35))
    p.rect(3, 4, w - 6, h - 8, base)
    for xx in range(6, w - 5, 7):
        p.rect(xx, 6, 2, h - 12, lit(base, 0.35))
    return p


def mat(w, h, col):
    p = Pix(w, h)
    p.rect(0, 0, w, h, dim(col, 0.35))
    p.rect(1, 1, w - 2, h - 2, col)
    for xx in range(3, w - 2, 3):
        p.vline(xx, 3, h - 6, lit(col, 0.3))
    p.frame(2, 2, w - 4, h - 4, dim(col, 0.2))
    return p


# =================================================================== storage
BOOKS = [C("#b5453a"), C("#3f6fa5"), C("#4d8a5a"), C("#d3a338"), C("#7d4f9a"), C("#d9d0b8"), C("#a05a2c"), C("#2f4f6a")]


def book_row(p, x, y, w, h, rng):
    xx = x
    while xx < x + w - 1:
        bw = rng.choice((2, 2, 3))
        bh = h - rng.choice((0, 0, 1, 2, 3))
        col = rng.choice(BOOKS)
        bw = min(bw, x + w - xx)
        p.rect(xx, y + h - bh, bw, bh, col)
        p.vline(xx, y + h - bh, bh, dim(col, 0.3))
        p.p(xx + bw - 1, y + h - bh, lit(col, 0.4))
        xx += bw
        if rng.random() < 0.12:
            xx += 1


def bookcase(w, h, wood, doors=False, seed=1):
    p = Pix(w, h)
    wd = WOOD[wood]
    rng = random.Random(seed)
    box(p, 0, 0, w, h, wd["face"], wd["line"], top=wd["top"], top_h=2)
    rows = max(2, (h - 8) // 11)
    inner_h = (h - 6 - 2 * rows + 2) // rows
    for r in range(rows):
        y0 = 3 + r * (inner_h + 2)
        p.rect(2, y0, w - 4, inner_h, dim(wd["dark"], 0.35))
        book_row(p, 3, y0 + 1, w - 6, inner_h - 1, rng)
        p.hline(1, y0 + inner_h, w - 2, wd["top"])
        p.hline(1, y0 + inner_h + 1, w - 2, wd["dark"])
    p.rect(1, h - 4, w - 2, 3, wd["dark"])
    p.hline(2, h - 5, w - 4, wd["line"])
    if doors:
        half = (w - 4) // 2
        for dx in (2, 2 + half):
            for yy in range(3, h - 5):
                for xx in range(dx, dx + half):
                    r, g, b, a = p.get(xx, yy)
                    p.p(xx, yy, mix((r, g, b, 255), GLASS, 0.35))
            p.frame(dx, 3, half, h - 8, wd["line"])
            p.hline(dx + 2, 5, 3, (255, 255, 255, 255)); p.p(dx + 2, 6, (255, 255, 255, 255))
        handle(p, w // 2 - 2, h // 2)
        handle(p, w // 2 + 1, h // 2)
    return p


def cabinet(w, h, wood, doors=2, drawers=0, top_items=False, seed=1):
    p = Pix(w, h)
    wd = WOOD[wood]
    rng = random.Random(seed)
    box(p, 0, 0, w, h, wd["face"], wd["line"], top=wd["top"], top_h=4)
    p.hline(1, 5, w - 2, wd["hi"])
    body_y = 7
    dh = h - body_y - 5
    if drawers:
        dr_h = max(5, dh // drawers)
        for i in range(drawers):
            y0 = body_y + i * dr_h
            box(p, 2, y0, w - 4, dr_h - 1, wd["top"], wd["dark"], shade=False)
            handle(p, w // 2 - 1, y0 + dr_h // 2 - 1)
    else:
        dw = (w - 4) // doors
        for i in range(doors):
            x0 = 2 + i * dw
            box(p, x0, body_y, dw - (1 if i < doors - 1 else 0), dh, wd["top"], wd["dark"], shade=False)
            p.frame(x0 + 2, body_y + 2, dw - 5, dh - 4, wd["face"])
            handle(p, x0 + (dw - 4 if i == 0 else 2), body_y + dh // 2 - 1)
    for lx in (2, w - 4):
        p.rect(lx, h - 4, 2, 4, wd["line"])
    if top_items:
        for ix in (4, w // 2, w - 10):
            p.rect(ix, 1, 4, 3, rng.choice(BOOKS))
    return p


def shelf(w, h, wood, seed=1):
    """open display shelf (jars, books, a plant) - drawn front-on."""
    p = Pix(w, h)
    wd = WOOD[wood]
    rng = random.Random(seed)
    box(p, 0, 0, w, h, dim(wd["dark"], 0.4), wd["line"])
    levels = 2 if h < 40 else 3
    lh = (h - 4) // levels
    for i in range(levels):
        y0 = 2 + i * lh
        p.hline(1, y0 + lh - 3, w - 2, wd["top"])
        p.hline(1, y0 + lh - 2, w - 2, wd["face"])
        p.hline(1, y0 + lh - 1, w - 2, wd["dark"])
        xx = 3
        while xx < w - 8:
            kind = rng.choice(("book", "book", "jar", "plant", "box"))
            if kind == "book":
                bw = rng.randint(6, 12); book_row(p, xx, y0 + 2, bw, lh - 5, rng)
            elif kind == "jar":
                bw = 5; p.rect(xx, y0 + lh - 9, 5, 6, GLASS); p.frame(xx, y0 + lh - 9, 5, 6, GLASS_D); p.rect(xx + 1, y0 + lh - 7, 3, 3, rng.choice(BOOKS))
            elif kind == "plant":
                bw = 6; p.rect(xx + 1, y0 + lh - 7, 4, 4, C("#b8653a")); p.rect(xx, y0 + lh - 11, 6, 4, C("#4d8a3c")); p.p(xx + 2, y0 + lh - 12, C("#6fb04a"))
            else:
                bw = 6; p.rect(xx, y0 + lh - 8, 6, 5, rng.choice(BOOKS)); p.hline(xx, y0 + lh - 8, 6, C("#f0e4c0"))
            xx += bw + 2
    return p


def desk(w, h, wood, items=False, seed=3):
    p = Pix(w, h)
    wd = WOOD[wood]
    rng = random.Random(seed)
    top_y = 8
    box(p, 0, top_y, w, 7, wd["top"], wd["line"], top=wd["hi"], top_h=2)
    box(p, 3, top_y + 7, w - 6, h - top_y - 7, wd["face"], wd["line"])
    box(p, w - 20, top_y + 8, 16, h - top_y - 11, wd["top"], wd["dark"], shade=False)
    handle(p, w - 13, top_y + 10)
    box(p, w - 20, top_y + 8, 16, 7, wd["top"], wd["dark"], shade=False)
    handle(p, w - 13, top_y + 11)
    for lx in (4, w - 7):
        p.rect(lx, h - 4, 3, 4, wd["line"])
    if items:
        box(p, 5, 2, 12, 7, C("#4a5a68"), OL)                           # laptop/monitor
        p.rect(7, 3, 8, 4, C("#7fd0e8"))
        p.rect(20, 5, 7, 4, C("#f0ead8")); p.hline(21, 6, 5, C("#9a9488"))   # papers
        p.rect(31, 4, 4, 5, C("#c75a4a")); p.frame(31, 4, 4, 5, OL)          # mug
        p.rect(38, 6, 6, 3, rng.choice(BOOKS)); p.rect(38, 4, 5, 2, rng.choice(BOOKS))
    return p


def lowcab(w, h, wood):
    p = Pix(w, h)
    wd = WOOD[wood]
    box(p, 0, 0, w, h, wd["face"], wd["line"], top=wd["top"], top_h=4)
    third = (w - 4) // 3
    for i in range(3):
        box(p, 2 + i * third, 6, third - 1, h - 10, wd["top"], wd["dark"], shade=False)
        handle(p, 2 + i * third + third // 2 - 1, 6 + (h - 10) // 2 - 1)
    for lx in (2, w - 4):
        p.rect(lx, h - 3, 2, 3, wd["line"])
    return p


def bench(w, h, wood):
    p = Pix(w, h)
    wd = WOOD[wood]
    box(p, 0, 0, w, 7, wd["top"], wd["line"], top=wd["hi"], top_h=2)
    for lx in (2, w - 5):
        p.rect(lx, 7, 3, h - 7, wd["line"]); p.vline(lx + 1, 7, h - 8, wd["dark"])
    p.hline(5, 9, w - 10, wd["dark"])
    return p


def narrow(w, h, wood, seed=2, tall=False):
    p = Pix(w, h)
    wd = WOOD[wood]
    if tall:
        box(p, 0, 0, w, h, wd["face"], wd["line"], top=wd["top"], top_h=3)
        box(p, 2, 6, w - 4, 18, wd["top"], wd["dark"], shade=False); handle(p, w - 5, 14)
        box(p, 2, 26, w - 4, h - 31, wd["top"], wd["dark"], shade=False); handle(p, w - 5, 33)
        p.rect(2, h - 3, 2, 3, wd["line"]); p.rect(w - 4, h - 3, 2, 3, wd["line"])
        return p
    return shelf(w, h, wood, seed)


# =================================================================== kitchen
def counter_top(p, x, y, w, col):
    p.rect(x, y, w, 5, col)
    p.hline(x, y, w, lit(col, 0.5))
    p.hline(x, y + 4, w, dim(col, 0.3))


def counter(w, h, wood, top):
    """base cabinets with drawers and doors, counter top on the upper rows."""
    p = Pix(w, h)
    wd = WOOD[wood]
    counter_top(p, 0, 0, w, top)
    p.frame(0, 0, w, 5, wd["line"])
    box(p, 0, 5, w, h - 5, wd["face"], wd["line"])
    n = max(2, w // 32)
    cw = w // n
    for i in range(n):
        x0 = i * cw + 2
        if i % 2 == 0:
            for k in range(3):
                box(p, x0, 7 + k * 5, cw - 5, 4, wd["top"], wd["dark"], shade=False)
                p.hline(x0 + (cw - 5) // 2 - 1, 8 + k * 5, 3, C("#8a7a68"))
        else:
            half = (cw - 5) // 2
            box(p, x0, 7, half, h - 10, wd["top"], wd["dark"], shade=False)
            box(p, x0 + half, 7, cw - 5 - half, h - 10, wd["top"], wd["dark"], shade=False)
            handle(p, x0 + half - 2, 11); handle(p, x0 + half + 1, 11)
    p.hline(1, h - 2, w - 2, dim(wd["face"], 0.5))
    return p


def wall_cabs(w, h, wood):
    p = Pix(w, h)
    wd = WOOD[wood]
    box(p, 0, 0, w, h - 2, wd["face"], wd["line"], top=wd["top"], top_h=2)
    p.hline(0, h - 1, w, dim(wd["face"], 0.5))
    n = max(2, w // 32)
    cw = w // n
    for i in range(n):
        x0 = i * cw + 2
        half = (cw - 5) // 2
        box(p, x0, 4, half, h - 9, wd["top"], wd["dark"], shade=False)
        box(p, x0 + half, 4, cw - 5 - half, h - 9, wd["top"], wd["dark"], shade=False)
        handle(p, x0 + half - 2, h - 10); handle(p, x0 + half + 1, h - 10)
    return p


def kitchen_run(w, h, wood, top, sink=True):
    p = Pix(w, h)
    wd = WOOD[wood]
    wall = C("#e8dfc4") if wood != "grey" else C("#cfd3d8")
    p.rect(0, 0, w, 13, wall)
    for yy in (4, 8, 12):
        p.hline(0, yy, w, dim(wall, 0.12))
    for xx in range(0, w, 6):
        p.vline(xx, 0, 13, dim(wall, 0.08))
    p.hline(0, 0, w, wd["line"])
    base = counter(w, h - 13, wood, top)
    p.paste(base, 0, 13)
    if sink:
        sx = w // 3
        p.rect(sx, 8, 22, 6, C("#9aa4ae")); p.frame(sx, 8, 22, 6, OL)
        p.rect(sx + 2, 10, 18, 3, C("#6f7c88")); p.hline(sx + 2, 10, 18, C("#b9c3cc"))
        p.vline(sx + 11, 2, 7, C("#cfd6dc")); p.hline(sx + 11, 2, 4, C("#cfd6dc")); p.p(sx + 14, 3, C("#8a949e"))
    return p


def sink_top(w, h, top, steel):
    p = Pix(w, h)
    counter_top(p, 0, 0, w, top)
    p.frame(0, 0, w, 5, OL)
    p.rect(0, 5, w, h - 5, dim(top, 0.2))
    p.frame(0, 5, w, h - 5, OL)
    p.rect(6, 1, w - 12, h - 4, steel); p.frame(6, 1, w - 12, h - 4, OL)
    p.rect(8, 3, w - 16, h - 8, dim(steel, 0.18)); p.hline(8, 3, w - 16, lit(steel, 0.4))
    p.vline(w // 2, 0, 3, C("#d6dde2")); p.p(w // 2 + 1, 0, C("#d6dde2"))
    return p


def stove(w, h, wood, lit_oven=False, grey=False):
    p = Pix(w, h)
    body = C("#8b8f98") if grey else C("#6d3f54")
    if not grey:
        body = C("#7b4a5e")
    box(p, 0, 0, w, 10, dim(body, 0.35), OL)                            # backsplash
    for bx in (6, 20):
        p.ell(bx, 2, 7, 5, C("#25222a"), OL); p.ell(bx + 2, 3, 3, 2, C("#c0452c"))
    box(p, 0, 10, w, h - 10, body, OL, top=lit(body, 0.2), top_h=2)
    p.hline(2, 13, w - 4, lit(body, 0.4))
    for kx in (5, 11, 17, 23):
        p.rect(kx, 15, 2, 2, C("#e8d9a8"))
    box(p, 3, 19, w - 6, h - 25, dim(body, 0.45), OL)
    glow = C("#f08a24") if lit_oven else C("#3a2f36")
    p.rect(5, 21, w - 10, h - 30, glow)
    if lit_oven:
        p.rect(7, h - 14, w - 14, 3, C("#ffd25a")); p.hline(5, 21, w - 10, C("#ffb44a"))
    if not lit_oven:
        p.hline(5, 21, w - 10, lit(glow, 0.3))
    p.hline(5, 18, w - 10, C("#e8d9a8"))
    p.rect(3, h - 4, w - 6, 3, dim(body, 0.5))
    return p


def fridge(w, h, steel=False, open_=False):
    p = Pix(w, h)
    col = C("#9aa0aa") if steel else C("#f1f3f4")
    shade = dim(col, 0.2)
    bw = 24 if not steel else 32
    if steel and open_:
        bw = 32
    elif not steel and open_:
        bw = 24
    box(p, 0, 0, bw, h - 2, col, C("#3b4048"))
    p.vline(2, 3, h - 8, lit(col, 0.5))
    split = 20 if not steel else 24
    p.hline(1, split, bw - 2, shade)
    if steel:
        p.vline(bw // 2, 2, h - 6, shade)
        p.rect(bw // 2 - 8, 8, 4, 8, C("#2f343c")); p.rect(bw // 2 - 7, 9, 2, 5, C("#79c4e0"))
        p.rect(bw // 2 - 2, 30, 2, 12, C("#d6dae0")); p.rect(bw // 2 + 1, 30, 2, 12, C("#d6dae0"))
    else:
        p.rect(bw - 6, 7, 2, 9, C("#8a9098")); p.rect(bw - 6, 25, 2, 14, C("#8a9098"))
    p.rect(1, h - 4, bw - 2, 2, shade)
    if open_:
        dx = bw
        iw = (w - bw)
        box(p, dx - 2, 3, iw + 2, h - 8, C("#dfe6e9"), C("#3b4048"))
        for yy in range(10, h - 10, 11):
            p.hline(dx, yy, iw - 2, C("#a9c4cc"))
        p.rect(dx + 2, 5, 3, 3, C("#d9704a")); p.rect(dx + 2, 21, 4, 3, C("#74b25a"))
    return p


# =================================================================== electronics
def tv(on):
    p = Pix(36, 20)
    box(p, 0, 0, 36, 17, C("#2c2f38"), OL)
    scr = C("#7ad0e8") if on else C("#11151c")
    p.rect(2, 2, 32, 13, scr)
    if on:
        for i in range(0, 32, 4):
            p.vline(2 + i, 2, 13, lit(scr, 0.15) if (i // 4) % 2 else scr)
        p.rect(6, 5, 10, 6, C("#f2c14e")); p.rect(20, 4, 9, 8, C("#e8664a"))
    else:
        p.hline(3, 3, 12, C("#2a3140")); p.p(4, 4, C("#2a3140"))
    p.rect(14, 17, 8, 2, C("#1d2027")); p.rect(10, 19, 16, 1, C("#1d2027"))
    return p


def soundbar():
    p = Pix(32, 6)
    box(p, 0, 0, 32, 6, C("#30343e"), OL)
    for xx in range(3, 29, 3):
        p.p(xx, 3, C("#6a7080"))
    p.p(28, 2, C("#6ee08a"))
    return p


def speaker():
    p = Pix(10, 32)
    box(p, 0, 0, 10, 28, C("#3a3d46"), OL)
    p.ell(2, 3, 6, 6, C("#20232a"), OL); p.p(4, 5, C("#8a90a0"))
    p.ell(1, 12, 8, 8, C("#20232a"), OL); p.ell(3, 14, 4, 4, C("#555b6a"))
    p.rect(1, 28, 2, 4, OL); p.rect(7, 28, 2, 4, OL)
    return p


# =================================================================== doors & windows
def door(w, h, kind, wood="brown"):
    p = Pix(w, h)
    wd = WOOD[wood]
    frame_c = wd["dark"]
    if kind == "black":
        box(p, 0, 0, w, h, frame_c, wd["line"])
        p.rect(3, 3, w - 6, h - 3, C("#0b0b10"))
        p.hline(3, 3, w - 6, C("#000000"))
        return p
    if kind == "closed":
        box(p, 0, 0, w, h, frame_c, wd["line"])
        p.rect(3, 3, w - 6, h - 3, wd["face"])
        for (x0, y0, ww, hh) in ((5, 5, w - 10, 16), (5, 24, w - 10, h - 28)):
            box(p, x0, y0, ww, hh, wd["top"], wd["dark"], shade=False)
            p.frame(x0 + 2, y0 + 2, ww - 4, hh - 4, wd["face"])
        p.rect(w - 8, h // 2, 3, 3, C("#f0d890")); p.p(w - 8, h // 2, C("#ffffff"))
        return p
    box(p, 0, 0, w, h - 3, frame_c, wd["line"])                          # open
    p.rect(3, 3, w - 6, h - 6, C("#17131a"))
    p.rect(w - 10, 4, 7, h - 9, C("#2a2430"))
    d = ImageDraw.Draw(p.im)
    d.polygon([(3, 3), (3, h - 6), (11, h - 9), (11, 7)], fill=wd["face"], outline=wd["line"])
    p.rect(8, h // 2 - 3, 2, 2, C("#f0d890"))
    p.rect(2, h - 4, w - 4, 4, wd["dark"]); p.hline(2, h - 4, w - 4, wd["line"])
    return p


def window(w, h, kind, frame=C("#8b5a3a")):
    p = Pix(w, h)
    lite = frame
    p.rect(0, 0, w, h, frame); p.frame(0, 0, w, h, dim(frame, 0.6))
    gx, gy, gw, gh = 3, 3, w - 6, h - 6
    half = (gw - 2) // 2
    for i in range(2):
        x0 = gx + i * (half + 2)
        if kind == "night":
            for yy in range(gh):
                p.hline(x0, gy + yy, half, mix(C("#1d2a5a"), C("#3b4f8f"), yy / max(1, gh)))
            p.p(x0 + 3, gy + 3, C("#ffffff")); p.p(x0 + half - 4, gy + 6, C("#ffe9a0")); p.p(x0 + 5, gy + gh - 6, C("#ffffff"))
            if i == 1:
                p.ell(x0 + half - 8, gy + 2, 5, 5, C("#f4eec8"))
        else:
            for yy in range(gh):
                p.hline(x0, gy + yy, half, mix(C("#a5e0f0"), C("#d8f4f8"), yy / max(1, gh)))
            p.hline(x0 + 2, gy + 3, 5, C("#ffffff")); p.hline(x0 + 4, gy + 2, 4, C("#ffffff"))
            p.hline(x0 + half - 8, gy + gh - 6, 6, C("#ffffff"))
            for k in range(3):                                           # glass glint
                p.p(x0 + 2 + k, gy + gh - 3 - k, C("#ffffff"))
        p.frame(x0, gy, half, gh, dim(frame, 0.5))
    p.hline(1, h - 2, w - 2, dim(frame, 0.3))
    return p


def curtain_window(w, h, cloth):
    p = window(w, h, "day", C("#c6b08a"))
    p.rect(1, 1, 5, h - 2, cloth); p.rect(w - 6, 1, 5, h - 2, cloth)
    for yy in range(2, h - 2, 3):
        p.vline(3, yy, 1, dim(cloth, 0.3)); p.vline(w - 4, yy, 1, dim(cloth, 0.3))
    p.hline(0, 0, w, dim(cloth, 0.5))
    return p


def double_door(w, h):
    p = Pix(w, h)
    wd = WOOD["brown"]
    box(p, 0, 0, w, h, wd["dark"], wd["line"])
    for x0 in (2, w // 2 + 1):
        box(p, x0, 3, w // 2 - 3, h - 4, wd["face"], wd["line"])
        p.rect(x0 + 2, 5, w // 2 - 7, 8, GLASS); p.frame(x0 + 2, 5, w // 2 - 7, 8, wd["line"])
    p.rect(w // 2 - 3, h // 2 + 2, 2, 3, C("#f0d890")); p.rect(w // 2 + 1, h // 2 + 2, 2, 3, C("#f0d890"))
    return p


def steel_door(w, h):
    p = Pix(w, h)
    box(p, 0, 0, w, h, C("#8f98a4"), C("#2d333c"))
    for xx in range(4, w - 3, 6):
        p.vline(xx, 2, h - 4, C("#aab2bd")); p.vline(xx + 1, 2, h - 4, C("#6f7884"))
    p.hline(1, h // 2, w - 2, C("#5d6672"))
    p.rect(w // 2 - 2, h - 8, 4, 4, C("#d0a43c"))
    for xx in (3, w - 4):
        p.p(xx, 3, C("#d6dbe2")); p.p(xx, h - 4, C("#d6dbe2"))
    return p


# =================================================================== fireplaces
def fireplace(brick, burning):
    w, h = 32, 48
    p = Pix(w, h)
    base = C("#9a6a52") if brick else C("#9ea3a8")
    dk = dim(base, 0.3)
    mortar = dim(base, 0.18)
    box(p, 9, 0, 14, 12, base, OL)                                       # chimney
    box(p, 1, 10, w - 2, 5, lit(base, 0.2), OL)                          # mantel
    box(p, 3, 15, w - 6, h - 15, base, OL)
    rng = random.Random(7)
    for yy in range(17, h - 2, 4):                                       # brick / stone courses
        p.hline(4, yy, w - 8, mortar)
        off = rng.randint(0, 5)
        for xx in range(4 + off, w - 4, 7):
            p.vline(xx, yy + 1, 3, mortar)
    for yy in range(2, 12, 4):
        p.hline(10, yy, 12, mortar)
    p.rect(7, 22, w - 14, h - 24, C("#1c1214")); p.frame(7, 22, w - 14, h - 24, OL)
    p.rect(6, 21, w - 12, 1, dk)
    p.rect(7, h - 5, w - 14, 3, C("#3a2b2c"))                            # hearth
    p.rect(9, h - 8, 14, 3, C("#6b4326")); p.rect(11, h - 10, 10, 3, C("#8a5a30"))   # logs
    if burning:
        d = ImageDraw.Draw(p.im)
        d.polygon([(16, 24), (11, h - 9), (21, h - 9)], fill=C("#f08a24"))
        d.polygon([(16, 29), (13, h - 9), (19, h - 9)], fill=C("#ffd25a"))
        p.p(15, 32, C("#fff2b0")); p.p(16, 33, C("#fff2b0"))
    return p


# =================================================================== decor
def lamp_tripod():
    p = Pix(16, 47)
    p.rect(2, 0, 12, 10, C("#f4e1a0")); p.frame(2, 0, 12, 10, C("#a9894a"))
    p.hline(3, 1, 10, C("#fff6cc")); p.vline(7, 1, 9, C("#e6cf84"))
    p.vline(8, 10, 20, C("#4a3a30"))
    d = ImageDraw.Draw(p.im)
    d.line([(8, 30), (2, 46)], fill=OL); d.line([(8, 30), (14, 46)], fill=OL); d.line([(8, 30), (8, 46)], fill=OL)
    p.hline(5, 38, 7, C("#6b5648"))
    return p


def lamp_floor(shade, h=46, w=16):
    p = Pix(w, h)
    cx = w // 2
    sh = min(12, w - 3)
    x0 = cx - sh // 2
    sh_h = 12 if h > 30 else 9
    p.rect(x0, 0, sh, sh_h, shade); p.frame(x0, 0, sh, sh_h, dim(shade, 0.45))
    p.hline(x0 + 1, 1, sh - 2, lit(shade, 0.45)); p.vline(x0 + 3, 2, sh_h - 3, lit(shade, 0.2))
    p.vline(cx, sh_h, h - sh_h - 4, C("#4a4a54")); p.vline(cx - 1, sh_h, h - sh_h - 4, C("#6a6a76"))
    p.ell(cx - 5, h - 5, 10, 5, C("#3a3a44"), OL)
    return p


def lamp_table(shade):
    p = Pix(16, 25)
    p.rect(3, 0, 10, 9, shade); p.frame(3, 0, 10, 9, dim(shade, 0.45)); p.hline(4, 1, 8, lit(shade, 0.45))
    p.rect(7, 9, 2, 8, C("#6a5a4a"))
    p.ell(3, 15, 10, 9, C("#8a6a4a"), OL); p.ell(5, 16, 5, 3, C("#b88e62"))
    return p


def picture(w, h, kind):
    p = Pix(w, h)
    box(p, 0, 0, w, h, C("#7a5238"), OL, shade=False)
    p.rect(2, 2, w - 4, h - 4, C("#3d2a1e"))
    iw, ih = w - 6, h - 6
    if kind == "sunset":
        for yy in range(ih):
            p.hline(3, 3 + yy, iw, mix(C("#f6c04a"), C("#e0603e"), yy / ih) if yy < ih * 0.6 else C("#3d6a8c"))
        p.ell(w // 2 - 3, 4, 7, 7, C("#fff0a8"))
        p.hline(3, 3 + int(ih * 0.6), iw, C("#f7a24a"))
    else:
        for yy in range(ih):
            p.hline(3, 3 + yy, iw, C("#a8dcf0"))
        d = ImageDraw.Draw(p.im)
        d.polygon([(3, h - 3), (10, 6), (17, h - 3)], fill=C("#6aa05a"))
        d.polygon([(12, h - 3), (22, 5), (w - 3, h - 3)], fill=C("#4d8a4a"))
        p.hline(3, h - 4, iw, C("#3c6a38"))
    return p


def mirror_tall():
    p = Pix(16, 46)
    box(p, 0, 0, 16, 42, C("#b08a5a"), OL, shade=False)
    for yy in range(3, 39):
        p.hline(3, yy, 10, mix(C("#cfeaf2"), C("#a6cbd6"), yy / 40))
    for k in range(6):
        p.p(4 + k, 28 - k, C("#ffffff"))
    p.rect(3, 42, 2, 4, OL); p.rect(11, 42, 2, 4, OL)
    return p


def plant(w, h, pot, leaf, kind="leafy"):
    p = Pix(w, h)
    ph = max(7, h // 3)
    px0 = w // 2 - (w // 3)
    pw = (w // 3) * 2 + (w % 2)
    d = ImageDraw.Draw(p.im)
    d.polygon([(px0, h - ph), (px0 + pw - 1, h - ph), (px0 + pw - 2, h - 1), (px0 + 1, h - 1)], fill=pot, outline=dim(pot, 0.5))
    p.hline(px0, h - ph, pw, lit(pot, 0.35))
    p.hline(px0 + 1, h - ph + 1, pw - 2, dim(pot, 0.2))
    rng = random.Random(h * 31 + w)
    cx = w // 2
    top = h - ph - 1
    for _ in range(9):
        ang = rng.uniform(-1.0, 1.0)
        ln = rng.randint(max(4, top // 3), max(5, top - 1))
        ex, ey = cx + int(ang * (w // 2 - 1)), top - ln
        d.line([(cx, top), (ex, ey)], fill=dim(leaf, 0.35))
        d.ellipse((ex - 2, ey - 1, ex + 2, ey + 2), fill=leaf)
        p.p(ex, ey - 1, lit(leaf, 0.4))
    return p


def flowers(w, h, petal, stem=C("#4a8a3c")):
    p = Pix(w, h)
    cx = w // 2
    p.vline(cx, h // 3, h - h // 3 - 5, stem)
    p.rect(max(0, cx - 3), h - 6, min(7, w), 6, C("#c8a070")); p.frame(max(0, cx - 3), h - 6, min(7, w), 6, OL)
    rng = random.Random(w * 7 + h)
    for _ in range(3 if w > 8 else 2):
        fx, fy = rng.randint(1, w - 2), rng.randint(1, h // 2)
        p.rect(fx - 1, fy, 3, 3, petal); p.p(fx, fy + 1, C("#ffe9a0"))
        p.vline(fx, fy + 3, h - fy - 8, stem)
    return p


def clock():
    p = Pix(16, 16)
    p.ell(0, 0, 16, 16, C("#f6f1e4"), OL)
    p.ell(2, 2, 12, 12, C("#fffaf0"))
    p.vline(8, 4, 5, OL); p.hline(8, 8, 3, OL)
    p.p(8, 3, C("#c0452c")); p.p(8, 12, C("#c0452c")); p.p(3, 8, C("#c0452c")); p.p(12, 8, C("#c0452c"))
    return p


# =================================================================== bedroom / school / shop pieces
def bed(blanket, sheet=C("#f4f0e6")):
    p = Pix(41, 33)
    wd = WOOD["brown"]
    box(p, 0, 0, 41, 9, wd["face"], OL, top=wd["top"], top_h=2)          # headboard
    box(p, 3, 7, 35, 10, sheet, OL)                                       # mattress end / pillows
    box(p, 5, 8, 13, 7, lit(sheet, 0.4), dim(sheet, 0.4), shade=False)
    box(p, 23, 8, 13, 7, lit(sheet, 0.4), dim(sheet, 0.4), shade=False)
    box(p, 2, 15, 37, 15, blanket, OL)                                    # blanket
    p.hline(3, 16, 35, lit(blanket, 0.4))
    for xx in range(6, 36, 6):
        p.vline(xx, 19, 8, dim(blanket, 0.15))
    box(p, 0, 27, 41, 6, wd["face"], OL, top=wd["top"], top_h=1)         # footboard
    return p


def wardrobe(w, h, glass=False):
    p = Pix(w, h)
    wd = WOOD["brown"]
    box(p, 0, 0, w, h, wd["face"], OL, top=wd["top"], top_h=3)
    half = (w - 5) // 2
    for x0 in (2, 3 + half):
        box(p, x0, 5, half, h - 9, wd["top"], wd["dark"], shade=False)
        if glass:
            p.rect(x0 + 2, 7, half - 4, h - 13, GLASS); p.frame(x0 + 2, 7, half - 4, h - 13, GLASS_D)
            p.hline(x0 + 3, 8, 3, C("#ffffff"))
        else:
            p.frame(x0 + 2, 7, half - 4, h - 13, wd["face"])
    handle(p, w // 2 - 3, h // 2); handle(p, w // 2 + 2, h // 2)
    for lx in (2, w - 4):
        p.rect(lx, h - 3, 2, 3, OL)
    return p


def vanity(flip):
    p = Pix(28, 30)
    wd = WOOD["white"]
    box(p, 4, 0, 20, 16, C("#9a7550"), OL, shade=False)
    p.rect(6, 2, 16, 12, GLASS); p.frame(6, 2, 16, 12, GLASS_D)
    for k in range(5):
        p.p(8 + k, 10 - k, C("#ffffff"))
    box(p, 0, 15, 28, 15, wd["face"], wd["line"], top=wd["top"], top_h=3)
    box(p, 3, 20, 10, 6, wd["top"], wd["dark"], shade=False); handle(p, 8, 22)
    box(p, 15, 20, 10, 6, wd["top"], wd["dark"], shade=False); handle(p, 20, 22)
    p.rect(20 if not flip else 5, 12, 3, 3, C("#e87a9a"))
    return p


def dresser(w, h, drawers):
    return cabinet(w, h, "brown", drawers=drawers, doors=0) if drawers else cabinet(w, h, "brown", doors=2)


def school_desks(w, h, n):
    p = Pix(w, h)
    wd = WOOD["orange"]
    each = w // n
    for i in range(n):
        x0 = i * each
        box(p, x0, 0, each - 1, 8, wd["top"], OL, top=wd["hi"], top_h=2)
        p.rect(x0 + 1, 8, each - 3, 3, wd["face"])
        box(p, x0 + 3, 12, each - 7, 4, C("#6b6f78"), OL)                 # chair back
        for lx in (x0 + 2, x0 + each - 5):
            p.rect(lx, 11, 2, h - 11, OL)
    return p


def teacher_desk():
    p = Pix(28, 27)
    wd = WOOD["brown"]
    box(p, 0, 6, 28, 7, wd["top"], OL, top=wd["hi"], top_h=2)
    box(p, 2, 13, 24, 14, wd["face"], OL)
    box(p, 4, 15, 9, 10, wd["top"], wd["dark"], shade=False); handle(p, 8, 19)
    box(p, 15, 15, 9, 10, wd["top"], wd["dark"], shade=False); handle(p, 19, 19)
    p.rect(3, 1, 8, 6, C("#e8e2d0")); p.frame(3, 1, 8, 6, OL)           # book
    p.rect(18, 2, 5, 5, C("#3f8a5a")); p.frame(18, 2, 5, 5, OL)         # plant pot
    return p


def globe(tint):
    p = Pix(13, 21)
    p.ell(1, 0, 11, 11, tint, OL)
    p.rect(4, 3, 4, 3, C("#5da05a")); p.rect(7, 6, 3, 3, C("#5da05a")); p.p(3, 7, C("#5da05a"))
    p.p(3, 2, lit(tint, 0.6)); p.p(4, 2, lit(tint, 0.6))
    p.vline(6, 11, 6, C("#8a8a94"))
    p.ell(2, 16, 9, 5, C("#6a4a30"), OL)
    return p


def chalkboard():
    p = Pix(28, 23)
    box(p, 0, 0, 28, 20, C("#9a7550"), OL, shade=False)
    p.rect(2, 2, 24, 16, C("#2f4a40"))
    p.hline(5, 6, 10, C("#e8e8e0")); p.hline(5, 9, 14, C("#e8e8e0")); p.hline(5, 12, 8, C("#e8e8e0"))
    p.rect(2, 18, 24, 2, C("#6a4a30"))
    p.rect(8, 17, 4, 1, C("#f4f0e0"))
    p.rect(4, 20, 2, 3, OL); p.rect(22, 20, 2, 3, OL)
    return p


def board_wall():
    p = Pix(26, 13)
    box(p, 0, 0, 26, 13, C("#c0a070"), OL, shade=False)
    p.rect(2, 2, 22, 9, C("#e0c890"))
    p.rect(4, 3, 5, 4, C("#f8f4e8")); p.rect(11, 4, 5, 4, C("#f4d86a")); p.rect(18, 3, 4, 5, C("#a8d8e8"))
    p.p(6, 3, C("#c0452c")); p.p(13, 4, C("#c0452c")); p.p(20, 3, C("#c0452c"))
    return p


def locker():
    p = Pix(32, 44)
    col = C("#5b82b8")
    box(p, 0, 0, 32, 44, col, C("#27406a"), top=lit(col, 0.2), top_h=2)
    for x0 in (2, 17):
        box(p, x0, 4, 13, 36, lit(col, 0.08), C("#27406a"), shade=False)
        for yy in (8, 11, 14):
            p.hline(x0 + 3, yy, 7, C("#27406a"))
        p.rect(x0 + 10, 24, 2, 4, C("#d6dae0"))
    p.hline(2, 41, 28, dim(col, 0.4))
    return p


def whiteboard_stand():
    p = Pix(34, 54)
    box(p, 0, 0, 34, 32, C("#9aa0aa"), C("#3a3f48"), shade=False)
    p.rect(2, 2, 30, 28, C("#f8f8f6"))
    p.hline(5, 8, 16, C("#5a7ac0")); p.hline(5, 13, 22, C("#c0452c")); p.hline(5, 18, 12, C("#3a8a5a")); p.hline(5, 23, 18, C("#5a7ac0"))
    p.rect(2, 30, 30, 2, C("#6a707a"))
    p.rect(15, 32, 4, 18, C("#6a707a"))
    d = ImageDraw.Draw(p.im)
    d.line([(17, 50), (6, 53)], fill=C("#3a3f48")); d.line([(17, 50), (28, 53)], fill=C("#3a3f48")); d.line([(17, 50), (17, 53)], fill=C("#3a3f48"))
    return p


def store_rack(w, h, seed):
    p = Pix(w, h)
    rng = random.Random(seed)
    wd = WOOD["white"]
    box(p, 0, 0, w, h, wd["face"], wd["line"], top=wd["top"], top_h=2)
    lv = 2 if h < 40 else 3
    lh = (h - 4) // lv
    goods = [C("#e0684a"), C("#e8c04a"), C("#6ab04a"), C("#5a90d0"), C("#d890c0")]
    for i in range(lv):
        y0 = 3 + i * lh
        p.rect(2, y0, w - 4, lh - 2, dim(wd["dark"], 0.2))
        xx = 3
        while xx < w - 6:
            gw = rng.choice((4, 5, 6)); gh = rng.randint(lh - 7, lh - 4)
            col = rng.choice(goods)
            p.rect(xx, y0 + lh - 2 - gh, gw, gh, col); p.hline(xx, y0 + lh - 2 - gh, gw, lit(col, 0.5))
            xx += gw + 1
        p.hline(1, y0 + lh - 2, w - 2, wd["top"]); p.hline(1, y0 + lh - 1, w - 2, wd["dark"])
    return p


def crate(w, h):
    p = Pix(w, h)
    wd = WOOD["orange"]
    box(p, 0, 0, w, h, wd["face"], OL)
    for yy in range(3, h - 2, 4):
        p.hline(1, yy, w - 2, wd["dark"])
    p.rect(0, 0, 3, h, wd["dark"]); p.rect(w - 3, 0, 3, h, wd["dark"]); p.frame(0, 0, w, h, OL)
    p.hline(3, 1, w - 6, wd["hi"])
    return p


def palm_pot():
    p = Pix(23, 31)
    d = ImageDraw.Draw(p.im)
    p.rect(9, 12, 4, 12, C("#8a5a34")); p.vline(10, 12, 12, C("#b07844"))
    for ex, ey in ((2, 6), (6, 2), (11, 1), (17, 3), (21, 8), (4, 11), (19, 12)):
        d.line([(11, 12), (ex, ey)], fill=C("#2f6a34"))
        d.ellipse((ex - 2, ey - 1, ex + 2, ey + 2), fill=C("#4c9a48"))
    p.ell(11 - 2, 11, 5, 4, C("#6a4426"))
    box(p, 5, 23, 13, 8, C("#b8653a"), OL, top=C("#d98a5a"), top_h=1)
    return p


def pot_plant(w, h, pot, leaf):
    return plant(w, h, pot, leaf)


def mirror_stand():
    p = Pix(34, 21)
    box(p, 3, 0, 28, 17, C("#a47a50"), OL, shade=False)
    p.rect(5, 2, 24, 13, GLASS); p.frame(5, 2, 24, 13, GLASS_D)
    for k in range(7):
        p.p(8 + k, 12 - k, C("#ffffff"))
    p.rect(5, 17, 3, 4, OL); p.rect(26, 17, 3, 4, OL)
    return p


def world_map():
    p = Pix(7, 4)
    p.rect(0, 0, 7, 4, C("#e8d9a8")); p.frame(0, 0, 7, 4, C("#6a4a30"))
    p.rect(1, 1, 2, 2, C("#6aa05a")); p.rect(4, 1, 2, 1, C("#6aa05a")); p.p(5, 2, C("#5a90d0"))
    return p


# =================================================================== wall & floor patches (tile in x)
def wall_patch(col, trim, panel=False):
    p = Pix(48, 28)
    p.rect(0, 0, 48, 28, col)
    if panel:
        for xx in range(0, 48, 12):
            p.vline(xx, 0, 22, dim(col, 0.22)); p.vline(xx + 1, 0, 22, lit(col, 0.18))
        p.hline(0, 3, 48, lit(col, 0.2)); p.hline(0, 4, 48, dim(col, 0.12))
    else:
        for yy in range(2, 22, 6):
            for xx in range(0, 48, 4):
                p.p((xx + (yy // 6) * 2) % 48, yy, dim(col, 0.07))
        p.hline(0, 0, 48, lit(col, 0.3))
    p.hline(0, 22, 48, lit(trim, 0.3))                                    # skirting / dado rail
    p.rect(0, 23, 48, 4, trim)
    p.hline(0, 24, 48, lit(trim, 0.2))
    p.hline(0, 27, 48, dim(trim, 0.35))
    return p


def floor_wood(col):
    p = Pix(32, 32)
    p.rect(0, 0, 32, 32, col)
    rng = random.Random(int(sum(col[:3])))
    for r in range(4):
        y0 = r * 8
        p.hline(0, y0, 32, dim(col, 0.22))
        p.hline(0, y0 + 1, 32, lit(col, 0.12))
        off = rng.choice((0, 8, 16, 24))
        p.vline(off % 32, y0, 8, dim(col, 0.22))
        p.vline((off + 16) % 32, y0 + 8 if r < 3 else y0, 8 if r < 3 else 0, dim(col, 0.22))
        for _ in range(3):
            p.hline(rng.randint(0, 28), y0 + rng.randint(3, 6), rng.randint(2, 4), dim(col, 0.08))
    return p


def floor_tile(col):
    p = Pix(32, 32)
    p.rect(0, 0, 32, 32, col)
    for q in range(4):
        x0, y0 = (q % 2) * 16, (q // 2) * 16
        p.frame(x0, y0, 16, 16, dim(col, 0.22))
        p.rect(x0 + 1, y0 + 1, 14, 1, lit(col, 0.18)); p.rect(x0 + 1, y0 + 1, 1, 14, lit(col, 0.12))
        if (q + (q // 2)) % 2 == 0:
            p.rect(x0 + 3, y0 + 3, 10, 10, dim(col, 0.06))
    return p


# =================================================================== registry: name -> sprite
BEIGE, GREY_S, RED_S = C("#d8c3a0"), C("#9aa1ae"), C("#b8453c")
SHADE_COL = {"a": C("#f4e1a0"), "b": C("#e8b0a0")}


def interiors():
    R = {}
    # --- living room
    R["sofa_beige"] = sofa(48, 32, BEIGE); R["sofa_beige_back"] = sofa(48, 32, BEIGE, "back")
    R["sofa_beige_l"] = sofa(31, 48, BEIGE, "l"); R["sofa_beige_r"] = sofa(31, 48, BEIGE, "r")
    R["sofa_grey"] = sofa(48, 32, GREY_S); R["sofa_grey_back"] = sofa(48, 32, GREY_S, "back")
    R["armchair_beige"] = armchair(32, 32, BEIGE); R["armchair_beige_back"] = armchair(32, 32, BEIGE, "back")
    R["armchair_grey"] = armchair(32, 32, GREY_S); R["armchair_grey_back"] = armchair(32, 32, GREY_S, "back")
    R["sofa_red"] = sofa(48, 26, RED_S)
    for n, b, lt in (("fireplace_stone", False, False), ("fireplace_stone_lit", False, True),
                     ("fireplace_brick", True, False), ("fireplace_brick_lit", True, True)):
        R[n] = fireplace(b, lt)
    R["table_brown_h"] = table(48, 32, "brown"); R["table_brown_v"] = table_v(28, 48, "brown")
    for d in ("back", "front", "l", "r"):
        R["chair_brown_" + {"back": "back", "front": "front", "l": "l", "r": "r"}[d]] = chair(16, 25 if d == "front" else 32, d, "brown")
    R["chair_white_back"] = chair(16, 32, "back", "white"); R["chair_white_front"] = chair(16, 25, "front", "white")
    R["table_round_white"] = table(32, 32, "white", True); R["table_round_brown"] = table(32, 32, "brown", True)
    R["coffee_table"] = table(32, 16, "brown"); R["stool_a"] = stool(C("#b98a5a")); R["stool_b"] = stool(C("#7f9fb8"))
    R["rug_white_h"] = rug(64, 32, C("#f1ece0"), C("#cfc6b2"), "weave", True); R["rug_white_v"] = rug(32, 64, C("#f1ece0"), C("#cfc6b2"), "weave", True)
    R["rug_dots_h"] = rug(64, 32, C("#9bb8c8"), C("#6f8ea2"), "dots")
    R["rug_red_h"] = rug(64, 32, C("#a8453e"), C("#6f2a2a"), "diamond", True); R["rug_red_v"] = rug(32, 64, C("#a8453e"), C("#6f2a2a"), "diamond", True)
    R["rug_red2_h"] = rug(64, 32, C("#b5584a"), C("#7a3a30"), "stripes", True)
    R["runner_white"] = runner(64, 16, C("#f1ece0"), C("#cfc6b2")); R["runner_olive"] = runner(64, 16, C("#a4a864"), C("#6f7440"))
    R["rug_round_white"] = rug(48, 32, C("#f1ece0"), C("#cfc6b2"), round_=True); R["rug_round_small"] = rug(32, 26, C("#d9a066"), C("#a8703c"), round_=True)
    R["rug_round_grey"] = rug(48, 32, C("#b9bec8"), C("#8a909c"), round_=True)
    R["tv_off"], R["tv_on"] = tv(False), tv(True)
    R["soundbar"] = soundbar(); R["speaker_l"] = speaker(); R["speaker_r"] = speaker()
    # --- kitchen
    R["fridge_white"] = fridge(24, 56); R["fridge_white_open"] = fridge(28, 56, open_=True)
    R["fridge_steel"] = fridge(32, 61, True); R["fridge_steel_open"] = fridge(51, 61, True, True)
    R["kitchen_run_sink"] = kitchen_run(121, 47, "cream", C("#d8c9a0")); R["kitchen_run_sink_olive"] = kitchen_run(121, 47, "cream", C("#a4a864"))
    R["kitchen_run_end"] = kitchen_run(32, 42, "cream", C("#d8c9a0"), sink=False)
    R["stove"] = stove(32, 42, "brown"); R["stove_lit"] = stove(32, 42, "brown", True); R["stove_grey_lit"] = stove(32, 42, "grey", True, True)
    R["sink_a"] = sink_top(32, 16, C("#d8c9a0"), C("#a9b2bc")); R["sink_b"] = sink_top(32, 16, C("#e8e0cc"), C("#8fa8b8")); R["sink_grey"] = sink_top(32, 16, C("#b8bcc4"), C("#a9b2bc"))
    R["counter_row"] = counter(128, 23, "cream", C("#d8c9a0")); R["counter_row_grey"] = counter(128, 23, "grey", C("#d4d7dc"))
    R["wall_cabinets"] = wall_cabs(128, 23, "cream"); R["wall_cabinets_grey"] = wall_cabs(128, 23, "grey")
    # --- cabinets & storage (a/b = brown wood, w = white, wc = cream)
    R["bookcase_a"] = bookcase(48, 48, "brown", False, 1); R["bookcase_doors"] = bookcase(48, 48, "brown", True, 1)
    R["bookcase_color"] = bookcase(48, 48, "teal", False, 2); R["bookcase_color_doors"] = bookcase(48, 48, "teal", True, 2)
    R["bookcase_w"] = bookcase(48, 48, "white", False, 3); R["bookcase_w_doors"] = bookcase(48, 48, "white", True, 3)
    R["bookcase_wc"] = bookcase(48, 48, "cream", False, 4); R["bookcase_wc_doors"] = bookcase(48, 48, "cream", True, 4)
    R["cabinet_tall"] = narrow(16, 48, "brown", tall=True)
    R["sideboard_a"] = cabinet(48, 45, "brown", 2, top_items=True, seed=1); R["sideboard_b"] = cabinet(48, 45, "brown", 0, 3)
    R["sideboard_w"] = cabinet(48, 45, "white", 2, top_items=True, seed=2); R["sideboard_wc"] = cabinet(48, 45, "cream", 2, top_items=True, seed=3)
    R["shelf_a"] = shelf(48, 34, "brown", 1); R["shelf_b"] = shelf(48, 34, "brown", 5)
    R["shelf_w"] = shelf(48, 34, "white", 2); R["shelf_wc"] = shelf(48, 34, "cream", 3)
    R["desk_items"] = desk(48, 25, "brown", True); R["desk_b"] = desk(48, 25, "brown"); R["desk_w"] = desk(48, 25, "white"); R["desk_wc"] = desk(48, 25, "cream")
    R["lowcab_a"] = lowcab(48, 25, "brown"); R["lowcab_b"] = lowcab(48, 25, "orange"); R["lowcab_w"] = lowcab(48, 25, "white")
    R["bench_a"] = bench(48, 14, "brown")
    R["cabinet_big"] = cabinet(48, 48, "brown", 2); R["cabinet_big_w"] = cabinet(48, 48, "white", 2)
    R["cabinet_wide"] = cabinet(48, 45, "brown", 3); R["cabinet_wide_w"] = cabinet(48, 45, "white", 3)
    R["cabinet_mid"] = cabinet(48, 34, "brown", 2)
    R["narrow_shelf"] = narrow(16, 34, "brown", 4)
    # --- doors & windows
    R["doorway_black"] = door(30, 48, "black"); R["door_closed"] = door(30, 48, "closed"); R["door_open"] = door(30, 51, "open")
    R["window_day"] = window(48, 30, "day"); R["window_night"] = window(48, 30, "night")
    R["window_red"] = curtain_window(25, 20, C("#c0453a")); R["window_white"] = curtain_window(25, 20, C("#f2eee4"))
    R["window_sky"] = window(28, 21, "day", C("#6f8ea8"))
    R["door_double"] = double_door(32, 28); R["steel_door"] = steel_door(64, 25)
    # --- decor
    R["lamp_tripod"] = lamp_tripod(); R["lamp_floor_a"] = lamp_floor(C("#f4e1a0")); R["lamp_floor_b"] = lamp_floor(C("#a8cfd8"))
    R["lamp_table_a"] = lamp_table(C("#f4e1a0")); R["lamp_table_b"] = lamp_table(C("#e8b0a0"))
    R["picture_sunset"] = picture(32, 16, "sunset"); R["picture_hills"] = picture(32, 16, "hills")
    R["mirror_tall"] = mirror_tall(); R["mirror_stand"] = mirror_stand()
    R["plant_red_pot"] = plant(15, 30, C("#b8453c"), C("#4c9a48")); R["plant_fern_pot"] = plant(16, 31, C("#d9b46a"), C("#2f7a3c"))
    R["plant_grey_pot"] = plant(16, 31, C("#9aa1ae"), C("#5aa04a")); R["plant_small"] = plant(16, 16, C("#c8803f"), C("#5aa04a"))
    R["plant_pot_tall"] = plant(14, 23, C("#a86a44"), C("#3f8a3c")); R["plant_pot_small"] = plant(12, 14, C("#c8803f"), C("#5aa04a"))
    R["flowers_pink"] = flowers(13, 19, C("#e8789a")); R["flowers_blue"] = flowers(7, 17, C("#5a90e0"))
    R["clock"] = clock(); R["palm"] = palm_pot(); R["world_map"] = world_map()
    # --- bedroom / school / shop
    R["bed_blue"] = bed(C("#4f7fc0")); R["bed_white"] = bed(C("#e8e4da"))
    R["table_orange"] = table(41, 40, "orange"); R["table_light"] = table(41, 40, "cream")
    R["bench_orange"] = bench(38, 21, "orange")
    R["bookshelf_wood_a"] = bookcase(32, 35, "orange", False, 6); R["bookshelf_wood_b"] = bookcase(34, 32, "brown", False, 7)
    R["rug_red_gold"] = rug(60, 40, C("#a8453e"), C("#d8b04a"), "diamond", True)
    R["rug_blue_gold_v"] = rug(40, 60, C("#3f6fa5"), C("#d8b04a"), "diamond", True); R["rug_red_gold_v"] = rug(40, 60, C("#a8453e"), C("#d8b04a"), "diamond", True)
    R["mat_green"] = mat(24, 18, C("#5a9a5a")); R["mat_red"] = mat(24, 18, C("#b8453c")); R["mat_blue"] = mat(24, 18, C("#4f7fc0")); R["mat_blue2"] = mat(24, 18, C("#6fa8d0"))
    R["mat_small_red"] = mat(16, 16, C("#b8453c"))
    R["store_rack_w"] = store_rack(64, 32, 1); R["store_rack_tall"] = store_rack(21, 31, 2)
    R["store_shelf_a"] = store_rack(96, 34, 3); R["store_shelf_b"] = store_rack(98, 36, 4)
    R["crate_a"] = crate(17, 15); R["crate_b"] = crate(17, 13)
    R["school_desk_row"] = school_desks(66, 23, 3); R["teacher_desk"] = teacher_desk()
    R["globe_a"] = globe(C("#5a90d0")); R["globe_b"] = globe(C("#6ab0b0"))
    R["chalkboard"] = chalkboard(); R["board_wall"] = board_wall(); R["locker_blue"] = locker(); R["whiteboard_stand"] = whiteboard_stand()
    R["wardrobe_a"] = wardrobe(27, 39); R["wardrobe_glass"] = wardrobe(27, 27, True); R["wardrobe_b"] = wardrobe(27, 32)
    R["vanity_a"] = vanity(False); R["vanity_b"] = vanity(True)
    R["dresser_a"] = dresser(25, 21, 3); R["dresser_b"] = dresser(48, 24, 0)
    R["floor_lamp_red"] = lamp_floor(C("#c0453a"), 26, 19)
    R["floor_lamp_blue"] = lamp_floor(C("#5a82c0"), 35, 19); R["floor_lamp_cream"] = lamp_floor(C("#f2e8c8"), 33, 15)
    # --- wall / floor patches
    R["wall_cream"] = wall_patch(C("#f1e6c0"), C("#a98a5a")); R["wall_teal"] = wall_patch(C("#7fb0a8"), C("#e8e0cc"))
    R["wall_white"] = wall_patch(C("#f4f1ea"), C("#b9a98a")); R["wall_pink"] = wall_patch(C("#e8b8b8"), C("#f4eee4"))
    R["wall_sage"] = wall_patch(C("#a8c0a0"), C("#e8e0cc"))
    R["panel_grey"] = wall_patch(C("#a9aeb8"), C("#6f7480"), True); R["panel_orange"] = wall_patch(C("#e0a868"), C("#8a5a30"), True)
    R["panel_brown"] = wall_patch(C("#a8764c"), C("#5a3a28"), True)
    R["floor_wood_light"] = floor_wood(C("#d8aa72")); R["floor_wood_pale"] = floor_wood(C("#e8cfa0")); R["floor_wood_dark"] = floor_wood(C("#8a5a3a"))
    R["floor_tile_light"] = floor_tile(C("#e6e2d8")); R["floor_tile_taupe"] = floor_tile(C("#b8a898")); R["floor_tile_dark"] = floor_tile(C("#5a5e68"))
    return R


# =================================================================== characters (16x32 frames, 24 x 7 sheet)
FRAME_W, FRAME_H = 16, 32
DIR_COL = {"right": 0, "up": 6, "left": 12, "down": 18}
SKIN = C("#f0c8a0")
SKIN_D = C("#d8a47c")
OUTLINE = C("#2e2230")

BODIES = {
    # hair, shirt, pants, shoe, style
    "adam": dict(hair=C("#6b4a2e"), shirt=C("#4a6fa5"), pants=C("#3a3f58"), shoe=C("#2a2430"), style="short", wide=0),
    "alex": dict(hair=C("#2b2b3a"), shirt=C("#b8453c"), pants=C("#4a4a54"), shoe=C("#e8e0d0"), style="spiky", wide=0),
    "amelia": dict(hair=C("#c0703a"), shirt=C("#4a9a6a"), pants=C("#6a4a8a"), shoe=C("#5a3a30"), style="long", wide=0),
    "bob": dict(hair=C("#e0b050"), shirt=C("#6a9a5a"), pants=C("#7a5a3a"), shoe=C("#3a2a24"), style="cap", wide=1),
}


def _outline(img):
    px = img.load()
    w, h = img.size
    marks = []
    for y in range(h):
        for x in range(w):
            if px[x, y][3] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] > 0 and px[nx, ny] != OUTLINE:
                        marks.append((x, y)); break
    for x, y in marks:
        px[x, y] = OUTLINE


def char_frame(body, facing, mode, i):
    b = BODIES[body]
    p = Pix(FRAME_W, FRAME_H)
    ph = i % 6
    if mode == "walk":
        bob = (0, 1, 0, 0, 1, 0)[ph]
        lift = ((0, 0), (1, 0), (0, 0), (0, 0), (0, 1), (0, 0))[ph]
        stride = (0, 2, 2, 0, -2, -2)[ph]
    else:
        bob = 1 if ph in (3, 4) else 0
        lift, stride = (0, 0), 0
    wd = b["wide"]
    cx = 8
    top = 9 + bob                                                   # head top
    hair, shirt, pants, shoe = b["hair"], b["shirt"], b["pants"], b["shoe"]
    side = facing in ("left", "right")
    sx = 1 if facing == "right" else -1

    # legs
    leg_y = 26
    if b["style"] == "long":                                         # skirt + bare legs
        p.rect(cx - 4, 24 + bob, 8, 3, pants); p.hline(cx - 4, 26 + bob, 8, dim(pants, 0.25))
        leg_y = 27
    if side:
        for k, (off, lf) in enumerate(((stride, lift[0]), (-stride, lift[1]))):
            lx = cx - 1 + off
            col = pants if b["style"] != "long" else SKIN
            p.rect(lx, leg_y + bob, 3, 4 - lf - (0 if lf == 0 else 0), col)
            p.rect(lx - (0 if sx > 0 else 1), 30 - lf, 4, 2, shoe)
    else:
        for k, (lx, lf) in enumerate(((cx - 4, lift[0]), (cx, lift[1]))):
            col = pants if b["style"] != "long" else SKIN
            p.rect(lx, leg_y + bob, 3, 4 - lf, col)
            p.rect(lx - 1 + (1 if k else 0), 30 - lf, 4, 2, shoe)

    # torso + arms
    tw = 8 + wd * 2
    tx = cx - tw // 2
    p.rect(tx, 18 + bob, tw, 7, shirt)
    p.hline(tx, 18 + bob, tw, lit(shirt, 0.3))
    p.hline(tx, 24 + bob, tw, dim(shirt, 0.25))
    if b["style"] == "cap":
        p.rect(tx + 1, 21 + bob, tw - 2, 4, C("#5a7ab0")) if not side else None
    arm_sw = (0, 1, 0, 0, -1, 0)[ph] if mode == "walk" else 0
    if side:
        ax = cx - 1 - sx * 0
        p.rect(ax, 19 + bob + arm_sw, 3, 5, dim(shirt, 0.15)); p.rect(ax, 24 + bob + arm_sw, 3, 1, SKIN)
    else:
        p.rect(tx - 1, 19 + bob + arm_sw, 2, 5, dim(shirt, 0.15)); p.rect(tx - 1, 24 + bob + arm_sw, 2, 1, SKIN)
        p.rect(tx + tw - 1, 19 + bob - arm_sw, 2, 5, dim(shirt, 0.15)); p.rect(tx + tw - 1, 24 + bob - arm_sw, 2, 1, SKIN)

    # head
    hw = 10 + wd
    hx = cx - hw // 2
    p.rect(hx, top + 1, hw, 9, SKIN)
    p.rect(hx + 1, top, hw - 2, 1, SKIN)
    p.hline(hx + 1, top + 9, hw - 2, SKIN_D)
    long_ = b["style"] == "long"
    if facing == "down":
        p.rect(hx, top, hw, 4, hair); p.rect(hx + 1, top - 1, hw - 2, 1, hair)
        p.hline(hx + 1, top + 4, 2, hair); p.hline(hx + hw - 3, top + 4, 2, hair)
        p.p(cx - 3, top + 6, OUTLINE); p.p(cx + 2, top + 6, OUTLINE)
        p.p(cx - 3, top + 5, C("#ffffff")) if False else None
        p.hline(cx - 1, top + 8, 2, C("#c0786a"))
        p.p(hx + 1, top + 7, C("#e8a88c")); p.p(hx + hw - 2, top + 7, C("#e8a88c"))
        if long_:
            p.rect(hx - 1, top + 3, 2, 12, hair); p.rect(hx + hw - 1, top + 3, 2, 12, hair)
    elif facing == "up":
        p.rect(hx - (1 if long_ else 0), top, hw + (2 if long_ else 0), 10, hair); p.rect(hx + 1, top - 1, hw - 2, 1, hair)
        p.hline(hx + 1, top + 9, hw - 2, dim(hair, 0.25))
        if long_:
            p.rect(hx, top + 10, hw, 6, hair); p.hline(hx + 1, top + 15, hw - 2, dim(hair, 0.25))
    else:
        fx = hx + hw - 4 if sx > 0 else hx + 3                       # face side
        bx0 = hx if sx > 0 else hx + 4                               # back-of-head hair block
        p.rect(hx, top, hw, 3, hair); p.rect(hx + 1, top - 1, hw - 2, 1, hair)
        p.rect(bx0, top, 6, 8, hair)
        p.p(fx + (1 if sx > 0 else -1), top + 6, OUTLINE)
        p.p(fx + (2 if sx > 0 else -2), top + 7, SKIN_D)
        p.hline(fx - (0 if sx > 0 else -1), top + 8, 2, C("#c0786a"))
        if long_:
            p.rect(bx0, top + 8, 6, 8, hair)
    # style extras
    if b["style"] == "spiky":
        for k in range(0, hw - 1, 3):
            p.p(hx + 1 + k, top - 2, hair)
        p.p(hx + 2, top - 1, hair); p.p(hx + hw - 3, top - 1, hair)
    if b["style"] == "cap":
        capc = C("#c0453a")
        p.rect(hx - 1, top - 1, hw + 2, 4, capc); p.hline(hx, top - 2, hw, capc)
        p.hline(hx - 1, top + 2, hw + 2, dim(capc, 0.3))
        if facing == "down":
            p.hline(hx, top + 3, hw, dim(capc, 0.45))
        elif side:
            p.hline(hx + hw - 1 if sx > 0 else hx - 3, top + 3, 4, dim(capc, 0.45))
    img = p.im
    _outline(img)
    return img


def recolor(sheet, hue_deg):
    """rotate hair/clothes hue, keep skin tones."""
    if hue_deg == 0:
        return sheet.copy()
    a = sheet.load()
    out = sheet.copy()
    o = out.load()
    for y in range(sheet.height):
        for x in range(sheet.width):
            r, g, b, al = a[x, y]
            if al == 0:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hh, ss, vv = int(h * 255), int(s * 255), int(v * 255)
            if 4 <= hh <= 30 and 40 <= ss <= 200 and vv >= 150:
                continue
            h2 = (h + hue_deg / 360) % 1.0
            r2, g2, b2 = colorsys.hsv_to_rgb(h2, s, v)
            o[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255), al)
    return out


def characters():
    HUES = [0, 50, 110, 170, 230, 290]
    for body in BODIES:
        sheet = Image.new("RGBA", (FRAME_W * 24, FRAME_H * 7), (0, 0, 0, 0))
        for facing, c0 in DIR_COL.items():
            for mode, row in (("idle", 1), ("walk", 2)):
                for i in range(6):
                    fr = char_frame(body, facing if facing != "left" else "left", mode, i)
                    sheet.alpha_composite(fr, ((c0 + i) * FRAME_W, row * FRAME_H))
        for i in range(4):                                           # row 0: four standing poses (unused by the game)
            sheet.alpha_composite(char_frame(body, ("down", "up", "left", "right")[i], "idle", 0), (i * FRAME_W, 0))
        for hue in HUES:
            recolor(sheet, hue).save(os.path.join(OUT, "characters", f"{body}_{hue}.png"))


# =================================================================== beach pieces (assets/town/beach_*)
SAND_W = C("#e8c98a")
WATER = [C("#2f7fd0"), C("#4a9ae0"), C("#6cb8f0")]


def blob(w, h, seed, pad=2, lobes=5):
    rng = random.Random(seed)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    cx, cy = w / 2, h / 2
    for _ in range(lobes):
        rx, ry = rng.uniform(w * 0.22, w * 0.36), rng.uniform(h * 0.22, h * 0.36)
        ox, oy = rng.uniform(-w * 0.14, w * 0.14), rng.uniform(-h * 0.14, h * 0.14)
        d.ellipse((cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry), fill=255)
    return m


def tide_pool(w, h, seed, rocky=False):
    p = Pix(w, h)
    m = blob(w, h, seed, lobes=6 if not rocky else 3)
    mp = m.load()
    rng = random.Random(seed + 1)
    inside = lambda x, y: 0 <= x < w and 0 <= y < h and mp[x, y] > 0
    for y in range(h):
        for x in range(w):
            if not inside(x, y):
                continue
            edge = sum(not inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            near = any(not inside(x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3))
            if rocky:
                col = C("#b0743f") if edge else (C("#c98a52") if near else None)
                if col is None:
                    col = WATER[(x + y) % 2] if (x * 3 + y * 5) % 7 else WATER[2]
            else:
                if edge:
                    col = C("#d8b873")
                elif near:
                    col = C("#9fd8f0")
                else:
                    col = WATER[(x // 2 + y) % 2] if (x * 3 + y * 5) % 9 else WATER[2]
            p.p(x, y, col)
    if rocky:
        for _ in range(26):                                          # chunky stones on the rim
            x, y = rng.randint(0, w - 2), rng.randint(0, h - 2)
            if inside(x, y) and p.get(x, y) in (C("#b0743f"), C("#c98a52")):
                p.rect(x, y, 2, 2, rng.choice((C("#c98a52"), C("#9a6232"), C("#dba46a"))))
    return p


def rock(w, h, seed):
    p = Pix(w, h)
    rng = random.Random(seed)
    d = ImageDraw.Draw(p.im)
    d.ellipse((0, 3, w - 1, h - 1), fill=C("#b0743f"), outline=C("#7a4a28"))
    d.ellipse((2, 1, w - 4, h - 5), fill=C("#c98a52"))
    p.rect(3, 3, rng.randint(3, 5), 2, C("#e8b07a"))
    p.hline(2, h - 3, w - 4, C("#8a5530"))
    return p


def palm(w, h, lean):
    p = Pix(w, h)
    d = ImageDraw.Draw(p.im)
    base_x = w // 2 + lean
    pts = []
    for t in range(0, h - 14):
        x = base_x - int(lean * 2 * t / (h - 14)) + (1 if t % 5 == 0 else 0) * 0
        pts.append((x, h - 6 - t))
    for k, (x, y) in enumerate(pts):
        p.rect(x - 1, y, 3, 1, C("#9a6a3c") if k % 4 else C("#7a4e2a"))
    tx, ty = pts[-1]
    for ex, ey in ((tx - 13, ty + 4), (tx - 9, ty - 4), (tx, ty - 7), (tx + 9, ty - 4), (tx + 13, ty + 4), (tx - 6, ty + 8), (tx + 6, ty + 8)):
        d.line([(tx, ty), (ex, ey)], fill=C("#2c6a30"), width=2)
        d.line([(tx, ty - 1), (ex, ey - 1)], fill=C("#4c9a48"))
    p.ell(tx - 2, ty, 5, 4, C("#6a4426"))
    p.ell(w // 2 - 7 + lean, h - 6, 14, 6, C("#d8ae6a"))
    p.ell(w // 2 - 5 + lean, h - 5, 10, 4, C("#e8c98a"))
    p.rect(base_x - 1, h - 8, 3, 3, C("#8a5a30"))
    return p


def sprout():
    p = Pix(16, 29)
    d = ImageDraw.Draw(p.im)
    for ex, ey, c in ((2, 6, "#3f8a3c"), (13, 5, "#3f8a3c"), (5, 1, "#5aa04a"), (10, 2, "#5aa04a"), (8, 0, "#6ab45a")):
        d.line([(8, 24), (ex, ey)], fill=C(c), width=2)
    p.ell(5, 23, 7, 5, C("#d8ae6a"))
    p.rect(7, 22, 3, 3, C("#8a5a30"))
    return p


def flower(seed):
    p = Pix(16, 16)
    rng = random.Random(seed)
    cols = [C("#e0453a"), C("#e8789a"), C("#f2c14e")]
    for _ in range(rng.randint(2, 3)):
        x, y = rng.randint(2, 12), rng.randint(2, 11)
        col = rng.choice(cols)
        p.p(x, y - 1, col); p.p(x - 1, y, col); p.p(x + 1, y, col); p.p(x, y + 1, col); p.p(x, y, C("#ffe9a0"))
        p.p(x, y + 2, C("#3f8a3c")); p.p(x + 1, y + 2, C("#5aa04a"))
    return p


def beach():
    save("beach_palm_0", palm(32, 45, -2), "town"); save("beach_palm_1", palm(32, 48, 2), "town")
    save("beach_sprout", sprout(), "town")
    for i, (w, h) in enumerate(((15, 15), (14, 15), (15, 15), (14, 15))):
        save(f"beach_rock_{i}", rock(w, h, i + 3), "town")
    for i in range(4):
        save(f"beach_pool_s{i}", tide_pool(32, 32, 11 + i), "town")
    save("beach_pool_big", tide_pool(48, 48, 5, rocky=True), "town")
    for i in range(6):
        save(f"beach_flowers_{i}", flower(20 + i), "town")


def main():
    for name, pix in interiors().items():
        save(name, pix)
    characters()
    beach()
    print("wrote", len(SIZES), "interior sprites, 24 character sheets, 18 beach pieces")


if __name__ == "__main__":
    main()
