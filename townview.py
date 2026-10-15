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


def spr(name):
    """Native sprite scaled x3 with nearest neighbour (cached)."""
    img = assets.image(f"town/{name}.png")
    return assets.scaled(f"town/{name}.png", img.get_width() * PX, img.get_height() * PX, smooth=False)


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
                s.blit(tile(f"seawall_{x % 4}"), (sx, sy))
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


def _tree_name(x, y, rows):
    h = hash2(x + 3, y + 11)
    border = x <= 1 or x >= 42 or y == 0 or y >= 15
    if border:
        return ("tree_pine_0" if h < 0.22 else "tree_pine_1" if h < 0.36 else "tree_glow" if h < 0.44 else
                "tree_oak_1" if h < 0.64 else "tree_oak_2" if h < 0.8 else "tree_oak_0")
    return ("tree_blossom_0" if h < 0.3 else "tree_blossom_1" if h < 0.5 else "tree_oak_1" if h < 0.75 else "tree_oak_0")


def make_prop(name, tx, ty, w_tiles=1, dy=0):
    img = spr(name)
    x = tx * TILE + (w_tiles * TILE - img.get_width()) // 2
    bottom = (ty + 1) * TILE
    return Prop(img, x, bottom - img.get_height() + dy, bottom)


def build_props(rows):
    props = []
    h_, w_ = len(rows), len(rows[0])
    for y in range(h_):
        x = 0
        while x < w_:
            t = rows[y][x]
            if t == "T":
                props.append(make_prop(_tree_name(x, y, rows), x, y, dy=6))
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
        pic = spr(b.sprite.split("/")[-1][:-4])
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
        pic = spr(b.sprite.split("/")[-1][:-4])
        bx = int(fx * TILE + (fw * TILE - pic.get_width()) // 2)
        by = int((fy + fh) * TILE - pic.get_height() + 2 * PX)
        pr = Prop(pic, bx, by, int((fy + fh) * TILE))
        pr.back_zone = zones.get(b.id)
        out.append(pr)
    return out


# ---------------------------------------------------------------------------------------------------- pond
def pond_frames(rows):
    frames = []
    for region in wm.POND_REGIONS:
        px0, py0, pw, ph = region
        per = []
        for f in range(4):
            surf = pygame.Surface((pw * TILE, ph * TILE))
            for yy in range(ph):
                for xx in range(pw):
                    surf.blit(tile(f"pond_{(f + xx + yy) % 4}"), (xx * TILE, yy * TILE))
            surf.blit(spr("lilypads"), (TILE * 2 + 8, TILE + 6))
            surf.blit(spr("lilypads"), (pw * TILE - TILE * 3, TILE * (ph - 2) + 4))
            per.append(surf)
        frames.append((region, per))
    return frames


def pond_reeds(rows):
    out = []
    for (px0, py0, pw, ph) in wm.POND_REGIONS:
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
    def __init__(self, rows, buildings, rects, origins, ponds, lamps, smoke):
        self.rows, self.buildings, self.rects, self.origins = rows, buildings, rects, origins
        self.ponds, self.lamps, self.smoke = ponds, lamps, smoke


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
    for (region, per) in fx.ponds:
        px0, py0, pw, ph = region
        frame = per[int(t * 2.2) % 4]
        surf.blit(frame, (px0 * TILE - cam.x, py0 * TILE - cam.y))
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
            if rows[my][mx] == "P" and (mx * 3 + my * 5) % 4 == 0:
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
