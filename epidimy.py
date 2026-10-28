"""Epidimy Town - the settlement north of Route 1.  Laid out after the reference screenshot (terraced plateau with two
cottages on the upper left, a cave in the rock band, a fountain pond in the middle, a lake on the west, a row of cottages on
the east, the library and Scimon Center in the north-east and a supply mart by the south road).
Buildings are Riven Town's own sprites (town/bld_house_*, bld_cush, bld_mart); the Green Gym keeps its MPW sprite (no Riven equivalent).

This module is pure data (no pygame): the tile grid, buildings, NPCs and signs.  TileMap._render_epidimy draws it with Riven
Town's own renderer (townview.py): the same lawns, cobbled roads with kerbs, stone walls, coping-rimmed ponds, trees, lamps and
benches.  routes.py wires it in as area "epidimy", linked to the north end of Route 1.

Collision legend (the same letters as worldmap.OVERWORLD_SOLID, so TileMap collision works unchanged)
  G grass  F flower patch  P cobbled road  A stairs (walkable)  L lamp post (walk-past, drawn as a prop)  D door
  Solid: T tree  w water  h stone wall (rock band / plateau rim)  B building  S signpost  b bench  u bush  r boulder  f fence
Peaceful town: no tall grass, so no wild encounters here."""
from worldmap import (BACK_ZONES, Building, Interior, INTERIOR_SOLID, PALETTES, ROOM_ROWS, _npc, _trainer,
                      open_backs, trim_footprints)

AREA_ID = "epidimy"
NAME = "Epidimy Town"
W, H = 32, 29
FOREST_Y = 25                      # rows from here down are the southern forest (with the Route 1 road cut through it)
FOUNTAIN_REGION = (12, 11, 5, 3)   # the fountain pond (x, y, w, h in tiles): the only water with a jet
CHEST = (1, 12)                    # a hidden supply chest in the nook behind the west lake (routes.CHESTS)
LEGEND = "GFPALDTwhBSbureX"        # every letter the grid may contain (validated below; e = walk-behind row)
SOLID = set("TwhBSburX")

# arrival tiles: one step inside the map from the road that links to Route 1 (x 6..9 on both sides)
ROUTE1_GATE_X = (6, 7, 8, 9)
# gates of the wider network (kanto.py wires these to Routes 2 and 22): north over the plateau lane, west through the forest
NORTH_GATE_X = (6, 7)
WEST_GATE_Y = (20, 21)
START = (7, H - 2)


# --------------------------------------------------------------------------- grid construction
def _build():
    g = [["G"] * W for _ in range(H)]

    def rect(x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = ch

    def spans(rows, ch):                                  # rows: {y: (x0, x1)}
        for y, (x0, x1) in rows.items():
            rect(x0, y, x1, y, ch)

    def put(cells, ch, only="G"):
        for x, y in cells:
            if g[y][x] in only:
                g[y][x] = ch

    rect(0, 0, W - 1, 1, "h")                             # the rock band along the top of the map
    rect(0, 2, 0, H - 1, "T")                             # forest edge, west and east
    rect(W - 1, 2, W - 1, H - 1, "T")
    rect(0, FOREST_Y, W - 1, H - 1, "T")                  # southern forest ...
    rect(ROUTE1_GATE_X[0], FOREST_Y, ROUTE1_GATE_X[-1], H - 1, "P")   # ... with the road to Route 1 cut through it

    # raised plateau (upper left): grass inside, rim on the south and east, stairs down in the middle of the south rim
    rect(0, 2, 0, 8, "h")
    rect(13, 2, 13, 8, "h")
    rect(0, 8, 13, 8, "h")
    rect(6, 8, 7, 8, "A")
    rect(2, 7, 12, 7, "P")                                # road along the foot of the two cottages
    rect(12, 2, 12, 7, "P")                               # road up to the cave
    g[1][12] = "h"                                        # the cave mouth (art in epidimy_view, dialogue in SIGNS)

    # roads of the lower town
    rect(6, 9, 9, 13, "P")                                # landing below the stairs
    rect(6, 14, 29, 15, "P")                              # east-west high street
    rect(7, 16, 8, FOREST_Y - 1, "P")                             # south road
    rect(17, 8, 18, 13, "P")                              # up to the north-east quarter
    rect(18, 8, 29, 9, "P")
    rect(27, 6, 27, 7, "P")                               # to the Scimon Center door
    rect(10, 22, 19, 22, "P")                             # forecourt of Corinne's house and the mart

    # water
    spans({13: (2, 4), 14: (2, 5), 15: (2, 5), 16: (2, 5), 17: (2, 5), 18: (3, 5), 19: (3, 4)}, "w")   # west lake
    rect(12, 11, 16, 13, "w")                             # fountain pond
    spans({18: (21, 25), 19: (20, 26), 20: (21, 25)}, "w")                                              # south-east pond

    # buildings (footprint x, y, w, h; the door is the bottom-centre tile)
    for b in BUILDINGS:
        fx, fy, fw, fh = b.footprint
        rect(fx, fy, fx + fw - 1, fy + fh - 1, "B")
        g[b.door[1]][b.door[0]] = "D"

    # scenery
    put(((1, 2), (2, 2), (11, 3), (3, 10), (4, 10), (3, 12)), "T")
    rect(14, 2, 17, 6, "T")                               # the grove north of the fountain (also seals the pocket beside the gym)
    rect(28, 16, 30, 21, "T")
    put(((27, 18), (27, 19), (27, 20), (28, 22), (29, 22), (30, 22)), "T")
    put(((10, 12), (13, 18), (27, 17), (30, 12), (22, 16), (9, 20)), "u")
    put(((9, 16), (23, 16), (3, 6), (5, 9), (31 - 3, 12)), "F")
    put(((6, 9), (9, 9), (1, 7), (17, 14), (12, 14), (24, 9), (22, 14), (26, 14), (30, 8)), "L", only="GPF")  # lamp posts
    g[12][5] = "b"                                        # benches
    g[18][6] = "b"
    for (x, y) in SIGNS:
        if (x, y) != CAVE:
            g[y][x] = "S"
    g[CHEST[1]][CHEST[0]] = "X"                           # a hidden supply chest behind the west lake (routes.CHESTS)
    put(((1, 13), (2, 12)), "T")                          # trees seal the nook so the chest stays tucked away
    # the wider network's gates: north through the rock band above the plateau lane (Route 2),
    # west through the southern forest (Route 22)
    rect(NORTH_GATE_X[0], 0, NORTH_GATE_X[-1], 1, "P")
    rect(0, WEST_GATE_Y[0], 6, WEST_GATE_Y[-1], "P")
    return ["".join(r) for r in g]


# --------------------------------------------------------------------------- signs and NPCs
CAVE = (12, 1)
SIGNS = {
    (10, 14): ["Signpost: Epidimy Town.",
               "North: the Highland Terrace - two cottages and the cave.",
               "North-east: the Green Gym, Cush's Repair Nook and the Town Hall.",
               "East: cottages. South: Route 1."],
    (13, 21): ["Signpost: Epidimy Supply Mart - open daily. Containment Modules and repair kits."],
    CAVE: ["The cave mouth is dark and cold. A rope barrier and a notice: 'Survey in progress - closed until further notice.'"],
}

NPCS = [
    _npc("epi-pim", 15, 14, "#d98aa6", "#6a3a4a", "Lass Pim", [
        "Pim: Welcome to Epidimy Town, {name}!",
        "Pim: The fountain in the middle is older than the town itself.",
        "Pim: Folks say a Scimon sleeps in the cave, but the survey team won't let anyone near it."]),
    _npc("epi-odo", 6, 17, "#7f9ec9", "#3f4a5a", "Fisher Ora", [
        "Ora: Nothing bites in the west lake, but it's calming just to sit here.",
        "Ora: The lake feeds the fountain through an old channel under the road."]),
    _npc("epi-fenn", 22, 15, "#8fae6f", "#4a5a34", "Gardener Fenn", [
        "Fenn: These cottages all have window boxes - I plant them every spring.",
        "Fenn: Mind the pond, {name}, the bank is slippery."]),
    _npc("epi-rafi", 24, 16, "#e0c48a", "#6a4a2a", "Young Rina", [
        "Rina: Race you to the Scimon Center! ...Oh, {name}, you're not racing? Fine.",
        "Rina: Heal up there before you go anywhere dangerous."]),
]


# --------------------------------------------------------------------------- buildings (Riven Town's own sprites)
def _house(id_, name, sprite, fx, fy, npc):
    return Building(id_, name, "House", "house", (fx + 1, fy + 3), (fx + 1, fy + 4), (fx, fy, 3, 4),
                    f"town/bld_house_{sprite}.png",
                    Interior(f"{id_}-interior", ROOM_ROWS["house"], (5, 9), (5, 8), [npc], PALETTES["store"], spec="house"),
                    area=AREA_ID)


BUILDINGS = [
    # two cottages on the plateau
    _house("epi-pell", "Pell's House", 0, 3, 3, _npc("epi-pell-npc", 6, 6, "#8fae6f", "#4a5a34", "Pell", [
        "Pell: I keep the best garden on this side of town.",
        "Pell: The road to the east is still closed, I'm afraid."])),
    _house("epi-brin", "Brin's House", 1, 8, 3, _npc("epi-brin-npc", 6, 6, "#c96a8f", "#5a3a44", "Brin", [
        "Brin: The view from up here is the best in town.",
        "Brin: If you hear rumbling, it's just the cave settling."])),
    # the Green Gym (north-east, where the library used to stand) and the Scimon Center.
    # The gym interior is the ring, and the ring has an order: two single-file gates on the corridor are
    # guarded by the coaches -- Sora holds the west gate, Rook the east one and he won't fight before Sora
    # is beaten.  Leader Fern waits at the top of the ring and requires both (`requires` is checked by
    # overworld._challenge against the beaten trainers).  Beaten coaches step aside (`aside` tiles).
    Building("epi-gym", "Epidimy Green Gym", "Green Gym", "hall", (21, 7), (21, 8), (18, 1, 7, 7), "mpw/buildings/gym_green.png",
             Interior("epi-gym-interior", ROOM_ROWS["gym-ring"], (7, 12), (7, 11), [
                 _trainer("gym-sora", 4, 7, "Coach Sora", [
                     "Sora: Welcome to the ring, {name}!",
                     "Sora: I hold the west gate, and this gate opens for battles only. Show me your form!",
                 ], [("sporelet-baby", 10)],
                     post=["Sora: Solid footwork out there.",
                           "Sora: The east gate is Rook's - and he doesn't move for anyone."],
                     facing="down", aside=(5, 9)),
                 _trainer("gym-rook", 10, 7, "Coach Rook", [
                     "Rook: So you're climbing the ring. Bold.",
                     "Rook: Gym rules, though - Sora takes you first, always.",
                     "Rook: Beat her, then bring it on!",
                 ], [("sproutle-baby", 11)],
                     post=["Rook: Hah! Clean win.",
                           "Rook: Fern's waiting at the top of the ring. Don't keep her waiting."],
                     facing="down", requires=("gym-sora",),
                     locked=["Rook: Whoa there, {name} - gym rules.",
                             "Rook: Sora holds the west gate and she tests everyone first.",
                             "Rook: Beat her, and I'm all yours."],
                     aside=(9, 9)),
                 _trainer("epi-leader", 7, 4, "Leader Fern", [
                      "Fern: You made it around the ring, {name} - most never do.",
                      "Fern: The Green Gym grows its champions slowly... and roots out the rest.",
                      "Fern: My Petalug and Florabot will do exactly that. Let's battle!",
                  ], [("petalug", 12), ("florabot", 14)],
                      post=["Fern: Magnificent, {name}!",
                            "Fern: The Green Gym is proud to have rooted for you. Come back any time."],
                      facing="down", stamp="green", disc="verdantdisc",
                     requires=("gym-sora", "gym-rook"),
                     locked=["Fern: Not so fast, {name}!",
                             "Fern: The ring has an order - Sora first, then Rook.",
                             "Fern: Clear both gates, and I'll gladly show you what a champion looks like."]),
             ], PALETTES["hall"], spec="gym-ring"), area=AREA_ID),
    # every repair centre is a Cush franchise: same name, same sprite, same nook (see sprites.LOOK_ALIKE)
    Building("epi-center", "Cush's Repair Nook", "Cush", "repair", (27, 5), (27, 6), (25, 2, 5, 4), "town/bld_cush.png",
             Interior("epi-center-interior", ROOM_ROWS["cush"], (5, 9), (5, 8), [
                  _npc("epi-cush", 5, 4, "#e07a8a", "#8a3a4a", "Cush", [
                      "Cush: Welcome to the nook, {name}.",
                      "Cush: Hand me your Scimons and I'll patch up their systems - no charge."], service="repair")],
                       PALETTES["repair"], spec="cush"),
             shop=[("repaircell", 200), ("nanorepair", 600)], repairs=True, has_database=True, area=AREA_ID,
             pass_item="epipass"),
    # cottages above the high street (the hall stands where Milo's cottage used to, next to the gym)
    _house("epi-hale", "Hester's House", 1, 24, 10, _npc("epi-hale-npc", 6, 6, "#c98a4a", "#5a3a24", "Old Hester", [
        "Hester: Back in my day, Route 1 was nothing but mud.",
        "Hester: Now there's a ledge to hop down. Progress, hmph."])),
    _house("epi-tamsin", "Tamsin's House", 2, 28, 10, _npc("epi-tamsin-npc", 6, 6, "#c9b06f", "#5a4a2a", "Tamsin", [
        "Tamsin: I moved here for the quiet. And the pond.",
        "Tamsin: The ducks never showed up, though."])),
    # the town hall: Mayoress Vela issues the Epidimy Town Pass (services here are pass-gated)
    Building("epi-hall", "Epidimy Town Hall", "Hall", "hall", (21, 13), (21, 14), (19, 10, 5, 4), "town/bld_hall.png",
             Interior("epi-hall-interior", ROOM_ROWS["hall"], (5, 9), (5, 8), [
                 _npc("epi-mayor", 6, 4, "#7fae9a", "#3a5a4a", "Mayoress Vela", [
                     "Vela: Welcome to Epidimy Town Hall, {name}.",
                     "Vela: Epidimy runs on trust, but even trust needs paperwork.",
                     "Vela: The highland air makes every Scimon shinier - ask any trainer."], gives="epipass")],
                      PALETTES["hall"], spec="hall"), area=AREA_ID),
    # beside the west lake and the mart
    _house("epi-corin", "Corinne's House", 2, 10, 16, _npc("epi-corin-npc", 6, 6, "#c98a4a", "#5a3a24", "Corinne", [
        "Corinne: Ora fishes in the lake all day. I've never seen her catch anything.",
        "Corinne: Come by anytime, {name}."])),
    Building("epi-mart", "Epidimy Supply Mart", "Supply Mart", "store", (16, 21), (16, 22), (14, 16, 5, 6), "town/bld_mart.png",
             Interior("epi-mart-interior", ROOM_ROWS["mart"], (6, 12), (6, 11), [
                 _npc("epi-clerk", 4, 6, "#6fae86", "#3f5f4a", "Clerk Bram", [
                     "Bram: Welcome to the Epidimy Supply Mart, {name}!",
                     "Bram: Same stock as the Riven shop, just closer to the highland."], service="shop")],
                      PALETTES["store"], spec="mart"),
              shop=[("repaircell", 200), ("nanorepair", 600), ("stabilizer", 300), ("standard", 200),
                    ("cryo", 600), ("magnetic", 600), ("bio", 600)], area=AREA_ID, pass_item="epipass"),
]
DOOR_INDEX = {b.door: b for b in BUILDINGS}

# walk-behind backs + fade zones for every Epidimy building; the hall's sprite is taller than its footprint and
# overhangs the road behind it, so its fade zone reaches up over the road as well
ROWS = open_backs(trim_footprints(_build(), BUILDINGS), BUILDINGS)
BACK_ZONES["epi-hall"] = (18, 8, 23, 13)


def _ponds():
    """Bounding boxes (x, y, w, h) of every water body, for the animated pond layer."""
    seen, out = set(), []
    for y in range(H):
        for x in range(W):
            if ROWS[y][x] != "w" or (x, y) in seen:
                continue
            stack, cells = [(x, y)], []
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (cx + dx, cy + dy)
                    if n not in seen and 0 <= n[0] < W and 0 <= n[1] < H and ROWS[n[1]][n[0]] == "w":
                        seen.add(n)
                        stack.append(n)
            xs, ys = [c[0] for c in cells], [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    return out


POND_REGIONS = _ponds()


def building_at_door(x, y):
    return DOOR_INDEX.get((x, y))


def validate():
    """Data checks that run at import: shape, legend, doors, NPC placement and full walkability from the Route 1 gate."""
    assert len(ROWS) == H and all(len(r) == W for r in ROWS), "epidimy: ragged rows"
    assert all(c in LEGEND for r in ROWS for c in r), "epidimy: unknown tile letter"
    for b in BUILDINGS:
        assert b.area == AREA_ID
        x, y = b.door
        assert ROWS[y][x] == "D", f"{b.id}: door is not a D tile"
        ex, ey = b.entry_return
        assert ROWS[ey][ex] not in SOLID, f"{b.id}: entry_return is solid"
        fx, fy, fw, fh = b.footprint
        assert (x, y) == (fx + fw // 2, fy + fh - 1), f"{b.id}: door is not the bottom-centre tile"
        assert any(ROWS[yy][xx] == "B" for yy in range(fy, fy + fh) for xx in range(fx, fx + fw)), f"{b.id}: footprint has no building tile"
        i = b.interior                                   # the room itself: exits, spawn and NPCs sit on open tiles
        ex, ey = i.exit_tile
        assert i.rows[ey][ex] == "E", f"{b.id}: interior exit tile is not E"
        sx, sy = i.spawn
        assert i.rows[sy][sx] not in INTERIOR_SOLID, f"{b.id}: interior spawn is solid"
        for n in i.npcs:
            assert i.rows[n["y"]][n["x"]] not in INTERIOR_SOLID, f"{b.id}: interior NPC {n['id']} is on a solid tile"
    ids = [b.id for b in BUILDINGS]
    assert len(ids) == len(set(ids)), "duplicate building id"
    seen, stack = {START}, [START]
    assert ROWS[START[1]][START[0]] not in SOLID, "epidimy: start is solid"
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in seen and 0 <= nx < W and 0 <= ny < H and ROWS[ny][nx] not in SOLID:
                seen.add((nx, ny))
                stack.append((nx, ny))
    open_tiles = {(x, y) for y in range(H) for x in range(W) if ROWS[y][x] not in SOLID}
    assert open_tiles == seen, f"epidimy: unreachable open tiles {sorted(open_tiles - seen)}"
    for b in BUILDINGS:
        assert b.door in seen, f"{b.id}: door unreachable"
    for n in NPCS:
        assert (n["x"], n["y"]) in seen, f"NPC {n['id']} is walled off"
    blocked = {(n["x"], n["y"]) for n in NPCS}                    # an NPC must never cut the town in two
    seen2, stack = {START}, [START]
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in seen2 and (nx, ny) in seen and (nx, ny) not in blocked:
                seen2.add((nx, ny))
                stack.append((nx, ny))
    assert seen2 == seen - blocked, f"an NPC blocks part of Epidimy: {sorted(seen - blocked - seen2)}"
    for (sx, sy) in SIGNS:
        assert any((sx + dx, sy + dy) in seen for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), f"sign {(sx, sy)} can't be read"
        assert ROWS[sy][sx] in SOLID, f"sign {(sx, sy)} must be a solid tile"
    for x in ROUTE1_GATE_X:
        assert ROWS[H - 1][x] == "P" and ROWS[H - 2][x] == "P", "road to Route 1 is broken"
    return True


validate()
