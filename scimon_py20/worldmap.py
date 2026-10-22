"""Riven Town: tile layouts, buildings, interiors and NPCs. Port of V34's lib/game/worldmap.ts.

Overworld tile legend (revamped town)
  G grass   F flower bed   g tall grass (wild encounters)   P cobbled road   p plaza pavers   D door (walk onto it to enter)
  e back yard behind the Hall/Lab/Library/Mart (walkable)   L lamp post (walk-past, not solid)   s sand   z sand flowers (walkable decal)   W ocean (solid)   w pond (solid)   h sea wall (solid)   k sea-gate lantern pillar (solid)
  Solid scenery: T tree  B building  H hedge  f fence  c crop plot  b bench  N notice board  M market stall
                 O flower planter  x crates  y barrel  Y hay bale  S signpost  m mailbox  a scarecrow  u bush  r rock
  Beach (rows 17-20, original beach art): Q palm tree  i palm sprout  j beach rock  v tide pool (2x2 or 3x3)  -- all solid

Interior legend (its own namespace)
  # solid   . floor   E exit mat   C counter (solid, talk across it)   S shelf   M machine
  K bookcase   b bench   p plant   @ Sci-Database terminal (solid; face it and interact)
Rooms are built from sprite props in interiors.py; their collision grids are generated from the prop footprints."""
from dataclasses import dataclass, field
from typing import Optional

from mpw_sizes import SIZES

MAP_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTPTTTTTTTTTTTTTTTTTTTTTT",
    "TTGBBBBBTBBBBBFBBBBBFPFGBBBBBFBBBBBFGBBBFfTT",
    "TTGBBBBBFBBBBBFBBBBBFPFGBBBBBFBBBBBFGBBBFfTT",
    "TTGBBBBBFFBBBBFBBBBBLPLGBBBBBFBBBBBFGBBBFfTT",
    "TTGBBBBBGBBBBBFBBBBBGPGTBBBBBFBBBBBmGBDBFfTT",
    "TTGBBBBBYBBDBBFBBDBBGPOGBBDBBGBBDBBLPPPGGGTT",
    "TTTBBDBBGGOPLGGLOPGNGpppPPPPPPPPPPPPPBBBFfTT",
    "TTGxLPFxFFGPHHHHHPGpppppggggggggggggPBBBFfTT",
    "TTPPPPPPPPPPPPPPPPPpppppSGGGGGGGGGGGPBBBFfTT",
    "TTGfffffffffBBBBBFGbGPGGwwwwwwwwwwwLPBDBFfTT",
    "TTYfccaccccfBBBBBGTggPLFwwwwwwwwwwwGPPPGGGTT",
    "TTGfGGGGGGGfGBBBBFGggPGFwwwwwwwwwwwFPBBBFfTT",
    "TTyfcccGccafBBDBBGTggPGFwwwwwwwwwwwFPBBBFfTT",
    "TTGffffGffffGGPPPPPPPPGGGGGGGGGGGGGGPBBBFfTT",
    "TTGGGGGGxgggggggggggLPLGGGGGGLTGGGGLPBDBFfTT",
    "TTTTTPggggTTTTGHHHHHGPHHHHHHHHHHHHHHPPPTTTTT",
    "hhhhhhhhhhhhhhhhhhhhkPkhhhhhhhhhhhhhhhhhhhhh",
    "ssssssszssssszssissssssssszssssjvvssssssisss",
    "ssQssssssszsvvvssQssssssssssssssvvssQsssszsj",
    "ssszsvvssQsjvvvssssssssszssssQsssszsszvvssQs",
    "sjssivvsssssvvvssszssssssjsissszsssjssvvssss",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]
MAP_W, MAP_H = len(MAP_ROWS[0]), len(MAP_ROWS)
LEDGE_DOWN = "l"                                 # one-way ledge: hop DOWN over it (see TileMap.ledge_landing), solid from every other side
OVERWORLD_SOLID = set("TWwBhkHfcbNMOxyYSmauqrQijvlL")
INTERIOR_SOLID = set("#CSMKbp@ ")
PLAYER_START = (38, 5)


def _water_regions():
    """Bounding boxes of small decorative ponds (the plaza fountain, the yard pond) -- not the ocean."""
    seen, regions = set(), []
    for y in range(MAP_H):
        for x in range(MAP_W):
            if MAP_ROWS[y][x] != "w" or (x, y) in seen:
                continue
            stack, cells = [(x, y)], []
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < MAP_W and 0 <= ny < MAP_H and (nx, ny) not in seen and MAP_ROWS[ny][nx] == "w":
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            if len(cells) <= 80:
                xs, ys = [c[0] for c in cells], [c[1] for c in cells]
                regions.append((min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    return regions


POND_REGIONS = _water_regions()


# --------------------------------------------------------------------------- NPCs
def _npc(id, x, y, color, hair, name, lines, heals=False, service=None):
    return dict(id=id, x=x, y=y, color=color, hair=hair, name=name, lines=lines, heals=heals, service=service)


NPCS = [
    _npc("venn", 20, 7, "#c9c4d6", "#b7b2c4", "Prof. Venn", [
        "Prof. Venn: Welcome to Riven Town!",
        "Prof. Venn: Wild Scimons roam the tall grass by the Farms.",
        "Prof. Venn: Step into it to trigger an encounter.",
        "Prof. Venn: Come see me anytime - I'll restore your Scimons to full.",
    ], heals=True),
    _npc("kael", 23, 9, "#c96a4a", "#5a3a2a", "Kael", [
        "Kael: So the professor gave you a Scimon too?",
        "Kael: Weaken a wild one, lower its Stability,",
        "Kael: then throw a Containment Module to catch it!",
        "Kael: I'll surpass you as a Researcher. Just watch.",
    ]),
    _npc("ilo", 33, 7, "#7f9ec9", "#3f4a5a", "Warden Ila", [
        "Warden Ila: Welcome to Riven Town.",
        "Warden Ila: The Supply Mart stocks Containment Modules.",
        "Warden Ila: Cush's repair nook patches up your Scimons free of charge.",
    ]),
    _npc("jori", 41, 10, "#8fae6f", "#4a5a34", "Jora", [
        "Jora: There's a couple more houses down this row.",
        "Jora: Follow the main path south and you'll hit the beach.",
    ]),
    _npc("sella", 25, 18, "#e0c48a", "#6a4a2a", "Sella", [
        "Sella: The ocean stretches out forever from here.",
        "Sella: I come down to the beach whenever I need to think.",
    ]),
]

# --------------------------------------------------------------------------- interiors
# Room layouts and their collision grids live in interiors.py: every grid is generated from the footprints of
# the furniture sprites, so what you see is what blocks you.
from interiors import ROWS as ROOM_ROWS

PALETTES = {
    "store": dict(floorA="#d8c9a6", floorB="#d0bf99", wall="#c07a4a", wallTop="#9c5f38", accent="#e0b040"),
    "repair": dict(floorA="#cfd8e0", floorB="#c4ced8", wall="#d1552f", wallTop="#a63f22", accent="#e05a72"),
    "lab": dict(floorA="#cdd3d8", floorB="#c2c9cf", wall="#7f8a99", wallTop="#5e6874", accent="#5b5bd6"),
    "hall": dict(floorA="#d5cdb8", floorB="#cac2ad", wall="#8e8c52", wallTop="#6e6c3c", accent="#b2b06e"),
    "library": dict(floorA="#ccd6e0", floorB="#c1cdd9", wall="#4a5a8a", wallTop="#38446a", accent="#6a86c9"),
    "farm": dict(floorA="#d3ddd0", floorB="#c8d4c4", wall="#4f7a5a", wallTop="#3a5c42", accent="#5be07f"),
}


@dataclass
class Interior:
    id: str
    rows: list
    exit_tile: tuple
    spawn: tuple
    npcs: list
    palette: dict
    spec: Optional[str] = None           # key into interiors.SPECS (sprite-built rooms)


@dataclass
class Building:
    id: str
    name: str
    sign: str
    kind: str                            # lab | store | repair | hall | house
    door: tuple
    entry_return: tuple
    footprint: tuple                     # x, y, w, h in tiles (floats allowed)
    sprite: str
    interior: Interior
    shop: Optional[list] = None          # [(item id, price)]
    repairs: bool = False
    has_database: bool = False
    area: str = "overworld"             # which outdoor map the door is on ("overworld" = Riven Town; see routes.py)


def _house_interior(id_, npc):
    return Interior(id_, ROOM_ROWS["house"], (5, 9), (5, 8), [npc], PALETTES["store"], spec="house")


BUILDINGS = [
    Building("lab", "Astrion Research Lab", "LAB", "lab", (17, 5), (17, 6), (15, 0, 5, 6), "town/bld_lab.png",
             Interior("lab-interior", ROOM_ROWS["lab"], (5, 9), (5, 8), [
                 _npc("lab-aide", 5, 5, "#e4e4ee", "#6a6f7a", "Aide Mira", [
                     "Aide Mira: Welcome to the Astrion Research Lab.",
                     "Aide Mira: Every Scimon you capture is logged here automatically.",
                     "Aide Mira: Prof. Venn is out by the plaza again - he usually is."])],
                      PALETTES["lab"], spec="lab"), has_database=True),
    Building("hall", "Riven Town Hall", "Hall", "hall", (11, 5), (11, 6), (9, 0, 5, 6), "town/bld_hall.png",
             Interior("hall-interior", ROOM_ROWS["hall"], (5, 9), (5, 8), [
                 _npc("mayor", 6, 4, "#c9b06f", "#5a4a2a", "Mayor Rees", [
                     "Mayor Rees: Riven Town was founded on the old Astrion dig site.",
                     "Mayor Rees: Researchers are always welcome here.",
                     "Mayor Rees: Mind the tall grass out by the Farms."])],
                      PALETTES["hall"], spec="hall")),
    Building("cush", "Cush's Repair Nook", "Cush", "repair", (14, 12), (14, 13), (12, 9, 5, 4),
             "town/bld_cush.png",
             Interior("cush-interior", ROOM_ROWS["cush"], (5, 9), (5, 8), [
                 _npc("cush", 5, 4, "#e07a8a", "#8a3a4a", "Cush", [
                     "Cush: Welcome to the nook.",
                     "Cush: Hand me your Scimons and I'll patch up their systems - no charge."],
                      service="repair")], PALETTES["repair"], spec="cush"),
             shop=[("repaircell", 200), ("nanorepair", 600)], repairs=True, has_database=True),
    Building("library", "Riven Library", "Library", "hall", (26, 5), (26, 6), (24, 0, 5, 6),
             "town/bld_library.png",
             Interior("library-interior", ROOM_ROWS["library"], (5, 9), (5, 8), [
                 _npc("archivist", 5, 4, "#c9b06f", "#3a3a4a", "Archivist Yuna", [
                     "Archivist Yuna: Every Scimon species ever logged is catalogued here.",
                     "Archivist Yuna: Feel free to browse, just mind the bindings - some are old."])],
                      PALETTES["library"], spec="library")),
    Building("mart", "Riven Supply Mart", "Supply Mart", "store", (32, 5), (32, 6), (30, 0, 5, 6),
             "town/bld_mart.png",
             Interior("mart-interior", ROOM_ROWS["mart"], (6, 12), (6, 11), [
                 _npc("shopkeeper", 4, 6, "#6fae86", "#3f5f4a", "Clerk Dax", [
                     "Clerk Dax: Welcome to the Riven Supply Mart!",
                     "Clerk Dax: Containment Modules, repair kits - all in stock."], service="shop")],
                      PALETTES["store"], spec="mart"),
             shop=[("repaircell", 200), ("nanorepair", 600), ("stabilizer", 300), ("standard", 200),
                   ("cryo", 600), ("magnetic", 600), ("bio", 600)]),
    Building("farms-a", "Riven Farms Market", "Farms", "store", (5, 6), (5, 7), (3, 1, 5, 6),
             "town/bld_farm_a.png",
             Interior("farms-a-interior", ROOM_ROWS["farms-a"], (5, 9), (5, 8), [
                 _npc("farmer-wren", 5, 4, "#8fae6f", "#4a5a2a", "Farmer Wes", [
                     "Farmer Wes: This bio-dome keeps Riven Town fed year-round.",
                     "Farmer Wes: The field out back grows the slower crops."])],
                      PALETTES["farm"], spec="farms-a")),
    Building("player-house", "Your House", "House", "house", (38, 4), (38, 5), (37, 1, 3, 4),
             "town/bld_house_0.png",
             _house_interior("player-house-interior", _npc("player-mom", 6, 6, "#c96a8f", "#5a3a44", "Mom", [
                 "Mom: Morning! Did you sleep well?",
                 "Mom: Prof. Venn came by earlier looking for you.",
                 "Mom: Don't forget your bag before you head out!"]))),
    Building("cottage-toma", "Tomi's Cottage", "House", "house", (38, 9), (38, 10), (37, 6, 3, 4),
             "town/bld_house_1.png",
             _house_interior("cottage-toma-interior", _npc("toma", 6, 6, "#c98a4a", "#5a3a24", "Tomi", [
                 "Tomi: Careful walking out on the sand at night.",
                 "Tomi: The beach is lovely this time of year, though."]))),
    Building("cottage-reya", "Reya's Cottage", "House", "house", (38, 14), (38, 15), (37, 11, 3, 4),
             "town/bld_house_2.png",
             _house_interior("cottage-reya-interior", _npc("reya", 6, 6, "#4f8fae", "#2a3a4a", "Reya", [
                 "Reya: I moved down here for the sea air.",
                 "Reya: Tomi's place is just up the row."]))),
]

DOOR_INDEX = {b.door: b for b in BUILDINGS}


def building_at_door(x, y):
    return DOOR_INDEX.get((x, y))


# --------------------------------------------------------------------------- startup sanity checks
# Walk-behind buildings: the upper rows of these footprints (below the top map row) become walkable back yard ('e'), so the
# backs of the Hall, Lab, Library and Mart can be reached from the lawn strips beside them.  The facade (the bottom three rows
# of the footprint, door included) stays solid, and the building is drawn as a depth-sorted prop so you walk *behind* it.
BACK_ACCESS = ("hall", "lab", "library", "mart")
BACK_ROWS = (1, 2, 3)                      # offsets from the footprint's top row; offset 0 stays solid (map edge)
BACK_ZONES = {}                            # building id -> (x0, y0, x1, y1) in tiles, used to fade the building while you are behind it


def native_size(sprite):
    """Native (w, h) of a building sprite.  mpw_sizes.SIZES (generated) knows the MPW cut-outs; any other sprite (the Riven
    Town art in assets/town/) is measured from its PNG header, so this module stays pygame-free."""
    got = SIZES.get(sprite)
    if got:
        return got
    import os
    import struct
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", sprite), "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {sprite!r}")
    return struct.unpack(">II", head[16:24])


def trim_footprints(rows, buildings, scale=3, tile=48):
    """Pure-python twin of townview's building placement: a building sprite no longer fills its whole footprint, so every
    'B' tile that the (bottom-anchored, centred) sprite covers by less than a quarter is returned to lawn.  What you see is
    what blocks you; doors ('D') and everything that is not 'B' are untouched.  Returns new row strings."""
    out = [list(r) for r in rows]
    for b in buildings:
        w, h = native_size(b.sprite)
        sw, sh = w * scale, h * scale
        fx, fy, fw, fh = (int(v) for v in b.footprint)
        bx = fx * tile + (fw * tile - sw) / 2
        by = (fy + fh) * tile - sh + 2 * scale
        for y in range(fy, fy + fh):
            for x in range(fx, fx + fw):
                if out[y][x] != "B":
                    continue
                ox = max(0.0, min(x * tile + tile, bx + sw) - max(x * tile, bx)) / tile
                oy = max(0.0, min(y * tile + tile, by + sh) - max(y * tile, by)) / tile
                if ox < 0.25 or oy < 0.25:
                    out[y][x] = "G"
    return ["".join(r) for r in out]


MAP_ROWS[:] = trim_footprints(MAP_ROWS, BUILDINGS)


def _open_backs():
    for b in BUILDINGS:
        if b.id not in BACK_ACCESS:
            continue
        fx, fy, fw, fh = (int(v) for v in b.footprint)
        ys = [fy + o for o in BACK_ROWS]
        for y in ys:
            row = list(MAP_ROWS[y])
            for x in range(fx, fx + fw):
                if row[x] == "B":                  # corners that are already lawn / flowers stay as they are
                    row[x] = "e"
            MAP_ROWS[y] = "".join(row)
        BACK_ZONES[b.id] = (fx, ys[0], fx + fw - 1, ys[-1])


_open_backs()

# What the plaza signpost (S tile) says when you face it and press confirm. Directions are as seen from the sign itself.
SIGN_LINES = [
    "Signpost: Welcome to Riven Town!",
    "Up: Route 1.",
    "Down: The Beach.",
    "Left (west): Farms, Town Hall, Astrion Lab and Cush's Repair Nook.",
    "Right (east): the Library, Supply Mart and the Residential Houses.",
]


def validate():
    for i, row in enumerate(MAP_ROWS):
        assert len(row) == MAP_W, f"overworld row {i} is {len(row)} wide, expected {MAP_W}"
    for b in BUILDINGS:
        assert MAP_ROWS[b.door[1]][b.door[0]] == "D", f"{b.id}: door is not a D tile"
        ex, ey = b.entry_return
        assert MAP_ROWS[ey][ex] not in OVERWORLD_SOLID, f"{b.id}: entry_return is solid"
        w = len(b.interior.rows[0])
        assert all(len(r) == w for r in b.interior.rows), f"{b.id}: ragged interior"
        ex, ey = b.interior.exit_tile
        assert b.interior.rows[ey][ex] == "E", f"{b.id}: exit tile is not E"
        has_terminal = any("@" in r for r in b.interior.rows)
        assert has_terminal == b.has_database, f"{b.id}: has_database={b.has_database} but @ present={has_terminal}"
        sx, sy = b.interior.spawn
        assert b.interior.rows[sy][sx] not in INTERIOR_SOLID, f"{b.id}: spawn is solid"
        for n in b.interior.npcs:
            assert b.interior.rows[n["y"]][n["x"]] not in INTERIOR_SOLID, f"{b.id}: NPC {n['id']} stands on a solid tile"
        seen, stack = {b.interior.spawn}, [b.interior.spawn]
        rows = b.interior.rows
        while stack:
            cx, cy = stack.pop()
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + ddx, cy + ddy
                if (nx, ny) not in seen and 0 <= ny < len(rows) and 0 <= nx < len(rows[0]) \
                        and rows[ny][nx] not in INTERIOR_SOLID:
                    seen.add((nx, ny))
                    stack.append((nx, ny))
        assert b.interior.exit_tile in seen, f"{b.id}: exit not reachable from spawn"
        for n in b.interior.npcs:
            assert (n["x"], n["y"]) in seen, f"{b.id}: NPC {n['id']} is walled off"

    # every door, NPC and tall-grass tile of the town must be reachable on foot from the start tile
    seen, stack = {PLAYER_START}, [PLAYER_START]
    while stack:
        cx, cy = stack.pop()
        for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + ddx, cy + ddy
            if (nx, ny) not in seen and 0 <= ny < MAP_H and 0 <= nx < MAP_W and (MAP_ROWS[ny][nx] not in OVERWORLD_SOLID):
                seen.add((nx, ny))
                stack.append((nx, ny))
    for b in BUILDINGS:
        assert b.door in seen, f"{b.id}: door unreachable"
    for n in NPCS:
        assert (n["x"], n["y"]) in seen, f"NPC {n['id']} is walled off in the town"
    grass = [(x, y) for y in range(MAP_H) for x in range(MAP_W) if MAP_ROWS[y][x] == "g"]
    assert grass and all(g in seen for g in grass), "some tall grass is unreachable"
    backs = [(x, y) for y in range(MAP_H) for x in range(MAP_W) if MAP_ROWS[y][x] == "e"]
    assert backs and all(t in seen for t in backs), "a building's back yard is unreachable"
    beach = [(x, y) for y in range(17, 21) for x in range(MAP_W) if MAP_ROWS[y][x] not in OVERWORLD_SOLID]
    assert beach and all(t in seen for t in beach), "beach dressing seals off part of the sand"


validate()
