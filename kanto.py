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
# Every grid below is decoded metatile-for-metatile from the pokefirered decomp (data/layouts/<Map>/map.bin),
# with the game's border gates carved where FireRed passes through gate buildings or surf channels, plus
# small stair-gap connectors where FireRed's one-way ledges would otherwise seal a pocket off for good.
ROUTE2N_ROWS = [
    "TTTTTTTTgPPPTTTTTTTTTTTT",
    "TTTTTTTTgPPPTTTTTTTTTTTT",
    "TTgggggggPPPuuuuuuuuuuTT",
    "TTgggggggPPPTgggggggggTT",
    "TTgggggggPPPTgggggggggTT",
    "TTgggggggPPPTgggggggggTT",
    "TTgggggggPPPTrrrrrrrrgTT",
    "TTgggggggPPPTrrrrrrrrgTT",
    "TTgggggggPPPTrrrrrrrrgTT",
    "TTggPPPPPPPPTrrrrrrrrgTT",
    "TTggPPPPPPPPTrrrrrrrrgTT",
    "TTggPPPPPPPPTrrrrPrrrgTT",
    "TTggPPPPggggTgSGGGGGGGTT",
    "TTuuPPPPuuugrgGGGGGGGGTT",
    "TTBBBPPPPBrgggGGGGGGGGTT",
    "TTBBBPPBBBGGGGGGGGGGGGTT",
    "TTBBBPPBBBTTTTgGGGGGGgTT",
    "TTBBBBBBBBTTTTggggggggTT",
    "TTBBBBBBBBTTTTggggggggTT",
    "TTBBBBBBBBTTTTggggggggTT",
    "TTTTTTTTTTTTTTPPPPPgggTT",
    "TTTTTTTTTTTTTTBBBBBGGGTT",
    "TTTTTTTTTTTTTTBBBBBGGGTT",
    "TTTTTTTTTTTTTTGGGGGGGGTT",
    "TTTTTTTTTTTTTTTTGGGGGGTT",
    "TTTTTTTTTTTTTTTTPPPGGGTT",
]

ROUTE2_ROWS = [
    "TTTTTTTTTTTTTTTTuPPPuuTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTlllGllTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTggggggTT",
    "TTTTTTTTTTTTTTTTlllGllTT",
    "TTTTTTTTTPPPPPPPggggggTT",
    "TTTTTTTTTTTTTTTTgPPPPgTT",
    "TTTTTTTTTTTTTTTTGPPPPGTT",
    "TTTTTTTTTTTTTTTTuPPPPuTT",
    "TTTTTTTTTTTTTTTTBBPBBBTT",
    "TTTTTTTTTTTTTTTTBBPBBBTT",
    "TTTTTTTTTTTTTTTTBBPPPPTT",
    "TTPPPPPPPPTTTTTTrrPrrrTT",
    "TTBPBBBBBBTTTTTTBrPPrBTT",
    "TTBPBBBBBBTTTTTTuPPPPuTT",
    "TTBPBBBBBBTTTTTSgPPPPgTT",
    "TTBPPPPPPBTTTTTTgPPPPgTT",
    "TTPGPPPPGTTTTTTTGggGggTT",
    "TTBBrPPrBBTTTTTTlllGllTT",
    "TTPuPPPPuPPuuuTTgGGGGgTT",
    "TTgFPPPPggggggTTgGGGGgTT",
    "TTFgPPPPggggggTTgGGGGgTT",
    "TTlllllllllgggTTgGGGGgTT",
    "TTgPPPggggggggTTggGGGgTT",
    "TTFPPPggggggggTTllGlllTT",
    "TTgPPPggggggggTTggGgGGTT",
    "TTFPPPggggggggTTggGGGGTT",
    "TTgPPPggggggggTTggGGGgTT",
    "TTFPPPggggggggTTggGGGgTT",
    "TTgPPPGGGGGGGGGGGGGGGGTT",
    "TTgPPPTTTTTTTTTTgGGGGgTT",
    "TTgPPPTTTTTTTTTTFGGGGgTT",
    "TTgPPPTTTTTTTTTTGFggGFTT",
    "TTgPPPTTTTTTTTTTFgggFGTT",
    "TTgPPPPPPPPPPPTTGGGGGFTT",
    "TTgPPPPPPPPPPPTTGGGGGGTT",
    "TTgPPPPPPPPPPPggGGGGGGTT",
    "TTlllllllGGlllGGllGlllTT",
    "TTGGPPPPPPPPPPTTggggggTT",
    "TTTTPPPPPPPPPPTTgGGGggTT",
    "TTTTPPPSgggPPPTTGGGGFgTT",
    "TTTTPPPGgggPPPTTGGGGGFTT",
    "TTTTPPPPPPPPPPTTGGGGFgTT",
    "TTTTPPPPPPPPPPTTGGGFgFTT",
    "TTTTGGgggPPPggTTGGGGGGTT",
    "TTTTTTrggPPPGGTTTTTTTTTT",
    "TTTTTTrggPPPTTTTTTTTTTTT",
]

ROUTE3_ROWS = [
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrsPPPPPPPPPPrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrBBBBBrrrPPPrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrBBBBBrrrPPPrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrgGgrGGBBBBBrrrPPPrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPrgggGBBrBBPrrPPPrrrrrrrrrrrP",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPgggggPPPPPPPrrrrrrrrrrPP",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrlllllPPPPPPPPPPSPPrrrrrrrrrrPP",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPPPPPPPPPPPrrrrrrrrrPPP",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPPPPPlllllllrrrrrrrrPll",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPrPPPPPPPPPPPPPPPPPrrrrrrrrggg",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrlllllllllPPPPPPPPrPPPPPPPPPggg",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPPPPPlllllllrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPrPPPPPPPPPPPPPPrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPPPPPPrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrlllPPPPPPPrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPlllrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrPPPPPPPPPPPPPPPPPPPPPPrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrPPPPPPPPPPPPPPPPPPPPPPPPPPrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrGPPPPrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrPPPPPPgggggggPPPPPPPPPPPPPrrrrrrPPPPPPPPPPPPPPPPrrrrrrrrrgggggrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrgggggggggrrrgggggggrrggPPPrrrrrPPPPPPPPPPPPPPPPPPPrrrrrrrgggggrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrlllggllllrrrlllllllrrlllGgrrrrrPPPPggggggggggPPPPPrrrrrrrgggggrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrgggggggggggggrrrgggggggrrgggggrrrrrllllggrrrrrrrlllllgrrrrrrrlllGGrrrrrrrrrrrrrrrrrrrr",
    "PPPgggggggggggggggggrrrgggGgggrrggggggggggggggggrrrrrrrgggGgGrrrrrrrGggggrrrrrrrrrrrrrrrrrrrr",
    "PPPgggggggggggggggggrrrgggggggrrrgggggggggggggggrrrrrrrgggGgGrrrrrggggggGggggrrrrrrrrrrrrrrrr",
    "PPPggggggrrrggggggggrrrgggggggrrrgggggggggggggggrrrrrrrgGgGgGggggggggguuSggggggrrrrrrrrrrrrrr",
    "ggrrrrrrrrrrllllggllrrrlllllllrrrggggggggggggggrrrrrrrrgGgGgGgggggggggGggggggggrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrggggggggrrrgggggggrrrggggggggggggggrrrrrrrrGggGgGgggggggggGggggggggrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrPPPPPPPPPggggggggrrrrrrggggggggggggrrrrrrrrFGFGgGgGggggggggggggggggrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrPPPPPPPPPPPPPPPrrrrrrggggggggggggrrrrrrrrrrGFGgGgggggggggggggggggrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrggggggggrrrrrrrrrrFGFGFGgggggggggggggrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
]

ROUTE4_ROWS = [
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrggrggggggrgrrrrrrrrrgrgggggrrrrrrrrrrrrrrrrggggPPPPPPPrrrrrrrrrrr",
    "PPPrrrrrrrggrggggggrggrGFGFGrggrgggggrFgFGgGgggggggggggggPXPPPPPPPPPPPPPPPP",
    "PPPrrrrrrrggrggggggrGGrFGFGFrggrgggggrgFgFGggggggggggggggPPPPPPPPPPPPPPPPPP",
    "PPPrrrrrggggrllggllTGGrgGGggrggrgggggrllllllllllllPlllllllllllllkkkkkkkkkkk",
    "PPPPPPPgggggggggggggggrgggggrggrggggggggggggggggggggggggggggggggkWWWWWWWWWW",
    "PSPPPPPgggggggggggggggrgggggrggrlGGlllllllllllllllllllllllllllllkWWWWWWWWWW",
    "ggggggggggggggggggggggrgggggrgggggggggggggggggGggggggGGGGGggggggkWWWWWWWWWW",
    "llllllllggglllllllllllTgPPPgrlTgggggggGGGGggggGggggggTTTTlllllllkkkkkkkkkkk",
    "ggggggggggggggggggggggGgPPPGGGrlllllGGTTTTlllllllllllTTTTggPPPPPPPPPPPPPPPP",
    "gggggggggggggggggPPPPPPPPPPPPPPPPPPPPgTTTTgggggggggggTTTTggPPPPPPPPPPPPPPPP",
    "rrrrrrrrggggGGGGgPPPPPPPPPPPPPPPPPPPPgTTTTgggggggggggTTTTggPPPPPPPPPPPPPPPP",
    "rrrrrrrrrrrrTTTTgPPPPPPPPPPPPPPPPPPPPgTTTTgggggggggggggTTggPPPggkrrrrrrrrrr",
    "rrrrrrrrrrrrTTTTggggggggggggggggggggGGTTTTgggggggggggggTTllPPPllkTTTTTTTTTT",
    "rrrrrrrrrrrrrrrrllGGlllllllllGGlllllTTTTTTgggggggggggggTTggPPPggkTTTTTTTTTT",
    "rrrrrrrrrrrrrrrrGFGFGgGgggggggggggggTTTTTTgggggggggggggTTggPPPggkTTTTTTTTTT",
    "rrrrrrrrrrrrrrrrFGFGFGFGggggggggggGgTTTTTTggggggggggggggggggggGGkTTTTTTTTTT",
    "rrrrrrrrrrrrrrrrrrrrrrrGggggggggggggTTrrrrrrrrrrrrrrrgggggggggrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
]

ROUTE5_ROWS = [
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPPggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkllllllllkPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkllllllllkPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkllllllllkPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPPggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkllllllllkPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkggggggggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkgPPPPPggrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkGBBBBBGGrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkGBBBBBGGrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkGPPBBBGGrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkGBPrBBGGrPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrPPPPkGGGGGGGGkPPPPkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrggggllllllllllGGGGkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrgggggggggggggggPPPBTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrgggggggggggggggBBBBTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrggggggggPPPPGggBBBBTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrgggggggGPPPPGggBPBBTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrgggggggrPPPPrggggSrTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTrgggggggBBPPBBggggGkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTkkkPkkkkBBPPBBkkkPkkTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTGGGGGGGGBBPPBBGGGGGGTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTBPPPBBTTTPTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTPPPTTTTTPTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTBPPPrBTTTPTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTrPPPPrTTTPTTTTTTTTTTTTTTTT",
]

ROUTE6_ROWS = [
    "TTTTTTTTTPPPPPPBTTTTTTTT",
    "TTTTTTTTTPPPPPPBTTTTTTTT",
    "TTTTTTTTTTBBPPPBTTTTTTTT",
    "TTTTTTTTTTPBPPBBTTTTTTTT",
    "TTkkkkkkkrPTPPTTkkkkkkTT",
    "TTgggGgggrPrPPrBkgggggTT",
    "TTgggggggkgPPPPgkgggggTT",
    "TTlllGllllgPPPPglllGllTT",
    "TTggggggggGPPPPGggggggTT",
    "TTggggggggggggggggggggTT",
    "TTggggggggggggggggPPPPTT",
    "TTlllllllGllllllllBBBBTT",
    "TTPPPPPPPPPPPPPPPPBBBBTT",
    "TTPPPPPPPPPPPPPPPPBBBBTT",
    "TTPPPPPPPPPPPPPPPPPPPPTT",
    "TTggggPPPggggggPPPPPPSTT",
    "TTggggPPPgggggggggggggTT",
    "TTggggPPPgggggggggggggTT",
    "TTggggPPPgggggggggggggTT",
    "TTggggPPPPPPPPPPPPPPggTT",
    "TTggggPPPPPPPPPPPPPPggTT",
    "TTggggPPPPPPPPPPPPPPggTT",
    "TTgggggggggggggggPPPggTT",
    "TTWWWWWWWWWWWWWggPPPggTT",
    "TTWWWWWWWWWWWWWggPPPggTT",
    "TTWWWWWWWWWWWWWggPPPggTT",
    "TTWWWWWWWWWWWWWggPPPggTT",
    "TTggggggggPPPPPPPPPPggTT",
    "TTggggggggPPPPPPPPPPggTT",
    "TTggggggggPPPPPPPPPPggTT",
    "TTkkPkrgggPPPggggkkkPkTT",
    "TTGGGGrgggPPPggggkGGGGTT",
    "TTTTTTrgggPPPggggkTTTTTT",
    "TTTTTTrgggPPPggggkTTTTTT",
    "TTTTTTkkkrPPPkkkkkTTTTTT",
    "TTTTTTGGgrPPPPGGGGTTTTTT",
    "TTTTTTTTgrPPPkTTTTTTTTTT",
    "TTTTTTTTgPPPPkTTTTTTTTTT",
    "WWWWWWWWWPPPPkTTTTTTTTTT",
    "WWWWWWWWWPPPgkTTTTTTTTTT",
]

ROUTE7_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "PPPgggggggSggggggggrTTTT",
    "PPPgggggggrggggggggkTTTT",
    "PPPgggggggrggggggggkTTTT",
    "PPPGggggggrggggggFGkTTTT",
    "TTTTggggggrgggggggFkgggG",
    "TTTTggggggrFGFGGPPPBBBkP",
    "TTTTllggllTGFGGPBBBBBBPG",
    "TTTTggggggggggPPBBBBBBPP",
    "TTTTggggggggggPPPPPPPPPP",
    "TTTTggPPPPggggPPBBBBBBGP",
    "TTTTllBBBBgGllllllTkkkPk",
    "TTTTgGBBBBgggggggggkGPGG",
    "PPPPGPPPBBgggggggggkTTTT",
    "TTTTggggggggggggGggkTTTT",
    "TTTTgggggggggggggggkTTTT",
    "TTTTGGGGGGGGGGGGGGGGTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
]

ROUTE8_ROWS = [
    "TTTTrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "TTTTrrrrrrrrPPPPPrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "TTTTrrrrrrrrBBBBFPPPPPPPPrggggggggggggggggggggggggggggggTTTTTTTTTTTTrrrr",
    "TTTTrrrrrrrrBBBBgPPPPPPPPrggggggggggggggggggggggggggggggTTTTTTTTTTTTrrrr",
    "TTTTrrrrrrrrBBBBFPPPPPPPPrggPPPPPPPPPPPPPPPPPPPPPPPPPgggTTTTTTTTTTTTrrrr",
    "TTTTrrrrGFGFGPPPSPPrlllllrggPPPPPPPPPPPPPPPPPPPPPPPPPgggTTTTTTTTTTTTrrrr",
    "GGGGrrrrFGgGGPPPPPPkPPPPPrggPPPPPPPPPPPPPPPPPPPPPPPPPgggTTTTTTFgFGFGrrrr",
    "kBPBBBBkkkgggPPPPPPkPPPPPrggPPPgggggggggggggggggggPPPgggTTTTTTGFGFgFrrrr",
    "PPPBBBBPgggggPPPgggkPPPPPrggPPPggGkkkkkkkkkkkkrgggPPPgggTTTTTTggggggrrrr",
    "PPPBBBBPPPPPPPPPgggklllllrggPPPggkkFgggggggggGkrggPPPgggTTTTTTgggPPPPPPP",
    "PPPPPPPPPPPPPPPPgggkPPPPPkggPPPggkFgggggggGggFgrggPPPgggTTTTTTgggPPPPPPP",
    "PBBBBBBGPPPPPPPPgggkPPPPPGggPPPggkgFggGgggggggFkggPPPgggTTTTTTgggPPPPPPP",
    "PkkkkkkkgggggPPPgggkPPPPPGggPPPggkGGggggggggggGGggPPPgggTTTTTTgggPPPkkkk",
    "GGGGrrrrrrrrgPPPgggkkkkkkkggPPPggkFgggggggggggGrggPPPgggTTTTTTgggPPPrrrr",
    "TTTTrrrrrrrrgPPPggggggggggggPPPggkggggggggggggFrggPPPggggggggggggPPPrrrr",
    "TTTTrrrrrrrrgPPPggggggggggggPPPggGgGggggggGggggrggPPPggggggggggggPPPrrrr",
    "TTTTrrrrrrrrgPPPPPPPPPPPPPPPPPPggrGggggggggggggrggPPPPPPPPPPPPPPPPPPrrrr",
    "TTTTrrrrrrrrGPPPPPPPPPPPPPPPPPPggkFGFGggggFGgGFrggPPPPPPPPPPPPPPPPPPrrrr",
    "TTTTrrrrrrrrGPPPPPPPPPPPPPPPPPPggkgFgFggGFgFGFgkggPPPPPPPPPPPPPPPPPPrrrr",
    "TTTTrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
]

ROUTE9_ROWS = [
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "PPPGGGrgggggggggggggggggggggggrrrrrrggggggrrrrrrgggggggggggPPPPPPrrrrrrr",
    "PPPTTTrgggggggggggggggggggggggrrrrrrggggggrrrrrrGggggggggggPPPPPPrrrrrrr",
    "PPPTTTrgggggggggggrrrrrGggggggrrrrrrggggggrrrrrrggggggGGGGrBrrrPPrrrrrrr",
    "TTTTTTrgggggggggggrrrrrlllllggrrrrrrllGGllrrrrrrllGGllllllrrrrrllrrrrrrr",
    "TTTTTTrgggggggggggrrrrrPPPPPPPrrrrrrPPPPPPrrrrrrPPPPPPPPPPrrrrrPPrrrrrrr",
    "GGGgggrgggggggggggrrrrrPPPPPPPrrrrrrPPPPPPPPPPPPPPPPPPPPPPrrrrrPPrrrrrrr",
    "kkPkkkkllllllllrggrrrrrPPPPPPSrrrrrrrrrrrPPPPPPPPPPPPPPPPPrrrrrPPrrrrrrr",
    "ggGggggPPPPPPPPrrrrrrrrPPPPPPPPPPPPPrrrrrPPPPrrrrrPPPrrrrrrrrrrPPPPPPPPP",
    "ggrggggPPPPPPPPrrrrrrrrPPPPPPPPPPPPPrrrrrPPPPrrrrrPPPrrrrrPPPPPPPPPPPPPP",
    "PkkkrrrBrrrPPPPrrrrrrrrlllllllllllPPrrrrrPPPPrrrrrPPPrrrrrPPPPPPPPPPPPPP",
    "GGGGrrrrrrrllllrrrrrrrrPPPPPPPPPPPggrrrrrllllrrrrrllGrrrrrPPPrrrrrPPPrrr",
    "TTTTrrrrrrrPPPPrrrrrrrrPPPPPPPPPPPggrrrrrggggrrrrrgggrrrrrlllrrrrrlllrrr",
    "TTTTrrrrrrrPPPPPPPPPPPPPPPPPPPPPPggggggggggggggggggggrrrrrPPPrrrrrPPPrrr",
    "TTTTrrrrrrrPPPPPPPPPPPPPPPrrrrrrPGgggggggggggggggggggrrrrrgggrrrrrPPPrrr",
    "TTTTrrrrrrrlllllllllPPllllrrrrrrllgglllllllllllllllllrrrrrlllrrrrrlllrrr",
    "TTTTrrrrrrrPPPPPPPPPPPPPPPrrrrrrgggggggggggggggggggggggggggggggggggggrrr",
    "TTTTkrrrrrrPPPPPPPPPPPPPPPrrrrrrgggggggggggggggggggggggggggggggggggggrrr",
    "TTrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "TTrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
]

ROUTE10_ROWS = [
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrWWWWWWWWWWWWWWWWWWWWrr",
    "rrWWWWWWWWWWWWWWWWWWWWrr",
    "rrWWWWWWWWWWWWWWWWWWWWrr",
    "rrGGGGGGGGGGGGGGGGGWWWrr",
    "rrkkGgkkkkkkkkkkkkrWWWrr",
    "rrggggggggggggggggkWWWrr",
    "rrPPggggggggggggggkWWWrr",
    "PPPPPgggggggggggggkWWWrr",
    "PPPPPgggggggggggggkWWWrr",
    "PPPPPgggggggggggggkWWWrr",
    "rrPPggggggggggggggkWWWrr",
    "rrlllllllllllllGGkTWWWrr",
    "rrGgGgGgGgGgGgGgGgkWWWrr",
    "rrggggggggggggggggkWWWrr",
    "rrrrrrrrrrrgGgGgGgkWWWrr",
    "rrrrrrrrrrrGGGGGggkWWWrr",
    "rrrrrrrrrrrBBBBBGgkWWWrr",
    "rrrrrrrrrrrBBBBBggkWWWrr",
    "PPPPPPPPPrrBBBBBGgkWWWrr",
    "rrPPPPPPPPGBBrBBggkWWWrr",
    "rrPPkkkSkTGPPPPPGgkWWWrr",
    "rrPPPPPPGgGPPPPPggkWWWrr",
    "rrPPPPPGggTPPPPPGgkWWWrr",
    "rrPPPPPgGgGgGgGgGgkWWWrr",
    "rrPPPPPGggTgggggggkWWWrr",
    "rrPPPPGgggGgGgGgGgkWWWrr",
    "rrPPgggGgGTgggggggkWWWrr",
    "rrGgGgGgggGgGgGgGgkWWWrr",
    "rrgggggGgGgggggggGkWWWrr",
    "rrkkkkkkkkkkkkkkkPkWWWrr",
    "rrrrrrrrrrrrrrrrrggWWWrr",
    "rrrrrrrrrrrrrrrrrGgWWWrr",
    "rrrrrrrrrrrrrrrrrggWWWrr",
    "rrrrBrBrBrBrrrrrrGgWWWrr",
    "rrrrBrBrBrBrBrrrrggWWWrr",
    "rgrBBBBBBBBBBrrrrGgWWWrr",
    "PGPPrrrrrrrrrrrrrggWWWrr",
    "rgPTrBBBBBrTrrrrrPPWWWrr",
    "rGSkWBBBBBWkBrrrrPPWWWrr",
    "PPPPPPPPBBWBGrrrrPPWWWrr",
    "rggggPPPPPgPPrrrPPPWWWrr",
    "rrggggSggPPPPrrrPPPWWWrr",
    "rrPPPPPPPPPPPrrrPPPWWWrr",
    "rrPPPPPPPPPPPPPPPPPWWWrr",
    "rrPPPPPPPPPPPPPPPPPWWWrr",
    "rrPPPPPPPPPPPPPPPWWWWWrr",
    "rrWWWWWWWWWWWWWWWWWWWWrr",
    "rrWWWWWWWWWWWWWWWWWWWWrr",
    "rrWWWWWWWWWWWWWWWWWWWWrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrPggggrr",
    "PPPPPPPPPrrrrrrrrPggGgrr",
    "rrrPPPPPPPPPPPPPPPggggrr",
    "rrrPPPPPPPPPPPPSPPggggrr",
    "rrrPPPPPPPPPPPPPPgggggrr",
    "rrrPPPPPPPPPrrrrrgggggrr",
    "rrPPPPPPPPPPrrrrrlGlllrr",
    "rrPPPrrrrrrrrrrrrgggggrr",
    "rrPPPrrrrrrrrrrrrgggggrr",
    "rrlllrrrrrrrrrrrrgggggrr",
    "rrPPPrrrrrrrrrrrrllllGrr",
    "rrPPPrrrrrrrrrrrrggggGrr",
    "rrPgggggggggggggggggggrr",
    "rrggggggggggggggggggggrr",
    "rrggggggggggggggggggggrr",
    "rrrrrrrrrrrggggggGGGggrr",
    "rrrrrrrrrrrggggggGGGggrr",
    "rrrrrrrrrrrggggGGGGGGGrr",
    "rrrrrrrrrrrllGrTTTTTTTrr",
    "rrrrrrrrrrrgggrTTTTTTTrr",
    "rrrrrrrrggggggrTTTTTTTrr",
    "rrrrrrrrggggggrTTTTTTTrr",
    "rrrrrrrrgggggrrTTTTTTTrr",
    "rrrrrrrrPPPggrrTTTTTTTrr",
]

ROUTE11_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTgggPPPPPPPPPPPPPPPPPPggggPPPPPPPPPPPPPPPggggggggTTTTTTTTTTTT",
    "TTTTTrrrTTTTgggPPPPPPPPPPPPPPPPPPggggPPPPPPPPPPPPPPPggggggggTTTTTTTTTTTT",
    "TTTTrrPPrrTTgggPPPPPPPPPPPPPPPPPPggggPPPPPPPPPPPPPPPggggggggTTTTTTTTTTTT",
    "TTTTrrPPrrTTgggPPPggggggggggggPPPggggPPPgggggggggPPPggggggrgTTTTTTTTTTTT",
    "gggGrrPrrrTTgggPPPggSgggggggggPPPggggPPPggggggggggggggggggggTTTTTTTTTTTT",
    "PPPPPPPrrrTTgggPPPggggPPPPPPPPPPPggggPPPPPPPPPPPggggggggkkkBBBBBBTTTTTTT",
    "PPPgggggggPPPPPPPPggggPPPPPPPPPPPggggPPPPPPPPPPPggggggggggPBBBBBBBkkkkkk",
    "PPPgggggggPPPPPPPPggggPPPPPPPPPPPggggPPPPPPPPPPPggggPPPPgPPBBBBBBPPPPPPP",
    "ggggggggggPPPPPPPPPPPPPPPgggggPPPPPPPPPPgggggPPPggggPPPPgPPBBBBBBPPPPPPP",
    "WWWWWWWWWWWWWggPPPPPPPPPPgggggPPPPPPPPPPgggggPPPggggPPPPgPPBBBBBBGPPPPPP",
    "WWWWWWWWWWWWWggPPPPPPPPPPgggggPPPPPPPPPPgggggPPPggggPPPgkkkkkkkkkkPkrrrr",
    "WWWWWWWWWWWWWggggggggggggggggggggggggPPPgggggPPPggggPPPgggggGGGGGGGGTTTT",
    "TTTTTTTTTTTTTugggggggggggggggggggggggPPPPPPPPPPPggggPPPgggggTTTTTTTTTTTT",
    "TTTTTTTTTTTTGGgggggggggggggggggggggggPPPPPPPPPPPggggPPPgggggTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTgPPPgggggggggggggggggggPPPPPPPPPPPggggPPPgggggTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTgPPPPPPPPPPPPPPPPPPPPPPPPPgggggPPPPPPPPPPgggggTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTgPPPPPPPPPPPPPPPPPPPPPPPPPgggggPPPPPPPPPPgggggTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTGPPPPPPPPPPPPPPPPPPPPPPPPPgggggPPPPPPPPPPGGGGGTTTTTTTTTTTT",
]

ROUTE12_ROWS = [
    "rrrrrrrrrrrPPPrrrrrrrrrr",
    "rrrrrrrrrrrggPrrrrrrrrrr",
    "rrrrrrrrrrrggPrrrrrrrrrr",
    "rrrrrrrrrrrggrrrrrrrrrrr",
    "rrrrrrrrrrrggrrrrrrrrrrr",
    "rrrrrrrWWWWIIWWWWWWWWWWW",
    "rrrrrrrWWWWIIWWWWWWWWWWW",
    "rrrrrrrWWWWIIWWWWWWWWWWW",
    "rrrrrrrWWWWIIWWWWWWWWWWW",
    "rrrrrrrWWWWIIWWWWWWWWWWW",
    "rrrrrrrIIIIIIIIIWWWWWWWW",
    "rrrrrrrIIIIIIIIIWWWWWWWW",
    "rrrrrrrIIWWWWIIIWWWWWWWW",
    "rrrrrrrIIWWWWIIIISIIWWWW",
    "rrrrrrrIIWWWWIIIIIIIWWWW",
    "rrrrrrrIIWWWWIIIWWWWWWWW",
    "rrrrrrrIIWWWPPPPPWWWWWWW",
    "rrrrrrrIIWWWBPPPBWWWWWWW",
    "rrrrrrrWWWWWBPPPBWWWWWWW",
    "rrrrrrrWWWWWBPPPBWWWWWWW",
    "rrrrrrrWWWWWTTPTTWWWWWWW",
    "rrrrrrrWWWWWBrPrBWWWWWWW",
    "rrrrrrrrWWWWWIIIWWWWWWWW",
    "rrrrrrrrrWWWWIIIWWWWWWWW",
    "rrrrrrrrrWWWWIIIWWWWWWWW",
    "rrrrrrrrrWWWWIIIWWWWWWWW",
    "rrrrrrrrrIIIIIIIIIIIWWWW",
    "rrrrrrrrrIIIIIIIIIIIWWWW",
    "rrrrrrrrrWWWWWWWWWIIWWWW",
    "rrrrrrrrWWWWWWWWWWIIWWWW",
    "rrrrrrrrWWWWWWWWWWIIWWWW",
    "rrrrrrrrIIWWWIIIIIIIWWWW",
    "rrrrrrrrIIWWWIIIIIIIWWWW",
    "rrrrrrrrIIWWWIIWWWWPWWWW",
    "rrrrrrrrIIWWWIIWWWWPWWWW",
    "rrrrrrrrIIWWWIIWWWGGWWWW",
    "rrrrrrrrIIIIIIIWWWggWWWW",
    "rrrrrrrrIIIIIIIWWWggWWWW",
    "rrrrrrrrIIWWWWWWWWggWWWW",
    "rrrrrrrrIIWWWWWWWWggWWWW",
    "rrrrrrrrIIWWWWWWWWWWWWWW",
    "rrrrrrrTIIWWWWWWWWWWWWWW",
    "TTTTTTTTIIIIIIIIIIIIWWWW",
    "TTTTTTTTIIIIIIIIIIIIWWWW",
    "TTTTTTTTIIWWIIWWWWWWWWWW",
    "TTTTTTTTIIWWIIWWWWWWWWWW",
    "TTTTTTTTIIWWIIWWWWWWWWWW",
    "TTTTTTTTWWWWIIIIIIWWWWWW",
    "TTTTTTTTWWWWIIIIIIWWWWWW",
    "TTTTTTTTWWWWWWWWIIIIWWWW",
    "TTTTTTTTWWWWWWWWIIIIWWWW",
    "TTTTTTTTWWWWWWWWIIWWWWWW",
    "TTTTTTTTWWWWWWWWIIWWWWWW",
    "TTTTTTTTIIIIIIWWIIWWWWWW",
    "TTTTTTTTIIIIIIWWIIWWWWWW",
    "TTTTTTTTIIWWIIWWggGGWWWW",
    "TTTTTTTTIIWWIIWWggggWWWW",
    "TTTTTTTTIIWWIIWWggggWWWW",
    "TTTTTTTTIIWWIIIIggggWWWW",
    "TTTTTTTTIIWWIIIIggggWWWW",
    "TTTTTTTTIIWWWWWWWWWWWWWW",
    "TTTTTTTTIIWWWWWWWWWWWWWW",
    "TTTTTTTTIIWWWWWWWWWWWWWW",
    "TTTTTTTTIIIIIIIIIIIIWWWW",
    "TTTTTTTTIIIIIIIIIIIIWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "kkkkkkkrWWWWWWIIWWWWWWWW",
    "gggggggkkkkkkkISWWWWWWWW",
    "ggggggggggggggIIWWWWWWWW",
    "gggggggkkkkkkkIIWWWWWWWW",
    "rrrrrrrTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIIIIIWWWW",
    "TTTTTTTTWWWWWWIIIIIIWWWW",
    "TTTTTTTTWWWWWWWWWWIIWWWW",
    "TTTTTTTTWWWWWWWWWWIIWWWW",
    "TTTTTTTTWWWWWWWWWWIIWWWW",
    "TTTTTTTTIIGIPPPIGGggWWWW",
    "TTTTTTTTIIgBBBBBFgFgWWWW",
    "TTTTTTTTIIgBBBBBgFggWWWW",
    "TTTTTTTTIIggggggggggWWWW",
    "TTTTTTTTIIkkkkkkkkkkWWWW",
    "TTTTTTTTIIWWWWWWWWWWWWWW",
    "TTTTTTTTIIWWWWWWWWWWWWWW",
    "TTTTTTTTIIWWWWWWWWWWWWWW",
    "TTTTTTTTIIIIIIIIIIWWWWWW",
    "TTTTTTTTIIIIIIIIIIWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIWWWWWWWW",
    "TTTTTTTTTTTTWWIIWWWWWWWW",
    "TTTTTTTTgggTWWIIWWWWWWWW",
    "TTTTTTTTgggGIIIIWWWWWWWW",
    "TTTTTTTTggTGIIIIWWWWWWWW",
    "TTTTTTTTTTggWWIIIIIIWWWW",
    "TTTTTTTTggggWWIIIIIIWWWW",
    "TTTTTTTTIIIIIIIIWWWWWWWW",
    "TTTTTTTTIIIIIIIIWWWWWWWW",
    "TTTTTTTTWWWWWWIIIIIIWWWW",
    "TTTTTTTTWWWWWWIIIIIIWWWW",
    "TTTTTTTTWWWWWWWWWWIIWWWW",
    "TTTTTTTTWWWWWWWWWWIIWWWW",
    "TTTTTTTTkkkkkkIIIIIIWWWW",
    "TTTTTTTTgggggGIIIIIIWWWW",
    "TTTTTTTTggggrrWWIIWWWWWW",
    "TTTTTTTTggggTTWWIIWWWWWW",
    "TTTTTTTTggggTTWWIIWWWWWW",
    "TTTTTTTTggggTTWWIIWWWWWW",
    "TTTTTTTTggggTTIIIIWWWWWW",
    "TTTTTTTTggggTPIIIIWWWWWW",
    "TTTTTTTTggggTPIIWWWWWWWW",
    "TTTTTTTTTTTTTPIIWWWWWWWW",
]

ROUTE13_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTIIIWWWWWWW",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTIIPWWWWWWW",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTIIPWWWWWWW",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTIIPWWWWWWW",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTIIWWWWWWWW",
    "PgggFgFgFgFggggggGGGGGgggggggggggFkggggggggggggggggggggggggGTTIIWWWWWWWW",
    "PPPPkkkkkkkkkkkkgGGGGGkkkkkkkkkgFgBggrkkkkkkGGGGGggggggggggGTTIIWWWWWWWW",
    "PggggggggggggGGGggggggBgggggggggggggggggggggTTTTGggggggggggGTTIIWWWWWWWW",
    "PPPPkkkkkkkkkGGGkkkkkkBGGkkkkkkkkkkkkkkkkkggTTTTGggggggggggGTTIIWWWWWWWW",
    "PFggFggggggggGGGBgFGgGgGgGgGgGgGggggBgggggggTTTTTTTTTTTTTTTTTTIIWWWWWWWW",
    "kkkkkkggkkkkkkkkBFgkkkkkkkkkkkkkkgggBggkkkggTTTTTTTTTTTTTTTTTTIIWWWWWWWW",
    "ggggggggBGggggggggggggggggGGGgBgggggggggggggggIIIIIIIIIIIIIIIIIIWWWWWWWW",
    "kkkkkkkkBggkkkkkkkkkkkkkkkGGGGBggkkkkkkkkSkkggIIIIIIIIIIIIIIIIIIWWWWWWWW",
    "BgggggggggggggggggggggBgGgGGGGGgggggggggggggggWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "BGkkkkkkggkkkkkkkkkkkrBGkkkkkkkkkkkkkkkkkkkkkkWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "TTTTTTTTTTTTTTTTTTTTTTTTWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

ROUTE14_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTrggggFgFgFgggggggg",
    "TTTTTTrggkkkkkkkkkkkkPPP",
    "TTTTTTrggggggggggggggggP",
    "TTTTTTrkkkkkkkkkkkggkPPP",
    "TTTTTTrggggggggggggggggg",
    "TTTTTTrkkggkkkkkkkkkkkkk",
    "TTTTTTrggggggggggggggggg",
    "TTTTTTrkkkkkkkgggSkkkkkk",
    "TTTTTTrgFgFgggPPPggggggg",
    "TTTTTTrFgFggggPPPkrrrrrr",
    "TTTTTTrgFgggggPPPkTTTTTT",
    "TTTTTTrGGGGGGGPPPkTTTTTT",
    "TTTTTTrTTTTTTGPPPkTTTTTT",
    "TTTTTTrTTTTTTGPPPkTTTTTT",
    "TTTTTTrgggggTTPPPkTTTTTT",
    "TTTTTTrgggggTTPPPkTTTTTT",
    "TTTTTTrgggggTTPPPkTTTTTT",
    "TTTTTTrgggggTTPPPkTTTTTT",
    "TTTTTTrgggggTTPPPkWWWWWW",
    "TTTTTTrgggggTTPPPkWWWWWW",
    "TTTTTTrggggGTTPPPkWWWWWW",
    "TTTTTTrGllllTTPPPkWWWWWW",
    "TTTTTTrggPPPTTPPPkWWWWWW",
    "TTTTTTrggPPPTTPPPkWWWWWW",
    "TTTTTTrggPPPTTPPPkWWWWWW",
    "TTTTTTrggPPPTTPPPkGGGGWW",
    "TTTTTTrggPPPTTPPPkkPkrWW",
    "TTTTTTrggPPPTTPPPggggkWW",
    "TTTTTTrggPPPTTPPPggggkWW",
    "TTTTTTrggPPPTTPPPggggkWW",
    "TTTTTTrggPPPGGPPPggggkWW",
    "TTTTTTrggPPPTTPPPggggkWW",
    "TTTTTTrggPPPTTPPPggggkWW",
    "TTTTTTrggPPPTTPPPggggkWW",
    "TTTTTTrggPPPTTPPPggFgkWW",
    "TTTTTTrggPPPTTPPPgFggkWW",
    "TTTTTTrggPPPTTPPPggFgkWW",
    "TTTTTTrggPPPTTPPPgFggkWW",
    "TTTTTTrggPPPTTPPPggFgkWW",
    "TTTTTTkGGPPPTTPPPgFgGkWW",
    "TTPPPPPPPPPPTTPPPggFGkWW",
    "TTPPPPPPPPPPggPPPgggGkWW",
    "gGPPPPPPPPPPggPPPgggGkWW",
    "grggggggggggggPPPgggGkWW",
    "lTggFgFgFgFgggPPPgggGkWW",
    "gGgggFgFgFggggPPPgggGkWW",
    "ggGgggggggggggPPPgggGkWW",
    "PPPPPPPPPPPPPPPPPgggGkWW",
    "PPPPPPPPPPPPPPPPPggGGkWW",
    "PPPPPPPPPPPPPPPPPgggGkWW",
    "kkkkkkkkkkPkkkkkkkkkkkWW",
    "GGGGGGGGGGGGGGGGGGGGGGWW",
    "TTTTTTTTTTTTTTTTTTTTTTWW",
    "TTTTTTTTTTTTTTTTTTTTTTWW",
    "TTTTTTTTTTTTTTTTTTTTTTWW",
]

ROUTE15_ROWS = [
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "TTTTTTTTTTTTTTTTrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "TTTTTTGGGGGgggggrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "TTTTTTkkPkBBBBBBkggggggggggggggggggggggggggggggggggggggggggggggggggggggg",
    "TTTTTTGGGPBBBBBBPlllllllllllllllllllllllllllllllllllllllllllPlllllllllll",
    "PPPPPPPPPPPBBBBBPPPPggggggFGFGFGgggggggggGgggggFGFGggggFGFGgggggggFGFGgg",
    "PPPPPPPPPPPPPPPPPPPPgggggggFgFgFgggggggggSggggggFgFgggggFgFggggggggFgFgg",
    "PPPPPPPPPPBBBBBBGPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "rrrrrrkPkkkkkkkkrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "TTTTTTGGGGGGGGGGrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "TTTTTTTTTTTTTTTTkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkPPP",
    "TTTTTTTTTTTTTTTTGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]

ROUTE16_ROWS = [
    "WWTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "WWTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "WWTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "WGPTTTTTTPPPPGPTTTTTTBBBBBBTTTTTTTTTTTTTTTTTTTTT",
    "WrPkkkkkkBBBBBPkkkkkrBBBBBBrkkkkkkkkkkkkkkTTTTTT",
    "WrgPPPPPPBBBBBPPPPPPPBBBBBBPPPPPPgggggggggTTTTTT",
    "WrgPPPPPPPPPPPPPPPPPPBBBBBBPPPPPPgggggggggTTTTTT",
    "WrgPPPPPPPPPPPPPPPPPPBBBBBBGPPPPPgggggggggTTTTTT",
    "WrgPPPPPPPPPPPPPPggggBBBBBBgggPPPPPPPPPPPPTTTTTT",
    "WrgggggggggggggggggggBBBBBBgggPPPPPPPPPPPPTTTTTT",
    "WrPkkkkkkkkkkkkkkkkkkBBBBBBkkrPPPPPPPPPPPPTTTTTT",
    "WrggggggggggggggggggPBBBBBBPGkkkkSkkkkkkkGTTTTTT",
    "WrgPPPggggPPPPPPPPPPPBBBBBBPPPTTTggggggggggggggP",
    "WrgPPPggggPPPPPPPPPPPTGGGGPPPPgggggggggggggggggP",
    "WrgPPPggggPPPPPPPPPPPBBBBBBGPPTTTggggggggggggggP",
    "WrgPPPggggPPPPPkrrrrPrrrrrrPrrrrrrrrrrrrrrrrrrrr",
    "WrgPPPggggPPPPPkTTTTPTTTTTTPTTTTTTTTTTTTTTTTTTTT",
    "WrgPPPSPPPPPPPPkTTTTPTTTTTTPTTTTTTTTTTTTTTTTTTTT",
    "WrgPPPPPPPPPPPPkTTTTPTTTTTTPTTTTTTTTTTTTTTTTTTTT",
    "WrPPPPPPPPPPPPPkTTTTPTTTTTTPTTTTTTTTTTTTTTTTTTTT",
]

ROUTE17_ROWS = [
    "WPPPPPPPPPPPPPPkTTTTTTTT",
    "WPGPPPPPPPPPPPGkTTTTTTTT",
    "WPPPPPPPPPPPPPPkPWWWWWWW",
    "WrPPPPPPPPPPPPPTPWWWWWWW",
    "WrPPPPPPPPPPPPPPPWWWWWWW",
    "WrPPPPPPPPPPPPPkPWWWWWWW",
    "WkGPPPPPPPPPPPGkPWWWWWWW",
    "WTPPPPPPPPPPPPPkPWWWWWWW",
    "WrPPPPPPPPPPPPPTPGGGGGGW",
    "WrPPPPPPPPPPPPPkkkkkkkrW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WkGPPPPPPPPPPPPPPPPPPGkW",
    "WTPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPTW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WkGPPPPPPPPPPPPPPPPPPGkW",
    "WTPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPTW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WkGPPPPPPPPPPPPPPPPPPGkW",
    "WTPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPTW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WkGPPPPPPPPPPPPPPPPPPGkW",
    "WTPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPTW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPWWWWPPPPPkW",
    "WkGPPPPPPPPPPWWWWPPPPGkW",
    "WTPPPPPPPPPPPWWWWPPPPPkW",
    "WrPPPPPPPPPPPWWWWPPPPPTW",
    "WrPPPPPPPPPPPWWWWPPPPPkW",
    "WrPPPPPPPPPPPWWWWPPPPPkW",
    "WkGPPPPPPPPPPWWWWPPPPGkW",
    "WTPPPPPPPPPPPWWWWPPPPPkW",
    "WrPPPPPPPPPPPWWWWPPPPPTW",
    "WrPPPPPPPPPPPWWWWPPPPPkW",
    "WrPPPPPPPPPPPWWWWPPPPPkW",
    "WkGPPPPPPPPPPWWWWPPPPGkW",
    "WTPPPPPPPPPPPWWWWPPPPPkW",
    "WrPPPPPPPPPPPWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPrWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPrWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPrWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPTW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPkW",
    "WkGPPPWWWWPPPWWWWPPPPGkW",
    "WTPPPPWWWWPPPWWWWPPPPPkW",
    "WrPPPPWWWWPPPWWWWPPPPPTW",
    "WrPPPPPPPPPPPWWWWPPPPPkW",
    "WrPPPPPPPPPPPWWWWPPPPPkW",
    "WkGPPPPPPPPPPWWWWPPPPGkW",
    "WTPPPPPPPPPPSWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPTW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WkGPPPPPWWWWWWWWWPPPPGkW",
    "WTPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPTW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WkGPPPPPWWWWWWWWWPPPPGkW",
    "WTPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPTW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WkGPPPPPWWWWWWWWWPPPPGkW",
    "WTPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPTW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WkGPPPPPWWWWWWWWWPPPPGkW",
    "WTPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPTW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WkGPPPPPWWWWWWWWWPPPPGkW",
    "WTPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPTW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPrPPPPPPPPPkW",
    "WkGPPPPPWWWWWWWWWPPPPGkW",
    "WTPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPTW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPWWWWWWWWWPPPPPkW",
    "WkGPPPPPWWWWWWWWWPPPPGkW",
    "WTPPPPPPWWWWWWWWWPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPTW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WrPPPPPPPPPPPPPPPPPPPPkW",
    "WkkkkkkrPPPkkkPPPkkkkkkW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPPPPPPPkWWWWWW",
    "WWWWWWWrPPPSPPPPPkWWWWWW",
    "WWWWWWWrPPPlPllllkWWWWWW",
    "WWWWWWWrPPPggggggkWWWWWW",
]

ROUTE18_ROWS = [
    "WWWWWWWrPPPggggGFkWWWWWWWWWWWWWWrTTTTTTTTPTTTTTTPTTTTTTTTTTT",
    "WWWWWWWrgFgggggFgkWWWWWWWWWWWWWWrTTTTTTTTPTTTTTTPTTTTTTTTTTT",
    "WWWWWWWrFGggggggFkWWWWWWWWWWWWWWrTTTTTTTTPTTTTTTPTTTTTTTTTTT",
    "WWWWWWWrgFgggggFGkWWWWWWWWWWWWWWrTTTTTTTTPTTTTTTPTTTTTTTTTTT",
    "WWWWWWWrFgggggggFkWWWWWWWWWWWWWWrTTTTTTTTPTTTTTTPTTTTTTTTTTT",
    "WWWWWWWrgFgggggFgkWWWWWWWWWWWWWWrTTTTTTTTPTTTTTTPTTTTTTTTTTT",
    "WWWWWWWrFgggggggFkWWWWWWWWWWWWWWrTTTTTTTTPBBBBBBPTTTTrTTTTTT",
    "WWWWWWWrgPPPPPPPggGGGGGGGGGGGGGGkkkkkSkkkPBBBBBBPgggSkkkkkkk",
    "WWWWWWWrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPBBBBBBPPPPPPPPPPPP",
    "WWWWWWWrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPBBBBBBPPPPPPPPPPPP",
    "WWWWWWWkPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPBBBBBBGPPPPPPPPPPP",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTuuuuuuuuuggrrrrrrrrrr",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTgggggggggggTTTTTTTTTT",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTgggggggggGGTTTTTTTTTT",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTgggggggguTTTTTTTTTTTT",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTggggggggTTTTTTTTTTTTT",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTggggggggTTTTTTTTTTTTT",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTggggggggTTTTTTTTTTTTT",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWruuuuuuuurWWWWWWTTTTTT",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWTTTTTT",
]

ROUTE19_ROWS = [
    "rrrrrrrsssPPPssssrrrrrrr",
    "rrrrrrrssssssssssrrrrrrr",
    "rrrrrrrsssssssrssrrrrrrr",
    "rrrrrrrllgglllrssrrrrrrr",
    "rrrrrrrssggsssrssrrrrrrr",
    "rrrrrrrlllllllrssrrrrrrr",
    "rrrrrrrsssssssrssrrrrrrr",
    "rrrrrrrlllllllrssrrrrrrr",
    "rrrrrrrssssssssssrrrrrrr",
    "WWWWWWWWssssssssWWWWWWWW",
    "WWWWWWWWssssssssWWWWWWWW",
    "WWWWWWWWssssssssWWWWWWWW",
    "WWWWWWWWWssssSssWWWWWWWW",
    "WWWWWWWWWWWsssssWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
    "WWWWWWWWWWIIIIWWWWWWWWWW",
]

ROUTE20_ROWS = [
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWrrrrrrrrrrWWWssssssssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWrrrrrrrrrrrsssssssssssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWsggssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWrrrrrrrrrrrssssssssssssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWsggsssWWWWWWWWWWWWWWWWWWWWWWWWWWWWrrrrrrrrrrrssssrrrrrsssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWsssssWWWWWWWWWWWWWWWsssWWWWWWWWWWWsrrrrrrrrrssssrrrrrrrssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWWWW",
    "PPPWWWWWWWWWWWWWWWWWWsssWWWWWWWWWWWWWWWWWssssWWWWWWWWWWssrrrPrrrSsssrrrrrrrrrsWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWsssWWWWWWPPP",
    "PssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssP",
    "PPPWWWWWWWWWWWWWWPWWWWWWWWWWWWWWPWWWWWWWWWWssWWWWWWWWWWWsssssssssssrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWPPP",
    "WWWWWWWWWWWWWWWWWPWWWWWWWWWWWWWWPWWWWWWWWWWWWWWWWWWWWWWWsssssssWWWPrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWPWWWWWWWWWWWWWWsWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWPrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWsWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWPsrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWPSrrrPrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWPsssssssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWssssWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

ROUTE21_ROWS = [
    "TTTTTIIIWWWkIIkkkkTTTTTT",
    "TTTTTIIIIIIIISgggkTTTTTT",
    "TTTTTIIIIIIIIIgggkTTTTTT",
    "TTTTTIIIWWWggggggkTTTTTT",
    "TTTTTTrWWWWggggggkTTTTTT",
    "TTTTTTrWWWWggggggkTTTTTT",
    "TTTTTTrWWWWggggggkTTTTTT",
    "TTTTTTrWWWWggggggkTTTTTT",
    "TTTTTTrWWWWggggggkTTTTTT",
    "TTTTTTrWWWWggggggkTTTTTT",
    "TTTTTTrWWWWggggggkkkkkkk",
    "TTTTTTrWWWWWIIWWWWWWWWWW",
    "TTTTTTrWWWWWIIWWWWWWWWWW",
    "TTTTTTrWWWWWIIWWWWWWWWWW",
    "kkkkkkkWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWssWWWWWW",
    "WWWWWWWWWWWWIIWsssWWWWWW",
    "WWWWWWWWWWWWIIPssWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWssWWWWIIWWWWWWWWWW",
    "WWWWWsssssWWIIWWWWWWWWWW",
    "WWWWWsssssPPIIWWWWWWWWWW",
    "WWWWWsssssWWIIWWWWWWWWWW",
    "WWWWWWWWsWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWsWWWWWW",
    "WWWWWWWWWWWWIIPPsssWWWWW",
    "WWWWWWWWWWWWIIWWsssWWWWW",
    "WWWWWWWWWWWWIIWWssWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWsWWWIIWWWWWWWWWW",
    "WWWWWWWWsssPIIWWWWWWWWWW",
    "WWWWWWWWWssWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWsssWWWWW",
    "WWWWWWWWWWWWIIWssssWWWWW",
    "WWWWWWWWWWWWIIPsssWWWWWW",
    "WWWWWWWWWWWWIIWWssWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWssssWWIIWWWWWWWWWW",
    "WWWWWWsssssPIIWWWWWWWWWW",
    "WWWWWWWssssWIIWWWWWWWWWW",
    "WWWWWWWWsssWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWssPIIWWWWWWWWWW",
    "WWWWWWWssssWIIWWWWWWWWWW",
    "WWWWWWWsssWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWIIWWWWWWWWWW",
    "WWWWWWWWWWWWPPWWWWWWWWWW",
    "WWWWWWWWWWWWPPWWWWWWWWWW",
    "WWWWWWWWWWWWPPWWWWWWWWWW",
    "WWWWWPPPPPPPPPWWWWWWWWWW",
    "WWWWWPPPPPPPPPWWWWWWWWWW",
]

ROUTE22_ROWS = [
    "rrrrTTTPPPTTTrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPP",
    "rrrrTTTPPPTTTrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrPPPPP",
    "rrrrTTTPPPTTTrrrrrrrrrrrrrrrrrrrrrggggggggrPrrrP",
    "rrrrkBBBPPBBBrrrrrrrrrrrrrrrrrrrrrllllglllrPPPrr",
    "rrkkBBBBPPBBBkrkkkkkkkPPPPPPPPPPPPPPPPPPggrPPPPP",
    "rrkTBTTBPPTTBTrPPPPPPPPPPPPPPPPPPPPPPPPPGGrrrPrr",
    "rrkTTGGPPPGGTTrPPPPPPPPPPPPPPPPPPPPPPPPPTTgggggP",
    "rrkPPPPPPPPPPPrgggggggggggggrrrrrrggggggTTgPPPPP",
    "rrkPPPPPPPPPPPrlllllllWWWWWWrrrrrrllggllTTgPPPPP",
    "rrklllllPPGgllrgggggggWWWWWWrrrrrrggggggTTgPPPPP",
    "rrkgggggggggggrgggggggWWWWWWrrrrrrggggggTTgPPPrr",
    "rrkgggggggggggrgggggggWWWWWWrrrrrrggggggTTgPPPrr",
    "rrkkgggSkkkkkkkgggggggGGGGGGrrrrrrggggggTTgPPPrr",
    "rrrrggGgggggggggggggggggggggrrrrrrggggggTTgPPPrr",
    "rrrrggggggggggggggggggggggggrrrrrrggggggggggggrr",
    "rrrrlllllllllllllllllllllllllllllllllllgglllllrr",
    "rrrrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPrr",
    "rrrrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPrr",
    "rrrrPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
]

ROUTE23_ROWS = [
    "rrrrrrrrrBPPPBrrrrrrrrrr",
    "rrrrrrrPPPPPPBPPrrrrrrrr",
    "TTTTTTkPkPPPPPPPPkTTTTTT",
    "TTTTTTkPkkPPPPkPPkTTTTTT",
    "TTTTTTPPPkPPPPkPkkTTTTTT",
    "TTHHHHkPPPPPPkPPkkHHHHTT",
    "TTBBBBkPPPPPPkPPPkBBBBTT",
    "TTBBBBPPkPPPPPPPPPBBBBTT",
    "TTBBBBPPkPPPPPPPkPBBBBTT",
    "TTBBBBkPPkPPPkPPkPBBBBTT",
    "TTBBBBkPPkPPPkPPkPBBBBTT",
    "TTBBBBPPPPPPPkPPPPBBBBTT",
    "TTBBBBkkkPPPPkPkPPBBBBTT",
    "TTBBBBkPkPPPPkPkPPBBBBTT",
    "TTBBBBkPkPPPPkPkPkBBBBTT",
    "TTkBBkkPkPPPPPPkPkkBBkTT",
    "TTSPPZPPPPPPPPPPPPZPPZTT",
    "TTPPPPPPPPPPPPPPPPPPPPTT",
    "TTPGPPPPPPPPPPPPPPPPPPTT",
    "TTPPPPPPPPPPPPPPPPPPPPTT",
    "TTrrrrrrrrPPPrrrrrrPPGTT",
    "TTrrrrrrrrPPPrrrrrrPPGTT",
    "TTrrrrrrrrrrrrrrrrrPPGTT",
    "TTrrrrrrrrrrrrrrrrrPPGTT",
    "TTrrrrrrrrrrrrrrrrrPPGTT",
    "TTrrrrrrrrrrrrrrrrrrGGTT",
    "TTrrrrrrrrrrrrrrrrrrrGTT",
    "TTrrrrrrrrrrrrrrrrrrrGTT",
    "TTrkrPrkrrrrrrrrrrPrrGTT",
    "TTGZPPPZrrrrrrrrrPPPPPTT",
    "TTPPPPPPPrrrrrrrrPPPPPTT",
    "TTPZPPPPrrrrrrrrrFPPPPTT",
    "TTPPPPPPPPPPPPPPPPFPFPTT",
    "TTrPPPPPPrrrrrrrrrrrrrTT",
    "TTPGPPPGrrrrrrrrrrrrrrTT",
    "TTrZPPPPPrrrrrrrrrrrrrTT",
    "TTPPPPPPrrrrrrrrrrrrrrTT",
    "TTPPPPPPPrrrrrrrrrrrrrTT",
    "TTPrPPPPrrrrrrrrrrrrrrTT",
    "TTPPPPPPrrrrrrrrrrrrrrTT",
    "TTrGPPPGPrrrrrrrrrrrrrTT",
    "TTPPPPPZPrrrrrrrrrrrrrTT",
    "TTrPPPPPPPrrrPPPPPPrPPTT",
    "TTPrPPPPPPPrrPPPPPPPPPTT",
    "TTPPPPPPPPPrrPPPPPPPPPTT",
    "TTBBBBPPPPPGrrrPPPPPPPTT",
    "TTBBBBPPPPPGrrrPPPPPPPTT",
    "TTBBBBBBBPPGPPGPPPPPPPTT",
    "TTBBBBBBBPPPPPPPPPFPFPTT",
    "TTBBBBBBBPPPPPPPPFPFPPTT",
    "TTBBBBBBBPPPPPPPPPPPPPTT",
    "TTkBBkBBkPPPPPPPPPPPPPTT",
    "TTZPPZPPZPPPPPPBBBBBBBTT",
    "TTPPPPPPPPPPPPPBBBBBBBTT",
    "TTPPPPPPPPPPPPPBBBBBBBTT",
    "TTBBBBBBBBBBPPPBBBBBBBTT",
    "TTBBBBBBBBBBPGGBBBBBBBTT",
    "TTBBBBBBBBBTGGGBBBBBBBTT",
    "TTBBBBBBBBBBPPPBBBBBBBTT",
    "TTBBBBBBBBBBPPPBBBBBBBTT",
    "TTBBBBBBkBBkPPPkBBkBBBTT",
    "TTBBBBBBZPPZPPPZFPZBBBTT",
    "TTBBBBBBPPPPPPPGGPFBBBTT",
    "TTBBBBBBPPPPPPPPFPGBBBTT",
    "TTBBBBBBPPPrrPPPGGFBBBTT",
    "TTBBBBBBPPPrrPPPPPPBBBTT",
    "TTBBBBBBrPPPrPPPPPPBBBTT",
    "TTBBBBBBrPGGrPPPPPPBBBTT",
    "TTBBBBBBrPPPrPPrrPPBBBTT",
    "TTBBBBBBrPPPrPPrrPPBBBTT",
    "TTBBBBBBPPPrrPPGrPPBBBTT",
    "TTBBBBBBPPPrrPPGrPPBBBTT",
    "TTBBBBBBPPPPPPPrPPPkBkTT",
    "TTBBBBBBrGPPPPPrPPPZPZTT",
    "TTBBBBBBrrPPPGFPFPPPPPTT",
    "TTBBBBBBrrPPPFPFPPPPPPTT",
    "TTBBBBBBrrPPPGPPGPPPPPTT",
    "TTBBBBBBIIPPPPPPPPPPPPTT",
    "TTBBBBBBIIWWWWWWPPPPPPTT",
    "TTBBBBBBIIWWWWWWBBBBBBTT",
    "TTBBBBBBIIWWWWWWBBBBBBTT",
    "TTBBBBBBIIWWWWWWBBBBBBTT",
    "TTBBBBBBIIWWWWWWBBBBBBTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTBBBBBWIIBBBBBBBBBBBBTT",
    "TTBBBBTWIIBBBBBBBBBBBBTT",
    "TTBBBBBWIIBBBBBBBBBBBBTT",
    "TTBBBBkWIIBBBBBBBBBBBBTT",
    "TTBBBWBWIIWWWWWWWWWBBBTT",
    "TTBBBWWWIIWWWWWWWWWBBBTT",
    "TTBBBWWWIIWWWWWWWWWBBBTT",
    "TTBBBWWWIIWWWWWWWWWBBBTT",
    "TTBBBWWWIIWWWWWWWWWBBBTT",
    "TTBBBWWWIIsssWWWWWWBBBTT",
    "TTBBBWWWIIsssWWWWWWBBBTT",
    "TTBBBWWWIIsssWWWWWWBBBTT",
    "TTBBBWWWIIsssWWWWWWBBBTT",
    "TTWWWWWWIIWWWWWWWWWBBBTT",
    "TTWWWWWWIIWWWWWWWWWBBBTT",
    "TTWWWWWWIIWWWWWWWWWBBBTT",
    "TTWWWWWWIIWWWWWWWWWBBBTT",
    "TTWWWWWWIIWWWWWWWWWBBBTT",
    "TTBBBBBBIIBBBWWWBBBBBBTT",
    "TTBBBBBBIIBBTWWWBBBBBBTT",
    "TTBBBBBBIIBBBWWWBBBBBBTT",
    "TTBBBBBBIIBBkWWWBBBBBBTT",
    "TTWWWWWWIIWWBWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTWWWWWWIIWWWWWWWWWWWWTT",
    "TTBBBBBBIIBBPPPBBBBBBBTT",
    "TTBBBBBBIIBBPGGBBBBBBBTT",
    "TTBBBBBBIIBTGGGBBBBBBBTT",
    "TTBBBBBBIIBBPPPBBBBBBBTT",
    "TTBBBBBBIIBkPPPkBBBBBBTT",
    "TTPPPPPPIIPZPPPZPPPPPPTT",
    "TTGPPPPPIIPPPPPPPPPPPGTT",
    "TTGPPPPPPPPPPPPPPPPPPGTT",
    "TTPPPPPPPPPPPPPPPPPPPPTT",
    "TTPPPBBBBPPPPPBBBBBBBBTT",
    "TTPGPBBBBPPPPPBBBBBBBBTT",
    "TTPPPBBBBPPPPPBBBBBBBBTT",
    "TTPPPBBBkPPPPPBBBBBBBBTT",
    "TTGGPPPPZPPPPPPPPPPPPPTT",
    "TTTTFPPPPPPPPPPFPPFPPFTT",
    "TTTTPFPPPPPPPPPPPPPPPPTT",
    "TTTTFPPPPPPPPPPPPFPPFPTT",
    "TTHHPPPPPPPPPPPPPPPPPPTT",
    "TTBBBBPGGBBPPPBBBBBBBBTT",
    "TTBBBTGGGBBPPPBBBBBBBBTT",
    "TTBBBBPPPBBPPPBBBBBBBBTT",
    "TTkBBkPPPkBPPPBBBBBBBkTT",
    "TTZFPZPPPZPPPPPPPPPPPZTT",
    "TTGGPFPPPPPPPPPPPPPPGGTT",
    "TTTTFPPPPPPPPPPPPPPPTTTT",
    "TTTTGGPPPPPPPPPPPPPPTTTT",
    "TTTTTTPPPPPPPPPPPPPPTTTT",
    "TTTTTTBBBBBPPPGGBBBBTTTT",
    "TTTTTTBBBBBPPPGGBBBBTTTT",
    "TTTTTTBBBBBPPPPPBBBBTTTT",
    "TTTTTTkBBBBPPPPPkBBkTTTT",
    "TTTTTTZPPPPPPPPPZPFZTTTT",
    "TTTTTTTPPPPPPPPPPPPFTTTT",
    "TTTTTTTPPPPPPPPPPPFPTTTT",
    "TTTTTTTPPPPPPPPPPFPFPFTT",
    "BrrTkkrPPGkPPPrrrrrrrkTT",
    "rrrrTTTBPPTPPPrrrrrrrrTT",
    "rrrrTTTTPPPPPPrrrrrrrrTT",
    "rrrrTTTTPPPPPPrrrrrrrrTT",
    "rrrrTTTTPPPPPPrrrrrrrrTT",
    "rrrrTTTTPPPPPPrrrrrrrrrr",
    "rrrrTTTTPPPPPPrrrrrrrrrr",
]

ROUTE24_ROWS = [
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrPPPPPPPPPrPPPrgggPPP",
    "rrrrPPPPPPPPPrPPPrgGgPPP",
    "rrrrPPPPPPPPPrPPPrgggPPP",
    "rrrllllPPllllrPPPrllllll",
    "rrrPPPPPPPPPPPPPPPPPPPPP",
    "rrrPPPPPPPPPPPPPPPPPPPPP",
    "rrrPPPPPPPPPPPPPPPPPPPPP",
    "rrrFGFggggPPPTTTTTTTTTTT",
    "rrrGFgggggPPPTgggggggggg",
    "rrrFggggggPPPTgggrrrrrrr",
    "rrrgFgggggPPPTgggrrrrrrr",
    "rrrFGgggggPPPTgggrrrrrrr",
    "rrrgggggggPPPTgggrrrrrrr",
    "rrrGggWWWkPPPTgggrrrrrrr",
    "rrrgggWWWBPPPrgggrrrrrrr",
    "rrrGggWWWBPPIBgggrrrrrrr",
    "rrrgggWWWBPPIBgggrrrrrrr",
    "rrrgggWWWBPPIBgggrrrrrrr",
    "rrrgggWWWBPPIBgggrrrrrrr",
    "rrrgggWWWBPPIBgggrrrrrrr",
    "rrrgggWWWBPPIBgggrrrrrrr",
    "rrrgggWWWBPPIBgggrrrrrrr",
    "rrrgggWWWBSPIBgggrrrrrrr",
    "rrrgggWWWBPPIBgggkrrrrrr",
    "rrrgggWWWBPPIBgggkWWWWWW",
    "rrrgggWWWBPPIBgggkWWWWWW",
    "rrrgggWWWBPPIBgggkWWWWWW",
    "rrrgggWWWBPPIBgggkWWWWWW",
    "rrrgggWWWBPPIBgggkWWWWWW",
    "rrrrWWWWWBPPIBgggkWWWWWW",
    "rrrrWWWWWBPPIBgggkWWWWWW",
    "rrrrWWWWWBPPIBgggkWWWWWW",
    "rrrrWWWWWBPPIBgggkWWWWWW",
    "rrrrWWWWWBPPIBgggkWWWWWW",
    "rrrrWWWWWBPPIPgggkWWWWWW",
    "rrrrWWWWWBPPIPgggkWWWWWW",
    "rrrrWWWWWBPPIPPPgkWWWWWW",
]

ROUTE25_ROWS = [
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrTTBBrrrrrrrrrrrrrrrrrr",
    "rrrrrrrrrrrrgggTgggTgggggTgggggTggGFgFgFGFrTTTTTTBBTTTTTTTTTTTrrrrrrrrrr",
    "PggggggggggggggTgggTgggggTgggggTggggggggGgkTTTTTTrrrrrTTTTTTTTWWWWrrrrrr",
    "PggggggggggggggGgggGgggggTTTGTgggggggggggGkkkkkkrBBrBBkkkksssssssssssssP",
    "PggggggggggggggGTGTGTggggTgggTggggGTGFGFGgggggggggPPPgggggsssssssssssssP",
    "llllllllllTTGGTTGgggTGTTGTgggGggggGTFGFGGGggGggPPPPPPPPPGgsssssssssssssP",
    "PPPPPPPPPPPPPGggTgggTggggTgggGgGTTggGggggggggggPPPPPPPPPgggggkWWWWWWWrrr",
    "PPPPPPPPPPPPPTggTTggTgggggggggSgTGGgGggggGgGgGggggggggggGgGgGkWWWWWWWWWW",
    "PPPPPPPPPPPPPTggGgGGTGTggggggGgGTGFgFgFGgGgWWWWWWPPPPPWWWWWWgkWWWWWWWWWW",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTIITTTTBBWWWWWWPPPPPWWWWWWGkWWWWWWWWWW",
    "gggggggggggggggggggggggggggggggggggggggggGGWWWWWWPPPPPWWWWWWgkWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrgGGGGGGGggGgGGGGGGGGkWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrBBBBBBBBBBBBBBBBBBBBkWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
]

MOSSMERE_ROWS = [
    "BBBBPPPBBBBTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "BBBBPPPBBBBTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "BBBBPPPBBBBTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "BBBBPPPBBBBTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "BBBBPPPBBBBTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "BBBBPPPBBBBgggggggggggggTTTggggggggggggPgPGPGPGPgPgTTT",
    "BBBBPPPBBBBgPPPPPPPPPPPgTTTggggggggggggGPGPgPgPgPGgTTT",
    "BBBBPPPBBBBgPPPPPPPPPPPgTTTggggGGPgGPGgPgGPGGPgGgggTTT",
    "TGGPPPPPGGTgPPPPPPPPPPPgTTTgggggTTTTTTTTTTTTTTTggggTTT",
    "BrBrPPPrBrBgPPPgggggPPPgTTTgggggTTTTTTTTTTTTTTTggggTTT",
    "TTTTIPPTTTTgPPPggPggPPPgTTTgggggTTTTTTTTTTTTTTTggggTTT",
    "TTTTPPPTTTTgggggTTTgggggTTTgggggTTTTTTTTTTTTTTTggggTTT",
    "TTTrggSrTTTgggggTTTgggggTTTgggggTTTTTTTTTTTTTTTggggTTT",
    "TTTgggggTTTgggggTTTgggggTTTgggggTTTTTTTTTTTTTTTggggTTT",
    "TTTgggggTTTgggggTTTgggggTTTgggggTTTTTTTTTTTTTTTggggTTT",
    "TTTgggggTTTgggggTTTgggggTTTgggggggggggggGGGggggggggTTT",
    "TTTgggggTTTgggggTTTgggggTTTgggggggggggggPPPggggggggTTT",
    "TTTgggggTTTgggggTTTgggggTTTgggggggggggggPPPgGGPGGPgTTT",
    "TTTgggggTTTgggggTTTgggggTTTgggggggggggggPPPggTTTTTTTTT",
    "TTTgggggTTTgggggTTTgggggTTTggggggggggPggPPPggTTTTTTTTT",
    "TTTgggggTTTgggggTTTgggggTTTggggggTTTTTTgPPPggTTTTTTTTT",
    "TTTgggggTTTgggggTTTgggggTTTggggggTTTTTTgPPPggTTTTTTTTT",
    "TTTgggggTTTgggggTTTgggggTTTGgGgGgTTTTTTgPPPggTTTTTTTTT",
    "TTTgggggTTTgggggTTTPgPPPPPPPPPPPgTTTTTTgPPPggTTTTTTTTT",
    "TTTgggggTTTgggggTTTTTPPPPPPPPPPPgTTTTTTgPPPggTTTTTTTTT",
    "TTTgggggTTTgggggTTTTTPPPPPPPPPPPgTTTTTTgPPPgGPgPGPgTTT",
    "TTTgggggTTTgggggggTTTTTTTTTTTTTTTTTTTTTgPPPrgGPGPgPTTT",
    "TTTgggggggggggggggTTTTTTTTTTTTTTTTTTTTTgPPPPPggggPgTTT",
    "TTTgggggggggggggggTTTTTTTTTTTTTTTTTTTTTgPPPPPggggggTTT",
    "TTTgPPPggrgggPPPGgTTTTTTTTTTTTTTTTTTTTTgggggGPgggggTTT",
    "TTTgPPPPPPPPPPPPGgTTTTTTTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTgPPPPPPPPPPPPggggggggTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTgPPPPPPPPPPPPggggggggTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTgPggPggPggPggPgggPGPgTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTTTTTTTTTTTTTTTTgPgPGgTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTTTTTTTTTTTTTTTTgPPGPgTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTgggggggggggggggTTTTTTTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTgggggggggggggggTTTTTTTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTgggggggggggggggTTTTTTTTTTTTTTTTTTTTTgggggTTTggggTTT",
    "TTTgggggggggggggggTTTTTTTTTTTTTTTTTTTTTgggggTTTggPgTTT",
    "TTTggggggggggggggggggggggggggggggTTTTTTggggggggGPGPTTT",
    "TTTTTTTTTTTTggggggggggggggggrGgggTTTTTTggggggggPGPgTTT",
    "TTTTTTTTTTTTgggggggggggggggggggggTTTTTTgggggggPGPPPTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggggggTTTTTTggggggTTTTTTTTT",
    "TTTTTTTTTTTTgggggTTTTTTTTTgggPGggTTTTTTggggggTTTTTTTTT",
    "TTTgggggggggggggggggggggggggTTTgggggggggggggGggggggTTT",
    "TTTgggggggggggggggggggggggggTTTgggggggggggggGggggggTTT",
    "TTTgggggggggggggggggggggggggTTTGgggggggggggggggggggTTT",
    "TTTggggggggggggGggggggggggGggggggggggggggggggggggggTTT",
    "TTTggggggggggggPPPPPPPPPPPPggggggggggggrgggggggggggTTT",
    "TTTggggggggggggPPPPPPPPPPPPgGGGrgggggggGGggggggggggTTT",
    "TTTgggggggggGPGPPPPPPPPPPPPgPPPGggPGGPgGPgGggggggggTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTPPPPPGTTTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTBBBBPPPBBBBTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTBBBBPPPBBBBTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTBBBBPPPBBBBTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTBBBBPPPBBBBTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTBBBBPPPBBBBTTTTTTTTTTTTTTTTTTT",
    "TTTTTTTTTTTTTTTTTTTTTTTTBBBBPPPBBBBTTTTTTTTTTTTTTTTTTT",
]

MTCRESCENT_ROWS = [
    "hhhhhhhhhhhhhhhrrrhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhhhhhhhhhhhhhhrrhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
    "hhPPPPPPPPPhhrhrhhhhPPPPPPPPPPPPPPPPPPPPPPPPPPhh",
    "hhPPPPPPPPPPhrhhhhhPPPPPPPPPPPPPPPPPPPPPPPPPPPhh",
    "hhPPPPPPPPPPPrhhhhPPPPPPPPPPPPPPPPPPPPPPPPPPPPhh",
    "hhPPPPPPPPPPPrrrrhPPPPPPPPPPPPPPPPPPPPPPPPPPPPhh",
    "PPPPPPPPPPPPPrrhhPPPPPPPPPPPPPPPPPPPPPPPPPPPPPhh",
    "hhPPPPPPPPPPPhrrhPPPPPPPPPPPPPPPPPPPPPPPPhPPPPhh",
    "hhPPPPPPPPPPPhrrPPPPPPPPPPPPPPPPPPPPPPPPhhhhPPhh",
    "hhPPPPPPPPPPPhrrPPPPPPPPPPPPPPPPPPPPPPPPPhhPPPhh",
    "hhPPPPPPPPPPPhrrPPPPhhhhhhhhhhhhhhhPPPPPPPPPPPhh",
    "PPPPPPPPPPPPPhrrPPPPrrrrrrrrrrrrrrrPPPPPPPPPPPhh",
    "PPPPPPPPggPPPhrrPPPPhhhhhhhhhhhhhhhPPPPPPPPPPPhh",
    "PPPPPPPPggPPPhrrPPPPhhhhhPPPPPhhhhPPPPPPPPPPPPhh",
    "hhPPPPPPPPPPPhrrPPPPrrrhPPPPPPPPPPPPPPPhhhPPPPPP",
    "hhPPPPPPPPPPPhrrPPPPrrrhPPPPPPPPPPPPPPPrrrPPPPPP",
    "hhPPPPPPPPPPPhhhPPPPrrrPPPPPPPPPPPPPPPPrrrPPPPPP",
    "hrPPPPPPPPPPPPPPPPPPrrrPPPPhhhPPPPPPPPPrrrPPPPrh",
    "hrPPPPPPPPPPPPPPPPPPhhhPPPPrrrPPPPPPPPPrrrPPPPrh",
    "hrhhhhhhhhhPPPPPPPPPhhhPPPPrrrPPPPPPPPPhhhPPPPrh",
    "hrrrrrrrrrrPPPPPPPPPrrrPSPPrrrPPPPPPPPPhhhPPPPrh",
    "hrhhhhhhhrrPPPPPPPPPrrrPPPPrrrPPPPPPPPPrrrPPPPrh",
    "hrPPPPhhrrrhhhhhhhhhrrrPPPPhhhPPPPPPPPPrrrPPPPrh",
    "hrPPPPPhrrrrrrrrrrrrrrrPPPPhhhPPPPPPPPPrrrPPPPrh",
    "hrPPPPPPrrrhhhhhhhhhhhhPPPPrrrPPPPPPPPPrrrPPPPrh",
    "hrPPPPPPrrrPPPPPPPPPPPPPPPPrrrPPPPPPPPPhhhPPPPrh",
    "hrPPPPPPrrrPPPPPPPPrPPPPPPPrrrPPPPPPPPPhhhPPPPrh",
    "hrPPPPPPhhhPPPPPPPPPPPPPPPPrrrPPPPPPPPPrrrPPPPrh",
    "hrPPPPPPPPPPPPPPPPPPPPPPPPPhhhPPPPPPPPPrrrPPPPrh",
    "hrPPPPPPPPPPPPPPPPPPhhhhhhhhhhPPPhhhPPPrrrPPPPhh",
    "hhPPPPPPPPPPPPPPPPPPrrrrrrrrrrPPPrrrggPrrrPPPPhh",
    "hhPPPPPPPPPPPPhhPPPPrrrrhhhhhhPPPrrrggPhhhPPPPhh",
    "hhPPPPPPPPPPPhhhhPPPrrrrhPPPPPPPPrrrPPPPPPPPPPhh",
    "hhPPPPPPPPPPPrrrrPPPrrrrhhPPPPPPPrrrPPPPPPPPPPhh",
    "hhPPPPPPPPPPPrrrrPPPrrrrhhPPPPPPPhhhPPPPPPPPPPhh",
    "hhPPPPPPPPPPPrrrrPPPrrrrhPPPPPPPPPPPPPPPPPPPPPhh",
    "hhPPPPPPPPPPPrrrrPPPrrrrPPPPPPPPPPPPPPPPPPPPPPhh",
    "hhPPPPPPPPPPPhhhhPPPhhhhPPPPPPPPPPPPPPPPPPPPPPhh",
    "hrhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhrh",
    "rrrhrrhrhhhrhhhhrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
]

HOLLOWGATE_ROWS = [
    "PPhhhhhhhrrrrrrrrrrrrrrPPPPPPPPPPPPPPPPPPhhhhhhP",
    "PPrPPPhhrrrrrrrhhhhhhhPPPPPPPPPPPPPPPPPPPrhhPPrP",
    "PPPPPPPhrrrrrrrrPPPPPrPPPPPPPPPPPPPPPPPPPrPPPPPP",
    "PPrPPPPPrrrrrrrrPPPPPhhhhhhPhhhhhhhhhhhhPrPPPPrP",
    "PPhPPPPPrrrrrrrrPPPPPPPPPPPPPPPPPPPPPPPhPrPPPPrP",
    "hhhPPPPPhhhhhhhhPPPPPPPPPPPPPPPPPPPPPPPhPrPPPPrP",
    "hPPPPPPPPPPPhhhhPPPPPPPPPPPPPPPPPPPPPPPhrrPPPPrP",
    "hPPPPPPPPPPPhrrrPPPPPPPPPPPPPPPPPPPPPPPhrrPPPPrP",
    "hPPPPPPPPPPPhrrrPPPPPPPPPPPPPPggPPPPPPPhhhPPPPrP",
    "hPPPPPPPPPPPhrrrhhhhhhhhPPPPhhhhhhhhhhhhhhPPPPrP",
    "hPPPPPhhhPPPhrrrrrrrrrrrPPPPrrrrrrrrrrrrrrPPPPrP",
    "hPPPPPrrrPPPPrrhhhhhhhhhPPPPhhhhhhhhhhhhhhPPPPrP",
    "rPPPPPrrrPPPPrrrhhPPPhhhPPPPPPPPPPPPPPPPPPPPPPrP",
    "rPPPPPrrrhPPPrrrPPPPPrrrPPPPPPPPPPPPPPPPPPPPPPrP",
    "rPPPPhrrrPPPPrrrPPPPPrrrhhPPPPPPPPPPPPPPPPPPPhrP",
    "rPPPPPrrrhPPPhhhPPPPPhhhhhPhPPPPPPPPPPPPPPhhhhrP",
    "hPPPPhrrrPPPPPPPPPPPPhhhhhhhhhhhhhhhhhhhhhhhhhrP",
    "hPPPPPrrrPPPPPPPPPPPPrrrrrrrrrrrrrrrrrrrrrrrrrrP",
    "PPPPPPrrrPPPPPPPPPPPPhhhhhhhhhhhhhhhhhhhhhhhhhrP",
    "PPPPPhrrrPPPPPPPPPPPPPPPShhhhhPPPhPPhhhhhPPPhhrP",
    "PPPPPPhhhPPPPPPPPPPPggPPPrrrhPPPPPPPhrrhPPPPPPPP",
    "hPPPPPPPPPPPPPPPPPPPggPPPrrrPPPPPPPPhrrPPPPPPPPP",
    "hPPPPPPPPPPPPPPPPPPPPPPPPrrrPPPPPPPPhrrPPPPPPPPP",
    "hPPPPPPPPPPPPPPPPPPPPPPPhrrrPPPPPPPPhrrPPPPPPPrP",
    "hPPPPPPPPPPPPPPPPPPhhhhhhhhhPPPPPPPPhrrPPPPPPPrP",
    "rhhPhhhhhhhhhhhhhhhhhhhhhhhhPPPPPPPPhrrPPPPPPPrP",
    "rrrPrrrrrrrrrrrrrrrrrrrrrrrrPPPPPPPPhrrPPPPPPPrP",
    "hhhPhhhhhhhhhhhhhhhhhhhhhhhhPPPPPPPPhrrPPPPPPhrP",
    "hPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPhrrPPPPPPPrP",
    "hPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPhrrPPPPPPPrP",
    "hPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPhrrPPPPPPPrP",
    "hPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPhhhPPPPPhPrP",
    "rhhhhhhhhhhhPPPPPPPPPPPhhhhhhhhPPPPPPPPPPPPhhhrP",
    "rrrrrrrrrrrrPPrPPPPPPPPrrrrrrrrPPPPPPPPPPPPhhPrP",
    "rrrrrrrrrrrrPPPPPPPhPPPrrrrrrrrPhPPPPPPPPPPPPPrP",
    "rrrrrrrrrrrrPPPPPPPPPPPrrrrrrrrPhhhPPPPPPPPPPPrP",
    "rrrrrrrrrrrrPhPPPPPPhPPrrrrrrrrhhhhhhhhhhhhhhhhP",
    "rrrrrrrrrrrrPPPhPPPPPhPrrrrrrrrrrrrrrrrrrrrrrrrP",
    "rhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhrrrrrrrrrrrrrrrrP",
    "hhhhhhhhhhhhhhrrrrrrrrhhhhhhhhhhrrrrrrrrrrrrrrrr",
]

ASCENT_ROWS = [
    "hhPPPhhrrrrrrhhhhhhhrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhPPPhhhrrrhhhPhhPPhhhhrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhPPPPhhhrrrhhPhhhPPhhrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhhPPPhhhhhhPPPPPPPPPhhhrrrrrrrrrrrrrrrrrrrrrrrr",
    "hhhhPPPhhhhhhhPPhPPPPPhrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrhPPPhPPPPPPPPPPPPPhPPrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrhPPPrPPPPPPPPPPPPPrPPrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrhPPPrPPPPPPPPPPPPPrPPrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhhhPPrPPPPPPPPPPPPPrPPrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrhPPhhhhPhhhPPhhPhhPPrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrhhPPPPPggPrPPrhPPSPPrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrhPPhPPPghPrPPrhhPPPhrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrhPhrPPPPrhrPPrhhhhhhrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrrhPPrPPPPrhrPPrhhhhhhrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhhhPPrPPPPPPPPPrhPPPhhhrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrhPPPrPPPPPPPPPrPPPPhrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "hhPPPhhPhhhhhhhhhPhPPhrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhPPhhPPhhhPPPPPPPPPhhrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhhPPPPPhhPPPhhPPPPPhhhrrrrrrrrrrrrrrrrrrrrrrrrr",
    "hhhhPPPPPPPPPhhPPhhhhhrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rrhhhhhhPPPPPhhhhhhrrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
    "rhhhhhhhhhPPPhhhhhhhrrrrrrrrrrrrrrrrrrrrrrrrrrrr",
]

SEAGLASS_ROWS = [
    "hhhhhhhhhhPhhhhhhPPPPPhhhhhhhhPPhhhhhh",
    "hhhhhhhhhhPhhhhhhhPPPPhhhhhhhhPPhhhhhh",
    "hhhhhhhhhhPhhhhhhhPPSPhhhhhhhhPPhhhhhh",
    "hhhhPPrPPPPPPPPPPPPPPPPrPPPPPhPPPPPhhh",
    "hhhhPPPPPPPPPPPPPPPPPPPPPPPhrhPPPPPhhh",
    "hhhhPPPPPPPPPPPPPPPPPPPPPPPhPhPPPPPhhh",
    "hhhhPPggPPPPPPPPPPPPrPPPPPPPPhPPPPPhhh",
    "hhhhPhggPPPPPPhhhhPPhPhhhPPhhhPPPPPhhh",
    "hhhhPhPPPPPPPPhPPPPPPPPPhPPPhPPPPPPhhh",
    "GhhhPPPPPPPPPPhPPPPPPPPPhhPPPPPPPPPhhh",
    "PhhhrPPPPPPPPrhPPPPPPPPPhhPPPPPPPPPhhh",
    "PPPhrPPPPPPPPPhPPPPPPPPPhhPPPPPPPPPhhh",
    "PPPPPPPPPPPPPPhPPPPPPPPPhhPPPPPPPPPhhh",
    "PPPhPPPPPPPrPPhPPPPPPPPPhhPPPPPPPPPhhh",
    "hhhhhhhhPPhhhhhPPPPPPPPPhhhPhhhhhhhhhh",
    "hhhPPPPPPPPPPPPPPPPPPPPPhhPPPPPPPPPhhh",
    "hGPPPPPPPPPPPPPPPPPPPPPPhhPPggPPPPPPPh",
    "hhhPPPPPPPPPPPPPPPPPPPPPhhPPggPPPPPhhh",
    "hhhPPPPPPPPPPPPPPPPPPPPPhhPPPPPPPPPhhh",
    "hhhPPPPPPPPPPPPPPPPPPPPPhhPPPPPPPPPhhh",
    "hhGhhPPPhhPhhPhhhhhhPhhPhhhhhhhPPPhhhh",
    "PPPPPPPPhhPhhPhhhhhhGhhPhhhhhhhPPPhhhh",
    "hhhGhhhhhhPhhhhhhhhhhhhPGhhhhhhhhPPPhh",
    "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
]


ROUTES = [
    # FireRed's Route 2, metatile for metatile (decoded from the pokefirered decomp): the long forest road
    # from Epidimy up to Mossmere Wood, with Diglett's-Cave-style hill, both forest gates, the mid-route
    # checkpoint building the road passes through, and the one-way ledge shortcuts down its east side.
    Route("route2", "Route 2", 24, 54, "grass", 21, {"s": 10, "n": 18},
          rows=ROUTE2_ROWS, start=(10, 52), sign_tiles=[(7, 47), (15, 22)],
          buildings=[towns._landmark("route2", "route2-checkpoint", "Route 2 Checkpoint", "Checkpoint", "gatehouse",
                                     20, 15, [
                         towns._npc("route2-guard-alder", 6, 6, "#7f9ec9", "#3f4a5a", "Guard Alder", [
                             "Guard Alder: The checkpoint - half way between Epidimy and the wood.",
                             "Guard Alder: The road walks straight through. Mind the ledges on the way down."])]),
                     towns._landmark("route2", "route2-gate-s", "Woodland Gate", "Gate", "gatehouse", 7, 23, [
                         towns._npc("route2-guard-birch", 6, 6, "#7f9ec9", "#3f4a5a", "Guard Birch", [
                             "Guard Birch: The southern gate - Mossmere Wood is through here, researcher.",
                             "Guard Birch: Wild Scimons wait in the long grass either side of the road."])])],
          signs=[["Signpost: Route 2.", "North: Mossmere Wood - the old forest.", "South: Epidimy Town."],
                 ["Trainer Tips.", "Wild Scimons hide in the tall grass.", "Walk softly, and keep a",
                  "hardy partner up front."]]),
    Route("route2n", "Route 2 North", 24, 26, "forest", 22, {"n": 10, "s": 17},
          rows=ROUTE2N_ROWS, start=(10, 2), sign_tiles=[(14, 12)], traveler_tiles=[(9, 7)],
          buildings=[_gate_hut("route2n", "Forest Gate", 4, 11, [
              "Guard Rowan: South gate of the old growth - Stonreach's quarry dust starts past the ridge.",
              "Guard Rowan: Mind the ledges on the Stonreach side."]),
                     towns._landmark("route2n", "route2-house", "Route 2 House", "House", "gatehouse", 15, 20, [
                         towns._npc("route2-warden", 6, 6, "#a98150", "#5a4630", "Warden Fir", [
                             "Warden Fir: This house watches the treeline - mine, now.",
                             "Warden Fir: Rest up, {name}. The wood is long and the road is quiet."])])],
          signs=[_sign("Route 2 North", ["North: Stonreach Town - the quarry city.", "South: through Mossmere Wood."])],
          travelers=[
              _hiker("route2n-hiker-moss", ["Moss: I counted four hundred trees today. Then lost count."])]),
    Route("route3", "Route 3", 93, 40, "mountain", 23, {"n": 79, "w": 30},
          rows=ROUTE3_ROWS, start=(79, 2), sign_tiles=[(72, 31), (78, 7)], traveler_tiles=[(11, 24), (30, 25)],
          signs=[_sign("Route 3", ["East: Mt. Crescent - the crescent cave glows at night.",
                                   "West: Stonreach Town."]),
                 _sign("Route 3", ["East: the crater road. Mind the ledges - they only go down."])],
          travelers=[
              _hiker("route3-hiker-scree", ["Scree: Loose stones everywhere - watch your step, {name}.",
                                            "Scree: The crystals up ahead hum when Scimons are near."],
                     battle=("pebblon", 8)),
              _ranger("route3-ranger-quarry", ["Quarry: The road east climbs toward the crater."])]),
    Route("route4", "Route 4", 75, 20, "grass", 24, {"w": 4, "e": 11},
          rows=ROUTE4_ROWS, start=(4, 7), sign_tiles=[(1, 7)], traveler_tiles=[(20, 10)],
          signs=[_sign("Route 4", ["East: Tidebrook Town - the bridge city.", "West: Mt. Crescent.",
                                   "They say supplies get stashed off the road here. Nobody knows who by."])],
          travelers=[
              _ranger("route4-ranger-meadow", ["Meadow: A fine stretch of grass, this.",
                                               "Meadow: Ideal training weather, {name}."])]),
    Route("route5", "Route 5", 48, 40, "grass", 25, {"n": 16, "s": 24},
          rows=ROUTE5_ROWS, start=(16, 2), sign_tiles=[(32, 32)], traveler_tiles=[(30, 10)],
          buildings=[_gate_hut("route5", "Aurum Gate", 21, 34, [
              "Guard Aurel: The Aurum City gate - the grid roads hum day and night.",
              "Guard Aurel: City rules: no battling in the plaza. The roads, though - go wild."]),
              _daycare("route5", 21, 20)],
          signs=[_sign("Route 5", ["South: Aurum City - the golden crossroads.", "North: Tidebrook Town.",
                                   "The Day-Care is north - they raise Scimons like their own."])],
          travelers=[
              _cast("route5-trader-quill", ["Quill: A trader never turns down a battle!",
                                               "Quill: Win and I'll consider the road toll waived. I'm not that kind of trader, but still."],
                       ("sparkit", 9), look=_look(7, 1, 2, 1),
                       post=["Quill: A pleasure, {name}. The road's yours."], facing="left")]),
    Route("route6", "Route 6", 24, 40, "grass", 26, {"n": 13, "s": 10},
          rows=ROUTE6_ROWS, start=(13, 2), sign_tiles=[(21, 15)], traveler_tiles=[(12, 27)],
          buildings=[_gate_hut("route6", "Aurum Gate", 9, 0, [
              "Guard Ledger: North gate to Aurum - the city of the golden crossroads.",
              "Guard Ledger: The wagons run all night. Walk the road, not the grass, after dark."])],
          signs=[_sign("Route 6", ["South: Emberport City - the harbour.", "North: Aurum City."])],
          travelers=[
              _ranger("route6-ranger-south", ["South: Freight wagons all day on this road. Watch your toes."])]),
    Route("route7", "Route 7", 24, 20, "grass", 27, {"e": 10, "w": 4},
          rows=ROUTE7_ROWS, start=(22, 9), sign_tiles=[(10, 2)], traveler_tiles=[(10, 10), (14, 13)],
          signs=[_sign("Route 7", ["West: Verdance City - everything here is grown, never built.",
                                   "East: Aurum City."])],
          travelers=[
              _hiker("route7-hiker-hedge", ["Hedge: I race the wagons to the city. The wagons usually win."],
                     battle=("dewbit", 9)),
              _ranger("route7-ranger-bloom", ["Bloom: The hedges along this road were planted by Verdance's gardeners."])]),
    Route("route8", "Route 8", 72, 20, "grass", 28, {"w": 9, "e": 10},
          rows=ROUTE8_ROWS, start=(2, 10), sign_tiles=[(16, 5)], traveler_tiles=[(35, 10)],
          signs=[_sign("Route 8", ["East: Dusklight Town - the town under the western rim.",
                                   "West: Aurum City."])],
          travelers=[
              _ranger("route8-ranger-dusk", ["Dusk: The light changes near Dusklight. You'll see.",
                                             "Dusk: The town closes at dusk. Or opens. It's hard to say."])]),
    Route("route9", "Route 9", 72, 20, "grass", 29, {"w": 2, "e": 9},
          rows=ROUTE9_ROWS, start=(3, 9), sign_tiles=[(29, 7)], traveler_tiles=[(25, 9), (45, 13)],
          signs=[_sign("Route 9", ["East: Hollowgate Tunnel - bring a lamp.", "West: Tidebrook Town."])],
          travelers=[
              _hiker("route9-hiker-lamp", ["Lamp: The tunnel's perfectly safe. Probably. Bring a lamp anyway."],
                     battle=("cindermite", 9)),
              _ranger("route9-ranger-creek", ["Creek: The creek here feeds Tidebrook's river."])]),
    Route("route10", "Route 10", 24, 80, "mountain", 30, {"w": 9, "s": 9},
          rows=ROUTE10_ROWS, start=(9, 4), sign_tiles=[(7, 21), (2, 39), (6, 42), (15, 59)], traveler_tiles=[(10, 29)],
          buildings=[towns._center("route10", 9, 58)],
          signs=[_sign("Route 10", ["South-east: Dusklight Town.", "West: Hollowgate Tunnel.",
                                    "Cush's nook stands mid-route - free repairs, hot soup smell."]),
                 _sign("Route 10", ["Hollowgate Tunnel - north entrance.", "Lanterns provided. Courage isn't."]),
                 _sign("Trainer Tips", ["Wild Scimons in the tunnel grass hum before they pounce.",
                                        "Walk softly and keep a hardy partner up front."]),
                 _sign("Route 10", ["South: Dusklight Town - the town under the western rim."])],
          travelers=[
              _hiker("route10-hiker-scarp", ["Scarp: The scarp settles at night. That rumble is normal.",
                                             "Scarp: Dusklight's just over the ridge, {name}."])]),
    Route("route11", "Route 11", 72, 20, "grass", 31, {"w": 8},
          rows=ROUTE11_ROWS, start=(3, 9), sign_tiles=[(20, 6)], traveler_tiles=[(30, 10)],
          buildings=[_gate_hut("route11", "Emberport Gate", 4, 5, [
              "Guard Keel: The Emberport gate - east road ends at a bench and a view.",
              "Guard Keel: I stamp maps for tourists. Yours says 'dead end' twice."])],
          signs=[_sign("Route 11", ["West: Emberport City.", "The road ends here. The bench is nice, though."])],
          travelers=[
              _ranger("route11-ranger-bench", ["Bench: Officially I patrol this road.",
                                               "Bench: Unofficially I sit on the bench and watch the sea."])]),
    Route("route12", "Route 12", 24, 120, "grass", 32, {"n": 12, "s": 14},
          rows=ROUTE12_ROWS, start=(12, 2), sign_tiles=[(15, 69), (17, 13)], traveler_tiles=[(12, 92)],
          buildings=[_gate_hut("route12", "Dusklight Gate", 12, 15, [
              "Guard Wick: The coast road starts here - Dusklight's monuments watch you leave.",
              "Guard Wick: Wild Scimons nest along the cliffs. Rare ones. Quiet ones."])],
          signs=[_sign("Route 12", ["South: the coast road continues.", "North: Dusklight Town."]),
                 _sign("Route 12", ["The boardwalk south - every plank counted, every wave heard."])],
          travelers=[
              _ranger("route12-ranger-coast", ["Coast: You can smell the sea from here, {name}.",
                                               "Coast: The road south winds along the cliffs. Take your time."])]),
    Route("route13", "Route 13", 72, 20, "grass", 33, {"n": 63, "w": 7},
          rows=ROUTE13_ROWS, start=(62, 2), sign_tiles=[(41, 12)], traveler_tiles=[(40, 11)],
          signs=[_sign("Route 13", ["South: the cliff road bends east ahead.", "North: Dusklight's coast."])],
          travelers=[
              _ranger("route13-ranger-tern", ["Tern: The seabirds nest on the cliff edge. Do not join them."])]),
    Route("route14", "Route 14", 24, 60, "grass", 34, {"e": 7, "w": 53},
          rows=ROUTE14_ROWS, start=(22, 6), sign_tiles=[(17, 12)], traveler_tiles=[(10, 30)],
          signs=[_sign("Route 14", ["East: the road swings back toward Vespera.", "West: the cliff road."])],
          travelers=[
              _hiker("route14-hiker-cliff", ["Cliff: Best sea views in the region, right here.",
                                             "Cliff: Vespera's hedges are two days east."], battle=("sporelet", 10))]),
    Route("route15", "Route 15", 72, 20, "grass", 35, {"w": 11, "e": 14},
          rows=ROUTE15_ROWS, start=(13, 11), sign_tiles=[(41, 11)], traveler_tiles=[(40, 10)],
          buildings=[_gate_hut("route15", "Vespera Gate", 9, 7, [
              "Guard Hedge: The Vespera gate - town of hedges, arches and one closed safari.",
              "Guard Hedge: Whatever the hedges tell you, don't follow them. They lie for fun."])],
          signs=[_sign("Route 15", ["East: Vespera City - mind the hedges.", "West: the coast road."])],
          travelers=[
              _ranger("route15-ranger-gate", ["Gate: Almost there, {name}. Vespera's arches are just past the rise."])]),
    Route("route16", "Route 16", 48, 20, "grass", 36, {"e": 13, "s": 3},
          rows=ROUTE16_ROWS, start=(45, 12), sign_tiles=[(33, 11), (6, 17)], traveler_tiles=[(14, 12)],
          buildings=[_gate_hut("route16", "Verdance Gate", 39, 9, [
              "Guard Petal: The Verdance gate - the Grand Mart's glass roof shines at dusk.",
              "Guard Petal: South is the long hedge road. It's one-way fun, downhill all the way."])],
          signs=[_sign("Route 16", ["East: Verdance City.", "South: the hedge roads wind south toward Vespera."]),
                 _sign("Route 16", ["Southbound traffic only past this point. The hedges insist."])],
          travelers=[
              _cast("route16-rider-vroom", ["Vroom: The hedge roads are my race track!",
                                            "Vroom: Watch the corners, {name} - and your Scimon's Stability."],
                    ("pebblon", 10), look=_look(8, 1, 4, 0),
                    post=["Vroom: Nice pace! See you on the road."], facing="up")]),
    Route("route17", "Route 17", 24, 160, "grass", 37, {"n": 2, "s": 9},
          rows=ROUTE17_ROWS, start=(2, 2), sign_tiles=[(12, 97), (11, 157)], traveler_tiles=[(10, 122)],
          signs=[_sign("Route 17", ["South: the long road south - all downhill, no climbing back.",
                                    "North: Verdance's west gate."]),
                 _sign("Route 17 - the hedge road", ["All downhill. All the time. Enjoy the ride, {name}."])],
          travelers=[
              _ranger("route17-ranger-verge", ["Verge: The hedgerows hum in spring. Nobody knows why.",
                                               "Verge: Verdance's gardeners claim it's on purpose."])]),
    Route("route18", "Route 18", 60, 20, "grass", 38, {"n": 9, "e": 9},
          rows=ROUTE18_ROWS, start=(9, 2), sign_tiles=[(37, 7), (52, 7)], traveler_tiles=[(40, 10)],
          signs=[_sign("Route 18", ["East: Vespera City.", "North: the long road from Verdance."]),
                 _sign("Route 18", ["East: Vespera's arches. West: the hill you just descended."])],
          travelers=[
              _hiker("route18-hiker-bramble", ["Bramble: The hedges here lean in when you pass.",
                                               "Bramble: Vespera folk say they're friendly. I say they're nosey."])]),
    Route("route19", "Route 19", 24, 60, "sea", 39, {"n": 11, "s": 11},
          rows=ROUTE19_ROWS, start=(11, 2), sign_tiles=[(13, 12)], traveler_tiles=[(11, 10)],
          signs=[_sign("Route 19", ["South: the sea crossing to Seaglass Isles.", "North: Vespera City.",
                                    "Stay on the boards - the tide under them is real."])],
          travelers=[
              _sailor("route19-sailor-tide", ["Tide: The boards creak but they hold. Mostly.",
                                              "Tide: Seaglass Isles sparkle at noon. Worth the walk, {name}."])]),
    Route("route20", "Route 20", 120, 20, "sea", 40, {"w": 9, "e": 9},
          rows=ROUTE20_ROWS, start=(3, 9), sign_tiles=[(64, 8), (68, 14)], traveler_tiles=[(30, 9)],
          signs=[_sign("Route 20", ["East: Seaglass Isles.", "West: Cinderfall Island - the piers are warm."]),
                 _sign("Route 20", ["The Seafoam crossing - the caves mark the middle of the channel."])],
          travelers=[
              _sailor("route20-sailor-swell", ["Swell: Two islands, one road, zero boats.",
                                               "Swell: The walking's honest though, {name}."])]),
    Route("route21", "Route 21", 24, 100, "sea", 41, {"n": 6, "s": 12},
          rows=ROUTE21_ROWS, start=(6, 2), sign_tiles=[(13, 1)], traveler_tiles=[(12, 40)],
          signs=[_sign("Route 21", ["South: Cinderfall Island.", "North: Riven Town - home of the Astrion Lab.",
                                    "The mainland crossing. Mind the tide tables."])],
          travelers=[
              _sailor("route21-sailor-current", ["Current: The current runs north to Riven's pier.",
                                                 "Current: I used to ferry folks. Now I cheer them on."])]),
    Route("route22", "Route 22", 48, 24, "grass", 42, {"n": 8, "e": 7},
          rows=ROUTE22_ROWS, start=(44, 7), sign_tiles=[(7, 12)], traveler_tiles=[(34, 10)],
          buildings=[_gate_hut("route22", "League Gate", 6, 2, [
              "Gate Warden Stamp: The League road starts here. The gate checks legs, not stamps - yet.",
              "Gate Warden Stamp: Route 23 climbs to the Ascent. The Plateau waits above."])],
          signs=[_sign("Route 22", ["East: Epidimy Town.", "West: Route 23 - the League road begins."])],
          travelers=[
              _ranger("route22-ranger-pilgrim", ["Pilgrim: Everyone who walks west is heading for the Plateau.",
                                                 "Pilgrim: The League road asks one thing: keep walking, {name}."])]),
    Route("route23", "Route 23", 24, 160, "mountain", 43, {"s": 9, "n": 11},
          rows=ROUTE23_ROWS, start=(9, 157), sign_tiles=[(2, 16)], traveler_tiles=[(9, 80)],
          encounters=False,
          buildings=[_gate_hut("route23", "League Checkpoint", 11, 147, [
              "Checkpoint Clerk Seal: The checkpoint records every challenger by name.",
              "Checkpoint Clerk Seal: One day the gate will ask for stamps. The case in your Pack is ready."])],
          signs=[_sign("Route 23", ["North: the Ascent Road - the final climb.",
                                    "South: Route 22 - the League gate road.", "The gate checks stamps. The road checks legs."])],
          travelers=[
              _hiker("route23-hiker-summit", ["Summit: I've walked this road nine times.",
                                              "Summit: The tenth time's for the stamp case, {name}."])]),
    Route("route24", "Route 24", 24, 40, "grass", 44, {"s": 14, "e": 4},
          rows=ROUTE24_ROWS, start=(13, 37), sign_tiles=[(10, 25)], traveler_tiles=[(10, 10), (14, 20)],
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
    Route("route25", "Route 25", 72, 20, "grass", 45, {"w": 4, "e": 5},
          rows=ROUTE25_ROWS, start=(4, 7), sign_tiles=[(30, 8)], traveler_tiles=[(26, 8)],
          signs=[_sign("Route 25", ["East: Ost's Cabin - the road ends at the windmill.",
                                    "West: Route 24 - back to Tidebrook."])],
          travelers=[
              _ranger("route25-ranger-meander", ["Meander: This road doesn't go anywhere. That's the point.",
                                                 "Meander: Ost's windmill is the best dead end in the region."])]),
]

# --------------------------------------------------------------------------- the wild places
PLACES = [
    Route("mossmere", "Mossmere Wood", 54, 69, "forest", 51, {"s": 29, "n": 5},
          rows=MOSSMERE_ROWS, start=(29, 66), sign_tiles=[(6, 12)], traveler_tiles=[(20, 31)],
          signs=[_sign("Mossmere Wood", ["North: the wood thins toward Stonreach.", "South: Route 2.",
                                         "The old growth. The trees were here first; act accordingly."])],
          travelers=[
              _ranger("mossmere-warden-fern", ["Warden Fern: The wood hums at dusk. Old magic or old machines.",
                                               "Warden Fern: Keep to the path, {name} - the moss swallows boots."])]),
    Route("mt_crescent", "Mt. Crescent", 48, 40, "mountain", 52, {"w": 12, "e": 15},
          rows=MTCRESCENT_ROWS, start=(2, 12), sign_tiles=[(24, 20)], traveler_tiles=[(10, 10)],
          signs=[_sign("Mt. Crescent", ["East: Route 4 - down to Tidebrook.", "West: Route 3 - down to Stonreach.",
                                        "The crater glows faintly on clear nights."])],
          travelers=[
              _hiker("mt_crescent-surveyor", ["Surveyor Sliver: The crater's rock isn't in any catalogue.",
                                              "Surveyor Sliver: The crystals resonate. My instruments hate it."],
                     battle=("nanolyte", 11))]),
    Route("hollowgate", "Hollowgate Tunnel", 48, 40, "tunnel", 53, {"w": 19, "e": 21},
          rows=HOLLOWGATE_ROWS, start=(2, 19), sign_tiles=[(24, 19)], traveler_tiles=[(30, 19)],
          signs=[_sign("Hollowgate Tunnel", ["East: Route 10 - down to Dusklight.", "West: Route 9 - back to Tidebrook.",
                                             "The lanterns are maintained by both towns. Usually."])],
          travelers=[
              _hiker("hollowgate-keeper-wick", ["Keeper Wick: Mind the beams, mind the dark, mind your step.",
                                                "Keeper Wick: Halfway is the loneliest part. Walk on, {name}."])]),
    Route("ascent", "Ascent Road", 48, 22, "mountain", 54, {"s": 11, "n": 3},
          rows=ASCENT_ROWS, start=(11, 20), sign_tiles=[(20, 10)], traveler_tiles=[(10, 11)],
          signs=[_sign("Ascent Road", ["North: Astrion Plateau - the League's home.", "South: Route 23.",
                                       "The last road. Every trainer walks it twice: once up, once down."])],
          travelers=[
              _npc("ascent-guide", 0, 0, "#c9c4d6", "#6a6f7a", "Ascent Guide Stele", [
                  "Stele: The Plateau is past the rim, {name}.",
                  "Stele: Whatever happens up there, the road remembers you."], look=LEAGUE_LOOK)]),
    Route("seaglass", "Seaglass Isles", 38, 24, "island", 55, {"n": 19, "w": 12},
          rows=SEAGLASS_ROWS, start=(18, 2), sign_tiles=[(20, 2)], traveler_tiles=[(10, 12)],
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
    (("route3", "n"), ("mt_crescent", "w")),
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
    (("route13", "w"), ("route14", "e")),
    (("route14", "w"), ("route15", "e")),
    (("route15", "w"), ("vespera", "n")),
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
    (("route22", "n"), ("route23", "s")),
    (("route23", "n"), ("ascent", "s")),
    (("ascent", "n"), ("astrion_plateau", "s")),
    (("tidebrook", "n"), ("route24", "s")),
    (("route24", "e"), ("route25", "w")),
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
