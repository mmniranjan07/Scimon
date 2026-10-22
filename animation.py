"""Modular sprite animation.

Three small building blocks, all driven by `dt` seconds (so speed is identical at 30, 60 or 144 fps):

* `Animation`   -- an immutable frame sequence (+ fps, loop / ping-pong).  `frame_at(t)` is a pure function of time.
* `Animator`    -- a tiny state machine over named Animations, for *objects*: a chest is `closed -> opening -> open`,
                   a terminal screen is just `loop`.  One-shot states chain into the next state automatically.
* `SheetAnimator` -- stateless 4-directional character frames cut from a sheet by a layout dict (settings.SHEET_LAYOUT):
                   `frame(mode, facing, t)`.  Characters already track their own animation clock, so no state is needed.

`Hover` is the procedural float used by overworld Sci-Mon.  Nothing here knows about maps, collision or the game."""
import math
import random

import pygame

import assets
from settings import CHAR_PX, PX, SHEET_LAYOUT


# --------------------------------------------------------------------------- frame sequences
class Animation:
    def __init__(self, frames, fps=8.0, loop=True, pingpong=False):
        if not frames:
            raise ValueError("an Animation needs at least one frame")
        self.frames = list(frames)
        self.fps, self.loop, self.pingpong = float(fps), loop, pingpong
        n = len(self.frames)
        # index order for one full cycle: 0..n-1, plus the way back for ping-pong (without repeating the ends)
        self._order = list(range(n)) + (list(range(n - 2, 0, -1)) if pingpong and n > 2 else [])

    @property
    def duration(self):
        return len(self._order) / self.fps

    def index_at(self, t):
        step = int(max(0.0, t) * self.fps)
        if self.loop:
            return self._order[step % len(self._order)]
        return self._order[min(step, len(self._order) - 1)]          # one-shot: hold the last frame

    def frame_at(self, t):
        return self.frames[self.index_at(t)]

    def finished(self, t):
        return (not self.loop) and t >= self.duration


class Animator:
    """State machine over named animations.

        a = Animator({"closed": Animation(...), "opening": Animation(..., loop=False), "open": Animation(...)},
                     initial="closed", chain={"opening": "open"})
        a.play("opening")      # starts the one-shot; when it ends the animator moves on to "open" by itself
        a.update(dt); surface = a.frame
    """

    def __init__(self, animations, initial, chain=None):
        self.animations, self.chain = animations, dict(chain or {})
        self.state, self.t = initial, 0.0
        if initial not in animations:
            raise KeyError(initial)

    def play(self, name, restart=False):
        if name != self.state or restart:
            self.state, self.t = name, 0.0

    def update(self, dt):
        self.t += dt
        anim = self.animations[self.state]
        nxt = self.chain.get(self.state)
        if nxt and anim.finished(self.t):
            leftover = self.t - anim.duration
            self.state, self.t = nxt, leftover                    # carry the spill-over so timing stays exact

    @property
    def frame(self):
        return self.animations[self.state].frame_at(self.t)

    @property
    def done(self):
        """True when the current state is a finished one-shot with nothing chained after it."""
        a = self.animations[self.state]
        return a.finished(self.t) and self.state not in self.chain


# --------------------------------------------------------------------------- strips & sheets
def strip_frames(surf, frame_w, frame_h, count=None):
    """Cut a horizontal strip into `count` native-resolution frames (all of them when count is None)."""
    n = surf.get_width() // frame_w if count is None else count
    if n <= 0 or frame_h > surf.get_height() or n * frame_w > surf.get_width():
        raise ValueError(f"strip {surf.get_size()} cannot hold {n} frames of {frame_w}x{frame_h}")
    return [surf.subsurface((i * frame_w, 0, frame_w, frame_h)).copy() for i in range(n)]


def scale_frames(frames, factor):
    return [pygame.transform.scale(f, (max(1, round(f.get_width() * factor)), max(1, round(f.get_height() * factor))))
            for f in frames]


def screen_frames(size, color, count=6, seed=7):
    """Procedural 'glowing terminal screen' overlay: scrolling text-like bars, a sweeping scan line and a blinking
    cursor, as native-resolution translucent frames to composite over a monitor sprite."""
    w, h = size
    rng = random.Random(seed)
    lines = [rng.randint(max(2, w // 3), max(3, w - 2)) for _ in range(h // 2 + count)]
    out = []
    for i in range(count):
        f = pygame.Surface((w, h), pygame.SRCALPHA)
        f.fill(color + (70,))
        for row in range(h // 2):
            ln = lines[(row + i) % len(lines)]
            pygame.draw.line(f, color + (235,), (1, row * 2), (min(w - 1, ln), row * 2))
        scan = (i * h) // count
        pygame.draw.line(f, (255, 255, 255, 120), (0, scan), (w, scan))
        if i % 2 == 0:
            f.set_at((min(w - 1, lines[i] // 2 + 2), h - 1), (255, 255, 255, 255))
        out.append(f)
    return out


# --------------------------------------------------------------------------- 4-directional characters
class SheetAnimator:
    """Frames for one character sheet.  Layout (frame size, which column each facing starts at, which row is idle /
    walk, fps) comes from settings.SHEET_LAYOUT, so a new sheet only needs to follow that layout."""

    def __init__(self, sheet, layout=None):
        self.layout = layout or SHEET_LAYOUT
        self.sheet = sheet
        self._anims = {}

    def animation(self, mode, facing):
        key = (mode, facing)
        anim = self._anims.get(key)
        if anim is None:
            L = self.layout
            fw, fh = L["frame"]
            n = L["frames_per_dir"]
            row = L["rows"][mode]
            x0 = L["dir_col"][facing] * fw
            frames = [pygame.transform.scale(self.sheet.subsurface((x0 + i * fw, row * fh, fw, fh)), (fw * PX, fh * PX))
                      for i in range(n)]
            anim = self._anims[key] = Animation(frames, fps=L["fps"][mode])
        return anim

    def frame(self, mode, facing, t):
        return self.animation(mode, facing).frame_at(t)

    def frame_index(self, mode, facing, index):
        a = self.animation(mode, facing)
        return a.frames[index % len(a.frames)]


_sheet_cache = {}


def sheet_animator(rel):
    """Shared SheetAnimator for the character sheet at assets/<rel> (one per file)."""
    sa = _sheet_cache.get(rel)
    if sa is None:
        sa = _sheet_cache[rel] = SheetAnimator(assets.image(rel))
    return sa


# --------------------------------------------------------------------------- MPW overworld sheets (32x32, 4x4)
class MpwSheetAnimator:
    """MPWSP01 overworld sheet: 128x128 = 4 columns x 4 rows of 32x32 frames.  Rows are facings (down, left, right, up);
    frames 0 and 2 are the standing pose, 1 and 3 the two walking steps.  Frames are cropped (rows only) to the union of
    their opaque pixels so the feet sit on the bottom edge, then drawn at CHAR_PX (settings.py, 2x) with nearest-neighbour scaling.
    Same interface as SheetAnimator: animation / frame / frame_index."""
    ROWS = {"down": 0, "left": 1, "right": 2, "up": 3}
    FPS = {"idle": 3.0, "walk": 8.0}

    def __init__(self, sheet):
        self.sheet, self._anims = sheet, {}
        top, bottom = 32, 0
        for r in range(4):
            for c in range(4):
                rect = sheet.subsurface((c * 32, r * 32, 32, 32)).get_bounding_rect()
                if rect.h:
                    top, bottom = min(top, rect.y), max(bottom, rect.bottom)
        self.top, self.bottom = (top, bottom) if bottom > top else (0, 32)

    def _frames(self, facing):
        r = self.ROWS[facing]
        h = self.bottom - self.top
        return [pygame.transform.scale(self.sheet.subsurface((c * 32, r * 32 + self.top, 32, h)), (32 * CHAR_PX, h * CHAR_PX))
                for c in range(4)]

    def animation(self, mode, facing):
        key = (mode, facing)
        anim = self._anims.get(key)
        if anim is None:
            f = self._frames(facing)
            anim = self._anims[key] = Animation(f if mode == "walk" else [f[0]], fps=self.FPS.get(mode, 3.0))
        return anim

    def frame(self, mode, facing, t):
        return self.animation(mode, facing).frame_at(t)

    def frame_index(self, mode, facing, index):
        a = self.animation(mode, facing)
        return a.frames[index % len(a.frames)]


_mpw_cache = {}


def mpw_animator(n):
    """Shared MpwSheetAnimator for assets/mpw/ow/ow<n>.png (n = 1..10)."""
    sa = _mpw_cache.get(n)
    if sa is None:
        sa = _mpw_cache[n] = MpwSheetAnimator(assets.image(f"mpw/ow/ow{n}.png"))
    return sa


# --------------------------------------------------------------------------- hover
class Hover:
    """Smooth vertical float: offset(t) in pixels (negative = up).  `lift(t)` is 0..1 for scaling the ground shadow."""

    def __init__(self, amplitude_px, period=2.4, phase=None):
        self.amp, self.period = amplitude_px, period
        self.phase = random.random() * math.tau if phase is None else phase

    def _s(self, t):
        return math.sin(t * math.tau / self.period + self.phase)

    def offset(self, t):
        return -self.amp * (self._s(t) + 1) / 2

    def lift(self, t):
        return (self._s(t) + 1) / 2
