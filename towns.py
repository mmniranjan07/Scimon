"""The wider region's styled towns -- Stonreach, Tidebrook, Aurum City, Emberport, Verdance, Dusklight, Vespera,
Cinderfall Island, the Astrion Plateau and Ost's Cabin -- all drawn with Riven Town's own renderer, exactly like
Epidimy Town (map.TileMap._render_styled).

This module is pure data (no pygame): for every town it builds the tile grid, stamps the buildings (Riven Town's
sprites + the three landmark sprites from tools/town_network_art.py), and places NPCs, signs and gates.  routes.py
merges these into the area graph; kanto.py wires each gate to its route.

Grid legend (the same letters as worldmap.OVERWORLD_SOLID, so TileMap collision works unchanged):
  G grass  F flowers  P road  p plaza  A stairs  D door  w pond  s sand  W ocean  R bridge  I pier  V volcanic
  U sea glass    Solid: T tree  h wall  B building  S sign  b bench  u bush  r rock  f fence  H hedge
                 n cinder rock  o lava  Z monument  C moon crystal  t tunnel beam  K garden arch  d mooring post
                 J lighthouse (2x2)  X loot chest
Peaceful towns: no tall grass, so no wild encounters here."""
import worldmap as wm
from worldmap import BACK_ZONES, Building, Interior, INTERIOR_SOLID, PALETTES, ROOM_ROWS, _npc, _trainer, open_backs, trim_footprints

# MPW look code without importing pygame (the formula behind sprites.make_look): sheet * 1024 + 1 + skin + 6*hair + 48*cloth
def _look(sheet, skin, hair, cloth):
    return sheet * 1024 + 1 + skin + 6 * hair + 48 * cloth

# outfit palettes per place: (cloth, hair) hue INDICES into sprites.CLOTH_HUES / HAIR_HUES, plus a favourite sheet
# (0 crimson, 1 gold, 2 leaf, 3 teal, 4 cobalt, 5 royal, 6 orchid, 7 rose / hair: 0 ginger, 1 brown, 2 blond,
#  3 green, 4 azure, 5 indigo, 6 violet, 7 pink)
OUTFITS = {
    "stonreach": (1, 1, 4),        # miner gold-browns, bucket-hat sheet
    "tidebrook": (3, 4, 6),        # river teals
    "aurum": (1, 2, 7),            # merchant golds
    "emberport": (4, 4, 10),       # sailor cobalt, straw-hat sheet
    "verdance": (2, 3, 4),         # gardener leaf
    "dusklight": (6, 6, 3),        # dusk violets
    "vespera": (7, 7, 6),          # orchid / rose
    "cinderfall": (0, 0, 7),       # volcano ember
    "astrion_plateau": (5, 5, 3),  # league royal
    "osts_cabin": (1, 1, 10),      # inventor workwear
}


def area_look(area, who, sheet=None):
    """A look code that dresses `who` in the palette of their town (stable per id)."""
    cloth, hair, default_sheet = OUTFITS.get(area, (105, 28, 2))
    import zlib
    h = zlib.crc32(str(who).encode())
    n = sheet if sheet is not None else 2 + h % 9
    return _look(n, h % 6, (h >> 3) % 8 if sheet is None else hair, cloth)


# --------------------------------------------------------------------------- grid building helpers
class Grid:
    def __init__(self, w, h, fill="G"):
        self.w, self.h = w, h
        self.g = [[fill] * w for _ in range(h)]

    def rect(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < self.w and 0 <= y < self.h:
                    self.g[y][x] = ch

    def put(self, cells, ch, only="G"):
        for x, y in cells:
            if 0 <= x < self.w and 0 <= y < self.h and self.g[y][x] in only:
                self.g[y][x] = ch

    def rim(self, ch):
        self.rect(0, 0, self.w - 1, 0, ch)
        self.rect(0, self.h - 1, self.w - 1, self.h - 1, ch)
        self.rect(0, 0, 0, self.h - 1, ch)
        self.rect(self.w - 1, 0, self.w - 1, self.h - 1, ch)

    def rows(self):
        return ["".join(r) for r in self.g]


# --------------------------------------------------------------------------- shared buildings
MART_STOCK = [("repaircell", 200), ("nanorepair", 600), ("stabilizer", 300), ("standard", 200),
              ("cryo", 600), ("magnetic", 600), ("bio", 600)]


def _house(area, id_, name, sprite, fx, fy, npc):
    return Building(id_, name, "House", "house", (fx + 1, fy + 3), (fx + 1, fy + 4), (fx, fy, 3, 4),
                    f"town/bld_house_{sprite}.png",
                    Interior(f"{id_}-interior", ROOM_ROWS["house"], (5, 9), (5, 8), [npc], PALETTES["store"], spec="house"),
                    area=area)


def _center(area, fx, fy):
    """Every settlement's Cush's Repair Nook franchise: free repairs, the nook counter, the same face."""
    return Building(f"{area}-center", "Cush's Repair Nook", "Cush", "repair", (fx + 2, fy + 3), (fx + 2, fy + 4),
                    (fx, fy, 5, 4), "town/bld_cush.png",
                    Interior(f"{area}-center-interior", ROOM_ROWS["cush"], (5, 9), (5, 8), [
                        _npc(f"cush-{area}", 5, 4, "#e07a8a", "#8a3a4a", "Cush", [
                            "Cush: Welcome to the nook, {name}.",
                            "Cush: Hand me your Scimons and I'll patch up their systems - no charge."],
                            service="repair")],
                        PALETTES["repair"], spec="cush"),
                    shop=[("repaircell", 200), ("nanorepair", 600)], repairs=True, has_database=True, area=area)


def _mart(area, name, fx, fy, clerk, lines):
    return Building(f"{area}-mart", name, "Supply Mart", "store", (fx + 2, fy + 5), (fx + 2, fy + 6),
                    (fx, fy, 5, 6), "town/bld_mart.png",
                    Interior(f"{area}-mart-interior", ROOM_ROWS["mart"], (6, 12), (6, 11), [
                        _npc(f"{area}-clerk", 4, 6, "#6fae86", "#3f5f4a", clerk, lines, service="shop")],
                        PALETTES["store"], spec="mart"),
                    shop=MART_STOCK, area=area)


def _hall(area, id_, name, fx, fy, npc):
    return Building(id_, name, "Hall", "hall", (fx + 2, fy + 3), (fx + 2, fy + 4), (fx, fy, 5, 4),
                    "town/bld_hall.png",
                    Interior(f"{id_}-interior", ROOM_ROWS["hall"], (5, 9), (5, 8), [npc], PALETTES["hall"], spec="hall"),
                    area=area)


# landmark buildings of the wider region (tower, museum, grand mart, gate huts, the mansion, the lab)
LANDMARK_SPECS = {"tower": ("hall", "hall"), "museum": ("library", "library"), "deptstore": ("mart", "store"),
                  "gatehouse": ("house", "store"), "mansion": ("house", "store"), "lab": ("lab", "lab")}


def _landmark(area, id_, name, sign, kind, fx, fy, npcs, shop=None, repairs=False, has_database=False):
    """A landmark building: FRLG-style footprint sizes (tower 3x8, museum/deptstore/lab/mansion 4x5-6,
    gate hut 2x3), door bottom-centre, interior from the shared room set with themed NPCs."""
    spec, palette = LANDMARK_SPECS[kind]
    sizes = {"tower": (3, 8), "museum": (4, 5), "deptstore": (4, 6), "gatehouse": (2, 3), "mansion": (4, 6),
             "lab": (5, 6)}
    fw, fh = sizes[kind]
    sprite = {"tower": "bld_tower", "museum": "bld_museum", "deptstore": "bld_deptstore",
              "gatehouse": "bld_gatehouse", "mansion": "bld_mansion", "lab": "bld_lab"}[kind]
    exit_tile = (6, 12) if spec == "mart" else (5, 9)
    spawn = (6, 11) if spec == "mart" else (5, 8)
    return Building(id_, name, sign, "hall", (fx + fw // 2, fy + fh - 1), (fx + fw // 2, fy + fh),
                    (fx, fy, fw, fh), f"town/{sprite}.png",
                    Interior(f"{id_}-interior", ROOM_ROWS[spec], exit_tile, spawn, list(npcs),
                             PALETTES[palette], spec=spec),
                    shop=shop, repairs=repairs, has_database=has_database, area=area)


def _gym_lot(g, x0, y0, x1, y1):
    """A fenced gym lot (the region runs one gym - Fern's - so every other town's lot waits, signposted)."""
    for x in range(x0, x1 + 1):
        g.g[y0][x] = "f"
        g.g[y1][x] = "f"
    for y in range(y0, y1 + 1):
        g.g[y][x0] = "f"
        g.g[y][x1] = "f"
    g.g[y1][(x0 + x1) // 2] = "G"          # the gate gap on the south side


class Town:
    """One styled town.  `gates` maps a side ("n"/"s"/"e"/"w") to the rim tiles the routes link through; the grid
    builder receives the Grid plus the gate tiles and dresses the town around them."""

    def __init__(self, id, name, w, h, gates, build, buildings, npcs, signs, start, desc, fill="G", rim="T"):
        self.id, self.name, self.w, self.h, self.desc = id, name, w, h, desc
        self.gates = gates
        g = Grid(w, h, fill)
        if rim:
            g.rim(rim)
        self.gate_tiles = {}
        for side, tiles in gates.items():
            gt = []
            for t in tiles:
                x, y = t
                g.g[y][x] = "P"
                gt.append((x, y))
            self.gate_tiles[side] = gt
        build(g, self.gate_tiles)
        for b in buildings:
            fx, fy, fw, fh = (int(v) for v in b.footprint)
            g.rect(fx, fy, fx + fw - 1, fy + fh - 1, "B")
            g.g[b.door[1]][b.door[0]] = "D"
        for (sx, sy) in signs:
            g.g[sy][sx] = "S"
        self.buildings, self.npcs, self.signs, self.start = buildings, list(npcs), dict(signs), start
        self.ROWS = open_backs(trim_footprints(g.rows(), buildings), buildings)
        self.POND_REGIONS = _ponds(self.ROWS)
        self.AREA = None          # routes.py fills in the Area object


def _ponds(rows):
    """Bounding boxes (x, y, w, h) of every water body, for the animated pond layer (epidimy._ponds, generalized)."""
    h, w = len(rows), len(rows[0])
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if rows[y][x] != "w" or (x, y) in seen:
                continue
            stack, cells = [(x, y)], []
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (cx + dx, cy + dy)
                    if n not in seen and 0 <= n[0] < w and 0 <= n[1] < h and rows[n[1]][n[0]] == "w":
                        seen.add(n)
                        stack.append(n)
            xs, ys = [c[0] for c in cells], [c[1] for c in cells]
            out.append((min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    return out


def validate_town(t):
    """The Epidimy checks, generalized: shape, doors, full walkability from the start, NPCs never cut the town."""
    rows, W, H = t.ROWS, t.w, t.h
    solid = wm.OVERWORLD_SOLID
    assert len(rows) == H and all(len(r) == W for r in rows), f"{t.id}: ragged rows"
    for b in t.buildings:
        assert b.area == t.id
        x, y = b.door
        assert rows[y][x] == "D", f"{t.id}/{b.id}: door is not a D tile"
        ex, ey = b.entry_return
        assert rows[ey][ex] not in solid, f"{t.id}/{b.id}: entry_return is solid"
        i = b.interior
        ex, ey = i.exit_tile
        assert i.rows[ey][ex] == "E", f"{t.id}/{b.id}: interior exit tile is not E"
    ids = [b.id for b in t.buildings]
    assert len(ids) == len(set(ids)), f"{t.id}: duplicate building id"
    seen, stack = {t.start}, [t.start]
    assert rows[t.start[1]][t.start[0]] not in solid, f"{t.id}: start is solid"
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in seen and 0 <= nx < W and 0 <= ny < H and rows[ny][nx] not in solid:
                seen.add((nx, ny))
                stack.append((nx, ny))
    open_tiles = {(x, y) for y in range(H) for x in range(W) if rows[y][x] not in solid}
    assert open_tiles == seen, f"{t.id}: unreachable open tiles {sorted(open_tiles - seen)}"
    for b in t.buildings:
        assert b.door in seen, f"{t.id}/{b.id}: door unreachable"
    for side, tiles in t.gate_tiles.items():
        for gt in tiles:
            assert gt in seen, f"{t.id}: gate {side}{gt} unreachable"
    blocked = {(n["x"], n["y"]) for n in t.npcs}
    for gt in [g for tiles in t.gate_tiles.values() for g in tiles]:
        assert gt not in blocked, f"{t.id}: an NPC stands in a gate"
    seen2, stack = {t.start}, [t.start]
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in seen2 and (nx, ny) in seen and (nx, ny) not in blocked:
                seen2.add((nx, ny))
                stack.append((nx, ny))
    assert seen2 == seen - blocked, f"an NPC blocks part of {t.id}: {sorted(seen - blocked - seen2)}"
    for (sx, sy) in t.signs:
        assert any((sx + dx, sy + dy) in seen for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))), f"{t.id} sign {(sx, sy)} can't be read"
        assert rows[sy][sx] in solid, f"{t.id} sign {(sx, sy)} must be a solid tile"
    for n in t.npcs:
        assert (n["x"], n["y"]) in seen, f"{t.id} NPC {n['id']} is walled off"
    return True


# --------------------------------------------------------------------------- the towns
# Each settlement follows its FireRed/LeafGreen counterpart's building placement (adapted to the region's own
# landmarks: the gym lots wait for the League's second season - Fern's Green Gym is the region's only gym).

def _stonreach_build(g, gates):
    g.rect(14, 12, 15, 24, "P")                    # main street (south gate)
    g.rect(8, 12, 28, 13, "P")                     # quarry road (east gate)
    g.rect(12, 15, 17, 18, "p")                    # plaza
    g.g[16][14] = "q"                              # the well
    _gym_lot(g, 11, 3, 13, 5)                      # the gym lot, north-centre like Pewter's
    # the quarry: walled diggings north-east with an opening on the south side
    g.rect(22, 2, 28, 7, "h")
    g.rect(23, 3, 27, 6, "G")
    g.rect(25, 7, 26, 7, "P")
    g.put(((24, 4), (26, 5)), "C", only="G")       # moon crystals dug out of the quarry
    g.put(((23, 6), (10, 14), (19, 15), (18, 20), (9, 16)), "r", only="G")
    g.put(((3, 14), (19, 18), (28, 16), (12, 20), (7, 13)), "T", only="G")
    g.put(((4, 13), (18, 14), (13, 19), (27, 14)), "u", only="G")
    g.put(((13, 14), (18, 15), (10, 18), (24, 21)), "b", only="G")


def _tidebrook_build(g, gates):
    g.rect(12, 6, 15, 11, "w")                     # the river, upper reach
    g.rect(12, 14, 15, 24, "w")                    # the river, lower reach
    g.rect(14, 1, 15, 11, "P")                     # north street
    g.rect(14, 14, 15, 24, "P")                    # south street
    g.rect(1, 12, 28, 13, "P")                     # the bridge road (crosses at the river gap)
    for y in list(range(6, 12)) + list(range(14, 25)):
        g.g[y][14] = g.g[y][15] = "R"              # plank bridges where the street crosses the water
    g.rect(9, 16, 12, 19, "p")
    g.g[17][10] = "q"
    _gym_lot(g, 17, 16, 19, 18)                    # the gym lot, south-centre like Cerulean's
    g.rect(20, 17, 24, 20, "w")                    # the mill pond
    g.put(((3, 14), (7, 10), (17, 14), (27, 15), (19, 14), (6, 22)), "T", only="G")
    g.put(((8, 15), (17, 10), (25, 15), (12, 20)), "u", only="G")
    g.put(((11, 11), (16, 11), (8, 12), (20, 14)), "F", only="G")
    g.put(((10, 15), (12, 18)), "b", only="G")


def _aurum_build(g, gates):
    g.rect(15, 1, 16, 26, "P")
    g.rect(1, 13, 30, 14, "P")
    g.rect(11, 9, 20, 18, "p")                     # the grand plaza
    g.g[13][15] = g.g[13][16] = "p"
    g.g[12][15] = "q"                              # the plaza well
    _gym_lot(g, 4, 9, 6, 11)                       # the gym lot, west-centre like Saffron's
    g.put(((10, 8), (21, 8), (10, 19), (21, 19)), "O", only="G")       # planters
    g.put(((13, 10), (18, 17), (14, 19)), "b", only="G")
    g.put(((9, 12), (22, 12), (9, 16), (22, 16)), "F", only="G")
    g.put(((3, 10), (28, 10), (3, 18), (28, 18), (12, 3), (19, 3)), "T", only="G")


def _emberport_build(g, gates):
    g.rect(0, 23, 29, 25, "W")                     # the harbour ocean
    g.rect(14, 1, 15, 21, "P")                     # harbour street (north gate)
    g.rect(16, 12, 28, 13, "P")                    # east road (Route 11 gate)
    g.rect(11, 14, 16, 17, "p")
    g.g[15][13] = "q"
    _gym_lot(g, 4, 14, 6, 16)                      # the gym lot, west like Vermilion's
    g.rect(9, 20, 10, 25, "I")                     # the fishing pier, out into the ocean
    g.rect(26, 19, 27, 20, "J")                    # the lighthouse footprint (2x2)
    g.put(((12, 21), (16, 21)), "d", only="s")     # mooring posts along the quay
    g.put(((3, 20), (6, 16), (18, 20), (21, 16), (27, 16)), "Q", only="s")   # palms on the sand
    g.put(((8, 16), (17, 20), (25, 21)), "j", only="s")
    g.put(((4, 12), (19, 15), (12, 19)), "T", only="s")
    g.put(((10, 15), (14, 18)), "b", only="s")


def _verdance_build(g, gates):
    g.rect(1, 12, 28, 13, "P")                     # the avenue
    g.rect(14, 6, 15, 11, "P")                     # the garden walk
    g.rect(12, 9, 17, 15, "p")
    g.g[11][14] = "q"
    _gym_lot(g, 3, 15, 5, 17)                      # the gym lot, west-centre like Celadon's
    g.rect(4, 4, 10, 4, "H")                       # hedge parterres
    g.rect(18, 4, 24, 4, "H")
    g.put(((13, 6), (16, 6)), "K", only="G")       # garden arches flanking the walk
    g.rect(4, 6, 10, 7, "F")
    g.rect(18, 6, 24, 7, "F")
    g.put(((3, 10), (26, 9), (26, 17), (11, 4), (17, 4), (9, 17)), "T", only="G")
    g.put(((8, 10), (20, 10), (10, 16), (19, 15)), "u", only="G")
    g.put(((13, 10), (16, 13)), "b", only="G")


def _dusklight_build(g, gates):
    g.rect(13, 1, 14, 22, "P")
    g.rect(1, 11, 12, 12, "P")
    g.rect(9, 14, 14, 17, "p")
    g.g[15][11] = "q"
    g.put(((7, 10), (19, 10), (8, 19), (20, 15), (11, 10), (16, 16)), "Z", only="G")   # the old monuments
    g.put(((3, 10), (3, 15), (10, 12), (17, 13), (6, 21), (21, 20)), "T", only="G")
    g.put(((5, 13), (22, 13), (12, 19)), "u", only="G")
    g.put(((10, 16), (13, 13)), "b", only="G")


def _vespera_build(g, gates):
    g.rect(14, 1, 15, 24, "P")
    g.rect(1, 12, 13, 13, "P")
    g.rect(11, 9, 16, 14, "p")
    g.g[11][13] = "q"
    _gym_lot(g, 11, 16, 13, 18)                    # the gym lot, centre like Fuchsia's
    g.rect(4, 4, 9, 4, "H")                        # hedge walks
    g.rect(18, 4, 24, 4, "H")
    g.rect(4, 16, 8, 16, "H")
    g.rect(19, 16, 24, 16, "H")
    g.put(((9, 8), (21, 8), (6, 14), (21, 14)), "K", only="G")   # arches at the hedge gaps
    g.put(((3, 8), (26, 8), (3, 19), (26, 19), (11, 3), (17, 3)), "T", only="G")
    g.put(((10, 10), (17, 15), (12, 17)), "F", only="G")
    g.put(((13, 12), (16, 10)), "b", only="G")


def _cinderfall_build(g, gates):
    g.rect(0, 22, 29, 25, "W")                     # the southern ocean
    g.rect(0, 10, 2, 15, "W")                      # the western inlet (Route 21 pier)
    g.rect(27, 10, 29, 15, "W")                    # the eastern inlet (Route 20 pier)
    g.rect(0, 12, 5, 13, "I")                      # piers out to both map edges
    g.rect(24, 12, 29, 13, "I")
    g.rect(6, 12, 23, 13, "P")                     # the island road
    g.rect(11, 15, 16, 18, "p")
    _gym_lot(g, 20, 16, 22, 18)                    # the gym lot, south like Cinnabar's
    g.rect(8, 4, 12, 6, "o")                       # the lava fields
    g.rect(17, 5, 20, 7, "o")
    g.put(((7, 7), (13, 5), (16, 8), (21, 4), (9, 16), (20, 16), (24, 17), (5, 16)), "n", only="V")
    g.put(((3, 12), (10, 12), (14, 16)), "b", only="V")


def _plateau_build(g, gates):
    g.rect(14, 16, 15, 24, "P")                    # the climb from Ascent Road
    g.rect(10, 10, 19, 15, "p")                    # the League plaza
    g.rect(6, 12, 23, 13, "P")
    g.rect(2, 2, 27, 2, "h")                       # the crater rim
    g.put(((6, 10), (23, 10)), "O", only="G")      # planters by the plaza
    g.put(((12, 14), (17, 12)), "b", only="G")
    g.put(((4, 6), (26, 6), (4, 22), (26, 22), (12, 17), (17, 17)), "T", only="G")
    g.put(((5, 14), (24, 15)), "F", only="G")


def _cabin_build(g, gates):
    g.rect(10, 4, 11, 16, "P")                     # the path from Route 25
    g.put(((4, 9), (5, 9), (7, 9), (8, 9), (13, 9), (14, 9), (16, 9), (17, 9)), "f", only="G")   # yard fences
    g.put(((3, 3), (18, 3), (3, 13), (18, 13), (8, 12), (14, 12)), "T", only="G")
    g.put(((13, 6), (8, 8), (16, 10)), "u", only="G")
    g.put(((9, 6), (12, 10)), "F", only="G")


def _gate_guard(name, lines):
    return _npc(name, 6, 6, "#7f9ec9", "#3f4a5a", name.split("-", 1)[1].replace("-", " ").title(), lines)


TOWNS = [
    Town("stonreach", "Stonreach Town", 30, 26,
         {"s": [(14, 25), (15, 25)], "e": [(29, 12), (29, 13)]},
         _stonreach_build,
         [_center("stonreach", 4, 8),
          _landmark("stonreach", "stonreach-museum", "Museum of Science", "Museum", "museum", 17, 3, [
              _npc("stonreach-curator", 5, 4, "#c9b06f", "#3a3a4a", "Curator Slate", [
                  "Slate: Welcome to the Museum of Science, {name}.",
                  "Slate: The crater room explains Mt. Crescent - the moon rock fell before the towns had names.",
                  "Slate: Mind the fossil wing; some exhibits hum."])], has_database=True),
          _mart("stonreach", "Stonreach Supply Mart", 24, 15, "Clerk Flint",
                ["Flint: Welcome to the Stonreach Supply Mart, {name}!",
                 "Flint: Quarry folk go through repair cells fast - stock's always fresh."]),
          _house("stonreach", "stonreach-house1", "Bram's House", 0, 5, 19,
                 _npc("stonreach-bram", 6, 6, "#8fae6f", "#4a5a34", "Bram", [
                     "Bram: The quarry's been in my family for three generations.",
                     "Bram: Mind the crystals - they hum when a storm's coming."])),
          _house("stonreach", "stonreach-house2", "Petra's House", 1, 19, 19,
                 _npc("stonreach-petra", 6, 6, "#c96a8f", "#5a3a44", "Petra", [
                     "Petra: I chip fossils out of the quarry walls, {name}.",
                     "Petra: Some of them chip back."]))],
         [_npc("stonreach-foreman", 14, 19, "#a98150", "#5a4630", "Foreman Grit", [
              "Grit: Stonreach built itself out of that quarry, {name}.",
              "Grit: The east road leads to Mt. Crescent - watch for loose Scimons."]),
          _npc("stonreach-kid", 18, 13, "#e0c48a", "#6a4a2a", "Young Cob", [
              "Cob: I found a glowing rock up in the diggings once!",
              "Cob: Dad says it was just quartz. It HUMMED, though."])],
         {(14, 4): ["Signpost: Stonreach Gym - the lot is ready, the League says one gym per region. For now the ring waits."],
          (13, 14): ["Signpost: Stonreach Town.", "South: Route 2 North - back through Mossmere Wood.",
                     "East: Route 3, then Mt. Crescent.", "The Museum of Science is north-east - exhibits daily."],
          (21, 14): ["Signpost: Stonreach Supply Mart - open daily. Containment Modules and repair kits."]},
         (15, 23),
         "A quarry town under the western crags."),
    Town("tidebrook", "Tidebrook Town", 30, 26,
         {"w": [(0, 12), (0, 13)], "e": [(29, 12), (29, 13)], "n": [(14, 0), (15, 0)], "s": [(14, 25), (15, 25)]},
         _tidebrook_build,
         [_center("tidebrook", 17, 4),
          _mart("tidebrook", "Tidebrook Supply Mart", 24, 4, "Clerk Marilla",
                ["Marilla: Welcome to the Tidebrook Supply Mart, {name}!",
                 "Marilla: River damp is hard on gears - stock up on repair cells."]),
          _house("tidebrook", "tidebrook-wheelworks", "Tidebrook Wheelworks", 0, 3, 17,
                 _npc("tidebrook-wade", 6, 6, "#4f8fae", "#2a3a4a", "Mechanic Wade", [
                     "Wade: Wheels, propellers, hover skirts - I true them all.",
                     "Wade: The river hums at dusk. Even my balances agree."])),
          _house("tidebrook", "tidebrook-house2", "Brooke's House", 1, 24, 17,
                 _npc("tidebrook-brooke", 6, 6, "#c98a4a", "#5a3a24", "Brooke", [
                     "Brooke: I skip stones off the bridge every morning.",
                     "Brooke: My record is eleven skips, {name}."]))],
         [_npc("tidebrook-keeper", 10, 12, "#7f9ec9", "#3f4a5a", "Bridge Keeper Roan", [
              "Roan: Mind the planks, {name} - the river took two boards last spring.",
              "Roan: North road runs to Route 24; south to Route 5 and the golden city."]),
          _npc("tidebrook-angler", 20, 15, "#8fae6f", "#4a5a34", "Angler Nel", [
              "Nel: Nothing bites in the mill pond. I keep trying anyway.",
              "Nel: The east road goes to Hollowgate Tunnel. Bring a lamp."])],
         {(21, 15): ["Signpost: Tidebrook Gym - the League says one gym per region. The lot echoes with old battle cries."],
          (11, 11): ["Signpost: Tidebrook Town.", "West: Route 4 - Mt. Crescent road.",
                     "East: Route 9, then Hollowgate Tunnel.", "North: Route 24. South: Route 5 to Aurum City."],
          (16, 14): ["Signpost: The mill pond - no swimming, no fishing, no skipping stones. (The stones skip themselves sometimes.)"]},
         (14, 2),
         "A river town stitched together with plank bridges."),
    Town("aurum", "Aurum City", 32, 28,
         {"n": [(15, 0), (16, 0)], "s": [(15, 27), (16, 27)], "w": [(0, 13), (0, 14)], "e": [(31, 13), (31, 14)]},
         _aurum_build,
         [_hall("aurum", "aurum-hall", "Aurum Trade Hall", 4, 4,
                _npc("aurum-magnate", 6, 4, "#c9b06f", "#5a4a2a", "Magnate Auric", [
                    "Auric: Aurum City runs on Scimon trades, {name}.",
                    "Auric: Every trainer that passes through raises the market. Do good business."])),
          _landmark("aurum", "aurum-spire", "The Aurum Spire", "Spire", "tower", 12, 2, [
              _npc("aurum-director", 6, 4, "#c9c4d6", "#6a6f7a", "Director Celia", [
                  "Celia: The Spire broadcasts the region's trade signals from the top floor.",
                  "Celia: Every road you walked is a line on our charts, {name}.",
                  "Celia: The grid roads hum with wild Scimons - the city pays well for calm ones."])],
              has_database=True),
          _center("aurum", 23, 4),
          _mart("aurum", "Aurum Grand Mart", 23, 20, "Clerk Gilda",
                ["Gilda: The Grand Mart serves every passerby, pass or no pass!",
                 "Gilda: Finest stock on the island, {name}."]),
          _house("aurum", "aurum-house1", "Ledger House", 0, 4, 20,
                 _npc("aurum-ledger", 6, 6, "#7fae9a", "#3a5a4a", "Accountant Vell", [
                     "Vell: I audit the trade ledgers. The numbers always balance.",
                     "Vell: Except that one quarter. We don't talk about that quarter."])),
          _house("aurum", "aurum-house2", "Gildas' House", 2, 9, 20,
                 _npc("aurum-gildas", 6, 6, "#c9b06f", "#5a4a2a", "Gildas", [
                     "Gildas: They say the plaza well grants good trades.",
                     "Gildas: I threw in a wrench. My truck's run perfectly since."]))],
         [_npc("aurum-herald", 13, 12, "#e0c48a", "#6a4a2a", "Herald Brass", [
              "Brass: Welcome to Aurum City, the golden crossroads!",
              "Brass: West to Verdance, east to Dusklight, south to Emberport."]),
          _npc("aurum-tourist", 18, 15, "#d98aa6", "#6a3a4a", "Tourist Cobi", [
              "Cobi: I'm collecting a coin from every town fountain!",
              "Cobi: Your Riven Town beach counts. Don't argue."])],
         {(14, 8): ["Signpost: Aurum City.", "North: Route 5 - Tidebrook road.", "South: Route 6 - Emberport road.",
                    "West: Route 7 to Verdance. East: Route 8 to Dusklight.",
                    "The Spire towers over the plaza - trade tours on the hour."],
          (7, 10): ["Signpost: Aurum Gym - the League says one gym per region. The lot is wired for lights anyway."],
          (17, 19): ["Signpost: Aurum Grand Mart - everything a trader needs, priced in good faith. Mostly."]},
         (15, 24),
         "The golden crossroads of the region."),
    Town("emberport", "Emberport City", 30, 26,
         {"n": [(14, 0), (15, 0)], "e": [(29, 12), (29, 13)]},
         _emberport_build,
         [_center("emberport", 3, 4),
          _mart("emberport", "Emberport Supply Mart", 20, 4, "Clerk Salty",
                ["Salty: Welcome aboard the Emberport Supply Mart, {name}!",
                 "Salty: Sea air rusts everything - buy two repair cells, use one."]),
          _house("emberport", "emberport-fanclub", "Scimon Fan Club", 0, 25, 4,
                 _npc("emberport-fan", 6, 6, "#d98aa6", "#6a3a4a", "Club Chair Marlin", [
                     "Marlin: The Fan Club celebrates Scimons of every make and model!",
                     "Marlin: Membership is free. Enthusiasm is mandatory, {name}."])),
          _house("emberport", "emberport-house1", "Marina House", 1, 3, 18,
                 _npc("emberport-marina", 6, 6, "#4f8fae", "#2a3a4a", "Marina", [
                     "Marina: The lighthouse has blinked twice a minute for forty years.",
                     "Marina: Never three times. Never once. Exactly twice."])),
          _house("emberport", "emberport-house2", "Dockside House", 2, 24, 15,
                 _npc("emberport-dock", 6, 6, "#c98a4a", "#5a3a24", "Dock", [
                     "Dock: The east road ends at a fence and a view.",
                     "Dock: Route 11 - officially a road, unofficially a bench with a road attached."]))],
         [_npc("emberport-captain", 9, 22, "#7f9ec9", "#3f4a5a", "Captain Brie", [
              "Brie: The pier's open, but no boats run since the ferry line folded.",
              "Brie: Walk the sea routes if you must - watch the tide tables."]),
          _npc("emberport-harbour", 13, 12, "#8fae6f", "#4a5a34", "Harbourmaster Gale", [
              "Gale: Emberport moves half the region's freight, {name}.",
              "Gale: All of it by road now. The north gate stays busy."])],
         {(7, 15): ["Signpost: Emberport Gym - the League says one gym per region. The lot doubles as a stage on fair days."],
          (13, 13): ["Signpost: Emberport City.", "North: Route 6 - Aurum City road.",
                     "East: Route 11 (it ends at a bench).", "The pier is open - the ferry is not."],
          (8, 21): ["Signpost: Emberport Pier. Fishing by permit. The lighthouse is not a climbing frame."]},
         (14, 20),
         "The region's harbour city.", fill="s"),
    Town("verdance", "Verdance City", 30, 26,
         {"e": [(29, 12), (29, 13)], "w": [(0, 12), (0, 13)]},
         _verdance_build,
         [_landmark("verdance", "verdance-grandmart", "Verdance Grand Mart", "Grand Mart", "deptstore", 3, 4, [
              _npc("verdance-clerk", 4, 6, "#6fae86", "#3f5f4a", "Clerk Flora", [
                  "Flora: Welcome to the Verdance Grand Mart - every floor a garden!",
                  "Flora: Seven stories in the old catalogues. We grown-fitted the rest."])],
              shop=MART_STOCK + [("nanorepair", 600), ("stabilizer", 300)], has_database=True),
          _center("verdance", 10, 19),
          _house("verdance", "verdance-gamecorner", "The Hedge Corner", 2, 24, 16,
                 _npc("verdance-coyn", 6, 6, "#8e5bb0", "#3a2a4a", "Attendant Coyn", [
                     "Coyn: The Corner is quiet since the coin games moved on.",
                     "Coyn: Try a round of 'guess the hedge' - I always win."])),
          _house("verdance", "verdance-house1", "Ivy's House", 0, 16, 19,
                 _npc("verdance-ivy", 6, 6, "#8fae6f", "#4a5a34", "Ivy", [
                     "Ivy: My hedge maze took thirty years to grow in.",
                     "Ivy: The arches keep it honest. Mostly."])),
          _house("verdance", "verdance-house2", "Rose's House", 2, 24, 4,
                 _npc("verdance-rose", 6, 6, "#c96a8f", "#5a3a44", "Rose", [
                     "Rose: The flower beds change with every season, {name}.",
                     "Rose: Except the blue ones. Those are perennial."]))],
         [_npc("verdance-gardener", 8, 12, "#8fae6f", "#4a5a2a", "Head Gardener Sorrel", [
              "Sorrel: Everything in Verdance is grown, never built.",
              "Sorrel: Even the roads. Don't ask how long the avenue took."]),
          _npc("verdance-florist", 20, 15, "#d98aa6", "#6a3a4a", "Florist Peony", [
              "Peony: Take the west road to Route 16 - the hedgerows hum in spring.",
              "Peony: East is Route 7, straight to Aurum City."])],
         {(6, 16): ["Signpost: Verdance Gym - the League says one gym per region. The lot grew over twice already."],
          (11, 11): ["Signpost: Verdance City.", "East: Route 7 - Aurum City road.",
                     "West: Route 16 - the hedge roads south.", "The Grand Mart is the big glass one, north-west."],
          (18, 14): ["Signpost: Please stay on the paths. The hedges are older than the town and stricter about it."]},
         (14, 10),
         "The garden city."),
    Town("dusklight", "Dusklight Town", 28, 24,
         {"n": [(13, 0), (14, 0)], "w": [(0, 11), (0, 12)], "s": [(13, 23), (14, 23)]},
         _dusklight_build,
         [_center("dusklight", 3, 4),
          _landmark("dusklight", "dusklight-tower", "The Monument Tower", "Tower", "tower", 16, 2, [
              _npc("dusklight-keeper2", 6, 4, "#7f9ec9", "#3f4a5a", "Tower Keeper Mist", [
                  "Mist: The tower rings once a year, on the long dusk.",
                  "Mist: Wild Scimons gather to listen. You're welcome to listen too, {name}."])],
              has_database=True),
          _mart("dusklight", "Dusklight Supply Mart", 19, 4, "Clerk Umbra",
                ["Umbra: Welcome to the Dusklight Supply Mart, {name}.",
                 "Umbra: We close at dusk. We open at dusk. The hours are negotiable."]),
          _house("dusklight", "dusklight-fuji", "Keeper's Cottage", 0, 20, 18,
                 _npc("dusklight-elder", 6, 6, "#c9b06f", "#5a4a2a", "Elder Fernworth", [
                     "Fernworth: I tend the monuments so nobody has to remember alone.",
                     "Fernworth: The tower hums at night. Old bells do that. Old bells, yes."])),
          _house("dusklight", "dusklight-house1", "Lantern House", 1, 3, 18,
                 _npc("dusklight-lantern", 6, 6, "#7f9ec9", "#3f4a5a", "Lantern", [
                     "Lantern: I light the monuments every evening.",
                     "Lantern: For who? For what? Tradition, {name}. Tradition."]))],
         [_npc("dusklight-visitor", 16, 12, "#d98aa6", "#6a3a4a", "Visitor Moth", [
              "Moth: I came for the monuments and stayed for the quiet.",
              "Moth: South road runs down to Route 12 and the long coast."])],
         {(12, 13): ["Signpost: Dusklight Town.", "North: Route 10 - Hollowgate Tunnel road.",
                     "West: Route 8 - Aurum City road.", "South: Route 12 - the coast road begins.",
                     "The Monument Tower is north-east. Visitors welcome; whispering encouraged."],
          (20, 13): ["Signpost: The monuments remember. Please do not lean on them."]},
         (13, 20),
         "The quiet town under the western rim."),
    Town("vespera", "Vespera City", 30, 26,
         {"n": [(14, 0), (15, 0)], "w": [(0, 12), (0, 13)], "s": [(14, 25), (15, 25)]},
         _vespera_build,
         [_center("vespera", 4, 4),
          _landmark("vespera", "vespera-safarigate", "Vespera Safari Gate", "Safari", "gatehouse", 18, 2, [
              _gate_guard("vespera-warden", [
                  "Warden Bramble: The Safari Reserve is north - CLOSED for a wild survey.",
                  "Warden Bramble: The hedge walks keep their own wilds. Ask them politely."])]),
          _mart("vespera", "Vespera Supply Mart", 20, 17, "Clerk Orchid",
                ["Orchid: Welcome to the Vespera Supply Mart, {name}!",
                 "Orchid: Half the town trains Scimons in the hedges. Stock reflects that."]),
          _house("vespera", "vespera-wardenhouse", "Warden's House", 0, 4, 17,
                 _npc("vespera-thistle", 6, 6, "#8e5bb0", "#3a2a4a", "Warden Thistle", [
                     "Thistle: The reserve opens when the survey ends. It always ends.",
                     "Thistle: The hedge walks hide more than shortcuts, {name}."]))],
         [_npc("vespera-herbalist", 13, 10, "#8e5bb0", "#3a2a4a", "Herbalist Sage", [
              "Sage: Every hedge in Vespera is planted on purpose. Nothing is accidental.",
              "Sage: North gate to Route 15; west to Route 18; south to the sea."]),
          _npc("vespera-runner", 17, 13, "#e0c48a", "#6a4a2a", "Hedge Runner Wren", [
              "Wren: I can cross the whole town without touching a road!",
              "Wren: ...the hedges moved. They do that."])],
         {(10, 17): ["Signpost: Vespera Gym - the League says one gym per region. The lot trains hedges meanwhile."],
          (13, 8): ["Signpost: Vespera City.", "North: Route 15 - the coast road in.",
                    "West: Route 18 - the hedge roads north.", "South: Route 19 - the sea crossing.",
                    "The Safari Gate is north-east: closed for a wild survey."],
          (16, 16): ["Signpost: The hedges are training grounds. Enter at your own risk. Seriously."]},
         (14, 22),
         "The hedge city."),
    Town("cinderfall", "Cinderfall Island", 30, 26,
         {"w": [(0, 12), (0, 13)], "e": [(29, 12), (29, 13)]},
         _cinderfall_build,
         [_landmark("cinderfall", "cinderfall-lab", "Cinderfall Research Lab", "Lab", "lab", 4, 4, [
              _npc("cinderfall-researcher", 5, 5, "#e4e4ee", "#6a6f7a", "Researcher Pyx", [
                  "Pyx: The lab reads the island's breathing - magma tides, gas vents, the works.",
                  "Pyx: The mansion up the hill? We don't. It reads you."])],
              has_database=True),
          _center("cinderfall", 20, 4),
          _mart("cinderfall", "Cinderfall Supply Mart", 13, 4, "Clerk Ash",
                ["Ash: Welcome to the Cinderfall Supply Mart, {name}!",
                 "Ash: Volcanic grit gets everywhere. Two repair cells minimum."]),
          _landmark("cinderfall", "cinderfall-mansion", "The Old Mansion", "Mansion", "mansion", 4, 15, [
              _npc("cinderfall-caretaker", 6, 6, "#7f9ec9", "#3f4a5a", "Caretaker Umber", [
                  "Umber: The mansion predates the lab. Predates the town, some say.",
                  "Umber: The doors creak in the same key every night. I've started humming along.",
                  "Umber: Wild Scimons slip in through the cellar. Shadow ones. Mind the dark."])]),
          _house("cinderfall", "cinderfall-house1", "Watch House", 0, 24, 16,
                 _npc("cinderfall-watch", 6, 6, "#e0592f", "#5a3a24", "Watcher Cinder", [
                     "Cinder: The lava fields breathe at night. Perfectly normal.",
                     "Cinder: Mostly. Keep to the piers if they start humming."]))],
         [_npc("cinderfall-pier", 10, 12, "#7f9ec9", "#3f4a5a", "Pier Keeper Ember", [
              "Ember: West pier runs to Route 21 and the mainland; east pier to Route 20 and the isles.",
              "Ember: The planks stay warm. Volcanic, not broken. Probably."]),
          _npc("cinderfall-geologist", 14, 16, "#8e5bb0", "#3a2a4a", "Geologist Flux", [
              "Flux: The island grows a hand-span a year!",
              "Flux: The mart complains. I celebrate."])],
         {(23, 17): ["Signpost: Cinderfall Gym - the League says one gym per region. The lot is warm to the touch."],
          (9, 11): ["Signpost: Cinderfall Island.", "West pier: Route 21 - the mainland crossing.",
                    "East pier: Route 20 - the isles crossing.",
                    "The Research Lab is west; the Old Mansion north-west. The mansion keeps its own hours."],
          (20, 14): ["Signpost: The piers are warm because the island is warm. Do not test this with your hand."]},
         (7, 12),
         "A volcanic island between two sea roads.", fill="V"),
    Town("astrion_plateau", "Astrion Plateau", 30, 26,
         {"s": [(14, 25), (15, 25)]},
         _plateau_build,
         [Building("plateau-hall", "Astrion League Hall", "League", "hall", (9, 8), (9, 9), (7, 2, 5, 7),
                   "town/bld_plateau.png",
                   Interior("plateau-hall-interior", ROOM_ROWS["hall"], (5, 9), (5, 8), [
                       _npc("league-clerk", 6, 4, "#c9c4d6", "#6a6f7a", "League Clerk Astra", [
                           "Astra: Welcome to the Astrion League Hall, {name}.",
                           "Astra: Champions are made on the roads below. The Hall only records them.",
                           "Astra: The stamps case in your Pack has room for every gym in the region."])],
                       PALETTES["hall"], spec="hall"), has_database=True, area="astrion_plateau"),
          _center("astrion_plateau", 9, 17),
          _mart("astrion_plateau", "League Supply Mart", 17, 17, "Clerk Crest",
                ["Crest: The League mart stocks everything a champion's team needs!",
                 "Crest: Same prices as the lowlands. The view is free."])],
         [_npc("plateau-guard", 13, 16, "#7f9ec9", "#3f4a5a", "League Guard Vane", [
              "Vane: The Ascent Road is the only way up, {name}. The rim does the rest.",
              "Vane: Trainers come here to dream. Some of them make it."]),
          _npc("plateau-guide", 18, 11, "#8fae6f", "#4a5a34", "Plateau Guide Ridge", [
              "Ridge: The hall keeps the records. The road keeps the trainers.",
              "Ridge: Rest at the nook before you climb back down."])],
         {(13, 17): ["Signpost: Astrion Plateau.", "South: the Ascent Road, then Route 23.",
                     "The League Hall records every champion. The nook and mart stand either side of the road."],
          (10, 9): ["Signpost: Astrion League Hall. Visitors welcome. Dreams encouraged."]},
         (14, 20),
         "The League's home above the clouds."),
    Town("osts_cabin", "Ost's Cabin", 22, 18,
         {"s": [(10, 17), (11, 17)]},
         _cabin_build,
         [Building("osts-windmill", "Ost's Windmill", "Windmill", "house", (6, 6), (6, 7), (5, 3, 3, 4),
                   "town/bld_windmill.png",
                   Interior("osts-windmill-interior", ROOM_ROWS["house"], (5, 9), (5, 8), [
                       _npc("ost", 6, 6, "#c98a4a", "#5a3a24", "Ost", [
                           "Ost: My windmill grinds grain and charges batteries, {name}.",
                           "Ost: Route 25 dead-ends here - perfect for thinking. And tinkering."])],
                       PALETTES["store"], spec="house"), area="osts_cabin"),
          _house("osts_cabin", "osts-house", "Ost's Cottage", 0, 14, 4,
                 _npc("osts-apprentice", 6, 6, "#7fae9a", "#3a5a4a", "Apprentice Bolt", [
                     "Bolt: Ost taught me everything about Scimon gear!",
                     "Bolt: Mostly I sweep the mill. It's a start."]))],
         [_npc("osts-visitor", 12, 10, "#8fae6f", "#4a5a34", "Tinker Rivet", [
              "Rivet: I hiked all of Route 25 for a glimpse of the windmill!",
              "Rivet: Worth it. Don't tell anyone the road ends here - it's our secret."])],
         {(12, 5): ["Signpost: Ost's Cabin. The windmill is older than the road and plans to outlast it."]},
         (10, 14),
         "A tinker's refuge at the end of Route 25."),
]

for _t in TOWNS:
    for _n in _t.npcs:
        if not _n["id"].startswith("cush-"):
            _n.setdefault("look", area_look(_t.id, _n["id"]))
    for _b in _t.buildings:
        for _n in _b.interior.npcs:
            if not _n["id"].startswith("cush-"):
                _n.setdefault("look", area_look(_t.id, _n["id"]))

if __name__ == "__main__":                 # python3 towns.py [id] prints a town grid for debugging
    import sys
    for _t in (TOWNS if len(sys.argv) < 2 else [next(t for t in TOWNS if t.id == sys.argv[1])]):
        print("==", _t.id)
        for _y, _r in enumerate(_t.ROWS):
            print(f"{_y:2d} {_r}")
else:
    for _t in TOWNS:
        validate_town(_t)


# every town with a nook is a healer (a wipe returns to the nearest one the player has used)
HEALERS = [dict(id=f"{t.id}-center", name="Cush's Repair Nook", area=t.id,
                tile=next(b.entry_return for b in t.buildings if b.id == f"{t.id}-center"), facing="down")
           for t in TOWNS if any(b.id == f"{t.id}-center" for b in t.buildings)]
