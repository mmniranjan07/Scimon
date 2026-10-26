"""ASSET MAPPING -- the one file to edit when you re-map art.  Pure data: no pygame, no file paths (those are in
settings.py), no game logic.

Every entry maps a *role* the game cares about ("metal floor", "lab terminal", "loot chest") to artwork.  An entry
lists its sources in priority order and the first one that actually exists wins:

    P(col, row, cw, ch)   PRIMARY   SuperRetroWorld atlas, in grid cells        (settings.PRIMARY_ATLASES)
    G(x, y, w, h)         SECONDARY Cute RPG Interiors global.png, pixel rect   (settings.SECONDARY_ATLAS)
    L("name")             LEGACY    the project's own assets/interiors/<name>.png

so the Cute RPG pack is only ever reached when the SuperRetro atlas has no equivalent, and the project's own sci-fi
props (server rack, containment tank...) fill the roles neither pack covers.  `python tools/atlas_inspector.py`
renders every atlas with (col, row) labels to help you find cells; `python tools/atlas_inspector.py --report`
prints which source each role resolved to.

Collision lives on the role, so a server rack is solid no matter which room it is placed in:
    collide  ""  walkable    "#"  solid    "C"  counter (solid, talk across it)    "@"  Sci-Database terminal (solid)
    foot     (w, h) footprint in tiles; the sprite is centred on it and its bottom edge sits on the footprint's bottom.
             A placement can override it (put(..., fw=, fh=)).
    layer    "floor" decal drawn into the background | "wall" decor in the midground wall | "mid" depth-sorted with
             characters | "fg" foreground overlay drawn above characters."""
from dataclasses import dataclass


def P(col, row, cw=1, ch=1):
    return ("primary", col, row, cw, ch)


def G(x, y, w, h):
    return ("secondary", x, y, w, h)


def L(name):
    return ("legacy", name)


def M(x, y, w, h):
    """Modern Interiors furniture sheet, exact pixel rect (objects there are not cell aligned)."""
    return ("modern", x, y, w, h)


def B(col, row, cw=1, ch=1):
    """Modern Interiors Room Builder sheet (walls / floors), in cells."""
    return ("builder", col, row, cw, ch)


@dataclass(frozen=True)
class TileDef:
    name: str
    sources: tuple
    layer: str = "mid"
    collide: str = ""
    foot: tuple = (1, 1)
    recolor: tuple = None          # (hue_lo, hue_hi, shift_degrees) -- see atlas.recolor
    glow: tuple = None             # (r, g, b, radius_in_tiles, strength 0..1): light halo in the foreground


@dataclass(frozen=True)
class AnimDef:
    """An animated object.  kind: 'loop' (plays forever) or 'chest' (closed -> opening -> open on interact)."""
    name: str
    kind: str
    base: tuple = None             # static art under the animation (a source tuple); None for pure strips
    strip: str = None              # file in settings.PRIMARY_ANIM_DIR: horizontal strip of 16x32 frames
    frame: tuple = (16, 32)
    fps: float = 8.0
    overlay: dict = None           # loop kinds: {"strip": "fire.png", "at": (x, y), "recolor": (lo, hi, shift)}
    screen: tuple = None           # loop kinds: (x, y, w, h, (r, g, b)) procedural glowing screen over `base`
    glow: tuple = None             # (r, g, b, radius_in_tiles, strength 0..1): light halo drawn in the foreground
    collide: str = "#"
    foot: tuple = (1, 1)
    loot: tuple = None             # chest kinds: (item id, quantity)
    fallback: tuple = ()           # static sources used if the strip/pack is missing
    layer: str = "mid"


TILES = {}
ANIMS = {}


def info(name):
    """TileDef or AnimDef for a role name (both expose layer / collide / foot)."""
    d = TILES.get(name) or ANIMS.get(name)
    if d is None:
        raise KeyError(f"tileset_map has no entry named {name!r}")
    return d


def _t(name, *sources, **kw):
    TILES[name] = TileDef(name, tuple(sources), **kw)


def _a(name, kind, **kw):
    ANIMS[name] = AnimDef(name, kind, **kw)


# ============================================================================ FLOORS  (background layer)
# The atlas floor cells are self-contained 2x2 checkers, so any single cell tiles seamlessly.
_t("floor_grid",       P(6, 9),  L("floor_tile_light"), layer="floor")      # dark steel grid plating
_t("floor_grid_ring",  P(6, 10), L("floor_tile_light"), layer="floor")      # same, with a ring decal
_t("floor_plate",      P(4, 6),  L("floor_tile_light"), layer="floor")      # grey diamond plate
_t("floor_stripe",     P(6, 8),  L("floor_tile_light"), layer="floor")      # striped hazard plating
_t("floor_cyan",       P(3, 9),  L("floor_tile_light"), layer="floor")      # cyan guide-lane tile
_t("floor_cyan_ring",  P(3, 10), L("floor_tile_light"), layer="floor")
_t("mat_metal",        P(6, 2, 2, 1), L("mat_red"), layer="floor", foot=(2, 1))   # airlock mat at the door

# ============================================================================ WALLS  (midground layer)
# Back wall = two plain rows + one railed row; side/front walls are one solid tile thick.
_t("wall_blue",        P(1, 0),  L("wall_teal"), layer="wall")
_t("wall_blue_rail",   P(1, 1),  L("panel_grey"), layer="wall")
_t("wall_stone",       P(3, 2),  L("wall_teal"), layer="wall")              # reinforced room boundary
_t("wall_stone_base",  P(3, 3),  L("panel_grey"), layer="wall")

# wall decor (no collision)
_t("porthole",         P(8, 0),  L("x_portrait_0"), layer="wall")
_t("porthole_b",       P(9, 0),  L("x_portrait_1"), layer="wall")
_t("window_wide",      P(14, 0, 2, 2), L("window_day"), layer="wall", foot=(2, 1))
_t("display_strip",    P(15, 2), L("x_portrait_0"), layer="wall")
_t("notice_board",     P(11, 10), L("x_family_photo"), layer="wall")
_t("picture_view",     P(10, 10), L("x_portrait_1"), layer="wall")

# ============================================================================ FURNITURE / INTERACTABLES  (midground, depth-sorted)
# -- primary pack ----------------------------------------------------------------------------------------------
_t("console_box",      P(19, 1), L("lowcab_w"), collide="#")                # steel console block
_t("crate_stack",      P(21, 0, 2, 2), L("crate_a"), collide="#", foot=(2, 1))
_t("crate_single",     P(19, 0), L("crate_b"), collide="#")
_t("brazier",          P(5, 11, 1, 2), L("lamp_floor_a"), collide="#")
_t("steel_chest",      P(23, 1), L("crate_a"), collide="#")                 # static stand-in for the animated chest
# -- roles the SuperRetro pack has no sci-fi equivalent for: the project's own art ----------------------------------
_t("server_rack",      L("x_server_rack"), collide="#")
_t("containment_pod",  L("x_tank"), collide="#", foot=(2, 1))
_t("hydro_bay",        L("x_hydro_a"), collide="#", foot=(3, 1))
_t("lab_bench",        L("x_lab_bench"), collide="#", foot=(3, 1))
_t("holo_table",       L("x_holo_table"), collide="#", foot=(3, 1))
_t("whiteboard",       L("whiteboard_stand"), collide="#", foot=(2, 1))
_t("plant_pot",        L("plant_grey_pot"), collide="#")
# -- decor you can walk past (no collision) ---------------------------------------------------------------------
_t("microscope",       L("x_microscope"), layer="mid")
_t("book_stack",       L("x_book_stack"), layer="mid")
# -- secondary pack: generic, non-tech clutter, used only where the primary pack has nothing suitable ------------
_t("specimen_jars",    G(193, 363, 30, 21), L("x_book_stack"), layer="mid")  # two sealed jars on a wooden tray
_t("storage_box",      G(69, 359, 22, 35),  L("crate_b"), collide="#")       # plain wooden storage box

# ============================================================================ ANIMATED OBJECTS
# Chest strips are 6 frames of 16x32: [0,1] closed idle, [2..4] lid opening, [5] open.
_a("chest_steel", "chest", strip="chest_003.png", fps=10, loot=("repaircell", 2), fallback=(P(23, 1), L("crate_a")))
_a("chest_wood",  "chest", strip="chest_001.png", fps=10, loot=("repaircell", 1), fallback=(P(23, 0), L("crate_a")))

# Glowing power cores: the dark brazier with the pack's flame strip recoloured from orange to cyan / violet.
_a("plasma_core", "loop", base=P(5, 11, 1, 2), overlay=dict(strip="fire.png", at=(0, -12), recolor=(0, 70, 165)),
   glow=(90, 230, 255, 1.6, 0.55), fps=9, fallback=(L("lamp_floor_a"),))
_a("plasma_core_violet", "loop", base=P(5, 11, 1, 2),
   overlay=dict(strip="fire2.png", at=(0, -12), recolor=(0, 70, 255)),
   glow=(190, 120, 255, 1.6, 0.5), fps=8, fallback=(L("lamp_floor_b"),))

# Retro CRT terminals with a procedural animated screen laid over the sprite's dark glass.
_a("terminal_big",   "loop", base=P(9, 12, 1, 2), screen=(2, 17, 12, 7, (110, 255, 190)), collide="@", fps=5,
   glow=(110, 255, 190, 1.3, 0.28), fallback=(P(9, 12, 1, 2), L("tv_on")))
_a("terminal_small", "loop", base=P(8, 12, 1, 2), screen=(3, 19, 10, 6, (120, 220, 255)), collide="@", fps=4,
   glow=(120, 220, 255, 1.2, 0.25), fallback=(P(8, 12, 1, 2), L("tv_on")))


# ============================================================================ MODERN INTERIORS (LimeZu, free)
# Used by the town's houses, shops, hall, library and farm market.  Sprites are exact pixel rects of the furniture
# sheet (M) or cells of the Room Builder sheet (B); `L(...)` after each is the project art used if the pack is absent.
_WARM = (255, 204, 120, 1.5, 0.30)                    # lamp glow

# -- walls: a back wall is cap + fill + base rows; one set per colour (row of the Room Builder sheet) --------------------
_WALL_SETS = {"salmon": 5, "yellow": 7, "mint": 9, "wood": 11, "brown": 13, "red": 15, "lavender": 17, "beige": 19}
for _n, _r in _WALL_SETS.items():
    _t(f"m_wall_{_n}_cap",  B(1, _r),     L("wall_cream"),   layer="wall")      # middle cell of each piece: the
    _t(f"m_wall_{_n}_fill", B(5, _r),     L("wall_cream"),   layer="wall")      # outer cells carry the dark end caps
    _t(f"m_wall_{_n}_base", B(1, _r + 1), L("panel_orange"), layer="wall")

# -- floors (3 x 2 cell patterns that tile seamlessly) -------------------------------------------------------------------
_t("m_floor_brick",    B(11, 5, 3, 2),  L("floor_wood_dark"),  layer="floor")
_t("m_floor_yellow",   B(11, 7, 3, 2),  L("floor_wood_pale"),  layer="floor")
_t("m_floor_cyan",     B(11, 9, 3, 2),  L("floor_tile_light"), layer="floor")
_t("m_floor_grey",     B(11, 11, 3, 2), L("floor_tile_taupe"), layer="floor")
_t("m_floor_herring",  B(11, 13, 3, 2), L("floor_wood_light"), layer="floor")

# -- furniture (solid unless a placement says otherwise; footprints are set where the piece is placed) -------------------
_t("m_bookcase_a",     M(80, 224, 32, 32),  L("bookcase_a"),   foot=(2, 1), collide="#")
_t("m_bookcase_b",     M(80, 256, 32, 32),  L("bookcase_color"), foot=(2, 1), collide="#")
_t("m_cabinet",        M(114, 772, 27, 39), L("cabinet_big"),  foot=(2, 1), collide="#")
_t("m_cabinet_glass",  M(179, 777, 27, 32), L("cabinet_wide"), foot=(2, 1), collide="#")
_t("m_cupboard",       M(144, 820, 48, 39), L("cabinet_big"),  foot=(3, 1), collide="#")
_t("m_dresser",        M(19, 949, 27, 23),  L("dresser_a"),    foot=(2, 1), collide="#")
_t("m_dresser_wide",   M(80, 949, 32, 21),  L("dresser_b"),    foot=(2, 1), collide="#")
_t("m_dresser_small",  M(0, 949, 16, 20),   L("dresser_a"),    foot=(1, 1), collide="#")
_t("m_counter",        M(0, 917, 48, 20),   L("desk_items"),   foot=(3, 1), collide="C")      # 3 small drawer units
_t("m_table_long",     L("x_table_long"),   foot=(6, 1), collide="C")                            # one seamless 6-drawer table (tools/make_long_tables.py)
_t("m_table_big",      L("x_table_big"),    foot=(3, 3), collide="C")                            # large platform table, 3 fused tiers
_t("m_vanity",         M(34, 779, 28, 30),  L("vanity_a"),     foot=(2, 1), collide="#")
_t("m_table",          M(13, 161, 38, 37),  L("table_round_brown"), foot=(2, 2), collide="#")
_t("m_bench",          M(117, 216, 38, 21), L("bench_orange"), foot=(2, 1), collide="#")
_t("m_sofa",           M(128, 288, 33, 26), L("sofa_red"),     foot=(2, 1), collide="#")
_t("m_armchair",       M(161, 288, 15, 26), L("armchair_beige"), collide="#")
_t("m_chair_front",    M(32, 341, 16, 26),  L("chair_brown_front"), collide="#")      # seen from the front (faces down)
_t("m_chair_back",     M(64, 341, 16, 26),  L("chair_brown_back"),  collide="#")      # seen from behind (faces up)
_t("m_chair_left",     M(98, 342, 13, 25),  L("chair_brown_l"),     collide="#")
_t("m_chair_right",    M(113, 342, 13, 25), L("chair_brown_r"),     collide="#")
_t("m_goods_shelf_a",  M(160, 1094, 96, 34), L("store_shelf_a"), foot=(6, 1), collide="#")   # shop shelving, 6 wide
_t("m_goods_shelf_b",  M(160, 1142, 96, 34), L("store_shelf_b"), foot=(6, 1), collide="#")
_t("m_cooler",         M(32, 296, 64, 32),  L("store_rack_w"), foot=(4, 1), collide="#")     # glass fridge shelves
_t("m_cart",           M(102, 297, 21, 31), L("store_rack_tall"), collide="#")
_t("m_reading_desk",   M(121, 618, 28, 22), L("x_reading_desk"), foot=(2, 1), collide="#")
_t("m_crates",         M(0, 890, 48, 22),   L("crate_a"),      foot=(3, 1), collide="#")     # produce crates
_t("m_plant_tree",     M(167, 713, 18, 31), L("plant_pot_tall"), collide="#")
_t("m_plant_small",    M(193, 722, 14, 23), L("plant_fern_pot"), collide="#")
_t("m_palm",           M(213, 704, 23, 31), L("palm"),         collide="#")
_t("m_lamp_blue",      M(192, 856, 15, 33), L("lamp_floor_a"), glow=_WARM, collide="#")
_t("m_lamp_red",       M(208, 856, 15, 33), L("lamp_floor_b"), glow=_WARM, collide="#")
_t("m_lamp_cream",     M(176, 887, 15, 25), L("lamp_floor_a"), glow=_WARM, collide="#")
_t("m_lamp_tan",       M(193, 904, 13, 33), L("lamp_floor_a"), glow=_WARM, collide="#")
_t("m_globe",          M(193, 1057, 13, 21), L("globe_a"))
_t("m_monitor",        M(208, 58, 13, 11),  L("tv_on"))                                       # CRT for terminals

# -- rugs (floor decals) -------------------------------------------------------------------------------------------------
_t("m_rug_red",        M(114, 244, 60, 40), L("rug_red_gold"),   layer="floor")
_t("m_rug_red_v",      M(212, 258, 40, 60), L("rug_red_gold_v"), layer="floor")
_t("m_rug_blue_v",     M(212, 178, 40, 60), L("rug_blue_gold_v"), layer="floor")
_t("m_mat",            M(180, 318, 24, 18), L("mat_red"),        layer="floor", foot=(2, 1))

# -- wall decor ----------------------------------------------------------------------------------------------------------
_t("m_window_red",     M(115, 391, 25, 20), L("window_day"),  layer="wall")
_t("m_window_grey",    M(147, 391, 25, 20), L("window_day"),  layer="wall")
_t("m_pic_forest",     M(165, 346, 21, 13), L("picture_hills"), layer="wall")
_t("m_pic_hills",      M(130, 362, 28, 13), L("picture_hills"), layer="wall")
_t("m_pic_aqua",       M(6, 362, 21, 14),   L("picture_sunset"), layer="wall")
_t("m_pic_small",      M(34, 1130, 13, 15), L("x_family_photo"), layer="wall")
_t("m_map",            M(160, 1065, 32, 19), L("world_map"),  layer="wall")

# -- project art that has no equivalent in the free pack (kitchen, flags, workshop and farm props, the bed) --------------
for _n in ("bed_blue", "lamp_table_b", "stove", "fridge_white", "flowers_pink", "x_flag_red", "x_flag_teal", "x_podium",
           "x_book_stack", "x_register", "x_basket", "x_fruit_crate_a", "x_fruit_crate_b", "x_sale_sign", "x_parts_shelf",
           "x_workbench", "x_tool_wall", "x_toolbox", "x_seed_bins", "x_trough_a", "x_watering_can", "x_hanging_plants",
           "x_banner_red", "x_banner_teal", "x_window_light"):
    _t(_n, L(_n))
_t("x_backdoor", L("doorway_black"), layer="wall")     # the repair bays' back-room door (the Bandits' reveal)
