"""Interior rooms.

Every room is a LayeredSpec (layered_room.py): floors, walls and furniture are *roles* defined in tileset_map.py, so
this file only says what goes where.  The collision grid (`ROWS`, same legend as worldmap.py) is generated from the
placements, so the F3 overlay always matches what you see.

Placement shorthands (x, y) = top-left tile of the footprint, (fw, fh) = footprint in tiles, dx / dy nudge in px:
  S  solid furniture     C  counter (solid, talk across it)     T  Sci-Database terminal (solid)
  N  decor you can walk past     F  floor decal (rug, mat)     W  wall decor (window, picture) hanging from tile row y
Tall furniture only blocks the floor tiles its base stands on; the upper part overhangs the wall behind it and is
depth-sorted against characters by the bottom edge of its footprint.

Art: the lab uses the SuperRetroWorld pack; the town's houses and shops use Modern Interiors (free).  The beds are the
project's own sprite and are placed exactly as before."""
from layered_room import (C, F, Floor, LayeredSpec, N, S, Spawn, T, W, Walls, collision_rows as _layered_rows, put)


class Prop:
    """A depth-sorted piece of scenery: drawn with characters, ordered by `sort_y` (used by townview for the town)."""

    def __init__(self, image, x, y, sort_y):
        self.image, self.x, self.y, self.sort_y = image, x, y, sort_y


def _walls(style):
    """Back wall = cap row + plain row + skirting row; side and front walls use the plain piece."""
    return Walls(back=(f"m_wall_{style}_cap", f"m_wall_{style}_fill", f"m_wall_{style}_base"),
                 side=f"m_wall_{style}_fill", front=f"m_wall_{style}_fill")


# --------------------------------------------------------------------------- the houses (player's home + cottages)
HOUSE = LayeredSpec(
    "house", 12, 10, (5, 6), floor=Floor("m_floor_herring"), walls=_walls("yellow"), door_mat="m_mat",
    things=(
        W("m_window_red", 5, 0, 2, dy=26), W("m_pic_forest", 2, 0, 2, dy=34),
        F("m_rug_red", 3, 5, 4, 3),
        S("m_bookcase_a", 1, 3, 2), S("m_lamp_blue", 3, 3), S("m_plant_small", 4, 3), S("m_dresser", 5, 3, 2),
        S("stove", 7, 3, 2), S("fridge_white", 9, 3, 2),
        S("bed_blue", 1, 6, 3, 2), N("lamp_table_b", 1, 5, dx=-4, dy=-10),             # the bed, exactly as before
        S("m_table", 8, 6, 2, 2), S("m_chair_front", 8, 5), S("m_chair_back", 8, 8),
        S("m_chair_right", 7, 6), S("m_chair_left", 10, 6), N("flowers_pink", 8, 6, dx=14, dy=-26),
        S("m_plant_tree", 10, 8), S("m_dresser_small", 1, 8), S("m_plant_small", 2, 8),
    ))

# --------------------------------------------------------------------------- town hall
HALL = LayeredSpec(
    "hall", 12, 10, (5, 6), floor=Floor("m_floor_brick"), walls=_walls("brown"), door_mat="m_mat",
    things=(
        W("m_window_grey", 5, 0, 2, dy=26), W("m_pic_hills", 2, 0, 2, dy=34), W("m_pic_forest", 9, 0, 2, dy=34),
        S("m_bookcase_a", 1, 3, 2), S("m_bookcase_b", 3, 3, 2), S("m_lamp_red", 5, 3), S("m_lamp_blue", 6, 3),
        S("m_bookcase_b", 7, 3, 2), S("m_bookcase_a", 9, 3, 2),
        S("m_plant_tree", 1, 4), S("m_plant_tree", 10, 4), S("x_podium", 3, 4),
        F("m_rug_blue_v", 5, 6, 3, 3),
        C("m_counter", 5, 5, 3), N("m_globe", 5, 5, dx=-14, dy=-30), N("x_book_stack", 7, 5, dx=2, dy=-36),
        S("m_sofa", 2, 6, 2), S("m_armchair", 4, 6), S("m_armchair", 8, 6), S("m_sofa", 9, 6, 2),
        S("m_sofa", 2, 8, 2), S("m_armchair", 4, 8), S("m_armchair", 8, 8), S("m_sofa", 9, 8, 2),
    ))

# --------------------------------------------------------------------------- the lab: SuperRetroWorld art
# Floors / walls / terminals / chest / power cores come from the sprite packs through tileset_map.py; collision comes
# from each role's flags, so there are no kinds or footprints to keep in sync here.
LAB = LayeredSpec(
    "lab", 12, 10, (5, 6),
    floor=Floor("floor_grid", rows=(
        "..........",
        ".....cc...",
        ".....cc...",
        ".....cc...",
        ".....cc...",
        ".....cc...",
    ), legend={"c": "floor_cyan"}),
    walls=Walls(),
    things=(
        put("porthole", 2, 0, dy=10), put("porthole_b", 9, 0, dy=10), put("notice_board", 6, 0, dy=8),
        put("server_rack", 1, 3), put("server_rack", 2, 3), put("containment_pod", 3, 3, 2),
        put("terminal_big", 5, 3), put("console_box", 6, 3), put("terminal_small", 7, 3),
        put("hydro_bay", 8, 3, 3),
        put("plasma_core", 1, 5), put("plasma_core_violet", 10, 5),
        put("lab_bench", 2, 6, 3), put("microscope", 3, 6, dy=-30),
        put("holo_table", 7, 6, 3),
        put("plant_pot", 1, 8), put("crate_stack", 8, 8, 2), put("chest_steel", 10, 8, id="lab-case"),
        put("specimen_jars", 3, 8, dy=-2),
    ),
    creatures=(Spawn("sparkit", 9, 4),),
)

# --------------------------------------------------------------------------- supply mart (14 x 13)
MART = LayeredSpec(
    "mart", 14, 13, (6, 7), floor=Floor("m_floor_cyan"), walls=_walls("mint"), door_mat="m_mat",
    things=(
        W("x_banner_red", 3, 0), W("x_banner_teal", 10, 0),
        S("m_goods_shelf_a", 1, 3, 6), S("m_goods_shelf_b", 7, 3, 6),
        S("m_cooler", 9, 5, 4), S("m_cart", 1, 5),
        F("m_rug_red", 3, 9, 4, 2),
        C("m_table_long", 2, 7, 6), N("x_register", 6, 7, dy=-48),
        S("m_table", 9, 8, 2, 2), N("x_basket", 9, 8, dx=6, dy=-44), N("x_fruit_crate_a", 10, 8, dx=-4, dy=-44),
        S("m_crates", 10, 10, 3), S("m_plant_tree", 1, 10), S("m_palm", 12, 8), S("x_sale_sign", 8, 11),
        N("x_basket", 1, 8, dx=2),
    ))

# --------------------------------------------------------------------------- Cush's repair nook
CUSH = LayeredSpec(
    "cush", 12, 10, (5, 6), floor=Floor("m_floor_grey"), walls=_walls("lavender"), door_mat="m_mat",
    things=(
        W("x_tool_wall", 4, 1, 3), W("x_backdoor", 9, 0, dy=4),             # the back-room door (the Bandits' reveal)
        S("x_parts_shelf", 1, 3, 3), S("x_workbench", 4, 3, 3), S("m_lamp_red", 7, 3),
        T("m_counter", 8, 3, 3), N("m_monitor", 8, 3, 3, dy=-50),
        C("m_table_long", 3, 5, 6), N("x_register", 4, 5, dy=-48), N("x_toolbox", 7, 5, dy=-48),
        F("m_rug_red", 4, 7, 4, 2),
        S("m_bench", 8, 7, 3), S("m_plant_small", 1, 7), S("m_plant_tree", 10, 6), N("x_toolbox", 2, 8, dy=-2),
    ))

# --------------------------------------------------------------------------- library
LIBRARY = LayeredSpec(
    "library", 12, 10, (5, 6), floor=Floor("m_floor_herring"), walls=_walls("red"), door_mat="m_mat",
    things=(
        W("m_map", 5, 0, 2, dy=30), W("m_pic_small", 2, 0, 2, dy=34), W("m_pic_small", 9, 0, 2, dy=34),
        S("m_bookcase_a", 1, 3, 2), S("m_bookcase_b", 3, 3, 2), S("m_bookcase_a", 5, 3, 2), S("m_bookcase_b", 7, 3, 2),
        S("m_bookcase_a", 9, 3, 2),
        C("m_counter", 4, 5, 3), N("x_book_stack", 6, 5, dy=-36),
        S("m_bookcase_b", 1, 6, 2), S("m_bookcase_a", 1, 8, 2),
        F("m_rug_red", 5, 7, 4, 2),
        S("m_reading_desk", 8, 6, 2), S("m_chair_front", 8, 5), S("m_chair_back", 9, 7),
        N("m_globe", 10, 6, dy=-30), S("m_lamp_tan", 10, 8),
    ))

# --------------------------------------------------------------------------- farm market
FARM_A = LayeredSpec(
    "farms-a", 12, 10, (5, 6), floor=Floor("m_floor_yellow"), walls=_walls("beige"), door_mat="m_mat",
    things=(
        W("m_window_red", 5, 0, 2, dy=26), W("x_hanging_plants", 1, 1, 2, dy=-4),
        S("m_cooler", 1, 3, 4), S("m_plant_tree", 5, 3), S("m_plant_small", 6, 3), S("m_cooler", 7, 3, 4),
        C("m_counter", 4, 5, 3), N("x_fruit_crate_b", 4, 5, dy=-48),
        S("x_seed_bins", 1, 6, 3), S("x_trough_a", 8, 6, 3),
        S("m_crates", 7, 8, 3), N("x_watering_can", 3, 7, dy=-2),
        S("m_plant_tree", 1, 8), S("m_palm", 10, 8),
    ))

# --------------------------------------------------------------------------- the green gym: the ring
# A challenge ring: the walkable floor circles a central platform (three counter rows), its corners marked by
# glowing plasma posts and a cyan outline painted on the floor.  The leader waits on the far side of the ring;
# the gym coaches patrol the corridor and must be beaten before she accepts a challenge.
GYM_RING = LayeredSpec(
    "gym-ring", 16, 13, (7, 8), floor=Floor("m_floor_grey", rows=(
        "..............",
        "..............",
        "...rrrrrrr....",
        "...r.....r....",
        "...r.....r....",
        "...r.....r....",
        "...rrrrrrr....",
        "..............",
        "..............",
    ), legend={"r": "m_floor_cyan"}),
    walls=_walls("mint"), door_mat="m_mat",
    things=(
        W("x_banner_teal", 3, 0), W("m_window_grey", 6, 0, 2, dy=26), W("x_banner_teal", 12, 0),
        put("plasma_core", 4, 5), put("plasma_core_violet", 10, 5),          # the ring posts
        put("plasma_core_violet", 4, 9), put("plasma_core", 10, 9),
        C("m_table_big", 6, 6, 3, 3),                                        # the platform inside the ring
        F("m_rug_red_v", 7, 4, 2, 2),                                        # the leader's spot
        # the island's flanks and the corridor hedges: the ring has exactly two single-file gates,
        # west at (4, 7) and east at (10, 7) -- each guarded by a gym coach (fight them in order)
        S("m_plant_tree", 5, 6), S("m_plant_tree", 5, 7), S("m_plant_tree", 5, 8),
        S("m_plant_tree", 9, 6), S("m_plant_tree", 9, 7), S("m_plant_tree", 9, 8),
        S("m_plant_tree", 1, 7), S("m_plant_tree", 2, 7), S("m_plant_tree", 3, 7),
        S("m_plant_tree", 11, 7), S("m_plant_tree", 12, 7), S("m_plant_tree", 13, 7), S("m_plant_tree", 14, 7),
        S("m_plant_tree", 1, 3), S("m_plant_tree", 14, 3),
        S("m_bench", 2, 10), S("m_bench", 12, 10),
        S("m_plant_small", 5, 10), S("m_plant_small", 10, 10),
    ),
    creatures=(Spawn("sporelet", 13, 4),),
)

LAYERED = {s.id: s for s in (HOUSE, HALL, LAB, MART, CUSH, LIBRARY, FARM_A, GYM_RING)}
ROWS = {k: _layered_rows(s) for k, s in LAYERED.items()}
