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
  d mooring post   J lighthouse (2x2 footprint)                       (solid props, see townview.build_props)
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
    `encounters` says whether the area has wild tall grass; `ponds` / `jets` / `cave` feed the styled renderer."""

    def __init__(self, id, name, rows, signs=None, npcs=(), buildings=(), styled=False,
                 start=None, encounters=True, ponds=(), jets=(), cave=None):
        self.id, self.name, self.rows, self.signs, self.npcs = id, name, rows, signs or {}, list(npcs)
        self.buildings, self.styled = list(buildings), styled
        self.start = start
        self.encounters = encounters
        self.ponds, self.jets, self.cave = list(ponds), list(jets), cave
        self.w, self.h = len(rows[0]), len(rows)


ROUTE1_START = (11, 28)
TOWN = "overworld"                      # key of the town map in OverworldScene

# ---------------------------------------------------------------------------
# Wild encounters: every grass-bearing area draws from its own biome table.  A species' home biome comes from
# species_expanded.WILD_HOME (the field survey: Botanic/Bio/Atmospheric/Chemical/Mechanical/Radiant in the grass
# biomes, Hydro on the water, Cryo in the highland snow country, Thermal by the volcanic shores, Geologic and
# Metallic in the caves, Electric on the grid + tunnel, Plasma/Quantum/Nano/Digital on Aurum's city roads,
# Cosmic/Shadow by Dusklight's monuments and the deep sea).  Levels scale with distance from Riven Town.
BIOME_AREAS = {
    "meadow": [("route1", 2, 5), ("route4", 6, 10), ("route5", 7, 11), ("route6", 8, 12), ("route7", 8, 12),
               ("route8", 8, 12), ("route9", 8, 12), ("route11", 5, 9), ("route12", 9, 13), ("route13", 9, 13),
               ("route14", 10, 14), ("route15", 10, 14), ("route16", 9, 13), ("route17", 9, 13),
               ("route18", 10, 14), ("route24", 5, 9), ("route25", 5, 9)],
    "forest": [("route2", 3, 7), ("route2n", 4, 8), ("mossmere", 4, 8)],
    "water": [("route19", 12, 16), ("route20", 12, 16), ("route21", 12, 16), ("seaglass", 12, 16)],
    "highland": [("route22", 10, 15), ("ascent", 13, 17)],
    "volcanic": [("route20", 12, 16), ("route21", 12, 16)],
    "cave": [("route3", 6, 10), ("route10", 11, 15), ("mt_crescent", 11, 15)],
    "tunnel": [("hollowgate", 12, 16)],
    "city": [("route5", 7, 11), ("route6", 8, 12), ("route7", 8, 12), ("route8", 8, 12)],
    "ghost": [("route8", 8, 12), ("route10", 11, 15), ("route12", 9, 13), ("route13", 9, 13)],
    "plateau": [("ascent", 13, 17)],
    "sea": [("route19", 12, 16), ("route20", 12, 16), ("route21", 12, 16)],
}
_BIOME_WEIGHT = {"common": 10, "uncommon": 5, "rare": 2}
from data import STARTER_IDS

_CLASSIC_BASES = {"sporelet", "dewbit", "cindermite", "sparkit", "pebblon", "nanolyte"}
_WILD_EXCLUDED = _CLASSIC_BASES | set(STARTER_IDS)     # classics: Route 1 only; starters: never wild

AREA_ENCOUNTERS = {}
AREA_BIOMES = {}                       # area id -> set of home biomes its table draws from (test / debug)
for _biome, _areas in BIOME_AREAS.items():
    _pool = [(sid, _BIOME_WEIGHT[SPECIES[sid].rarity]) for sid, home in WILD_HOME.items() if home == _biome
             and not any(sid == b or sid.startswith(b + "-") for b in _WILD_EXCLUDED)]
    for _area, _lo, _hi in _areas:
        AREA_ENCOUNTERS.setdefault(_area, []).extend((sid, _w, _lo, _hi) for sid, _w in _pool)
        AREA_BIOMES.setdefault(_area, set()).add(_biome)
# the classic commons are Riven Town's own cast: Route 1 only (every other route draws purely from its biomes)
_CLASSIC = [("sporelet", 30), ("dewbit", 25), ("cindermite", 20), ("sparkit", 13), ("pebblon", 8), ("nanolyte", 4)]
AREA_ENCOUNTERS["route1"][:0] = [(sid, _w, 2, 5) for sid, _w in _CLASSIC]

# evolution stages join the wild pools: three-stage lines also spawn their babies (common, low levels) and
# finals (rare, top-of-band); two-stage lines spawn their finals rarely.  Biome purity holds: stages inherit
# the line's home biome, so each stage lands in exactly the areas its family already inhabits.
for _area, _table in list(AREA_ENCOUNTERS.items()):
    _extra = []
    _seen = {sid for sid, _w, _lo, _hi in _table}
    for sid, w, lo, hi in list(_table):
        chain = CHAIN_OF.get(sid, [sid])
        if len(chain) < 2:
            continue
        if any(chain[0] == b or chain[0].startswith(b + "-") for b in _WILD_EXCLUDED) and _area != "route1":
            continue
        pos = chain.index(sid)
        if pos > 0 and chain[0] not in _seen:                 # the baby of a three-stage line
            _extra.append((chain[0], max(4, int(w * 0.9)), lo, min(hi, lo + 2)))
            _seen.add(chain[0])
        if pos < len(chain) - 1 and chain[-1] not in _seen:   # the final stage, rare and high-level
            _extra.append((chain[-1], max(2, int(w * 0.2)), max(lo, hi - 3), hi + 2))
            _seen.add(chain[-1])
    _table.extend(_extra)
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
                     start=_r.start, encounters=_r.encounters)
for _k, _v in kanto.LINKS.items():
    LINKS.setdefault(_k, {}).update(_v)
HEALERS_EXTRA = towns.HEALERS + kanto.HEALERS

# Outdoor loot chests (layered_room.FieldChest), area id -> [dict(tile, key, loot)].  House rule, enforced in
# validate(): at most ONE town and ONE route hide a chest, so what they hold stays special.
CHESTS = {
    epi.AREA_ID: [dict(tile=epi.CHEST, key="epidimy:chest",
                       loot=(("hydrocell", 1), ("nanorepair", 2)))],
    **kanto.CHESTS,
}


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


ROUTE_LEGEND = "GFgPTurfhSl" + "sW" + "Qijvz" + "RIVU" + "XnZoCtKdJ" + "BDe" + "Hw"


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
    missing = (set(AREAS) | {TOWN}) - seen_areas
    assert not missing, f"areas unreachable from the town: {sorted(missing)}"

    # the town's north road must be the link tile, and the route must be fully walkable from the entrance
    assert wm.MAP_ROWS[0][21] == "P" and wm.MAP_ROWS[1][21] == "P", "town road does not reach the north exit"

    # ---- per non-styled area: everything reachable, ledges never soft-lock, signs/NPCs/grass sane
    reach = {}
    for a in AREAS.values():
        if a.styled:
            continue
        arrivals = {(tx, ty) for links in LINKS.values() for (tgt, (tx, ty), _f) in links.values() if tgt == a.id}
        assert arrivals, f"{a.id}: no way in"
        seen = set()
        for s in arrivals:
            seen |= _reach(a.rows, a.w, a.h, s, solid)
        reach[a.id] = seen
        open_tiles = {(x, y) for y in range(a.h) for x in range(a.w) if a.rows[y][x] not in solid}
        assert open_tiles == seen, f"{a.id} has unreachable open tiles: {sorted(open_tiles - seen)}"
        exits = set(LINKS.get(a.id, {}))
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
        blocked_by_npc = {(n["x"], n["y"]) for n in a.npcs}        # an NPC must never cut the route in two
        assert not blocked_by_npc & exits, f"{a.id}: an NPC stands on a link tile"
        seen2 = set()
        for s in arrivals:
            seen2 |= _reach(a.rows, a.w, a.h, s, solid, blocked_by_npc)
        assert seen2 == seen - blocked_by_npc, f"an NPC blocks part of {a.id}: {sorted(seen - blocked_by_npc - seen2)}"

    # ---- healers: warp tiles must be walkable, unoccupied and never on a route (healers live in the towns)
    for h in HEALERS:
        assert h["area"] == TOWN or h["area"] in AREAS, f"healer {h['id']} is not in a known area"
        rows = rows_of(h["area"])
        assert rows[h["tile"][1]][h["tile"][0]] not in solid, f"healer {h['id']} warps onto a solid tile"
        assert h["tile"] not in {(n["x"], n["y"]) for n in npcs_of(h["area"])}, f"healer {h['id']} warps onto an NPC"
        assert h["facing"] in ("up", "down", "left", "right"), f"healer {h['id']} has a bad facing"

    # ---- wild encounters: every grass-bearing area has a valid table, tables only name real species,
    # and the biome rule holds: outside Route 1 no species appears outside its home biome
    assert set(AREA_ENCOUNTERS) <= {a.id for a in AREAS.values()}, "encounter table for an unknown area"
    for a in AREAS.values():
        if a.styled or not a.encounters:
            continue
        table = AREA_ENCOUNTERS.get(a.id)
        assert table, f"{a.id} has wild encounters but no table"
        for sid, w, lo, hi in table:
            assert sid in SPECIES and w > 0 and 1 <= lo <= hi <= 40, (a.id, sid, w, lo, hi)
            if a.id != "route1":
                assert WILD_HOME.get(sid, a.id) in AREA_BIOMES.get(a.id, set()), \
                    f"{a.id}: {sid} ({WILD_HOME.get(sid)}) is outside its biome"
                _base = sid.replace("-baby", "").replace("-mid", "").replace("-final", "")
                assert _base not in {"sporelet", "dewbit", "cindermite", "sparkit", "pebblon", "nanolyte"}, \
                    f"{a.id}: classic cast member {sid} escaped Route 1"
                assert _base not in STARTER_IDS, f"{a.id}: starter {sid} is never wild"

    # ---- chests: at most one town + one route, each on an X tile with a reachable approach
    chest_areas = {area for area, chests in CHESTS.items() if chests}
    styled_chest_areas = {a for a in chest_areas if a == TOWN or AREAS[a].styled}
    assert len(styled_chest_areas) <= 1, "at most one town may hide a chest"
    assert len(chest_areas - styled_chest_areas) <= 1, "at most one route may hide a chest"
    for area, chests in CHESTS.items():
        rows = rows_of(area)
        if area not in reach:                          # styled areas: walk from their start, like their validate()
            start = AREAS[area].start or (epi.START if area == epi.AREA_ID else None)
            reach[area] = _reach(rows, len(rows[0]), len(rows), start, solid) if start else set()
        for c in chests:
            cx, cy = c["tile"]
            assert rows[cy][cx] == "X", f"chest {c['key']} is not on an X tile"
            assert any((cx + dx, cy + dy) in reach[area] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), \
                f"chest {c['key']} cannot be reached"
            for item, _n in c["loot"]:
                assert item in CATALOG, f"chest {c['key']} holds unknown item {item}"
    return True


#validate()
