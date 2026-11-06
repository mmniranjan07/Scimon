"""Outdoor areas beyond Riven Town.  Route 1 is laid out after a reference map: a winding path between stone ledges, with
tall-grass patches, fences, boulders and forest edges, linked to the town by its north road.  The wider region lives in
towns.py (styled towns, drawn like Epidimy) and kanto.py (routes and wild places); all three are merged into the AREAS /
LINKS graph below and validated together.
Tile legend = the overworld legend in worldmap.py, using only tiles the game already draws:
  G lawn   F flower lawn   g tall grass (wild encounters)   P cobbled road / stone steps through the ledges
  T tree   u bush   r boulder   l one-way ledge (hop down, never up)   f fence   h stone ledge wall (solid)   S signpost
  s sand   W ocean (solid)   Q palm   i sprout   j beach rock   v tide pool   z sand flowers   -- beach dressing
  R bridge   I pier planks   V volcanic ground   U sea-glass decal            (walkable, see townview.draw_ground)
  X loot chest   n cinder rock   o lava pool   Z monument   C moon crystal   t tunnel beam   K garden arch
  d mooring post   J lighthouse (2x2 footprint)   * item ball   ^ waterfall (Hydroclimb shortcut)
                                                                      (solid props, see townview.build_props)
The ridges of the reference are `l` ledges: walk into one from the tile above and you hop over it; from the sides or below it blocks. Its stairs are `P` gaps; the leafy undergrowth is walkable lawn.

Areas are joined by LINKS: stepping on a link tile fades to the target area.  validate() (run at import, like worldmap's)
guarantees the whole network can actually be walked: every open tile of every route is reachable from its entrances,
nobody can be soft-locked by a ledge, NPCs never cut a road, and the graph is connected from the town."""
import heapq
import math

import epidimy as epi
import worldmap as wm
from data import CATALOG, CHAIN_OF, SPECIES, WILD_HOME

ROUTE1_ROWS = [
    "TTTTTTPPPPTTTTTTTTTTTTTTTT",
    "TTTTTGPPPPGGGGGGGGGGGTTTTT",
    "TTTTTGPPPPPPPPPPPPPPGTTTTT",
    "TTTTTllGGTTTTTTTTGPPGTTTTT",
    "TTTTTggggTTTTTTTTGPPGTTTTT",
    "TTTTTggggTTTTTTTTGPPGTTTTT",
    "TTTTTggggTTTTTTTTGPPGTTTTT",
    "TTTTTgggggggggGGGllllTTTTT",
    "TTTTTGGGGGGGGGGGGGGGlTTTTT",
    "TTTTTGGGGGlllllllllllTTTTT",
    "TTTTlllGGGgggggGGGGGlTTTTT",
    "TTTTgggGlllllllllGGggTTTTT",
    "TTTTggggggPSPPPGgggggTTTTT",
    "TTTTggggggPPPPPTTTTTTTTTTT",
    "TTTTTTTggggPPGGTTTTTTTTTTT",
    "TTTTTTTggggPPGGTTTTTTTTTTT",
    "TTTTTTTTTTggggTTTTTTTTTTTT",
    "TTTTTTTTTTggggTTTTTTTTTTTT",
    "TTTTTTTTTTggggTTTTTTTTTTTT",
    "TTTTTTTGPPPPPPPPPPPPGTTTTT",
    "TTTTTTTGPPPPPPPPPPPPGTTTTT",
    "llllllllllllllllllPPllllll",
    "TTTGGGGGGGGGGGGGGGPPGTTTTT",
    "TTTGGPPPPPPPPPPPPPPPGTTTTT",
    "TTTllGGGGllllllllllllTTTTT",
    "TTTGGgggggPPPPGGGggggTTTTT",
    "TTTGggggggPPPPGggggggTTTTT",
    "TTTTTTTTTTgggTTTTTTTTTTTTT",
    "TTTTTTTTTTgggTTTTTTTTTTTTT",
    "TTTTTTTTTTPPPTTTTTTTTTTTTT",
]

ROUTE1_SIGNS = {
    (11, 12): ["Signpost: Route 1.", "South: Riven Town.", "Hop down a ledge to take a shortcut - you cannot climb back up.",
                "Use the stairs in the long ridge to go north.",
                "The tall grass ahead is full of wild Scimons."],
}

ROUTE1_NPCS = [
    wm._npc("ranger", 14, 13, "#6f8f5a", "#4a3a24", "Ranger Dana", [
        "Ranger Dana: Welcome to Route 1, {name}!",
        "Ranger Dana: The tall grass is full of wild Scimons. Bring a healthy team.",
        "Ranger Dana: You can hop DOWN a ledge, but never climb up one - use the stairs.",
        "Ranger Dana: The road north leads to Epidimy Town - a quiet place with a fine fountain.",
    ]),
    wm._trainer("luke", 8, 10, "Luke", [
        "Luke: Hey! I saw you crossing my lawn, {name}!",
        "Luke: My Sparkit and I train out here every day.",
        "Luke: Let's battle - right now!",
    ], ("sparkit", 6),
        post=["Luke: Whoa, you're strong!",
              "Luke: I've still got a lot of training to do."], facing="right"),
    wm._trainer("walker", 12, 19, "Walker", [
        "Walker: Halt, traveler!",
        "Walker: Nobody passes my patrol without a battle.",
        "Walker: Meet my Pebblon!",
    ], ("pebblon", 7),
        post=["Walker: Impressive, {name}.",
              "Walker: The road is yours. Walk safely."], facing="up",
        rematch=True,
        ask=["Walker: Back for more already, {name}?",
             "Walker: I've been training too, you know. Rematch?"]),
]


class Area:
    """An outdoor map.  `styled` areas (Epidimy Town, the towns in towns.py) are drawn by their own renderer and carry
    buildings with doors.  `start` is the safe fallback spot (a wipe / bad save never strands the player);
    `encounters` says whether the area has wild tall grass; `ponds` / `jets` / `cave` feed the styled renderer;
    `dark` cave places sit in near-blackness until the Lumen ability widens the light around the player."""

    def __init__(self, id, name, rows, signs=None, npcs=(), buildings=(), styled=False,
                 start=None, encounters=True, ponds=(), jets=(), cave=None, dark=False):
        self.id, self.name, self.rows, self.signs, self.npcs = id, name, rows, signs or {}, list(npcs)
        self.buildings, self.styled = list(buildings), styled
        self.start = start
        self.encounters = encounters
        self.ponds, self.jets, self.cave = list(ponds), list(jets), cave
        self.dark = dark
        self.w, self.h = len(rows[0]), len(rows)


ROUTE1_START = (11, 28)
TOWN = "overworld"                      # key of the town map in OverworldScene

# ---------------------------------------------------------------------------
# Wild encounters: an explicit zone registry replaces the old per-area biome tables.  Each zone pins one
# habitat_id to concrete tiles of one area (a tile-letter mask, optionally narrowed by rectangles), carries the
# area's level band from the database, and is the only thing the overworld's encounter trigger consults.  Mixed
# areas (water + volcanic on the sea routes, city + meadow on the grid roads, ghost patches near Dusklight,
# highland vs plateau on the Ascent) distinguish their patches by tile letters or position -- an area-wide
# habitat list can mis-spawn, so it is never consulted.
from data import DB as _DB
from data import HABITATS as _HABITATS

# area id -> [(habitat_id, tile letters, rectangles or None for the whole area)]; first match wins.
ZONE_TABLE = {
    "route1": [("meadow", "g", None)],
    "route2": [("forest", "g", None)],
    "route2n": [("forest", "g", None)],
    "mossmere": [("forest", "g", None)],
    "route3": [("cave", "g", None)],
    "route4": [("meadow", "g", None)],
    # the grid roads: tall grass = meadow, the cobbled facility roads = city
    "route5": [("meadow", "g", None), ("city", "P", None)],
    "route6": [("meadow", "g", None), ("city", "P", None)],
    "route7": [("meadow", "g", None), ("city", "P", None)],
    # route8: west grass = meadow, east grass = Dusklight's ghost patches, roads = city
    "route8": [("meadow", "g", [(0, 0, 35, 19)]), ("ghost", "g", [(36, 0, 71, 19)]), ("city", "P", None)],
    "route9": [("meadow", "g", None)],
    # route10: the north grass = cave, the south grass by the lake = ghost
    "route10": [("cave", "g", [(0, 0, 23, 39)]), ("ghost", "g", [(0, 40, 23, 79)])],
    "route11": [("meadow", "g", None)],
    # route12/13: inland grass = meadow, the coastal grass by the ocean = ghost
    "route12": [("meadow", "g", None)],
    "route13": [("ghost", "g", [(40, 0, 71, 19)]), ("meadow", "g", None)],
    "route14": [("meadow", "g", None)],
    "route15": [("meadow", "g", None)],
    "route16": [("meadow", "g", None)],
    "route17": [("meadow", "g", None)],
    "route18": [("meadow", "g", None)],
    "route24": [("meadow", "g", None)],
    "route25": [("meadow", "g", None)],
    # the sea routes: sand = water shallows (volcanic shore near Cinderfall), piers and causeways = sea
    "route19": [("water", "sg", None), ("sea", "I", None)],
    "route20": [("volcanic", "s", [(0, 0, 15, 19)]), ("sea", "s", [(90, 0, 119, 19)]), ("water", "s", None)],
    "route21": [("volcanic", "s", [(0, 50, 23, 99)]), ("water", "s", None), ("sea", "I", None)],
    "seaglass": [("water", "P", None)],
    "route22": [("highland", "g", None)],
    # the Ascent (Victory Road pass): the upper floor = plateau, the climb below = highland
    "ascent": [("plateau", "P", [(0, 0, 47, 10)]), ("highland", "P", [(0, 11, 47, 21)])],
    "mt_crescent": [("cave", "P", None)],
    "hollowgate": [("tunnel", "P", None)],
    # the Vespera Safari Reserve: four sub-zones, one habitat each (FireRed's Safari Zone areas)
    "safari": [("water", "s", [(2, 2, 33, 8)]), ("highland", "g", [(2, 9, 9, 22)]),
               ("forest", "g", [(26, 9, 33, 24)]), ("meadow", "g", [(11, 9, 24, 24)])],
}

# Zone level bands for places the Sci-Database has no survey records for (the reserve's wardens set
# their own bands: a gym-6 region, so Vespera's ceiling applies through ZONE_GYM below).
BAND_OVERRIDES = {
    ("safari", "meadow"): (16, 26), ("safari", "water"): (18, 28),
    ("safari", "forest"): (20, 30), ("safari", "highland"): (22, 32),
}

_DB_BANDS = {(b["area_id"], h["id"]): (b["min_level"], b["max_level"])
             for h in _HABITATS.values() for b in h["source_area_level_bands"]}
DEFAULT_BAND = (2, 16)


def habitat_grid(area):
    """Per-tile habitat ids for an outdoor area: the habitat of the zone governing each tile, or None on
    safe ground.  A zone themes its whole rectangle (the terrain around the wild Scimon), not just the
    encounter letters -- the map renderer tints the ground after the Scimon that live there."""
    rows = AREA_ROWS.get(area)
    if not rows:
        return None
    grid = [[None] * len(rows[0]) for _ in rows]
    for z in ENCOUNTER_ZONES.get(area, ()):
        if z["rects"] is None:
            rects = [(0, 0, len(rows[0]) - 1, len(rows) - 1)]
        else:
            rects = z["rects"]
        for (x0, y0, x1, y1) in rects:
            for y in range(max(0, y0), min(len(rows), y1 + 1)):
                for x in range(max(0, x0), min(len(rows[0]), x1 + 1)):
                    if grid[y][x] is None:
                        grid[y][x] = z["habitat_id"]
    return grid


def _build_zones():
    from data import FAMILIES as _FAM
    zones = {}
    for area, specs in ZONE_TABLE.items():
        lst = []
        for i, (habitat, tiles, rects) in enumerate(specs):
            band = list(BAND_OVERRIDES.get((area, habitat)) or _DB_BANDS.get((area, habitat), DEFAULT_BAND))
            # extend the band minimum downward when first forms can't reach the original floor
            first_floors = [SPECIES[s].max_wild_level for f in _FAM.values()
                            if habitat in f["normal_habitats"] for s in f["chain_ids"]
                            if SPECIES[s].stage_ordinal == 1]
            if first_floors:
                floor = max(first_floors)
                if band[0] > floor:
                    band[0] = max(1, floor)
            lst.append({"zone_id": f"{area}:{habitat}:{i}", "area_id": area, "habitat_id": habitat,
                        "tiles": frozenset(tiles), "rects": tuple(rects) if rects else None,
                        "band": tuple(band), "wild_enabled": True})
        zones[area] = lst
    return zones


from data import SPECIES


ENCOUNTER_ZONES = _build_zones()

# ---------------------------------------------------------------------------
# Gym progression: each zone references the gym it prepares the player for.  The gym's wild ceiling
# (FireRed ace level minus the configured gap) caps all wild levels in that zone.  Zones are mapped
# by progression position (the gym challenge they prepare for), not by route number or geography.
ZONE_GYM = {
    "route1": 1, "route2": 1, "route2n": 1, "mossmere": 1,
    "route3": 2, "route4": 2, "route22": 2, "route11": 2,
    "route5": 3, "route6": 3, "route7": 3, "route8": 3, "route9": 3,
    "route10": 4, "route12": 4, "route13": 4, "route14": 4, "mt_crescent": 4,
    "route15": 5, "route16": 5, "route17": 5, "route18": 5,
    "route19": 5, "route20": 5, "route21": 5, "seaglass": 5, "hollowgate": 5,
    "safari": 6,                              # the reserve prepares you for Vespera's own gym
    "ascent": 7,                                                             # postgame zone
}
POSTGAME_ZONES = {"ascent"}                # explicit postgame designations (ceiling 50 after the boss)

# The cave places the Excavator ability can burrow out of (FireRed's Escape Rope): K_g warps the
# player back to the mouth they came in through (the network's link arrival into the place).
CAVE_PLACES = ("mt_crescent", "hollowgate", "ascent")

from encounters import GYM_REFERENCE, POSTGAME_WILD_CAP, POSTGAME_STORY_FLAG

for _area, _zs in ENCOUNTER_ZONES.items():
    for _z in _zs:
        _gym = ZONE_GYM.get(_area, 1)
        _z["gym_id"] = _gym
        _z["gym_ceiling"] = GYM_REFERENCE[_gym]["ceiling"]
        _z["postgame"] = _area in POSTGAME_ZONES


def zone_at(area, x, y):
    """The encounter zone covering tile (x, y) of an outdoor area, or None (safe ground / interiors)."""
    rows = AREA_ROWS.get(area)
    if not rows or not (0 <= y < len(rows)) or not (0 <= x < len(rows[0])):
        return None
    tile = rows[y][x]
    for z in ENCOUNTER_ZONES.get(area, ()):
        if tile in z["tiles"]:
            if z["rects"] is None or any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in z["rects"]):
                return z
    return None


AREAS = {"route1": Area("route1", "Route 1", ROUTE1_ROWS, ROUTE1_SIGNS, ROUTE1_NPCS, start=ROUTE1_START),
         epi.AREA_ID: Area(epi.AREA_ID, epi.NAME, epi.ROWS, epi.SIGNS, epi.NPCS, epi.BUILDINGS, styled=True,
                           start=epi.START, ponds=epi.POND_REGIONS, jets=[epi.FOUNTAIN_REGION], cave=epi.CAVE)}

# area id -> {tile: (target area id, target tile, facing on arrival)}.  Arrival tiles are one step inside the target so a
# link is never re-triggered on arrival.
LINKS = {
    TOWN: {(21, 0): ("route1", ROUTE1_START, "up")},
    "route1": {(10, 29): (TOWN, (21, 1), "down"), (11, 29): (TOWN, (21, 1), "down"),
               (12, 29): (TOWN, (21, 1), "down"),
               # the north end of Route 1 (road tiles x 6..9 of row 0) leads to Epidimy Town's south road
               **{(x, 0): (epi.AREA_ID, (x, epi.H - 2), "up") for x in epi.ROUTE1_GATE_X}},
    epi.AREA_ID: {(x, epi.H - 1): ("route1", (x, 1), "down") for x in epi.ROUTE1_GATE_X},
}

# ---------------------------------------------------------------------------
# The wider region: towns.py holds the styled towns (Stonreach, Tidebrook, ... and the Plateau), kanto.py the
# numbered routes and wild places between them.  Both are pure data; this merge wires the whole network together.
import towns
import kanto

for _t in towns.TOWNS:
    AREAS[_t.id] = Area(_t.id, _t.name, _t.ROWS, _t.signs, _t.npcs, _t.buildings, styled=True,
                        start=_t.start, ponds=_t.POND_REGIONS)
for _k, _r in kanto.AREAS.items():
    AREAS[_k] = Area(_k, _r.name, _r.rows, _r.signs, _r.npcs, getattr(_r, "buildings", ()),
                     start=_r.start, encounters=_r.encounters, dark=(_k in CAVE_PLACES))
for _k, _v in kanto.LINKS.items():
    LINKS.setdefault(_k, {}).update(_v)
HEALERS_EXTRA = towns.HEALERS + kanto.HEALERS

# ---------------------------------------------------------------------------
# The Vespera Safari Reserve (FireRed's Safari Zone): four fenced sub-zones over one big map -- the
# entry meadow, the north wetland, the west ridge and the east grove -- each with its own habitat
# table above.  You cannot walk here: the warden at Vespera's Safari Gate warps you in once the
# session is paid for, and the south gate's LINK tiles walk you back out to the town.
SAFARI_AREA = "safari"
SAFARI_ARRIVAL = (17, 27)               # where the warden sets you down (never a link tile)
SAFARI_W, SAFARI_H = 36, 30


def _safari_rows():
    """The reserve grid, built deterministically (no pygame, no random): a sand wetland across the
    north, a rocky ledge ridge in the west, a bushy grove in the east, a checked meadow in the
    middle, all inside a tree ring, with the gate road to Vespera at the south."""
    w, h = SAFARI_W, SAFARI_H
    g = [["G"] * w for _ in range(h)]

    def put(x0, y0, x1, y1, ch):
        for y in range(max(0, y0), min(h - 1, y1) + 1):
            for x in range(max(0, x0), min(w - 1, x1) + 1):
                g[y][x] = ch
    put(0, 0, w - 1, 0, "T")            # the tree ring
    put(0, h - 1, w - 1, h - 1, "T")
    put(0, 0, 0, h - 1, "T")
    put(w - 1, 0, w - 1, h - 1, "T")
    put(2, 2, 33, 8, "s")               # the north wetland: sand, ponds, tide pools
    put(12, 4, 17, 7, "w")
    put(20, 3, 24, 6, "w")
    for x, y in ((6, 7), (9, 3), (18, 5), (26, 4), (30, 7)):
        g[y][x] = "v"
    put(2, 9, 9, 22, "g")               # the west ridge: grass over rocks, one hop-down ledge
    put(2, 12, 9, 12, "l")
    for y in range(9, 23):
        for x in range(2, 10):
            if g[y][x] == "g" and (x * 5 + y * 11) % 13 == 0:
                g[y][x] = "r"
    put(11, 9, 24, 24, "G")             # the middle meadow: checked lawn and tall grass
    for y in range(10, 25):
        for x in range(11, 25):
            if (x * 7 + y * 3) % 4 < 2:
                g[y][x] = "g"
    put(26, 9, 33, 24, "g")             # the east grove: grass, bushes, tree clumps
    for y in range(9, 25):
        for x in range(26, 34):
            if (x * 13 + y * 5) % 11 == 0:
                g[y][x] = "u"
            elif (x * 3 + y * 17) % 19 == 0:
                g[y][x] = "T"
    put(10, 10, 10, 24, "f")            # the fences with their two gates
    put(10, 15, 10, 16, "G")
    put(25, 10, 25, 24, "f")
    put(25, 15, 25, 16, "G")
    put(14, 24, 14, 24, "S")            # the gate plaza: signs, the road, the item ball
    put(21, 24, 21, 24, "S")
    put(15, 24, 20, 28, "P")
    put(16, 29, 19, 29, "P")
    g[27][31] = "*"
    return ["".join(r) for r in g]


SAFARI_SIGNS = {
    (14, 24): ["Signpost: The Safari Reserve.", "North: the wetland flats - Scimons wade there all day.",
               "West: the ridge, where the ledges hop down and the rock-dwellers sunbathe.",
               "East: the grove - quiet, shaded, full of shy undergrowth Scimons.",
               "No battling in the reserve! Bait, rocks and Safari Modules only."],
    (21, 24): ["Signpost: Ranger post 3.", "Please do not feed the wild Scimons outside of supervised baiting.",
               "Lost Safari Modules are NOT replaceable."],
}

SAFARI_NPCS = [
    wm._npc("safari-ranger", 16, 23, "#4a7a4a", "#2a4a2a", "Ranger Fern", [
        "Ranger Fern: Welcome to the reserve, {name}!",
        "Ranger Fern: No battles in here - your modules do the work. Bait calms them, rocks rile them.",
        "Ranger Fern: Watch your step budget. The PA will call you home when it runs out.",
    ]),
]

AREAS[SAFARI_AREA] = Area(SAFARI_AREA, "Safari Reserve", _safari_rows(), SAFARI_SIGNS, SAFARI_NPCS,
                          start=SAFARI_ARRIVAL)
LINKS[SAFARI_AREA] = {(17, 29): ("vespera", (18, 6), "down"), (18, 29): ("vespera", (18, 6), "down")}

AREA_ROWS = {TOWN: wm.MAP_ROWS, **{a.id: a.rows for a in AREAS.values()}}

# Outdoor loot chests (layered_room.FieldChest), area id -> [dict(tile, key, loot)].  House rule, enforced in
# validate(): at most ONE town, ONE route and ONE wild place hide a chest, so what they hold stays special.
CHESTS = {
    epi.AREA_ID: [dict(tile=epi.CHEST, key="epidimy:chest",
                       loot=(("hydrocell", 1), ("nanorepair", 2)))],
    **kanto.CHESTS,
}

# FRLG-style item balls (layered_room.ItemBall): a pickup lying in the road, face it and confirm.
ITEM_BALLS = {**kanto.ITEM_BALLS,
              "safari": [dict(tile=(31, 27), key="safari:ball", loot=(("nanorepair", 2),))]}

# The waterfall tile ('^'): solid rock-water that only the Hydroclimb ability makes walkable (a shortcut
# column, climbable up and down once the ability is held).  '*' is the item-ball tile.  Both glyphs live
# in the route legend; the punctuation keeps them clear of every letter the town renderer prop-maps.
FALLS_TILE = "^"

# The wild places (kanto.py's non-route areas): they may hide one chest of their own.
PLACE_AREAS = frozenset({"mossmere", "mt_crescent", "hollowgate", "ascent", "seaglass"})


# ---------------------------------------------------------------------------
# Healers: places that restore the party.  After a wipe the player is sent back to the nearest one they have
# visited, or (failsafe, OverworldScene.end_wild_battle) the nearest one in an area they have already been
# through, so dying can never strand them nor skip them ahead: Prof. Venn by the town plaza, the two
# Cush's Repair Nook franchises (Riven Town and Epidimy) and one nook per town of the wider network.
# `tile` is where the player is set down, one step from the healer.
HEALERS = [
    dict(id="venn", name="Prof. Venn", area=TOWN, tile=(20, 8), facing="up"),
    dict(id="cush", name="Cush's Repair Nook", area=TOWN,
         tile=next(b.entry_return for b in wm.BUILDINGS if b.id == "cush"), facing="down"),
    dict(id="epi-center", name="Cush's Repair Nook", area=epi.AREA_ID,
         tile=next(b.entry_return for b in epi.BUILDINGS if b.id == "epi-center"), facing="down"),
] + HEALERS_EXTRA


def travel_cost(start_area, start_tile, target_area, target_tile):
    """Estimated walking distance in tiles between two spots, or None when no link path reaches the target.
    Within one area it is the straight tile distance; across areas it chains through link tiles (+1 per
    crossing).  A small Dijkstra over (area, entry tile) states, so the network's loops cost nothing:
    the old recursive walk exploded combinatorially once the routes formed cycles."""
    best, result = {(start_area, start_tile): 0.0}, None
    heap = [(0.0, start_area, start_tile)]
    while heap:
        c, area, tile = heapq.heappop(heap)
        if c > best.get((area, tile), math.inf):
            continue
        if area == target_area:
            d = c + math.hypot(tile[0] - target_tile[0], tile[1] - target_tile[1])
            if result is None or d < result:
                result = d
        for (lt, (dst, at, _f)) in LINKS.get(area, {}).items():
            nd = c + math.hypot(tile[0] - lt[0], tile[1] - lt[1]) + 1
            key = (dst, at)
            if nd < best.get(key, math.inf):
                best[key] = nd
                heapq.heappush(heap, (nd, dst, at))
    return result


def building_at(area, x, y):
    """The building whose door is on tile (x, y) of an outdoor area (None when there is none)."""
    if area == TOWN:
        return wm.building_at_door(x, y)
    a = AREAS.get(area)
    return next((b for b in a.buildings if b.door == (x, y)), None) if a else None


def _moves(rows, w, h, pos, solid):
    """Tiles reachable from `pos` in one move: the four neighbours, plus the landing tile of a ledge hop (south only)."""
    x, y = pos
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and rows[ny][nx] not in solid:
            yield (nx, ny)
    if y + 2 < h and rows[y + 1][x] == wm.LEDGE_DOWN and rows[y + 2][x] not in solid:
        yield (x, y + 2)


def _reach(rows, w, h, start, solid, blocked=frozenset()):
    seen, stack = {start}, [start]
    while stack:
        for n in _moves(rows, w, h, stack.pop(), solid):
            if n not in seen and n not in blocked:
                seen.add(n)
                stack.append(n)
    return seen


ROUTE_LEGEND = "GFgPTurfhSlk" + "sW" + "Qijvz" + "RIVU" + "XnZoCtKdJ" + "BDe" + "Hw" + "^*"


def validate():
    solid = wm.OVERWORLD_SOLID                     # includes the ledge tile: you can only *land* beside it

    def rows_of(area):
        return wm.MAP_ROWS if area == TOWN else AREAS[area].rows

    def npcs_of(area):
        return wm.NPCS if area == TOWN else AREAS[area].npcs

    # ---- shape + legend
    for a in AREAS.values():
        assert all(len(r) == a.w for r in a.rows), f"{a.id}: ragged rows"
        if not a.styled:                                       # styled areas validate their own legend
            assert all(c in ROUTE_LEGEND for r in a.rows for c in r), f"{a.id}: unknown tile letter"
        assert a.start is not None and a.rows[a.start[1]][a.start[0]] not in solid, f"{a.id}: start tile is bad"

    # ---- links: on walkable tiles, arrivals walkable / free / not on an NPC, facings valid
    for src, links in LINKS.items():
        rows = rows_of(src)
        for (x, y), (dst, (tx, ty), facing) in links.items():
            assert rows[y][x] not in solid, f"link {src}{(x, y)} is on a solid tile"
            drows = rows_of(dst)
            assert drows[ty][tx] not in solid and (tx, ty) not in LINKS.get(dst, {}), f"arrival {dst}{(tx, ty)} is bad"
            assert (tx, ty) not in {(n["x"], n["y"]) for n in npcs_of(dst)}, f"arrival {dst}{(tx, ty)} lands on an NPC"
            assert facing in ("up", "down", "left", "right")

    # ---- the whole graph is reachable on foot from the town
    seen_areas, stack = {TOWN}, [TOWN]
    while stack:
        for _tile, (dst, _at, _f) in LINKS.get(stack.pop(), {}).items():
            if dst not in seen_areas:
                seen_areas.add(dst)
                stack.append(dst)
    seen_areas.add(SAFARI_AREA)     # the reserve: entered by the warden's paid warp, left via its gate
    missing = (set(AREAS) | {TOWN}) - seen_areas
    assert not missing, f"areas unreachable from the town: {sorted(missing)}"

    # the town's north road must be the link tile, and the route must be fully walkable from the entrance
    assert wm.MAP_ROWS[0][21] == "P" and wm.MAP_ROWS[1][21] == "P", "town road does not reach the north exit"

    # ---- per non-styled area: everything reachable, ledges never soft-lock, signs/NPCs/grass sane.
    # Tiles sealed behind a waterfall column ('y') are exempt from the base pass but must be reachable
    # -- and never a trap -- once the Hydroclimb ability makes the falls walkable.
    reach = {}
    reach_ab = {}                                   # the with-Hydroclimb reach, where the area has falls
    for a in AREAS.values():
        if a.styled:
            continue
        arrivals = {(tx, ty) for links in LINKS.values() for (tgt, (tx, ty), _f) in links.values() if tgt == a.id}
        if a.id == SAFARI_AREA:
            arrivals = {SAFARI_ARRIVAL}         # the warden's warp lands here; its gate links walk out
        assert arrivals, f"{a.id}: no way in"
        exits = set(LINKS.get(a.id, {}))
        seen = set()
        for s in arrivals:
            seen |= _reach(a.rows, a.w, a.h, s, solid)
        reach[a.id] = seen
        open_tiles = {(x, y) for y in range(a.h) for x in range(a.w) if a.rows[y][x] not in solid}
        gated = open_tiles - seen
        assert not gated or any(c == FALLS_TILE for r in a.rows for c in r), \
            f"{a.id} has unreachable open tiles (no falls to gate them): {sorted(gated)}"
        if gated:
            ability_solid = solid - {FALLS_TILE}
            ability_seen = set()
            for s in arrivals:
                ability_seen |= _reach(a.rows, a.w, a.h, s, ability_solid)
            reach_ab[a.id] = ability_seen
            assert gated <= ability_seen, f"{a.id}: falls-gated tiles unreachable even with Hydroclimb: {sorted(gated)}"
            for t in sorted(gated):
                back = _reach(a.rows, a.w, a.h, t, ability_solid)
                assert exits & back, f"{a.id} soft-lock (with Hydroclimb): no way back to an exit from {t}"
        assert exits <= seen, f"{a.id}: an exit is not reachable: {sorted(exits - seen)}"
        for t in sorted(seen):
            assert exits & _reach(a.rows, a.w, a.h, t, solid), f"{a.id} soft-lock: no way back to an exit from {t}"
        ledges = [(x, y) for y in range(a.h) for x in range(a.w) if a.rows[y][x] == wm.LEDGE_DOWN]
        assert not ledges or any((x, y - 1) in seen and (x, y + 1) in seen for x, y in ledges), f"{a.id}: no ledge can actually be hopped"
        if a.encounters:
            assert any(c == "g" for r in a.rows for c in r), f"{a.id} has no tall grass"
        else:
            assert not any(c == "g" for r in a.rows for c in r), f"{a.id} should have no tall grass"
        for (sx, sy) in a.signs:
            assert a.rows[sy][sx] == "S", f"{a.id} sign {(sx, sy)} is not on an S tile"
            assert any((sx + dx, sy + dy) in seen for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), f"{a.id} sign {(sx, sy)} can't be read"
        assert sum(c == "S" for r in a.rows for c in r) == len(a.signs), f"{a.id}: an S tile has no sign text"
        for n in a.npcs:
            assert (n["x"], n["y"]) in seen, f"{a.id} NPC {n['id']} is walled off"
            if "battle" in n:
                assert isinstance(n["battle"], tuple) and len(n["battle"]) == 2, f"{a.id} trainer {n['id']} has no battle spec"
                assert n.get("facing") in ("up", "down", "left", "right"), f"{a.id} trainer {n['id']} has a bad facing"
        blocked_by_npc = {(n["x"], n["y"]) for n in a.npcs
                          if not n.get("require_stamps")}          # badge-gate guards block only below their stamp count
        assert not blocked_by_npc & exits, f"{a.id}: an NPC stands on a link tile"
        seen2 = set()
        for s in arrivals:
            seen2 |= _reach(a.rows, a.w, a.h, s, solid, blocked_by_npc)
        assert seen2 == seen - blocked_by_npc, f"an NPC blocks part of {a.id}: {sorted(seen - blocked_by_npc - seen2)}"
        for n in a.npcs:                                           # the badge-gate guards (FireRed's Route 23):
            if n.get("require_stamps"):
                assert n["aside"], f"{a.id}: stamp guard {n['id']} has no aside tile"
                ax, ay = n["aside"]
                assert a.rows[ay][ax] not in solid, f"{a.id}: stamp guard {n['id']} cannot step aside"
                assert any((ax + dx, ay + dy) in seen2 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), \
                    f"{a.id}: stamp guard {n['id']} aside tile is cut off"

    # ---- healers: warp tiles must be walkable, unoccupied and never on a route (healers live in the towns)
    for h in HEALERS:
        assert h["area"] == TOWN or h["area"] in AREAS, f"healer {h['id']} is not in a known area"
        rows = rows_of(h["area"])
        assert rows[h["tile"][1]][h["tile"][0]] not in solid, f"healer {h['id']} warps onto a solid tile"
        assert h["tile"] not in {(n["x"], n["y"]) for n in npcs_of(h["area"])}, f"healer {h['id']} warps onto an NPC"
        assert h["facing"] in ("up", "down", "left", "right"), f"healer {h['id']} has a bad facing"

    # ---- wild encounters: the zone registry.  Every grass-bearing area has at least one zone, zones sit on
    # tiles their area actually has, every one of the 11 habitats and every family habitat is reachable, and
    # every family with Thermal in either type slot is normal to volcanic only.
    assert set(ENCOUNTER_ZONES) <= {a.id for a in AREAS.values()}, "encounter zone for an unknown area"
    seen_habitats = set()
    for a in AREAS.values():
        if a.styled or not a.encounters:
            assert a.id not in ENCOUNTER_ZONES, f"{a.id} should have no encounter zones"
            continue
        zones = ENCOUNTER_ZONES.get(a.id)
        assert zones, f"{a.id} has wild encounters but no zones"
        for z in zones:
            lo, hi = z["band"]
            assert 1 <= lo <= hi <= 100, f"{z['zone_id']}: bad band {z['band']}"
            assert z["habitat_id"] in _HABITATS, f"{z['zone_id']}: unknown habitat"
            tiles = {a.rows[y][x] for y in range(a.h) for x in range(a.w)
                     if a.rows[y][x] in z["tiles"]
                     and (z["rects"] is None or any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in z["rects"]))}
            assert tiles, f"{z['zone_id']}: no matching tiles on the map"
            if "g" in z["tiles"]:
                assert "g" in tiles, f"{z['zone_id']}: grass zone rect matches no tall grass"
            seen_habitats.add(z["habitat_id"])
    assert seen_habitats == set(_HABITATS), f"habitats without any zone: {sorted(set(_HABITATS) - seen_habitats)}"
    for f in _DB["families"]:
        for h in f["normal_habitats"]:
            assert h in seen_habitats, f"family {f['id']}: habitat {h} has no encounter zone"
    for sid, sp in SPECIES.items():
        if "Thermal" in sp.types:
            assert WILD_HOME.get(sid) == "volcanic", f"{sid}: Thermal species outside volcanic ({WILD_HOME.get(sid)})"

    # ---- chests: at most one town + one route + one wild place, each on an X tile with a reachable approach
    chest_areas = {area for area, chests in CHESTS.items() if chests}
    styled_chest_areas = {a for a in chest_areas if a == TOWN or AREAS[a].styled}
    assert len(styled_chest_areas) <= 1, "at most one town may hide a chest"
    assert len(chest_areas - styled_chest_areas - PLACE_AREAS) <= 1, "at most one route may hide a chest"
    assert len(chest_areas & PLACE_AREAS) <= 1, "at most one wild place may hide a chest"
    for area, chests in CHESTS.items():
        rows = rows_of(area)
        if area not in reach:                          # styled areas: walk from their start, like their validate()
            start = AREAS[area].start or (epi.START if area == epi.AREA_ID else None)
            reach[area] = _reach(rows, len(rows[0]), len(rows), start, solid) if start else set()
        for c in chests:
            cx, cy = c["tile"]
            assert rows[cy][cx] == "X", f"chest {c['key']} is not on an X tile"
            ok = reach[area] | reach_ab.get(area, set())
            assert any((cx + dx, cy + dy) in ok for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), \
                f"chest {c['key']} cannot be reached"
            for item, _n in c["loot"]:
                assert item in CATALOG, f"chest {c['key']} holds unknown item {item}"
    return True


#validate()
