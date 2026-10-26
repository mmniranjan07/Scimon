"""The numbered routes and wild places of the wider region -- every road on the reference map is its own walkable
area, and towns.py's gates wire them into one network.  Route 1 (routes.py) is the template; these maps are built
by a small deterministic generator so each route gets a winding road, tall-grass patches, dressed shoulders, signs
and a couple of travelers, all guaranteed walkable (routes.validate() checks every map at import).

Themes: grass (meadows), forest (dense trees), mountain (stone rims and boulders), sea (plank walkways over the
ocean), island (sand and sea glass), tunnel (a lit corridor through the rock).

This module is pure data (no pygame)."""
import random
from collections import deque

import worldmap as wm
from worldmap import _npc, _trainer, open_backs, trim_footprints
import towns

# MPW look code without importing pygame (the formula behind sprites.make_look)
def _look(sheet, skin, hair, cloth):
    return sheet * 1024 + 1 + skin + 6 * hair + 48 * cloth

RANGER_LOOK = _look(4, 1, 1, 2)            # the green bucket-hat ranger
SAILOR_LOOK = _look(10, 1, 1, 4)           # straw hat, cobalt slicker
HIKER_LOOK = _look(5, 2, 2, 1)             # the wild-haired hiker
LEAGUE_LOOK = _look(3, 0, 5, 5)            # league whites and royal blue

_THEMES = {
    "grass":   ("G", "T"),
    "forest":  ("G", "T"),
    "mountain": ("G", "h"),
    "sea":     ("W", "W"),
    "island":  ("s", "W"),
    "tunnel":  ("h", "h"),
}


class Route:
    """An outdoor route map.  Two ways to build one:
    * hand-authored: pass `rows` (FRLG-shaped ASCII, matching the route's gate coordinates) plus explicit
      `start`, `traveler_tiles` and `sign_tiles` -- the grid is used exactly as drawn (Kanto geography).
    * generated: the seeded road carve + theme dressing builds the map (legacy helper, still available).
    Either way, landmark `buildings` (gate huts, the Route 10 nook, the day-care) are stamped on top with a
    spur path so every door stays reachable."""

    def __init__(self, id, name, w, h, theme, seed, ends, encounters=True, signs=(), travelers=(), chest_spur=False,
                 buildings=(), water_band=None, slope_rows=(), cove=None,
                 rows=None, start=None, traveler_tiles=None, sign_tiles=None):
        self.id, self.name, self.w, self.h = id, name, w, h
        self.encounters = encounters
        rng = random.Random(seed)
        fill, rim = _THEMES[theme]
        self.gates = {side: _gate_cells(w, h, side, c) for side, c in ends.items()}
        if rows is not None:
            # ---- hand-authored map (FRLG geography): the grid is used exactly as drawn ------------------------
            assert len(rows) == h and all(len(r) == w for r in rows), f"{id}: hand rows must be {w}x{h}"
            g = [list(r) for r in rows]
            road = [(x, y) for y in range(h) for x in range(w) if g[y][x] in "PIR"]
            for side, tiles in self.gates.items():
                for (x, y) in tiles:
                    assert g[y][x] in "PIR", f"{id}: gate {side}{(x, y)} is not a road tile in the hand rows"
            self.chest = next(((x, y) for y in range(h) for x in range(w) if g[y][x] == "X"), None)
            assert len(sign_tiles or ()) == len(signs), f"{id}: one tile per sign, please"
            assert len(traveler_tiles or ()) == len(travelers), f"{id}: one tile per traveler, please"
            self.signs = {tuple(t): list(lines) for t, lines in zip(sign_tiles or (), signs)}
            self.npcs = [dict(spec, x=tx, y=ty) for spec, (tx, ty) in zip(travelers, traveler_tiles or ())]
            self.start = start or (self.w // 2, self.h // 2)
            assert g[self.start[1]][self.start[0]] not in "TBhwoWVnZCKJdXl", f"{id}: start tile is solid"
        else:
            # ---- generated map (legacy helper) ----------------------------------------------------------------
            g = [[fill] * w for _ in range(h)]
            for side, tiles in self.gates.items():
                for (x, y) in tiles:
                    g[y][x] = "I" if theme in ("sea", "island") else "P"
            pts = {side: tiles[0] for side, tiles in self.gates.items()}
            order = list(ends)
            road = []
            for i in range(len(order) - 1):
                road += _carve(g, w, h, pts[order[i]], pts[order[i + 1]], rng,
                               plank=theme in ("sea", "island"))
            if len(order) == 1:         # a dead end: the road runs in and stops at a quiet spot
                a = pts[order[0]]
                b = (rng.randrange(w // 3, 2 * w // 3), rng.randrange(h // 3, 2 * h // 3))
                road += _carve(g, w, h, a, b, rng, plank=theme in ("sea", "island"))
            for side, tiles in self.gates.items():  # the arrival cells one step inside every gate
                for (x, y) in tiles:
                    ax, ay = {"n": (x, 1), "s": (x, h - 2), "w": (1, y), "e": (w - 2, y)}[side]
                    g[ay][ax] = "I" if theme in ("sea", "island") else "P"
                    if (ax, ay) not in road:
                        road.append((ax, ay))
            self.road = road
            # dressing per theme
            if theme == "tunnel":
                for i, (x, y) in enumerate(road[::3]):
                    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                        if 0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] == "h" and (i + dx + dy) % 2 == 0:
                            g[y + dy][x + dx] = "t"
            if theme in ("sea", "island"):
                stops, beds = 0, 0                          # sand rest stops; tide-grass beds for encounters
                for _ in range(max(8, (w * h) // 45)):
                    if stops >= max(2, (w * h) // 90) and (beds >= 2 or not encounters):
                        break
                    rx, ry = road[rng.randrange(len(road))]
                    dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
                    x, y = rx + dx, ry + dy
                    if not (0 < x < w - 2 and 0 < y < h - 2):
                        continue
                    ok = all(g[y + i][x + j] in "Ws" for i in range(2) for j in range(2))
                    if not ok:
                        continue
                    for yy in (y, y + 1):
                        for xx in (x, x + 1):
                            if g[yy][xx] == "W":
                                g[yy][xx] = "s"
                    stops += 1
                    if encounters and (beds < 2 or rng.random() < 0.5):
                        for yy in (y, y + 1):               # tide-grass beds: the sea routes' wild patch
                            for xx in (x, x + 1):
                                g[yy][xx] = "g"
                        beds += 1
                    elif rng.random() < 0.7:
                        g[y][x] = "Q"
                    elif rng.random() < 0.4:
                        g[y][x] = "j"                       # a beach rock on the sand
            if theme == "tunnel" and encounters:
                for _ in range(max(3, (w * h) // 60)):      # glow-moss chambers carved into the tunnel wall
                    rx, ry = road[rng.randrange(len(road))]
                    dx, dy = rng.choice(((0, -1), (0, 1), (-1, 0), (1, 0)))
                    x, y = rx + dx * 2, ry + dy * 2
                    if not (0 < x < w - 3 and 0 < y < h - 3):
                        continue
                    if all(g[y + i][x + j] == "h" for i in range(2) for j in range(2)) and g[ry][rx] in "Pt":
                        for yy in (y, y + 1):
                            for xx in (x, x + 1):
                                g[yy][xx] = "g"
                        g[ry + dy][rx + dx] = "P"           # open the chamber onto the road
            elif theme not in ("sea", "island"):
                if encounters:
                    for _ in range(max(3, (w * h) // 55)):  # tall-grass patches beside the road
                        pw, ph = rng.randrange(3, 6), rng.randrange(2, 5)
                        x, y = rng.randrange(1, w - pw - 1), rng.randrange(1, h - ph - 1)
                        if all(g[yy][xx] == fill for yy in range(y, y + ph) for xx in range(x, x + pw)):
                            for yy in range(y, y + ph):
                                for xx in range(x, x + pw):
                                    g[yy][xx] = "g"
                for _ in range(max(4, (w * h) // 45)):      # scattered dressing
                    x, y = rng.randrange(1, w - 1), rng.randrange(1, h - 1)
                    if g[y][x] != fill:
                        continue
                    g[y][x] = rng.choice("Trruu" if theme != "mountain" else "rrrTTuu")
                if theme == "forest":
                    for _ in range((w * h) // 22):
                        x, y = rng.randrange(1, w - 1), rng.randrange(1, h - 1)
                        if g[y][x] == fill:
                            g[y][x] = "T"
                if theme == "mountain":
                    for _ in range(3):
                        x, y = rng.randrange(2, w - 2), rng.randrange(2, h - 2)
                        if g[y][x] == fill:
                            g[y][x] = "C"                   # a moon crystal glinting in the scree
            # signs on the road shoulder
            self.signs = {}
            for i, lines in enumerate(signs):
                spot = _shoulder(g, w, h, road, rng, i)
                if spot:
                    self.signs[spot] = lines
            # travelers stand on the road itself (never the only free lane of a 2-wide road)
            self.npcs = []
            for i, spec in enumerate(travelers):
                frac = (i + 1) / (len(travelers) + 1)
                tile = road[min(len(road) - 1, int(len(road) * frac))]
                self.npcs.append(dict(spec, x=tile[0], y=tile[1]))
            # chest pocket (Route 4): a dead-end clearing off the road, sealed by trees
            self.chest = _chest_spur(g, w, h, road, rng) if chest_spur else None
            self.start = road[1] if len(road) > 1 else (self.w // 2, self.h // 2)
        # ---- landmark buildings (gate huts, the Route 10 nook, the day-care): stamped, with a spur to the road
        self.buildings = list(buildings)
        if self.buildings:
            for b in self.buildings:
                fx, fy, fw, fh = (int(v) for v in b.footprint)
                for yy in range(fy, fy + fh):
                    for xx in range(fx, fx + fw):
                        g[yy][xx] = "B"
                g[b.door[1]][b.door[0]] = "D"
                _spur_to_road(g, w, h, b.entry_return, set(road))
            self.rows = open_backs(trim_footprints(["".join(r) for r in g], self.buildings), self.buildings)
            g = [list(r) for r in self.rows]
        self.road = road
        self.rows = ["".join(r) for r in g]


def _spur_to_road(g, w, h, entry, road):
    """Carve a 1-wide path from a building's entry tile to the nearest road tile (BFS over open cells)."""
    q, prev = deque([entry]), {entry: None}
    goal = None
    while q:
        c = q.popleft()
        if c in road:
            goal = c
            break
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            if n not in prev and 0 <= n[0] < w and 0 <= n[1] < h and g[n[1]][n[0]] not in "TBhwoWVnZCKJdX":
                prev[n] = c
                q.append(n)
    if goal:
        c = goal
        while prev[c] is not None:
            c = prev[c]
            if g[c[1]][c[0]] in "GsVu":
                g[c[1]][c[0]] = "P"


def _gate_cells(w, h, side, center):
    """The two link tiles of a gate: (centre, centre + 1) along the rim."""
    if side == "n":
        return [(center, 0), (center + 1, 0)]
    if side == "s":
        return [(center, h - 1), (center + 1, h - 1)]
    if side == "w":
        return [(0, center), (0, center + 1)]
    return [(w - 1, center), (w - 1, center + 1)]


def _carve(g, w, h, a, b, rng, plank=False):
    """Carve a 2-wide road from gate tile `a` to gate tile `b` (an L with a random elbow); returns the road tiles in order."""
    (x0, y0), (x1, y1) = a, b
    tiles = []

    def put(x, y):
        if 0 <= x < w and 0 <= y < h:
            g[y][x] = "I" if plank else "P"
            if (x, y) not in tiles:
                tiles.append((x, y))

    def h_run(x0, x1, y):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            put(x, y)
            put(x, y + 1 if y + 1 < h else y - 1)
    if rng.random() < 0.5:
        h_run(x0, x1, y0)
        for y in range(min(y0, y1), max(y0, y1) + 1):
            put(x1, y)
            put(x1 + 1 if x1 + 1 < w else x1 - 1, y)
    else:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            put(x0, y)
            put(x0 + 1 if x0 + 1 < w else x0 - 1, y)
        h_run(x0, x1, y1)
    return tiles


def _shoulder(g, w, h, road, rng, i):
    """A solid shoulder cell beside the road for a signpost (never on the road itself)."""
    for _ in range(40):
        x, y = road[rng.randrange(len(road))]
        dx, dy = rng.choice(((0, -1), (0, 1), (-1, 0), (1, 0)))
        sx, sy = x + dx, y + dy
        if 0 < sx < w - 1 and 0 < sy < h - 1 and g[sy][sx] in "GgsV":
            g[sy][sx] = "S"
            return (sx, sy)
    return None


def _chest_spur(g, w, h, road, rng):
    """A 3x3 clearing with a hidden chest at the far end, reached by a short spur off the road."""
    mid = len(road) // 2
    for k in range(len(road)):                     # scan outward from the middle of the road
        mx, my = road[(mid + (k // 2) * (1 if k % 2 else -1)) % len(road)]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = mx + dx, my + dy
            if not (0 < x < w - 1 and 0 < y < h - 1) or g[y][x] not in "GgsVTur":
                continue
            cx, cy = x + dx * 2, y + dy * 2
            if not (0 < cx < w - 2 and 0 < cy < h - 2):
                continue
            cells = [(cx + i, cy + j) for i in range(3) for j in range(3)]
            if not all(g[yy][xx] in "GgsVTur" for (xx, yy) in cells):
                continue
            for (xx, yy) in cells:
                g[yy][xx] = "G"
            g[cy + dy + 1][cx + dx + 1] = "X"      # the chest in the far corner, sealed by trees/walls around
            for i in (-1, 0, 1, 2):
                for j in (-1, 0, 1, 2):
                    xx, yy = cx + i, cy + j
                    if 0 <= xx < w and 0 <= yy < h and (xx, yy) not in cells:
                        if g[yy][xx] in "GgsV":
                            g[yy][xx] = "T" if g[yy][xx] != "V" else "n"
            return (cx + dx + 1, cy + dy + 1)
    return None


# --------------------------------------------------------------------------- shared traveler dialogue
def _name(who):
    return who.split("-", 1)[1].replace("-", " ").title()


def _ranger(who, lines, battle=None, **kw):
    if battle:
        return _trainer(who, 0, 0, _name(who), lines, battle, look=RANGER_LOOK, **kw)
    return _npc(who, 0, 0, "#6f8f5a", "#4a3a24", _name(who), lines, look=RANGER_LOOK, **kw)


def _sailor(who, lines, battle=None, **kw):
    if battle:
        return _trainer(who, 0, 0, _name(who), lines, battle, look=SAILOR_LOOK, **kw)
    return _npc(who, 0, 0, "#7f9ec9", "#3f4a5a", _name(who), lines, look=SAILOR_LOOK, **kw)


def _hiker(who, lines, battle=None, **kw):
    if battle:
        return _trainer(who, 0, 0, _name(who), lines, battle, look=HIKER_LOOK, **kw)
    return _npc(who, 0, 0, "#a98150", "#5a4630", _name(who), lines, look=HIKER_LOOK, **kw)


def _cast(who, lines, battle=None, look=None, **kw):
    """A traveler with their own outfit look (helpers above use the shared ranger / sailor / hiker palettes)."""
    if battle:
        return _trainer(who, 0, 0, _name(who), lines, battle, look=look, **kw)
    return _npc(who, 0, 0, "#c9b06f", "#5a4a2a", _name(who), lines, look=look, **kw)


def _sign(name, dirs):
    return [f"Signpost: {name}."] + [f"{d}." for d in dirs]


# --------------------------------------------------------------------------- the routes
def _gate_hut(rid, name, fx, fy, lines):
    """A route guard hut (FRLG's gate houses): enterable, a guard inside, planted beside the road."""
    return towns._landmark(rid, f"{rid}-gate", name, "Gate", "gatehouse", fx, fy,
                           [towns._gate_guard(f"{rid}-guard", lines)])


def _daycare(rid, fx, fy):
    return towns._house(rid, f"{rid}-daycare", "The Day-Care", 0, fx, fy,
                        towns._npc(f"{rid}-daykeeper", 6, 6, "#8fae6f", "#4a5a34", "Day-Care Keeper Sorrel", [
                            "Sorrel: Leave a Scimon with me and I'll raise it like my own!",
                            "Sorrel: The tiny ones grow so fast on this road. Must be the air."]))


# --------------------------------------------------------------------------- hand-authored maps (FRLG geography)
# Each grid is drawn to its FireRed/LeafGreen counterpart's shape: gate tiles stay at the coordinates the LINKS
# table expects, ledges carry stair gaps where paths cross, and one-way descents flow toward an exit.

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]

ROUTE2N_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTllllllGGGGlllllllTTT",
    "TTTTggggggGGGGgggggggTTT",
    "TTTTggggggGGGGgggggggTTT",
    "TTTTggggggGGGGgggggggTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTTGGGGGGGGSGGGGGGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTlllllllGGGGGlllllllTT",
    "TTTgggggggGGGGGgggggggTT",
    "TTTgggggggGGGGGgggggggTT",
    "TTTGGGGGGGGGGGGGGGGGGGGT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGGGGGTTTTTTT",
    "TTTTTTTTTTTPPTTTTTTTTTTT",
]
ROUTE5_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTlllllGGGGGGGGGGGGTTT",
    "TTTTgggggGGGGGGGGGGGGTTT",
    "TTTTgggggGGGGGGGGGGGGTTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGTTSTTTTTTTTTTT",
    "TTTTGGGGGGTTTTTGGGGGGGTT",
    "TTTTGGGGGGTTTTTGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGggggggTT",
    "TTTTGGGGGGGGGGGGggggggTT",
    "TTTTGGGGGGGGGGGGggggggTT",
    "TTTTGGGGGGGGGGGlllllllTT",
    "TTTTGGGGGGGGGGGgggggggTT",
    "TTTTGGGGGGGGGGGgggggggTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGGGGGGGGGTTT",
    "TTTTTTTTTTTPPTTTTTTTTTTT",
]
ROUTE6_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGSggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTwwwwwwGGGGGGggggGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGggggggTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTPPTTTTTTTTTTT",
]
ROUTE7_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGTTTTTTTTTTGGGGGGGGGGT",
    "TGGGGGGTTTTTTTTTTGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGSGGGGGGGGGGGGGGT",
    "TGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "TGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGTTTTTTTTGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
]
ROUTE8_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGTTTTTTTTGGGGGGGGTTTTTTT",
    "TGGGGTTTTTTTTGGGGGGGGTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "TGGGGTTTTTTTTGGGGGGGGTTTTTTT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGggggggggSGGGGGGGggggggT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]
ROUTE9_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGggggggGGGGggggggGGGGGGTT",
    "TGGGggggggGGGGggggggGGGGGGTT",
    "TGGGggggggGGGGggggggGGGGGGTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGlllllGGGlllllGGGGlllllllT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGGgggggggT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGlllllGGGlllllGGGGlllllT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGGgggggggT",
    "TGGGGggggggggGGGGGGGgggggggT",
    "TGGGGGGGGGGGGSGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]
ROUTE10_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGrrGGGGGGrrGGGGGGGGTTTTT",
    "TGGGGggggggggGGGGggGGGGTTTTT",
    "TGGGGrrGGGGGGrrGGGGGGGGTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGWWTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGWWTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGWWTTTTT",
    "PGGGGGGGGGGGGGGGGGGGGWWTTTTT",
    "PGGGGGGGGGGGGGGGGGGGGWWTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGWWTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGWWTTTTT",
    "TGGGGGGGGGGGGGGWWWWWWTTTTTTT",
    "TGGGGrrGGGGSGGGWWWWWWTTTTTTT",
    "TGGGGGGGGGGGGGGWWWWWWTTTTTTT",
    "TGGGGggggggggGGWWWWWWTTTTTTT",
    "TGGGGGGGGGGGGGGWWWWWWTTTTTTT",
    "TGGGGGGGGGGGGGGWWWWWTTTTTTTT",
    "TTTTTTTTTTTTTPPWWWWWWTTTTTTT",
]
ROUTE11_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGSGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "PGGGGGGGGGGGGGGGGGTTTT",
    "PGGGGGGGGGGGGGGGGGTTTT",
    "TGGGGggggggGGGGggggTTT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggGGGGggggTTT",
    "TGGGGGGGGGGGGGGGGGGGGT",
    "TTTTTTTTTTTTTTTTTTTTTT",
]
ROUTE12_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTggggTTGGGGGTggggTTTT",
    "TTTTggggTTGGGGGTggggTTTT",
    "TTTTggggTTGGGGGTggggTTTT",
    "TTTTggggTTGGGGGTggggTTTT",
    "TTTTggggTTGGGGGTggggTTTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTlllllGGGGGGGTTggggTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGSGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTlllllGGGGGGGGTWWWWTT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGTWWWWT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTPPTTTTTTTTTTT",
]
ROUTE13_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTggggTTGGGGGGGgggTTTT",
    "TTTTggggTTGGGGGGGWWTTTTT",
    "TTTTggggTTGGGGGGGWWTTTTT",
    "TTTTggggTTGGGGGGGWWTTTTT",
    "TTTTggggTTGGGGGGGWWTTTTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTggggggTTGGGGGTWWWWTT",
    "TTTTggggggTTGGGGGTWWWWTT",
    "TTTTggggggTTGGGGGTWWWWTT",
    "TTTTggggggSGGGGGGTWWWWTT",
    "TTTTggggggTTGGGGGTWWWWTT",
    "TTTTggggggTTGGGGGTWWWWTT",
    "TTTTggggggTTGGGGWWWWWWWW",
    "TTTTggggggTTGGGGWWWWWWWW",
    "TTTTggggggTTGGGGWWWWWWWW",
    "TTTTggggggTTGGGGWWWWWWWW",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTTTTTTTGGGGTTTTTTTTTT",
    "TTTTTTTTTTGGGGTTTTTTTTTT",
    "TTTTTTTTTTGGGGTTTTTTTTTT",
    "TTTTTTTTTTGGGGTTTTTTTTTT",
    "TTTTTTTTTTGGGGTTTTTTTTTT",
    "TTTTTTTTTTGPPGTTTTTTTTTT",
]
ROUTE14_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGHHHHHHHHGGGGGGGGTTTTTTT",
    "TGGGGHHHHHHHHGGGGGGGGTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGHHHHHHHHGGGGGGGGTTTTTTT",
    "TGGGGHHHHHHHHGGGGGGGGTTTTTTT",
    "TGGGGGGGGGGGSGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]
ROUTE15_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGrrGGGGGGT",
    "TGGGGggggggggGGGGGGrrGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGSGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]
ROUTE16_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGggggggggGGGGGGGGggggggT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGSGGGGGGGGGGGGT",
    "TGGGGHHHHHHHHGGGGGGGGTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGPPPPPPPPPPPPPPPPPPP",
    "TGGGGGGGGPPPPPPPPPPPPPPPPPPP",
    "TGGGGGGGGPPGGGGGGGGGGGGGGGGT",
]
ROUTE18_ROWS = [
    "TTTTTTTTTPPTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTGGTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTGGggggggggGGGGGGTTT",
    "TTTTTTTTTGGggggggggGGGGGGTTT",
    "TTTTTTTTTGGggggggggGGGGGGTTT",
    "TTTTTTTTTGGggggggggGGGGGGTTT",
    "TTTTTTTTTGGGGGGGGGGGGGGGGGGT",
    "TTTTTTTTTGGGGGGGGGGGGGGGGGGT",
    "TTTTTTTTTGGGSGGGGGGGGGGGGGGT",
    "TTTTTTTTTPPPPPPPPPPPPPPPPPPT",
    "TTTTTTTTTPPPPPPPPPPPPPPPPPPT",
    "TTTTTTTTTPPPPPPPPPPPPPPPPPPT",
    "TTTTTTTTTPPPPPPPPPPPPPPPPPPT",
    "TTTTTTTTTPPPPPPPPPPPPPPPPPPT",
    "TTTTTTTTTGGGGGGGGGGGGGGGGGGT",
    "TTTTTTTTTGGgggggGGGGGGgggggT",
    "TTTTTTTTTGGgggggGGGGGGgggggT",
    "TTTTTTTTTGGGGGGGGGGGGGGGGGGP",
    "TTTTTTTTTGGGGGGGGGGGGGGGGGGP",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]
ROUTE19_ROWS = [
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWssWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWssssWIIWWWWWWWWWWW",
    "WWWWWWssssggIIWWWWWWWWWW",
    "WWWWWWssssIIWWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWssssIIIIIIIWWWWWWWWWWW",
    "WWssggWWWWWIIWWWWWWWWWWW",
    "WWssssWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWssssWWWW",
    "WWWWWWWWWWWIIIIIssSsggWW",
    "WWWWWWWWWWWIIWWWssssWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWssssssWWWIIWWWWWWWWWWW",
    "WWssssgggIIIIIIIWWWWWWWW",
    "WWssssssWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWW",
]
ROUTE20_ROWS = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWssssWWWWWWWWWWWWWW",
    "WWWWWWWWWWSsggWWWWWWWWWWWWWW",
    "IIIIIIIIIIIIssssIIIIIIIIIIIW",
    "IIIIIIIIIIIIssssIIIIIIIIIIIW",
    "WWWWWWWWWWWWssssggWWWWWWWWWW",
    "WWWWWWWWWWWWssssWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWIIWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWIIssggWWWWWWWW",
    "WWWWWWWWWWWWWWIIssssWWWWWWWW",
    "WWWWWWWWWWWWWWIIssssWWWWWWWW",
    "WWWWWWWWWWWWWWIIIIIIIIIIIIII",
    "WWWWWWWWWWWWWWIIIIIIIIIIIIII",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]
ROUTE21_ROWS = [
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWssssWWWIIWWWWWWWWW",
    "WWssggWWWIIWWWWWWWWW",
    "WWssSsIIIIIWWWWWWWWW",
    "WWssssWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWssssWW",
    "WWWWWWWWWIIIIIssggWW",
    "WWWWWWWWWIIWWWssssWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWsssssWWIIWWWWWWWWW",
    "WWssgggIIIWWWWWWWWWW",
    "WWsssssWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
    "WWWWWWWWWIIWWWWWWWWW",
]
ROUTE22_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGggggggggGGGGGGrrGGGGGGT",
    "TGGGGggggggggGGGGGGrrGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGTTTTTTGGTTTTTTTTGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "PGGGGGGPPPPPPPPPPPPPPPPGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGSGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]
ROUTE23_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTrrrrrGGGGGGGGGGGGTTT",
    "TTTTGGGGGGGSGGGGGGGGGTTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTllllGGllllllllGGllTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGWWTTTTTT",
    "TTTTGGGGGGWWRRWWGGGGGGTT",
    "TTTTGGGGGGWWRRWWGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGllllGGllllTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGGTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGGGGGTTTTTTT",
    "TTTTTTTTTTTPPTTTTTTTTTTT",
]
ROUTE25_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TGGGGGGGGGGGGGGGGGWWWWWWTT",
    "TggggggGGGGGGGGGGGWWWWWWTT",
    "TGGGGGGGGGGGGGGGGGWWWWWWTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGT",
    "TGGGGGGGGGGGGGGGGGGGGGGGGT",
    "PPPPPPPPPPPPPPPPPPPPPTTTTT",
    "PPPPPPPPPPPPPPPPPPPPPTTTTT",
    "TGGGGGGGGGGGGGGGGGGPPPPTTT",
    "TGGGGGGGGGGGGGGGGGGGGGPPTT",
    "TGGGGGGGGGGGSGGGGGGGGGPPTT",
    "TGGGGGGGGGGGGGGGGGGGGGPPTT",
    "TGGGGGGGGGGGGGGGGGGGGGPPTT",
    "TGGGGGGGGGGGGGGGGGGGGGPPTT",
    "TGGGGGGGGGGGGGGGGGGGGGGGPP",
    "TGGGGGGGGGGGGGGGGGGGGGGGPP",
    "TGGGGGGGGGGGGGGGGGGGGGGGPP",
    "TTTTTTTTTTTTTTTTTTTTTTTTTT",
]
MOSSMERE_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTGGGGGGGGTTTTTTTTTTTTTT",
    "TTTTGGGGGGSGTTTGGTTTTTTTTT",
    "TTTTggggGGGGTTTGGTTTTTTTTT",
    "TTTTggggGGGGTTTGGTTTTTTTTT",
    "TTTTggggGGGGTTTGGTTTTTTTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTTTT",
    "TTTTGGGGggggGGGGggggGGGGTT",
    "TTTTGGGGggggGGGGggggGGGGTT",
    "TTTTGGGGggggGGGGggggGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGTTTTT",
    "TTTTggggggGGGGggggggGGGGTT",
    "TTTTggggggGGGGggggggGGGGTT",
    "TTTTggggggGGGGggggggGGGGTT",
    "TTTTGGGGGGGGGGGGGGGGGTTTTT",
    "TTTTGGGGTTTGGTTTTggggggTTT",
    "TTTTggggTTTGGTTTTGGGGGGTTT",
    "TTTTggggTTTGGTTTTGGGGGGTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTTTT",
    "TTTTTTTTTTTPPTTTTTTTTTTTTT",
]
MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hggggrrggggggrrGGGGCCggggggh",
    "hGGGGrrGGGGGGrrGGGGCCGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGSGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGllllGGllllllGGllllllllh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hggggrrggggggrrggggCCggggggh",
    "hggggrrggggggrrggggCCggggggh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]
HOLLOWGATE_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhgghhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhgghhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhPhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhPPPPPSPPPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPh",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPh",
    "hhhhhhhhhhhhhhhhhhhhgghhhhhhhh",
    "hhhhtthhhhhhhhtthhhhhhtthhhhhh",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]
ASCENT_ROWS = [
    "TTTTTTTTTTPPTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTSGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTlGTTTTTTTTTT",
    "TTTTgggggGGTTTTTTTTTTT",
    "TTTTgggggGGTTTTTTTTTTT",
    "TTTTgggggGGTTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTlGTTTTTTTTTT",
    "TTTTTTTTTTggggggGGTTTT",
    "TTTTTTTTTTggggggGGTTTT",
    "TTTTTTTTTTggggggGGTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTlGTTTTTTTTTT",
    "TTTTrrrrrrGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTPPTTTTTTTTTT",
]
SEAGLASS_ROWS = [
    "WWWWWWWWWWWIIWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWIIWWWWWWWWWWWWWWW",
    "WWWWSsssIIWWWWWWWWWWWWWWWWWW",
    "WWWWssggIIWWWWWWWWWWWWWWWWWW",
    "WWWWssssIIWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWIIWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWIIWWWWWWWWWWWWWWWWWW",
    "WWssssIIIIWWWWWWWWWWWWWWWWWW",
    "WWssggWWIIWWWWWWWWWWWWWWWWWW",
    "IIIIIIIIIIWWWWWWWWWWWWWWWWWW",
    "IIIIIIIIIIWWWWWWWWWWWWWWWWWW",
    "WWssssWWWIIWWWWWWWWWWWWWWWWW",
    "WWssggWWWIIWWWWWWWWWWWWWWWWW",
    "WWssssWWWIIWWWWWWWWWWWWWWWWW",
    "WWWWWWWWIIWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWIIIssssWWWWWWWWWWWWW",
    "WWWWWWWWIIIssggWWWWWWWWWWWWW",
    "WWWWWWWWIIIssssWWWWWWWWWWWWW",
    "WWWWWWWWIIWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWIIWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

ROUTE2_ROWS = [
    "TTTTTTTTTTTPPTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTGGGGTTTGGTTTTGGGGTTT",
    "TTTTllllllGGGGlllllllTTT",
    "TTTTggggggGGGGgggggggTTT",
    "TTTTggggggGGGGgggggggTTT",
    "TTTTggggggGGGGgggggggTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTTGGGGGGGGGGGGGGGGGTTT",
    "TTTTGGGGGGGGSGGGGGGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTTGGGTTTTGGGGTTTGGGTTT",
    "TTTlllllllGGGGGlllllllTT",
    "TTTgggggggGGGGGgggggggTT",
    "TTTgggggggGGGGGgggggggTT",
    "TTTGGGGGGGGGGGGGGGGGGGGT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTGGTTTTTTTTTTT",
    "TTTTTTTTTTTPPTTTTTTTTTTT",
]
ROUTE3_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGgggggGGGgggggggGGGggggggGh",
    "hGgggggGGGgggggggGGGggggggGh",
    "hGgggggGGGgggggggGGGggggggGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGlllllGllGllllllGllllllllGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGgggggggGGGggggggGGGgggggGh",
    "PGGgggggggGGGggggggGGGggggGh",
    "PGGgggggggGGGggggggGGGggggGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGlllllGllllGllllllGllllllGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGggggggGGGggggggggGGGggggGh",
    "hGggggggGGGggggggggGGGggggGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGP",
    "hGGGGGGGGGGGSGGGGGGGGGGGGGGP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]
ROUTE4_ROWS = [
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGgggggGGGgggggggGGGggggggGh",
    "hGgggggGGGgggggggGGGggggggGh",
    "hGgggggGGGgggggggGGGggggggGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGlllllGllGllllllGllllllllGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGggggGGGGgggggGGGgggggggGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "PGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGlllllGllllGllllllGllllllGh",
    "hGGGGGGGGGGGGGGGGGGGGGGGGGGh",
    "hGgggggggGGGggggggGGGggggGGh",
    "hGGGGGGGGGGGSGGGGGGGGGGGGGGh",
    "hGGGGGGGGGGTTTTTTTGGGGGGGGGh",
    "hGGGGGGGGGGTGGXGGGGGGGGGGGPP",
    "hGGGGGGGGGGTGGGGGTGGGGGGGGPP",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]
ROUTE24_ROWS = [
    "TTTTTTTTTTPPTTTTTTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "WWWWWWWWWWRRWWWWWWWWWW",
    "WWWWWWWWWWRRWWWWWWWWWW",
    "WWWWWWWWWWRRWWWWWWWWWW",
    "WWWWWWWWWWRRWWWWWWWWWW",
    "WWWWWWWWWWRRWWWWWWWWWW",
    "WWWWWWWWWWRRWWWWWWWWWW",
    "WWWWWWWWWWRRWWWWWWWWWW",
    "TTTTggggTTGGTTggggTTTT",
    "TTTTggggTTGGTTggggTTTT",
    "TTTTgggSGGGGGGggggTTTT",
    "TTTTGGGGGGGGGGGGGGTTTT",
    "TTTTGGTTTTGGTTTTGGTTTT",
    "TTTTGGTTTTGGTTTTGGTTTT",
    "TTTTgggGGGGGGgggGTTTTT",
    "TTTTgggGGGGGGgggGTTTTT",
    "TTTTGGGGGGGGGGGGGTTTTT",
    "TTTTTTTTTTGGTTTTTTTTTT",
    "TTTTTTTTTTPPTTTTTTTTTT",
]
ROUTE17_ROWS = [
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPSPPPPfGGGggGG",
    "GGGGGGGGfPPPPPPPPfGGGggG",
    "GGGGGGGGfPPPPPPPPfGGGggG",
    "GGGGGGGGfPPPPPPPPfGGGggG",
    "GGGGGGGGGPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfllllllllfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGfPPPPPPPPGGGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGggG",
    "GGGGGGGGfllllllllfGGGggG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfllllllllfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
    "GGGGGGGGfPPPPPPPPfGGGGGG",
]

ROUTES = [
    Route("route2", "Route 2", 24, 26, "grass", 21, {"s": 11, "n": 11},
          rows=ROUTE2_ROWS, start=(11, 1), sign_tiles=[(12, 15)], traveler_tiles=[(12, 16)],
          buildings=[_gate_hut("route2", "Forest Gate", 13, 1, [
              "Guard Pine: The forest gate - Mossmere Wood starts past the treeline.",
              "Guard Pine: Sign in on the way through. It's tradition. And paperwork."])],
          signs=[_sign("Route 2", ["North: Mossmere Wood - the old forest.", "South: Epidimy Town."])],
          travelers=[
              _ranger("route2-ranger-pat", ["Pat: The wood ahead is the old growth - keep to the road, {name}.",
                                            "Pat: Mossmere's trees have stood since before the towns had names."])]),
    Route("route2n", "Route 2 North", 24, 26, "forest", 22, {"n": 11, "s": 11},
          rows=ROUTE2N_ROWS, start=(11, 24), sign_tiles=[(12, 16)], traveler_tiles=[(12, 12)],
          buildings=[_gate_hut("route2n", "Forest Gate", 13, 21, [
              "Guard Rowan: South gate of the old growth - Stonreach's quarry dust starts past the ridge.",
              "Guard Rowan: Mind the ledges on the Stonreach side."])],
          signs=[_sign("Route 2 North", ["North: Stonreach Town - the quarry city.", "South: through Mossmere Wood."])],
          travelers=[
              _hiker("route2n-hiker-moss", ["Moss: I counted four hundred trees today. Then lost count."])]),
    Route("route3", "Route 3", 28, 20, "mountain", 23, {"w": 9, "e": 17},
          rows=ROUTE3_ROWS, start=(1, 9), sign_tiles=[(12, 18)], traveler_tiles=[(5, 13), (15, 16)],
          signs=[_sign("Route 3", ["East: Mt. Crescent - the crescent cave glows at night.",
                                   "West: Stonreach Town."])],
          travelers=[
              _hiker("route3-hiker-scree", ["Scree: Loose stones everywhere - watch your step, {name}.",
                                            "Scree: The crystals up ahead hum when Scimons are near."],
                     battle=("pebblon", 8)),
              _ranger("route3-ranger-quarry", ["Quarry: The road east climbs toward the crater."])]),
    Route("route4", "Route 4", 28, 20, "grass", 24, {"w": 9, "e": 17},
          rows=ROUTE4_ROWS, start=(1, 9), sign_tiles=[(12, 15)], traveler_tiles=[(6, 13)],
          signs=[_sign("Route 4", ["East: Tidebrook Town - the bridge city.", "West: Mt. Crescent.",
                                   "They say supplies get stashed off the road here. Nobody knows who by."])],
          travelers=[
              _ranger("route4-ranger-meadow", ["Meadow: A fine stretch of grass, this.",
                                               "Meadow: Ideal training weather, {name}."])]),
    Route("route5", "Route 5", 24, 26, "grass", 25, {"n": 11, "s": 11},
          rows=ROUTE5_ROWS, start=(11, 1), sign_tiles=[(12, 11)], traveler_tiles=[(13, 10)],
          buildings=[_gate_hut("route5", "Aurum Gate", 18, 21, [
              "Guard Aurel: The Aurum City gate - the grid roads hum day and night.",
              "Guard Aurel: City rules: no battling in the plaza. The roads, though - go wild."]),
              _daycare("route5", 14, 2)],
          signs=[_sign("Route 5", ["South: Aurum City - the golden crossroads.", "North: Tidebrook Town.",
                                   "The Day-Care is north - they raise Scimons like their own."])],
          travelers=[
              _cast("route5-trader-quill", ["Quill: A trader never turns down a battle!",
                                               "Quill: Win and I'll consider the road toll waived. I'm not that kind of trader, but still."],
                       ("sparkit", 9), look=_look(7, 1, 2, 1),
                       post=["Quill: A pleasure, {name}. The road's yours."], facing="left")]),
    Route("route6", "Route 6", 24, 26, "grass", 26, {"n": 11, "s": 11},
          rows=ROUTE6_ROWS, start=(11, 1), sign_tiles=[(15, 10)], traveler_tiles=[(12, 15)],
          buildings=[_gate_hut("route6", "Aurum Gate", 13, 1, [
              "Guard Ledger: North gate to Aurum - the city of the golden crossroads.",
              "Guard Ledger: The wagons run all night. Walk the road, not the grass, after dark."])],
          signs=[_sign("Route 6", ["South: Emberport City - the harbour.", "North: Aurum City."])],
          travelers=[
              _ranger("route6-ranger-south", ["South: Freight wagons all day on this road. Watch your toes."])]),
    Route("route7", "Route 7", 28, 20, "grass", 27, {"e": 17, "w": 9},
          rows=ROUTE7_ROWS, start=(1, 9), sign_tiles=[(12, 7)], traveler_tiles=[(10, 10), (18, 9)],
          signs=[_sign("Route 7", ["West: Verdance City - everything here is grown, never built.",
                                   "East: Aurum City."])],
          travelers=[
              _hiker("route7-hiker-hedge", ["Hedge: I race the wagons to the city. The wagons usually win."],
                     battle=("dewbit", 9)),
              _ranger("route7-ranger-bloom", ["Bloom: The hedges along this road were planted by Verdance's gardeners."])]),
    Route("route8", "Route 8", 28, 20, "grass", 28, {"e": 17, "w": 9},
          rows=ROUTE8_ROWS, start=(1, 9), sign_tiles=[(13, 14)], traveler_tiles=[(14, 12)],
          signs=[_sign("Route 8", ["East: Dusklight Town - the town under the western rim.",
                                   "West: Aurum City."])],
          travelers=[
              _ranger("route8-ranger-dusk", ["Dusk: The light changes near Dusklight. You'll see.",
                                             "Dusk: The town closes at dusk. Or opens. It's hard to say."])]),
    Route("route9", "Route 9", 28, 20, "grass", 29, {"e": 17, "w": 9},
          rows=ROUTE9_ROWS, start=(1, 9), sign_tiles=[(13, 16)], traveler_tiles=[(8, 13), (20, 16)],
          signs=[_sign("Route 9", ["East: Hollowgate Tunnel - bring a lamp.", "West: Tidebrook Town."])],
          travelers=[
              _hiker("route9-hiker-lamp", ["Lamp: The tunnel's perfectly safe. Probably. Bring a lamp anyway."],
                     battle=("cindermite", 9)),
              _ranger("route9-ranger-creek", ["Creek: The creek here feeds Tidebrook's river."])]),
    Route("route10", "Route 10", 28, 20, "mountain", 30, {"s": 13, "w": 9},
          rows=ROUTE10_ROWS, start=(1, 9), sign_tiles=[(11, 14)], traveler_tiles=[(8, 15)],
          buildings=[towns._center("route10", 13, 8)],
          signs=[_sign("Route 10", ["South-east: Dusklight Town.", "West: Hollowgate Tunnel.",
                                    "Cush's nook stands mid-route - free repairs, hot soup smell."])],
          travelers=[
              _hiker("route10-hiker-scarp", ["Scarp: The scarp settles at night. That rumble is normal.",
                                             "Scarp: Dusklight's just over the ridge, {name}."])]),
    Route("route11", "Route 11", 22, 16, "grass", 31, {"w": 9},
          rows=ROUTE11_ROWS, start=(1, 9), sign_tiles=[(10, 6)], traveler_tiles=[(14, 8)],
          buildings=[_gate_hut("route11", "Emberport Gate", 5, 6, [
              "Guard Keel: The Emberport gate - east road ends at a bench and a view.",
              "Guard Keel: I stamp maps for tourists. Yours says 'dead end' twice."])],
          signs=[_sign("Route 11", ["West: Emberport City.", "The road ends here. The bench is nice, though."])],
          travelers=[
              _ranger("route11-ranger-bench", ["Bench: Officially I patrol this road.",
                                               "Bench: Unofficially I sit on the bench and watch the sea."])]),
    Route("route12", "Route 12", 24, 26, "grass", 32, {"n": 11, "s": 11},
          rows=ROUTE12_ROWS, start=(11, 1), sign_tiles=[(12, 12)], traveler_tiles=[(12, 16)],
          buildings=[_gate_hut("route12", "Dusklight Gate", 13, 1, [
              "Guard Wick: The coast road starts here - Dusklight's monuments watch you leave.",
              "Guard Wick: Wild Scimons nest along the cliffs. Rare ones. Quiet ones."])],
          signs=[_sign("Route 12", ["South: the coast road continues.", "North: Dusklight Town."])],
          travelers=[
              _ranger("route12-ranger-coast", ["Coast: You can smell the sea from here, {name}.",
                                               "Coast: The road south winds along the cliffs. Take your time."])]),
    Route("route13", "Route 13", 24, 26, "grass", 33, {"n": 11, "s": 11},
          rows=ROUTE13_ROWS, start=(11, 1), sign_tiles=[(10, 12)], traveler_tiles=[(12, 16)],
          signs=[_sign("Route 13", ["South: the cliff road bends east ahead.", "North: Dusklight's coast."])],
          travelers=[
              _ranger("route13-ranger-tern", ["Tern: The seabirds nest on the cliff edge. Do not join them."])]),
    Route("route14", "Route 14", 28, 20, "grass", 34, {"e": 17, "w": 9},
          rows=ROUTE14_ROWS, start=(1, 9), sign_tiles=[(12, 14)], traveler_tiles=[(14, 15)],
          signs=[_sign("Route 14", ["East: the road swings back toward Vespera.", "West: the cliff road."])],
          travelers=[
              _hiker("route14-hiker-cliff", ["Cliff: Best sea views in the region, right here.",
                                             "Cliff: Vespera's hedges are two days east."], battle=("sporelet", 10))]),
    Route("route15", "Route 15", 28, 20, "grass", 35, {"e": 17, "w": 9},
          rows=ROUTE15_ROWS, start=(1, 9), sign_tiles=[(12, 7)], traveler_tiles=[(12, 10)],
          buildings=[_gate_hut("route15", "Vespera Gate", 23, 14, [
              "Guard Hedge: The Vespera gate - town of hedges, arches and one closed safari.",
              "Guard Hedge: Whatever the hedges tell you, don't follow them. They lie for fun."])],
          signs=[_sign("Route 15", ["East: Vespera City - mind the hedges.", "West: the coast road."])],
          travelers=[
              _ranger("route15-ranger-gate", ["Gate: Almost there, {name}. Vespera's arches are just past the rise."])]),
    Route("route16", "Route 16", 28, 20, "grass", 36, {"e": 17, "s": 9},
          rows=ROUTE16_ROWS, start=(26, 17), sign_tiles=[(14, 9)], traveler_tiles=[(14, 12)],
          buildings=[_gate_hut("route16", "Verdance Gate", 23, 14, [
              "Guard Petal: The Verdance gate - the Grand Mart's glass roof shines at dusk.",
              "Guard Petal: South is the long hedge road. It's one-way fun, downhill all the way."])],
          signs=[_sign("Route 16", ["East: Verdance City.", "South: the hedge roads wind south toward Vespera."])],
          travelers=[
              _cast("route16-rider-vroom", ["Vroom: The hedge roads are my race track!",
                                            "Vroom: Watch the corners, {name} - and your Scimon's Stability."],
                    ("pebblon", 10), look=_look(8, 1, 4, 0),
                    post=["Vroom: Nice pace! See you on the road."], facing="up")]),
    Route("route17", "Route 17", 24, 26, "grass", 37, {"n": 11, "s": 11},
          rows=ROUTE17_ROWS, start=(11, 1), sign_tiles=[(11, 2)], traveler_tiles=[(10, 20)],
          signs=[_sign("Route 17", ["South: the long road south - all downhill, no climbing back.",
                                    "North: Verdance's west gate."])],
          travelers=[
              _ranger("route17-ranger-verge", ["Verge: The hedgerows hum in spring. Nobody knows why.",
                                               "Verge: Verdance's gardeners claim it's on purpose."])]),
    Route("route18", "Route 18", 28, 20, "grass", 38, {"e": 17, "n": 9},
          rows=ROUTE18_ROWS, start=(9, 1), sign_tiles=[(12, 8)], traveler_tiles=[(14, 12)],
          signs=[_sign("Route 18", ["East: Vespera City.", "North: the long road from Verdance."])],
          travelers=[
              _hiker("route18-hiker-bramble", ["Bramble: The hedges here lean in when you pass.",
                                               "Bramble: Vespera folk say they're friendly. I say they're nosey."])]),
    Route("route19", "Route 19", 24, 26, "sea", 39, {"n": 11, "s": 11},
          rows=ROUTE19_ROWS, start=(11, 1), sign_tiles=[(18, 12)], traveler_tiles=[(11, 10)],
          signs=[_sign("Route 19", ["South: the sea crossing to Seaglass Isles.", "North: Vespera City.",
                                    "Stay on the boards - the tide under them is real."])],
          travelers=[
              _sailor("route19-sailor-tide", ["Tide: The boards creak but they hold. Mostly.",
                                              "Tide: Seaglass Isles sparkle at noon. Worth the walk, {name}."])]),
    Route("route20", "Route 20", 28, 20, "sea", 40, {"e": 17, "w": 9},
          rows=ROUTE20_ROWS, start=(0, 9), sign_tiles=[(10, 8)], traveler_tiles=[(13, 10)],
          signs=[_sign("Route 20", ["East: Seaglass Isles.", "West: Cinderfall Island - the piers are warm."])],
          travelers=[
              _sailor("route20-sailor-swell", ["Swell: Two islands, one road, zero boats.",
                                               "Swell: The walking's honest though, {name}."])]),
    Route("route21", "Route 21", 20, 30, "sea", 41, {"n": 9, "s": 9},
          rows=ROUTE21_ROWS, start=(9, 1), sign_tiles=[(4, 4)], traveler_tiles=[(9, 15)],
          signs=[_sign("Route 21", ["South: Cinderfall Island.", "North: Riven Town - home of the Astrion Lab.",
                                    "The mainland crossing. Mind the tide tables."])],
          travelers=[
              _sailor("route21-sailor-current", ["Current: The current runs north to Riven's pier.",
                                                 "Current: I used to ferry folks. Now I cheer them on."])]),
    Route("route22", "Route 22", 28, 20, "grass", 42, {"e": 17, "w": 9},
          rows=ROUTE22_ROWS, start=(1, 9), sign_tiles=[(12, 13)], traveler_tiles=[(12, 10)],
          buildings=[_gate_hut("route22", "League Gate", 23, 14, [
              "Gate Warden Stamp: The League road starts here. The gate checks legs, not stamps - yet.",
              "Gate Warden Stamp: Route 23 climbs to the Ascent. The Plateau waits above."])],
          signs=[_sign("Route 22", ["East: Epidimy Town.", "West: Route 23 - the League road begins."])],
          travelers=[
              _ranger("route22-ranger-pilgrim", ["Pilgrim: Everyone who walks west is heading for the Plateau.",
                                                 "Pilgrim: The League road asks one thing: keep walking, {name}."])]),
    Route("route23", "Route 23", 24, 26, "mountain", 43, {"n": 11, "s": 11},
          rows=ROUTE23_ROWS, start=(11, 1), sign_tiles=[(11, 4)], traveler_tiles=[(11, 8)],
          encounters=False,
          buildings=[_gate_hut("route23", "League Checkpoint", 13, 21, [
              "Checkpoint Clerk Seal: The checkpoint records every challenger by name.",
              "Checkpoint Clerk Seal: One day the gate will ask for stamps. The case in your Pack is ready."])],
          signs=[_sign("Route 23", ["North: the Ascent Road - the final climb.",
                                    "South: Route 22 - the League gate road.", "The gate checks stamps. The road checks legs."])],
          travelers=[
              _hiker("route23-hiker-summit", ["Summit: I've walked this road nine times.",
                                              "Summit: The tenth time's for the stamp case, {name}."])]),
    Route("route24", "Route 24", 22, 20, "grass", 44, {"s": 10, "n": 10},
          rows=ROUTE24_ROWS, start=(10, 1), sign_tiles=[(7, 11)], traveler_tiles=[(10, 4), (11, 6)],
          signs=[_sign("Route 24", ["North: the road to Route 25.", "South: Tidebrook Town.",
                                    "The long bridge - every challenger crosses it. Every one."])],
          travelers=[
              _cast("route24-picnic-piper", ["Piper: You startled my picnic, {name}!",
                                             "Piper: A battle settles it. Winner keeps the sandwich."],
                    ("aquabit", 10), look=_look(9, 1, 7, 7),
                    post=["Piper: Fine win. The sandwich was stale anyway."], facing="left"),
              _ranger("route24-ranger-bridge", ["Bridge: The bridge warden counts crossers. You're number 4,102.",
                                                "Bridge: The record holder crossed in forty seconds. Unsupported."],
                      battle=("sparkit", 11))]),
    Route("route25", "Route 25", 26, 20, "grass", 45, {"e": 16, "w": 8},
          rows=ROUTE25_ROWS, start=(1, 9), sign_tiles=[(12, 12)], traveler_tiles=[(10, 11)],
          signs=[_sign("Route 25", ["East: Ost's Cabin - the road ends at the windmill.",
                                    "West: Route 24 - back to Tidebrook."])],
          travelers=[
              _ranger("route25-ranger-meander", ["Meander: This road doesn't go anywhere. That's the point.",
                                                 "Meander: Ost's windmill is the best dead end in the region."])]),
]

# --------------------------------------------------------------------------- the wild places
PLACES = [
    Route("mossmere", "Mossmere Wood", 26, 28, "forest", 51, {"n": 11, "s": 11},
          rows=MOSSMERE_ROWS, start=(11, 1), sign_tiles=[(10, 4)], traveler_tiles=[(12, 12)],
          signs=[_sign("Mossmere Wood", ["North: the wood thins toward Stonreach.", "South: Route 2.",
                                         "The old growth. The trees were here first; act accordingly."])],
          travelers=[
              _ranger("mossmere-warden-fern", ["Warden Fern: The wood hums at dusk. Old magic or old machines.",
                                               "Warden Fern: Keep to the path, {name} - the moss swallows boots."])]),
    Route("mt_crescent", "Mt. Crescent", 28, 22, "mountain", 52, {"e": 19, "w": 10},
          rows=MTCRESCENT_ROWS, start=(1, 10), sign_tiles=[(13, 12)], traveler_tiles=[(10, 10)],
          signs=[_sign("Mt. Crescent", ["East: Route 4 - down to Tidebrook.", "West: Route 3 - down to Stonreach.",
                                        "The crater glows faintly on clear nights."])],
          travelers=[
              _hiker("mt_crescent-surveyor", ["Surveyor Sliver: The crater's rock isn't in any catalogue.",
                                              "Surveyor Sliver: The crystals resonate. My instruments hate it."],
                     battle=("nanolyte", 11))]),
    Route("hollowgate", "Hollowgate Tunnel", 30, 16, "tunnel", 53, {"e": 7, "w": 8},
          rows=HOLLOWGATE_ROWS, start=(1, 9), sign_tiles=[(12, 7)], traveler_tiles=[(14, 9)],
          signs=[_sign("Hollowgate Tunnel", ["East: Route 10 - down to Dusklight.", "West: Route 9 - back to Tidebrook.",
                                             "The lanterns are maintained by both towns. Usually."])],
          travelers=[
              _hiker("hollowgate-keeper-wick", ["Keeper Wick: Mind the beams, mind the dark, mind your step.",
                                                "Keeper Wick: Halfway is the loneliest part. Walk on, {name}."])]),
    Route("ascent", "Ascent Road", 22, 28, "mountain", 54, {"n": 10, "s": 10},
          rows=ASCENT_ROWS, start=(10, 1), sign_tiles=[(10, 4)], traveler_tiles=[(11, 10)],
          signs=[_sign("Ascent Road", ["North: Astrion Plateau - the League's home.", "South: Route 23.",
                                       "The last road. Every trainer walks it twice: once up, once down."])],
          travelers=[
              _npc("ascent-guide", 0, 0, "#c9c4d6", "#6a6f7a", "Ascent Guide Stele", [
                  "Stele: The Plateau is past the rim, {name}.",
                  "Stele: Whatever happens up there, the road remembers you."], look=LEAGUE_LOOK)]),
    Route("seaglass", "Seaglass Isles", 28, 22, "island", 55, {"n": 11, "w": 9},
          rows=SEAGLASS_ROWS, start=(0, 9), sign_tiles=[(4, 2)], traveler_tiles=[(10, 12)],
          signs=[_sign("Seaglass Isles", ["West: Route 20 - Cinderfall crossing.", "North: Route 19 - Vespera crossing.",
                                          "The sand is littered with sea glass. Take only photographs and one piece."])],
          travelers=[
              _sailor("seaglass-beachcomber", ["Comber: Ten years of beachcombing and I still fill a jar a week.",
                                               "Comber: The green pieces are the luckiest, {name}."])]),
]

AREAS = {a.id: a for a in ROUTES + PLACES}

# --------------------------------------------------------------------------- the link graph
_TOWN_GATE_S = [(10, 23), (11, 23)]            # Riven Town's sea pier (worldmap.py rows 21-23, x 10-11)
_EPI_GATES = {"n": [(x, 0) for x in (6, 7)], "w": [(0, y) for y in (20, 21)]}


def _area_wh(area_id):
    if area_id == "overworld":
        return (len(wm.MAP_ROWS[0]), len(wm.MAP_ROWS))
    if area_id == "epidimy":
        import epidimy
        return (epidimy.W, epidimy.H)
    t = next((t for t in towns.TOWNS if t.id == area_id), None)
    if t:
        return (t.w, t.h)
    return (AREAS[area_id].w, AREAS[area_id].h)


def _gate_tiles(area_id, side):
    if area_id == "overworld":
        return _TOWN_GATE_S
    if area_id == "epidimy":
        return _EPI_GATES[side]
    t = next((t for t in towns.TOWNS if t.id == area_id), None)
    if t:
        return t.gate_tiles[side]
    return AREAS[area_id].gates[side]


_ARRIVALS = {
    "n": lambda w, h, tiles: ([(x, 1) for x, _ in tiles], "down"),
    "s": lambda w, h, tiles: ([(x, h - 2) for x, _ in tiles], "up"),
    "w": lambda w, h, tiles: ([(1, y) for _, y in tiles], "right"),
    "e": lambda w, h, tiles: ([(w - 2, y) for _, y in tiles], "left"),
}

# edges: (area A, side of A, area B, side of B) -- each becomes two link entries (one per direction)
EDGES = [
    (("epidimy", "n"), ("route2", "s")),
    (("mossmere", "n"), ("route2n", "s")),
    (("route2", "n"), ("mossmere", "s")),
    (("route2n", "n"), ("stonreach", "s")),
    (("stonreach", "e"), ("route3", "w")),
    (("route3", "e"), ("mt_crescent", "w")),
    (("mt_crescent", "e"), ("route4", "w")),
    (("route4", "e"), ("tidebrook", "w")),
    (("tidebrook", "s"), ("route5", "n")),
    (("route5", "s"), ("aurum", "n")),
    (("aurum", "s"), ("route6", "n")),
    (("route6", "s"), ("emberport", "n")),
    (("aurum", "w"), ("route7", "e")),
    (("route7", "w"), ("verdance", "e")),
    (("aurum", "e"), ("route8", "w")),
    (("route8", "e"), ("dusklight", "w")),
    (("tidebrook", "e"), ("route9", "w")),
    (("route9", "e"), ("hollowgate", "w")),
    (("hollowgate", "e"), ("route10", "w")),
    (("route10", "s"), ("dusklight", "n")),
    (("emberport", "e"), ("route11", "w")),
    (("dusklight", "s"), ("route12", "n")),
    (("route12", "s"), ("route13", "n")),
    (("route13", "s"), ("route14", "w")),
    (("route14", "e"), ("route15", "w")),
    (("route15", "e"), ("vespera", "n")),
    (("verdance", "w"), ("route16", "e")),
    (("route16", "s"), ("route17", "n")),
    (("route17", "s"), ("route18", "n")),
    (("route18", "e"), ("vespera", "w")),
    (("vespera", "s"), ("route19", "n")),
    (("route19", "s"), ("seaglass", "n")),
    (("seaglass", "w"), ("route20", "e")),
    (("route20", "w"), ("cinderfall", "e")),
    (("overworld", "s"), ("route21", "n")),
    (("route21", "s"), ("cinderfall", "w")),
    (("epidimy", "w"), ("route22", "e")),
    (("route22", "w"), ("route23", "s")),
    (("route23", "n"), ("ascent", "s")),
    (("ascent", "n"), ("astrion_plateau", "s")),
    (("tidebrook", "n"), ("route24", "s")),
    (("route24", "n"), ("route25", "w")),
    (("route25", "e"), ("osts_cabin", "s")),
]

LINKS = {}
for (_a, _sa), (_b, _sb) in EDGES:
    aw, ah = _area_wh(_a)
    bw, bh = _area_wh(_b)
    ga = _gate_tiles(_a, _sa)
    gb = _gate_tiles(_b, _sb)
    arr_a, face_a = _ARRIVALS[_sa](aw, ah, ga)      # entering A through its side _sa
    arr_b, face_b = _ARRIVALS[_sb](bw, bh, gb)      # entering B through its side _sb
    for t, at in zip(ga, arr_b):
        LINKS.setdefault(_a, {})[t] = (_b, at, face_b)
    for t, at in zip(gb, arr_a):
        LINKS.setdefault(_b, {})[t] = (_a, at, face_a)

# Route 4 hides a supply chest in a sealed clearing off the road
CHESTS = {}
for _r in ROUTES:
    if _r.chest:
        CHESTS[_r.id] = [dict(tile=_r.chest, key=f"{_r.id}:chest",
                              loot=(("biotrellis", 1), ("repaircell", 3)))]

# the Route 10 nook is a real healer on the road (FRLG's Route 10 centre)
HEALERS = [dict(id="route10-center", name="Cush's Repair Nook", area="route10",
                tile=next(b.entry_return for r in ROUTES if r.id == "route10"
                          for b in r.buildings if b.id == "route10-center"), facing="down")]
