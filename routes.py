"""Outdoor areas beyond Riven Town.  Route 1 is laid out after a reference map: a winding path between stone ledges, with
tall-grass patches, fences, boulders and forest edges, linked to the town by its north road.

Tile legend = the overworld legend in worldmap.py, using only tiles the game already draws:
  G lawn   F flower lawn   g tall grass (wild encounters)   P cobbled road / stone steps through the ledges
  T tree   u bush   r boulder   f fence   h stone ledge wall (solid)   S signpost
Cliffs of the reference are the stone `h` wall; its stairs are `P` gaps in them; the leafy undergrowth is walkable lawn.

Areas are joined by LINKS: stepping on a link tile fades to the target area.  validate() (run at import, like worldmap's)
guarantees Route 1 can actually be walked: every open tile, every patch of tall grass, the NPC and every sign are
reachable from the town entrance, and the links line up with the town."""
import worldmap as wm

ROUTE1_ROWS = [
    "TuTTTTTTTTTTGSuhhhhhuuSGGFTTTT",
    "TFGruuhhhhhGGhhhGGFhhhhGGFGGTT",
    "uGGGhhhuuThPhhGGGGrGGGhhhuGrTT",
    "hhhPhGrrrTGFurGGGGGGGGGGhuGGTT",
    "uuGGGGFGGFGGGGGGGFfffGufhuuGTT",
    "TTTTTTuuhhhhhhhhhhhFGGGuhuuGTT",
    "TTTTTTuhhGGGGfGggGhgGGuhGGGGTT",
    "TTGGuuPhGGuuGfGgghGgGGFhuuGGTT",
    "TTgGGGPGGuuGGuGuuhGgGGhuTTGGTT",
    "TTggGGGGhuuGuGGhGGGuGGhTTTGGGG",
    "TTgguuFrhGGGGGGhffuuGGhTThhPhh",
    "TTggFuGhhhhhhGGPGFuugghuThFGGh",
    "TTuuGrGhTGGFGhGGGGGugghhhhGTGh",
    "TTTTGFhhTGuuFhGuGGGFGgGuGGGGGh",
    "TTTTGGhGGGuuuhhGGGGGGGGGGGGrrh",
    "TTTTGhhGGGuGuuhGuGGGFGGGrhGGGG",
    "TTTTGPGGGGGGuhGrFGGGuuGGGhFGuG",
    "TTTThhGGGGFGuhGGGGGGTTuuGhTGur",
    "TTTThTGGhhhhhGFuuuGGTTuuGhTFFu",
    "TTuuhTGFuuGGhTrTTTTrTTTTrhhGuu",
    "TTuFGPGGGGGGhTuTTTTuTTTTuuhGGF",
    "TTFGGhrGGFShuuTTTTTTTTTTTThGGG",
    "TTuuGGhGGGGhuuTTTTTTTTTTTThhhG",
    "TTTTTThfPPfhTTTTTTTTTTTTTTuuhT",
    "TTTTTThGPPGhTTTTTTTTTTTTTTuuhT",
]

ROUTE1_SIGNS = {
    (10, 21): ["Signpost: Route 1.", "South: Riven Town.",
               "North: tall grass, stone ledges and the way to the next town.",
               "Keep to the steps when a ledge blocks the path."],
    (13, 0): ["Signpost: North gate (west).", "The trail beyond is closed while the survey team works.", "Head back to Riven Town for now."],
    (22, 0): ["Signpost: North gate (east).", "The trail beyond is closed while the survey team works.", "Head back to Riven Town for now."],
}

ROUTE1_NPCS = [
    wm._npc("ranger", 10, 22, "#6f8f5a", "#4a3a24", "Ranger Dane", [
        "Ranger Dane: Welcome to Route 1!",
        "Ranger Dane: The tall grass is full of wild Scimons. Bring a healthy team.",
        "Ranger Dane: The stone ledges are too steep to climb - use the stairs.",
        "Ranger Dane: The north gates are shut for now. Come back once the survey is done.",
    ]),
]


class Area:
    def __init__(self, id, name, rows, signs=None, npcs=()):
        self.id, self.name, self.rows, self.signs, self.npcs = id, name, rows, signs or {}, list(npcs)
        self.w, self.h = len(rows[0]), len(rows)


TOWN = "overworld"                      # key of the town map in OverworldScene
AREAS = {"route1": Area("route1", "Route 1", ROUTE1_ROWS, ROUTE1_SIGNS, ROUTE1_NPCS)}

# area id -> {tile: (target area id, target tile, facing on arrival)}.  Arrival tiles are one step inside the target so a
# link is never re-triggered on arrival.
LINKS = {
    TOWN: {(21, 0): ("route1", (8, 22), "up")},
    "route1": {(8, 24): (TOWN, (21, 1), "down"), (9, 24): (TOWN, (21, 1), "down")},
}
ROUTE1_START = (8, 22)


def validate():
    for a in AREAS.values():
        assert all(len(r) == a.w for r in a.rows), f"{a.id}: ragged rows"
        assert all(c in "GFgPTurfhS" for r in a.rows for c in r), f"{a.id}: unknown tile letter"
    solid = wm.OVERWORLD_SOLID
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
    seen, stack = {ROUTE1_START}, [ROUTE1_START]
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cx + dx, cy + dy)
            if 0 <= n[0] < r1.w and 0 <= n[1] < r1.h and n not in seen and r1.rows[n[1]][n[0]] not in solid:
                seen.add(n)
                stack.append(n)
    open_tiles = {(x, y) for y in range(r1.h) for x in range(r1.w) if r1.rows[y][x] not in solid}
    assert open_tiles == seen, f"Route 1 has unreachable open tiles: {sorted(open_tiles - seen)}"
    assert any(r1.rows[y][x] == "g" for y in range(r1.h) for x in range(r1.w)), "Route 1 has no tall grass"
    assert all(t in seen for t in LINKS["route1"]), "Route 1's exit to the town is not reachable"
    for (sx, sy) in r1.signs:
        assert r1.rows[sy][sx] == "S", f"sign {(sx, sy)} is not on an S tile"
        assert any((sx + dx, sy + dy) in seen for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), f"sign {(sx, sy)} can't be read"
    assert sum(c == "S" for r in r1.rows for c in r) == len(r1.signs), "an S tile has no sign text"
    for n in r1.npcs:
        assert (n["x"], n["y"]) in seen, f"NPC {n['id']} is walled off"
    blocked_by_npc = {(n["x"], n["y"]) for n in r1.npcs}                   # an NPC must never cut the route in two
    seen2, stack = {ROUTE1_START}, [ROUTE1_START]
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cx + dx, cy + dy)
            if n in seen and n not in seen2 and n not in blocked_by_npc:
                seen2.add(n)
                stack.append(n)
    assert seen2 == seen - blocked_by_npc, f"an NPC blocks part of Route 1: {sorted(seen - blocked_by_npc - seen2)}"
    # the top gates (signposts) are the only place the trail leaves the map; both must be next to walkable ground
    return True


validate()
