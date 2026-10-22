"""Renderer for the revamped Riven Town overworld.

The ground (grass variants, cobbled roads with kerbs, plaza, crop plots, hedges, fences, pond coping, sea wall) and the
buildings are baked once into one big Surface.  Tall scenery (trees, lamp posts, benches, stalls...) becomes depth-sorted
`Prop`s so characters walk behind canopies and in front of benches.  Animated extras (pond shimmer + fountain, lamp glow,
chimney smoke, lab beacon, road studs, name tags that fade in near a building) are drawn per frame by `draw_fx`.

Sand and ocean tiles are drawn by map.draw_overworld_tile exactly as before.  The beach only gains dressing cut from the
original beach art (tools/generate_original_art.py -> assets/town/beach_*.png): palms and sprouts (Q, i) and rock lumps
(j) are depth-sorted props, tide pools (v, 2x2 small or 3x3 rock-ringed) and sand flowers (z) are baked onto the sand.
Art comes from assets/town/*.png (built by tools/town_terrain.py, town_props.py, town_buildings.py).
"""
import math

import pygame

import assets
import worldmap as wm
from interiors import Prop
from settings import PX, TILE, VOID

ROAD_LIKE = set("PpD")
GRASS_UNDER = set("GgFTBDHfLbNMOxyYSmauqrcp")      # tiles drawn over a lawn (everything except road/sand/sea/pond/wall)


def hash2(x, y):
    n = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return n - math.floor(n)


def _rel(name):
    """Asset path for a sprite name: bare names live in assets/town/, names with a folder ("mpw/buildings/lab") are paths."""
    return f"{name}.png" if "/" in name else f"town/{name}.png"


def spr(name, k=PX):
    """Native sprite scaled by `k` (x3 by default) with nearest neighbour (cached)."""
    rel = _rel(name)
    img = assets.image(rel)
    return assets.scaled(rel, max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k)), smooth=False)


def tile(name):
    return assets.scaled(f"town/{name}.png", TILE, TILE, smooth=False)


def tile_n(name, w, h):
    """A sprite stretched over w x h tiles (the 32x32 / 48x48 tide pools are exactly 2x2 / 3x3 tiles at x3)."""
    return assets.scaled(f"town/{name}.png", w * TILE, h * TILE, smooth=False)


# ---------------------------------------------------------------------------------------------------- tiles
def _at(rows, x, y):
    if 0 <= y < len(rows) and 0 <= x < len(rows[0]):
        return rows[y][x]
    return "T"


def _lawn(s, x, y, flowers=False):
    h = hash2(x, y)
    s.blit(tile(f"{'gflower' if flowers else 'grass'}_{int(h * 4) % 4}"), (x * TILE, y * TILE))


def _crop_kind(x, y):
    kinds = ["tomato", "cabbage", "wheat", "carrot", "lettuce", "berry"]
    return kinds[((x * 2 + y) // 2) % len(kinds)]


def draw_ground(s, rows, draw_old_tile):
    h_, w_ = len(rows), len(rows[0])
    for y in range(h_):
        for x in range(w_):
            t = rows[y][x]
            sx, sy = x * TILE, y * TILE
            if t in "sWQijvz":
                # the beach and ocean: original tile code; beach dressing (Q i j v z) stands on that same sand
                draw_old_tile(s, "W" if t == "W" else "s", sx, sy, x, y, rows)
                if t == "z":
                    s.blit(tile(f"beach_flowers_{int(hash2(x + 5, y + 9) * 6) % 6}"), (sx, sy))
                continue
            if t == "P" or t == "D":
                s.blit(tile(f"road_{int(hash2(x, y) * 4) % 4}"), (sx, sy))
            elif t == "p":
                s.blit(tile(f"plaza_{(x + y) % 2 + int(hash2(x, y) * 2) * 2}"), (sx, sy))
            elif t == "g":
                s.blit(tile(f"tallgrass_{int(hash2(x, y) * 4) % 4}"), (sx, sy))
            elif t == "F":
                _lawn(s, x, y, True)
            elif t == "w":
                s.blit(tile("pond_0"), (sx, sy))
            elif t in "hk":
                s.blit(_wall_tile(x, _at(rows, x, y - 1) in "hk", _at(rows, x, y + 1) in "hk"), (sx, sy))
            elif t == "c":
                s.blit(tile(f"crop_{_crop_kind(x, y)}_{(x + y) % 2}"), (sx, sy))
            else:
                _lawn(s, x, y)
            if t in "Pp":                                             # kerbs where the road meets the lawn
                for key, dx, dy in (("n", 0, -1), ("s", 0, 1), ("w", -1, 0), ("e", 1, 0)):
                    if _at(rows, x + dx, y + dy) not in ROAD_LIKE:
                        s.blit(tile(f"kerb_{key}"), (sx, sy))
    # hedges and fences autotile after the lawn exists
    for y in range(h_):
        for x in range(w_):
            t = rows[y][x]
            sx, sy = x * TILE, y * TILE
            if t == "H":
                l, r = _at(rows, x - 1, y) == "H", _at(rows, x + 1, y) == "H"
                kind = "mid" if (l and r) else "l" if r else "r" if l else "solo"
                s.blit(tile(f"hedge_{kind}"), (sx, sy))
            elif t == "f":
                l, r = _at(rows, x - 1, y) == "f", _at(rows, x + 1, y) == "f"
                u, d = _at(rows, x, y - 1) == "f", _at(rows, x, y + 1) == "f"
                if (l or r) and not (u or d):
                    s.blit(tile("fence_h"), (sx, sy))
                elif (u or d) and not (l or r):
                    s.blit(tile("fence_v"), (sx, sy))
                    if not u:
                        s.blit(tile("fence_post"), (sx, sy))
                else:
                    s.blit(tile("fence_post"), (sx, sy))
                    if l or r:
                        s.blit(tile("fence_h"), (sx, sy))
    _draw_ledges(s, rows)
    _draw_tide_pools(s, rows)
    # stone rim around the pond
    for y in range(h_):
        for x in range(w_):
            if rows[y][x] != "w":
                continue
            for key, dx, dy in (("n", 0, -1), ("s", 0, 1), ("w", -1, 0), ("e", 1, 0)):
                if _at(rows, x + dx, y + dy) != "w":
                    nx, ny = (x + dx) * TILE, (y + dy) * TILE
                    s.blit(tile(f"coping_{key}"), (nx, ny))


_ledge_cache = {}
_LEDGE_HI, _LEDGE_LIP, _LEDGE_FACE, _LEDGE_DARK = (226, 204, 160), (196, 170, 128), (152, 118, 84), (98, 74, 52)


def _ledge_piece(left_end, right_end, vertical, strip_right, variant):
    """One 16x16 art-pixel ledge tile (x3).  Horizontal: tan lip, brown face, dark foot and a soft shadow, with the ends
    rounded where the ledge stops.  Vertical (the side edge of a ledge run): a 4-pixel wide brown column."""
    key = (left_end, right_end, vertical, strip_right, variant)
    img = _ledge_cache.get(key)
    if img is not None:
        return img
    img = pygame.Surface((TILE, TILE), pygame.SRCALPHA)

    def px(x, y, w, h, col):
        img.fill(col, (x * PX, y * PX, w * PX, h * PX))

    if vertical:
        x0 = 11 if strip_right else 1
        px(x0 + (0 if strip_right else 3), 0, 1, 16, _LEDGE_LIP)          # lit inner edge
        px(x0 + (1 if strip_right else 1), 0, 2, 16, _LEDGE_FACE)
        px(x0 + (3 if strip_right else 0), 0, 1, 16, _LEDGE_DARK)         # dark outer edge
        for y in range(1, 16, 4):                                           # a few stones
            px(x0 + 1 + (variant + y) % 2, y, 1, 1, _LEDGE_DARK)
    else:
        a, b = (1 if left_end else 0), (15 if right_end else 16)
        px(a, 9, b - a, 1, _LEDGE_HI)
        px(a, 10, b - a, 1, _LEDGE_LIP)
        px(a, 11, b - a, 3, _LEDGE_FACE)
        px(a + (1 if left_end else 0), 14, b - a - (1 if left_end else 0) - (1 if right_end else 0), 1, _LEDGE_DARK)
        for i in range(variant % 4, 16, 4):                                 # stone seams
            if a <= i < b:
                px(i, 11, 1, 2, _LEDGE_DARK)
        shade = pygame.Surface((TILE, PX), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 55))
        img.blit(shade, (a * PX, 15 * PX), pygame.Rect(0, 0, (b - a) * PX, PX))
    _ledge_cache[key] = img
    return img


def _draw_ledges(s, rows):
    """One-way ledges ('l').  A tile with ledge neighbours left/right is a horizontal run; a tile with ledge tiles only above
    or below is the vertical side edge of a run, drawn on the side the run extends from."""
    for y in range(len(rows)):
        for x in range(len(rows[0])):
            if rows[y][x] != "l":
                continue
            l, r = _at(rows, x - 1, y) == "l", _at(rows, x + 1, y) == "l"
            u, d = _at(rows, x, y - 1) == "l", _at(rows, x, y + 1) == "l"
            vertical = (u or d) and not (l or r)
            strip_right = True
            if vertical:                                           # find the horizontal run this column belongs to
                yy = y
                while yy > 0 and rows[yy - 1][x] == "l":
                    yy -= 1
                while yy < len(rows) and rows[yy][x] == "l":
                    if _at(rows, x - 1, yy) == "l":
                        strip_right = True
                        break
                    if _at(rows, x + 1, yy) == "l":
                        strip_right = False
                        break
                    yy += 1
            s.blit(_ledge_piece(not l, not r, vertical, strip_right, x % 4), (x * TILE, y * TILE))


_wall_cache = {}


def _wall_tile(x, wall_above, wall_below):
    """Sea wall / stone ledge piece.  The sprite is a grass cap over a stone face; where another wall tile sits above, only
    the face is drawn (its brick rows repeated), so vertical ledges read as one continuous stone wall instead of stacked
    caps.  The bottom row of the sprite is the wall's dark foot and is kept only where the wall ends."""
    key = (x % 4, wall_above, wall_below)
    img = _wall_cache.get(key)
    if img is None:
        base = tile(f"seawall_{x % 4}")
        if not wall_above:
            img = base
        else:
            face = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            body_top, body_rows = 6 * PX, 9 * PX                     # sprite rows 6..14: brick body without the foot
            for y in range(0, TILE, body_rows):
                face.blit(base, (0, y), pygame.Rect(0, body_top, TILE, min(body_rows, TILE - y)))
            if not wall_below:
                face.blit(base, (0, TILE - PX), pygame.Rect(0, TILE - PX, TILE, PX))
            img = face
        _wall_cache[key] = img
    return img


def _draw_tide_pools(s, rows):
    """Each rectangle of 'v' tiles is one pool: 2x2 -> small sand pool (4 variants), 3x3 -> the rock-ringed pool."""
    seen = set()
    for y in range(len(rows)):
        for x in range(len(rows[0])):
            if rows[y][x] != "v" or (x, y) in seen:
                continue
            w = h = 0
            while _at(rows, x + w, y) == "v":
                w += 1
            while _at(rows, x, y + h) == "v":
                h += 1
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    seen.add((xx, yy))
            name = "beach_pool_big" if w == 3 else f"beach_pool_s{int(hash2(x, y) * 4) % 4}"
            s.blit(tile_n(name, w, h), (x * TILE, y * TILE))


# ---------------------------------------------------------------------------------------------------- props
PROP_SPRITE = {"L": "lamp_post", "b": "bench_0", "N": "notice_board", "x": "crate_stack", "y": "barrel", "Y": "hay_bale",
               "S": "signpost", "m": "mailbox", "a": "scarecrow", "q": "well", "u": "bush_0", "r": "rock_small"}


# Green trees cut from Trees.png (assets/mpw/trees, built by tools/build_mpw_assets.py).  Only green species are used:
# round and conical crowns, drawn at native size (about 1.3 tiles wide) with a soft ground shadow; the big round tree is rare.
GREEN_TREES = ("tree_a1", "tree_a2", "tree_a4", "tree_a5", "tree_a7", "tree_a8", "tree_a9", "tree_b3", "tree_b7",
               "tree_c0", "tree_c4", "tree_c8")
_shadowed = {}


def _tree_name(x, y, rows, green_only=False):
    """Name of the tree sprite for map tile (x, y): stable per tile, always a green MPW tree."""
    h = hash2(x + 3, y + 11)
    if h < 0.06:
        return "mpw/trees/tree_big"
    return "mpw/trees/" + GREEN_TREES[int(hash2(x * 7 + 1, y * 13 + 5) * len(GREEN_TREES)) % len(GREEN_TREES)]


def _with_shadow(name, k=1):
    """Sprite with a translucent ground ellipse under its trunk, so trees sit on the lawn instead of floating."""
    key = (name, k)
    img = _shadowed.get(key)
    if img is None:
        base = spr(name, k)
        w, h = base.get_size()
        sh_h = max(8, h // 7)
        img = pygame.Surface((w, h + sh_h // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(img, (14, 40, 14, 70), (w // 8, h - sh_h // 2, w * 3 // 4, sh_h))
        img.blit(base, (0, 0))
        _shadowed[key] = img
    return img


def make_prop(name, tx, ty, w_tiles=1, dy=0, k=PX, shadow=False):
    img = _with_shadow(name, k) if shadow else spr(name, k)
    x = tx * TILE + (w_tiles * TILE - img.get_width()) // 2
    bottom = (ty + 1) * TILE
    return Prop(img, x, bottom - img.get_height() + dy, bottom)


def build_props(rows, green_only=False):
    props = []
    h_, w_ = len(rows), len(rows[0])
    for y in range(h_):
        x = 0
        while x < w_:
            t = rows[y][x]
            if t == "T":
                props.append(make_prop(_tree_name(x, y, rows, green_only), x, y, dy=4, k=1, shadow=True))
            elif t == "u":                                            # green bush from Trees.png, halved to one tile wide
                props.append(make_prop(f"mpw/trees/bush_{int(hash2(x, y) * 2) % 2}", x, y, dy=2, k=0.5))
            elif t in PROP_SPRITE:
                props.append(make_prop(PROP_SPRITE[t], x, y, dy=2 if t != "L" else 3))
            elif t == "O":
                props.append(make_prop(f"planter_{int(hash2(x, y) * 4) % 4}", x, y, dy=2))
            elif t == "k":
                props.append(make_prop("sea_pillar", x, y, dy=0))
            elif t == "Q":                                            # beach palms (two variants)
                props.append(make_prop(f"beach_palm_{int(hash2(x, y) * 2) % 2}", x, y, dy=4))
            elif t == "i":
                props.append(make_prop("beach_sprout", x, y, dy=0))
            elif t == "j":
                props.append(make_prop(f"beach_rock_{int(hash2(x, y) * 4) % 4}", x, y, dy=0))
            elif t == "M":
                x2 = x
                while x2 < w_ and rows[y][x2] == "M":
                    x2 += 1
                n = x2 - x
                props.append(make_prop(f"market_{(x // 5) % 2}", x, y, w_tiles=n, dy=2))
                x = x2
                continue
            x += 1
    return props


# ---------------------------------------------------------------------------------------------------- buildings
def draw_buildings(s, buildings, as_props=()):
    """Bottom-anchored, centred on the footprint. Soft contact shadows first, then the sprites. Returns rects + origins.
    Buildings whose id is in `as_props` are not baked: build_building_props() returns them as depth-sorted props instead."""
    rects, origins = {}, {}
    seen = {}
    for b in buildings:
        fx, fy, fw, fh = b.footprint
        pic = spr(b.sprite[:-4])
        bx = int(fx * TILE + (fw * TILE - pic.get_width()) // 2)
        by = int((fy + fh) * TILE - pic.get_height() + 2 * PX)
        sh = pygame.Surface((pic.get_width() + 14, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (10, 30, 20, 70), sh.get_rect())
        s.blit(sh, (bx - 7 + 6, (fy + fh) * TILE - 12))
        if b.id not in as_props:
            s.blit(pic, (bx, by))
        rects[b.id] = pygame.Rect(bx, by, pic.get_width(), pic.get_height())
        origins[b.id] = (bx, by)
        seen[b.id] = pic
    return rects, origins


def building_props(buildings, ids, zones):
    """Walk-behind buildings as props sorted by the bottom of their footprint: anyone standing behind is drawn first (hidden by
    the facade), anyone in front is drawn on top.  `back_zone` lets the overworld fade the building while the player is behind it."""
    out = []
    for b in buildings:
        if b.id not in ids:
            continue
        fx, fy, fw, fh = b.footprint
        pic = spr(b.sprite[:-4])
        bx = int(fx * TILE + (fw * TILE - pic.get_width()) // 2)
        by = int((fy + fh) * TILE - pic.get_height() + 2 * PX)
        pr = Prop(pic, bx, by, int((fy + fh) * TILE))
        pr.back_zone = zones.get(b.id)
        out.append(pr)
    return out


# ---------------------------------------------------------------------------------------------------- pond
def pond_frames(rows, regions=None, jet_regions=None):
    """Animated water for each pond region (default: the town's).  With `jet_regions`, only those regions get the fountain
    jet (and no lily pads under it); every other region is plain water with lily pads."""
    frames = []
    for region in (wm.POND_REGIONS if regions is None else regions):
        px0, py0, pw, ph = region
        jet = jet_regions is None or region in jet_regions
        per = []
        for f in range(4):
            surf = pygame.Surface((pw * TILE, ph * TILE))
            for yy in range(ph):
                for xx in range(pw):
                    surf.blit(tile(f"pond_{(f + xx + yy) % 4}"), (xx * TILE, yy * TILE))
            if jet_regions is None or not jet:
                surf.blit(spr("lilypads"), (TILE * 2 + 8, TILE + 6))
                surf.blit(spr("lilypads"), (pw * TILE - TILE * 3, TILE * (ph - 2) + 4))
            per.append(surf)
        frames.append((region, per, jet))
    return frames


def pond_reeds(rows, regions=None):
    out = []
    for (px0, py0, pw, ph) in (wm.POND_REGIONS if regions is None else regions):
        for x in (px0, px0 + pw - 1):
            for y in (py0, py0 + ph - 1):
                out.append(make_prop(f"reeds_{(x + y) % 2}", x, y, dy=-4))
    return out


# ---------------------------------------------------------------------------------------------------- fx
_glow = {}


def _glow_surface(r, color):
    key = (r, color)
    g = _glow.get(key)
    if g is None:
        g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(r, 0, -3):
            a = int(46 * (1 - i / r) ** 1.6) + 2
            pygame.draw.circle(g, color + (a,), (r, r), i)
        _glow[key] = g
    return g


class Fx:
    def __init__(self, rows, buildings, rects, origins, ponds, lamps, smoke, studs=True):
        self.rows, self.buildings, self.rects, self.origins = rows, buildings, rects, origins
        self.ponds, self.lamps, self.smoke = ponds, lamps, smoke
        self.studs = studs                                      # pulsing studs in the cobbles (town roads only)


def smoke_points(origins):
    pts = []
    chim = {"player-house": (40, 6), "cottage-toma": (13, 6), "cottage-reya": (40, 6), "cush": (71, 1)}
    for bid, (cx, cy) in chim.items():
        if bid in origins:
            ox, oy = origins[bid]
            pts.append((ox + cx * PX, oy + cy * PX))
    return pts


def lamp_points(rows):
    pts = []
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == "L":
                pts.append((x * TILE + TILE // 2, (y + 1) * TILE - 33 * PX // 1 + 20))
            elif c == "k":
                pts.append((x * TILE + TILE // 2, (y + 1) * TILE - 20 * PX + 10))
    return pts


def draw_beacon(surf, cam, t, fx):
    """Astrion lab beacon glow. Drawn after the depth-sorted props because the lab itself is a prop now (walk-behind building)."""
    if "lab" in fx.origins:
        ox, oy = fx.origins["lab"]
        on = 0.5 + 0.5 * math.sin(t * 4)
        bx, by = ox + 41 * PX - cam.x, oy + 2 * PX - cam.y
        g = _glow_surface(34, (255, 80, 80))
        g.set_alpha(int(60 + 190 * on))
        surf.blit(g, (bx - 34, by - 34))


def draw_fx(surf, cam, t, fx, focus, font_render, rows):
    vw, vh = int(cam.view.x), int(cam.view.y)
    # pond
    for (region, per, has_jet) in fx.ponds:
        px0, py0, pw, ph = region
        frame = per[int(t * 2.2) % 4]
        surf.blit(frame, (px0 * TILE - cam.x, py0 * TILE - cam.y))
        if not has_jet:
            continue
        jet = spr(f"fountain_{int(t * 7) % 3}")
        cx = (px0 + pw / 2) * TILE - cam.x
        cy = (py0 + ph / 2) * TILE - cam.y + 22
        surf.blit(jet, (cx - jet.get_width() // 2, cy - jet.get_height() + 18))
    # glowing studs set into the cobbles (the old conduit lore, now a subtle pulse)
    c0, r0, cols, rws = cam.visible_tiles()
    for my in range(max(0, r0), min(len(rows), r0 + rws)):
        for mx in range(max(0, c0), min(len(rows[0]), c0 + cols)):
            if rows[my][mx] == "P" and (mx + my) % 2 == 0 and _at(rows, mx, my - 1) in ROAD_LIKE | set("T") or False:
                pass
            if fx.studs and rows[my][mx] == "P" and (mx * 3 + my * 5) % 4 == 0:
                a = int(120 + 120 * math.sin(t * 2.4 + (mx + my) * 0.8))
                pygame.draw.rect(surf, (110, 235, 245), (mx * TILE - cam.x + 22, my * TILE - cam.y + 22, 4, 4))
                pygame.draw.rect(surf, (210, 255, 255), (mx * TILE - cam.x + 23, my * TILE - cam.y + 23, 2, 2))
    # lamp glow
    for (lx, ly) in fx.lamps:
        sx, sy = lx - cam.x, ly - cam.y
        if -80 < sx < vw + 80 and -80 < sy < vh + 80:
            g = _glow_surface(74, (255, 214, 120))
            g.set_alpha(int(190 + 40 * math.sin(t * 2.0 + lx * 0.01)))
            surf.blit(g, (sx - 74, sy - 74))
    # chimney smoke
    for i, (sx0, sy0) in enumerate(fx.smoke):
        for k in range(4):
            ph = (t * 0.45 + i * 0.37 + k / 4) % 1.0
            x = sx0 + math.sin(ph * 5 + k) * 6 + ph * 14 - cam.x
            y = sy0 - ph * 70 - cam.y
            r = int(5 + ph * 8)
            a = int(150 * (1 - ph))
            puff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (235, 238, 240, a), (r, r), r)
            surf.blit(puff, (x - r, y - r))
    # name tags: fade in as the player gets close to a building
    fx_, fy_ = focus
    for i, b in enumerate(fx.buildings):
        r = fx.rects[b.id]
        d = math.hypot(r.centerx - fx_, r.bottom - fy_)
        if d > 330:
            continue
        alpha = int(255 * max(0.0, min(1.0, (330 - d) / 110)))
        img = font_render(b.sign if b.kind != "house" else ("Home" if b.id == "player-house" else b.sign))
        w, h = img.get_width() + 18, 22
        tag = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(tag, (60, 40, 28, 235), tag.get_rect(), border_radius=5)
        pygame.draw.rect(tag, (230, 196, 120, 255), tag.get_rect().inflate(-4, -4), 1, border_radius=3)
        tag.blit(img, img.get_rect(center=(w // 2, h // 2)))
        tag.set_alpha(alpha)
        cx = r.centerx - cam.x
        by = r.bottom - cam.y + 6
        surf.blit(tag, (cx - w // 2, by))
