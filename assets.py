"""Asset loader: every image/font is loaded once, converted to the display format and cached.

All scaling goes through small keyed caches (so a sprite scaled to the same size twice is
the same Surface), which keeps frame times flat and memory bounded -- the set of sizes the
game asks for is small and fixed."""
import os

import pygame

from data import SPECIES
from settings import ASSET_EXTENSIONS, ASSETS, MAX_IMAGE_BYTES, MAX_IMAGE_SIDE, TILE

_raw = {}        # path -> source Surface
_scaled = {}     # (path, w, h, smooth) -> Surface
_fonts = {}      # (kind, size) -> Font

FONT_FILES = {
    "display": "PressStart2P-Regular.ttf",   # chunky 8-bit headings / HUD (V34 --font-pixel)
    "body": "VT323-Regular.ttf",             # readable terminal body text (V34 --font-pixel-body)
    "ui": "DejaVuSans.ttf",                  # clean plain interface text (menus)
    "ui_b": "DejaVuSans-Bold.ttf",           # bold interface headings / section labels
}


def safe_path(rel, directory=False):
    """Resolve `rel` (relative to assets/) to a real file path, refusing anything that could escape the assets
    folder: absolute paths, '..' traversal, symlinks pointing outside, NUL bytes and unlisted extensions.
    Sprite paths come from settings.py (and could one day come from a mod/config file), so they are validated
    here, in the one place every load goes through."""
    if not isinstance(rel, str) or not rel or "\x00" in rel or os.path.isabs(rel):
        raise ValueError(f"bad asset path: {rel!r}")
    root = os.path.realpath(ASSETS)
    full = os.path.realpath(os.path.join(root, rel))
    try:
        inside = os.path.commonpath([root, full]) == root
    except ValueError:                                   # different drive on Windows
        inside = False
    if not inside:
        raise ValueError(f"asset path escapes the assets folder: {rel!r}")
    if not directory and os.path.splitext(full)[1].lower() not in ASSET_EXTENSIONS:
        raise ValueError(f"asset type not allowed: {rel!r}")
    return full


_path = safe_path        # historical name used by font() and preload()


def has(rel):
    """True if `rel` is a loadable asset (never raises) -- lets the tile resolver fall through to the next pack."""
    try:
        return os.path.isfile(safe_path(rel))
    except ValueError:
        return False


def image(rel):
    """Source surface for an asset path relative to assets/ (cached)."""
    surf = _raw.get(rel)
    if surf is None:
        full = safe_path(rel)
        if os.path.getsize(full) > MAX_IMAGE_BYTES:
            raise ValueError(f"asset too large: {rel!r}")
        surf = pygame.image.load(full)
        if max(surf.get_size()) > MAX_IMAGE_SIDE:
            raise ValueError(f"asset dimensions too large: {rel!r} {surf.get_size()}")
        surf = surf.convert_alpha() if pygame.display.get_surface() else surf
        _raw[rel] = surf
    return surf


def image_or_none(rel):
    """Like image() but returns None when the file is missing or invalid, so optional packs never crash the game."""
    try:
        return image(rel) if has(rel) else None
    except (ValueError, pygame.error, OSError):
        return None


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


def fit(rel, max_w, max_h, smooth=True, trim=False):
    """Scale keeping aspect ratio so the image fits in max_w x max_h.  With `trim`, transparent margins are cut
    first (cached bounding box), so the art renders at its true size and smooth scaling never blends the empty
    border into the visible edge pixels."""
    src = image(rel)
    if trim:
        r = _opaque_bbox(rel)
        if r.width < src.get_width() or r.height < src.get_height():
            src = src.subsurface(r)
    w, h = src.get_size()
    k = min(max_w / w, max_h / h)
    w2, h2 = max(1, int(w * k)), max(1, int(h * k))
    key = ("fit2", rel, w2, h2, smooth, trim)
    out = _scaled.get(key)
    if out is None:
        fn = pygame.transform.smoothscale if smooth else pygame.transform.scale
        out = _scaled[key] = fn(src, (w2, h2))
    return out


_trim_cache = {}


def _opaque_bbox(rel):
    r = _trim_cache.get(rel)
    if r is None:
        r = _trim_cache[rel] = image(rel).get_bounding_rect()
    return r


# --- Scimon sprites (assets/scimon/<species>-front.png / -back.png, the original art) -----------------------------
_back_cache = {}


def back_path(species_id):
    """Asset path of the species' back-view art, or None when only a front still exists.  Data keeps
    `back` None for the wild cast (tests/specimens pins that), so art presence is checked on disk once
    per species and cached: every species of the collection import gets a real back view this way."""
    if species_id not in _back_cache:
        sp = SPECIES[species_id]
        cand = "scimon/" + (sp.back or f"{species_id}-back.png")
        _back_cache[species_id] = cand if (sp.back or has(cand)) else None
    return _back_cache[species_id]


def mon_path(species_id, back=False):
    sp = SPECIES[species_id]
    if back:
        cand = back_path(species_id)
        if cand:
            return cand
    return "scimon/" + sp.front


def mon_image(species_id, max_w, max_h, back=False):
    return fit(mon_path(species_id, back), max_w, max_h, trim=True)


def mon_anim(species_id, kind, max_w, max_h, max_k=4):
    """Frame list for the idle / attack animation.  The original Scimon art is a single still per species, so this is one
    frame, drawn at the same scale as mon_image(); ScimonSprite then breathes (idle) and lunges (attack) on top of it."""
    return [mon_image(species_id, max_w, max_h)]


def ui_icon(name, scale=2):
    """MPW UI icon (assets/mpw/ui/<name>.png) scaled by an integer factor with nearest neighbour."""
    img = image(f"mpw/ui/{name}.png")
    return scaled(f"mpw/ui/{name}.png", img.get_width() * scale, img.get_height() * scale, smooth=False)


def item_icon(item_id, scale=2):
    """Pixel-art icon for a disc / module / item (assets/items/<id>.png), nearest-neighbour scaled; None when absent."""
    p = f"items/{item_id}.png"
    if not has(p):
        return None
    img = image(p)
    return scaled(p, img.get_width() * scale, img.get_height() * scale, smooth=False)


def font(kind, size):
    key = (kind, size)
    f = _fonts.get(key)
    if f is None:
        f = pygame.font.Font(_path("fonts/" + FONT_FILES[kind]), size)
        _fonts[key] = f
    return f


def preload_steps():
    """Yield (done, total) after each asset, so a caller can draw a progress bar between loads
    (the browser build needs that: one long blocking call would leave the canvas blank)."""
    jobs = []
    for folder in ("scimon", "mpw/buildings", "mpw/trees", "mpw/ow", "mpw/ui", "mpw/fx", "mpw/bg", "tiles/nature", "tiles/hitech", "tiles/res", "interiors", "town", "items"):
        full = safe_path(folder, directory=True)
        for name in sorted(os.listdir(full)):
            if name.lower().endswith(".png"):
                jobs.append((False, f"{folder}/{name}"))
    for kind, sizes in (("display", (8, 16, 24, 32, 48, 64)), ("body", (16, 20, 24, 28, 32, 40, 48)),
                        ("ui", (12, 13, 14, 15, 18)), ("ui_b", (12, 13, 15, 18))):
        for s in sizes:
            jobs.append((True, (kind, s)))
    for n, (is_font, ref) in enumerate(jobs, 1):
        font(*ref) if is_font else image(ref)
        yield n, len(jobs)


def preload():
    """Touch every asset once so the first time anything appears there is no disk hit."""
    for _ in preload_steps():
        pass
