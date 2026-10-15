"""Asset loader: every image/font is loaded once, converted to the display format and cached.

All scaling goes through small keyed caches (so a sprite scaled to the same size twice is
the same Surface), which keeps frame times flat and memory bounded -- the set of sizes the
game asks for is small and fixed."""
import os

import pygame

from settings import ASSETS, TILE
from data import SPECIES

_raw = {}        # path -> source Surface
_scaled = {}     # (path, w, h, smooth) -> Surface
_fonts = {}      # (kind, size) -> Font

FONT_FILES = {
    "display": "PressStart2P-Regular.ttf",   # chunky 8-bit headings / HUD (V34 --font-pixel)
    "body": "VT323-Regular.ttf",             # readable terminal body text (V34 --font-pixel-body)
}


def _path(rel):
    return os.path.join(ASSETS, rel)


def image(rel):
    """Source surface for an asset path relative to assets/ (cached)."""
    surf = _raw.get(rel)
    if surf is None:
        surf = pygame.image.load(_path(rel))
        surf = surf.convert_alpha() if pygame.display.get_surface() else surf
        _raw[rel] = surf
    return surf


def scaled(rel, w, h, smooth=True):
    key = (rel, int(w), int(h), smooth)
    surf = _scaled.get(key)
    if surf is None:
        src = image(rel)
        w, h = max(1, int(w)), max(1, int(h))
        fn = pygame.transform.smoothscale if smooth else pygame.transform.scale
        surf = fn(src, (w, h))
        _scaled[key] = surf
    return surf


def fit(rel, max_w, max_h, smooth=True):
    """Scale keeping aspect ratio so the image fits in max_w x max_h."""
    src = image(rel)
    w, h = src.get_size()
    k = min(max_w / w, max_h / h)
    return scaled(rel, w * k, h * k, smooth)


def mon_path(species_id, back=False):
    sp = SPECIES[species_id]
    name = sp.back if (back and sp.back) else sp.front
    return "scimon/" + name


def mon_image(species_id, max_w, max_h, back=False):
    return fit(mon_path(species_id, back), max_w, max_h)


def font(kind, size):
    key = (kind, size)
    f = _fonts.get(key)
    if f is None:
        f = pygame.font.Font(_path("fonts/" + FONT_FILES[kind]), size)
        _fonts[key] = f
    return f


def preload():
    """Touch every asset once so the first time anything appears there is no disk hit."""
    for folder in ("buildings", "scimon", "tiles/nature", "tiles/hitech", "tiles/res", "interiors", "characters", "town"):
        full = _path(folder)
        for name in sorted(os.listdir(full)):
            if name.lower().endswith(".png"):
                image(f"{folder}/{name}")
    for kind, sizes in (("display", (8, 16, 24, 32, 48, 64)), ("body", (16, 20, 24, 28, 32, 40, 48))):
        for s in sizes:
            font(kind, s)
