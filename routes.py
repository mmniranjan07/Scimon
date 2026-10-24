"""Outdoor areas beyond Riven Town.  Route 1 is laid out after a reference map: a winding path between stone ledges, with
tall-grass patches, fences, boulders and forest edges, linked to the town by its north road.

Tile legend = the overworld legend in worldmap.py, using only tiles the game already draws:
  G lawn   F flower lawn   g tall grass (wild encounters)   P cobbled road / stone steps through the ledges
  T tree   u bush   r boulder   l one-way ledge (hop down, never up)   f fence   h stone ledge wall (solid)   S signpost
The ridges of the reference are `l` ledges: walk into one from the tile above and you hop over it; from the sides or below it blocks. Its stairs are `P` gaps; the leafy undergrowth is walkable lawn.

Areas are joined by LINKS: stepping on a link tile fades to the target area.  validate() (run at import, like worldmap's)
guarantees Route 1 can actually be walked: every open tile, every patch of tall grass, the NPC and every sign are
reachable from the town entrance, and the links line up with the town."""
import math

import epidimy as epi
import worldmap as wm

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
    """An outdoor map.  `styled` areas (Epidimy Town) are drawn by their own renderer and carry buildings with doors."""

    def __init__(self, id, name, rows, signs=None, npcs=(), buildings=(), styled=False):
        self.id, self.name, self.rows, self.signs, self.npcs = id, name, rows, signs or {}, list(npcs)
        self.buildings, self.styled = list(buildings), styled
        self.w, self.h = len(rows[0]), len(rows)


TOWN = "overworld"                      # key of the town map in OverworldScene
AREAS = {"route1": Area("route1", "Route 1", ROUTE1_ROWS, ROUTE1_SIGNS, ROUTE1_NPCS),
         epi.AREA_ID: Area(epi.AREA_ID, epi.NAME, epi.ROWS, epi.SIGNS, epi.NPCS, epi.BUILDINGS, styled=True)}

# area id -> {tile: (target area id, target tile, facing on arrival)}.  Arrival tiles are one step inside the target so a
# link is never re-triggered on arrival.
LINKS = {
    TOWN: {(21, 0): ("route1", (11, 28), "up")},
    "route1": {(10, 29): (TOWN, (21, 1), "down"), (11, 29): (TOWN, (21, 1), "down"),
               (12, 29): (TOWN, (21, 1), "down"),
               # the north end of Route 1 (road tiles x 6..9 of row 0) leads to Epidimy Town's south road
               **{(x, 0): (epi.AREA_ID, (x, epi.H - 2), "up") for x in epi.ROUTE1_GATE_X}},
    epi.AREA_ID: {(x, epi.H - 1): ("route1", (x, 1), "down") for x in epi.ROUTE1_GATE_X},
}

ROUTE1_START = (11, 28)


# ---------------------------------------------------------------------------
# Healers: places that restore the party.  After a wipe the player is sent back to the nearest one they have
# visited, or (failsafe, OverworldScene.end_wild_battle) the nearest one in an area they have already been
# through, so dying can never strand them nor skip them ahead: Prof. Venn by the town plaza and the two
# Cush's Repair Nook franchises (Riven Town and Epidimy).  `tile` is where the player is set down, one step from the healer.
HEALERS = [
    dict(id="venn", name="Prof. Venn", area=TOWN, tile=(20, 8), facing="up"),
    dict(id="cush", name="Cush's Repair Nook", area=TOWN,
         tile=next(b.entry_return for b in wm.BUILDINGS if b.id == "cush"), facing="down"),
    dict(id="epi-center", name="Cush's Repair Nook", area=epi.AREA_ID,
         tile=next(b.entry_return for b in epi.BUILDINGS if b.id == "epi-center"), facing="down"),
]


def travel_cost(start_area, start_tile, target_area, target_tile, _seen=()):
    """Estimated walking distance in tiles between two spots, or None when no link path reaches the target.
    Within one area it is the straight tile distance; across areas it chains through the area's link tiles
    (+1 per crossing), so it is approximate but consistent enough to pick the nearest healer."""
    if start_area == target_area:
        return math.hypot(start_tile[0] - target_tile[0], start_tile[1] - target_tile[1])
    best = None
    for (lx, ly), (dst, (tx, ty), _) in LINKS.get(start_area, {}).items():
        if dst in _seen:
            continue
        sub = travel_cost(dst, (tx, ty), target_area, target_tile, _seen + (start_area,))
        if sub is None:                    # that branch of the map can't reach the target
            continue
        c = math.hypot(start_tile[0] - lx, start_tile[1] - ly) + 1 + sub
        if best is None or c < best:
            best = c
    return best


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


def validate():
    for a in AREAS.values():
        assert all(len(r) == a.w for r in a.rows), f"{a.id}: ragged rows"
        if not a.styled:                                       # styled areas validate their own legend (epidimy.validate)
            assert all(c in "GFgPTurfhSl" for r in a.rows for c in r), f"{a.id}: unknown tile letter"
    solid = wm.OVERWORLD_SOLID                                 # includes the ledge tile: you can only *land* beside it
    for src, links in LINKS.items():
        rows = wm.MAP_ROWS if src == TOWN else AREAS[src].rows
        for (x, y), (dst, (tx, ty), facing) in links.items():
            assert rows[y][x] not in solid, f"link {src}{(x, y)} is on a solid tile"
            drows = wm.MAP_ROWS if dst == TOWN else AREAS[dst].rows
            assert drows[ty][tx] not in solid and (tx, ty) not in LINKS.get(dst, {}), f"arrival {dst}{(tx, ty)} is bad"
            assert facing in ("up", "down", "left", "right")
    # the town's north road must be the link tile, and the route must be fully walkable from the entrance
    assert wm.MAP_ROWS[0][21] == "P" and wm.MAP_ROWS[1][21] == "P", "town road does not reach the north exit"
    r1 = AREAS["route1"]
    seen = _reach(r1.rows, r1.w, r1.h, ROUTE1_START, solid)
    open_tiles = {(x, y) for y in range(r1.h) for x in range(r1.w) if r1.rows[y][x] not in solid}
    assert open_tiles == seen, f"Route 1 has unreachable open tiles: {sorted(open_tiles - seen)}"
    assert any(r1.rows[y][x] == "g" for y in range(r1.h) for x in range(r1.w)), "Route 1 has no tall grass"
    assert all(t in seen for t in LINKS["route1"]), "Route 1's exit to the town is not reachable"
    # ledges are one-way, so make sure nobody can be trapped: from every tile the way back to the exit must exist
    exits = set(LINKS["route1"])
    for t in sorted(seen):
        assert exits & _reach(r1.rows, r1.w, r1.h, t, solid), f"Route 1 soft-lock: no way back to the exit from {t}"
    ledges = [(x, y) for y in range(r1.h) for x in range(r1.w) if r1.rows[y][x] == wm.LEDGE_DOWN]
    assert not ledges or any((x, y - 1) in seen and (x, y + 1) in seen for x, y in ledges), "no ledge can actually be hopped"
    for (sx, sy) in r1.signs:
        assert r1.rows[sy][sx] == "S", f"sign {(sx, sy)} is not on an S tile"
        assert any((sx + dx, sy + dy) in seen for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), f"sign {(sx, sy)} can't be read"
    assert sum(c == "S" for r in r1.rows for c in r) == len(r1.signs), "an S tile has no sign text"
    for n in r1.npcs:
        assert (n["x"], n["y"]) in seen, f"NPC {n['id']} is walled off"
        if "battle" in n:
            assert isinstance(n["battle"], tuple) and len(n["battle"]) == 2, f"trainer {n['id']} has no battle spec"
            assert n.get("facing") in ("up", "down", "left", "right"), f"trainer {n['id']} has a bad facing"
    blocked_by_npc = {(n["x"], n["y"]) for n in r1.npcs}                   # an NPC must never cut the route in two
    seen2 = _reach(r1.rows, r1.w, r1.h, ROUTE1_START, solid, blocked_by_npc)
    assert seen2 == seen - blocked_by_npc, f"an NPC blocks part of Route 1: {sorted(seen - blocked_by_npc - seen2)}"
    # healer warp tiles must be walkable, unoccupied and never on the route itself (healers live in the towns)
    for h in HEALERS:
        assert h["area"] in (TOWN, epi.AREA_ID), f"healer {h['id']} is not in a town"
        rows = wm.MAP_ROWS if h["area"] == TOWN else epi.ROWS
        assert rows[h["tile"][1]][h["tile"][0]] not in wm.OVERWORLD_SOLID, f"healer {h['id']} warps onto a solid tile"
        npcs = wm.NPCS if h["area"] == TOWN else epi.NPCS
        assert h["tile"] not in {(n["x"], n["y"]) for n in npcs}, f"healer {h['id']} warps onto an NPC"
        assert h["facing"] in ("up", "down", "left", "right"), f"healer {h['id']} has a bad facing"
    return True


validate()
