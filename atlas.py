"""Sprite-sheet slicing: cut an atlas into uniform grid cells (or explicit pixel rects) and scale them to the world.

An `Atlas` knows nothing about the game.  It owns one sheet and answers "give me the cells (col, row, w, h)" or
"give me this pixel rectangle", returning *native-resolution* surfaces; `to_world()` scales those to the game's TILE
size with nearest-neighbour so pixel art stays crisp.  Which sheet is loaded comes from settings.py; which cell means
"server rack" or "metal floor" lives in tileset_map.py -- this module is pure mechanism.

Cells are addressed in grid units, so one mapping works for 16x, 32x and 48x atlases that share a layout; only the
scale factor changes (TILE / grid)."""
import colorsys

import pygame

import assets
from settings import TILE


class Atlas:
    def __init__(self, rel, grid):
        self.rel, self.grid = rel, int(grid)
        if self.grid <= 0:
            raise ValueError("atlas grid must be positive")
        self.sheet = assets.image(rel)                       # raises if the file is missing / unsafe
        w, h = self.sheet.get_size()
        self.cols, self.rows = w // self.grid, h // self.grid
        self._native = {}                                    # (x, y, w, h) -> Surface

    @classmethod
    def try_load(cls, rel, grid):
        """Atlas or None (missing/invalid file): lets callers fall back to the next pack instead of crashing."""
        if not assets.has(rel) or assets.image_or_none(rel) is None:
            return None
        return cls(rel, grid)

    # ---- slicing ---------------------------------------------------------------------------
    @property
    def scale(self):
        """How much one native pixel is magnified to reach the world's TILE size."""
        return TILE / self.grid

    def rect(self, x, y, w, h):
        """Native-pixel sub-texture (a private copy, so callers may draw on it)."""
        sw, sh = self.sheet.get_size()
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > sw or y + h > sh:
            raise IndexError(f"{self.rel}: rect {(x, y, w, h)} is outside the {sw}x{sh} sheet")
        key = (x, y, w, h)
        surf = self._native.get(key)
        if surf is None:
            surf = self.sheet.subsurface((x, y, w, h)).copy()
            self._native[key] = surf
        return surf

    def cell(self, col, row, cw=1, ch=1):
        """Sub-texture covering `cw` x `ch` grid cells starting at (col, row)."""
        g = self.grid
        if not (0 <= col and 0 <= row and col + cw <= self.cols and row + ch <= self.rows):
            raise IndexError(f"{self.rel}: cell {(col, row, cw, ch)} is outside the {self.cols}x{self.rows} grid")
        return self.rect(col * g, row * g, cw * g, ch * g)

    def cells(self):
        """Iterate every cell as (col, row, Surface) -- handy for tooling and tests."""
        for r in range(self.rows):
            for c in range(self.cols):
                yield c, r, self.cell(c, r)

    # ---- scaling ---------------------------------------------------------------------------
    def to_world(self, surf):
        """Scale a native surface to world size (nearest-neighbour; exact pixel doubling at integer factors)."""
        return scale_nearest(surf, self.scale)


def scale_nearest(surf, factor):
    if abs(factor - 1.0) < 1e-6:
        return surf
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (max(1, round(w * factor)), max(1, round(h * factor))))


def is_blank(surf):
    """True if every pixel is fully transparent (empty atlas cell)."""
    return pygame.mask.from_surface(surf, 1).count() == 0


# ---- selective recolour -------------------------------------------------------------------------
def recolor(surf, hue_from, hue_to_shift, min_sat=0.35):
    """Copy of `surf` where pixels whose hue is in `hue_from` (degrees, inclusive, may wrap) and whose saturation is
    at least `min_sat` are rotated by `hue_to_shift` degrees.  Greys, whites and the steel-blue body of a sprite are
    left alone, so e.g. an orange flame can become cyan plasma without tinting the metal around it.
    Done once per sprite at load (tiny surfaces), never per frame."""
    out = surf.copy()
    lo, hi = hue_from
    w, h = out.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = out.get_at((x, y))
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            deg = hh * 360
            in_range = (lo <= deg <= hi) if lo <= hi else (deg >= lo or deg <= hi)
            if ss >= min_sat and in_range:
                nr, ng, nb = colorsys.hsv_to_rgb(((deg + hue_to_shift) % 360) / 360, ss, vv)
                out.set_at((x, y), (round(nr * 255), round(ng * 255), round(nb * 255), a))
    return out
