"""Interior rooms built from sprite props.

Every piece of furniture is a Prop: a sprite plus a *footprint* on the tile grid.  The footprint is the hitbox:
the collision grid (`rows`, same legend as worldmap.py) is generated from the footprints, so the F3 overlay always
matches what you see.  Tall furniture (bookcases, fridges, wardrobes) only blocks the floor tiles its base stands on;
the upper part overhangs the wall behind it, and is depth-sorted against characters by the bottom edge of its footprint.

Prop kinds
  S  solid furniture           C  counter (solid, talk across it)      @  Sci-Database terminal (solid)
  n  decor you can walk past   f  floor decal (rug, mat), no collision w  wall decor (window, picture), no collision
Placement: (x, y) = top-left tile of the footprint, (fw, fh) = footprint size in tiles.  The sprite is centred on the
footprint horizontally and its bottom edge sits on the footprint's bottom edge ('w' props hang from the top of tile y).
dx / dy nudge the sprite in screen pixels.

Sprites are native 16 px-per-tile art (assets/interiors/*.png) scaled by PX with nearest-neighbour."""
from dataclasses import dataclass

import pygame

import assets
from settings import PX, TILE, VOID

WALL_ROWS = 3                      # rows 0-2 are the back wall; furniture bases start on row 3
TRIM = (86, 58, 38)
TRIM_HI = (128, 94, 64)


@dataclass
class Spec:
    id: str
    cols: int
    rows: int
    floor: str
    wall: str
    panel: str
    exits: tuple                   # x tiles of the doorway on the last row
    props: list


def _p(kind, name, x, y, fw=1, fh=1, dx=0, dy=0):
    return (kind, name, x, y, fw, fh, dx, dy)


def S(*a, **k): return _p("S", *a, **k)
def C(*a, **k): return _p("C", *a, **k)
def T(*a, **k): return _p("@", *a, **k)
def N(*a, **k): return _p("n", *a, **k)
def F(*a, **k): return _p("f", *a, **k)
def W(*a, **k): return _p("w", *a, **k)


# --------------------------------------------------------------------------- room layouts (revamped)
# Same footprints for the people and doors (spawn, exit, NPC tiles are unchanged); new furniture, wall decor, lighting.
HOUSE = Spec("house", 12, 10, "floor_wood_light", "wall_cream", "panel_orange", (5, 6), [
    W("window_day", 4, 0, 3, 2), W("clock", 9, 1, dy=4), W("x_family_photo", 2, 1, dy=6),
    F("rug_red_gold", 3, 5, 4, 3),
    S("bookcase_a", 1, 3, 3), S("lamp_floor_b", 4, 3), S("plant_fern_pot", 5, 3), S("stove", 7, 3, 2), S("fridge_white", 9, 3, 2),
    S("bed_blue", 1, 6, 3, 2), N("lamp_table_b", 1, 5, dx=-4, dy=-10),
    S("table_round_brown", 8, 5, 2, 2), S("chair_brown_front", 8, 4), S("chair_brown_back", 8, 7),
    S("chair_brown_r", 7, 5), S("chair_brown_l", 10, 5), N("flowers_pink", 8, 5, dx=14, dy=-26),
    S("plant_red_pot", 10, 8), S("dresser_a", 1, 8, 1), N("plant_pot_small", 2, 8, dy=-6),
])

HALL = Spec("hall", 12, 10, "floor_wood_dark", "wall_white", "panel_brown", (5, 6), [
    W("window_day", 4, 0, 3, 2), W("x_portrait_1", 3, 0, dy=-2),
    S("bookcase_color", 1, 3, 3), S("bookcase_color_doors", 8, 3, 3),
    S("x_flag_red", 4, 3), S("x_flag_teal", 7, 3),
    F("rug_red_gold_v", 5, 6, 3, 4),
    C("desk_items", 5, 5, 3), N("globe_a", 5, 5, dy=-18, dx=-14), N("x_book_stack", 7, 5, dx=2, dy=-24),
    S("bench_orange", 2, 6, 3), S("bench_orange", 2, 7, 3), S("bench_orange", 8, 6, 3), S("bench_orange", 8, 7, 3),
    S("plant_pot_tall", 1, 4), S("plant_pot_tall", 10, 4), S("x_podium", 3, 4), S("lamp_floor_a", 10, 5),
])

LAB = Spec("lab", 12, 10, "floor_tile_light", "wall_teal", "panel_grey", (5, 6), [
    W("window_day", 8, 0, 3, 2),
    S("x_server_rack", 1, 3), S("x_server_rack", 2, 3), S("x_tank", 3, 3, 2),
    T("lowcab_w", 5, 3, 3), N("tv_on", 5, 3, 3, dy=-30, dx=10),
    S("x_hydro_a", 8, 3, 3),
    S("x_lab_bench", 2, 6, 3), N("x_microscope", 3, 6, dy=-30), S("x_holo_table", 7, 6, 3),
    S("whiteboard_stand", 9, 8, 2), S("plant_grey_pot", 1, 8), N("x_book_stack", 4, 8, dy=-2),
])

MART = Spec("mart", 14, 13, "floor_wood_pale", "wall_cream", "panel_grey", (6, 7), [
    W("x_banner_red", 3, 0, dy=0), W("x_banner_teal", 10, 0, dy=0),
    S("store_shelf_a", 1, 3, 6), S("store_shelf_b", 7, 3, 6),
    S("store_rack_w", 9, 5, 4), S("store_rack_tall", 1, 5, dy=0),
    F("rug_dots_h", 3, 9, 4, 2),
    C("desk_items", 2, 7, 3), C("desk_items", 5, 7, 3), N("x_register", 6, 7, dy=-44),
    S("table_orange", 9, 8, 3, 2), N("x_basket", 10, 8, dy=-34), N("x_fruit_crate_a", 11, 8, dy=-34), S("crate_b", 12, 8), S("crate_b", 12, 9),
    S("plant_pot_tall", 1, 10), S("plant_grey_pot", 12, 11), S("x_sale_sign", 8, 11), N("x_basket", 1, 8, dx=2),
])

CUSH = Spec("cush", 12, 10, "floor_wood_pale", "wall_pink", "panel_orange", (5, 6), [
    W("x_tool_wall", 4, 1, 3),
    S("x_parts_shelf", 1, 3, 3), S("x_workbench", 4, 3, 3), S("lamp_floor_b", 7, 3), T("lowcab_w", 8, 3, 3), N("tv_on", 8, 3, 3, dy=-30, dx=10),
    C("desk_wc", 3, 5, 3), C("desk_wc", 6, 5, 3), N("x_register", 4, 5, dy=-42), N("x_toolbox", 7, 5, dy=-42),
    F("rug_red2_h", 4, 7, 4, 2),
    S("bench_orange", 8, 7, 3), S("plant_fern_pot", 1, 7), S("plant_red_pot", 10, 6), N("x_toolbox", 2, 8, dy=-2),
])

LIBRARY = Spec("library", 12, 10, "floor_wood_dark", "wall_cream", "panel_brown", (5, 6), [
    S("bookcase_a", 1, 3, 3), S("bookcase_color", 4, 3, 3), S("bookcase_doors", 7, 3, 3), S("narrow_shelf", 10, 3),
    C("desk_items", 4, 5, 3), W("plant_small", 6, 1, dy=4), N("x_book_stack", 6, 5, dy=-24),
    S("shelf_a", 1, 6, 3), S("shelf_b", 1, 8, 3),
    F("rug_dots_h", 5, 7, 4, 2),
    S("x_reading_desk", 8, 6, 3), S("chair_brown_front", 8, 5, 1), S("chair_brown_back", 9, 7),
    N("globe_b", 10, 6, dy=-26),
    S("armchair_beige", 9, 8), S("lamp_floor_a", 10, 8),
])

FARM_A = Spec("farms-a", 12, 10, "floor_wood_pale", "wall_sage", "panel_grey", (5, 6), [
    W("window_day", 5, 0, 3, 2), W("x_hanging_plants", 1, 1, 2, dy=-4),
    S("store_rack_w", 1, 3, 4), S("store_rack_w", 7, 3, 4), S("plant_pot_tall", 5, 3), S("plant_fern_pot", 6, 3),
    C("desk_items", 4, 5, 3), N("x_fruit_crate_b", 4, 5, dy=-44),
    S("x_seed_bins", 1, 6, 3), S("x_trough_a", 8, 6, 3),
    S("crate_a", 1, 7), S("crate_b", 10, 7), N("x_watering_can", 3, 7, dy=-2),
    S("plant_red_pot", 1, 8), S("palm", 10, 8),
])

SPECS = {s.id: s for s in (HOUSE, HALL, LAB, MART, CUSH, LIBRARY, FARM_A)}


# --------------------------------------------------------------------------- collision grid from footprints
def build_rows(spec):
    """Collision grid: '#' solid, '.' floor, 'E' exit, 'C' counter, '@' terminal.  Footprints decide everything."""
    exit_y = spec.rows - 1 if spec.id != "mart" else spec.rows - 1
    g = [["#"] * spec.cols for _ in range(spec.rows)]
    for y in range(WALL_ROWS, spec.rows - 1):
        for x in range(1, spec.cols - 1):
            g[y][x] = "."
    for x in spec.exits:
        g[exit_y][x] = "E"
    for kind, name, x, y, fw, fh, dx, dy in spec.props:
        ch = {"S": "#", "C": "C", "@": "@"}.get(kind)
        if ch is None:
            continue
        for yy in range(y, y + fh):
            for xx in range(x, x + fw):
                assert 0 < xx < spec.cols - 1 and WALL_ROWS <= yy < spec.rows - 1, (spec.id, name, xx, yy)
                assert g[yy][xx] == ".", f"{spec.id}: {name} overlaps another footprint at {(xx, yy)}"
                g[yy][xx] = ch
    return ["".join(r) for r in g]


ROWS = {k: build_rows(s) for k, s in SPECS.items()}


# --------------------------------------------------------------------------- baked lighting
def _radial(r, color, a_max):
    g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(r, 0, -2):
        a = int(a_max * (1 - i / r) ** 1.5) + 1
        pygame.draw.circle(g, color + (a,), (r, r), i)
    return g


def _edge_shade(s, W_, H_, exit_y):
    """Soft darkening along the side walls and under the back wall so the room has depth."""
    top = WALL_ROWS * TILE
    for i in range(26):
        a = int(70 * (1 - i / 26) ** 2)
        for x0 in (TILE + i, W_ - TILE - i - 1):
            pygame.draw.line(s, (0, 0, 0), (x0, top), (x0, exit_y * TILE), 1) if False else None
    sh = pygame.Surface((26, exit_y * TILE - top), pygame.SRCALPHA)
    for i in range(26):
        a = int(62 * (1 - i / 26) ** 2)
        pygame.draw.line(sh, (20, 10, 5, a), (i, 0), (i, sh.get_height()))
    s.blit(sh, (TILE, top))
    s.blit(pygame.transform.flip(sh, True, False), (W_ - TILE - 26, top))
    bot = pygame.Surface((W_ - 2 * TILE, 22), pygame.SRCALPHA)
    for i in range(22):
        pygame.draw.line(bot, (20, 10, 5, int(55 * (1 - i / 22) ** 2)), (0, 21 - i), (bot.get_width(), 21 - i))
    s.blit(bot, (TILE, exit_y * TILE - 22))


def _light_pass(s, spec):
    for kind, name, x, y, fw, fh, dx, dy in spec.props:
        if kind == "w" and name.startswith("window"):
            li = _sprite("x_window_light")
            s.blit(li, (x * TILE + (fw * TILE - li.get_width()) // 2, WALL_ROWS * TILE))
        elif name.startswith(("lamp_floor", "lamp_table")):
            img = _sprite(name)
            cx = x * TILE + fw * TILE // 2 + dx
            cy = (y + fh) * TILE - int(img.get_height() * 0.72) + dy
            g = _radial(84, (255, 204, 120), 70)
            s.blit(g, (cx - 84, cy - 84))
        elif name == "tv_on" or name.startswith("x_holo") or name.startswith("x_tank") or name.startswith("x_hydro"):
            col = (120, 230, 255) if name != "x_hydro_a" and name != "x_hydro_b" else (255, 160, 240)
            img = _sprite(name)
            cx = x * TILE + fw * TILE // 2 + dx
            cy = (y + fh) * TILE - img.get_height() // 2 + dy
            s.blit(_radial(70, col, 34), (cx - 70, cy - 70))


# --------------------------------------------------------------------------- rendering
class Prop:
    """A depth-sorted piece of furniture: drawn with characters, ordered by the bottom edge of its footprint."""

    def __init__(self, image, x, y, sort_y):
        self.image, self.x, self.y, self.sort_y = image, x, y, sort_y


def _sprite(name):
    img = assets.image(f"interiors/{name}.png")
    return assets.scaled(f"interiors/{name}.png", img.get_width() * PX, img.get_height() * PX, smooth=False)


def _tile_h(surf, patch, x0, y0, x1):
    pw = patch.get_width()
    x = x0
    while x < x1:
        surf.blit(patch, (x, y0))
        x += pw


def render(spec):
    """Returns (static surface, [Prop]) for a room."""
    W_, H_ = spec.cols * TILE, spec.rows * TILE
    s = pygame.Surface((W_, H_))
    s.fill(TRIM)
    exit_y = spec.rows - 1
    # floor
    fl = _sprite(spec.floor)
    for y in range(WALL_ROWS * TILE, exit_y * TILE + TILE, fl.get_height()):
        for x in range(TILE, W_ - TILE, fl.get_width()):
            s.blit(fl, (x, y))
    # back wall: plain upper wall + panelled lower wall
    wall, panel = _sprite(spec.wall), _sprite(spec.panel)
    _tile_h(s, wall, 0, 0, W_)
    _tile_h(s, panel, 0, WALL_ROWS * TILE - panel.get_height(), W_)
    pygame.draw.rect(s, TRIM, (0, 0, W_, 2 * PX))
    sh = pygame.Surface((W_ - 2 * TILE, 9), pygame.SRCALPHA)
    sh.fill((0, 0, 0, 55))
    s.blit(sh, (TILE, WALL_ROWS * TILE))
    # side walls and front wall (thin trim bands drawn over their solid tiles)
    for x0 in (0, W_ - TILE):
        pygame.draw.rect(s, TRIM, (x0, WALL_ROWS * TILE - 12, TILE, H_))
    pygame.draw.rect(s, TRIM_HI, (TILE - 3 * PX // 2, WALL_ROWS * TILE, 3 * PX // 2, H_ - WALL_ROWS * TILE))
    pygame.draw.rect(s, TRIM_HI, (W_ - TILE, WALL_ROWS * TILE, 3 * PX // 2, H_ - WALL_ROWS * TILE))
    pygame.draw.rect(s, TRIM, (0, exit_y * TILE, W_, TILE))
    pygame.draw.rect(s, TRIM_HI, (TILE, exit_y * TILE, W_ - 2 * TILE, 3 * PX // 2))
    # doorway: floor + doormat across the exit tiles
    for x in spec.exits:
        s.blit(fl, (x * TILE, exit_y * TILE), (0, 0, TILE, TILE))
    mat = _sprite("mat_red")
    cx = sum(spec.exits) / len(spec.exits) * TILE + TILE // 2
    s.blit(mat, (int(cx - mat.get_width() / 2), (exit_y + 1) * TILE - mat.get_height() - 4))

    _edge_shade(s, W_, H_, exit_y)
    props = []
    for kind, name, x, y, fw, fh, dx, dy in spec.props:
        img = _sprite(name)
        px_ = x * TILE + (fw * TILE - img.get_width()) // 2 + dx
        if kind == "w":
            s.blit(img, (px_, y * TILE + dy))
            continue
        bottom = (y + fh) * TILE
        py_ = bottom - img.get_height() + dy
        if kind == "f":
            s.blit(img, (px_, py_))
        else:
            props.append(Prop(img, px_, py_, bottom + (1 if kind == "n" else 0)))
    _light_pass(s, spec)
    return s, props
