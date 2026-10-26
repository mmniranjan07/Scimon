"""Tilemaps: collision, pre-rendered world surfaces, animated overlays and the follow camera.

* Collision is grid based: a tile is solid or not, and a step is only allowed when the destination tile's
  bounding Rect is free of solid tiles and NPC rects (pygame.Rect.collidelist).
* The static world (terrain, trees, buildings, painted rooms) is drawn once into one big Surface at load;
  per frame we only blit the camera's window and draw a few animated overlays (path glow, signs, ponds).
* Terrain art is a port of V34's canvas drawing on a 16-unit grid, scaled by PX (3) to the 48 px tile."""
import math

import pygame

import assets
import interiors
import layered_room
import townview
import worldmap as wm
from routes import AREAS, CHESTS
from settings import PX, TILE, VOID, W, H, hexc


def hash2(x, y):
    n = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return n - math.floor(n)


def px(surf, color, x, y, w, h, scale=PX):
    pygame.draw.rect(surf, color, (round(x * scale), round(y * scale), max(1, round(w * scale)), max(1, round(h * scale))))


def _c(s):
    return hexc(s) if isinstance(s, str) else s


# --------------------------------------------------------------------------- camera
def cam_clamp(center, map_px, view_px):
    """Clamp the camera to the map, or centre a map smaller than the viewport (V34 camClamp)."""
    if map_px <= view_px:
        return round((map_px - view_px) / 2)
    return max(0, min(map_px - view_px, round(center)))


class Camera:
    def __init__(self, view_w=W, view_h=H):
        self.view = pygame.Vector2(view_w, view_h)
        self.x = self.y = 0

    def follow(self, world_pos, map_px_w, map_px_h):
        self.x = cam_clamp(world_pos[0] - self.view.x / 2 + TILE / 2, map_px_w, self.view.x)
        self.y = cam_clamp(world_pos[1] - self.view.y / 2 + TILE / 2, map_px_h, self.view.y)

    def apply(self, rect):
        return rect.move(-self.x, -self.y)

    def visible_tiles(self, margin=1):
        c0, r0 = int(self.x // TILE) - margin, int(self.y // TILE) - margin
        return c0, r0, int(self.view.x // TILE) + 2 + margin * 2, int(self.view.y // TILE) + 2 + margin * 2


# --------------------------------------------------------------------------- overworld terrain
def _grass_tile():
    return assets.scaled("tiles/nature/grass.png", TILE, TILE, smooth=False)


def draw_overworld_tile(surf, t, sx, sy, mx, my, rows):
    """One overworld tile at pixel (sx, sy) -- a port of V34 drawOverworldTile (static parts only)."""
    h = hash2(mx, my)
    grass_like = t not in "Whrsk"
    if grass_like:
        surf.blit(_grass_tile(), (sx, sy))
    ox = lambda v: sx + v * PX     # noqa: E731  16-unit -> pixels
    oy = lambda v: sy + v * PX     # noqa: E731

    def R(color, x, y, w, hh):
        pygame.draw.rect(surf, _c(color), (ox(x), oy(y), w * PX, hh * PX))

    if t == "s":
        R("#e8d3a0" if h > 0.5 else "#e0c890", 0, 0, 16, 16)
        if h > 0.6: R("#d4b878", 4, 6, 2, 2)
        if h < 0.25: R("#d4b878", 10, 10, 2, 2)
        if 0.4 < h < 0.6: R("#cbab6a", 2, 11, 3, 1)
    elif t == "P":
        R("#cfd6dc", 0, 0, 16, 16)
        R("#bcc5cc", 0, 0, 16, 2)
        R("#bcc5cc", 0, 14, 16, 2)
        if h > 0.6: R("#c3ccd2", 6, 8, 3, 3)
        if h < 0.2: R("#c3ccd2", 2, 3, 2, 2)
    elif t == "k":
        surf.blit(_grass_tile(), (sx, sy))
        R("#5c6a76", 6, 4, 4, 11)
        R("#8894a0", 6, 4, 1, 11)
        R("#3f4a54", 5, 13, 6, 2)
        R("#7ef2ff", 7, 2, 2, 2)
    elif t == "W":
        R("#3f86bd", 0, 0, 16, 16)
        R("#5aa0d0", 2, 3, 6, 2)
        R("#5aa0d0", 9, 9, 5, 2)
        R("#2f6f9f", 0, 14, 16, 2)
    elif t == "F":
        colors = ["#e05a72", "#e8c33a", "#e88fb0", "#f0f0f0"]
        R(colors[int(h * 4) % 4], 3, 4, 3, 3)
        R("#e8c33a", 4, 5, 1, 1)
        R(colors[int(h * 7) % 4], 9, 9, 3, 3)
    elif t == "g":
        R("#4f8f3a", 1, 5, 4, 9)
        R("#5aa042", 6, 3, 4, 11)
        R("#4f8f3a", 11, 6, 4, 8)
        R("#3f7a2e", 2, 12, 12, 3)
    elif t == "c":
        R("#5c6a76", 0, 0, 16, 16)
        R("#7a8896", 0, 2, 16, 2)
        for cx, top in ((2, 3), (7, 4), (12, 3)):
            R("#3f7a2e", cx, top, 2, 6)
            R("#5be07f", cx, top - 1, 2, 2)
    elif t == "r":
        surf.blit(_grass_tile(), (sx, sy))
        surf.blit(assets.scaled("tiles/nature/rocks.png", (16 + 4) * PX, 13 * PX), (sx - 2 * PX, sy + PX))
    elif t == "h":
        surf.blit(_grass_tile(), (sx, sy))
        R("#8fa0ac", 0, 6, 16, 10)
        R("#c7d3da", 0, 6, 16, 2)
        R("#5f6f7a", 0, 13, 16, 3)
        lit = h > 0.5
        R("#59f3ff" if lit else "#c98bff", 6, 9, 2, 2)
    # T trees are drawn in a later pass (they overhang neighbouring tiles); B/D stay plain grass.


def draw_tree(surf, sx, sy, mx, my):
    h = hash2(mx, my)

    def R(color, x, y, w, hh):
        pygame.draw.rect(surf, _c(color), (sx + x * PX, sy + y * PX, w * PX, hh * PX))

    if h < 0.16:       # bioluminescent alien flora: glowing cyan trunk, purple crown
        R("#0d2b30", 5, 2, 6, 16)
        R("#31e8ff", 6, 4, 2, 13)
        R("#8f5fe0", 6, -2, 4, 6)
        R("#b98bff", 3, 0, 4, 6)
        R("#d6b3ff", 9, 1, 4, 5)
    else:
        surf.blit(assets.scaled("tiles/nature/tree.png", (16 + 6) * PX, (16 + 6) * PX, smooth=False),
                  (sx - 3 * PX, sy - 6 * PX))


# --------------------------------------------------------------------------- procedural interiors
_FURNITURE = {
    "store": ("tiles/hitech/floor-store.png", {
        "C": ("tiles/hitech/counter.png", True, 22, None), "S": ("tiles/hitech/shelf.png", True, 26, None),
        "p": ("tiles/hitech/plant.png", False, 19, 13)}),
    "repair": ("tiles/hitech/floor-repair.png", {
        "M": ("tiles/hitech/machine.png", True, 24, None), "C": ("tiles/hitech/counter.png", True, 22, None),
        "@": ("tiles/hitech/terminal.png", False, 18, 13)}),
}


def _furniture_runs(rows, chars):
    runs = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            c = row[x]
            if c in chars:
                x2 = x + 1
                while x2 < len(row) and row[x2] == c:
                    x2 += 1
                runs.append((c, x, y, x2 - x))
                x = x2
            else:
                x += 1
    return runs


def draw_interior_tile(surf, t, sx, sy, mx, my, pal, floor_texture):
    if t == " ":
        return
    h = hash2(mx, my)

    def R(color, x, y, w, hh, a=None):
        col = _c(color)
        if a is not None:
            s = pygame.Surface((max(1, int(w * PX)), max(1, int(hh * PX))), pygame.SRCALPHA)
            s.fill(col + (a,))
            surf.blit(s, (sx + x * PX, sy + y * PX))
        else:
            pygame.draw.rect(surf, col, (sx + x * PX, sy + y * PX, w * PX, hh * PX))

    if t != "#" and not floor_texture:
        R(pal["floorA"] if (mx + my) % 2 == 0 else pal["floorB"], 0, 0, 16, 16)
        R((0, 0, 0), 0, 15, 16, 1, 15)
        R((0, 0, 0), 15, 0, 1, 16, 15)
    if t == "#":
        R(pal["wall"], 0, 0, 16, 16)
        R(pal["wallTop"], 0, 0, 16, 5)
        R((0, 0, 0), 0, 13, 16, 3, 46)
        if h > 0.6: R((255, 255, 255), 4, 8, 6, 3, 20)
    elif t == "E":
        R("#8a5a3a", 1, 3, 14, 10)
        R("#a86f48", 2, 4, 12, 8)
        R("#5a3a24", 1, 3, 14, 1)
        lbl = assets.font("display", 8).render("OUT", True, hexc("#3a2418"))
        surf.blit(lbl, lbl.get_rect(center=(sx + TILE // 2, sy + 9 * PX)))
    elif t == "C":
        R("#8a6a44", 0, 2, 16, 12); R("#a98150", 0, 2, 16, 4); R(pal["accent"], 0, 12, 16, 2); R("#5a4630", 0, 14, 16, 2)
    elif t == "S":
        R("#7a5a34", 0, 0, 16, 16); R("#5a4630", 0, 7, 16, 2); R("#5a4630", 0, 14, 16, 2)
        goods = ["#e05a72", "#5b5bd6", "#57b06f", "#e8c33a"]
        R(goods[int(h * 4) % 4], 2, 2, 4, 5); R(goods[int(h * 9) % 4], 8, 3, 4, 4)
        R(goods[int(h * 13) % 4], 3, 10, 4, 4); R(goods[int(h * 17) % 4], 9, 10, 4, 4)
    elif t == "M":
        R("#8a8f98", 0, 1, 16, 15); R("#6a6f78", 0, 1, 16, 3); R("#2a3038", 3, 6, 10, 7)
        R(pal["accent"], 4, 7, 3, 2); R("#7fd0e0" if h > 0.5 else "#57b06f", 9, 7, 3, 2)
    elif t == "K":
        R("#6a4a2c", 0, 0, 16, 16); R("#4a3420", 0, 7, 16, 2)
        spines = ["#c9584a", "#4a7fc0", "#c9a13a", "#5aa063"]
        for i in range(4):
            R(spines[(i + int(h * 4)) % 4], 2 + i * 3, 2, 2, 5)
            R(spines[(i + int(h * 7)) % 4], 2 + i * 3, 10, 2, 5)
    elif t == "b":
        R("#a98150", 1, 5, 14, 5); R("#7a5a34", 1, 10, 3, 4); R("#7a5a34", 12, 10, 3, 4)
    elif t == "@":
        R("#4a5058", 1, 1, 14, 14); R("#6a727c", 1, 1, 14, 2); R("#1a2028", 3, 3, 10, 7)
        R("#57b06f" if h > 0.5 else "#7fd0e0", 4, 4, 8, 2); R("#38a8e0", 4, 7, 5, 1)
        R(pal["accent"], 4, 12, 3, 2); R("#2a2a33", 9, 12, 3, 2)
    elif t == "p":
        R("#a06a44", 5, 10, 6, 5); R("#2f6b2f", 3, 2, 10, 8); R("#4a924a", 5, 3, 5, 4)


# --------------------------------------------------------------------------- the map object
class TileMap:
    """A walkable area. Build with TileMap.overworld() or TileMap.interior(building)."""

    def __init__(self, kind, rows, npc_defs, building=None, baked=None):
        self.kind, self.rows, self.building = kind, rows, building
        self.w, self.h = len(rows[0]), len(rows)
        self.px_w, self.px_h = self.w * TILE, self.h * TILE
        self.solid_set = wm.OVERWORLD_SOLID if kind == "overworld" else wm.INTERIOR_SOLID
        self.npc_defs = npc_defs
        self.baked = baked
        # Rect-based collision world: one Rect per solid tile, merged into horizontal runs for debug drawing.
        self.solid_rects = self._build_solid_rects()
        self.tile_rects = [r for r in self.solid_rects]           # kept for collidelist
        self.surface = None
        self.floor_texture = False
        self.props = []                    # depth-sorted furniture (interiors only)
        self.foreground = None             # overlay layer drawn above characters (layered rooms)
        self.fx = []                       # animated light halos (layered rooms)
        self.animated = []                 # props with update(dt)
        self.interactables = {}            # (tx, ty) -> object with interact(state)
        self.area, self.name = "overworld", "Riven Town"     # which outdoor area this is (routes.py) and its HUD name
        self.signs = {}                    # (tx, ty) of an S tile -> dialogue lines

    # ---- collision ----------------------------------------------------------------
    def _build_solid_rects(self):
        rects = []
        for y in range(self.h):
            for x in range(self.w):
                if self.rows[y][x] in self.solid_set:
                    rects.append(pygame.Rect(x * TILE, y * TILE, TILE, TILE))
        return rects

    def tile_at(self, x, y):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return "T" if self.kind == "overworld" else " "
        return self.rows[y][x]

    def is_solid(self, x, y):
        return self.tile_at(x, y) in self.solid_set

    def is_tall_grass(self, x, y):
        return self.kind == "overworld" and self.tile_at(x, y) == "g"

    def is_counter(self, x, y):
        return self.kind == "interior" and self.tile_at(x, y) == "C"

    def is_terminal(self, x, y):
        return self.kind == "interior" and self.tile_at(x, y) == "@"

    def blocked(self, tx, ty, npc_rects=()):
        """Bounding-box test for stepping onto tile (tx, ty): solid tile, outside the map, or an NPC rect."""
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return True
        box = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
        if box.collidelist(self.solid_rects) != -1:
            return True
        return box.collidelist(list(npc_rects)) != -1

    def ledge_landing(self, tx, ty, npc_rects=()):
        """One-way ledge: if (tx, ty) is a ledge tile and the tile right below it is free, return that landing tile (the
        player hops over the ledge, south only).  Anything else about a ledge tile is plain collision, so it cannot be
        entered from the sides or from below."""
        if self.kind != "overworld" or self.tile_at(tx, ty) != wm.LEDGE_DOWN:
            return None
        if self.blocked(tx, ty + 1, npc_rects):
            return None
        return (tx, ty + 1)

    # ---- factories ----------------------------------------------------------------
    @classmethod
    def overworld(cls):
        m = cls("overworld", wm.MAP_ROWS, wm.NPCS)
        m.signs = {(x, y): list(wm.SIGN_LINES) for y, row in enumerate(wm.MAP_ROWS) for x, c in enumerate(row) if c == "S"}
        m._render_overworld()
        return m

    @classmethod
    def route(cls, area_id):
        """An outdoor area beyond the town (routes.py): same tiles, collision and encounters as the town, plus the
        area's own buildings for the styled towns and its loot chests (routes.CHESTS)."""
        a = AREAS[area_id]
        m = cls("overworld", a.rows, a.npcs)
        m.area, m.name, m.signs = a.id, a.name, dict(a.signs)
        m._render_styled(a) if a.styled else m._render_route()
        for ch in CHESTS.get(area_id, ()):                 # outdoor loot chests (layered_room.FieldChest)
            c = layered_room.field_chest(ch["tile"], ch["key"], ch["loot"])
            m.props.append(c)
            m.animated.append(c)
            m.interactables[c.tile] = c
        return m

    @classmethod
    def interior(cls, b):
        i = b.interior
        m = cls("interior", i.rows, i.npcs, building=b, baked=i.spec)
        m.area, m.name = getattr(b, "area", "overworld"), b.name   # battles indoors use the building's area bg
        m._render_interior()
        return m

    # ---- rendering ----------------------------------------------------------------
    def _render_overworld(self):
        """Revamped town: ground + buildings baked once, scenery as depth-sorted props (see townview.py)."""
        s = pygame.Surface((self.px_w, self.px_h))
        s.fill(VOID)
        townview.draw_ground(s, self.rows, draw_overworld_tile)
        self.building_rects, origins = townview.draw_buildings(s, wm.BUILDINGS, as_props=wm.BACK_ACCESS)
        self.props = (townview.build_props(self.rows) + townview.pond_reeds(self.rows)
                      + townview.building_props(wm.BUILDINGS, wm.BACK_ACCESS, wm.BACK_ZONES))
        self.surface = s
        self.fx = townview.Fx(self.rows, wm.BUILDINGS, self.building_rects, origins, townview.pond_frames(self.rows),
                              townview.lamp_points(self.rows), townview.smoke_points(origins))
        self._tag_cache = {}

    def _render_route(self):
        """The routes' renderer: same ground and scenery as the town, plus any landmark buildings (gate huts,
        the Route 10 nook, the day-care) -- walk-behind, with name tags like the towns'."""
        s = pygame.Surface((self.px_w, self.px_h))
        s.fill(VOID)
        townview.draw_ground(s, self.rows, draw_overworld_tile)
        a = AREAS[self.area]
        origins = {}
        if getattr(a, "buildings", ()):
            ids = [b.id for b in a.buildings]
            self.building_rects, origins = townview.draw_buildings(s, a.buildings, as_props=ids)
            self.props = (townview.build_props(self.rows, green_only=True)
                          + townview.building_props(a.buildings, ids, wm.BACK_ZONES))
        else:
            self.building_rects = {}
            self.props = townview.build_props(self.rows, green_only=True)
        self.surface = s
        self.fx = townview.Fx(self.rows, a.buildings, self.building_rects, origins, [], [], [], studs=False,
                              glows=townview.glow_points(self.rows))
        self._tag_cache = {}

    def _render_styled(self, a):
        """A styled town (Epidimy Town or one of towns.py) with Riven Town's renderer: same lawns, cobbles + kerbs,
        stone walls, coping-rimmed ponds, trees, lamps -- but the area's own buildings, ponds, jets and cave."""
        rr = [r.replace("A", "P") for r in self.rows]                    # stairs are drawn as road tiles, like Route 1's
        s = pygame.Surface((self.px_w, self.px_h))
        s.fill(VOID)
        townview.draw_ground(s, rr, draw_overworld_tile)
        if a.cave:                                                        # a cave mouth cut into the stone wall (Epidimy)
            cx, cy = a.cave
            pygame.draw.rect(s, (36, 30, 32), (cx * TILE + 5 * PX, cy * TILE + 4 * PX, 6 * PX, 12 * PX), border_top_left_radius=3 * PX, border_top_right_radius=3 * PX)
            pygame.draw.rect(s, (92, 84, 88), (cx * TILE + 4 * PX, cy * TILE + 3 * PX, 8 * PX, PX))
        ids = [b.id for b in a.buildings]                                 # every building is a walk-behind fade prop
        self.building_rects, origins = townview.draw_buildings(s, a.buildings, as_props=ids)
        ponds = a.ponds
        self.props = (townview.build_props(rr, green_only=True) + townview.pond_reeds(rr, ponds)
                      + townview.building_props(a.buildings, ids, wm.BACK_ZONES))
        self.surface = s
        self.fx = townview.Fx(rr, a.buildings, self.building_rects, origins,
                              townview.pond_frames(rr, ponds, a.jets), townview.lamp_points(rr), [],
                              glows=townview.glow_points(rr))
        self._tag_cache = {}

    def sign_at(self, x, y):
        return self.signs.get((x, y))

    def update(self, dt):
        """Advance animated props (chests, glowing cores / screens, hovering Sci-Mon)."""
        for a in self.animated:
            a.update(dt)

    def interactable_at(self, x, y):
        return self.interactables.get((x, y))

    def sync_state(self, state):
        """Re-apply saved state (opened chests) to the room's objects."""
        for o in self.interactables.values():
            o.sync(state)

    def draw_top(self, surf, cam, t):
        """Overlays that must sit above the depth-sorted props (the lab beacon glow / a room's foreground layer)."""
        if self.kind == "overworld":
            townview.draw_beacon(surf, cam, t, self.fx)
            return
        if self.foreground is not None:
            surf.blit(self.foreground, (-cam.x, -cam.y))
        for f in self.fx:
            f.draw(surf, cam, t)

    def _render_interior(self):
        b = self.building
        if self.baked in interiors.LAYERED:   # layer-based room: background / midground / foreground
            room = layered_room.build(interiors.LAYERED[self.baked])
            self.surface = room.static_surface()
            self.props, self.foreground, self.fx = room.props, room.foreground, room.fx
            self.animated, self.interactables = room.animated, room.interactables
            assert self.surface.get_size() == (self.px_w, self.px_h), (self.baked, self.surface.get_size())
            return
        pal = b.interior.palette
        s = pygame.Surface((self.px_w, self.px_h))
        s.fill(VOID)
        floor_key, furn = (None, {})
        if b.kind in _FURNITURE:
            floor_key, furn = _FURNITURE[b.kind]
        self.floor_texture = floor_key is not None
        if floor_key:
            tile = assets.scaled(floor_key, TILE, TILE, smooth=False)
            for y in range(self.h):
                for x in range(self.w):
                    if self.rows[y][x] != "#":
                        s.blit(tile, (x * TILE, y * TILE))
        for y in range(self.h):
            for x in range(self.w):
                t = self.rows[y][x]
                if t in furn:
                    if t == "#":
                        continue
                    continue       # furniture sprites are drawn per run below
                draw_interior_tile(s, t, x * TILE, y * TILE, x, y, pal, self.floor_texture)
        for ch, x, y, run in _furniture_runs(self.rows, set(furn)):
            rel, stretch, hh, ww = furn[ch]
            bottom = (y + 1) * TILE
            if stretch:
                s.blit(assets.scaled(rel, run * TILE, hh * PX), (x * TILE, bottom - hh * PX))
            else:
                w = (ww or 16) * PX
                for i in range(run):
                    s.blit(assets.scaled(rel, w, hh * PX), (x * TILE + i * TILE + TILE // 2 - w // 2, bottom - hh * PX))
        self.surface = s

    # ---- per-frame ------------------------------------------------------------------
    def draw(self, surf, cam, t, debug=False):
        surf.fill(VOID)
        surf.blit(self.surface, (-cam.x, -cam.y))
        if self.kind == "overworld":
            self._draw_overworld_fx(surf, cam, t)
        if debug:
            self.draw_debug(surf, cam)

    def _draw_overworld_fx(self, surf, cam, t):
        def tag(label):
            img = self._tag_cache.get(label)
            if img is None:
                img = assets.font("display", 8).render(label, True, (250, 236, 200))
                self._tag_cache[label] = img
            return img
        focus = getattr(self, "focus", (0, 0))
        townview.draw_fx(surf, cam, t, self.fx, focus, tag, self.rows)

    def draw_debug(self, surf, cam):
        """Dev aid (F3): red = solid, green = exit, yellow = counter, cyan = terminal."""
        ov = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        for y in range(self.h):
            for x in range(self.w):
                ch = self.rows[y][x]
                col = None
                if self.kind == "interior":
                    col = {"E": (0, 255, 0, 100), "C": (255, 220, 0, 100), "@": (0, 200, 255, 100)}.get(ch)
                if col is None and ch in self.solid_set and ch != "C" and ch != "@":
                    col = (255, 0, 0, 80)
                if col:
                    ov.fill(col)
                    surf.blit(ov, (x * TILE - cam.x, y * TILE - cam.y))
