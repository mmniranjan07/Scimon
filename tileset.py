"""Resolves the roles in tileset_map.py to ready-to-draw Surfaces.

    sprite("floor_grid")        -> world-scale Surface for a static role
    anim_asset("plasma_core")   -> frames + animator recipe for an animated object
    report()                    -> {role: "primary(6, 9)" | "secondary(...)" | "legacy:x_tank" | "MISSING"}

Sources are tried in the order tileset_map lists them, so a missing pack (or a cell that turns out blank) quietly falls
through to the next one and the game still runs; a role with nothing at all gets a loud magenta placeholder and a
single log line, never an exception.  Everything is cached: each role is cut, recoloured and scaled exactly once."""
import logging

import pygame

import assets
import atlas as atlas_mod
import animation
from settings import (MODERN_GRID, MODERN_INTERIORS, MODERN_ROOM_BUILDER, PRIMARY_ANIM_DIR, PRIMARY_ATLASES, PRIMARY_GRID,
                      PX, SECONDARY_ATLAS, SECONDARY_GRID, TILE)
from tileset_map import ANIMS, TILES, info

log = logging.getLogger("scimon.tileset")

_atlases = {}
_native = {}          # source tuple -> (native Surface, scale factor, label) | None
_sprites = {}         # role -> (world Surface, label)
_anims = {}           # role -> AnimAsset
_warned = set()


# --------------------------------------------------------------------------- atlases
def atlas(pack):
    """The loaded Atlas for "primary" / "secondary", or None when that pack is not installed."""
    if pack not in _atlases:
        if pack == "primary":
            rel, grid = PRIMARY_ATLASES.get(PRIMARY_GRID), PRIMARY_GRID
        elif pack == "secondary":
            rel, grid = SECONDARY_ATLAS, SECONDARY_GRID
        elif pack == "modern":
            rel, grid = MODERN_INTERIORS, MODERN_GRID
        elif pack == "builder":
            rel, grid = MODERN_ROOM_BUILDER, MODERN_GRID
        else:
            raise KeyError(pack)
        _atlases[pack] = atlas_mod.Atlas.try_load(rel, grid) if rel else None
    return _atlases[pack]


def reset():
    """Forget everything (tests / hot-swapping settings)."""
    for d in (_atlases, _native, _sprites, _anims, _warned):
        d.clear()


# --------------------------------------------------------------------------- source resolution
def _resolve(src):
    """(native Surface, scale factor, label) for one source tuple, or None if unavailable."""
    if src in _native:
        return _native[src]
    out = None
    kind = src[0]
    try:
        if kind == "primary":
            a = atlas("primary")
            if a:
                surf = a.cell(*src[1:])
                if not atlas_mod.is_blank(surf):
                    out = (surf, a.scale, f"primary{src[1:]}")
        elif kind in ("secondary", "modern"):                  # pixel-rect addressed sheets
            a = atlas(kind)
            if a:
                surf = a.rect(*src[1:])
                if not atlas_mod.is_blank(surf):
                    out = (surf, a.scale, f"{kind}{src[1:]}")
        elif kind == "builder":                                # cell addressed (walls / floors)
            a = atlas("builder")
            if a:
                surf = a.cell(*src[1:])
                if not atlas_mod.is_blank(surf):
                    out = (surf, a.scale, f"builder{src[1:]}")
        elif kind == "legacy":
            surf = assets.image_or_none(f"interiors/{src[1]}.png")
            if surf is not None:
                out = (surf, PX, f"legacy:{src[1]}")
        else:
            raise KeyError(kind)
    except IndexError as e:                     # a mapping that points outside the sheet: log it, try the next source
        _warn(f"bad mapping {src}: {e}")
    _native[src] = out
    return out


def _first(sources):
    for src in sources:
        got = _resolve(src)
        if got:
            return got
    return None


def _warn(msg):
    if msg not in _warned:
        _warned.add(msg)
        log.warning(msg)


def _placeholder(w=TILE, h=TILE):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            pygame.draw.rect(s, (255, 0, 255) if (x // 8 + y // 8) % 2 == 0 else (30, 0, 30), (x, y, 8, 8))
    return s


# --------------------------------------------------------------------------- static roles
def _build_sprite(name):
    d = TILES[name]
    got = _first(d.sources)
    if got is None:
        _warn(f"no art found for role {name!r}; using a placeholder")
        return _placeholder(d.foot[0] * TILE, d.foot[1] * TILE), "MISSING"
    surf, factor, label = got
    if d.recolor:
        surf = atlas_mod.recolor(surf, d.recolor[:2], d.recolor[2])
    return atlas_mod.scale_nearest(surf, factor), label


def sprite(name):
    """World-scale Surface for a static role (shared: do not draw on it)."""
    got = _sprites.get(name)
    if got is None:
        got = _sprites[name] = _build_sprite(name)
    return got[0]


# --------------------------------------------------------------------------- animated roles
class AnimAsset:
    """Everything needed to make independent Animators (and glow lights) for one animated role."""

    def __init__(self, defn, animations, chain, initial, label):
        self.defn, self.animations, self.chain, self.initial, self.label = defn, animations, chain, initial, label
        first = next(iter(animations.values())).frames[0]
        self.size = first.get_size()

    def animator(self):
        return animation.Animator(self.animations, self.initial, self.chain)


def _compose(base, overlay_frames, at):
    """Native-resolution frames: `base` with each overlay frame laid on it at `at`.  The overlay may poke outside the
    base (a flame above a brazier): the canvas grows up/left to fit, with the base at the bottom."""
    bw, bh = base.get_size()
    fw, fh = overlay_frames[0].get_size()
    ox, oy = at
    minx, miny = min(0, ox), min(0, oy)
    w, h = max(bw, ox + fw) - minx, max(bh, oy + fh) - miny
    frames = []
    for f in overlay_frames:
        c = pygame.Surface((w, h), pygame.SRCALPHA)
        c.blit(base, (-minx, -miny))
        c.blit(f, (ox - minx, oy - miny))
        frames.append(c)
    return frames


def _build_anim(name):
    d = ANIMS[name]
    strip_rel = f"{PRIMARY_ANIM_DIR}/{d.strip}" if d.strip else None
    strip = assets.image_or_none(strip_rel) if strip_rel else None

    # ---- chests: closed idle -> opening (one-shot) -> open ------------------------------------------------------
    if d.kind == "chest":
        if strip is None:
            got = _first(d.fallback)
            surf, factor, label = got if got else (_placeholder(16, 16), 1, "MISSING")
            f = atlas_mod.scale_nearest(surf, factor)
            one = animation.Animation([f], fps=1)
            return AnimAsset(d, {"closed": one, "opening": one, "open": one}, {}, "closed", label)
        fw, fh = d.frame
        frames = animation.scale_frames(animation.strip_frames(strip, fw, fh), PX)
        anims = {
            "closed": animation.Animation(frames[0:2], fps=1.5),
            "opening": animation.Animation(frames[2:5], fps=d.fps, loop=False),
            "open": animation.Animation(frames[5:6], fps=1),
        }
        return AnimAsset(d, anims, {"opening": "open"}, "closed", f"strip:{d.strip}")

    # ---- looping objects: base sprite + animated overlay (flame strip or procedural screen) ------------------
    got = _first((d.base,) + tuple(d.fallback)) if d.base else None
    if got is None:
        _warn(f"no art found for animated role {name!r}; using a placeholder")
        surf, factor, label = _placeholder(16, 32), 1, "MISSING"
    else:
        surf, factor, label = got
    overlay, at = None, (0, 0)
    if d.overlay:
        ov = assets.image_or_none(f"{PRIMARY_ANIM_DIR}/{d.overlay['strip']}")
        if ov is not None:
            fw, fh = d.frame
            overlay = animation.strip_frames(ov, fw, fh)
            if d.overlay.get("recolor"):
                lo, hi, shift = d.overlay["recolor"]
                overlay = [atlas_mod.recolor(f, (lo, hi), shift, min_sat=0.25) for f in overlay]
            at = d.overlay.get("at", (0, 0))
    elif d.screen and got is not None and got[2].startswith(("primary", "secondary")):
        x, y, w, h, color = d.screen
        overlay, at = animation.screen_frames((w, h), color, count=6), (x, y)       # screen rect is in base px
    if overlay is None:                                        # pack/strip missing: a still frame still works
        frames = [atlas_mod.scale_nearest(surf, factor)]
    else:
        frames = animation.scale_frames(_compose(surf, overlay, at), factor)
    return AnimAsset(d, {"loop": animation.Animation(frames, fps=d.fps)}, {}, "loop", label)


def anim_asset(name):
    a = _anims.get(name)
    if a is None:
        a = _anims[name] = _build_anim(name)
    return a


# --------------------------------------------------------------------------- tooling
def report():
    """{role: source label} for every role (builds them all) -- `tools/atlas_inspector.py --report`."""
    out = {}
    for n in TILES:
        sprite(n)
        out[n] = _sprites[n][1]
    for n in ANIMS:
        out[n] = anim_asset(n).label
    return out
