"""Layer-based interior rooms built from the tile map (tileset_map.py).

A `LayeredSpec` is pure data: room size, exits, a floor plan, wall roles and a list of placements.  Two things are
derived from that one description so they can never disagree:

  * collision_rows(spec)  -> the ASCII collision grid the rest of the game already speaks
                             ('#' solid, '.' floor, 'E' exit, 'C' counter, '@' Sci-Database terminal).  It needs no
                             images and no display, so worldmap.py can call it at import time.
  * build(spec)           -> a LayeredRoom with the three render layers:
        BACKGROUND  floors + floor decals + soft edge shading           (opaque, baked once)
        MIDGROUND   walls + wall decor (baked) and furniture / animated objects (depth-sorted with characters)
        FOREGROUND  overlay drawn above characters: placed 'fg' tiles + animated light halos

Placement kinds are derived from each role's layer / collide flags in tileset_map.py -- a server rack is solid
wherever you put it -- so a layout reads as "what goes where" and nothing else."""
import math
from dataclasses import dataclass, field

import pygame

import assets
import tileset
from data import ITEMS
from settings import TILE, VOID
from sprites import CreatureSprite
from tileset_map import info

WALL_ROWS = 3                     # rows 0..2 are the back wall; furniture bases start on row 3
SHADE = (6, 10, 22)
SOLID = ("#", "C", "@")


# --------------------------------------------------------------------------- the data model
@dataclass(frozen=True)
class Put:
    """Place role `name` with its footprint's top-left tile at (x, y).  fw/fh override the role's footprint,
    dx/dy nudge the sprite in screen px, `layer` / `collide` override the role's defaults, `id` keys saved state."""
    name: str
    x: int
    y: int
    fw: int = None
    fh: int = None
    dx: int = 0
    dy: int = 0
    layer: str = None
    collide: str = None
    id: str = None


def put(name, x, y, fw=None, fh=None, dx=0, dy=0, **kw):
    return Put(name, x, y, fw, fh, dx, dy, **kw)


# Compact placement shorthands (same letters the old prop renderer used): the kind sets collision and layer.
def S(name, x, y, fw=None, fh=None, dx=0, dy=0): return put(name, x, y, fw, fh, dx, dy, collide="#", layer="mid")
def C(name, x, y, fw=None, fh=None, dx=0, dy=0): return put(name, x, y, fw, fh, dx, dy, collide="C", layer="mid")
def T(name, x, y, fw=None, fh=None, dx=0, dy=0): return put(name, x, y, fw, fh, dx, dy, collide="@", layer="mid")
def N(name, x, y, fw=None, fh=None, dx=0, dy=0): return put(name, x, y, fw, fh, dx, dy, collide="", layer="mid")
def F(name, x, y, fw=None, fh=None, dx=0, dy=0): return put(name, x, y, fw, fh, dx, dy, collide="", layer="floor")
def W(name, x, y, fw=None, fh=None, dx=0, dy=0): return put(name, x, y, fw, fh, dx, dy, collide="", layer="wall")


@dataclass(frozen=True)
class Spawn:
    """A hovering overworld Sci-Mon (decorative, solid on its tile)."""
    species: str
    x: int
    y: int


@dataclass(frozen=True)
class Floor:
    """`rows` is an ASCII plan of the walkable area (cols-2 wide, rows-WALL_ROWS-1 tall); '.' = base tile, other
    characters are looked up in `legend` (char -> role)."""
    base: str
    rows: tuple = ()
    legend: dict = field(default_factory=dict)

    def name_at(self, fx, fy):
        if self.rows:
            ch = self.rows[fy][fx]
            if ch != ".":
                return self.legend[ch]
        return self.base


@dataclass(frozen=True)
class Walls:
    back: tuple = ("wall_blue", "wall_blue", "wall_blue_rail")      # one role per back-wall row, top to bottom
    side: str = "wall_stone"
    front: str = "wall_stone"


@dataclass(frozen=True)
class LayeredSpec:
    id: str
    cols: int
    rows: int
    exits: tuple                    # x tiles of the doorway on the last row
    floor: Floor
    walls: Walls
    things: tuple = ()
    creatures: tuple = ()
    door_mat: str = "mat_metal"
    wall_rows: int = WALL_ROWS


# --------------------------------------------------------------------------- derived properties
def _foot(p):
    d = info(p.name)
    return (p.fw if p.fw is not None else d.foot[0]), (p.fh if p.fh is not None else d.foot[1])


def _collide(p):
    return p.collide if p.collide is not None else info(p.name).collide


def _layer(p):
    return p.layer or info(p.name).layer


def _check_floor(spec):
    fh = spec.rows - spec.wall_rows - 1
    rows = spec.floor.rows
    assert not rows or (len(rows) == fh and all(len(r) == spec.cols - 2 for r in rows)), \
        f"{spec.id}: floor plan must be {spec.cols - 2}x{fh}"


def collision_rows(spec):
    """Collision grid from the placements: '#' solid, '.' floor, 'E' exit, 'C' counter, '@' terminal.  Pure data."""
    _check_floor(spec)
    wr, exit_y = spec.wall_rows, spec.rows - 1
    g = [["#"] * spec.cols for _ in range(spec.rows)]
    for y in range(wr, exit_y):
        for x in range(1, spec.cols - 1):
            g[y][x] = "."
    for x in spec.exits:
        g[exit_y][x] = "E"
    blockers = [(p.name, p.x, p.y, *_foot(p), _collide(p)) for p in spec.things]
    blockers += [(f"spawn:{c.species}", c.x, c.y, 1, 1, "#") for c in spec.creatures]
    for name, x, y, fw, fh, ch in blockers:
        if ch not in SOLID:
            continue
        for yy in range(y, y + fh):
            for xx in range(x, x + fw):
                assert 0 < xx < spec.cols - 1 and wr <= yy < exit_y, (spec.id, name, xx, yy)
                assert g[yy][xx] == ".", f"{spec.id}: {name} overlaps another footprint at {(xx, yy)}"
                g[yy][xx] = ch
    return ["".join(r) for r in g]


# --------------------------------------------------------------------------- animated / interactive objects
class AnimatedProp:
    """Depth-sorted object whose picture changes: same attributes as a static prop (`image`, `x`, `y`, `sort_y`) so
    the overworld draws it like any other, plus update(dt) and an optional interact()."""

    def __init__(self, asset, x, y, sort_y, tile, key):
        self.asset, self.animator = asset, asset.animator()
        self.x, self.y, self.sort_y, self.tile, self.key = x, y, sort_y, tile, key

    @property
    def image(self):
        return self.animator.frame

    def update(self, dt):
        self.animator.update(dt)

    def interact(self, state):
        return None

    def sync(self, state):
        pass


def _opened(state):
    s = getattr(state, "opened_chests", None)
    if s is None:
        s = state.opened_chests = set()
    return s


class Chest(AnimatedProp):
    """Loot chest: closed idle -> opening (one-shot) -> open.  Gives its loot once; remembered in GameState."""
    opened = False

    def sync(self, state):
        should = self.key in _opened(state)
        if should != self.opened:
            self.opened = should
            self.animator.play("open" if should else "closed", restart=True)

    def interact(self, state):
        if self.opened:
            return ["The case is empty."]
        item, n = self.asset.defn.loot
        self.opened = True
        self.animator.play("opening", restart=True)
        state.add_item(item, n)
        _opened(state).add(self.key)
        name = ITEMS[item].name if item in ITEMS else item
        return ["You open the supply case.", f"Found {name} x{n}!"]


_radial_cache = {}


def _radial(radius, color):
    """Soft round light: alpha falls off smoothly from the centre (cached per colour/size)."""
    key = (radius, color)
    g = _radial_cache.get(key)
    if g is None:
        g = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            a = int(255 * (1 - r / radius) ** 1.8) + 1
            pygame.draw.circle(g, color + (min(255, a),), (radius, radius), r)
        _radial_cache[key] = g
    return g


class GlowFx:
    """Pulsing light halo, drawn in the foreground layer (above characters) so light spills over them."""

    def __init__(self, center, color, radius, strength, phase):
        self.center, self.color, self.radius, self.strength, self.phase = center, color, radius, strength, phase

    def draw(self, surf, cam, t):
        pulse = 0.82 + 0.18 * math.sin(t * math.tau * 0.9 + self.phase)
        g = _radial(self.radius, self.color)
        g.set_alpha(int(255 * self.strength * pulse))
        surf.blit(g, (self.center[0] - self.radius - cam.x, self.center[1] - self.radius - cam.y))


# --------------------------------------------------------------------------- the built room
class LayeredRoom:
    def __init__(self, spec, background, midground, props, foreground, fx, interactables):
        self.spec = spec
        self.background, self.midground, self.foreground = background, midground, foreground
        self.props, self.fx, self.interactables = props, fx, interactables
        self.animated = [p for p in props if hasattr(p, "update")]

    def static_surface(self):
        """Background + midground walls composited into one opaque Surface (what TileMap blits each frame)."""
        s = self.background.copy()
        s.blit(self.midground, (0, 0))
        return s


_texture_cache = {}


def _texture(name, w, h):
    """`name` tiled across a w x h canvas, for roles whose art is not exactly one TILE (legacy fallbacks)."""
    key = (name, w, h)
    tex = _texture_cache.get(key)
    if tex is None:
        s = tileset.sprite(name)
        tex = pygame.Surface((w, h), pygame.SRCALPHA)
        sw, sh = s.get_size()
        for y in range(0, h, sh):
            for x in range(0, w, sw):
                tex.blit(s, (x, y))
        _texture_cache[key] = tex
    return tex


def _blit_cell(dst, name, tx, ty, room_w, room_h):
    s = tileset.sprite(name)
    if s.get_size() == (TILE, TILE):
        dst.blit(s, (tx * TILE, ty * TILE))
    else:
        dst.blit(_texture(name, room_w, room_h), (tx * TILE, ty * TILE), pygame.Rect(tx * TILE, ty * TILE, TILE, TILE))


def _place(img, p, fw, fh):
    """Top-left of a sprite for a placement: centred on the footprint, bottom edge on the footprint's bottom."""
    x = p.x * TILE + (fw * TILE - img.get_width()) // 2 + p.dx
    bottom = (p.y + fh) * TILE
    return x, bottom - img.get_height() + p.dy, bottom


class _StaticProp:
    def __init__(self, image, x, y, sort_y):
        self.image, self.x, self.y, self.sort_y = image, x, y, sort_y


def _shade_edges(bg, spec):
    """Soft darkening under the back wall, along the side walls and above the front wall, so the floor has depth."""
    W_, H_ = bg.get_size()
    top, bot = spec.wall_rows * TILE, (spec.rows - 1) * TILE

    def band(length, a_max, size):
        s = pygame.Surface(size, pygame.SRCALPHA)
        vertical = size[0] == length
        for i in range(length):
            a = int(a_max * (1 - i / length) ** 2)
            if vertical:
                pygame.draw.line(s, SHADE + (a,), (i, 0), (i, size[1]))
            else:
                pygame.draw.line(s, SHADE + (a,), (0, i), (size[0], i))
        return s

    under = band(22, 95, (W_ - 2 * TILE, 22))
    bg.blit(under, (TILE, top))
    side = band(22, 80, (22, bot - top))
    bg.blit(side, (TILE, top))
    bg.blit(pygame.transform.flip(side, True, False), (W_ - TILE - 22, top))
    front = pygame.transform.flip(band(18, 70, (W_ - 2 * TILE, 18)), False, True)
    bg.blit(front, (TILE, bot - 18))


def build(spec):
    _check_floor(spec)
    W_, H_ = spec.cols * TILE, spec.rows * TILE
    wr, exit_y = spec.wall_rows, spec.rows - 1

    # ---- BACKGROUND: floors, floor decals, shading ------------------------------------------------------------
    bg = pygame.Surface((W_, H_))
    bg.fill(VOID)
    for ty in range(wr, exit_y):
        for tx in range(1, spec.cols - 1):
            _blit_cell(bg, spec.floor.name_at(tx - 1, ty - wr), tx, ty, W_, H_)
    for x in spec.exits:                                           # the doorway tile is floor too
        _blit_cell(bg, spec.floor.base, x, exit_y, W_, H_)
    _shade_edges(bg, spec)
    mat = tileset.sprite(spec.door_mat)
    cx = sum(spec.exits) / len(spec.exits) * TILE + TILE // 2
    bg.blit(mat, (int(cx - mat.get_width() / 2), (exit_y + 1) * TILE - mat.get_height() - 4))

    # ---- MIDGROUND (static): walls and wall decor ----------------------------------------------------------------
    mid = pygame.Surface((W_, H_), pygame.SRCALPHA)
    for ty in range(wr):
        name = spec.walls.back[min(ty, len(spec.walls.back) - 1)]
        for tx in range(spec.cols):
            _blit_cell(mid, name, tx, ty, W_, H_)
    for ty in range(wr, spec.rows):
        for tx in (0, spec.cols - 1):
            _blit_cell(mid, spec.walls.side, tx, ty, W_, H_)
    for tx in range(1, spec.cols - 1):
        if tx not in spec.exits:
            _blit_cell(mid, spec.walls.front, tx, exit_y, W_, H_)

    props, fx, interactables = [], [], {}
    fg = None
    for p in spec.things:
        layer, (fw, fh) = _layer(p), _foot(p)
        if p.name in tileset.ANIMS:
            asset = tileset.anim_asset(p.name)
            img = asset.animator().frame
            x, y, bottom = _place(img, p, fw, fh)
            key = f"{spec.id}:{p.id or f'{p.name}@{p.x},{p.y}'}"
            cls = Chest if asset.defn.kind == "chest" else AnimatedProp
            prop = cls(asset, x, y, bottom, (p.x, p.y), key)
            props.append(prop)
            if cls is Chest:
                interactables[(p.x, p.y)] = prop
            g = asset.defn.glow
            if g:
                fx.append(GlowFx((x + img.get_width() // 2, y + int(img.get_height() * 0.45)), g[:3],
                                 int(g[3] * TILE), g[4], phase=p.x * 1.7 + p.y))
            continue
        img = tileset.sprite(p.name)
        x, y, bottom = _place(img, p, fw, fh)
        if layer == "floor":
            bg.blit(img, (x, y))
        elif layer == "wall":
            mid.blit(img, (x, p.y * TILE + p.dy))
        elif layer == "fg":
            if fg is None:
                fg = pygame.Surface((W_, H_), pygame.SRCALPHA)
            fg.blit(img, (x, y))
        else:                                                      # "mid": depth-sorted with the characters
            props.append(_StaticProp(img, x, y, bottom + (0 if _collide(p) in SOLID else 1)))
            g = info(p.name).glow
            if g:
                fx.append(GlowFx((x + img.get_width() // 2, y + int(img.get_height() * 0.4)), g[:3], int(g[3] * TILE),
                                 g[4], phase=p.x * 1.3 + p.y))

    for c in spec.creatures:
        props.append(CreatureSprite(c.species, c.x, c.y))
    return LayeredRoom(spec, bg, mid, props, fg, fx, interactables)
